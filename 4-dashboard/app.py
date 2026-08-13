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


if __name__ == "__main__":
    app.run()
