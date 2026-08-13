# DiD and synthetic control for the price hike — an honest failure

**Claim [[k-1231]]:** DiD and synthetic control cannot measure the price
hike's effect on this data — and no modeling effort will fix that.

## TL;DR

- Both methods need a **comparison group that didn't get the price hike**
  (an untreated region, plan, or cohort). Our data is one company-wide
  daily series; everyone got the hike. There is nothing to compare against.
- This is not a weak result — the quantity these methods estimate is
  **mathematically undefined** here. More data of the same kind, better
  priors, or robustness checks cannot recover it.
- **The answer to the business question already exists:** Bayesian ITS
  ([[i-3fa2]]) found the hike cut daily conversion by **~15.6%**
  (95% HDI [-19.2%, -12.4%]). That estimate stands.

| Method | Feasible? | Why not |
|---|---|---|
| Difference-in-differences | No | All units treated → design matrix rank 2 of 4; the effect parameter doesn't exist |
| Synthetic control | No | Zero untreated units → donor pool empty; no weights to optimize |
| Bayesian ITS ([[i-3fa2]]) | **Yes** | Builds the counterfactual from the pre-hike trend; no control group needed |

## What we tried

We attempted a difference-in-differences and a synthetic-control estimate of
the effect of [[k-a1f4]] on [[k-77b0]]. `analysis.py` enumerates every column
of `1-data/derived/daily.csv` searching for a unit dimension (region, cohort,
plan, segment); it finds none (`failure.json`:
`candidate_unit_columns = []`). Run logged as r-123d in `2-analyses/RUNS.csv`;
the machine-readable record lives in `failure.json` next to the script.

## Why the designs are not identifiable (technical)

With `treated ≡ 1`, the `treated` column duplicates the intercept and
`treated*post` duplicates `post` — two of the four DiD parameters vanish
before any model is fit (design matrix rank 2, 4 required). DiD's interaction
coefficient compares treated and control *changes*; with no control group,
that parameter does not exist in any estimable model. Synthetic control's
donor-pool optimization has an empty feasible set — zero donors means no
weights, not bad weights. Parallel trends is not "untestable" — there is no
second trend for it to be a statement about. The design that *did* work is
Bayesian ITS with placebo-in-time validation ([[i-3fa2]]), which constructs
the counterfactual from the treated unit's own pre-period.

## What data would make them work (in priority order)

1. **Geographic/market rollout with untreated regions** — outcome at unit-day
   grain; at least one genuinely untreated market; unit-level pre-period at
   least 2× the longest seasonal cycle (annual seasonality is plausible, so
   ≥2 years); no cross-market spillover (SUTVA); cluster SEs at market level.
   Unlocks classic DiD and, with several untreated markets, a
   synthetic-control donor pool.
2. **Staggered rollout across cohorts/plans** — treatment timing varying by
   group enables an event-study / Callaway–Sant'Anna design. Caveat: naive
   TWFE under staggered adoption is contaminated by forbidden comparisons
   (Goodman-Bacon); use heterogeneity-robust estimators.
3. **Price-cell randomization or a holdout market** — the gold standard;
   randomized price cells make the counterfactual assumption-free rather
   than modeled.

Anticipation note: the hike was announced ~1 week early ([[k-a1f4]]); an
announcement contaminates a control only if the control could *see* it — a
holdout market shielded from the announcement stays clean, but a control plan
visible on the same pricing page does not (spillover, not anticipation, is
the binding threat).

## Registry

Registered as canonical fact [[k-1231]] so future agents cite it rather than
rediscover it. A future analyst reaching for DiD on this dataset should hit
this memo in one lookup, not re-run the dead end. If the data layer ever
gains a unit dimension, mint a new ID for the new feasibility finding — do
not edit this one in place.
