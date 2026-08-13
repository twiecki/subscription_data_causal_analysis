# Revenue impact of the price hike — memo

**Claim [[i-b7d3]]:** the price hike **increased** expected daily
subscription revenue by **~+12.2%** (95% interval [+7.7%, +16.7%];
P(uplift > 0) ≈ 1.0), despite the conversion drop.

Inputs, cited not restated: the conversion effect posterior [[i-3fa2]], the
governed intervention [[k-a1f4]] (+33% price), and the governed outcome
definition [[k-77b0]]. Computation: Monte-Carlo propagation of the effect
posterior into `(1 + price_uplift) * (1 + effect) - 1`, over the post
period from the derived data layer (`2-analyses/revenue-impact/analysis.py`,
seeded).

**Decision read:** the conversion loss [[i-3fa2]] is more than offset by
the higher price. Reverting the hike is not supported by this evidence.

Caveats: assumes constant price mix and no differential churn among
converters post-hike; horizon ends 2026-09-30 — do not extrapolate
([[i-3fa2]]'s caveats carry through).
