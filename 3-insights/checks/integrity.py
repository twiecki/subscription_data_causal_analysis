#!/usr/bin/env python3
"""Workspace integrity suite — the repo is the agent's memory, and memory rots.

Five checks, each answering a question you'd otherwise notice by accident:

  1 references   Does every cited insight ID ([[i-xxxx]] / [[k-xxxx]]) resolve
                 in insights/registry.md (or alias.tsv)? Sparse IDs make
                 typos loud instead of silently valid.
  2 binding      Does each registry source still exist AND still have the
                 hash recorded at bind time? An existence check finds broken
                 links; only a binding check finds *wrong* ones.
  3 staleness    Is every derived artifact newer than its sources? A stale
                 derivative is worse than none - it looks authoritative.
  4 copy-drift   Is the task's metric-contract.yml byte-identical to the
                 canonical contracts/metric-contract.yml? One fact, one place.
  5 superseded   Does any living doc cite a superseded insight as support?

Run:  python checks/integrity.py [--rebind]
Exit: non-zero on any failure (CI gate).
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "3-insights/registry.md"
ALIAS = ROOT / "3-insights/alias.tsv"
LIVING = [ROOT / "README.md", ROOT / "1-data/business-context.md", *ROOT.glob("2-analyses/*/[!t]*.md"), *ROOT.glob("4-dashboard/**/*.py")]
DERIVED = ROOT / "1-data/derived"
REBIND = "--rebind" in sys.argv
failures: list[str] = []


def sha12(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:12]


def parse_registry():
    rows = []
    for line in REGISTRY.read_text().splitlines():
        m = re.match(r"\|\s*([ik]-[0-9a-f]{4})\s*\|([^|]*)\|([^|]*)\|\s*([^|]*?)\s*\|([^|]*)\|\s*([0-9a-f]{12}|PENDING)\s*\|", line)
        if m:
            rows.append({"id": m.group(1), "status": m.group(2).strip(),
                         "source": m.group(4).strip(), "hash": m.group(6), "line": line})
    return rows


rows = parse_registry()
ids = {r["id"] for r in rows}
aliases = {l.split("\t")[0] for l in ALIAS.read_text().splitlines()[1:] if l.strip()}

# 1 references
for doc in LIVING:
    for ref in re.findall(r"\[\[([ik]-[0-9a-f]{4})\]\]", doc.read_text()):
        if ref not in ids and ref not in aliases:
            failures.append(f"[references] {doc.relative_to(ROOT)} cites {ref} — resolves to nothing")

# 2 binding (+ optional rebind)
text = REGISTRY.read_text()
for r in rows:
    src = ROOT / r["source"]
    if not src.exists():
        failures.append(f"[binding] {r['id']} source missing: {r['source']}")
        continue
    actual = sha12(src)
    if r["hash"] == "PENDING" or (REBIND and r["hash"] != actual):
        text = text.replace(r["line"], r["line"].replace(r["hash"], actual))
    elif r["hash"] != actual:
        failures.append(f"[binding] {r['id']} source {r['source']} changed since bind "
                        f"({r['hash']} -> {actual}) — re-verify the claim, then --rebind")
if text != REGISTRY.read_text():
    REGISTRY.write_text(text)
    print("[binding] wrote updated hashes to registry")

# 3 staleness
if DERIVED.exists():
    raws = list((ROOT / "1-data/raw").glob("*")) + [ROOT / "1-data/build_data.py"]
    newest_src = max(p.stat().st_mtime for p in raws)
    for d in DERIVED.glob("*.csv"):
        if d.stat().st_mtime < newest_src:
            failures.append(f"[staleness] {d.relative_to(ROOT)} is older than its sources — rebuild the layer")

# 4 copy-drift
task_contract = ROOT / "2-analyses/tasks/price-hike-causal-validation/environment/metric-contract.yml"
if task_contract.exists() and sha12(task_contract) != sha12(ROOT / "1-data/semantic-layer/conv_rate.yml"):
    failures.append("[copy-drift] task metric-contract.yml differs from 1-data/semantic-layer/conv_rate.yml — one fact, one place")

# 5 superseded citations (a living doc may mention a superseded ID only in its own supersession note)
superseded = {r["id"] for r in rows if r["status"].startswith("superseded")}
for doc in LIVING:
    if doc.name == "blind-run-claim.md":
        continue
    body = doc.read_text()
    for sid in superseded:
        for line in body.splitlines():
            if f"[[{sid}]]" in line and "superseded" not in line.lower() and "refut" not in line.lower():
                failures.append(f"[superseded] {doc.relative_to(ROOT)} cites {sid} as if it were live")

if failures:
    print("\n".join(failures))
    print(f"\nintegrity: {len(failures)} failure(s)")
    sys.exit(1)
print(f"integrity: all 5 checks green ({len(rows)} registered artifacts, {len(LIVING)} living docs scanned)")
