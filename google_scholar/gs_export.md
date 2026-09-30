---
name: google_scholar-gs_export
description: Export one or more Google Scholar results to Zotero by retrieving BibTeX from Scholar and pushing Zotero-friendly JSON to the local Zotero Connector.
argument-hint: "[data-cid or space-separated data-cids]"
---

# Google Scholar Export to Zotero

Use after `google_scholar/SKILL.md` has selected the browser automation backend. Follow the main skill's environment and reCAPTCHA rules.

## Arguments

`$ARGUMENTS` contains one or more Google Scholar `data-cid` values.

## Steps

For each `data-cid`:

1. Set `globalThis.__GS_EXTRACT_OPTIONS__ = { cid: "DATA_CID" }`.
2. Read and execute `google_scholar/scripts/fetch_bibtex_link.js` on a Google Scholar page.
3. If the result has an `error`, handle it according to the main skill.
4. Navigate to the returned `bibtexLink`.
   - Chrome DevTools MCP: `navigate_page` to the link.
   - Playwright fallback: `page.goto(bibtexLink, { waitUntil: 'domcontentloaded' })`.
5. Read and execute `google_scholar/scripts/read_bibtex.js`.
6. Append the returned BibTeX text to a temporary `.bib` file.

After collecting BibTeX, ask which Python interpreter to use and wait. Do not assume an interpreter, and do not use a machine-specific path.

1. Yes. I have a local Python. Provide the interpreter path in Other.
2. No. Install an environment with uv in this skill folder.
3. No. Do not install anything. Stop this skill.
4. Other.

- If the user chooses 1 or 4, use only the interpreter they provide.
- If the user chooses 2, create the environment with uv in this skill folder (the directory that contains `google_scholar/SKILL.md`). The bundled scripts use the Python standard library, so do not install extra packages. Then use that interpreter.
- If the user chooses 3, stop immediately. Do not install anything, and do not fall back to system Python.

Ask once per session, then reuse that interpreter. Keep `TEMP.bib` and `TEMP.json` in the current working directory.

1. Convert BibTeX to Zotero-friendly JSON:
   - `"<chosen-python>" "<google_scholar skill root>/scripts/parse_bibtex.py" TEMP.bib > TEMP.json`
2. If previous search results include `fullTextUrl`, add it as `pdfUrl` to the matching JSON item before pushing.
3. Push to Zotero:
   - `"<chosen-python>" "<google_scholar skill root>/scripts/push_to_zotero.py" TEMP.json`

## Batch Guidance

For multiple papers, process sequentially to reduce block risk:
1. Get BibTeX links one paper at a time.
2. Navigate to each BibTeX URL and read its body text.
3. Parse all collected entries once.
4. Push all parsed items in one Zotero call.

## Output Format

```text
Exported {count} paper(s) to Zotero from Google Scholar:
1. {title} ({publicationTitle}, {date})
```

Report Zotero push failures exactly as returned by the push script.
