# Price-hike effect on conversion — validated memo

**Claim [[i-3fa2]]:** the 2026-04-01 price increase ([[k-a1f4]]) reduced the
daily conversion rate ([[k-77b0]]) by **~15.6%** (95% HDI [-19.2%, -12.4%]).

Counterfactual: Bayesian interrupted time series, linear trend, 30-day
burn-in; specification selected by pre-period backtest. Validation:
placebo-in-time (real date z = -2.1, fake dates ~0), six-specification
sensitivity sweep (-11.9%..-16.7%), sampler diagnostics clean.

An earlier blind run shipped the opposite, since-superseded claim
[[i-c518]] — see `blind-run-claim.md` for why it was refuted, and the
course's Session 2 for the full story.
