---
name: gs-check
description: Use when preparing to run Google Scholar gs-* skills or when Chrome DevTools MCP, Chrome/Chromium, Playwright, Google Scholar, CAPTCHA, or reCAPTCHA readiness is uncertain.
argument-hint: "[optional reason]"
---

# Google Scholar Environment Check

Run this before any other `gs-*` skill. If this exact chat/session already completed `gs-check` successfully and the MCP/browser environment has not changed, do not repeat it.

## What the GS Skills Require

The other Google Scholar skills are DOM-scraping workflows. They require:
- Chrome DevTools MCP tools such as `navigate_page`, `evaluate_script`, and optionally `new_page`
- A local Chrome-family browser engine: Chrome, Chromium, Edge, or Playwright Chromium
- Google Scholar reachable from Playwright without immediate block/CAPTCHA

## Step 1: Check Chrome DevTools MCP

Check the currently available MCP tools for a Chrome DevTools server named like `chrome-devtools`, `chrome-dev-tools`, or equivalent tools exposing `navigate_page` and `evaluate_script`.

If Chrome DevTools MCP is already available, continue to Step 2.

If it is not available:

1. Add Chrome DevTools MCP to Claude Code or OpenCode, matching the MCP client currently being used. Do not use Cursor `.cursor/mcp.json` for this skill.

   Claude Code CLI example:
   ```bash
   claude mcp add --transport stdio --scope user chrome-devtools -- npx -y chrome-devtools-mcp@latest
   ```

   If the command fails on Windows because `npx` is not resolved directly:
   ```bash
   claude mcp add --transport stdio --scope user chrome-devtools -- cmd /c npx -y chrome-devtools-mcp@latest
   ```

   OpenCode config example for `opencode.json` or `.opencode/opencode.json`:
   ```json
   {
     "$schema": "https://opencode.ai/config.json",
     "mcp": {
       "chrome-devtools": {
         "type": "local",
         "command": ["npx", "-y", "chrome-devtools-mcp@latest"],
         "enabled": true
       }
     }
   }
   ```
2. Stop immediately.
3. Tell the user: "已加入 Chrome DevTools MCP 配置。请重启当前 Claude Code/OpenCode 会话或刷新 MCP 后再继续 Google Scholar 操作。"
4. Do not continue to any Google Scholar task in the same run, because newly added MCP tools are not available until the session reloads.

## Step 2: Check Local Chrome Kernel

Check for a local browser engine before using Google Scholar:

1. If `chrome-path.txt` exists in this `gs-check` skill folder, read it. The format is documented in `chrome-path.example.txt`. `chrome-path.txt` is a local file; do not commit it.
   - Treat the first non-empty, non-comment line as the preferred Chrome executable path.
   - If that path exists and can be launched, use it and continue to Step 3.
   - If the file is absent, empty, or the path is invalid, ignore it and scan common locations.
2. Scan common browser locations:

- Windows common paths:
  - `%ProgramFiles%\Google\Chrome\Application\chrome.exe`
  - `%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe`
  - `%LocalAppData%\Google\Chrome\Application\chrome.exe`
  - `%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`
- macOS common paths:
  - `/Applications/Google Chrome.app`
  - `/Applications/Chromium.app`
  - `/Applications/Microsoft Edge.app`
- Linux common commands:
  - `google-chrome`
  - `chromium`
  - `chromium-browser`
  - `microsoft-edge`

When a valid local browser path is found by scanning, write that absolute executable path to `chrome-path.txt` in this skill folder so later checks can test it first. Do not commit that file.

If no Chrome-family browser is found after checking `chrome-path.txt` and common locations, stop and ask the user to choose:

- (a) 安装 Google Chrome / Chromium / Edge 后再继续
- (b) 允许我尝试使用 Playwright 安装或调用 Chromium 继续处理

Do not silently install browsers or switch methods without the user's choice.

## Step 3: Check Playwright Can Reach Google Scholar

Use Playwright to open `https://scholar.google.com/` and verify the page is reachable. Prefer the executable path from `chrome-path.txt` when that file exists and the path is valid; otherwise prefer the local Chrome channel. Use Playwright Chromium only after the user chose option (b).

Recommended command pattern:

```bash
npx -y -p playwright node -e "const { chromium } = require('playwright'); const executablePath = process.env.CHROME_EXECUTABLE_PATH || undefined; (async () => { const browser = await chromium.launch(executablePath ? { executablePath, headless: true } : { channel: 'chrome', headless: true }); const page = await browser.newPage(); await page.goto('https://scholar.google.com/', { waitUntil: 'domcontentloaded', timeout: 30000 }); const text = await page.locator('body').innerText({ timeout: 10000 }); console.log(text.includes('Google Scholar') || text.includes('unusual traffic') ? 'scholar-reached' : 'scholar-unknown'); await browser.close(); })().catch(err => { console.error(err.message); process.exit(1); });"
```

If the Chrome channel is unavailable but Playwright Chromium is allowed, install or use Playwright's Chromium and rerun without `channel: 'chrome'`.

Interpretation:
- `scholar-reached` with normal page text: checks passed.
- CAPTCHA/reCAPTCHA/unusual traffic: stop and ask the user to complete verification manually in the MCP-controlled browser, then continue only after they confirm.
- Timeout, DNS, network, or access error: stop and report the connectivity failure. Do not run other `gs-*` skills.

## CAPTCHA and reCAPTCHA Rule

For any Google Scholar skill, if the page shows CAPTCHA/reCAPTCHA, `#gs_captcha_ccl`, "unusual traffic", or a script returns `{ error: "captcha" }`:

1. Stop all navigation, extraction, fetch, BibTeX export, and Zotero push steps.
2. Tell the user to complete the verification manually in the Chrome window controlled by MCP.
3. Wait for the user to confirm completion.
4. Retry only the current extraction/navigation once. If the verification persists, stop and report that Google Scholar is still blocking the session.

Never automate CAPTCHA solving, use third-party solving services, forge cookies, or attempt to bypass Google Scholar's access controls.

## Completion Signal

When all checks pass, say: "gs-check 已通过，本会话后续 `gs-*` 技能无需重复检查，除非 MCP 或浏览器环境变化。"
