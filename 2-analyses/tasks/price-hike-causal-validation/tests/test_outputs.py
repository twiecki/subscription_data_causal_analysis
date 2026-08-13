"""
Verifier for the price-hike-causal-validation task.

Grades artifacts only (never the chat): headline effect within the accepted
band around the hidden ground truth, estimand named, placebo-in-time sweep
run with the real date a clear outlier, reproducible code artifact present,
anticipation caveat discussed.
"""

import json
import math
import os
import re
import unittest

# True effect (hidden from the agent): the simulator applied a post-period
# subscribe-probability multiplier of 0.8425 => ~-15.75% on the daily rate.
ACCEPTED_RANGE = (-20.0, -10.0)
MIN_PLACEBO_DATES = 8
PLACEBO_Z_THRESHOLD = 2.0


def find(name):
    for path in (os.path.join("/root", name), name):
        if os.path.exists(path):
            return path
    return None


def load_json(name):
    path = find(name)
    if path is None:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


class TestResult(unittest.TestCase):
    def test_result_json_exists(self):
        self.assertIsNotNone(find("result.json"), "result.json not found in /root")

    def test_effect_in_accepted_range(self):
        result = load_json("result.json")
        self.assertIsInstance(result, dict, "result.json missing or invalid")
        self.assertIn("effect_pct", result, "result.json has no effect_pct")
        effect = float(result["effect_pct"])
        lo, hi = ACCEPTED_RANGE
        self.assertTrue(
            lo <= effect <= hi,
            f"effect_pct={effect:+.2f}% outside accepted range [{lo}, {hi}]",
        )

    def test_estimand_named(self):
        result = load_json("result.json") or {}
        estimand = result.get("estimand")
        self.assertIsInstance(estimand, str, "no estimand in result.json")
        self.assertGreaterEqual(
            len(estimand.strip()), 10, "estimand is not a meaningful sentence"
        )


class TestPlacebo(unittest.TestCase):
    def test_placebo_sweep_run(self):
        placebo = load_json("placebo.json")
        self.assertIsInstance(
            placebo, dict, "placebo.json missing — placebo-in-time sweep not run"
        )
        effects = placebo.get("placebo_effects_pct")
        self.assertIsInstance(effects, list, "placebo_effects_pct missing")
        effects = [float(e) for e in effects if e is not None and not math.isnan(float(e))]
        self.assertGreaterEqual(
            len(effects),
            MIN_PLACEBO_DATES,
            f"only {len(effects)} placebo dates (need {MIN_PLACEBO_DATES})",
        )

    def test_real_date_is_outlier(self):
        placebo = load_json("placebo.json") or {}
        effects = [
            float(e)
            for e in (placebo.get("placebo_effects_pct") or [])
            if e is not None and not math.isnan(float(e))
        ]
        real = placebo.get("real_effect_pct")
        self.assertIsNotNone(real, "real_effect_pct missing from placebo.json")
        self.assertGreaterEqual(len(effects), 2, "not enough placebo effects")
        mean = sum(effects) / len(effects)
        var = sum((e - mean) ** 2 for e in effects) / (len(effects) - 1)
        std = math.sqrt(var)
        self.assertGreater(std, 0.0, "placebo effects have zero spread")
        z = abs(float(real) - mean) / std
        self.assertGreaterEqual(
            z,
            PLACEBO_Z_THRESHOLD,
            f"real date z={z:.1f} not a clear outlier vs placebo distribution",
        )


class TestAuditability(unittest.TestCase):
    def test_code_artifact_exists(self):
        self.assertIsNotNone(
            find("analysis.py"),
            "analysis.py not found — inline-only analysis is not auditable",
        )

    def test_code_loads_the_provided_data(self):
        path = find("analysis.py")
        if path is None:
            self.skipTest("analysis.py missing (covered by test_code_artifact_exists)")
        code = open(path, errors="ignore").read()
        self.assertIn(
            "daily_aggregates_intervention.csv",
            code,
            "analysis.py does not read the provided dataset",
        )

    def test_memo_discusses_anticipation(self):
        path = find("memo.md")
        self.assertIsNotNone(path, "memo.md not found")
        memo = open(path, errors="ignore").read()
        self.assertTrue(
            re.search(r"anticipat", memo, re.I),
            "memo.md does not discuss anticipation effects (required by the contract)",
        )


if __name__ == "__main__":
    unittest.main()
