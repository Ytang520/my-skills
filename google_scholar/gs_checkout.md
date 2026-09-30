---
name: google_scholar-gs_checkout
description: Diagnose a failed Google Scholar workflow, create a new diagnostic run script without modifying the original script, and summarize the root cause and recommended original-script changes.
argument-hint: "[error output, script path, or failed operation]"
---

# Google Scholar Checkout

Use when a Google Scholar operation fails with a script error, unexpected DOM shape, navigation problem, empty result, BibTeX parse issue, or backend mismatch. Follow the main skill's environment and reCAPTCHA rules.

## Required Inputs

Collect as much of this context as is available:
- Failed operation and user intent.
- Error message or returned `{ error, message }` object.
- Original script path and script contents.
- Browser backend used: Chrome DevTools MCP or Playwright fallback.
- Current page URL and relevant page state.
- The input values used, such as query keywords, `data-cid`, page number, or BibTeX text.

## Diagnosis Process

1. Classify the failure:
   - Environment/backend: missing MCP tool, Playwright launch failure, invalid browser path.
   - Access block: Google Scholar verification or traffic block.
   - Navigation: wrong URL, timeout, cross-origin navigation, missing page context.
   - DOM extraction: selector no longer matches, result not on current page, missing `data-cid`.
   - Data conversion: malformed BibTeX, missing required Zotero fields.
   - Zotero handoff: Connector unavailable or push script returned a failure.
2. Read the original script and the relevant sub skill file.
3. Create a new run script instead of editing the original script.
   - Name it descriptively, such as `checkout_<operation>_<short_reason>.js` or `.py`.
   - Put it in a temporary or user-approved working location.
   - Preserve the original script's behavior, then add focused logging, guards, or fallback handling needed to prove the diagnosis.
   - Support the active backend. If the issue relates to backend compatibility, include both Chrome DevTools MCP instructions and Playwright fallback instructions.
4. Run or explain the new script only as far as the current environment safely allows.
5. Summarize the result and recommend exact changes for the original script, but do not modify it unless the user explicitly asks.

## Summary Format

```text
由于 {specific error or failed observation}，我们判断问题来自 {failure category and root cause}.

重新创建了 {new script path/name}。它在原有脚本基础上的变化：
- {change 1}
- {change 2}

对原有脚本建议修改：
- {recommended original-script change 1}
- {recommended original-script change 2}

验证结果：
{what the new script proved, or why verification stopped}
```

If the failure is caused by Google Scholar verification, stop and use the main skill's reCAPTCHA flow instead of generating bypass logic.
