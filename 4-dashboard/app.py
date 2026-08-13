import marimo

__generated_with = "0.23.4"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import re
    from pathlib import Path

    import marimo as mo
    import pandas as pd

    ROOT = Path(__file__).resolve().parents[1]
    return ROOT, mo, pd, re


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Repo dashboard

    The living view over this repo's artifacts: the insights registry, the
    derived data layer, and the latest integrity/eval state. Deployable as a
    static page via `marimo export html-wasm dashboard/app.py`.
    """)
    return


@app.cell(hide_code=True)
def _(ROOT, mo, pd, re):
    _rows = []
    for _line in (ROOT / "3-insights/registry.md").read_text().splitlines():
        _m = re.match(r"\|\s*([ik]-[0-9a-f]{4})\s*\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|", _line)
        if _m:
            _rows.append({"id": _m.group(1), "status": _m.group(2).strip(),
                          "claim": _m.group(3).strip(), "source": _m.group(4).strip()})
    insights = pd.DataFrame(_rows)
    _active = (insights.status == "active").sum() + (insights.status == "canonical").sum()
    _sup = insights.status.str.startswith("superseded").sum()
    mo.hstack([
        mo.stat(str(len(insights)), label="registered artifacts"),
        mo.stat(str(_active), label="live"),
        mo.stat(str(_sup), label="superseded"),
    ])
    return (insights,)


@app.cell(hide_code=True)
def _(insights):
    insights
    return


@app.cell(hide_code=True)
def _(ROOT, mo, pd):
    _p = ROOT / "1-data/derived/daily.csv"
    if _p.exists():
        _df = pd.read_csv(_p, parse_dates=["date"])
        _out = mo.vstack([
            mo.md(f"## Data layer\n`{len(_df)}` rows · {_df.date.min().date()} → {_df.date.max().date()} · provenance on every row"),
            mo.md("```\n" + (ROOT / "1-data/derived/BUILD_REPORT.txt").read_text() + "```"),
        ])
    else:
        _out = mo.md("## Data layer\n_not built — run `python 1-data/build_data.py`_")
    _out
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What we learned about this dataset

    Every figure below visualizes a **registered insight** — the plot cites
    the ID, the ID carries the evidence.
    """)
    return


@app.cell(hide_code=True)
def _(ROOT, mo, pd):
    import matplotlib.pyplot as plt
    import numpy as np

    _df = pd.read_csv(ROOT / "1-data/derived/daily.csv", parse_dates=["date"])
    _df["rate_pct"] = 100 * _df["conv_rate"]
    _t0 = pd.Timestamp("2026-04-01")
    _fit = _df[(_df.post == 0) & (_df.date >= _df.date.min() + pd.Timedelta(days=30))]
    _x = (_fit.date - _t0).dt.days.to_numpy()
    _b1, _b0 = np.polyfit(_x, _fit.rate_pct.to_numpy(), 1)
    _xa = (_df.date - _t0).dt.days.to_numpy()
    _cf = _b0 + _b1 * _xa

    _fig, _ax = plt.subplots(figsize=(9.5, 3.4))
    _ax.plot(_df.date, _df.rate_pct, ".", ms=2.5, color="#8A6B70", alpha=0.55, label="daily conversion rate")
    _mask = _xa >= 0
    _ax.plot(_df.date[_mask], _cf[_mask], "--", color="#5C5C5C", lw=1.6, label="no-hike counterfactual (linear pre-trend)")
    _ax.fill_between(_df.date[_mask], _df.rate_pct[_mask], _cf[_mask], color="#6D2E46", alpha=0.18)
    _ax.axvline(_t0, color="#6D2E46", lw=1.6)
    _ax.set_ylabel("conv rate (%)")
    _ax.set_ylim(0, min(1.0, _df.rate_pct.quantile(0.995) * 1.4))
    _ax.text(_t0, 0.72, "  price +33 %  [[k-a1f4]]", color="#6D2E46", fontsize=9,
             va="top", transform=_ax.get_xaxis_transform())
    _ax.legend(loc="upper right", fontsize=8, frameon=False)
    _ax.set_title("The intervention and its gap — the story behind [[i-3fa2]]", fontsize=11)
    _fig.tight_layout()
    from io import BytesIO as _BytesIO
    from base64 import b64encode as _b64
    _buf = _BytesIO()
    _fig.savefig(_buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(_fig)
    _src = "data:image/png;base64," + _b64(_buf.getvalue()).decode()
    mo.vstack([mo.md(f'<img src="{_src}" style="max-width:100%">'), mo.md("*Shaded: observed vs. counterfactual after the hike. The validated estimate lives in [[i-3fa2]]; this figure is orientation, not inference — the placebo sweep and sensitivity table are the evidence.*")])
    return np, plt


@app.cell(hide_code=True)
def _(mo, np, plt):
    _rng = np.random.default_rng(20260401)
    _eff = _rng.normal(-0.156, (0.192 - 0.124) / (2 * 1.96), 20_000)
    _uplift = (1 + 0.33) * (1 + _eff) - 1

    _fig, (_a1, _a2) = plt.subplots(1, 2, figsize=(9.5, 3.0))
    _a1.hist(100 * _eff, bins=60, color="#8A6B70", alpha=0.85)
    _a1.axvline(0, color="#5C5C5C", lw=1)
    _a1.set_title("conversion effect [[i-3fa2]]  ~ −15.6 %", fontsize=10)
    _a1.set_yticks([])
    _a2.hist(100 * _uplift, bins=60, color="#6D2E46", alpha=0.85)
    _a2.axvline(0, color="#5C5C5C", lw=1)
    _a2.set_title("revenue uplift [[i-b7d3]]  ~ +12.2 %,  P(>0) ≈ 1", fontsize=10)
    _a2.set_yticks([])
    for _a in (_a1, _a2):
        _a.set_xlabel("%")
        _a.spines[["top", "right", "left"]].set_visible(False)
    _fig.tight_layout()
    from io import BytesIO as _BytesIO
    from base64 import b64encode as _b64
    _buf = _BytesIO()
    _fig.savefig(_buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(_fig)
    _src = "data:image/png;base64," + _b64(_buf.getvalue()).decode()
    mo.vstack([mo.md(f'<img src="{_src}" style="max-width:100%">'), mo.md("*The decision in one row: conversions **down** — revenue **up**. Fewer subscriptions, each worth ~33 % more; the posterior of [[i-3fa2]] propagated into the business quantity ([[i-b7d3]], seeded MC).*")])
    return


if __name__ == "__main__":
    app.run()
