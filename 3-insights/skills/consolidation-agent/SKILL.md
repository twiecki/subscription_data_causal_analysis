---
name: consolidation-agent
description: >-
  Consolidate the repo's living documents against the insights registry.
  Use when 3-insights/checks/integrity.py reports failures, when an insight has been
  superseded, when the same fact appears in more than one place, or on the
  recurring maintenance trigger (issue labeled agent:consolidate). Corrections
  do not propagate themselves — this skill is how they propagate.
---

# Consolidation agent

The repo is the collective memory of everyone (and every agent) working in
it — and memory rots: a fact gets corrected in one file and keeps steering
work from three others. Your job is to make the repo agree with
`3-insights/registry.md` again.

## Rules

1. **One fact, one place.** Canonical values live in the registry; living
   documents cite IDs (`[[i-xxxx]]`), they do not restate numbers. If you
   find a restated value, replace it with a citation.
2. **Einarbeiten, not anhängen.** Merge corrections into the right place of
   the leading document. Never append "UPDATE: actually..." postscripts —
   append-only prose is where stale facts hide.
3. **Delete refuted content** from living documents. The superseded insight
   keeps existing in the registry (status `superseded-by:<id>`) and its
   source artifact stays — provenance is preserved there, not in scattered
   copies.
4. **Never reuse or renumber an ID.** New claim, new rolled ID. Retired
   names go to `3-insights/alias.tsv` (append-only).
5. **Re-bind deliberately.** If you edited a registry source on purpose, run
   `python 3-insights/checks/integrity.py --rebind`. If binding fails and you did NOT
   edit the source, that is a finding, not a nuisance — the claim may no
   longer be supported; investigate before rebinding.

## Workflow

1. `python 3-insights/checks/integrity.py` — the failure list is your task list.
2. For each failure, apply the rules above with the smallest edit that makes
   the check pass honestly (no deleting checks, no citing-around).
3. Re-run the suite until green; run `pytest` for the data-layer gate.
4. PR description: which IDs changed status, which documents were
   consolidated, which bindings were refreshed and why.
