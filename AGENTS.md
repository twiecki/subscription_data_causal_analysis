# House rules for agents working this repo

- **Numbers come from the data layer** (`1-data/derived/`, provenance on every
  row), never re-derived from raw files. Red test in `tests/` = layer
  off-limits; rebuild with `python 1-data/build_data.py` and investigate.
- **Definitions come from `1-data/contracts/metric-contract.yml`** — the governed
  outcome, grain, guard window. Don't invent metrics.
- **Claims are cited, not restated.** Reference insight IDs from
  `3-insights/registry.md` as `[[i-xxxx]]`. New finding → new rolled ID (4 hex
  chars, check it's unused), registered with source + evidence, bound via
  `python 3-insights/checks/integrity.py --rebind`.
- **Before you finish:** `uv run pytest -q` and
  `uv run python 3-insights/checks/integrity.py` must both be green.
- **Analysis discipline** lives in `2-analyses/skills/quasi-experiment-analysis/`;
  repo hygiene lives in `2-analyses/skills/consolidation-agent/`.
- Use `uv` for everything. Never commit `1-data/derived/` rebuild noise
  without rerunning the integrity suite.
