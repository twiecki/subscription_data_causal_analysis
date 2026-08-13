# Business context — why these questions get asked

The data layer tells an agent what the numbers *are*. This file tells it
what they *mean* to the business — so it answers what was **meant**, not
just what was asked. Read this before any analysis (house rule, AGENTS.md).

## The business

A freemium subscription publisher (think NYT-style). Readers sign up free,
enter the **subscriber pool** (signed up, not yet paying), and some convert
to paid. Conversion is the growth engine; price × conversions is the
revenue engine. The two can move in opposite directions — and did.

## The intervention, and why

Subscription price +33% on 2026-04-01 ([[k-a1f4]]) — a deliberate revenue
bet, announced publicly about a week in advance. The announcement matters:
it created an **anticipation cohort** that locked the old price just before
the hike (this is why the guard window exists in the semantic layer, and
why revenue-per-conversion is below +33% early in the post period).

## Who asks, and what they mean

| who | asks | actually means | governed answer |
|---|---|---|---|
| Growth | "did the hike hurt conversion?" | the causal effect on [[k-77b0]], not the raw pre/post diff | [[i-3fa2]] |
| Finance / board | "was it worth it?" | net **revenue**, not conversion — the decision metric | [[i-b7d3]] |
| Support / comms | "are users angry?" | out of scope for this repo — no sentiment data |  |

Ambient references you will hear: **"the hike"** = the 2026-04-01 change
([[k-a1f4]]); **"the pool"** = `subscriber_pool` as defined in the semantic
layer; **"the spike"** = the late-March anticipation bump (not organic
growth, not a data error).

## Decision frame

The effect is not the decision. Conversion went down AND the bet paid off
([[i-b7d3]]) — an analysis that stops at the conversion effect answers the
wrong question. Carry uncertainty into the revenue quantity before anyone
decides about rolling back the price.
