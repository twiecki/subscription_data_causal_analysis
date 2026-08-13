#!/usr/bin/env python3
"""DiD / synthetic-control feasibility check for the price hike — run r-123d."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

EXPECTED_COLUMNS = [
    "date", "subscriber_pool", "signups", "conversions",
    "conv_rate", "post", "source_file", "source_row",
]
INTERVENTION_DATE = "2026-04-01"  # [[k-a1f4]]

PROVENANCE_COLS = {"source_file", "source_row"}
TREATMENT_COLS = {"post"}
OUTCOME_COLS = {"conv_rate"}
COUNT_COLS = {"subscriber_pool", "signups", "conversions"}
TIME_COLS = {"date"}


def classify(col: str) -> str:
    if col in TIME_COLS:
        return "time index"
    if col in OUTCOME_COLS:
        return "outcome"
    if col in COUNT_COLS:
        return "count"
    if col in TREATMENT_COLS:
        return "treatment indicator"
    if col in PROVENANCE_COLS:
        return "provenance"
    return "unclassified"


def main() -> int:
    print("=== 1. Load derived layer ===")
    df = pd.read_csv(ROOT / "1-data/derived/daily.csv", parse_dates=["date"])
    assert list(df.columns) == EXPECTED_COLUMNS, f"unexpected columns: {list(df.columns)}"
    n_rows = len(df)
    date_min = df["date"].min().date().isoformat()
    date_max = df["date"].max().date().isoformat()
    print(f"rows = {n_rows}")
    print(f"date range = {date_min} .. {date_max}")
    print(f"intervention date = {INTERVENTION_DATE}")

    print("\n=== 2. Candidate control dimensions ===")
    columns_examined = {}
    candidate_unit_columns = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        n_unique = int(df[col].nunique())
        cls = classify(col)
        columns_examined[col] = {
            "dtype": dtype,
            "n_unique": n_unique,
            "classification": cls,
        }
        is_candidate = (
            cls not in {"time index", "outcome", "count", "treatment indicator", "provenance"}
            and n_unique >= 2
        )
        if is_candidate:
            candidate_unit_columns.append(col)
        print(f"  {col}: dtype={dtype}, n_unique={n_unique}, classification={cls}, candidate={is_candidate}")
    print(f"candidate_unit_columns = {candidate_unit_columns}")

    print("\n=== 3. DiD design matrix rank check ===")
    n = len(df)
    intercept = np.ones(n)
    treated = np.ones(n)
    post = df["post"].to_numpy(dtype=float)
    interaction = treated * post
    X = np.column_stack([intercept, treated, post, interaction])
    rank = int(np.linalg.matrix_rank(X))
    rank_required = 4
    print(f"design matrix X = [1, treated, post, treated*post], shape = {X.shape}")
    print(f"rank(X) = {rank}, required = {rank_required}")
    print("collinearities: treated == intercept (treated is 1 for all rows); treated*post == post")

    print("\n=== 4. Synthetic control donor check ===")
    n_donors = len(candidate_unit_columns)
    print(f"n_donors = {n_donors}")
    print("simplex weight optimization over an empty donor pool is infeasible: the feasible set is empty")

    print("\n=== 5. Guarded causalpy attempt ===")
    causalpy_available = False
    causalpy_error = None
    try:
        import causalpy as cp
        causalpy_available = True
        try:
            cp.DifferenceInDifferences(
                df,
                formula="conv_rate ~ 1 + post*group",
                time_variable_name="date",
                group_variable_name="group",
            )
        except Exception as exc:
            causalpy_error = str(exc)
            print(f"causalpy available but DiD failed: {causalpy_error}")
    except ImportError:
        print("causalpy not installed; skipping (causalpy_available=false, causalpy_error=None)")

    print("\n=== 6. Write failure.json ===")
    result = {
        "run_id": "r-123d",
        "analysis": "price-hike-did-failure",
        "data_source": "1-data/derived/daily.csv",
        "n_rows": n_rows,
        "date_range": [date_min, date_max],
        "intervention_fact": "k-a1f4",
        "outcome_fact": "k-77b0",
        "candidate_unit_columns": candidate_unit_columns,
        "columns_examined": columns_examined,
        "did": {
            "feasible": False,
            "design_matrix_rank": rank,
            "rank_required": rank_required,
            "reason": "treated==1 for all rows; interaction collinear with post; estimand undefined",
        },
        "synthetic_control": {
            "feasible": False,
            "n_donors": n_donors,
            "reason": "donor pool empty; simplex weight optimization has empty feasible set",
        },
        "causalpy_available": causalpy_available,
        "causalpy_error": causalpy_error,
        "fallback_that_worked": "i-3fa2",
        "verdict": "DiD and synthetic control structurally unidentifiable on single-aggregate data; negative result registered as k-1231",
    }
    out_path = HERE / "failure.json"
    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {out_path.relative_to(ROOT)}")

    print("\n=== 7. Verdict ===")
    print("DiD and synthetic control are structurally unidentifiable here; the design that worked is Bayesian ITS [[i-3fa2]].")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
