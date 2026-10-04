#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Report `bench docx-to-pdf` JSON results per corpus set and state, and the
paired difference between two or more results on the documents they share.

    pdf_sample_report.py NAME=results.json [NAME=other.json ...] [--sets a,b] [--worst N]

The first result is the reference. Per-doc scores are keyed by the bench's
stem `<state>__<id>_<stem>`; the id joins ``corpus/word/documents.csv`` for
the document's state and first set. Prints per bin: n, mean, median, <50,
>=90, generate failures; then per (state) and per (set) means; then for each
other bin the paired mean difference with a bootstrap 95 % interval, wins and
losses beyond 0.5, and the largest losses and wins by stem.
"""
from __future__ import annotations

import csv
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD = ROOT / "corpus" / "word"


def docs():
    out = {}
    for r in csv.DictReader((WORD / "documents.csv").open()):
        out[r["id"]] = (r["state"], r["sets"].split(";")[0] if r["sets"] else "?")
    return out


def load(path):
    d = json.loads(Path(path).read_text())
    tools = d["tools"]
    tool = next(iter(tools.values()))
    fails = {f["doc"] for f in tool.get("generate_failures", [])}
    scores = dict(tool["per_doc"])
    for f in fails:
        scores.setdefault(f, 0.0)
    return scores, fails


def main(argv):
    sets = None
    worst = 8
    bins = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--sets":
            sets = set(argv[i + 1].split(",")); i += 2; continue
        if a == "--worst":
            worst = int(argv[i + 1]); i += 2; continue
        name, path = a.split("=", 1)
        bins.append((name, *load(path)))
        i += 1
    meta = docs()

    def info(stem):
        state, rest = stem.split("__", 1)
        did = rest.split("_", 1)[0]
        return meta.get(did, (state, "?"))

    common = set.intersection(*(set(b[1]) for b in bins))
    if sets:
        common = {s for s in common if info(s)[1] in sets}
    common = sorted(common)
    print(f"{len(common)} documents shared by {len(bins)} result(s)")
    print(f"{'bin':>10} {'mean':>7} {'median':>7} {'<50':>5} {'>=90':>5} {'=100':>5} {'fails':>6}")
    for name, sc, fails in bins:
        xs = [sc[s] for s in common]
        print(f"{name:>10} {statistics.mean(xs):7.2f} {statistics.median(xs):7.2f} {sum(x < 50 for x in xs):5} {sum(x >= 90 for x in xs):5} {sum(x >= 99.99 for x in xs):5} {len([f for f in fails if f in common]):6}")
    for label, idx in (("state", 0), ("set", 1)):
        print(f"\nby {label}:" + "".join(f" {n:>9}" for n, _, _ in bins))
        groups = defaultdict(list)
        for s in common:
            groups[info(s)[idx]].append(s)
        for g, ss in sorted(groups.items()):
            print(f"  {g:28} n={len(ss):4}" + "".join(f" {statistics.mean(sc[s] for s in ss):9.2f}" for _, sc, _ in bins))
    ref_name, ref, _ = bins[0]
    rng = random.Random(7)
    for name, sc, _ in bins[1:]:
        d = [sc[s] - ref[s] for s in common]
        boots = sorted(statistics.mean(rng.choices(d, k=len(d))) for _ in range(2000))
        wins = sum(x > 0.5 for x in d)
        losses = sum(x < -0.5 for x in d)
        print(f"\n{name} − {ref_name}: mean {statistics.mean(d):+.3f} [95 % {boots[50]:+.3f}, {boots[1949]:+.3f}]  wins {wins}  losses {losses}  unchanged {len(d) - wins - losses}")
        by = defaultdict(list)
        for s in common:
            by[info(s)[1]].append(sc[s] - ref[s])
        for g, ds in sorted(by.items()):
            print(f"   {g:28} n={len(ds):4} mean {statistics.mean(ds):+.3f}  wins {sum(x > 0.5 for x in ds)}  losses {sum(x < -0.5 for x in ds)}")
        order = sorted(common, key=lambda s: sc[s] - ref[s])
        print("   largest losses:", [(s[:48], round(sc[s] - ref[s], 2)) for s in order[:worst] if sc[s] - ref[s] < -0.5])
        print("   largest wins:", [(s[:48], round(sc[s] - ref[s], 2)) for s in order[::-1][:worst] if sc[s] - ref[s] > 0.5])
    if len(bins) == 1:
        order = sorted(common, key=lambda s: ref[s])
        print("\nlowest:", [(s[:60], round(ref[s], 1)) for s in order[:worst]])


if __name__ == "__main__":
    main(sys.argv[1:])
