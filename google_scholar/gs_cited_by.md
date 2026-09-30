---
name: google_scholar-gs_cited_by
description: Find Google Scholar papers that cite a target paper by data-cid, or resolve a paper title to data-cid before opening the cited-by results.
argument-hint: "[data-cid or paper title]"
---

# Google Scholar Cited By

Use after `google_scholar/SKILL.md` has selected the browser automation backend. Follow the main skill's environment and reCAPTCHA rules.

## Arguments

`$ARGUMENTS` can be:
- A Google Scholar `data-cid`.
- A paper title or description that must first be resolved through `gs_search.md`.

## Steps

1. Resolve the target `data-cid`.
   - If `$ARGUMENTS` is a single alphanumeric token, use it directly.
   - Otherwise, run `gs_search.md`, compare titles, and select the best matching `dataCid`.
2. Navigate to:
   - `https://scholar.google.com/scholar?cites={DATA_CID}&hl=en&num=10`
3. Read and execute `google_scholar/scripts/extract_results.js`.
4. If the script returns an `error`, handle it according to the main skill.
5. Report citing papers with their own `dataCid` values.

## Output Format

```text
Papers citing {targetTitleOrCid}:
{total}

1. {title}
   Authors: {authors} | {journalYear}
   Cited by: {citedBy}
   Data-CID: {dataCid}
```

## Follow-up Routing

- More citing papers: read `gs_navigate_pages.md`.
- Export citing papers: read `gs_export.md`.
- Recursive citation tracking: read this file again with a citing paper's `dataCid`.
