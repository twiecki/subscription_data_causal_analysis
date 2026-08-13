# Universal causal-analysis checklist

Items that apply to *any* causal claim, regardless of design. Walk these
first; design-specific items go on top.

## Estimand vs estimator

- [ ] **Is the estimand named?** ATE / ATT / CATE / LATE / ITT? On what scale
  (level, ratio, log-odds)? Over what population? If the analyst can't say,
  flag it — there is no such thing as "the causal effect" without specifying
  whose, of what, on what.
- [ ] **Does the estimator target the named estimand?** A common silent error:
  estimand is "the average effect on the treated population" but the
  estimator returns "the average effect on the marginal at-risk pool at the
  time of intervention" — they differ when composition shifts.
- [ ] **What scale is the answer in?** Relative drop? Absolute drop on a
  small probability? Per-thousand? Confused units lead to confused decisions.

## Causal language calibration

- [ ] **Does the conclusion outrun the design?** Watch for "caused", "drove",
  "led to" attached to an estimate from a design that only supports
  association. Conversely, watch for hedging on a design that *does* support
  causation (you earned the strong language; use it).
- [ ] **Is there a clear counterfactual statement?** "If we had not done X,
  Y would have been Z." If the analysis can't produce this sentence,
  it's not causal yet.

## Uncertainty: two kinds

- [ ] **Estimation uncertainty** (given the model is right): is there an
  interval / posterior / standard error? Point estimates alone are
  decision-hostile.
- [ ] **Model uncertainty** (the model might be wrong): are alternative
  specifications shown? Sensitivity to functional form, control choice,
  bandwidth, etc.? A tight HDI from a single spec is overconfident.
- [ ] **Are these two reported separately?** Conflating them is common and
  misleading. "We're 95% confident the effect is in [a, b]" usually means
  "*if our model is right*, we're 95% confident."

## Robustness

- [ ] **Has the headline number been re-derived under a different specification?**
  If switching from linear to quadratic, or adding/dropping a covariate, or
  changing the bandwidth, moves the estimate by >25%, that's a finding.
- [ ] **Is there a placebo or falsification check?** Run the same analysis
  on a period or outcome where the effect *should* be zero. If you find
  one anyway, your design is broken.
- [ ] **Was data preprocessing tested for sensitivity?** Filtering, winsorizing,
  outlier removal, threshold choices. Each is a knob; each needs a sweep.

## Mechanism / heterogeneity

- [ ] **Is the average effect masking heterogeneity?** A null average can
  hide opposite-sign subgroup effects. Conversely, a big average can be
  driven by a small heterogeneous subgroup.
- [ ] **What's the proposed mechanism?** A causal estimate without a story
  about *why* invites bad inference about generalization. "Price went up,
  conversion went down — by what mechanism? Price sensitivity?
  Sticker shock? Cancellation of marketing?"

## Decision implication

- [ ] **Does the estimate translate to an action?** "The effect was −0.0002
  per day" is not actionable unless someone can turn it into "this costs
  us $X/year" or "we should/shouldn't do Y."
- [ ] **Is the uncertainty wide enough to change the decision?** If yes, the
  honest answer is "we don't know enough to act, gather more data."
- [ ] **What's the cost of being wrong?** A small effect with high
  asymmetric downside is a different decision than the same effect with
  symmetric stakes.

## Reproducibility

- [ ] **Is the random seed pinned?** If results depend on a single
  simulation / bootstrap / MCMC seed, that's a hidden source of variance.
- [ ] **Could a second analyst rerun this from the same data and get the
  same number?** Often the answer is no, because of undocumented
  filtering, manual cleanups, or version drift in the libraries.
