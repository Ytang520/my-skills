---
name: google_scholar-gs_fulltext
description: Resolve full-text, publisher, and DOI access links for a Google Scholar result using data-cid or a result number from the current page.
argument-hint: "[data-cid or result number]"
---

# Google Scholar Full Text

Use after `google_scholar/SKILL.md` has selected the browser automation backend. Follow the main skill's environment and reCAPTCHA rules.

## Arguments

`$ARGUMENTS` can be:
- A `data-cid` from a previous result.
- A result number from the current Google Scholar page.

## Steps

1. Ensure the target result is visible on the current Google Scholar results page. If not, run `gs_search.md` first.
2. Set `globalThis.__GS_EXTRACT_OPTIONS__`:
   - For `data-cid`: `{ cid: "DATA_CID" }`
   - For result number: `{ index: RESULT_NUMBER }`
3. Read and execute `google_scholar/scripts/extract_fulltext.js`.
4. If the script returns an `error`, handle it according to the main skill.
5. Report available direct full-text, publisher, and DOI links.

## Output Format

```text
Full Text Links - {title}

Authors: {authors} | {journalYear}

Direct Full Text:
{fullTextUrl or "No direct full text link available"}

Publisher Page:
{publisher or "N/A"}

DOI:
{doi or "No DOI detected"}
```

If the user asks to open the full text immediately, use the selected browser backend to open the best available link in this order: direct full text, DOI, publisher page.
