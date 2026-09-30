#!/usr/bin/env python3
"""Extract motivation/problem and method/solution sections from paper digestions."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path


MOTIVATION_TERMS = (
    "motivation",
    "problem",
    "limitation",
    "shortcoming",
    "research gap",
    "研究动机",
    "研究问题",
    "问题或不足",
    "问题与不足",
    "过往研究中的问题",
    "不足有哪些",
)

METHOD_TERMS = (
    "method",
    "methodology",
    "approach",
    "solution",
    "contribution",
    "解决方法",
    "研究方法",
    "本文方法",
    "针对各问题",
    "workflow",
)

METHOD_DISAMBIGUATORS = (
    "method",
    "methodology",
    "approach",
    "solution",
    "contribution",
    "解决方法",
    "研究方法",
    "本文方法",
    "针对各问题",
    "workflow",
)

TITLE_PATTERNS = (
    re.compile(r"^#\s*Paper Digestion:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^-\s*Title:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE),
)

PAPER_ID_PATTERNS = (
    re.compile(r"^-\s*(?:Paper ID|paper_id):\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^-\s*(?:DOI):\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^-\s*(?:arXiv(?: ID)?):\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE),
)


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def parse_sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown by headings; preserve pre-heading content as an empty-title section."""
    heading = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
    matches = list(heading.finditer(text))
    if not matches:
        return [("", text.strip())]

    sections: list[tuple[str, str]] = []
    prefix = text[: matches[0].start()].strip()
    if prefix:
        sections.append(("", prefix))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        sections.append((match.group(2).strip(), body))
    return sections


def score_heading(heading: str, terms: tuple[str, ...]) -> int:
    normalized = normalize(heading)
    return sum(1 for term in terms if normalize(term) in normalized)


def collect_matching_sections(
    sections: list[tuple[str, str]],
    terms: tuple[str, ...],
    excluded_terms: tuple[str, ...] = (),
) -> tuple[str, list[str]]:
    selected: list[str] = []
    headings: list[str] = []
    for heading, body in sections:
        normalized_heading = normalize(heading)
        is_document_title = normalized_heading.startswith("paper digestion:")
        is_excluded = bool(excluded_terms and score_heading(heading, excluded_terms))
        if heading and not is_document_title and not is_excluded and score_heading(heading, terms):
            content = f"### {heading}\n\n{body}".strip()
            if content not in selected:
                selected.append(content)
                headings.append(heading)
    return "\n\n".join(selected), headings


def fallback_paragraphs(text: str, terms: tuple[str, ...], limit: int = 4) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    hits = [part for part in paragraphs if any(normalize(term) in normalize(part) for term in terms)]
    return "\n\n".join(hits[:limit])


def first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def extract_paper_id(text: str) -> str | None:
    explicit = PAPER_ID_PATTERNS[0].search(text)
    if explicit:
        return explicit.group(1).strip()
    doi = PAPER_ID_PATTERNS[1].search(text)
    if doi:
        value = doi.group(1).strip()
        return value if value.casefold().startswith("doi:") else f"doi:{value}"
    arxiv = PAPER_ID_PATTERNS[2].search(text)
    if arxiv:
        value = arxiv.group(1).strip()
        return value if value.casefold().startswith("arxiv:") else f"arxiv:{value}"
    return None


def extract(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8-sig")
    sections = parse_sections(text)
    motivation, motivation_headings = collect_matching_sections(
        sections, MOTIVATION_TERMS, excluded_terms=METHOD_DISAMBIGUATORS
    )
    method, method_headings = collect_matching_sections(sections, METHOD_TERMS)

    used_fallback = {"motivation": False, "method": False}
    if not motivation:
        motivation = fallback_paragraphs(text, MOTIVATION_TERMS)
        used_fallback["motivation"] = bool(motivation)
    if not method:
        method = fallback_paragraphs(text, METHOD_TERMS)
        used_fallback["method"] = bool(method)

    title = first_match(TITLE_PATTERNS, text) or path.stem.removeprefix("digestion-")
    paper_id = extract_paper_id(text)
    return {
        "paper_id": paper_id,
        "title": title,
        "source_file": str(path.resolve()),
        "motivation": motivation,
        "method": method,
        "diagnostics": {
            "motivation_headings": motivation_headings,
            "method_headings": method_headings,
            "fallback_used": used_fallback,
            "missing": [
                name
                for name, value in (("motivation", motivation), ("method", method))
                if not value
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract motivation/problem and method/solution content from Markdown digestions."
    )
    parser.add_argument("--digestions-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Destination JSONL file")
    parser.add_argument("--index", type=Path, help="Optional digestions/index.json for paper_id mapping")
    return parser.parse_args()


def load_index(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    mapping: dict[str, str] = {}
    for item in data.get("papers", []):
        filename = item.get("digestion_file")
        paper_id = item.get("paper_id")
        if filename and paper_id:
            mapping[Path(filename).name] = paper_id
    return mapping


def main() -> int:
    args = parse_args()
    if not args.digestions_dir.is_dir():
        print(f"Digestions directory does not exist: {args.digestions_dir}", file=sys.stderr)
        return 2

    files = sorted(args.digestions_dir.glob("*.md"))
    if not files:
        print(f"No Markdown digestions found in: {args.digestions_dir}", file=sys.stderr)
        return 2

    index = load_index(args.index)
    records = []
    for path in files:
        record = extract(path)
        if path.name in index:
            record["paper_id"] = index[path.name]
        records.append(record)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    missing = sum(bool(record["diagnostics"]["missing"]) for record in records)  # type: ignore[index]
    print(json.dumps({"files": len(records), "records_with_missing_sections": missing, "output": str(args.output)}, ensure_ascii=False))
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
