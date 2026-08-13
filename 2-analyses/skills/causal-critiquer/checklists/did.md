# Difference-in-Differences checklist

Apply on top of `universal.md`. DiD identification rests on parallel trends:
the control unit's trajectory is what the treated unit *would have done*
absent treatment. Most DiD failures are not about the regression — they're
about whether parallel trends actually holds.

## Parallel trends

- [ ] **Is parallel trends shown in a plot, not just asserted?** A
  side-by-side time series of treated and control over the pre-period
  with both trajectories overlaid. If they're visibly not parallel,
  the design is broken before the regression runs.
- [ ] **How long is the pre-period?** One pre-period observation is a
  level difference, not a trend test. You need enough pre-data to
  *see* the parallel trends.
- [ ] **Has parallel trends been tested formally?** Event-study
  specification with leads — if the pre-treatment leads are jointly
  zero, parallel trends has empirical support. If they trend, you've
  detected non-parallelism.
- [ ] **What if parallel trends fails?** Honest answer: report it, don't
  hide it. Options: time-varying controls, synthetic control, or
  switch designs.

## Anticipation

- [ ] **Could the control unit also have anticipated the treatment?**
  Even if only the treated received treatment, a control that anticipated
  it (different reaction) violates SUTVA on the control side.
- [ ] **Did the treated unit anticipate?** Pre-treatment behavior change
  in the treated group inflates the pre-baseline; standard DiD attributes
  this to the trend rather than to anticipation.

## SUTVA

- [ ] **No spillover from treated to control?** If treatment status affects
  control units (e.g., subscriber moves to control market because of
  price hike in treated), the contrast is contaminated.
- [ ] **Stable treatment over time?** If the treatment intensity varied
  during the post period, DiD's single coefficient summarizes a moving
  target.

## Composition of treated vs control

- [ ] **Are the units comparable on observable pre-treatment characteristics?**
  Engagement mix, baseline rate, size, seasonality patterns. If they're
  systematically different, "parallel trends" may hold by accident
  rather than by structure.
- [ ] **Did the composition of either group change during the window?**
  E.g., new users joining only the treated market mid-window. The
  contrast is no longer apples-to-apples.

## Estimator specifics

- [ ] **Are standard errors clustered?** Repeated observations from the
  same units violate iid; unclustered SEs are too narrow. Cluster at
  the unit-of-treatment level (market, firm, region).
- [ ] **Two-way fixed effects with staggered adoption**: the Goodman-Bacon
  decomposition warning applies — TWFE with heterogeneous timing can
  give weird weights. If adoption is staggered, prefer event-study or
  the recent-DiD estimators (Callaway-Sant'Anna, de Chaisemartin,
  Sun-Abraham).

## Plot checks

- [ ] **Is the pre-period overlap shown?** The treated and control series
  should be visible together with the intervention line marked. A plot
  that hides one or the other is a tell.
- [ ] **Is the counterfactual reconstructed?** Show "control trajectory
  shifted up by the pre-gap" as the implied treated counterfactual.
  The visual gap is the estimated effect; absence of this plot makes
  the regression coefficient less interpretable.

## DiD-specific things people do wrong

- **Treating DiD as a one-time-difference test.** It's a panel design;
  one pre-observation per unit isn't enough.
- **Reporting "the DiD estimate" without showing the underlying series.**
  Reviewers should see the four cell means at minimum: (pre, treated),
  (post, treated), (pre, control), (post, control).
- **Ignoring functional-form choice.** Conv_rate vs log(conv_rate) vs
  conversions-count gives different DiD estimates and answers different
  causal questions. Pick one with reason.
- **Calling Synthetic Control "a DiD with weights."** It's not — different
  identification assumptions. Don't conflate.
