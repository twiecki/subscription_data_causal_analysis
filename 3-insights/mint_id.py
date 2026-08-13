#!/usr/bin/env python3
"""Mint a fresh artifact ID — rolled, not counted.

Why rolled: sequential IDs encode a *position*; any renumbering silently
rebinds every older citation, and in a dense number range a typo usually
hits another *valid* ID. Random IDs in a sparse space (65,536 addresses,
a handful used) make both failures loud: a typo resolves to nothing and
the integrity suite flags it.

Rules encoded here:
  - collision-checked against the insights registry, the alias table,
    and RUNS.csv — across ALL kinds, so no token ever means two things
  - IDs are never reused; retired names go to alias.tsv (append-only)
  - the `i-`/`k-`/`r-` namespace is reserved: never hand-write lookalike
    tokens in documents (that's how bulk rewrites mis-resolve)

Usage:  python 3-insights/mint_id.py [i|k|r]   (default: i)
"""
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIND = (sys.argv[1] if len(sys.argv) > 1 else "i").strip("-")
assert KIND in ("i", "k", "r"), "kind must be i (insight), k (canonical), r (run)"

taken = set()
for f in [ROOT / "3-insights/registry.md", ROOT / "3-insights/alias.tsv",
          ROOT / "2-analyses/RUNS.csv"]:
    if f.exists():
        taken |= set(re.findall(r"\b[ikr]-[0-9a-f]{4}\b", f.read_text()))

while True:
    candidate = f"{KIND}-{secrets.token_hex(2)}"
    if candidate not in taken:
        print(candidate)
        break
