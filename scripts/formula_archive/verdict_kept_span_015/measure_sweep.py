#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Which aligner's kept fraction separates Word's verdicts with one constant, across every wave?"""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "/tmp"); sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
from aligners import heckel, lcs_dp, greedy_lcr, left_greedy, patience, min_run

base = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow")
cache = Path("/tmp/pair_texts.json")
if cache.exists():
    pairs = json.load(open(cache))
else:
    pairs = []
    for wd in sorted((base / "probes").iterdir()):
        if not ((wd / "word").is_dir() and (wd / "A").is_dir()) or wd.name == "wave8":
            continue
        for r in sorted((wd / "word").glob("*.docx")):
            stem = r.name.split("__vs__")[0]
            pa, pb = wd / "A" / f"{stem}.docx", wd / "B" / f"{stem}.docx"
            if not (pa.exists() and pb.exists()):
                continue
            A, B, Rp = ra.paragraphs(pa), ra.paragraphs(pb), ra.paragraphs(r)
            ti = max(range(len(A)), key=lambda i: len(A[i].text("orig")))
            ta, tb = A[ti].text("orig"), (B[ti].text("rev") if ti < len(B) else "")
            vs = [v for v in ra.verdicts(Rp) if v.verdict != "unchanged" and (v.a_index == ti or (v.a_index is None and v.b_index == ti))]
            verdict = "/".join(sorted({v.verdict for v in vs})) or "unchanged"
            if verdict in ("word-level", "replaced"):
                pairs.append({"wave": wd.name, "name": stem, "ta": ta, "tb": tb, "W": verdict == "word-level"})
    for name, pa, pb, pr, idx in [("letters p5", "inputs/55_Traversal_cover_letter.docx", "inputs/56_Flow_cover_letter.docx", "word-docx/2_c55-v-c56__word.docx", 5)] + \
            [(f"metadata p{i}", "inputs/55_Traversal_metadata.docx", "inputs/56_Flow_metadata.docx", "word-docx/3_m55-v-m56__word.docx", i) for i in (3, 6, 9, 12, 14)]:
        A, B, Rp = ra.paragraphs(base / pa), ra.paragraphs(base / pb), ra.paragraphs(base / pr)
        ta, tb = A[idx].text("orig"), B[idx].text("rev")
        vs = [v for v in ra.verdicts(Rp) if v.verdict != "unchanged" and (v.a_index == idx or (v.a_index is None and v.b_index == idx))]
        pairs.append({"wave": "real", "name": name, "ta": ta, "tb": tb, "W": "word-level" in {v.verdict for v in vs}})
    json.dump(pairs, open(cache, "w"))
print(f"{len(pairs)} pairs")

ALIGNERS = {
    "lcs": lambda a, b: lcs_dp(a, b),
    "greedy-lcr": lambda a, b: greedy_lcr(a, b),
    "patience": lambda a, b: patience(a, b),
    "heckel": lambda a, b: heckel(a, b),
    "heckel-rec": lambda a, b: heckel(a, b, True),
    "left-greedy": lambda a, b: left_greedy(a, b),
    "left-greedy w10": lambda a, b: left_greedy(a, b, 10),
    "left-greedy w20": lambda a, b: left_greedy(a, b, 20),
    "left-greedy w40": lambda a, b: left_greedy(a, b, 40),
    "left-greedy runs≥2": lambda a, b: min_run(left_greedy(a, b), 2),
    "left-greedy w20 runs≥2": lambda a, b: min_run(left_greedy(a, b, 20), 2),
    "greedy-lcr runs≥2": lambda a, b: min_run(greedy_lcr(a, b), 2),
    "lcs runs≥2": lambda a, b: min_run(lcs_dp(a, b), 2),
}
res = defaultdict(dict)
for p in pairs:
    a, b = ra.words(p["ta"]), ra.words(p["tb"])
    mx = max(len(p["ta"]), len(p["tb"]), 1)
    for name, fn in ALIGNERS.items():
        s = fn(a, b)
        res[name][(p["wave"], p["name"])] = sum(len(a[i]) for i, _ in s) / mx
json.dump({k: {f"{w}|{n}": v for (w, n), v in d.items()} for k, d in res.items()}, open("/tmp/measure_sweep.json", "w"))

def best(pts):
    cands = sorted({v for v, _ in pts})
    return max(((sum((v >= t) == w for v, w in pts), t) for t in cands + [cands[-1] + 1e-9]), key=lambda x: x[0])
print(f"\n{'aligner':24} {'acc':>6} {'t':>7} {'errors':>6}  per-wave accuracy at the global t")
waves = sorted({p["wave"] for p in pairs})
for name in ALIGNERS:
    pts = [(res[name][(p["wave"], p["name"])], p["W"]) for p in pairs]
    acc, t = best(pts)
    per = []
    for w in waves:
        ps = [(res[name][(p["wave"], p["name"])], p["W"]) for p in pairs if p["wave"] == w]
        per.append(f"{w[:7]}={sum((v >= t) == ok for v, ok in ps) / len(ps):.2f}")
    print(f"{name:24} {acc / len(pts):6.3f} {t:7.4f} {len(pts) - acc:6}  {' '.join(per)}")