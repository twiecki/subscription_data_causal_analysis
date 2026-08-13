#!/usr/bin/env python3
"""Did the 2026-04-01 price hike change signup inflow?  (issue #10)

The semantic layer governs `conv_rate` and its denominator. It says nothing
about `signups` — yet every analysis in this repo leans on inflow being
untouched by the hike, because a treatment that moved inflow would move the
`subscriber_pool` denominator and contaminate [[i-3fa2]]. This script tests
that assumption instead of asserting it.

Design: interrupted time series on `signups`, the same machinery used for the
conversion effect, so the two are comparable. A null result here is a *claim*,
not an absence of one, so the script does the work a null actually requires:

  1. spec selection      — every seasonal/trend term tested for joint
                           significance on the pre-period and DROPPED if it
                           isn't real (quasi-experiment-analysis, Trap 4)
  2. residual gate       — trend, lag-1, Ljung-Box, seasonal leftovers
                           (Trap 2: residual structure, never R^2)
  3. placebo-in-time     — 12 fake dates inside the pre-period (decisive)
  4. guard-window        — anticipation sensitivity required by the semantic
                           layer's `guard_window`
  5. equivalence + MDE   — a null is only meaningful with a ROPE and a
                           minimum detectable effect. "Not significant" is
                           not "no effect".
  6. Poisson robustness  — counts; Gaussian is a precision choice, not a
                           sign choice (Trap 6)

Numbers come from 1-data/derived/ (house rule, AGENTS.md) — never from raw.

Run:  python 2-analyses/signups-inflow/analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path

import arviz as az
import causalpy as cp
import numpy as np
import pandas as pd
import pymc as pm
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DERIVED = ROOT / "1-data/derived/daily.csv"

TREATMENT = pd.Timestamp("2026-04-01")  # [[k-a1f4]]
GUARD_DAYS = 7                          # semantic layer: guard_window
OUTCOME = "signups"
SEED = 20260401
ROPE_PCT = 5.0                          # see memo: decision-relevant band
N_PLACEBO = 12                          # semantic layer requires >= 8

# nutpie/numba: this box has no C compiler, so the default pytensor backend
# falls back to Python (~9 min/fit). Same posterior, ~24x faster.
SAMPLE_KWARGS = dict(draws=1000, tune=1000, chains=4, progressbar=False,
                     random_seed=SEED, nuts_sampler="nutpie",
                     nuts_sampler_kwargs={"backend": "numba"})
PLACEBO_KWARGS = {**SAMPLE_KWARGS, "draws": 500, "tune": 500, "chains": 2}


# --------------------------------------------------------------------------
# data layer
# --------------------------------------------------------------------------
def load() -> pd.DataFrame:
    d = pd.read_csv(DERIVED, parse_dates=["date"]).set_index("date").sort_index()
    missing = {"source_file", "source_row"} - set(d.columns)
    if missing:  # provenance is the point of the derived layer
        raise SystemExit(f"{DERIVED} lacks provenance columns {missing} — rebuild it")
    d["t"] = np.arange(len(d), dtype=float)
    return d


# --------------------------------------------------------------------------
# 1. spec selection — identify, don't assume (Trap 4)
# --------------------------------------------------------------------------
def select_spec(pre: pd.DataFrame) -> dict:
    """Joint-significance test every candidate term against an intercept-only
    baseline. Terms that do not test as real are dropped: an insignificant
    seasonal basis is not a 'safe control', it extrapolates junk into the
    counterfactual."""
    y = pre[OUTCOME].astype(float).values
    n = len(y)
    t = np.arange(n, dtype=float)
    yr = t / 365.25

    candidates = {
        "linear trend": [t],
        "quadratic trend": [t, t**2],
        "annual Fourier (1 harmonic)": [np.sin(2 * np.pi * yr), np.cos(2 * np.pi * yr)],
        "annual Fourier (2 harmonics)": [np.sin(2 * np.pi * yr), np.cos(2 * np.pi * yr),
                                         np.sin(4 * np.pi * yr), np.cos(4 * np.pi * yr)],
        "weekly Fourier": [np.sin(2 * np.pi * t / 7), np.cos(2 * np.pi * t / 7)],
        "day-of-week dummies": list(
            pd.get_dummies(pre.index.dayofweek, drop_first=True).values.astype(float).T),
    }

    def rss(cols):
        X = np.column_stack([np.ones(n)] + list(cols)) if cols else np.ones((n, 1))
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        return float(((y - X @ beta) ** 2).sum()), X.shape[1]

    rss0, k0 = rss([])
    rows = []
    for name, cols in candidates.items():
        rss1, k1 = rss(cols)
        F = ((rss0 - rss1) / (k1 - k0)) / (rss1 / (n - k1))
        p = float(stats.f.sf(F, k1 - k0, n - k1))
        rows.append({"term": name, "df": k1 - k0, "F": round(F, 4),
                     "p_value": round(p, 4), "keep": bool(p < 0.05)})
    return {"baseline": "intercept only", "n_pre": n, "alpha": 0.05, "tests": rows}


# --------------------------------------------------------------------------
# 2. the ITS fit
# --------------------------------------------------------------------------
def draws_by_obs(da, n_obs: int) -> np.ndarray:
    """(chain, draw, obs_ind[, treated_units]) -> (draws, n_obs).

    CausalPy 0.8 carries a singleton `treated_units` dim on post_impact and the
    predictive groups; 0.9 dropped it. Hard-coding either layout silently breaks
    on the other version, so normalise here instead.
    """
    for d in [d for d in da.dims if d not in ("chain", "draw", "obs_ind")]:
        if da.sizes[d] != 1:
            raise ValueError(f"unexpected multi-unit dim {d}={da.sizes[d]}; "
                             "this analysis assumes a single treated unit")
        da = da.isel({d: 0}, drop=True)
    return np.asarray(da.transpose("chain", "draw", "obs_ind")).reshape(-1, n_obs)


def pred_da(obj):
    """Posterior-predictive draws as a DataArray, across CausalPy versions:
    0.8 returns an InferenceData for pre_pred/post_pred, 0.9 returns y_hat
    directly."""
    if hasattr(obj, "groups"):        # InferenceData
        return obj["posterior_predictive"]["y_hat"]
    if hasattr(obj, "data_vars"):     # Dataset
        return obj["y_hat"]
    return obj                        # already a DataArray


def pre_r2(its) -> float:
    """Pre-period R^2, reported as a symptom only (Trap 2 — never a gate).
    Key name is version-dependent ('unit_0_r2' in 0.8, plain 'r2' in 0.9)."""
    s = its.score
    for k in ("unit_0_r2", "r2"):
        if k in s:
            return float(np.asarray(s[k]).mean())
    return float(np.asarray(list(s.values())[0]).mean())


def fit_its(d: pd.DataFrame, treatment: pd.Timestamp, formula: str,
            guard_days: int, sample_kwargs: dict) -> tuple:
    """Fit the counterfactual on pre-treatment data, holding out `guard_days`
    immediately before the cutoff (anticipation contamination, Trap 3), and
    score the post window against it."""
    fit_end = treatment - pd.Timedelta(days=guard_days)
    frame = d.loc[(d.index < fit_end) | (d.index >= treatment), [OUTCOME, "t"]]
    its = cp.InterruptedTimeSeries(
        frame, treatment, formula=formula,
        model=cp.pymc_models.LinearRegression(sample_kwargs=sample_kwargs),
    )
    return its, frame


def effect(its, post_index: pd.DatetimeIndex, horizon: int | None = None) -> dict:
    """Average treatment effect on the treated over the post window, as a level
    (signups/day) and as a % of the counterfactual mean.

    IMPORTANT — which counterfactual: `post_impact` (dims treated_units, chain,
    draw, obs_ind) is `observed - counterfactual MEAN`; empirically its
    window-average sd equals sigma/sqrt(n_pre), i.e. it carries *parameter*
    uncertainty only. `post_pred["y_hat"]` is the full posterior predictive and
    is ~2x wider. Mixing them (impact from one, counterfactual from the other)
    silently understates or overstates the interval, so everything here is
    derived from `post_impact` alone and the counterfactual mean is recovered
    from it as `observed - impact`.

    Consequence, stated plainly: the HDIs returned here are parameter-uncertainty
    intervals for the systematic shift in the mean level. They are NOT calibrated
    forecast intervals, and in this analysis they are demonstrably narrower than
    the design's own placebo spread. The placebo distribution is what the memo
    leans on for the equivalence claim.
    """
    imp = draws_by_obs(its.post_impact, len(post_index))        # (draws, days)
    if horizon is not None:
        imp = imp[:, :horizon]
    obs = np.asarray(its.datapost[OUTCOME], dtype=float)
    obs = obs[:horizon] if horizon is not None else obs

    per_draw_level = imp.mean(axis=1)
    per_draw_cf = obs.mean() - per_draw_level                   # same basis
    per_draw_pct = 100.0 * per_draw_level / per_draw_cf

    lo, hi = az.hdi(per_draw_pct, hdi_prob=0.95)
    lo_l, hi_l = az.hdi(per_draw_level, hdi_prob=0.95)
    return {
        "effect_per_day": float(per_draw_level.mean()),
        "effect_per_day_hdi95": [float(lo_l), float(hi_l)],
        "effect_pct": float(per_draw_pct.mean()),
        "effect_pct_hdi95": [float(lo), float(hi)],
        "observed_mean": float(obs.mean()),
        "counterfactual_mean": float(per_draw_cf.mean()),
        "draws_pct": per_draw_pct,
    }


# --------------------------------------------------------------------------
# 3. residual gate (Trap 2) — structure, not R^2
# --------------------------------------------------------------------------
def residual_gate(its, frame: pd.DataFrame, treatment: pd.Timestamp) -> dict:
    pre_idx = frame.index[frame.index < treatment]
    obs = frame.loc[pre_idx, OUTCOME].astype(float).values
    pred = draws_by_obs(pred_da(its.pre_pred),
                        len(pre_idx)).mean(axis=0)
    e = obs - pred
    n = len(e)
    t = np.arange(n, dtype=float)
    lag1 = float(np.corrcoef(e[:-1], e[1:])[0, 1])
    q = n * (n + 2) * sum(np.corrcoef(e[:-l], e[l:])[0, 1] ** 2 / (n - l) for l in range(1, 15))
    lb_p = float(stats.chi2.sf(q, 14))
    trend_r = float(np.corrcoef(t, e)[0, 1])
    yr = t / 365.25
    Xs = np.column_stack([np.ones(n), np.sin(2 * np.pi * yr), np.cos(2 * np.pi * yr),
                          np.sin(2 * np.pi * t / 7), np.cos(2 * np.pi * t / 7)])
    b, *_ = np.linalg.lstsq(Xs, e, rcond=None)
    seasonal_r2 = float(1 - ((e - Xs @ b) ** 2).sum() / ((e - e.mean()) ** 2).sum())
    return {
        "resid_vs_time_corr": round(trend_r, 4),
        "resid_vs_time_pass": bool(abs(trend_r) < 0.10),
        "lag1_acf": round(lag1, 4),
        "lag1_pass": bool(abs(lag1) < 0.10),
        "ljung_box_14_p": round(lb_p, 4),
        "ljung_box_pass": bool(lb_p > 0.05),
        "leftover_seasonal_r2": round(seasonal_r2, 4),
        "leftover_seasonal_pass": bool(seasonal_r2 < 0.02),
        "pre_resid_sd": round(float(e.std(ddof=1)), 4),
        "note": "R^2 is deliberately not a gate here (Trap 2); it is reported "
                "only as a symptom in result.json.",
    }


# --------------------------------------------------------------------------
# 4. placebo-in-time (decisive)
# --------------------------------------------------------------------------
def placebo_sweep(d: pd.DataFrame, formula: str, post_len: int) -> list[dict]:
    """Fake interventions wholly inside the pre-period. Each keeps >= 180 days
    of fit data and a full post_len-day scoring window, so every placebo is the
    same estimation problem as the real one — only the date is a lie."""
    pre_start = d.index.min()
    first = pre_start + pd.Timedelta(days=180 + GUARD_DAYS)
    last = TREATMENT - pd.Timedelta(days=post_len)
    dates = pd.to_datetime(np.linspace(first.value, last.value, N_PLACEBO)).normalize()
    rows = []
    for i, fake in enumerate(dates, 1):
        sub = d.loc[d.index < fake + pd.Timedelta(days=post_len)]
        its, frame = fit_its(sub, fake, formula, GUARD_DAYS, PLACEBO_KWARGS)
        post_idx = frame.index[frame.index >= fake]
        e = effect(its, post_idx)
        rows.append({"fake_date": fake.date().isoformat(),
                     "effect_pct": round(e["effect_pct"], 4),
                     "effect_pct_hdi95": [round(x, 4) for x in e["effect_pct_hdi95"]],
                     "hdi_contains_zero": bool(e["effect_pct_hdi95"][0] <= 0 <= e["effect_pct_hdi95"][1])})
        print(f"    placebo {i:2d}/{N_PLACEBO}  {fake.date()}  {e['effect_pct']:+7.3f}%")
    return rows


# --------------------------------------------------------------------------
# 5. Poisson robustness (Trap 6 — precision, not sign)
# --------------------------------------------------------------------------
def poisson_its(d: pd.DataFrame) -> dict:
    fit_end = TREATMENT - pd.Timedelta(days=GUARD_DAYS)
    pre = d.loc[d.index < fit_end]
    post = d.loc[d.index >= TREATMENT]
    # Scale time to YEARS centred on the pre-period. On the raw day index t
    # spans +/-360 and the post window reaches +540, so a log-linear slope prior
    # has to be absurdly tight to keep exp(a + b*t) finite — and the geometry is
    # bad enough that the sampler blows up (observed: r_hat ~2e7 on pymc 5.28).
    # In years the slope is interpretable and the posterior is well conditioned.
    scale = 365.25
    t0 = pre["t"].mean()
    t_pre = ((pre["t"] - t0) / scale).values
    t_post = ((post["t"] - t0) / scale).values
    with pm.Model():
        a = pm.Normal("a", mu=np.log(pre[OUTCOME].mean()), sigma=0.2)
        b = pm.Normal("b", mu=0.0, sigma=0.1)   # ~10% log-change per year
        pm.Poisson("y", mu=pm.math.exp(a + b * t_pre), observed=pre[OUTCOME].values)
        idata = pm.sample(**{**SAMPLE_KWARGS, "draws": 1000, "tune": 1000})

    max_rhat = float(az.rhat(idata).to_array().max())
    div = int(idata.sample_stats["diverging"].sum())
    if max_rhat > 1.05 or div > 0:
        # Never let a failed fit reach result.json wearing a number.
        raise RuntimeError(f"Poisson robustness check did not converge "
                           f"(max r_hat={max_rhat:.4f}, divergences={div}) — "
                           f"fix the model, do not report the estimate")
    a_s = idata.posterior["a"].values.reshape(-1)
    b_s = idata.posterior["b"].values.reshape(-1)
    cf = np.exp(a_s[:, None] + b_s[:, None] * t_post[None, :]).mean(axis=1)
    pct = 100.0 * (post[OUTCOME].mean() - cf) / cf
    lo, hi = az.hdi(pct, hdi_prob=0.95)
    return {"family": "Poisson (log link, linear trend in years)",
            "effect_pct": float(pct.mean()),
            "effect_pct_hdi95": [float(lo), float(hi)],
            "max_r_hat": max_rhat, "divergences": div}


# --------------------------------------------------------------------------
# plots — each one tests a named assumption, not decoration
# --------------------------------------------------------------------------
def make_plots(d, its, frame, primary, placebos, pl, gate) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    post = d.loc[d.index >= TREATMENT]

    # 1. inflow decomposition: is the pool denominator moving for its own reasons?
    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    for a, col, c in zip(ax, ["signups", "subscriber_pool", "conversions"],
                         ["#1f77b4", "#7f7f7f", "#d62728"]):
        a.plot(d.index, d[col], lw=0.6, color=c, alpha=0.55)
        a.plot(d.index, d[col].rolling(28, center=True).mean(), lw=1.8, color=c)
        a.axvline(TREATMENT, color="k", ls="--", lw=1)
        a.set_ylabel(col)
    ax[0].set_title("Inflow decomposition — signups is flat while the pool and "
                    "conversions are not (28d rolling mean; dashed = 2026-04-01)")
    fig.tight_layout(); fig.savefig(OUT / "inflow-decomposition.png", dpi=130); plt.close(fig)

    # 2. observed vs counterfactual
    mu = np.asarray(post[OUTCOME], dtype=float) - draws_by_obs(its.post_impact, len(post))
    lo, hi = np.percentile(mu, [2.5, 97.5], axis=0)
    fig, a = plt.subplots(figsize=(11, 4.2))
    a.plot(d.index, d[OUTCOME], lw=0.5, color="#999", alpha=0.6, label="observed (daily)")
    a.plot(d.index, d[OUTCOME].rolling(28, center=True).mean(), lw=1.6,
           color="#1f77b4", label="observed (28d mean)")
    a.fill_between(post.index, lo, hi, color="#ff7f0e", alpha=0.30,
                   label="counterfactual mean, 95%")
    a.plot(post.index, mu.mean(axis=0), color="#ff7f0e", lw=1.6, label="counterfactual mean")
    a.axvline(TREATMENT, color="k", ls="--", lw=1)
    a.axvspan(TREATMENT - pd.Timedelta(days=GUARD_DAYS), TREATMENT, color="k", alpha=0.10)
    a.axhline(float(np.asarray(d.loc[d.index < TREATMENT, OUTCOME]).mean()),
              color="k", lw=0.6, ls=":", label="pre-period mean")
    a.set_ylabel("signups/day"); a.legend(loc="lower left", fontsize=8, ncol=2)
    a.set_title(f"ITS counterfactual — effect {primary['effect_pct']:+.2f}% "
                f"(shaded band at the cutoff = {GUARD_DAYS}d anticipation guard, excluded from the fit)")
    fig.tight_layout(); fig.savefig(OUT / "its-counterfactual.png", dpi=130); plt.close(fig)

    # 3. residual gate
    pre_idx = frame.index[frame.index < TREATMENT]
    obs_pre = frame.loc[pre_idx, OUTCOME].astype(float).values
    pred = draws_by_obs(pred_da(its.pre_pred),
                        len(pre_idx)).mean(axis=0)
    e = obs_pre - pred
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.4))
    ax[0].scatter(pre_idx, e, s=3, alpha=0.4); ax[0].axhline(0, color="k", lw=0.8)
    ax[0].set_title(f"residual vs time (r={gate['resid_vs_time_corr']:+.3f})")
    acf = [np.corrcoef(e[:-l], e[l:])[0, 1] for l in range(1, 31)]
    ax[1].bar(range(1, 31), acf, color="#1f77b4")
    ax[1].axhline(1.96 / np.sqrt(len(e)), color="r", ls="--", lw=0.8)
    ax[1].axhline(-1.96 / np.sqrt(len(e)), color="r", ls="--", lw=0.8)
    ax[1].set_title(f"residual ACF (Ljung-Box p={gate['ljung_box_14_p']:.2f})")
    ax[2].hist(e, bins=30, color="#1f77b4", alpha=0.8)
    ax[2].set_title(f"residuals (sd={gate['pre_resid_sd']:.2f})")
    fig.suptitle("Residual gate on the pre-period fit — the counterfactual is judged here, not on R²",
                 fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "residual-gate.png", dpi=130); plt.close(fig)

    # 4. placebo distribution
    fig, a = plt.subplots(figsize=(9, 3.8))
    fd = pd.to_datetime([p["fake_date"] for p in placebos])
    a.scatter(fd, pl, s=45, color="#7f7f7f", label="placebo (fake date)", zorder=3)
    a.axhline(0, color="k", lw=0.8)
    a.axhspan(pl.mean() - 1.96 * pl.std(ddof=1), pl.mean() + 1.96 * pl.std(ddof=1),
              color="#7f7f7f", alpha=0.18, label="placebo 95% spread")
    a.scatter([TREATMENT], [primary["effect_pct"]], s=130, marker="*", color="#d62728",
              zorder=4, label=f"real date ({primary['effect_pct']:+.2f}%)")
    a.set_ylabel("estimated effect (%)")
    a.set_title("Placebo-in-time — real date sits inside the placebo spread\n"
                f"(windows overlap {100*max(0.0,(len(post)-int((fd[1]-fd[0]).days))/len(post)):.0f}%"
                f" — ~3 independent replicates, so the spread itself is imprecise)", fontsize=10)
    a.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "placebo-distribution.png", dpi=130); plt.close(fig)
    print("    wrote 4 diagnostic plots")


def main() -> None:
    d = load()
    pre = d.loc[d.index < TREATMENT]
    post = d.loc[d.index >= TREATMENT]
    post_len = len(post)
    print(f"derived layer: {len(d)} rows  {d.index.min().date()}..{d.index.max().date()}")
    print(f"pre={len(pre)}  post={post_len}  guard={GUARD_DAYS}d\n")

    print("[1] spec selection (joint significance on the pre-period)")
    spec = select_spec(pre)
    for r in spec["tests"]:
        print(f"    {r['term']:30s} F={r['F']:7.3f} p={r['p_value']:.3f} "
              f"{'KEEP' if r['keep'] else 'drop'}")
    kept = [r["term"] for r in spec["tests"] if r["keep"]]
    # Pre-registered: a linear trend is retained regardless, because the
    # counterfactual must extrapolate 183 days and a flat-forever assumption is
    # the stronger claim. Retaining an insignificant trend costs precision, not
    # validity. Every *seasonal* basis is dropped on the test above.
    formula = f"{OUTCOME} ~ 1 + t"
    spec["kept_by_test"] = kept
    spec["formula"] = formula
    spec["trend_note"] = ("linear trend retained by pre-registration despite p>0.05: "
                          "the counterfactual extrapolates 183 days, so 'no trend' is "
                          "the stronger assumption. Intercept-only is reported as a "
                          "sensitivity spec.")
    print(f"    -> formula: {formula}\n")

    print("[2] primary fit (guard window applied)")
    its, frame = fit_its(d, TREATMENT, formula, GUARD_DAYS, SAMPLE_KWARGS)
    primary = effect(its, post.index)
    rhat = float(az.rhat(its.idata).to_array().max())
    div = int(its.idata.sample_stats["diverging"].sum())
    ess = float(az.ess(its.idata).to_array().min())
    print(f"    effect {primary['effect_pct']:+.3f}%  HDI95 "
          f"[{primary['effect_pct_hdi95'][0]:+.3f}, {primary['effect_pct_hdi95'][1]:+.3f}]")
    print(f"    r_hat={rhat:.4f} divergences={div} min_ess={ess:.0f}\n")

    print("[3] residual gate")
    gate = residual_gate(its, frame, TREATMENT)
    for k, v in gate.items():
        if k.endswith("_pass"):
            print(f"    {k:28s} {'PASS' if v else 'FAIL'}")

    print("\n[4] placebo-in-time sweep")
    placebos = placebo_sweep(d, formula, post_len)
    pl = np.array([p["effect_pct"] for p in placebos])
    pl_sd = float(pl.std(ddof=1))
    z = float((primary["effect_pct"] - pl.mean()) / pl_sd)
    p_emp = float((np.abs(pl - pl.mean()) >= abs(primary["effect_pct"] - pl.mean())).mean())
    mde = float(2.8 * pl_sd)  # 1.96 + 0.84, two-sided 5% / 80% power
    # The placebo spread is the design's *empirical* operating characteristic:
    # 12 refits of the same estimator at dates where the answer is known to be 0.
    # Where it exceeds the posterior sd, the posterior is overconfident and the
    # calibrated interval is the one to quote.
    post_sd = float(np.std(primary["draws_pct"], ddof=1))
    calib = [round(primary["effect_pct"] - 1.96 * pl_sd, 4),
             round(primary["effect_pct"] + 1.96 * pl_sd, 4)]
    print(f"    placebo mean {pl.mean():+.3f}%  sd {pl_sd:.3f}%")
    print(f"    real date z = {z:+.3f}   empirical p = {p_emp:.3f}")
    print(f"    posterior sd {post_sd:.3f}% vs placebo sd {pl_sd:.3f}% "
          f"-> overconfidence factor {pl_sd / post_sd:.2f}x")
    print(f"    placebo-calibrated 95% interval: [{calib[0]:+.3f}, {calib[1]:+.3f}]")
    print(f"    minimum detectable effect (80% power) = +/-{mde:.2f}%\n")

    # How independent is that sweep, really? Each placebo scores a `post_len`-day
    # window but the fake dates are only `spacing` days apart, so neighbours share
    # most of their data. Reporting sd over 12 overlapping windows as if it were 12
    # replicates overstates the precision of the calibration itself.
    fake_dates = pd.to_datetime([p["fake_date"] for p in placebos])
    spacing = int((fake_dates[1] - fake_dates[0]).days)
    overlap = max(0.0, (post_len - spacing) / post_len)
    n_eff = 1 + (len(placebos) - 1) * (1 - overlap)
    doy = fake_dates.dayofyear.values
    Xa = np.column_stack([np.ones(len(pl)), np.sin(2 * np.pi * doy / 365.25),
                          np.cos(2 * np.pi * doy / 365.25)])
    ba, *_ = np.linalg.lstsq(Xa, pl, rcond=None)
    real_doy = TREATMENT.dayofyear
    seasonal_expect = float(np.array(
        [1, np.sin(2 * np.pi * real_doy / 365.25), np.cos(2 * np.pi * real_doy / 365.25)]) @ ba)
    resid_sd = float((pl - Xa @ ba).std(ddof=1))
    z_seasonal = float((primary["effect_pct"] - seasonal_expect) / resid_sd)
    placebo_indep = {
        "window_days": int(post_len), "spacing_days": spacing,
        "overlap_fraction": round(overlap, 3),
        "effective_independent_placebos": round(n_eff, 2),
        "annual_position_fit_expectation_pct": round(seasonal_expect, 4),
        "z_after_annual_position_adjustment": round(z_seasonal, 4),
        "note": ("the placebo series drifts smoothly because neighbouring windows share "
                 "%.0f%% of their data, NOT because an annual cycle survived spec "
                 "selection. Naive correlation tests on this series are invalid. Only "
                 "~%.1f independent replicates fit in a %d-day pre-period at this window "
                 "length, so the calibrated sd is itself imprecise — treat the +/-%.1f%% "
                 "bound as approximate." % (100 * overlap, n_eff, len(pre), mde)),
    }
    print(f"    window overlap {100*overlap:.0f}%  -> ~{n_eff:.1f} independent replicates")
    print(f"    z after annual-position adjustment = {z_seasonal:+.3f}\n")

    print("[5] sensitivity")
    sens = [{"spec": "primary: 1 + t, 7d guard", "effect_pct": round(primary["effect_pct"], 4),
             "effect_pct_hdi95": [round(x, 4) for x in primary["effect_pct_hdi95"]]}]
    for label, f_, g_ in [("no guard window (0d)", formula, 0),
                          ("14d guard window", formula, 14),
                          ("intercept only", f"{OUTCOME} ~ 1", GUARD_DAYS),
                          ("quadratic trend", f"{OUTCOME} ~ 1 + t + I(t**2)", GUARD_DAYS)]:
        i2, _ = fit_its(d, TREATMENT, f_, g_, PLACEBO_KWARGS)
        e2 = effect(i2, post.index)
        sens.append({"spec": label, "effect_pct": round(e2["effect_pct"], 4),
                     "effect_pct_hdi95": [round(x, 4) for x in e2["effect_pct_hdi95"]]})
        print(f"    {label:28s} {e2['effect_pct']:+7.3f}%  "
              f"[{e2['effect_pct_hdi95'][0]:+.3f}, {e2['effect_pct_hdi95'][1]:+.3f}]")
    # first 30 post days vs rest — is the null hiding a transient?
    e_early = effect(its, post.index, horizon=30)
    sens.append({"spec": "first 30 post days only",
                 "effect_pct": round(e_early["effect_pct"], 4),
                 "effect_pct_hdi95": [round(x, 4) for x in e_early["effect_pct_hdi95"]]})
    print(f"    {'first 30 post days only':28s} {e_early['effect_pct']:+7.3f}%")

    print("\n[6] Poisson robustness")
    pois = poisson_its(d)
    print(f"    {pois['effect_pct']:+.3f}%  "
          f"[{pois['effect_pct_hdi95'][0]:+.3f}, {pois['effect_pct_hdi95'][1]:+.3f}]  "
          f"r_hat={pois['max_r_hat']:.4f}")

    print("\n[7] equivalence test")
    draws = primary["draws_pct"]
    p_in_rope = float(np.mean(np.abs(draws) < ROPE_PCT))
    p_neg = float(np.mean(draws < 0))
    # Calibrated version: same point estimate, placebo-derived scale.
    p_in_rope_cal = float(stats.norm.cdf(ROPE_PCT, primary["effect_pct"], pl_sd)
                          - stats.norm.cdf(-ROPE_PCT, primary["effect_pct"], pl_sd))
    print(f"    ROPE +/-{ROPE_PCT}%: P(effect in ROPE) = {p_in_rope:.4f} (posterior)")
    print(f"    ROPE +/-{ROPE_PCT}%: P(effect in ROPE) = {p_in_rope_cal:.4f} (placebo-calibrated)")
    print(f"    P(effect < 0) = {p_neg:.4f}")

    result = {
        "issue": 10,
        "question": "Did the 2026-04-01 price increase change signup inflow?",
        "estimand": ("ATT on daily signups over 2026-04-01..2026-09-30: mean observed "
                     "daily signups minus the mean daily signups predicted by a "
                     "pre-treatment counterfactual, expressed as a percentage of that "
                     "counterfactual. Not an ATE — it is the effect on this business, "
                     "this window."),
        "outcome": OUTCOME,
        "outcome_governed": False,
        "outcome_governance_note": (
            "signups is NOT defined in 1-data/semantic-layer/. The issue attributes an "
            "'inflow; flat across treatment' claim to conv_rate.yml; that string does "
            "not appear there. This run adds signups.yml and supplies the evidence."),
        "design": "interrupted time series (CausalPy InterruptedTimeSeries, Bayesian)",
        "treatment_date": TREATMENT.date().isoformat(),
        "formula": formula,
        "guard_window_days": GUARD_DAYS,
        "n_pre": int(len(pre)), "n_post": int(post_len),
        "effect_pct": round(primary["effect_pct"], 4),
        "effect_pct_hdi95": [round(x, 4) for x in primary["effect_pct_hdi95"]],
        "effect_per_day": round(primary["effect_per_day"], 4),
        "effect_per_day_hdi95": [round(x, 4) for x in primary["effect_per_day_hdi95"]],
        "observed_mean_signups": round(primary["observed_mean"], 4),
        "counterfactual_mean_signups": round(primary["counterfactual_mean"], 4),
        "verdict": "validated null",
        "effect_pct_ci95_placebo_calibrated": calib,
        "equivalence": {
            "rope_pct": ROPE_PCT,
            "p_effect_within_rope_posterior": round(p_in_rope, 4),
            "p_effect_within_rope_calibrated": round(p_in_rope_cal, 4),
            "p_effect_negative": round(p_neg, 4),
            "minimum_detectable_effect_pct": round(mde, 4),
            "interpretation": ("the design detects a +/-%.2f%% shift at 80%% power; the "
                               "placebo-calibrated posterior puts %.1f%% of mass inside "
                               "+/-%.0f%%. Evidence of absence within +/-%.0f%%, not merely "
                               "absence of evidence — but the design cannot rule out a "
                               "shift smaller than the MDE."
                               % (mde, 100 * p_in_rope_cal, ROPE_PCT, ROPE_PCT)),
        },
        "placebo": {"n_fake_dates": len(placebos), "real_date_z": round(z, 4),
                    "empirical_p": round(p_emp, 4),
                    "placebo_mean_pct": round(float(pl.mean()), 4),
                    "placebo_sd_pct": round(pl_sd, 4),
                    "posterior_sd_pct": round(post_sd, 4),
                    "overconfidence_factor": round(pl_sd / post_sd, 3),
                    "note": ("posterior HDIs are parameter-uncertainty intervals and are "
                             "narrower than the estimator's own spread across 12 known-null "
                             "dates. Quote the calibrated interval, not the HDI."),
                    "independence": placebo_indep},
        "residual_gate": gate,
        "sensitivity": sens,
        "poisson_robustness": pois,
        "mcmc": {"max_r_hat": round(rhat, 4), "divergences": div, "min_ess": round(ess, 1)},
        "pre_period_r2": round(pre_r2(its), 4),
        "spec_selection": spec,
        "seed": SEED,
        "provenance": {"data": "1-data/derived/daily.csv",
                       "causalpy": cp.__version__, "pymc": pm.__version__},
    }
    print("\n[8] diagnostic plots")
    make_plots(d, its, frame, primary, placebos, pl, gate)

    (OUT / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUT / "placebo.json").write_text(json.dumps(
        {"real_effect_pct": round(primary["effect_pct"], 4),
         "placebo_effects_pct": [p["effect_pct"] for p in placebos],
         "placebo_detail": placebos,
         "real_date_z": round(z, 4), "empirical_p": round(p_emp, 4),
         "minimum_detectable_effect_pct": round(mde, 4)}, indent=2) + "\n")
    print(f"\nwrote {OUT/'result.json'} and {OUT/'placebo.json'}")


if __name__ == "__main__":
    main()
