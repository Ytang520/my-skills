---
name: google_scholar-gs_search
description: Search Google Scholar for academic papers by keyword and return structured results with title, authors, venue/year, citation count, data-cid, and full-text links.
argument-hint: "[search keywords]"
---

# Google Scholar Basic Search

Use after `google_scholar/SKILL.md` has selected the browser automation backend. Follow the main skill's environment and reCAPTCHA rules.

## Arguments

`$ARGUMENTS` contains the search keywords.

## Steps

1. Build the search URL:
   - `https://scholar.google.com/scholar?q={URL_ENCODED_KEYWORDS}&hl=en&num=10`
2. Navigate to the URL:
   - Chrome DevTools MCP: `navigate_page`
   - Playwright fallback: `page.goto(url, { waitUntil: 'domcontentloaded' })`
3. Read `scripts/extract_results.js`.
4. Execute the script:
   - Chrome DevTools MCP: pass the script body to `evaluate_script`.
   - Playwright fallback: `const fn = eval(script); const result = await page.evaluate(fn);`
5. If the result has an `error` field, handle it according to the main skill.
6. If no other special requests, report results as a numbered list and always include `dataCid`.

## Output Format

```text
Searched Google Scholar for "$ARGUMENTS": {total}

1. {title}
   Authors: {authors} | {journalYear}
   Cited by: {citedBy} | Full text: {fullTextUrl}
   Data-CID: {dataCid}
```

## Follow-up Routing

- More results: read `gs_navigate_pages.md`.
- Cited-by tracking: read `gs_cited_by.md`.
- Full-text links: read `gs_fulltext.md`.
- Zotero export: read `gs_export.md`.
