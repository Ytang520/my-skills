---
name: gs-navigate-pages
description: Navigate Google Scholar search result pages. Use when user wants to see more results or go to a specific page.
argument-hint: "[next|previous|page N]"
user-invokable: false
---

# Google Scholar Navigate Pages

## Required GS Check

Before running this skill, use `gs-check` first. If this exact chat/session already completed `gs-check` successfully and the MCP/browser environment has not changed, do not repeat the check.

Prefer Chrome DevTools MCP for browser automation. If `gs-check` reports that Chrome DevTools MCP is unavailable but the user chose or approved the Playwright fallback, run the same workflow through Playwright instead: use `page.goto()` for `navigate_page`, `page.evaluate()` for `evaluate_script`, and `browser.newPage()` plus `page.goto()` for `new_page`. Use the browser executable path saved in `gs-check/chrome-path.txt` when that file exists and the path is valid, and keep this skill's output schema unchanged.

If neither Chrome DevTools MCP nor the approved Playwright fallback is available, stop and report the missing browser automation environment instead of trying WebFetch, curl, or non-browser scraping.

If Google Scholar shows CAPTCHA/reCAPTCHA, `#gs_captcha_ccl`, "unusual traffic", or any script returns `{ error: "captcha" }`, stop immediately and ask the user to complete the verification manually in the MCP-controlled or Playwright-controlled Chrome window. Continue only after the user confirms completion; never automate or bypass CAPTCHA.

Navigate search result pages. Requires context from a previous gs-search or gs-advanced-search call.

## Arguments

$ARGUMENTS can be:
- `next` — go to next page
- `previous` — go to previous page
- `page N` — go to page N

## Prerequisites

This skill requires context from a previous search:
- `currentUrl`: the current Google Scholar search URL
- `page`: current page number (1-based)

## Steps

### 1. Calculate new URL

Google Scholar uses `start` parameter for pagination (0-indexed, increments of 10):
- Page 1: `start=0` (or omitted)
- Page 2: `start=10`
- Page 3: `start=20`

Based on $ARGUMENTS:
- `next`: newStart = currentStart + 10
- `previous`: newStart = max(0, currentStart - 10)
- `page N`: newStart = (N - 1) * 10

Modify the `start` parameter in the current search URL. If `start` doesn't exist in the URL, append `&start={newStart}`.

### 2. Navigate

Use `mcp__chrome-devtools__navigate_page` with the updated URL.

### 3. Extract results (evaluate_script)

Same extraction script as gs-search step 2:

```javascript
async () => {
  for (let i = 0; i < 20; i++) {
    if (document.querySelector('#gs_res_ccl') || document.querySelector('#gs_captcha_ccl')) break;
    await new Promise(r => setTimeout(r, 500));
  }

  if (document.querySelector('#gs_captcha_ccl') || document.body.innerText.includes('unusual traffic')) {
    return { error: 'captcha', message: 'Google Scholar requires CAPTCHA verification. Please complete it in your browser, then tell me to continue.' };
  }

  const items = document.querySelectorAll('#gs_res_ccl .gs_r.gs_or.gs_scl');
  const results = Array.from(items).map((item, i) => {
    const titleEl = item.querySelector('.gs_rt a');
    const meta = item.querySelector('.gs_a')?.textContent || '';
    const parts = meta.split(' - ');
    const authors = parts[0]?.trim() || '';
    const journalYear = parts[1]?.trim() || '';
    const citedByEl = item.querySelector('.gs_fl a[href*="cites"]');

    return {
      n: NEW_START + i + 1,
      title: titleEl?.textContent?.trim() || item.querySelector('.gs_rt')?.textContent?.trim() || '',
      href: titleEl?.href || '',
      authors,
      journalYear,
      citedBy: citedByEl?.textContent?.match(/\d+/)?.[0] || '0',
      citedByUrl: citedByEl?.href || '',
      dataCid: item.getAttribute('data-cid') || '',
      fullTextUrl: (item.querySelector('.gs_ggs a') || item.querySelector('.gs_or_ggsm a'))?.href || '',
      snippet: item.querySelector('.gs_rs')?.textContent?.trim()?.substring(0, 200) || ''
    };
  });

  const totalText = document.querySelector('#gs_ab_md')?.textContent?.trim() || '';
  const hasNext = !!document.querySelector('#gs_n a.gs_ico_nav_next, #gs_nm a:last-child');
  const currentUrl = window.location.href;
  return { total: totalText, page: NEW_PAGE, resultCount: results.length, hasNext, currentUrl, results };
}
```

Replace `NEW_START` and `NEW_PAGE` with the computed values.

### 4. Report

```
Page {page} for "{query}" ({total}):

1. {title}
   Authors: {authors} | {journalYear}
   Cited by: {citedBy}
   Data-CID: {dataCid}

2. ...

{hasNext ? "More results available — ask me for the next page." : "No more results."}
```

## Notes

- This skill uses 2 tool calls: `navigate_page` + `evaluate_script`
- Google Scholar shows 10 results per page by default
- `start` parameter controls pagination offset
