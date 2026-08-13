"""Build the derived data layer from data/raw/.

Every derived row carries provenance (source file + row). The build report
records what was NOT ingested — silent gaps are the killer. A red test in
tests/test_data_layer.py means the derived layer is off-limits.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW, DERIVED = ROOT / "raw", ROOT / "derived"


def build() -> None:
    src = RAW / "daily_aggregates_intervention.csv"
    df = pd.read_csv(src, parse_dates=["date"])
    dropped = df[df.isna().any(axis=1)]
    df = df.dropna()
    out = df[["date", "subscriber_pool", "signups", "conversions", "conv_rate", "post"]].copy()
    out["source_file"] = src.name
    out["source_row"] = df.index + 2  # 1-based + header, so a row is findable in the raw file
    DERIVED.mkdir(exist_ok=True)
    out.to_csv(DERIVED / "daily.csv", index=False)
    report = [
        f"rows_in={len(df) + len(dropped)}",
        f"rows_out={len(out)}",
        f"rows_dropped={len(dropped)}  # NOT ingested — check before answering from this layer",
        f"span={out.date.min().date()}..{out.date.max().date()}",
    ]
    (DERIVED / "BUILD_REPORT.txt").write_text("\n".join(report) + "\n")
    print("\n".join(report))


if __name__ == "__main__":
    build()
