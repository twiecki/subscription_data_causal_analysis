# A production-grade agentic data science repo

One repo, all the pieces from the MADS course, interlocking — how you set up
agentic data science so that *many* people and *many* agents can work it
without it rotting:

| layer | property | where it lives | what breaks without it |
|---|---|---|---|
| **1 · Data** | derived layer + provenance | `1-data/` | every run re-derives numbers, each slightly differently |
| **1 · Data** | the semantic layer (governed definitions) | `1-data/semantic-layer/` — one file per metric | the metric means four things; the agent picks one silently |
| **1 · Data** | business context | `1-data/business-context.md` — why the questions get asked | the agent answers what was asked, not what was meant |
| **2 · Analyses** | the analyses themselves | `2-analyses/` | work exists only in chats |
| **2 · Analyses** | skills (discipline + verifier) | `2-analyses/skills/` — quasi-experiment-analysis, causal-critiquer | every run re-learns the same traps |
| **2 · Analyses** | evals (proof a skill helps) | `2-analyses/tasks/` + `eval.yml` | "seems to help" stays a vibe; models drift silently |
| **2 · Analyses** | the agent loop (harness) | `agent-task.yml` — label an issue, get a PR | no queue, no audit, no independent review |
| **3 · Insights** | claims as artifacts | `3-insights/registry.md` — stable IDs, status, binding hashes | refuted numbers keep steering decisions |
| **3 · Insights** | workspace integrity + hygiene | `3-insights/checks/` + `3-insights/skills/consolidation-agent/` | the repo is the agents' memory — and memory rots |
| **4 · Visibility** | the dashboard | `4-dashboard/app.py` (marimo, WASM-exportable) | the system's state lives in nobody's head |

The through-line: **agents propose, deterministic checks decide, humans
merge.** Judgment lives in text (skills, contracts); the non-negotiable
checks live in code (pytest, integrity suite, verifier) — encode the
invariants, not the entire path.

## Quickstart

```bash
uv sync
uv run python 1-data/build_data.py   # build the derived layer
uv run pytest -q                     # invariant gate
uv run python 3-insights/checks/integrity.py  # workspace integrity (5 checks)
uv run marimo run 4-dashboard/app.py # the dashboard
```

Try the multi-agent loop: open an issue describing an analysis, label it
`agent:analyze` (or `agent:consolidate` for repo hygiene), and watch the PR
arrive; label the PR `agent:review` for an independent critique. Needs
`ANTHROPIC_API_KEY` as a repo secret.

---

## The benchmark underneath

Causal-inference validation discipline, packaged as a
[SkillsBench](https://github.com/benchflow-ai/skillsbench) task (Harbor
format) — plus the CI/CD loops that keep it honest. Companion repo to the
MADS course module on the agentic-DS reliability stack.

The task: a subscription business raised its price ~33% without an A/B test.
The agent must estimate the causal effect from observational data **and**
honor a governed metric contract — placebo-in-time sweep, anticipation
sensitivity, auditable code artifact. A deterministic pytest verifier grades
the artifacts; the hidden ground truth (~−15.75%) lives in the verifier,
never in the container.

## Layout

```text
tasks/price-hike-causal-validation/
  task.toml            # metadata, timeouts, resources
  instruction.md       # agent-facing task (outcome-focused, deliberately dumb)
  environment/
    Dockerfile         # python:3.12-slim + pinned analysis stack
    daily_aggregates_intervention.csv
    metric-contract.yml                 # the governed definitions (v0.2.0)
    skills/quasi-experiment-analysis/   # curated skill (with-skill arm)
  solution/solve.sh    # oracle: a known-good analysis
  tests/
    test.sh            # pytest -> /logs/verifier/reward.txt
    test_outputs.py    # the verifier
.github/workflows/eval.yml   # the two CI loops (see below)
```

## What the verifier checks

1. `effect_pct` within [−20, −10] (hidden truth ~−15.75%)
2. estimand named
3. placebo sweep: ≥ 8 fake dates, real date z ≥ 2 — grades evidence
   *quality*, not checkbox compliance
4. `analysis.py` exists and reads the provided CSV (auditability)
5. memo discusses anticipation effects

## CI/CD: the two loops

[`./.github/workflows/eval.yml`](.github/workflows/eval.yml) runs:

| Loop | Trigger | What it does | Needs |
|---|---|---|---|
| **1 — verify the task** | every PR + push to main | builds the environment, runs the oracle (verifier must award reward 1), runs the negative control on an unsolved container (must award reward 0) | nothing |
| **2 — agent eval** | weekly cron (Mon 06:00 UTC) + manual dispatch | runs the real agent through the SkillsBench harness, with-skill and no-skill arms, and uploads reward rows as artifacts | `ANTHROPIC_API_KEY` repo secret |

Loop 1 means a contract, skill, or verifier edit that breaks the task shows
up red on the diff **before merge**. Loop 2 catches drift with no PR
attached — model updates, dependency rot — as a dropping pass rate. In
production the results rows go to a warehouse, keyed by skill + contract
version, so "did that change help?" is a `SELECT`.

## Run it locally

```bash
# oracle + verifier round trip (no API keys needed)
cd tasks/price-hike-causal-validation
docker build -t phcv-env environment/
docker run -d --name phcv phcv-env sleep infinity
docker cp solution/solve.sh phcv:/solve.sh && docker exec phcv bash /solve.sh
docker exec phcv mkdir -p /tests
docker cp tests/test_outputs.py phcv:/tests/ && docker cp tests/test.sh phcv:/tests/
docker exec phcv bash /tests/test.sh
docker exec phcv cat /logs/verifier/reward.txt   # 1 = pass
docker rm -f phcv

# full agent eval (in a clone of benchflow-ai/skillsbench, task copied to tasks/)
uv sync --locked
uv run bench tasks check tasks/price-hike-causal-validation
uv run bench run tasks/price-hike-causal-validation \
  --agent claude-agent-acp --model claude-sonnet-4-6 \
  --agent-env BENCHFLOW_SKILL_NUDGE=name        # with-skill arm
```

## Trial log (claude-agent-acp, Docker, n=1 per arm)

| model | skills | reward | failing check |
|---|---|---|---|
| sonnet-4-6 | – | 1.0 | — (read the contract unprompted, clean placebo) |
| haiku-4-5 | – | 0.0 | placebo z = 0.7 — sweep too noisy |
| haiku-4-5 | ✓ delivered & read | 0.0 | placebo z = 0.2 — still too noisy |

Findings, in maintenance-loop order:

1. **An over-specified instruction saturates the task.** v1 listed
   `placebo.json` as a deliverable — every model passed by following orders.
   Fixed: the instruction asks for the outcome; the standards live in
   `metric-contract.yml` in the environment.
2. **"With skills" ≠ skills delivered.** The first skill arm copied files
   into the container but the trajectory showed zero skill awareness; fixed
   with `BENCHFLOW_SKILL_NUDGE=name`. Grade the trace.
3. **The z-gate measures evidence quality.** Both haiku arms *ran* placebo
   sweeps; their distributions were too noisy to separate the real date.
4. **A workflow skill alone does not fix weak estimator execution** —
   matching the SkillsBench paper's nuance that skills don't help on 16/84
   tasks. Next patch candidates: concrete estimator idioms in the skill.

## References

- SkillsBench: [arXiv:2602.12670](https://arxiv.org/abs/2602.12670) ·
  [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench)
- [How Anthropic enables self-service data analytics with Claude](https://claude.com/blog/how-anthropic-enables-self-service-data-analytics-with-claude)
