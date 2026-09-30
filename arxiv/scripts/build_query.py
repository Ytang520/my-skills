#!/usr/bin/env python3
"""
Build arXiv query variants from keyword groups for user confirmation.
Does not perform any network requests.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GROUPS_FILE = SKILL_ROOT / "keyword_groups.json"

VARIANT_NAMES = ("field_ti_abs", "field_ti", "field_abs", "bare", "all_prefix")


def load_keyword_groups(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"keyword groups file must be a JSON object: {path}")
    return {str(k): [str(t) for t in v] for k, v in data.items()}


def _normalize_for_match(term: str) -> str:
    t = term.strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        t = t[1:-1]
    return t.casefold()


def _term_tokens(term: str) -> tuple[str, ...]:
    text = _normalize_for_match(term)
    return tuple(tok for tok in re.split(r"[\s\-]+", text) if tok)


def _is_contiguous_subsequence(short: tuple[str, ...], long: tuple[str, ...]) -> bool:
    if not short or len(short) >= len(long):
        return False
    n = len(short)
    for i in range(len(long) - n + 1):
        if long[i : i + n] == short:
            return True
    return False


def prune_phrase_subsumed(terms: list[str]) -> list[str]:
    """
    Within one OR group: drop a term if a strictly shorter sibling's tokens
    already appear as a contiguous subsequence (e.g. keep "language model",
    drop "large language model"). Never invents broader terms.
    """
    tokenized = [(t, _term_tokens(t)) for t in terms]
    drop: set[int] = set()
    for i, (_, toki) in enumerate(tokenized):
        if not toki:
            continue
        for j, (_, tokj) in enumerate(tokenized):
            if i == j or not tokj:
                continue
            if _is_contiguous_subsequence(tokj, toki):
                drop.add(i)
                break
    return [t for idx, (t, _) in enumerate(tokenized) if idx not in drop]


def expand_term(term: str, groups: dict[str, list[str]]) -> list[str]:
    """If term hits any synonym group, return the full group; else [term]."""
    needle = _normalize_for_match(term)
    for members in groups.values():
        for member in members:
            if _normalize_for_match(member) == needle:
                return list(members)
    return [term.strip()]


def expand_groups(
    raw_groups: list[list[str]],
    synonym_groups: dict[str, list[str]],
    expand: bool,
) -> list[list[str]]:
    expanded: list[list[str]] = []
    for group in raw_groups:
        terms: list[str] = []
        seen: set[str] = set()
        for term in group:
            candidates = expand_term(term, synonym_groups) if expand else [term.strip()]
            for t in candidates:
                key = _normalize_for_match(t)
                if key in seen:
                    continue
                seen.add(key)
                terms.append(t)
        terms = prune_phrase_subsumed(terms)
        if terms:
            expanded.append(terms)
    return expanded


def format_term_bare(term: str) -> str:
    t = term.strip()
    if not t:
        return t
    if (t[0] == '"' and t[-1] == '"') or " " not in t:
        return t
    return f'"{t}"'


def format_term_all(term: str) -> str:
    bare = format_term_bare(term)
    return f"all:{bare}"


def format_term_ti_abs(term: str) -> str:
    bare = format_term_bare(term)
    return f"(ti:{bare} OR abs:{bare})"


def format_term_field(term: str, field: str) -> str:
    bare = format_term_bare(term)
    return f"{field}:{bare}"


def join_group(terms: list[str], formatter) -> str:
    parts = [formatter(t) for t in terms]
    if len(parts) == 1:
        return parts[0]
    return f"({' OR '.join(parts)})"


def build_query(
    groups: list[list[str]],
    relation: str,
    formatter,
) -> str:
    if not groups:
        return ""
    pieces = [join_group(g, formatter) for g in groups]
    op = f" {relation.strip().upper()} "
    return op.join(pieces)


def resolve_display_max_results(value: str | int) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip().casefold()
    if text in {"all", "全部"}:
        return 1000
    return int(text)


def build_variants(
    groups: list[list[str]],
    relation: str = "AND",
    field: str = "ti_abs",
) -> list[dict[str, str]]:
    relation = relation.strip().upper()
    if relation not in {"AND", "OR"}:
        raise ValueError("relation must be AND or OR")

    field = field.strip().casefold()
    allowed = {"ti_abs", "ti", "abs", "all", "bare"}
    if field not in allowed:
        raise ValueError(f"field must be one of {sorted(allowed)}")

    variants: list[dict[str, str]] = []

    # Always include the user-selected / default field-aware variant first.
    if field == "ti_abs":
        variants.append(
            {
                "name": "field_ti_abs",
                "query": build_query(groups, relation, format_term_ti_abs),
                "note": "Default: match in title OR abstract for each term",
            }
        )
    elif field in {"ti", "abs"}:
        variants.append(
            {
                "name": f"field_{field}",
                "query": build_query(
                    groups, relation, lambda t, f=field: format_term_field(t, f)
                ),
                "note": f"Match in {field} only",
            }
        )
    elif field == "all":
        variants.append(
            {
                "name": "all_prefix",
                "query": build_query(groups, relation, format_term_all),
                "note": "all: prefix on every term",
            }
        )
    else:  # bare
        variants.append(
            {
                "name": "bare",
                "query": build_query(groups, relation, format_term_bare),
                "note": "No field prefix (API default fields)",
            }
        )

    # Comparison variants (skip duplicates of the primary)
    primary = variants[0]["name"]
    catalog = [
        (
            "field_ti_abs",
            format_term_ti_abs,
            "Default: match in title OR abstract for each term",
        ),
        ("field_ti", lambda t: format_term_field(t, "ti"), "Match in title only"),
        ("field_abs", lambda t: format_term_field(t, "abs"), "Match in abstract only"),
        ("bare", format_term_bare, "No field prefix (API default fields)"),
        ("all_prefix", format_term_all, "all: prefix on every term"),
    ]
    for name, formatter, note in catalog:
        if name == primary:
            continue
        variants.append(
            {
                "name": name,
                "query": build_query(groups, relation, formatter),
                "note": note,
            }
        )
    return variants


def parse_group_arg(value: str) -> list[str]:
    """Parse one --group value: comma-separated terms."""
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p]


def format_human(
    variants: list[dict[str, str]],
    groups: list[list[str]],
    relation: str,
    max_results: int,
    retrieve: str,
    field: str,
) -> str:
    lines = [
        "Proposed query variants (confirm before search):",
        f"Groups ({relation}): " + " | ".join("(" + " OR ".join(g) + ")" for g in groups),
        f"Requested field: {field}",
    ]
    for i, v in enumerate(variants, start=1):
        lines.append(f"{i}. [{v['name']}] {v['query']}")
        if v.get("note"):
            lines.append(f"   ({v['note']})")
    lines.append(f"max_results: {max_results} | retrieve: {retrieve}")
    lines.append("Reply with the variant number/name to run, or request edits.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build arXiv query variants from keyword groups (no network)."
    )
    parser.add_argument(
        "--group",
        "-g",
        action="append",
        required=True,
        help="One keyword group (comma-separated synonyms). Repeat for multiple groups.",
    )
    parser.add_argument(
        "--relation",
        "-r",
        default="AND",
        choices=["AND", "OR", "and", "or"],
        help="Relation between groups (default: AND)",
    )
    parser.add_argument(
        "--groups-file",
        type=Path,
        default=DEFAULT_GROUPS_FILE,
        help="Path to keyword_groups.json",
    )
    parser.add_argument(
        "--no-expand",
        action="store_true",
        help="Do not expand terms via keyword_groups.json",
    )
    parser.add_argument(
        "--field",
        default="all",
        choices=["ti_abs", "ti", "abs", "all", "bare"],
        help="Primary field mode to recommend (default: all = all: prefix, which covers "
        "title + abstract + authors + comments in one shot; ti_abs builds (ti: OR abs:) pairs)",
    )
    parser.add_argument(
        "--max-results",
        default="5",
        help='Reported max_results for confirmation display (default: 5). Use "all" for 1000.',
    )
    parser.add_argument(
        "--retrieve",
        default="both",
        choices=["both", "metadata", "pdf"],
        help="Reported retrieve mode for confirmation display (default: both)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human text",
    )
    args = parser.parse_args(argv)

    if not args.groups_file.is_file():
        print(f"keyword groups file not found: {args.groups_file}", file=sys.stderr)
        sys.exit(1)

    synonym_groups = load_keyword_groups(args.groups_file)
    raw_groups = [parse_group_arg(g) for g in args.group]
    raw_groups = [g for g in raw_groups if g]
    if not raw_groups:
        print("At least one non-empty --group is required", file=sys.stderr)
        sys.exit(1)

    groups = expand_groups(raw_groups, synonym_groups, expand=not args.no_expand)
    relation = args.relation.upper()
    field = args.field.casefold()
    max_results = resolve_display_max_results(args.max_results)
    variants = build_variants(groups, relation=relation, field=field)

    recommended = variants[0]["name"] if variants else "field_ti_abs"
    payload = {
        "groups": groups,
        "relation": relation,
        "field": field,
        "max_results": max_results,
        "retrieve": args.retrieve,
        "variants": variants,
        "recommended": recommended,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            format_human(
                variants,
                groups,
                relation,
                max_results,
                args.retrieve,
                field,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
