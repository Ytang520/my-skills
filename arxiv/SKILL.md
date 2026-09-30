---
name: arxiv
description: Search and retrieve arXiv papers by fuzzy name search (default), exact keyword matching, or direct arXiv id lookup; batch-fetch metadata and PDFs. Use when the user mentions arXiv, paper search, paper title lookup, academic paper retrieval, keyword literature search, downloading paper PDFs, or batch-getting papers by arXiv id.
---

# arXiv Search & Retrieve

## Overview

Search and retrieve arXiv papers. **Default search mode is fuzzy** (paper name / free-text relevance — not forced keyword containment). Switch to **keyword** mode only when the user explicitly requires keyword matching / containment. Also supports **direct arXiv id** lookup. Default retrieve mode is **both** (metadata + PDF).

## Python interpreter (required)

Before running any Python script for this skill, ask the user and wait. Do not assume an interpreter, and do not use a machine-specific path.

1. Yes. I have a local Python. Provide the interpreter path in Other.
2. No. Install an environment with uv in this skill folder.
3. No. Do not install anything. Stop this skill.
4. Other.

- If the user chooses 1 or 4, use only the interpreter they provide.
- If the user chooses 2, create the environment with uv in this skill folder (the directory that contains this `SKILL.md`) and install the `arxiv` package. Then use that interpreter.
- If the user chooses 3, stop immediately. Do not install anything, and do not fall back to system Python.

Ask once per session, then reuse that interpreter. Skill root for **scripts / keyword_groups.json / this SKILL.md** is the directory containing this file. `cd` into the skill root only so relative `scripts/...` resolve. **`--out-dir` is independent**: put results under the user's project / current working directory — **never** under the skill folder.

## Choose search mode first

```text
User gives arXiv id(s)?     -> mode=id
User asks keyword/exact
  containment / 必须包含关键词? -> mode=keyword (variants + confirm)
Otherwise (default)        -> mode=fuzzy (name / free-text)
```

| Mode | When | Behavior |
|------|------|----------|
| `fuzzy` (**default**) | Paper name, topic phrase, vague recall | Relevance free-text; **no** forced keyword containment; **no** synonym Boolean expansion required |
| `keyword` | User explicitly wants keywords to be contained / exact match | Decide groups + relations → synonym expand → **show variants → wait for confirm** → search |
| `id` | User passes arXiv id(s) or abs/pdf URLs | Direct `id_list` lookup |

### Mode discrimination examples (mandatory)

| User utterance | Mode | Why |
|---|---|---|
| 用关键词检索：必须同时包含 memory、LLM、attack | keyword | 「关键词检索」+「必须包含」 |
| exact keyword match in title and abstract for RAG and agent | keyword | exact keyword + field constraint |
| keyword search: papers that contain both jailbreak and LLM | keyword | keyword search + hard containment |
| 下载 1706.03762 | id | arXiv id |
| 找 Attention Is All You Need 这篇 | fuzzy | paper-name recall, not forced keyword containment |
| 随便搜一下 memory agent 相关论文 | fuzzy | topical browse; no keyword-trigger words |

**Keyword triggers (any one -> keyword):**  
`keyword search` / `关键词检索` / `用关键词` / `关键词搜索` / `exact keyword` / `必须包含` / `必须同时包含` / `强制包含` / `精确匹配` / hard-filter English `contain`/`contains`/`containment`.

**Never keyword for:** arXiv id; paper-title lookup; topical phrases with 「相关/随便搜/找一下」 and **none** of the triggers above.

Optional helper (no network):

```bash
"<chosen-python>" scripts/search_arxiv.py --detect-mode "随便搜一下 memory agent 相关论文"
# -> {"mode":"fuzzy", ...}
```

## Workflow

Copy and track:

```text
Task Progress:
- [ ] 1. Ask which Python interpreter to use
- [ ] 2. Detect mode: id | keyword | fuzzy (default fuzzy)
- [ ] 3a. id → search_arxiv.py --mode id --id ...
- [ ] 3b. fuzzy → search_arxiv.py --mode fuzzy --name/--query "..."
- [ ] 3c. keyword → build_query variants → user confirm → search_arxiv.py --mode keyword --query "..."
- [ ] 4. retrieve_papers.py (default: both)
```

### Step rules

1. **Mode first.** Default is **fuzzy**. Use **keyword** only if a keyword trigger is present (see table above). When unsure, run `--detect-mode` or choose fuzzy.
2. **Id shortcut.** If the input is an arXiv id (e.g. `2401.12345`, `arxiv:1706.03762`, abs URL), use `--mode id` (script also auto-detects pure ids).
3. **Keyword path only:** decide keyword groups + `AND`/`OR` → expand via [keyword_groups.json](keyword_groups.json) → run `build_query.py` (group-internal OR phrase-subsumption prune) → **show variants and wait for confirmation** → then search. For literal single-term containment without synonym expansion, pass `--no-expand`. Do **not** widen intent by replacing a specific phrase with a shorter general term that was not already in the group.
4. **Fuzzy path:** do **not** force field-prefixed exact containment; pass the paper name / free text to `--mode fuzzy`. Optionally tell the user the resolved fuzzy query, but no Boolean variant gate.
5. **Fields (keyword mode).** Default is the `all:` prefix (`all_prefix` variant): `all:"term"` covers title + abstract + authors + comments in one shot, keeps long multi-synonym queries short, and avoids `(ti: OR abs:)` pair duplication. Use `ti` / `abs` / `ti_abs` only when the user explicitly wants field-restricted matching.
6. **Count.** Default `max_results=5`. If the user wants all papers, use `1000` (`--max-results all`).
7. **Retrieve.** Default `both`. Switch to `metadata` or `pdf` only when the user asks.

## Quick Start

`cd` → skill root (scripts only). `PY` → the interpreter chosen above. `--out-dir` → **user project/cwd**, not the skill folder.

```bash
cd "<SKILL_ROOT>"   # this SKILL.md's directory (original or copy)

PY="<chosen-python>"
OUT="<USER_PROJECT_OR_CWD>/arxiv_results"

# A) Fuzzy by paper name (DEFAULT)
"$PY" scripts/search_arxiv.py --mode fuzzy --name "Attention Is All You Need" --max-results 5 --out-dir "$OUT"

# B) Direct by arXiv id
"$PY" scripts/search_arxiv.py --mode id --id 1706.03762 --out-dir "$OUT"

# C) Keyword (only when user requires keyword containment)
"$PY" scripts/build_query.py -g memory -g LLM -g attack --relation AND --max-results 5 --retrieve both
# After user confirms a variant:
"$PY" scripts/search_arxiv.py --mode keyword --query "CONFIRMED_QUERY" --max-results 5 --out-dir "$OUT"

# D) Retrieve metadata + PDFs (default both)
"$PY" scripts/retrieve_papers.py --from-json "$OUT/metadata/results.json" --mode both --out-dir "$OUT"
```

## Scripts

### `scripts/search_arxiv.py`

| Flag | Meaning | Default |
|------|---------|---------|
| `--mode` | `fuzzy` / `keyword` / `id` | `fuzzy` |
| `-q` / `--query` | Fuzzy free text, or confirmed keyword query | — |
| `-n` / `--name` | Paper name alias for fuzzy | — |
| `-i` / `--id` | arXiv id (repeatable); for id mode | — |
| `--max-results` | Number, or `all` → 1000 | `5` |
| `--sort` | `SubmittedDate` / `Relevance` / `LastUpdatedDate` | fuzzy→`Relevance`, keyword→`SubmittedDate` |
| `--out-dir` | Output root | `./arxiv_results` |

Writes:

- `out-dir/metadata/results.json` (includes `"mode"`)
- `out-dir/metadata/results.md`

Client settings: `page_size=100`, `delay_seconds=10`, `num_retries=5`.

### `scripts/build_query.py`

**Keyword mode only.** Build query variants for user confirmation. **No network.**

| Flag | Meaning | Default |
|------|---------|---------|
| `-g` / `--group` | One group (comma-separated). Repeatable | required |
| `-r` / `--relation` | Between groups: `AND` or `OR` | `AND` |
| `--field` | Primary field: `all` / `ti_abs` / `ti` / `abs` / `bare` | `all` |
| `--groups-file` | Synonym groups JSON | `keyword_groups.json` |
| `--no-expand` | Skip synonym expansion | off |
| `--max-results` | Display only; `all` → 1000 | `5` |
| `--retrieve` | Display only: `both`/`metadata`/`pdf` | `both` |
| `--json` | Machine-readable output | off |

Variants: `all_prefix` (**default** — `all:` covers title + abstract + authors + comments), `field_ti_abs`, `field_ti` / `field_abs`, `bare`.

### `scripts/retrieve_papers.py`

Batch retrieve by id list or search JSON. Default mode **both**.

| Flag | Meaning | Default |
|------|---------|---------|
| `-i` / `--id` | arXiv id (repeatable) | — |
| `--from-json` | Load ids from `results.json` | — |
| `--mode` | `both` / `metadata` / `pdf` | `both` |
| `--id-chunk-size` | ids per API request (max 200) | `100` |
| `--no-resume` | Refetch even if outputs already exist | off (resume ON) |
| `--out-dir` | Output root | `./arxiv_results` |

Outputs:

- `out-dir/metadata/<id>.json` (when metadata/both)
- `out-dir/pdfs/<id>.pdf` (when pdf/both)
- `out-dir/retrieve_summary.json`

Behavior: ids are fetched in **chunks of `--id-chunk-size`** (the arxiv package does not chunk `id_list` itself — see Limits below). Each chunk retries with exponential backoff (30 s × attempt, 5 attempts); a chunk that still fails is recorded in `failures` and the run **continues**. **Resume is ON by default**: ids whose `<id>.json` / `<id>.pdf` already exist in out-dir are skipped, so interrupted batches can simply be rerun.

## Limits & network notes

- **`id_list` is not auto-chunked by the arxiv package.** `Search._url_args` embeds the whole list in every page URL; >~200 ids produce over-long URLs that arXiv rejects — and the library's instant retries of the same giant URL can earn your IP a ~15-minute HTTP 429 ban. Both scripts here chunk to 100 ids/request. Don't raise `--id-chunk-size` past 200.
- **429 = back off, not retry.** If you see HTTP 429, wait several minutes before the next request; hammering extends the ban. The scripts' chunk-level backoff (30/60/90/120/150 s) handles transient 429s automatically.
- **Direct PDF URLs are deterministic**: `https://arxiv.org/pdf/<id>` (no API call needed). Useful for bulk PDF-only jobs once metadata is known.
- **Windows consoles**: both scripts reconfigure stdout/stderr to UTF-8; if you wrap them, keep that (cp1252 crashes on CJK error text).

## Keyword groups

Used in **keyword mode**. Shared synonym groups live in [keyword_groups.json](keyword_groups.json). On any hit, expand the whole group with `OR`, then drop terms **phrase-covered** by a shorter sibling already in that same OR group (e.g. keep `language model`, drop `large language model`). This only removes redundant narrower terms — it never invents a broader term. Seeded groups include `llm`, `agent`, `security`, `rag`, `memory`, `conformal`, `distribution_shift`. Note: expansion matches group **member strings** (e.g. `-g "conformal prediction"`), not group key names.

## Parameters cheat sheet

| Param | Default | Notes |
|-------|---------|-------|
| search mode | `fuzzy` | `keyword` only if user requires keyword containment; `id` for arXiv ids |
| `max_results` | `5` | User says all → `1000` |
| field (keyword) | `all:` prefix | `all_prefix` unless user specifies otherwise; covers ti+abs+authors+comments |
| retrieve | `both` | User can choose metadata-only or pdf-only |
| relation (keyword) | `AND` | Between keyword groups |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Using keyword Boolean flow for a paper title | Default is **fuzzy** (`--mode fuzzy --name "..."`) |
| Treating「相关/随便搜」as keyword mode | No trigger words -> stay **fuzzy** |
| Skipping variant confirmation in keyword mode | Keyword mode still requires `build_query.py` + user confirm |
| Forcing keyword containment when user did not ask | Stay on fuzzy unless a keyword trigger is present |
| Assuming a fixed or system Python | Ask which interpreter to use, then use only that answer |
| Writing `--out-dir` under the skill folder after `cd` | `cd` is for scripts only; `--out-dir` → user project/cwd |
| Forgetting “all papers” -> 1000 | Map “all/全部” to `--max-results all` (1000) |
| Skipping PDF when user did not opt out | Default retrieve mode is `both` |
| Assuming `id_list` is auto-chunked | It is now (100/request) — but only in these scripts, not in the raw `arxiv` package |
| Rerunning an interrupted batch from scratch | Resume is ON by default; just rerun the same command |

## Reference

Query-variant experiments: [test_all_prefix.py](test_all_prefix.py)
