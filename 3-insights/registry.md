# Insights registry — one fact, one place

Every insight and canonical fact is an **artifact with a stable ID**. IDs are
rolled, not counted (sparse hex space: a typo lands on nothing and gets
flagged by `3-insights/checks/integrity.py`, instead of silently hitting a valid
neighbor). The ID names the *claim*; the `sha256_12` column binds it to the
current bytes of its source (`--rebind` after editing a source on purpose).
Everything else in this repo **cites these IDs** instead of restating values.
Refuted insights are superseded, never edited in place; retired IDs live in
`alias.tsv` forever (append-only — CI enforces it). Mint new IDs with
`python 3-insights/mint_id.py [i|k|r]`; the `i-`/`k-`/`r-` namespace is
**reserved** — never hand-write lookalike tokens in documents.

| id | status | claim | source | evidence | sha256_12 |
|---|---|---|---|---|---|
| k-a1f4 | canonical | Intervention: subscription price +33% on 2026-04-01 | 1-data/semantic-layer/conv_rate.yml | governed contract, v0.2.0 | 877bf1bb40a2 |
| k-77b0 | canonical | Governed outcome: `conv_rate = conversions / subscriber_pool`, daily grain | 1-data/semantic-layer/conv_rate.yml | governed contract, v0.2.0 | 877bf1bb40a2 |
| i-3fa2 | active | The price hike reduced daily conversion by ~15.6% (95% HDI [-19.2, -12.4]) | 2-analyses/price-hike/memo.md | placebo-in-time z=-2.1 at real date; 6-spec sensitivity -11.9%..-16.7% | 9cfe1c856162 |
| i-c518 | superseded-by:i-3fa2 | "The drop is a composition artifact; little or no real effect" | 2-analyses/price-hike/blind-run-claim.md | REFUTED: mechanism has the wrong sign; placebo sweep ~0 at fake dates | 12266627b5e9 |
| k-099a | canonical | Governed metric: `signups` = daily gross new free registrations; inflow term of the pool identity | 1-data/semantic-layer/signups.yml | governed definition, v0.1.0 | 7c273d017293 |
| i-c64a | active | The price hike produced no detectable change in signup inflow: -1.55%, placebo-calibrated 95% CI [-4.92, +1.81]; bounded at +/-4.81% MDE | 2-analyses/signups-inflow/memo.md | validated null: placebo-in-time z=-1.20 over 12 fake dates (4/12 as extreme), ROPE +/-5% P=0.978, Poisson agrees -1.53% | f04014314048 |
