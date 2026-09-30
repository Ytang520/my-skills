# Subagent workflows

Use these contracts for citation collection, filtering, deep reading, and synthesis. Keep criteria and source material immutable within a wave.

## Contents

1. Citation-search serialization
2. Wave orchestration
3. Initial-filter task
4. Final-filter task
5. Deep-reading task
6. Intermediate-synthesis task

## 1. Citation-search serialization

Before any citation-based Google Scholar search, tell the user:

```text
Citation-based search requires Google Scholar through a single Chrome DevTools session. I will therefore run citation traversal serially with only one subagent at a time and use a fresh subagent for each target paper; this may take longer than parallel paper collection.
```

Create one citation-search task per target paper. Spawn a fresh subagent for that paper and have it complete the paper's full cited-by traversal, including all required result pages. Keep exactly one Google Scholar subagent active at any moment. After the task completes, wait for the browser to be released and let that subagent end; then spawn a different fresh subagent for the next target paper. Never use follow-up tasks to reuse a citation-search subagent for another paper. During this traversal, the main agent and all other subagents must not open or control Google Scholar or start another Chrome DevTools browser session. Never place Google Scholar citation-search tasks in a parallel spawn wave.

This serialization constraint applies specifically to the browser-dependent citation search. After Google Scholar traversal finishes, arXiv metadata enrichment and other non-browser work may use normal concurrency when safe.

## 2. Wave orchestration

1. Build a deterministic task manifest with task IDs, paper IDs, input file paths, and expected output paths.
2. Split tasks using the batch size fixed by `SKILL.md`; never enlarge a batch merely to reduce task count.
3. Spawn only up to the harness's currently available concurrency. Dispatch remaining tasks in later waves. Reuse idle subagents with follow-up tasks when supported.
4. Give each subagent only its assigned records, the approved criteria/questions, the output schema, and the destination. Do not expose other agents' conclusions.
5. Wait for the wave, record failures, validate structured outputs, and retry malformed/missing work once with a precise correction.
6. Merge by stable `paper_id`, reject duplicates, and compare actual IDs with the manifest before moving on.

When the harness exposes a dedicated multi-agent spawn workflow, use it for each wave while preserving these batch sizes and validation rules.

## 3. Initial-filter task

Give the subagent 5 records when total papers `<500`, otherwise 10.

```text
Classify only the assigned papers against the user approved criteria. You may use only title and abstract; do not search or infer unseen full-text content. Every criterion must be decidable from those two fields. Return one JSON result per paper using the filter schema. Decisions: pass when inclusion is supported and no exclusion is met; exclude when evidence directly meets an exclusion or contradicts a required inclusion; uncertain when the supplied text is insufficient. Quote or tightly paraphrase the decisive evidence. Do not alter criteria.
```

## 4. Final-filter task

Give the subagent 1 record when total candidates `<50`, otherwise 2.

```text
Reassess only the assigned papers against the same approved criteria using title, abstract, and exactly the first two PDF pages. Return one JSON result per paper using the filter schema. Do not use outside sources or assume later-page content. If pages are missing/corrupt, return unresolved rather than exclude. State what new evidence from the first two pages changed or confirmed relative to the abstract-only judgment.
```

## 5. Deep-reading task

Give exactly one paper to each subagent.

```text
Use $paper-reading on this one paper. Use the Chinese questionnaire and read the full paper, not only the abstract or first pages. Answer the user's additional questions as extra sections. Ground every claim in the paper, preserve English technical terms, and save the digestion in the assigned output directory. Return the paper_id and exact output path when complete; report acquisition/parsing failure without fabricating content.
```

## 6. Intermediate-synthesis task

Give no more than 10 extracted digestion records to each subagent.

```text
Synthesize only the assigned extracted records into a Chinese intermediate report. For each paper, identify the problem/motivation, method, core contribution, and its evidenced relationship to other assigned papers. Then summarize shared problem-solving logic, method families, chronological or conceptual development, conflicts, and open uncertainty. Use paper titles plus DOI/arXiv ID as anchors. Do not invent relationships, consult outside sources, or drop a record. Save Markdown to the assigned intermediate_reports path.
```

The main agent must treat intermediate reports as lossy analyses: reconcile them against extraction records and original digestions during final aggregation.
