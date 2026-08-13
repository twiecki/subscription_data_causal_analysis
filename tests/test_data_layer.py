"""Invariant gate for the derived layer. Red = the layer is off-limits."""
from pathlib import Path
import pandas as pd

DERIVED = Path(__file__).resolve().parents[1] / "data/derived/daily.csv"


def _df():
    return pd.read_csv(DERIVED, parse_dates=["date"])


def test_layer_exists():
    assert DERIVED.exists(), "run data/build_data.py first"


def test_provenance_complete():
    df = _df()
    assert df.source_file.notna().all() and df.source_row.notna().all()


def test_no_duplicate_days():
    df = _df()
    assert not df.date.duplicated().any()


def test_conv_rate_consistent():
    df = _df()
    recomputed = df.conversions / df.subscriber_pool
    assert (recomputed - df.conv_rate).abs().max() < 1e-9


def test_post_flips_once():
    df = _df().sort_values("date")
    assert (df.post.diff().fillna(0) != 0).sum() == 1
