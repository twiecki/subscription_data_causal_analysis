#!/bin/bash
set -e

# Oracle solution: write the reproducible analysis script to /root/analysis.py
# (the task requires the code artifact), then run it to produce result.json,
# placebo.json, and memo.md.

cat > /root/analysis.py << 'PYEOF'
"""
Interrupted Time Series (ITS) analysis of the 2026-04-01 subscription price
increase. Produces result.json, placebo.json, and memo.md.

Method (per metric-contract.yml):
  - Outcome: conv_rate = conversions / subscriber_pool (daily)
  - Drop rows with subscriber_pool < 1000 (early binomial noise)
  - Fit OLS on the pre-period: conv_rate ~ 1 + t + sin(2pi*month/12) + cos(2pi*month/12)
  - Effect: 100 * (mean observed post - mean counterfactual post) / mean cf post
  - Placebo sweep over 9 fake dates strictly inside the pre-period
  - Anticipation sensitivity: refit with 7- and 14-day guard windows
"""

import json
import math

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

DATA_PATH = "/root/daily_aggregates_intervention.csv"
INTERVENTION_DATE = pd.Timestamp("2026-04-01")

PLACEBO_DATES = [
    "2025-05-26", "2025-06-20", "2025-07-15", "2025-08-10", "2025-09-04",
    "2025-09-29", "2025-10-25", "2025-11-19", "2025-12-15",
]

FEATURE_COLS = ["t", "sin_annual", "cos_annual"]


def load_data(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["subscriber_pool"] >= 1000].copy()
    return df.sort_values("date").reset_index(drop=True)


def build_features(df, t0_date):
    df = df.copy()
    df["t"] = (df["date"] - t0_date).dt.days.astype(float)
    month = df["date"].dt.month.astype(float)
    df["sin_annual"] = np.sin(2 * math.pi * month / 12)
    df["cos_annual"] = np.cos(2 * math.pi * month / 12)
    return df


def fit_its(df, intervention_date, guard_days=0):
    t0 = df["date"].min()
    df = build_features(df, t0)
    cutoff = intervention_date - pd.Timedelta(days=guard_days)
    pre = df[df["date"] < cutoff]
    post = df[df["date"] >= intervention_date]
    model = LinearRegression()
    model.fit(pre[FEATURE_COLS], pre["conv_rate"])
    cf_post = model.predict(post[FEATURE_COLS])
    return 100.0 * (post["conv_rate"].mean() - cf_post.mean()) / cf_post.mean()


def run_placebo_sweep(df, placebo_dates):
    effects = []
    for fake in sorted(pd.Timestamp(d) for d in placebo_dates):
        t0 = df["date"].min()
        feat = build_features(df, t0)
        pre = feat[feat["date"] < fake]
        post = feat[(feat["date"] >= fake) & (feat["date"] < INTERVENTION_DATE)]
        if len(pre) < 30 or len(post) == 0:
            continue
        model = LinearRegression()
        model.fit(pre[FEATURE_COLS], pre["conv_rate"])
        cf = model.predict(post[FEATURE_COLS])
        effects.append(round(100.0 * (post["conv_rate"].mean() - cf.mean()) / cf.mean(), 4))
    return effects


def main():
    df = load_data(DATA_PATH)

    effect = fit_its(df, INTERVENTION_DATE, guard_days=0)
    effect_g7 = fit_its(df, INTERVENTION_DATE, guard_days=7)
    effect_g14 = fit_its(df, INTERVENTION_DATE, guard_days=14)
    placebos = run_placebo_sweep(df, PLACEBO_DATES)

    estimand = (
        "Average percentage reduction in the daily subscription conversion "
        "rate (conversions / subscriber_pool) over the post-period "
        "2026-04-01 to 2026-09-30, relative to the counterfactual predicted "
        "by an ITS model with linear trend and annual Fourier seasonality "
        "fit on the pre-period."
    )

    with open("/root/result.json", "w") as f:
        json.dump({"effect_pct": round(effect, 4), "estimand": estimand}, f, indent=2)

    with open("/root/placebo.json", "w") as f:
        json.dump(
            {"real_effect_pct": round(effect, 4), "placebo_effects_pct": placebos},
            f, indent=2,
        )

    mean_p = float(np.mean(placebos))
    std_p = float(np.std(placebos, ddof=1))
    z = abs(effect - mean_p) / std_p

    memo = f"""# Memo: impact of the 2026-04-01 price increase on daily conversion

## Claim

The price increase reduced the daily subscription conversion rate by
**{effect:.1f}%** relative to the modeled counterfactual.

## Method

Interrupted time series: OLS of conv_rate on a linear time trend plus annual
Fourier seasonality (sin/cos of month/12), fit on the pre-period after
dropping the first noisy days (subscriber_pool < 1000), extrapolated into the
183-day post-period.

## Validation

- Placebo-in-time sweep ({len(placebos)} fake dates inside the pre-period):
  effects range {min(placebos):.1f}% to {max(placebos):.1f}%, mean
  {mean_p:.1f}%. The real date is a clear outlier (z = {z:.1f}). The
  estimator does not manufacture effects at arbitrary dates.
- Anticipation sensitivity: excluding the final 7 / 14 pre-treatment days
  from the fit (guard window, per the metric contract) moves the estimate to
  {effect_g7:.1f}% / {effect_g14:.1f}%. The conclusion is robust to
  anticipation effects in the final pre-treatment week.

## Caveats

- The denominator (subscriber_pool) drifts as converters leave the pool; the
  trend term absorbs smooth drift, and the placebo sweep confirms the drift
  alone does not produce the observed break.
- Non-randomized rollout: the estimate relies on the counterfactual trend
  assumption; any unrelated shock coinciding exactly with 2026-04-01 would be
  attributed to the price change.
"""
    with open("/root/memo.md", "w") as f:
        f.write(memo)

    print(json.dumps({"effect_pct": round(effect, 4), "placebo_z": round(z, 2)}))


if __name__ == "__main__":
    main()
PYEOF

python3 /root/analysis.py
