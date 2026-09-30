#!/usr/bin/env python3
"""
Search arXiv and write paper metadata.

Modes:
  - fuzzy (default): free-text / paper-name relevance search (not exact keyword containment)
  - keyword: exact keyword query (from build_query / user-confirmed variants)
  - id: direct lookup by arXiv id(s)
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

import arxiv

# New-style (YYMM.NNNNN) or old-style (archive/NNNNNNN) arXiv ids
ARXIV_ID_RE = re.compile(
    r"(?:"
    r"(?:\d{4}\.\d{4,5})(?:v\d+)?"
    r"|"
    r"(?:[a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?"
    r")",
    re.IGNORECASE,
)

# Explicit keyword-mode triggers (any one => keyword). Keep fuzzy otherwise.
KEYWORD_TRIGGERS = (
    "keyword search",
    "exact keyword",
    "关键词检索",
    "用关键词",
    "关键词搜索",
    "关键词匹配",
    "必须包含",
    "必须同时包含",
    "强制包含",
    "精确匹配",
    "exact match",
    "contain both",
    "contains both",
    "hard containment",
)

logging.basicConfig(
    format="[%(asctime)s %(levelname)s] %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)


def ensure_utf8_stdio() -> None:
    """Avoid Windows cp1252 UnicodeEncodeError on Chinese output."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def resolve_max_results(value: str | int) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip().casefold()
    if text in {"all", "全部"}:
        return 1000
    return int(text)


def normalize_id(arxiv_id: str) -> str:
    text = arxiv_id.strip()
    text = text.replace("https://arxiv.org/abs/", "")
    text = text.replace("http://arxiv.org/abs/", "")
    text = text.replace("https://arxiv.org/pdf/", "")
    text = text.replace("http://arxiv.org/pdf/", "")
    text = text.replace("arxiv:", "")
    if text.endswith(".pdf"):
        text = text[:-4]
    return text.strip("/")


def looks_like_arxiv_id(text: str) -> bool:
    cleaned = normalize_id(text)
    return bool(ARXIV_ID_RE.fullmatch(cleaned))


def extract_arxiv_ids(text: str) -> list[str]:
    found = ARXIV_ID_RE.findall(text)
    # de-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for item in found:
        nid = normalize_id(item)
        if nid in seen:
            continue
        seen.add(nid)
        out.append(nid)
    return out


def has_keyword_trigger(user_text: str) -> bool:
    text = user_text.strip()
    if not text:
        return False
    lower = text.casefold()
    for trigger in KEYWORD_TRIGGERS:
        if trigger.casefold() in lower:
            return True
    # English hard-filter "contain/contains/containment" as forced filter,
    # but not casual Chinese 「相关」.
    if re.search(r"\bcontain(?:s|ment)?\b", lower):
        return True
    return False


def detect_search_mode(user_text: str) -> str:
    """
    Classify user utterance into id | keyword | fuzzy.

    Priority: id > keyword triggers > fuzzy (default).
    """
    text = user_text.strip()
    if not text:
        return "fuzzy"
    if looks_like_arxiv_id(text):
        return "id"

    ids = extract_arxiv_ids(text)
    keyword = has_keyword_trigger(text)

    # Short id-centric requests (e.g. "下载 1706.03762") -> id
    if ids and not keyword:
        remainder = text
        for i in ids:
            remainder = re.sub(re.escape(i), " ", remainder, flags=re.IGNORECASE)
        remainder = re.sub(
            r"https?://arxiv\.org/(?:abs|pdf)/|arxiv:|\.pdf",
            " ",
            remainder,
            flags=re.IGNORECASE,
        )
        remainder = re.sub(r"\s+", " ", remainder).strip()
        id_verbs = (
            "下载",
            "获取",
            "找",
            "搜",
            "retrieve",
            "download",
            "get",
            "fetch",
            "paper",
            "论文",
            "这篇",
            "这个",
            "帮我",
            "请",
        )
        leftover = remainder
        for v in id_verbs:
            leftover = re.sub(re.escape(v), " ", leftover, flags=re.IGNORECASE)
        leftover = re.sub(r"\s+", " ", leftover).strip(" 、,.")
        if not leftover or len(text) <= 48:
            return "id"

    if keyword:
        return "keyword"
    return "fuzzy"


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


def write_markdown(papers: list[dict], path: Path, query: str, mode: str) -> None:
    lines = [
        "# arXiv search results",
        "",
        f"Mode: `{mode}`",
        f"Query: `{query}`",
        f"Count: {len(papers)}",
        "",
    ]
    for i, p in enumerate(papers, start=1):
        authors = ", ".join(p.get("authors") or [])
        lines.extend(
            [
                f"## {i}. {p.get('title', '')}",
                "",
                f"- ID: `{p.get('id')}`",
                f"- Authors: {authors}",
                f"- Published: {p.get('published')}",
                f"- Categories: {', '.join(p.get('categories') or [])}",
                f"- PDF: {p.get('pdf_url')}",
                "",
                p.get("abstract") or "",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_fuzzy_query(name_or_text: str) -> str:
    """
    Free-text relevance query. Does NOT force exact keyword containment
    or field-prefixed Boolean groups. Softly prefers title matches when
    the input looks like a paper title (multi-word).
    """
    text = " ".join(name_or_text.strip().split())
    if not text:
        return ""
    # Multi-word: bias toward title while still allowing broader relevance hits
    if " " in text and not text.startswith("ti:") and ":" not in text.split()[0]:
        # Bare free text is the fuzzy default; also OR a quoted title hint
        quoted = text if (text[0] == '"' and text[-1] == '"') else f'"{text}"'
        return f"({text}) OR ti:{quoted}"
    return text


def search_by_query(
    query: str,
    max_results: int,
    sort_by: str,
) -> list[dict]:
    sort_map = {
        "SubmittedDate": arxiv.SortCriterion.SubmittedDate,
        "Relevance": arxiv.SortCriterion.Relevance,
        "LastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
    }
    if sort_by not in sort_map:
        raise ValueError(f"Unknown sort_by: {sort_by}. Choose from {list(sort_map)}")

    client = arxiv.Client(page_size=100, delay_seconds=10.0, num_retries=5)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=sort_map[sort_by],
    )

    papers: list[dict] = []
    start = time.time()
    logging.info("Searching arXiv (%s): %s", sort_by, query)

    for result in client.results(search):
        papers.append(paper_to_dict(result))
        if len(papers) >= max_results:
            break

    logging.info("Fetched %s papers in %.1fs", len(papers), time.time() - start)
    return papers


# arXiv tolerates ~100-200 ids per id_list request; the arxiv package embeds
# the ENTIRE id_list in every page URL, so unchunked large lists fail.
ID_CHUNK_SIZE = 100
CHUNK_RETRIES = 5
BACKOFF_BASE_S = 30.0


def iter_results_by_ids(ids: list[str], client: arxiv.Client | None = None):
    """Yield arxiv.Result for ids using chunked id_list requests.

    One shared client keeps delay_seconds politeness across chunks; each
    chunk retries with exponential backoff and is skipped (logged) rather
    than aborting the whole lookup if it keeps failing.
    """
    client = client or arxiv.Client(page_size=100, delay_seconds=10.0, num_retries=3)
    for start in range(0, len(ids), ID_CHUNK_SIZE):
        chunk = ids[start:start + ID_CHUNK_SIZE]
        for attempt in range(1, CHUNK_RETRIES + 1):
            try:
                search = arxiv.Search(id_list=chunk, max_results=len(chunk))
                yield from client.results(search)
                break
            except Exception as exc:  # noqa: BLE001 - backoff and isolate per chunk
                wait = BACKOFF_BASE_S * attempt
                logging.warning(
                    "id chunk starting at %d attempt %d/%d failed: %s; sleeping %.0fs",
                    start, attempt, CHUNK_RETRIES, exc, wait,
                )
                time.sleep(wait)
        else:
            logging.error("id chunk starting at %d FAILED; %d ids skipped", start, len(chunk))


def search_by_ids(ids: list[str], max_results: int | None = None) -> list[dict]:
    normalized = [normalize_id(i) for i in ids]
    # de-dupe
    seen: set[str] = set()
    unique: list[str] = []
    for i in normalized:
        if i in seen:
            continue
        seen.add(i)
        unique.append(i)

    limit = max_results if max_results is not None else len(unique)
    display = ", ".join(unique) if len(unique) <= 10 else f"{', '.join(unique[:10])}, ... ({len(unique)} ids)"

    papers: list[dict] = []
    start = time.time()
    logging.info("Looking up arXiv ids: %s", display)

    for result in iter_results_by_ids(unique):
        papers.append(paper_to_dict(result))
        if len(papers) >= limit:
            break

    logging.info("Fetched %s papers in %.1fs", len(papers), time.time() - start)
    return papers


# Backward-compatible alias used by older callers / unit checks
def search_arxiv(
    query: str,
    max_results: int,
    sort_by: str = "SubmittedDate",
) -> list[dict]:
    return search_by_query(query, max_results=max_results, sort_by=sort_by)


def main(argv: list[str] | None = None) -> int:
    ensure_utf8_stdio()

    parser = argparse.ArgumentParser(
        description=(
            "Search arXiv and write metadata. "
            "Default mode is fuzzy (name/free-text). "
            "Use --mode keyword for exact keyword queries; --mode id for arXiv ids."
        )
    )
    parser.add_argument(
        "--mode",
        default="fuzzy",
        choices=["fuzzy", "keyword", "id"],
        help="Search mode (default: fuzzy)",
    )
    parser.add_argument(
        "--query",
        "-q",
        default=None,
        help="Query string. Fuzzy: paper name / free text. Keyword: confirmed Boolean query.",
    )
    parser.add_argument(
        "--name",
        "-n",
        default=None,
        help="Paper name / free-text alias for fuzzy mode (same as --query in fuzzy).",
    )
    parser.add_argument(
        "--id",
        "-i",
        action="append",
        default=[],
        help="arXiv id (repeatable). Implies id mode when --mode omitted intents via ids.",
    )
    parser.add_argument(
        "--max-results",
        default="5",
        help='Max papers to fetch (default: 5). Use "all" or 1000 for up to 1000.',
    )
    parser.add_argument(
        "--sort",
        default=None,
        choices=["SubmittedDate", "Relevance", "LastUpdatedDate"],
        help="Sort criterion. Defaults: fuzzy->Relevance, keyword->SubmittedDate",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("arxiv_results"),
        help="Output directory (default: ./arxiv_results)",
    )
    parser.add_argument(
        "--detect-mode",
        metavar="UTTERANCE",
        default=None,
        help="Classify an utterance as fuzzy|keyword|id and exit (no network).",
    )
    args = parser.parse_args(argv)

    if args.detect_mode is not None:
        mode = detect_search_mode(args.detect_mode)
        print(json.dumps({"utterance": args.detect_mode, "mode": mode}, ensure_ascii=False))
        return 0

    max_results = resolve_max_results(args.max_results)
    if max_results < 1:
        print("--max-results must be >= 1", file=sys.stderr)
        sys.exit(1)

    mode = args.mode
    ids = [normalize_id(i) for i in (args.id or [])]
    text = (args.query or args.name or "").strip()

    # Auto-detect id mode when only ids are given, or query is purely an id
    if ids and not text and mode == "fuzzy":
        mode = "id"
    if not ids and text and looks_like_arxiv_id(text) and mode == "fuzzy":
        mode = "id"
        ids = [normalize_id(text)]
        text = ""
    if mode == "id" and not ids and text:
        ids = extract_arxiv_ids(text) or ([normalize_id(text)] if looks_like_arxiv_id(text) else [])

    if mode == "id":
        if not ids:
            print("id mode requires --id or an arXiv id in --query", file=sys.stderr)
            sys.exit(1)
        display_query = ", ".join(ids)
        papers = search_by_ids(ids, max_results=max_results)
        sort_used = "id_list"
    elif mode == "fuzzy":
        source = text or ""
        if not source:
            print("fuzzy mode requires --query / --name (paper name or free text)", file=sys.stderr)
            sys.exit(1)
        # If user pasted mixed text containing ids, prefer id hits first
        embedded = extract_arxiv_ids(source)
        if embedded and looks_like_arxiv_id(source):
            display_query = ", ".join(embedded)
            papers = search_by_ids(embedded, max_results=max_results)
            sort_used = "id_list"
            mode = "id"
        else:
            fuzzy_q = build_fuzzy_query(source)
            sort_used = args.sort or "Relevance"
            display_query = fuzzy_q
            papers = search_by_query(fuzzy_q, max_results=max_results, sort_by=sort_used)
    else:  # keyword
        if not text:
            print("keyword mode requires --query (confirmed exact keyword query)", file=sys.stderr)
            sys.exit(1)
        sort_used = args.sort or "SubmittedDate"
        display_query = text
        papers = search_by_query(text, max_results=max_results, sort_by=sort_used)

    out_dir = args.out_dir.resolve()
    meta_dir = out_dir / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "mode": mode,
        "query": display_query,
        "max_results": max_results,
        "sort": sort_used,
        "count": len(papers),
        "papers": papers,
    }

    json_path = meta_dir / "results.json"
    md_path = meta_dir / "results.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(papers, md_path, display_query, mode)

    print(
        json.dumps(
            {
                "ok": True,
                "mode": mode,
                "count": len(papers),
                "json": str(json_path),
                "md": str(md_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
