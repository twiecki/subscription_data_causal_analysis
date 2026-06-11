A subscription business raised its price by ~33% on **2026-04-01** without
running an A/B test. Estimate the causal effect of the price increase on the
daily subscription conversion rate from observational data, and deliver an
analysis a decision-maker can trust.

Data, provided in `/root/`:

- `daily_aggregates_intervention.csv` — daily grain, one row per calendar day
  (2024-04-01 … 2026-09-30), columns:
  - `date` — calendar day
  - `subscriber_pool` — users signed up but not yet subscribed (converters
    leave the pool, so the denominator drifts over time)
  - `signups` — new users that day
  - `conversions` — subscriptions started that day
  - `conv_rate` — `conversions / subscriber_pool`, the outcome of interest
  - `post` — 1 from 2026-04-01 onward
- `metric-contract.yml` — the governed definition of the outcome metric and
  the validation standards for analyses of it. Read it before touching the
  data, and honor it.

Deliverables, written into `/root/`:

1. `result.json` with keys:
   - `effect_pct` — your headline percentage effect of the price increase on
     the daily conversion rate (signed: a drop is negative)
   - `estimand` — what you estimated, in one sentence
2. `memo.md` — your conclusion, method, and the caveats a decision-maker needs
3. `analysis.py` — a runnable script that reproduces your numbers from the
   CSV; all analysis code must live in this file
4. Any further artifacts the metric contract requires.
