---
name: gs-export
description: Export Google Scholar paper(s) to Zotero via BibTeX. Gets citation data from Google Scholar's cite dialog, then pushes to Zotero desktop. Supports single or batch export.
argument-hint: "[data-cid or space-separated data-cids]"
---

# Google Scholar Export to Zotero

## Required GS Check

Before running this skill, use `gs-check` first. If this exact chat/session already completed `gs-check` successfully and the MCP/browser environment has not changed, do not repeat the check.

Prefer Chrome DevTools MCP for browser automation. If `gs-check` reports that Chrome DevTools MCP is unavailable but the user chose or approved the Playwright fallback, run the same workflow through Playwright instead: use `page.goto()` for `navigate_page`, `page.evaluate()` for `evaluate_script`, and `browser.newPage()` plus `page.goto()` for `new_page`. Use the browser executable path saved in `gs-check/chrome-path.txt` when that file exists and the path is valid, and keep this skill's output schema unchanged.

If neither Chrome DevTools MCP nor the approved Playwright fallback is available, stop and report the missing browser automation environment instead of trying WebFetch, curl, or non-browser scraping.

If Google Scholar shows CAPTCHA/reCAPTCHA, `#gs_captcha_ccl`, "unusual traffic", or any script returns `{ error: "captcha" }`, stop immediately and ask the user to complete the verification manually in the MCP-controlled or Playwright-controlled Chrome window. Continue only after the user confirms completion; never automate or bypass CAPTCHA.

Export Google Scholar paper citation data via BibTeX extraction and push to Zotero desktop.

## Arguments

$ARGUMENTS contains one or more data-cids (space-separated), e.g.:
- `TFS2GgoGiNUJ` — single paper
- `TFS2GgoGiNUJ abc123XYZ def456UVW` — batch export

## Steps

### Step 1: Get BibTeX for each paper

For each data-cid, perform 3 tool calls to bypass CORS:

#### 1a. Fetch cite dialog to get BibTeX link (evaluate_script)

```javascript
async () => {
  const cid = "DATA_CID_HERE";
  const resp = await fetch(
    `https://scholar.google.com/scholar?q=info:${cid}:scholar.google.com/&output=cite`,
    { credentials: 'include' }
  );
  const html = await resp.text();
  const doc = new DOMParser().parseFromString(html, 'text/html');

  // Extract export links
  const links = Array.from(doc.querySelectorAll('#gs_citi a')).map(a => ({
    format: a.textContent.trim(),
    url: a.href
  }));

  // Extract citation format texts
  const citations = Array.from(doc.querySelectorAll('#gs_citt tr')).map(tr => {
    const cells = tr.querySelectorAll('td');
    return {
      style: cells[0]?.textContent?.trim() || '',
      text: cells[1]?.textContent?.trim() || ''
    };
  });

  const bibtexLink = links.find(l => l.format === 'BibTeX');
  return { cid, bibtexLink: bibtexLink?.url || '', links, citations };
}
```

#### 1b. Navigate to BibTeX URL (navigate_page)

Use `mcp__chrome-devtools__navigate_page`:
- url: the `bibtexLink` URL from step 1a (on `scholar.googleusercontent.com`)

This bypasses CORS restrictions that block fetch() to googleusercontent.com.

#### 1c. Read BibTeX content (evaluate_script)

```javascript
async () => {
  return { bibtex: document.body.innerText || document.body.textContent || '' };
}
```

### Step 2: Parse BibTeX and push to Zotero

Before calling Python, ask which interpreter to use and wait. Do not assume an interpreter, and do not use a machine-specific path.

1. Yes. I have a local Python. Provide the interpreter path in Other.
2. No. Install an environment with uv in this skill folder.
3. No. Do not install anything. Stop this skill.
4. Other.

- If the user chooses 1 or 4, use only the interpreter they provide.
- If the user chooses 2, create the environment with uv in this skill folder (the directory that contains this `SKILL.md`). The bundled script uses the Python standard library, so do not install extra packages. Then use that interpreter.
- If the user chooses 3, stop immediately. Do not install anything, and do not fall back to system Python.

Ask once per session, then reuse that interpreter. Save the BibTeX data as JSON in the current working directory, then call the push script:

```bash
"<chosen-python>" "<SKILL_ROOT>/scripts/push_to_zotero.py" gs_papers.json
```

`SKILL_ROOT` is the directory that contains this `SKILL.md`. Before calling the script, construct `gs_papers.json` in the current working directory from BibTeX. Parse the BibTeX yourself and create the JSON array:

```json
[
  {
    "pmid": "",
    "title": "The title from BibTeX",
    "authors": [
      {"lastName": "Smith", "firstName": "John"}
    ],
    "journal": "Journal Name",
    "journalAbbr": "",
    "pubdate": "2022",
    "volume": "14",
    "issue": "4",
    "pages": "1054",
    "doi": "",
    "pdfUrl": "https://example.com/paper.pdf",
    "abstract": "",
    "keywords": [],
    "language": "en",
    "pubtype": ["Journal Article"]
  }
]
```

**IMPORTANT**: Set `pdfUrl` from the search result's `fullTextUrl` field (the PDF link extracted by gs-search). The Python script will download the PDF and upload it to Zotero via `/connector/saveAttachment` (Zotero 7.x ignores attachments in saveItems). PDF download may fail for some publishers (403, JS-redirect); these are reported as "PDF skip".

BibTeX fields mapping:
- `@article{key,` → `itemType: journalArticle`
- `@inproceedings{key,` → `itemType: conferencePaper`
- `@book{key,` → `itemType: book`
- `title={...}` → `title`
- `author={Last1, First1 and Last2, First2}` → `authors` array
- `journal={...}` → `journal`
- `year={...}` → `pubdate`
- `volume={...}` → `volume`
- `number={...}` → `issue`
- `pages={...}` → `pages`
- `publisher={...}` → (included in extra or publisher field)

### Step 3: Report

Single paper:
```
Exported to Zotero from Google Scholar:
  Title: {title}
  Authors: {authors}
  Journal: {journal} ({year})
  Data-CID: {dataCid}
```

Batch:
```
Exported {count} papers to Zotero from Google Scholar:
  1. {title1} ({journal1}, {year1})
  2. {title2} ({journal2}, {year2})
  ...
```

## Batch Export Optimization

For multiple papers, process sequentially to avoid CAPTCHA:
1. Get all BibTeX links in one evaluate_script call (fetch all cite dialogs)
2. Navigate to each BibTeX URL one at a time
3. Collect all BibTeX entries
4. Push all to Zotero in a single batch

## Notes

- Single paper export uses 3-4 tool calls: `evaluate_script` (cite dialog) + `navigate_page` (BibTeX URL) + `evaluate_script` (read BibTeX) + `bash python` (Zotero push)
- Batch export: 2N+1 tool calls (N papers: N navigate + N evaluate + 1 bash)
- BibTeX links are on `scholar.googleusercontent.com` — CORS blocks fetch(), so we use navigate_page to bypass
- Reuses `push_to_zotero.py` for Zotero Connector API communication
- Google Scholar BibTeX does NOT include abstract or DOI — these fields will be empty in Zotero
- After export, navigate back to Google Scholar page: `navigate_page` with type `back`
