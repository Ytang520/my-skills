#!/usr/bin/env python3
"""
Batch-retrieve arXiv papers (metadata and/or PDFs). Default mode: both.

Reliability design (v2, 2026-07):
- id_list is CHUNKED (default 100 ids/request). The arxiv package embeds the
  entire id_list in every page URL (Search._url_args), so unchunked large
  lists produce over-long URLs that arXiv rejects; retrying the same giant
  URL also triggers IP-level 429 throttling.
- One shared arxiv.Client across chunks keeps delay_seconds politeness.
- Each chunk gets its own exponential-backoff retries; a chunk that still
  fails is recorded in `failures` and the run CONTINUES (no all-or-nothing).
- Resume is ON by default: ids whose metadata/PDF already exists are skipped
  (--no-resume to force refetch).
- stdout/stderr are reconfigured to UTF-8 so Windows cp1252 consoles don't
  crash on non-ASCII error text.
"""
from __future__ import annotations

import argparse
import http.client
import json
import logging
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import arxiv

# arXiv tolerates ~100-200 ids per id_list; 100 is the battle-tested default.
DEFAULT_ID_CHUNK_SIZE = 100
MAX_ID_CHUNK_SIZE = 200
# Chunk-level retries ride on top of the library's internal per-page retries.
CHUNK_RETRIES = 5
BACKOFF_BASE_S = 30.0  # 429s need long, growing waits, not instant retries

logging.basicConfig(
    format="[%(asctime)s %(levelname)s] %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)


def ensure_utf8_stdio() -> None:
    """Avoid Windows cp1252 UnicodeEncodeError on non-ASCII output."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def paper_to_dict(result: arxiv.Result) -> dict:
    short_id = result.get_short_id()
    return {
        "id": short_id,
        "entry_id": result.entry_id,
        "title": result.title,
        "authors": [a.name for a in result.authors],
        "abstract": result.summary,
        "published": result.published.isoformat() if result.published else None,
        "updated": result.updated.isoformat() if result.updated else None,
        "primary_category": result.primary_category,
        "categories": list(result.categories),
        "pdf_url": result.pdf_url,
        "comment": result.comment,
        "doi": result.doi,
        "journal_ref": result.journal_ref,
    }


def load_ids_from_json(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        ids = []
        for item in data:
            if isinstance(item, str):
                ids.append(item)
            elif isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
        return ids
    if isinstance(data, dict):
        papers = data.get("papers") or data.get("results") or []
        ids = []
        for item in papers:
            if isinstance(item, dict) and item.get("id"):
                ids.append(str(item["id"]))
            elif isinstance(item, str):
                ids.append(item)
        if ids:
            return ids
        if data.get("id"):
            return [str(data["id"])]
    raise ValueError(f"Could not parse paper ids from {path}")


def normalize_id(arxiv_id: str) -> str:
    text = arxiv_id.strip()
    text = text.replace("https://arxiv.org/abs/", "")
    text = text.replace("http://arxiv.org/abs/", "")
    text = text.replace("arxiv:", "")
    if text.endswith(".pdf"):
        text = text[:-4]
    text = text.replace("/pdf/", "/").strip("/")
    return text


def base_id(arxiv_id: str) -> str:
    """Version-less id: 2502.15806v2 -> 2502.15806."""
    text = normalize_id(arxiv_id)
    return text.rsplit("v", 1)[0] if "v" in text else text


def safe_filename(arxiv_id: str) -> str:
    return normalize_id(arxiv_id).replace("/", "_")


def existing_stems(directory: Path, suffix: str) -> set[str]:
    """Stems of existing files, indexed both with and without version suffix."""
    stems: set[str] = set()
    if directory.is_dir():
        for f in directory.glob(f"*{suffix}"):
            stems.add(f.stem)
            stems.add(base_id(f.stem))
    return stems


def download_pdf(url: str, dest: Path, retries: int = 5, delay: float = 3.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    # Prefer HTTPS CDN-style URL without trailing version quirks
    pdf_url = url if url.endswith(".pdf") else f"{url}.pdf"
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                pdf_url,
                headers={"User-Agent": "arxiv-skill/1.0 (mailto:local@localhost)"},
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                chunks: list[bytes] = []
                expected = resp.headers.get("Content-Length")
                expected_n = int(expected) if expected and expected.isdigit() else None
                while True:
                    chunk = resp.read(1024 * 256)
                    if not chunk:
                        break
                    chunks.append(chunk)
                data = b"".join(chunks)
                if expected_n is not None and len(data) < expected_n:
                    raise http.client.IncompleteRead(data, expected_n - len(data))
            dest.write_bytes(data)
            return
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            http.client.IncompleteRead,
            http.client.RemoteDisconnected,
        ) as exc:
            last_error = exc
            logging.warning("PDF download attempt %s failed for %s: %s", attempt, pdf_url, exc)
            if dest.exists():
                dest.unlink(missing_ok=True)
            if attempt < retries:
                time.sleep(delay * attempt)
    raise RuntimeError(f"Failed to download {pdf_url}: {last_error}")


def fetch_by_ids(
    ids: list[str],
    client: arxiv.Client | None = None,
    chunk_size: int = DEFAULT_ID_CHUNK_SIZE,
) -> tuple[list[arxiv.Result], list[str]]:
    """Fetch Results for ids via CHUNKED id_list requests.

    Returns (results, failed_ids). A shared client is used so the library's
    delay_seconds rate limit applies across chunk boundaries. Each chunk is
    retried with exponential backoff; unrecoverable chunks are collected in
    failed_ids instead of aborting the whole run.
    """
    client = client or arxiv.Client(page_size=100, delay_seconds=10.0, num_retries=3)
    normalized = [normalize_id(i) for i in ids]
    chunk_size = max(1, min(chunk_size, MAX_ID_CHUNK_SIZE))

    results: list[arxiv.Result] = []
    failed: list[str] = []
    n_chunks = (len(normalized) + chunk_size - 1) // chunk_size
    for ci, start in enumerate(range(0, len(normalized), chunk_size), start=1):
        chunk = normalized[start:start + chunk_size]
        for attempt in range(1, CHUNK_RETRIES + 1):
            try:
                search = arxiv.Search(id_list=chunk, max_results=len(chunk))
                results.extend(client.results(search))
                logging.info("chunk %d/%d: fetched %d ids", ci, n_chunks, len(chunk))
                break
            except Exception as exc:  # noqa: BLE001 - backoff and isolate per chunk
                wait = BACKOFF_BASE_S * attempt
                logging.warning(
                    "chunk %d/%d attempt %d/%d failed: %s; sleeping %.0fs",
                    ci, n_chunks, attempt, CHUNK_RETRIES, exc, wait,
                )
                time.sleep(wait)
        else:
            logging.error(
                "chunk %d/%d FAILED after %d attempts; %d ids recorded as failed",
                ci, n_chunks, CHUNK_RETRIES, len(chunk),
            )
            failed.extend(chunk)
    return results, failed


def retrieve(
    ids: list[str],
    out_dir: Path,
    mode: str = "both",
    resume: bool = True,
    chunk_size: int = DEFAULT_ID_CHUNK_SIZE,
) -> dict:
    mode = mode.casefold()
    if mode not in {"both", "metadata", "pdf"}:
        raise ValueError("mode must be both|metadata|pdf")

    meta_dir = out_dir / "metadata"
    pdf_dir = out_dir / "pdfs"
    if mode in {"both", "metadata"}:
        meta_dir.mkdir(parents=True, exist_ok=True)
    if mode in {"both", "pdf"}:
        pdf_dir.mkdir(parents=True, exist_ok=True)

    # Resume: skip ids whose outputs already exist for the requested mode.
    meta_have = existing_stems(meta_dir, ".json") if mode in {"both", "metadata"} else set()
    pdf_have = existing_stems(pdf_dir, ".pdf") if mode in {"both", "pdf"} else set()
    pending: list[str] = []
    skipped = 0
    for raw_id in ids:
        nid = normalize_id(raw_id)
        need_meta = mode in {"both", "metadata"} and nid not in meta_have
        need_pdf = mode in {"both", "pdf"} and nid not in pdf_have
        if resume and not (need_meta or need_pdf):
            skipped += 1
            continue
        pending.append(raw_id)
    if skipped:
        logging.info("resume: skipping %d ids with existing outputs", skipped)

    results, fetch_failed = fetch_by_ids(pending, chunk_size=chunk_size)
    by_id = {r.get_short_id(): r for r in results}
    # Also index without version suffix
    for r in results:
        short = r.get_short_id()
        by_id[short] = r
        if "v" in short:
            base = short.rsplit("v", 1)[0]
            by_id.setdefault(base, r)

    papers_meta: list[dict] = []
    downloaded: list[str] = []
    failures: list[dict] = [{"id": i, "error": "chunk fetch failed after retries"} for i in fetch_failed]

    for raw_id in pending:
        nid = normalize_id(raw_id)
        if nid in fetch_failed:
            continue
        result = by_id.get(nid) or by_id.get(base_id(nid))
        if result is None:
            failures.append({"id": raw_id, "error": "not found via arXiv API"})
            continue

        meta = paper_to_dict(result)
        papers_meta.append(meta)
        short = meta["id"]
        stem = safe_filename(short)

        if mode in {"both", "metadata"}:
            meta_path = meta_dir / f"{stem}.json"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        if mode in {"both", "pdf"}:
            pdf_url = meta.get("pdf_url")
            pdf_path = pdf_dir / f"{stem}.pdf"
            if not pdf_url:
                failures.append({"id": short, "error": "missing pdf_url"})
                continue
            if resume and pdf_path.exists():
                continue
            try:
                download_pdf(pdf_url, pdf_path)
                downloaded.append(str(pdf_path))
                logging.info("Downloaded PDF: %s", pdf_path)
            except Exception as exc:  # noqa: BLE001 - collect and continue batch
                failures.append({"id": short, "error": str(exc)})

    summary = {
        "ok": len(failures) == 0,
        "mode": mode,
        "requested": len(ids),
        "resumed_skipped": skipped,
        "chunk_size": chunk_size,
        "metadata_count": len(papers_meta),
        "pdf_count": len(downloaded),
        "downloaded_pdfs": downloaded,
        "failures": failures,
        "out_dir": str(out_dir.resolve()),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "retrieve_summary.json"
    bundle = {"summary": summary, "papers": papers_meta}
    summary_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()

    parser = argparse.ArgumentParser(
        description="Batch retrieve arXiv papers (metadata and/or PDFs). Default: both."
    )
    parser.add_argument(
        "--id",
        "-i",
        action="append",
        default=[],
        help="arXiv id (repeatable). Example: -i 2401.12345 -i 2305.00001",
    )
    parser.add_argument(
        "--from-json",
        type=Path,
        help="Load ids from search results JSON (metadata/results.json)",
    )
    parser.add_argument(
        "--mode",
        default="both",
        choices=["both", "metadata", "pdf"],
        help="Retrieve mode (default: both)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("arxiv_results"),
        help="Output directory (default: ./arxiv_results)",
    )
    parser.add_argument(
        "--id-chunk-size",
        type=int,
        default=DEFAULT_ID_CHUNK_SIZE,
        help=f"ids per arXiv API request (default {DEFAULT_ID_CHUNK_SIZE}, max {MAX_ID_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Refetch ids even if their metadata/PDF already exists in out-dir",
    )
    args = parser.parse_args(argv)

    ids: list[str] = list(args.id or [])
    if args.from_json:
        ids.extend(load_ids_from_json(args.from_json))
    # de-dupe preserving order
    seen: set[str] = set()
    unique_ids: list[str] = []
    for i in ids:
        n = normalize_id(i)
        if n in seen:
            continue
        seen.add(n)
        unique_ids.append(n)

    if not unique_ids:
        print("Provide at least one --id or --from-json", file=sys.stderr)
        sys.exit(1)

    summary = retrieve(
        unique_ids,
        out_dir=args.out_dir.resolve(),
        mode=args.mode,
        resume=not args.no_resume,
        chunk_size=args.id_chunk_size,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
