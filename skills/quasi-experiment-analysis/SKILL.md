---
name: quasi-experiment-analysis
description: >-
  Estimate the causal effect of an intervention from observational time-series
  data using quasi-experimental methods (interrupted time series, difference-in-
  differences, synthetic control), e.g. with CausalPy. Use this whenever you are
  measuring the impact of a treatment, policy, launch, price change, or any
  before/after intervention and want a defensible effect estimate rather than a
  naive pre/post comparison. Triggers on "what was the effect of X", "did the
  intervention work", "interrupted time series", "ITS", "diff-in-diff",
  "synthetic control", "CausalPy", "measure intervention/treatment/policy impact",
  or any counterfactual "what would have happened without X" question. Consult it
  even when the modeling looks routine — the failure modes here are silent and
  produce confident, wrong answers.
---

# Quasi-Experimental Effect Estimation

You are estimating a causal effect from data where you could not randomize: you
only observe what happened before and after an intervention. Every method here
(interrupted time series, difference-in-differences, synthetic control) works the
same way underneath:

> **effect = observed outcome − predicted counterfactual**

The whole analysis rides on one fragile object: the **counterfactual**, the model
of "what would have happened anyway," fit on pre-intervention (and/or control)
data and extrapolated into the treated period. If that extrapolation is not
credible, the effect estimate is fiction — and the tooling will not tell you. It
will hand you a tight interval, a p-value, and a confident sign on top of a
counterfactual that explains nothing.

**The single most dangerous mistake is not a wrong formula. It is talking
yourself out of a correct, well-fit, surprising result** with a plausible-sounding
mechanism. Guard against that with an *objective check* (a placebo-in-time), not
with more reasoning. The traps below are ordered by how often they actually bite,
and they were distilled from a blind run that fell into the first one and an
independent validator that caught it.

## Workflow

Do these in order. Most bad estimates come from skipping 1–4 and jumping to 5.

1. **Understand the outcome's data-generating process.** What *is* this number —
   a count, a rate, a ratio? What generates its variance, and does anything
   mechanical drive its trend?
2. **Plot the raw series — and decompose ratios.** Plot the outcome over the full
   window with the intervention marked; for a ratio, plot numerator and
   denominator separately too. Look for pre-treatment spikes, level shifts,
   changing variance.
3. **Identify trend and seasonality empirically — don't assume the basis.**
   Measure the seasonal structure on the pre-period (periodogram / STL / residual
   ACF): what is the period, and is the cycle smooth? (Trap 4.)
4. **Fit the counterfactual and gate on its residual structure** — not on R²
   (Trap 2).
5. **Read the effect** — point estimate, interval, sign.
6. **Stress-test before you trust OR reject it.** Run a **placebo-in-time** first
   (it decides Traps 1 and 5), then alternative pre-windows and functional forms.
7. **Report with the assumptions attached**, not just the number.

## Diagnostic tools and widgets

Use executable diagnostics as evidence, not as decoration. The analysis agent may
create them while fitting; the critic agent should request or create them when
evidence is missing. Good diagnostics are small, named, and targeted at a specific
assumption:

- **Residual gate dashboard**: observed vs. counterfactual, pre-period residuals,
  residual ACF, and residuals by calendar position.
- **Seasonality probe**: periodogram / STL / Fourier-term comparison before
  choosing `C(dow)` or smooth seasonal terms.
- **Placebo explorer**: fake treatment dates across the pre-period, with the real
  treatment effect plotted against the placebo distribution.
- **Ratio decomposition**: outcome, numerator, denominator / `subscriber_pool`,
  and the intervention boundary on the same time scale.
- **Anticipation zoom**: a boundary-window view that shows whether behavior moved
  before the official treatment date.

In marimo, prefer a compact dashboard or AnyWidget that lets the human inspect the
load-bearing assumption directly. Treat generated tools as **run artifacts** by
default. Promote a tool into this skill only after it repeatedly catches a real
failure mode, has stable inputs/outputs, and is easier to reuse than to regenerate.

## The traps (ordered by how often they bite)

### Trap 1 — Talking yourself out of a real, well-fit, surprising effect

The most human failure, and the one that actually fired in the run this skill was
built from. You get a confident effect that **surprises you** — wrong sign, too
big, against your prior — and you invent a mechanism that nulls it out ("oh,
that's just a composition artifact") and discard a result that was correct.

A surprising-but-well-fit effect is a prompt to **investigate**, not to
**rationalize**. The discipline:

- **Run a placebo-in-time before you reject it** (see Validate). If fake
  pre-period interventions give ~0 while the real date is an outlier, the effect
  is real and your "artifact" story is wrong. An objective check beats a
  narrative — *you cannot reason your way out of a passing placebo.*
- **Name the confounder bucket.** Smooth confounders (secular trend, seasonality,
  slow composition drift) are **absorbed by a trend + seasonal counterfactual by
  design** — if you modeled them, "it's just the trend" is not a valid dismissal.
  Rough confounders (anticipation, announcements, one-off shocks) are the ones
  that actually bias; those are worth chasing.
- **Check the direction of your own mechanism.** The blind run claimed "the pool
  ages, so the rate falls mechanically" — but the pre-period rate was *rising*.
  A mechanism that predicts the opposite of what the data show is not an
  explanation. Plot it before you believe it.

### Trap 2 — Judging the counterfactual by R² instead of residual structure

R² is the wrong gate in **both** directions.

- A model that explains ~nothing pre-intervention (R² ≈ 0) is a flag to **go look
  at the residuals**, not a number to threshold on. It usually means the *mean
  structure* (trend, seasonality) is missing — fix that.
- But once the fit is non-trivial, **R² magnitude is irrelevant to bias.** A low
  R² often just means **irreducible noise** (e.g. binomial noise in a small-count
  daily rate) while the mean structure — the only thing the counterfactual depends
  on — is captured fine. A model with R²=0.12 and clean residuals gives an
  excellent estimate; one with R²=0.9 and a trending residual gives a terrible one.

The right diagnostic is always **residual structure**. Check three kinds of
leftover structure, thoroughly:

- **Trend**: residual vs. time correlation ≈ 0.
- **Short-range autocorrelation**: lag-1 (and a few low lags) ≈ 0.
- **Leftover periodicity**: residual ACF at *seasonal* lags ≈ 0, or regress the
  residuals on candidate seasonal terms and confirm they explain ~nothing.
  **Lag-1 ≈ 0 does NOT prove the seasonality is right** — an annual cycle leaves
  lag-1 ≈ 0 while still contaminating the counterfactual. This is the hole that
  lets Trap 4 through.

### Trap 3 — Anticipation and pre-treatment contamination

If subjects can react *before* the official intervention date — an announced price
increase, a pre-registration window, a leaked launch — the days just before the
cutoff are **contaminated by the treatment itself.** Fitting them into the "pre"
period bends the baseline toward the anticipation, biasing the extrapolated
counterfactual (often *overstating* the effect; or, if the run-up is misread as
"post sits on baseline," hiding it).

Telltale sign: a spike or dip in the last days/weeks before the cutoff that
doesn't match the longer baseline. Defenses: **exclude a guard window** of
pre-treatment periods from the fit, or model the anticipation explicitly. A
late-pre run-up is evidence *for* a real effect, not against it.

### Trap 4 — Choosing a seasonal basis by habit instead of identifying it

Seasonality must be **measured, then matched** — not assumed.

- **Wrong basis.** A smooth cycle (e.g. an annual sinusoid) modeled with
  categorical dummies (`C(month)`) is an overparameterized step-function proxy:
  ~11 noisy parameters for 2 smooth ones. Even when it absorbs the cycle in-sample
  it **extrapolates as jagged steps into the post period** — and a counterfactual
  *is* an extrapolation. Prefer **Fourier terms** (`sin`/`cos` at the seasonal
  period, plus a harmonic only if a residual check demands) for smooth cycles.
- **Spurious terms.** Adding day-of-week "because it's daily data" or monthly
  dummies "because business data has seasonality," without testing, drops junk
  regressors into the counterfactual. Insignificant terms widen intervals and
  alias with the trend and the treatment window — they are not "safe controls."

Defenses: identify the period/shape first (Step 3); **test every seasonal term for
joint significance** and drop the ones that aren't real; verify with the residual
gate (Trap 2) that no seasonal structure is left over. **When your docs or data
dictionary already state the functional form** (e.g. the library example uses
`y ~ 1 + sin_annual + cos_annual`), use it — don't fetch the reference and then
pattern-match back to your default.

### Trap 5 — Drifting denominators: usually absorbed, rarely the bias

A ratio outcome (rate = numerator / denominator) makes people nervous: a growing
user base, an aging at-risk pool where converters leave and "survivors" remain, an
accumulating stock. The nervousness is mostly misplaced.

- **A *smooth* drift shared by the pre-period and the counterfactual is absorbed
  by the trend term and differences out.** It is NOT a bias. This is the trap
  inside the trap: the worry is real-sounding but, once you have a trend term, the
  drift is handled. Rejecting a result because "the denominator drifts" is Trap 1
  wearing a statistics costume.
- **It bites only when** (a) the drift is *non-smooth* / changes shape at the
  boundary (the trend can't extrapolate it), or (b) the *treatment* changes the
  denominator dynamics (the post pool diverges from the counterfactual pool).
- **How to tell:** check the **sign and shape** of the pre-trend (if `corr(rate,
  denominator) > 0`, the "aging decline" story is already false), and run a
  **placebo-in-time** (if it's null, the drift isn't manufacturing your effect).

### Trap 6 — Model family is about precision, not sign

Matching the model family to the data-generating process is good practice, but
know what it buys you:

- **Counts / rates** → Poisson or Binomial with an **exposure/denominator term**
  is the principled choice; a Gaussian fit on the raw rate is heteroscedastic and
  lets noisy low-exposure periods distort the fit.
- **But this is a precision/efficiency issue, not a sign-flip issue.** A
  binomial-with-exposure model *tightens* the estimate; it does not reverse it.
  **Do not let a correct secondary critique ("you used Gaussian on a rate")
  launder an incorrect primary conclusion ("so the effect isn't real").** Use the
  alternative family as a robustness check, not as a reason to distrust a sign that
  a placebo already confirmed. Trimming a wildly heteroscedastic early period (tiny
  exposure) is a reasonable Gaussian band-aid for the same problem.

## Validate (this is where the answer is decided)

A point estimate without a stress test is a guess with decimal places. The first
one is not optional:

- **Placebo-in-time (decisive).** Put a fake intervention at several dates *inside*
  the pre-period and refit. A well-specified design gives ~0 there. If the real
  date's effect sits outside the spread of placebo effects, it is real — and this
  *overrides* any mechanism argument for dismissing it (Traps 1, 5). If placebos
  are themselves large, your counterfactual is biased.
- **Pre-window sensitivity**: refit dropping the earliest (noisiest) data and the
  anticipation guard window. The estimate should be stable; if it swings, say so.
- **Functional-form sensitivity**: linear vs. quadratic trend, with/without
  seasonality. Report the range, not a single hero number.
- **Eyeball the counterfactual**: plot observed vs. predicted across the whole
  window. The predicted line should hug the data pre-intervention and diverge
  (or not) after.

## Match the model (quick reference)

| Outcome type | Reasonable default | Note |
|---|---|---|
| Continuous, roughly Normal | Gaussian linear ITS, trend + seasonality | — |
| Count with stable exposure | Poisson/NegBin, exposure offset | Gaussian works for the sign; this tightens it |
| Rate from a fixed denominator | Binomial / logit | Gaussian on the proportion is fine for the sign |
| Rate from a drifting `subscriber_pool` / denominator | Gaussian with a trend term is usually fine (Trap 5); Binomial-with-exposure as a robustness check | the drift is absorbed, not a bias, if smooth |

The counterfactual model almost always needs an explicit **time trend** and
**seasonality** — the library will not invent them; add the columns and put them in
the formula. Identify the seasonal period first (Step 3) and prefer **Fourier
terms** for smooth cycles; keep only terms that test as real (Trap 4).

## Reporting

State the effect **with its assumptions attached**: the estimate and interval, the
counterfactual model and its *residual* check, the **placebo result**, which
confounders are absorbed vs. unaddressed, and the headline caveat that this is
quasi-experimental — the causal claim rests on the counterfactual being credible,
not on randomization. A naive pre/post difference is *not* an acceptable fallback;
it ignores trend, seasonality, and anticipation, and routinely gets both the
magnitude and the sign wrong.

## Tooling note (CausalPy)

CausalPy implements these designs; the library is incidental, the discipline above
is not.

- `cp.InterruptedTimeSeries(data, treatment_time, formula, model)` — `data` needs a
  datetime index; `treatment_time` is a `pd.Timestamp` on that index; the `formula`
  must reference columns **you** created for trend (`t`) and seasonality (`sin1`,
  `cos1`, …). CausalPy does not auto-generate them.
- Models: `cp.pymc_models.LinearRegression(sample_kwargs={...})` (Bayesian, gives a
  posterior/HDI) or a sklearn backend via `cp.create_causalpy_compatible_class`
  (fast, point estimate). LinearRegression is **Gaussian** — see Trap 6.
- After fitting: look at `result.score` (pre-period R²) only as a *symptom*
  (Trap 2), eyeball `result.plot()`, then `result.effect_summary()` for the
  estimate. `effect_summary()` reports "significant" effects regardless of whether
  the counterfactual fits — that confidence is not evidence; the placebo is.
- DiD and synthetic control live in the same API (`cp.DifferenceInDifferences`,
  `cp.SyntheticControl`) and obey the same traps, with the added requirement that
  control units be genuinely comparable and unaffected by the treatment.
- See the `causalpy-library` skill for API gotchas (e.g. `cp.skl_models.Linear
  Regression` does not exist; `did.plot()` can crash on recent matplotlib).

## Ship the decision, not just the effect

*(added after the revenue-impact run — the effect is not the decision)*

A causal effect on a proximate metric (conversion, clicks, churn) is an
input, not an answer. Before shipping, propagate the effect **posterior**
into the quantity the decision actually uses (revenue, cost, margin) —
by Monte-Carlo over the posterior, never point-times-point. Cite the
upstream insight ID as the input; register the business-level finding as
its own insight. A stakeholder should never have to do this arithmetic
in their head.
