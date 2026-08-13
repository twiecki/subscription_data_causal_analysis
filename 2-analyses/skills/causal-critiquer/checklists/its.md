# Interrupted Time Series checklist

Apply on top of `universal.md`. ITS is assumption-heavy in a quiet way:
the counterfactual lives entirely inside the parametric model the analyst
chose. Most ITS failures are not about the math.

## Counterfactual model

- [ ] **Is the pre-period long enough to identify the components in the
  formula?** Rule of thumb: at least 2× the longest period you're trying
  to model (so for monthly seasonality, ≥24 months pre). Short pre-period
  + seasonal terms = unidentified.
- [ ] **Was the functional form of the trend chosen by residual diagnostics
  or by assumption?** If linear was picked without checking, that's a
  finding. If quadratic was picked because "more flexibility is better,"
  that's also a finding — it usually over-fits and over-attributes.
- [ ] **Does the model spec include seasonality at the relevant frequency?**
  Daily/weekly business → weekly DOW pattern. Calendar-driven outcomes →
  monthly seasonality. News-driven outcomes → external shock indicators.
  If seasonality is in the data and not the model, residuals will show it.

## Non-stationary denominators (and when they actually bias you)

- [ ] **If the outcome is a rate (`numerator / denominator`), is the
  denominator stable or exogenous?** A growing user base, an aging at-risk
  pool, an accumulating stock — the denominator can move for its own reasons.
- [ ] **Is the drift SMOOTH, and is it shared by the counterfactual?** This is
  the distinction that matters, and it is the one analysts get wrong. A *smooth*
  compositional drift present in both the pre-period and the (unobserved)
  counterfactual is **absorbed by the trend term and differences out of the
  effect — it is NOT a bias.** The trend is doing its job. Do not reject a
  well-fit result merely because a denominator drifts; that is a common way to
  talk yourself out of a real effect.
- [ ] **It biases the estimate only in two cases:** (a) the drift is *non-smooth*
  or changes shape at the boundary, so the trend can't extrapolate it; or (b) the
  *treatment itself* changes the denominator dynamics, so the post-period pool
  diverges from the counterfactual pool. If you claim composition bias, name
  which of these two you mean.
- [ ] **Check the SIGN and shape of the pre-trend before invoking an "artifact".**
  A textbook failure: asserting "the pool ages, so the rate falls mechanically"
  when the pre-period rate is actually *rising*. Plot the rate against the
  denominator and against time. If `corr(rate, denominator) > 0`, the
  aging-decline story is false on its face — drop it.
- [ ] **The decisive test is a placebo-in-time, not a mechanism argument.** If you
  suspect the trend is manufacturing the effect, put a fake intervention in the
  pre-period and refit. If placebo effects are ~0 while the real date is an
  outlier, the denominator drift is NOT driving your estimate — stop rationalizing
  and report the effect.
- [ ] **Is there a ratio-decomposition artifact?** For a rate, the reviewer should
  see the numerator, denominator / `subscriber_pool`, and rate on the same time
  axis with the intervention marked. This is the fastest way to catch a plausible
  but wrong composition story.

## Treatment-time issues

- [ ] **Anticipation**: do subjects know the treatment is coming?
  Pre-intervention behavior changes in the days/weeks before the
  treatment date contaminate the pre-period baseline. ITS that ignores
  this attributes anticipation-affected behavior to the counterfactual,
  biasing the estimate toward zero.
- [ ] **Delayed response / fade-in**: does the treatment take time to
  bite? An instantaneous step-change spec on a gradually-rolling-out
  treatment will under-attribute the effect.
- [ ] **Treatment-effect heterogeneity over the post period**: did the
  effect dissipate, accumulate, or change? Averaging over the post
  window can mask this. Show effect vs time-since-intervention.

## Inferential validity

- [ ] **Residual autocorrelation**: same units persist across days, so
  errors are correlated. OLS and Normal-iid likelihoods both assume
  independence — confidence intervals from such models are too narrow.
  Diagnose with Durbin-Watson or residual ACF; correct with HAC errors
  or an AR(1) likelihood.
- [ ] **Multiple-specification fishing**: how many specs did the analyst
  try before reporting the headline? "I tried 5 and reported the one
  that looked right" is p-hacking under another name. Pre-register the
  spec or report all of them.
- [ ] **Sensitivity to treatment-time choice**: does the estimate change
  if the treatment time is moved by ±2 weeks? Should be roughly stable;
  if not, the trend model is doing too much work.

## Plot checks

- [ ] **Is the observed vs counterfactual plot showing a *credible*
  counterfactual?** If the projection visually diverges from the
  pre-period trend before the intervention (no reason it should), the
  formula is misspecified.
- [ ] **Are diagnostic plots tied to specific hypotheses?** A residual ACF tests
  autocorrelation; a periodogram tests missed seasonality; a placebo sweep tests
  fake breaks; a boundary zoom tests anticipation. Generic EDA plots are not a
  substitute for hypothesis-driven diagnostics.
- [ ] **Are zero / baseline lines marked?** Without them, the visual
  effect size is easy to overstate or understate.
- [ ] **Is the rolling-mean smoothing consistent across plots?** Different
  smoothing windows on the same data can look like different stories.

## ITS-specific things people do wrong

- **Treating "the time series is noisy" as "the model is uncertain."**
  Noise and uncertainty are different. A noisy series can still pin down
  a precise effect; a clean series can leave huge model uncertainty.
- **Reporting a single point estimate.** ITS without an interval is half
  an answer.
- **Ignoring the question of whether the pre-period trend is *really*
  what would have continued.** Trend extrapolation is the single
  strongest assumption in any ITS; it deserves its own paragraph in
  the write-up.
- **Confusing ATE with ATT.** ITS estimates the effect on the actually-
  treated period and population. Generalizing to "the effect of price
  hikes in general" requires more than this design.
