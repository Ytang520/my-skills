---
name: google_scholar-gs_navigate_pages
description: Navigate Google Scholar result pages using the start parameter for next, previous, or a specific page number.
argument-hint: "[next|previous|page N]"
user-invokable: false
---

# Google Scholar Navigate Pages

Use after `google_scholar/SKILL.md` has selected the browser automation backend. Follow the main skill's environment and reCAPTCHA rules.

## Prerequisites

Requires context from a previous search-like operation:
- `currentUrl`
- current page number or current `start` offset

## Steps

1. Calculate the new `start` offset:
   - `next`: current `start + 10`
   - `previous`: `max(0, current start - 10)`
   - `page N`: `(N - 1) * 10`
2. Update the current Google Scholar URL's `start` parameter.
3. Navigate to the updated URL.
4. Before executing `extract_results.js`, set page metadata when supported:
   - Chrome DevTools MCP: run `globalThis.__GS_EXTRACT_OPTIONS__ = { start: NEW_START, page: NEW_PAGE }` in the same page context, then run the extraction script.
   - Playwright fallback: `await page.evaluate(({ start, page }) => { globalThis.__GS_EXTRACT_OPTIONS__ = { start, page }; }, { start, page });`
5. Read and execute `google_scholar/scripts/extract_results.js`.
6. If the script returns an `error`, handle it according to the main skill.

## Output Format

```text
Page {page} for "{query}" ({total}):

1. {title}
   Authors: {authors} | {journalYear}
   Cited by: {citedBy}
   Data-CID: {dataCid}

{hasNextMessage}
```
