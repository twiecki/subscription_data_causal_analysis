"""Revenue impact of the 2026-04-01 price hike (answers issue #2).

Propagates the conversion-effect posterior [[i-3fa2]] into a revenue-uplift
estimate: fewer conversions, each worth ~33% more. Works from the derived
data layer (provenance guaranteed) and the governed outcome [[k-77b0]] --
no re-derivation from raw files.

Estimand: relative change in expected daily subscription revenue vs. the
no-hike counterfactual, 2026-04-01..2026-09-30, holding price mix constant.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRICE_UPLIFT = 0.33  # from the governed contract [[k-a1f4]]

# posterior for the conversion effect [[i-3fa2]]: mean -15.6%, 95% HDI [-19.2, -12.4]
EFF_MEAN, EFF_SD = -0.156, (0.192 - 0.124) / (2 * 1.96)

rng = np.random.default_rng(20260401)
eff = rng.normal(EFF_MEAN, EFF_SD, 20_000)
uplift = (1 + PRICE_UPLIFT) * (1 + eff) - 1

df = pd.read_csv(ROOT / "1-data/derived/daily.csv", parse_dates=["date"])
post = df[df.post == 1]

lo, hi = np.percentile(uplift, [2.5, 97.5])
print(f"post period: {post.date.min().date()}..{post.date.max().date()} ({len(post)} days)")
print(f"revenue uplift: {uplift.mean():+.1%}  (95% [{lo:+.1%}, {hi:+.1%}])")
print(f"P(uplift > 0) = {(uplift > 0).mean():.3f}")
