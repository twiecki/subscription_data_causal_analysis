#!/usr/bin/env python3
"""Deterministic checks for a fitted causal-inference analysis.

This is the *hard-check layer* of the causal-critiquer skill. It produces an
objective pass/fail signal so the critique is grounded in evidence, not in the
analyzing agent's own opinion of its work (LLM self-review degrades quality:
arXiv 2310.01798). Run this FIRST, then critique against the JSON it prints.

It checks three things that do not need judgment:
  1. MCMC sanity        — R-hat, divergences, ESS (ArviZ).
  2. Placebo-in-time    — shift the "intervention" into the pre-period; the
                          effect should be ~0. A non-zero placebo effect means
                          the design is detecting noise/trend, not the treatment.
  3. Prior sensitivity  — does the conclusion survive a different prior/spec.

Usage (the agent wires these to the live analysis objects):

    # A) you have a fitted CausalPy experiment + its idata
    from run_checks import run_all
    print(run_all(experiment=its, idata=its.idata, refit=refit_fn))

    # B) from the command line against a pickled experiment
    python run_checks.py --experiment its.pkl

`refit_fn(treatment_time) -> experiment` lets the placebo check refit at a fake
date without this script knowing your data-loading code. If you can't provide
it, the placebo check is reported as "skipped" rather than guessed.

Output: a JSON list of {check, passed, value, threshold, evidence}. `passed` is
null when a check could not be run (missing dependency / inputs) — never faked.
"""
from __future__ import annotations

import json
import sys


def _result(check, passed, value=None, threshold=None, evidence=""):
    return {"check": check, "passed": passed, "value": value,
            "threshold": threshold, "evidence": evidence}


def check_mcmc(idata, rhat_max=1.01, ess_min=400):
    """R-hat, divergences, ESS from an ArviZ InferenceData."""
    try:
        import arviz as az
    except ImportError:
        return [_result("mcmc", None, evidence="arviz not installed")]
    out = []
    try:
        rhat = float(az.rhat(idata).to_array().max())
        out.append(_result("convergence:r_hat", rhat <= rhat_max, round(rhat, 4),
                            rhat_max, "max R-hat across parameters"))
    except Exception as e:  # noqa: BLE001
        out.append(_result("convergence:r_hat", None, evidence=f"unavailable: {e}"))
    try:
        div = int(idata.sample_stats["diverging"].sum())
        out.append(_result("convergence:divergences", div == 0, div, 0,
                            "total divergent transitions"))
    except Exception as e:  # noqa: BLE001
        out.append(_result("convergence:divergences", None, evidence=f"unavailable: {e}"))
    try:
        ess = float(az.ess(idata).to_array().min())
        out.append(_result("convergence:ess_bulk", ess >= ess_min, round(ess, 1),
                            ess_min, "min bulk ESS across parameters"))
    except Exception as e:  # noqa: BLE001
        out.append(_result("convergence:ess_bulk", None, evidence=f"unavailable: {e}"))
    return out


def check_placebo_in_time(experiment=None, refit=None, fake_offsets=(-90, -180)):
    """Effect at a fake (pre-period) intervention date should be ~0.

    Prefers CausalPy's built-in ``cp.checks.PlaceboInTime`` (hierarchical null +
    Bayesian assurance). Falls back to refitting at shifted dates via ``refit``.
    """
    # Preferred: CausalPy's own check (verify your installed version exposes it).
    try:
        import causalpy as cp
        if experiment is not None and hasattr(cp, "checks") and hasattr(cp.checks, "PlaceboInTime"):
            res = cp.checks.PlaceboInTime().run(experiment)
            p = getattr(res, "p_effect_outside_null", None)
            passed = None if p is None else bool(p < 0.95)
            return [_result("placebo_in_time", passed, p, 0.95,
                            "cp.checks.PlaceboInTime: P(effect outside status-quo null)")]
    except Exception as e:  # noqa: BLE001
        # fall through to manual version
        manual_note = f"cp.checks.PlaceboInTime unavailable ({e}); using manual refit"
    else:
        manual_note = "cp.checks.PlaceboInTime not found; using manual refit"

    if refit is None:
        return [_result("placebo_in_time", None,
                        evidence="no refit() provided and cp.checks.PlaceboInTime unavailable — "
                                 "skipped, do NOT assume it passed")]
    rows = []
    for off in fake_offsets:
        try:
            exp = refit(off)  # refit at a fake date `off` days into the pre-period
            hdi = _effect_hdi(exp)
            contains_zero = hdi is not None and hdi[0] <= 0 <= hdi[1]
            rows.append(_result(f"placebo_in_time@{off}d", contains_zero, hdi, "94% HDI ∋ 0",
                                f"{manual_note}; placebo effect HDI {hdi} should contain 0"))
        except Exception as e:  # noqa: BLE001
            rows.append(_result(f"placebo_in_time@{off}d", None, evidence=f"refit failed: {e}"))
    return rows


def check_prior_sensitivity(experiment=None):
    """Does the effect survive an alternative prior/spec? (cp.checks.PriorSensitivity)"""
    try:
        import causalpy as cp
        if experiment is not None and hasattr(cp, "checks") and hasattr(cp.checks, "PriorSensitivity"):
            res = cp.checks.PriorSensitivity().run(experiment)
            return [_result("prior_sensitivity", None, str(res)[:300], None,
                            "compare effect summaries across priors — flag if sign/magnitude flips")]
    except Exception as e:  # noqa: BLE001
        return [_result("prior_sensitivity", None, evidence=f"unavailable: {e}")]
    return [_result("prior_sensitivity", None,
                    evidence="cp.checks.PriorSensitivity not found — rerun with a different prior manually")]


def _effect_hdi(experiment):
    """Best-effort 94% HDI of the causal effect from a fitted CausalPy experiment."""
    try:
        import arviz as az
        import numpy as np
        # CausalPy stores post-intervention impact; names vary by version/design.
        for attr in ("post_impact", "causal_impact", "impact"):
            obj = getattr(experiment, attr, None)
            if obj is not None:
                arr = np.asarray(obj).reshape(-1)
                lo, hi = az.hdi(arr, hdi_prob=0.94)
                return [round(float(lo), 6), round(float(hi), 6)]
    except Exception:  # noqa: BLE001
        return None
    return None


def run_all(experiment=None, idata=None, refit=None):
    results = []
    if idata is not None:
        results += check_mcmc(idata)
    results += check_placebo_in_time(experiment=experiment, refit=refit)
    results += check_prior_sensitivity(experiment=experiment)
    return json.dumps(results, indent=2)


if __name__ == "__main__":
    import argparse
    import pickle

    ap = argparse.ArgumentParser(description="Deterministic causal-analysis checks → JSON")
    ap.add_argument("--experiment", help="path to a pickled fitted CausalPy experiment")
    args = ap.parse_args()

    exp = None
    idata = None
    if args.experiment:
        with open(args.experiment, "rb") as fh:
            exp = pickle.load(fh)
        idata = getattr(exp, "idata", None)
    if exp is None and idata is None:
        sys.stderr.write(__doc__)
        sys.exit("\nNothing to check: pass --experiment, or import run_all() and "
                 "pass the live experiment/idata objects.\n")
    print(run_all(experiment=exp, idata=idata))
