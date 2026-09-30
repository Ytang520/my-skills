# Artifact schemas

Use UTF-8 for every text artifact. Resolve all paths under the user-selected output directory (default: current working directory).

## Contents

1. Collection artifacts
2. Filter artifacts
3. Deep-reading artifacts
4. Final artifacts
5. Coverage checks

## 1. Collection artifacts

### `citation_candidates.json`

Create only for citation-based reviews.

```json
{
  "method": "citation_based",
  "base_papers": ["stable-paper-id"],
  "max_recursion_depth": 3,
  "generated_at": "ISO-8601 timestamp",
  "papers": [
    {
      "paper_id": "doi:... | arxiv:... | title:<normalized-title>",
      "title": "Paper title",
      "authors_raw": "Authors as exposed by Google Scholar or null",
      "citation_depth": 1,
      "cites_frontier_ids": ["stable-paper-id"],
      "source_urls": ["https://..."],
      "provenance": ["google_scholar"]
    }
  ]
}
```

### `papers_metadata.json`

Use for both collection methods.

```json
{
  "method": "arxiv_based | citation_based",
  "search_record": {
    "keyword_groups": [{"name": "fairness", "terms": ["fairness"]}],
    "relation": "<A> AND/OR/NOT <B> ...",
    "axis_queries": [
      {
        "axis": "shift-fairness",
        "groups": ["fairness", "distribution shift"],
        "query": "(all:fairness) AND (all:\"distribution shift\" OR all:\"covariate shift\")"
      }
    ],
    "queries": ["(all:fairness) AND (all:\"distribution shift\" OR all:\"covariate shift\")"],
    "date_boundaries": {"from": null, "to": null},
    "base_papers": [],
    "max_recursion_depth": "3 for citation_based when unspecified | user-specified integer | null for arxiv_based",
    "searched_at": "ISO-8601 timestamp"
  },
  "papers": [
    {
      "paper_id": "doi:... | arxiv:... | title:<normalized-title>",
      "title": "Paper title",
      "abstract": "Abstract text or null",
      "author_names": "First Author, et.al | null",
      "date": "YYYY-MM-DD | YYYY | null",
      "doi": "canonical DOI without https://doi.org/ | null",
      "arxiv_id": "arXiv id or null",
      "paper_url": "primary URL or null",
      "pdf_url": "PDF URL or null",
      "citation_depth": "integer >= 0 for citation_based | null for arxiv_based",
      "provenance": ["arxiv", "google_scholar", "publisher", "web_search"],
      "metadata_status": "complete | partial | unresolved"
    }
  ],
  "unresolved": [
    {"paper_id": "...", "missing_fields": ["abstract"], "reason": "..."}
  ]
}
```

Canonicalize titles for deduplication by Unicode normalization, case folding, whitespace collapse, and removal of punctuation that does not alter words. Never overwrite a higher-quality primary-source value with a search snippet.

For `citation_based`, set `citation_depth=0` for each base paper and a positive integer for recursively discovered citing papers; default `max_recursion_depth` to 3 when the user did not specify a depth. For `arxiv_based`, set `citation_depth=null` and `max_recursion_depth=null`, and record the reviewed keyword groups, between-group relation, and the combined **complete** `all_prefix` queries actually searched (every `all:` term; no ellipsis; not a list of quoted phrases).

## 2. Filter artifacts

Use the same envelope for `initial_filter_results.json` and `final_filter_results.json`.

```json
{
  "stage": "initial_filter | final_filter",
  "criteria": {
    "include": ["verbatim user-selected criterion decidable from title and abstract"],
    "exclude": ["verbatim user-selected criterion decidable from title and abstract"]
  },
  "input_paper_ids": ["..."],
  "results": [
    {
      "paper_id": "...",
      "title": "...",
      "decision": "pass | exclude | uncertain | unresolved",
      "criterion_results": [
        {"criterion": "...", "result": "met | not_met | unclear", "evidence": "..."}
      ],
      "reason": "Concise decision rationale",
      "input_used": "title_abstract | title_abstract_first_two_pages",
      "reviewer_task_id": "stable subagent task identifier"
    }
  ],
  "summary": {"pass": 0, "exclude": 0, "uncertain": 0, "unresolved": 0}
}
```

## 3. Deep-reading artifacts

Store one Markdown file per selected paper under `digestions/`, following `$paper-reading`'s Chinese format. Preserve a mapping from filename to `paper_id` in `digestions/index.json`:

```json
{
  "papers": [
    {"paper_id": "...", "title": "...", "digestion_file": "digestion-....md", "status": "complete | failed"}
  ]
}
```

## 4. Final artifacts

- `extracted_digestions.jsonl`: one JSON object per line with `paper_id`, `title`, `source_file`, `motivation`, `method`, and extraction diagnostics.
- `intermediate_reports/report_batch_<NNN>.md`: a synthesis of no more than 10 extracted records, covering problems, methods, relationships, and uncertainties.
- `literature_review_report.md`: an evidence-grounded synthesis containing `问题解决整体思路`, `解决方法概览`, and `不同方法之间的发展脉络`.
- `literature_review_mindmap.md` (optional): Mermaid flowchart or user-selected format; every deep-read paper appears exactly once as a paper node.
- `suggested_papers.csv`: UTF-8 CSV with exactly `paper_name,date,doi,reasons`; quote/escape fields using a CSV library.

## 5. Coverage checks

Before closing a stage, verify:

- collection: paper IDs are unique and required keys exist;
- initial filter: result IDs equal collected IDs exactly;
- final filter: result IDs equal the user-selected candidate set exactly; when the user does not specify a subset, that set is initial `pass + uncertain` IDs;
- deep reading: complete digestion IDs equal the selected reading set, with failures reported separately;
- report extraction: every complete digestion has one JSONL record;
- mindmap: node paper IDs equal complete digestion IDs exactly;
- suggested CSV: row count equals `min(n, available eligible papers)` and every row maps to metadata.
