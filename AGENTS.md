# House rules for agents working this repo

- **Numbers come from the data layer** (`1-data/derived/`, provenance on every
  row), never re-derived from raw files. Red test in `tests/` = layer
  off-limits; rebuild with `python 1-data/build_data.py` and investigate.
- **Definitions come from the semantic layer** (`1-data/semantic-layer/`)
- **Read `1-data/business-context.md` before analyzing** — answer what the
  stakeholder *means*, not just what they ask; know the ambient references
  ("the hike", "the pool", "the spike") and the decision frame. — the governed
  outcome, grain, guard window. Don't invent metrics.
- **Claims are cited, not restated.** Reference insight IDs from
  `3-insights/registry.md` as `[[i-xxxx]]`. New finding → new ID via
  `python 3-insights/mint_id.py` (never hand-rolled, never reused), registered with source + evidence, bound via
  `python 3-insights/checks/integrity.py --rebind`.
- **Before you finish:** `uv run pytest -q` and
  `uv run python 3-insights/checks/integrity.py` must both be green.
- **Analysis discipline** lives in `2-analyses/skills/` (quasi-experiment-analysis,
  causal-critiquer); insight hygiene lives in `3-insights/skills/consolidation-agent/`.
- Use `uv` for everything. Never commit `1-data/derived/` rebuild noise
  without rerunning the integrity suite.
