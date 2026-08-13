# House rules for agents working this repo

- **Numbers come from the data layer** (`data/derived/`, provenance on every
  row), never re-derived from raw files. Red test in `tests/` = layer
  off-limits; rebuild with `python data/build_data.py` and investigate.
- **Definitions come from `contracts/metric-contract.yml`** — the governed
  outcome, grain, guard window. Don't invent metrics.
- **Claims are cited, not restated.** Reference insight IDs from
  `insights/registry.md` as `[[i-xxxx]]`. New finding → new rolled ID (4 hex
  chars, check it's unused), registered with source + evidence, bound via
  `python checks/integrity.py --rebind`.
- **Before you finish:** `uv run pytest -q` and
  `uv run python checks/integrity.py` must both be green.
- **Analysis discipline** lives in `skills/quasi-experiment-analysis/`;
  repo hygiene lives in `skills/consolidation-agent/`.
- Use `uv` for everything. Never commit `data/derived/` rebuild noise
  without rerunning the integrity suite.
