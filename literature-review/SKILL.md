---
name: literature-review
description: Plan and execute staged AI-related literature reviews, including arXiv-based or recursive citation-based paper collection, multi-agent title/abstract and optional PDF-front-page filtering, Chinese full-paper digestions, synthesis reports, optional development mindmaps, and recommended-reading CSVs. Use when a user asks for an AI literature review, survey, related-work collection, citation-chain review, paper screening, systematic paper reading, research-lineage synthesis, or wants to resume one of these stages from existing artifacts.
---

# AI Literature Review

Run a review as four auditable stages: collection, filtering, deep reading, and final artifact generation. Prefer a reviewable plan over immediate execution and keep explicit user gates between stages.

## Python interpreter

Before every Python command used by this skill, ask the user and wait. Do not assume an interpreter, and do not use a machine-specific path.

1. Yes. I have a local Python. Provide the interpreter path in Other.
2. No. Install an environment with uv in this skill folder.
3. No. Do not install anything. Stop this skill.
4. Other.

- If the user chooses 1 or 4, use only the interpreter they provide.
- If the user chooses 2, create the environment with uv in this skill folder (the directory that contains this `SKILL.md`) and install the `arxiv` package, because this skill runs the arxiv skill's scripts. Then use that interpreter.
- If the user chooses 3, stop immediately. Do not install anything, and do not fall back to system Python.

Ask once per session, then reuse that interpreter. Resolve bundled scripts relative to this `SKILL.md`. Write review artifacts to the user-specified output directory, defaulting to the current working directory; never write review outputs inside the skill directory.

## Default: produce a plan first

Unless the user explicitly says no literature-review plan:

1. Use the agent harness's Plan mode when available.
2. Produce a reviewable plan only; do not search, download, filter, or read papers yet.
3. **Initial-filter criteria — user chooses before the plan body.** Present candidate inclusion/exclusion criteria that can be decided from **title and abstract only**. For each candidate, state why title/abstract suffice. Ask the user to accept, reject, edit, or add; wait for that selection. Do not write a final criteria set into the plan on your own. Exception: the user explicitly asks for fully automated execution — then generate title/abstract-judgeable criteria and include them without waiting. Drop any criterion that needs PDF, methods section, or other full-text evidence; those belong to final filter or deep reading.
4. Then write the plan. Include the research scope, known requirements, collection method, arXiv **keyword groups and combinations** or base papers, recursion depth when `citation_based`, the **user-selected** initial-filter criteria, stage gates, subagent batching, requested final artifacts, output directory, and unresolved decisions. Whenever collection is `arxiv_based` (the default), the plan MUST include the query-construction slot below with a **complete** `all_prefix` string per axis (every `all:` term written out; no ellipsis). When collection is `citation_based`, state the recursion depth; if the user did not specify one, write the default of **3**.
5. Ask only for remaining information needed to approve the plan or start the next stage. Do not front-load later-stage questions other than the initial-filter criteria gate above.
6. Wait for the user to approve or revise the plan.
7. After the user approves the plan, merge every keyword-group variant from the approved complete `all_prefix` queries into the `keyword_groups.json` file that sits next to the arxiv skill's `SKILL.md`: union new terms into existing keys, add new group keys as needed, never delete existing groups or terms, keep the existing JSON quoting style (quote multi-word terms). This file is arxiv skill config for reuse, not a review output. Then begin collection (stage 1) unless the user asked to stop after the plan.

If the user explicitly declines a plan, begin at the first requested stage and still apply every stage gate below. When resuming, inspect existing artifacts and skip completed stages only when their outputs satisfy [references/artifact-schemas.md](references/artifact-schemas.md).

## Interaction and stage-gate rule

Treat every numbered stage as a checkpoint. Unless the user has explicitly authorized uninterrupted continuation through the next stage:

- summarize what completed, counts, failures, and output paths;
- recommend stopping for review and feedback;
- do not begin the next stage in the same turn.

Do not infer missing decisions that materially change the paper set. Ask at the specified decision node and wait.

## 1. Collect papers

Choose one method:

- **arxiv_based (default):** use the `$arxiv` skill **keyword path** to collect papers. **REQUIRED SUB-SKILL:** follow `$arxiv` keyword mode — decide groups + `AND`/`OR`/`NOT`, expand via its `keyword_groups.json`, run `build_query.py`, confirm the `all_prefix` variant, then search. Do not use arxiv fuzzy mode for collection unless the user explicitly asks for free-text recall only.

  Build **keyword combinations**; do not cover a topic with a list of quoted phrases.

  1. Split the topic into concept **groups** (one concept per group).
  2. Within a group: synonyms/variants joined by **OR** (`build_query.py` expands seeded groups and prunes phrase-subsumed terms; do not invent broader terms).
  3. Between groups on the same research axis: write the boolean as `<A> AND/OR/NOT <B> ...` (AND if every concept is required; OR if any suffices; NOT/ANDNOT to exclude). Do not hard-code the plan slot to AND when the intended logic is mixed.
  4. Independent axes (e.g. noise-fairness vs shift-fairness) are **separate combined queries**; union and dedupe afterward. Do not AND unrelated axes into one over-constrained query, and do not explode an axis into many near-duplicate phrase searches.
  5. Field: `--field all` / `all:` on **each term** (`all:"term"` covers title + abstract + authors + comments). Count: `--max-results all` (1000). Retrieval: metadata-only; no PDFs during collection.

  Plan slot (required, for user review) — fill this shape, not a phrase table. The `all_prefix query` line is the string that will be searched: write **every** `all:` term. Do not use `...`, `etc.`, or truncated OR lists.

  ```text
  Axis: <name>
    Groups: -g <concept A> -g <concept B> ...
    Relation: <A> AND/OR/NOT <B> ...
    all_prefix query: (all:"A" OR all:"A-syn") AND/OR/NOT (all:"B" OR all:"B-syn")
  ```

  Example (one shift-fairness axis, complete): Groups `-g fairness -g "distribution shift"`, Relation `fairness AND distribution_shift`, `all_prefix query`: `(all:fairness) AND (all:"distribution shift" OR all:"distribution shifts" OR all:"distributional shift" OR all:"distribution shifting" OR all:"label shift" OR all:"covariate shift" OR all:"concept shift" OR all:"prior probability shift" OR all:"dataset shift" OR all:"domain shift" OR all:"out-of-distribution" OR all:"out of distribution" OR all:OOD)`. Not `all:"fairness under distribution shift"` plus `all:"fairness distribution shift"` as separate phrase queries, and not `((all:fairness OR ...)) AND ((all:"distribution shift" OR ...))`. A quoted `all:"word1 word2 word3"` is a single phrase clause, not a combination; it misses papers that use the same concepts with different order, synonyms, or intervening words.

  Collect `title`, `abstract`, `author_names` formatted exactly as `<first author>, et.al`, `date`, and `doi`. Preserve `arxiv_id`, URLs, and provenance when available. Store deduplicated results in `papers_metadata.json` under the output directory.
- **citation_based:** require `base_paper` (one or more titles, IDs, or URLs). If `base_paper` is missing, ask and wait; do not invent base papers. If a maximum recursion depth is not specified, default to **3**; if the user specifies a depth, use that value. Before searching, notify the user that Google Scholar depends on a single Chrome DevTools session, so citation traversal will run serially with a fresh subagent for each target paper and may take longer. For each paper whose citations must be found, spawn one new subagent and let it handle that paper's complete cited-by search, including pagination. Keep only this one Scholar subagent active; after it finishes and releases the browser, end it and spawn a different fresh subagent for the next paper. Never reuse a citation-search subagent through follow-up tasks, and do not run any concurrent Google Scholar/Chrome DevTools operation from the main agent or another subagent. Follow the serial workflow in [references/subagent-workflows.md](references/subagent-workflows.md). Use `$google_scholar`, including its cited-by operation, to collect papers citing each frontier paper level by level through the requested depth (or the default of 3). First save deduplicated titles and any available authors to `citation_candidates.json`. Then enrich every candidate with abstract, date, DOI, and identifiers using the `$arxiv` skill in metadata-only mode; use web search only for unresolved papers and prefer primary paper or publisher pages. Save the enriched set to `papers_metadata.json`.

Deduplicate in this priority: normalized DOI, arXiv ID, then normalized title. Keep provenance and citation depth rather than discarding merged evidence. Use `null` for unavailable metadata; never guess. Follow the exact schemas in [references/artifact-schemas.md](references/artifact-schemas.md).

At completion, report counts for discovered, deduplicated, fully enriched, and unresolved papers, then apply the stage gate.

## 2. Filter papers

Use the **user-selected** inclusion/exclusion criteria from the approved plan. Do not invent a replacement set at this stage. If a criterion cannot be judged from title and abstract, do not apply it in the initial filter.

### 2A. Initial filter (required)

Classify from `(title, abstract)` only against those user-selected criteria. Delegate independent batches to subagents:

- fewer than 500 papers: 5 papers per subagent task;
- 500 or more papers: 10 papers per subagent task.

Use the multi-subagent wave workflow and prompt contract in [references/subagent-workflows.md](references/subagent-workflows.md). Require one result per paper with `pass`, `exclude`, or `uncertain`, criterion-level reasons, and evidence limited to the title/abstract. The main agent validates coverage, resolves duplicate/missing IDs, and writes `initial_filter_results.json`.

After presenting the initial-filter summary, ask whether to run the optional final filter and explain:

> The final filter downloads each initially passing/uncertain paper and gives subagents the title, abstract, and first two PDF pages. It costs more time and network/model work but can reject papers whose abstracts are ambiguous or misleading.

Wait for the answer unless the user already made this choice explicitly.

### 2B. Final filter (optional)

Run only after explicit user opt-in. Unless the user specifies a different candidate subset, include both `pass` and `uncertain` results from the initial filter. If the user explicitly requests only `pass` papers or another subset, follow that scope. Use `$arxiv` to download all PDFs in the selected candidate set; use web search and primary full-text sources when arXiv fails. Use the PDF tooling available in the harness to extract exactly the first two pages.

Delegate `(title, abstract, first_two_pages)` tuples:

- fewer than 50 papers: 1 paper per subagent task;
- 50 or more papers: 2 papers per subagent task.

Apply the same criteria and wave workflow. Never treat unavailable pages as negative evidence; mark the paper `unresolved` and explain the acquisition failure. Write `final_filter_results.json`, verify every candidate has exactly one result, then apply the stage gate.

The deep-reading set is final-filter passes when final filtering ran; otherwise it is initial-filter passes. Include uncertain papers only if the user's criteria or explicit decision allows them.

## 3. Deep-read papers

Before starting, ask whether the user has additional questions or focus areas beyond the standard paper-reading questionnaire, and wait for their response.

Create `<output_dir>/digestions/` if absent. Delegate exactly one paper per subagent. Each subagent must use `$paper-reading`, select its Chinese questionnaire (`references/reading_questions_ZH.md` within that skill), read the complete paper, answer in Chinese while preserving English technical terms, incorporate the user's extra questions, and save one `digestion-<paper_name>.md` in `digestions/`.

Require evidence grounded in the paper and prohibit fabrication. The main agent verifies one readable digestion per selected paper and records failures for retry. Then apply the stage gate.

## 4. Generate final artifacts

Before this stage, ask whether to generate the optional development mindmap. Explain that "all papers" means every paper with a successfully completed deep-reading digestion; each becomes a self-contained node of under 100 words, and edges state the concrete improvement/optimization relationship. Default to no mindmap until the user answers. The recommended-reading count defaults to 5 unless the user specifies `n`.

Read [references/artifact-schemas.md](references/artifact-schemas.md) before writing final artifacts.

### 4A. Literature review report

1. Run bundled [scripts/extract_digestions.py](scripts/extract_digestions.py) over `digestions/` to extract each paper's motivation/problem and method/solution content. Inspect the output and adjust heading aliases only if the actual digestion structure differs.
2. Delegate 10 extracted paper records per subagent task using [references/subagent-workflows.md](references/subagent-workflows.md). Save intermediate reports under `intermediate_reports/`.
3. Have the main agent aggregate all intermediate reports into `literature_review_report.md`. Include at minimum: the field's overall problem-solving logic (`问题解决整体思路`), a method overview (`解决方法概览`), and the development lineage among methods (`不同方法之间的发展脉络`). Reconcile contradictions against digestions and cite paper titles/DOIs or arXiv IDs; do not merely concatenate batch reports.

### 4B. Development mindmap (optional)

If opted in, create `literature_review_mindmap.md` as a Mermaid flowchart by default, or the user's requested format. Include every paper whose deep reading completed successfully; do not include failed or incomplete digestions. Use multiple thematic clusters; make each paper one node with a self-contained core-contribution summary under 100 words and no paper-local unexplained abbreviations. Connect papers only when evidence supports a development relationship, and label every edge with why the later paper improves or optimizes the earlier one. Represent independent roots explicitly rather than inventing edges.

### 4C. Suggested papers to read

Rank the `n` papers that best teach the field's foundational methods and research logic, balancing foundational, representative, and bridging works rather than citation count alone. Write `suggested_papers.csv` with columns `paper_name,date,doi,reasons`. Default `n=5`. Base every reason on the digestions and synthesis.

Verify coverage and output schemas, report all produced paths and omissions, then stop for user feedback unless the user explicitly requested another action.

## Non-negotiable safeguards

- Keep a stable paper ID across every artifact and preserve provenance.
- Never claim exhaustive coverage without recording keyword groups, relations, combined **complete** `all_prefix` queries, date boundaries, sources, and unresolved failures.
- Do not replace `$arxiv` group AND/OR/NOT combinations with a list of standalone `all:"multi-word phrase"` queries, and do not abbreviate `all_prefix` with `...`.
- Do not finalize initial-filter criteria without user selection unless the user asked for fully automated execution. Every initial-filter criterion must be decidable from title and abstract.
- After plan approval, merge approved group variants into the arxiv `keyword_groups.json` path above; do not wipe existing groups.
- Do not let a subagent silently change criteria or decide optional stages.
- Respect available subagent concurrency; dispatch in waves and reuse workers where supported.
- Validate batch coverage before synthesis: no missing papers, duplicate decisions, or untraceable report claims.
- Keep unrelated existing files untouched.
