---
name: google_scholar-gs_advanced_search
description: Perform advanced Google Scholar searches by translating natural-language criteria into Scholar URL parameters such as author, publication, date range, exact phrase, exclusions, and title-only scope.
argument-hint: "[describe search criteria]"
---

# Google Scholar Advanced Search

Use after `google_scholar/SKILL.md` has selected the browser automation backend. Follow the main skill's environment and reCAPTCHA rules.

## Arguments

`$ARGUMENTS` is a natural-language search request, such as:
- `Einstein relativity after 2020`
- `reviews about CRISPR in Nature`
- `exact phrase "machine learning" in title only`

## URL Parameter Mapping

| Criteria | Parameter | Example |
|----------|-----------|---------|
| Keywords | `q` | `q=gastric+cancer` |
| Author | `as_sauthors` | `as_sauthors=Albert+Einstein` |
| Journal/source | `as_publication` | `as_publication=Nature` |
| Start year | `as_ylo` | `as_ylo=2020` |
| End year | `as_yhi` | `as_yhi=2025` |
| Exact phrase | `as_epq` | `as_epq=machine+learning` |
| Any of these words | `as_oq` | `as_oq=immunotherapy+checkpoint` |
| Exclude words | `as_eq` | `as_eq=review` |
| Search scope | `as_occt` | `as_occt=title` or `as_occt=any` |
| Results per page | `num` | `num=10` |
| Language | `hl` | `hl=en` |

Always include `hl=en` and prefer `num=10`.

## Steps

1. Translate `$ARGUMENTS` into Scholar URL parameters.
2. Navigate to `https://scholar.google.com/scholar?{CONSTRUCTED_PARAMS}`.
3. Read and execute `google_scholar/scripts/extract_results.js`.
4. If the script returns an `error`, handle it according to the main skill.
5. Report the constructed parameters and structured results.

## Output Format

```text
Advanced search on Google Scholar:
Query parameters: {params}
{total}

1. {title}
   Authors: {authors} | {journalYear}
   Cited by: {citedBy} | Full text: {fullTextUrl}
   Data-CID: {dataCid}
```

Google Scholar does not support publication type or impact factor filters directly; use keywords and citation counts when needed.
