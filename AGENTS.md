# House rules for agents working this repo

- **Numbers come from the data layer** (`1-data/derived/`, provenance on every
  row), never re-derived from raw files. Red test in `tests/` = layer
  off-limits; rebuild with `python 1-data/build_data.py` and investigate.
- **Definitions come from the semantic layer** (`1-data/semantic-layer/`) — the governed
  outcome, grain, guard window. Don't invent metrics.
- **Claims are cited, not restated.** Reference insight IDs from
  `3-insights/registry.md` as `[[i-xxxx]]`. New finding → new ID via
  `python 3-insights/mint_id.py` (never hand-rolled, never reused), registered with source + evidence, bound via
  `python 3-insights/checks/integrity.py --rebind`.
- **Every analysis run appends a row to `2-analyses/RUNS.csv`** — run id,
  date, model, seed, headline, resulting insight ID. Which run produced
  which artifact must be answerable a year later (MLflow at scale; the
  property is what matters).
- **Before you finish:** `uv run pytest -q` and
  `uv run python 3-insights/checks/integrity.py` must both be green.
- **Analysis discipline** lives in `2-analyses/skills/` (quasi-experiment-analysis,
  causal-critiquer); insight hygiene lives in `3-insights/skills/consolidation-agent/`.
- Use `uv` for everything. Never commit `1-data/derived/` rebuild noise
  without rerunning the integrity suite.
