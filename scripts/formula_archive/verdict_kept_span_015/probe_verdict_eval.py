#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Baseline: jubarte's paragraph verdicts against Word's on the probe sets.
Usage: probe_verdict_eval.py [--bin PATH] [--out DIR] [--csv ROWS] [--force] PROBE_DIR...
Use a fresh --out per binary: existing outputs are reused unless --force.
Runs `jubarte A B -o OUT` per pair (skips existing outputs unless --force), then
classifies every changed paragraph in Word's redline and in jubarte's with
redline_anatomy.verdicts and reports agreement per set and a confusion matrix."""
import argparse, csv, subprocess, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import redline_anatomy as ra

ap = argparse.ArgumentParser()
ap.add_argument("dirs", nargs="+")
ap.add_argument("--bin", default="/Users/arthrod/T/jubarte-redlines/target/release/jubarte")
ap.add_argument("--out", default="/tmp/jub")
ap.add_argument("--force", action="store_true")
ap.add_argument("--jobs", type=int, default=8)
ap.add_argument("--csv", default=None)
args = ap.parse_args()

def run(job):
    a, b, o = job
    if o.exists() and not args.force:
        return o, None
    o.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([args.bin, str(a), str(b), "-o", str(o), "--force", "-q"], capture_output=True, text=True)
    return o, (r.returncode, r.stderr.strip()[-300:]) if r.returncode else None

def changed(paras):
    """verdict per changed paragraph, keyed by original index (or 'ins:<b>' for inserted)."""
    out = {}
    for v in ra.verdicts(paras):
        if v.verdict in ("unchanged", "mark-only"):
            continue
        key = ("a", v.a_index) if v.a_index is not None else ("b", v.b_index)
        out[key] = v.verdict
    return out

rows = []
for d in args.dirs:
    P = Path(d); name = P.name
    jobs = []
    for a in sorted((P / "A").glob("*.docx")):
        n = a.stem
        b = P / "B" / a.name
        wr = sorted((P / "word").glob(f"{n}__vs__*.docx"))
        if not b.exists() or not wr:
            continue
        jobs.append((a, b, Path(args.out) / name / f"{n}.docx", wr[0]))
    with ThreadPoolExecutor(args.jobs) as ex:
        results = list(ex.map(run, [(a, b, o) for a, b, o, _ in jobs]))
    for (a, b, o, wr), (_, err) in zip(jobs, results):
        if err:
            rows.append({"set": name, "name": a.stem, "para": "", "word": "", "jubarte": f"ERROR {err[0]}", "agree": False}); continue
        W = changed(ra.paragraphs(wr)); J = changed(ra.paragraphs(o))
        keys = sorted(set(W) | set(J), key=str)
        for k in keys:
            w, j = W.get(k, "unchanged"), J.get(k, "unchanged")
            rows.append({"set": name, "name": a.stem, "para": f"{k[0]}{k[1]}", "word": w, "jubarte": j, "agree": w == j})

if args.csv:
    with open(args.csv, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
by = defaultdict(list)
for r in rows:
    by[r["set"]].append(r)
print(f"{'set':10} {'paras':>6} {'agree':>6} {'rate':>6}   disagreements (word→jubarte)")
tot = 0; ok = 0
for s, rs in by.items():
    c = Counter((r["word"], r["jubarte"]) for r in rs if not r["agree"])
    n = len(rs); k = sum(r["agree"] for r in rs); tot += n; ok += k
    print(f"{s:10} {n:6} {k:6} {k / max(n, 1):6.3f}   " + ", ".join(f"{w}→{j} {c_}" for (w, j), c_ in c.most_common()))
print(f"{'ALL':10} {tot:6} {ok:6} {ok / max(tot, 1):6.3f}")
