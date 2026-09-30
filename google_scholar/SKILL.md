---
name: google_scholar
description: Use for any Google Scholar operation, including searching papers, advanced search, cited-by tracking, result pagination, full-text link discovery, BibTeX/Zotero export, and diagnosing Google Scholar workflow errors.
argument-hint: "[describe the Google Scholar task]"
---

# Google Scholar

Use this skill before any exact Google Scholar operation. This file is only the coordinating layer for environment readiness, browser automation selection, reCAPTCHA handling, and routing. Do not perform a search, export, pagination, full-text lookup, cited-by lookup, or checkout diagnosis from this file alone.

## What This Skill Requires

Google Scholar workflows are browser-based DOM extraction tasks. They require:
- Chrome DevTools MCP tools such as `navigate_page`, `evaluate_script`, and optionally `new_page`, or an approved Playwright fallback.
- A local Chrome-family browser engine: Chrome, Chromium, Edge, or Playwright Chromium.
- Google Scholar reachable in the controlled browser without an unresolved CAPTCHA or reCAPTCHA block.

Do not use WebFetch, curl, requests, or non-browser scraping for Google Scholar pages.

## Step 1: Select Browser Automation

Prefer Chrome DevTools MCP when a server named like `chrome-devtools`, `chrome-dev-tools`, or equivalent tools exposing `navigate_page` and `evaluate_script` is available.

If Chrome DevTools MCP is unavailable, ask the user before using Playwright fallback unless they already approved it in this chat/session. With Playwright fallback:
- Use `page.goto(url)` where a child skill says `navigate_page`.
- Use `page.evaluate(scriptOrFunction)` where a child skill says `evaluate_script`.
- Use `browser.newPage()` plus `page.goto(url)` where a child skill says `new_page`.
- Keep the child skill's output schema unchanged.

If neither Chrome DevTools MCP nor an approved Playwright fallback is available, stop and report that no supported browser automation environment is available.

## Step 2: Check Local Browser

Before navigating Google Scholar, check for a local browser engine:

1. If `chrome-path.txt` exists in this skill folder, read it. The format is documented in `chrome-path.example.txt`. `chrome-path.txt` is a local file; do not commit it.
   - Treat the first non-empty, non-comment line as the preferred executable path.
   - If the path exists and can be launched, use it.
   - If the file is absent, empty, or the path is invalid, ignore it and scan common locations.
2. Scan common browser locations:
   - Windows:
     - `%ProgramFiles%\Google\Chrome\Application\chrome.exe`
     - `%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe`
     - `%LocalAppData%\Google\Chrome\Application\chrome.exe`
     - `%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`
   - macOS:
     - `/Applications/Google Chrome.app`
     - `/Applications/Chromium.app`
     - `/Applications/Microsoft Edge.app`
   - Linux commands:
     - `google-chrome`
     - `chromium`
     - `chromium-browser`
     - `microsoft-edge`

When a valid local browser path is found by scanning, write that absolute path to `chrome-path.txt` in this skill folder for later checks. Do not commit that file.

If no Chrome-family browser is found, stop and ask the user to choose:
- 安装 Google Chrome / Chromium / Edge 后再继续
- 允许我尝试使用 Playwright 安装或调用 Chromium 继续处理

Do not silently install browsers or switch methods.

## Step 3: Check Google Scholar Reachability

Use the selected browser path, then open `https://scholar.google.com/`.

Recommended Playwright fallback smoke check:

```bash
npx -y -p playwright node -e "const { chromium } = require('playwright'); const executablePath = process.env.CHROME_EXECUTABLE_PATH || undefined; (async () => { const browser = await chromium.launch(executablePath ? { executablePath, headless: true } : { channel: 'chrome', headless: true }); const page = await browser.newPage(); await page.goto('https://scholar.google.com/', { waitUntil: 'domcontentloaded', timeout: 30000 }); const text = await page.locator('body').innerText({ timeout: 10000 }); console.log(text.includes('Google Scholar') || text.includes('unusual traffic') ? 'scholar-reached' : 'scholar-unknown'); await browser.close(); })().catch(err => { console.error(err.message); process.exit(1); });"
```

Interpretation:
- Normal Google Scholar page: continue.
- CAPTCHA, reCAPTCHA, `#gs_captcha_ccl`, or "unusual traffic": follow the reCAPTCHA rule below.
- Timeout, DNS, network, or access error: stop and report the connectivity failure.

When all previous checks pass, say: "google_scholar 环境检查已通过，本会话后续 Google Scholar 操作无需重复检查，除非 MCP 或浏览器环境变化。"


## (Optional) Step 4: Choose the Matching Operation File

After the environment is ready, you MUST choose and read at least one matching operation file from this same folder before taking any Google Scholar action. The operation files are the real task instructions; this main file only prepares and routes.

Do not continue with the user's Google Scholar request until the matching file has been read. If multiple files could apply, pick the most specific one. If the user asks for multiple independent Google Scholar actions, read and execute the matching files one at a time in the order needed.

Use this routing table:

| User intent | Required file to read next |
|-------------|----------------------------|
| Keyword search, find papers, search Scholar, list papers | `gs_search.md` |
| Filtered search by author, journal/source, year range, exact phrase, exclusions, title-only search | `gs_advanced_search.md` |
| "Cited by", citation tracking, papers that cite a result, citation chain | `gs_cited_by.md` |
| Next page, previous page, page N, more results | `gs_navigate_pages.md` |
| Full text, PDF link, publisher link, DOI link, open/read/download paper | `gs_fulltext.md` |
| Export to Zotero, BibTeX, citation export, save paper(s) | `gs_export.md` |
| Error diagnosis, failed script, unexpected result, broken Scholar workflow, create a new diagnostic run script | `gs_checkout.md` |

If the user provides only a `data-cid` without context:
- Read `gs_export.md` when they mention export, Zotero, BibTeX, save, or citation data.
- Read `gs_cited_by.md` when they mention citations or cited-by.
- Read `gs_fulltext.md` when they mention full text, PDF, DOI, or reading the paper.
- Ask a short clarification if the intended operation is still unclear.

After reading the required file, follow that file's steps exactly while continuing to apply this main file's browser backend and reCAPTCHA rules.

## NOTES:

### reCAPTCHA Rule

For every Google Scholar operation, if the page shows CAPTCHA/reCAPTCHA, `#gs_captcha_ccl`, "unusual traffic", or any script returns `{ error: "captcha" }`:

1. Stop all navigation, extraction, fetch, BibTeX export, and Zotero push steps.
2. Tell the user exactly: `Google Scholar 需要人机认证才能查看该内容。请在浏览器中手动登录后告诉我继续。`
3. Wait for the user to confirm completion.
4. Retry the current extraction/navigation once.
5. If the block persists, report that Google Scholar still requires verification and stop.

Never automate CAPTCHA solving, use third-party solving services, forge cookies, or bypass Google Scholar access controls.