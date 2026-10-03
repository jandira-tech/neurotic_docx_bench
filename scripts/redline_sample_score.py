#!/usr/bin/env python3
"""Score two or more jubarte binaries against Word on a stratified sample of
the corpus's Word compares, the bench way (candidate and oracle both rendered
by soffice, `bench compare`).

    redline_sample_score.py --bin main=/tmp/jubarte-main --bin branch=/tmp/jubarte-x \\
        --n 200 --seed 1 --work /tmp/rss-200 [--sets a,b] [--jobs 6] [--ids FILE]

Pairs come from ``corpus/word/comparisons.csv`` (state
tracking_without_comments, both inputs present), the same number from each
corpus set as far as it holds them, keyed by the comparison id. The oracle is
the LibreOffice render of Word's redline from ``corpus/libreoffice`` when the
corpus has it, else Word's redline rendered by soffice here (the same
backend). Writes ``<work>/scores.json`` ({id: {set, bins…}}) and prints per
bin mean/median, the paired difference between the first bin and each other
with a bootstrap 95 % interval, wins and losses beyond 0.5, and the same by
set. Re-running with the same work dir reuses generated docx and PDFs.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import statistics
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD = ROOT / "corpus" / "word"
LO_PDF = ROOT / "corpus" / "libreoffice" / "tracking_without_comments" / "pdf"


def pairs(sets):
    docs = {r["id"]: WORD / r["docx"] for r in csv.DictReader((WORD / "documents.csv").open())}
    out = []
    for r in csv.DictReader((WORD / "comparisons.csv").open()):
        if r["state"] != "tracking_without_comments":
            continue
        s = r["sets"].split(";")[0] if r["sets"] else "?"
        if sets and not (set(r["sets"].split(";")) & sets):
            continue
        base, nxt = docs.get(r["base_id"]), docs.get(r["next_id"])
        if base is None or nxt is None or not base.exists() or not nxt.exists():
            continue
        out.append({"id": r["id"], "set": s, "base": base, "next": nxt, "redline": WORD / r["docx"]})
    return out


def sample(ps, n, seed):
    by = defaultdict(list)
    for p in ps:
        by[p["set"]].append(p)
    rng = random.Random(seed)
    for v in by.values():
        rng.shuffle(v)
    chosen, i = [], 0
    while len(chosen) < n and any(by.values()):
        for s in sorted(by):
            if by[s] and len(chosen) < n:
                chosen.append(by[s].pop())
        i += 1
    return chosen


def sh(cmd, **kw):
    r = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, **kw)
    if r.returncode:
        print(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stderr[-800:]}", file=sys.stderr)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", action="append", required=True, help="NAME=PATH (first is the reference)")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--sets")
    ap.add_argument("--ids", help="file of comparison ids (one per line) instead of a sample")
    ap.add_argument("--work", required=True)
    ap.add_argument("--jobs", type=int, default=6)
    args = ap.parse_args()
    bins = [b.split("=", 1) for b in args.bin]
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    ps = pairs(set(args.sets.split(",")) if args.sets else None)
    if args.ids:
        want = set(Path(args.ids).read_text().split())
        chosen = [p for p in ps if p["id"] in want]
    else:
        chosen = sample(ps, args.n, args.seed)
    (work / "ids.txt").write_text("\n".join(p["id"] for p in chosen) + "\n")
    print(f"{len(chosen)} pairs from {len({p['set'] for p in chosen})} sets")

    # oracle PDFs
    oracle = work / "oracle"
    oracle.mkdir(exist_ok=True)
    to_render = work / "oracle_src"
    to_render.mkdir(exist_ok=True)
    missing = 0
    for p in chosen:
        dst = oracle / f"{p['id']}_redline.pdf"
        if dst.exists():
            continue
        lo = LO_PDF / (p["redline"].stem + ".pdf")
        if lo.exists():
            shutil.copy2(lo, dst)
        else:
            shutil.copy2(p["redline"], to_render / f"{p['id']}_redline.docx")
            missing += 1
    if missing:
        print(f"rendering {missing} oracle redlines with soffice")
        sh(["uv", "run", "bench", "render", str(to_render), str(work / "oracle_render"), "--backend", "soffice", "--jobs", str(args.jobs)])
        for f in (work / "oracle_render" / "pdf").glob("*.pdf"):
            shutil.copy2(f, oracle / f.name)

    scores = {p["id"]: {"set": p["set"]} for p in chosen}
    for name, path in bins:
        cdir = work / f"cand_{name}"
        ddir = cdir / "docx"
        ddir.mkdir(parents=True, exist_ok=True)
        fails = {}

        def gen(p, name=name, path=path, ddir=ddir, fails=fails):
            out = ddir / f"{p['id']}_{name}_redline.docx"
            if out.exists():
                return
            r = subprocess.run([path, str(p["base"]), str(p["next"]), "-o", str(out), "--force", "--quiet"],
                               capture_output=True, text=True)
            if r.returncode or not out.exists():
                fails[p["id"]] = (r.stderr or r.stdout or "no output").strip()[-200:]

        with ThreadPoolExecutor(args.jobs) as ex:
            list(ex.map(gen, chosen))
        print(f"{name}: {len(fails)} generation failures")
        sh(["uv", "run", "bench", "render", str(ddir), str(cdir), "--backend", "soffice", "--jobs", str(args.jobs)])
        sj = cdir / "scores.json"
        sh(["uv", "run", "bench", "compare", str(cdir / "pdf"), str(oracle), "--tool", name, "--jobs", str(args.jobs), "--json", str(sj)])
        got = json.loads(sj.read_text()) if sj.exists() else {}
        for p in chosen:
            scores[p["id"]][name] = 0.0 if p["id"] in fails else got.get(p["id"])
    (work / "scores.json").write_text(json.dumps(scores, indent=1))
    report(scores, [b[0] for b in bins])


def report(scores, names):
    ref = names[0]
    rows = {k: v for k, v in scores.items() if all(v.get(n) is not None for n in names)}
    print(f"\nscored {len(rows)} of {len(scores)} pairs")
    print(f"{'bin':>10} {'mean':>7} {'median':>7} {'<50':>5} {'>=90':>5}")
    for n in names:
        xs = [v[n] for v in rows.values()]
        print(f"{n:>10} {statistics.mean(xs):7.2f} {statistics.median(xs):7.2f} {sum(x < 50 for x in xs):5} {sum(x >= 90 for x in xs):5}")
    rng = random.Random(7)
    for n in names[1:]:
        d = [v[n] - v[ref] for v in rows.values()]
        boots = sorted(statistics.mean(rng.choices(d, k=len(d))) for _ in range(2000))
        wins = sum(x > 0.5 for x in d)
        losses = sum(x < -0.5 for x in d)
        print(f"\n{n} − {ref}: mean {statistics.mean(d):+.3f} [95 % {boots[50]:+.3f}, {boots[1949]:+.3f}]  wins {wins}  losses {losses}  unchanged {len(d) - wins - losses}")
        by = defaultdict(list)
        for v in rows.values():
            by[v["set"]].append(v[n] - v[ref])
        for s, ds in sorted(by.items()):
            print(f"   {s:28} n={len(ds):3} mean {statistics.mean(ds):+.3f}  wins {sum(x > 0.5 for x in ds)}  losses {sum(x < -0.5 for x in ds)}")
        worst = sorted(rows.items(), key=lambda kv: kv[1][n] - kv[1][ref])[:5]
        print("   largest losses:", [(k, round(v[n] - v[ref], 2)) for k, v in worst if v[n] - v[ref] < -0.5])
        best = sorted(rows.items(), key=lambda kv: kv[1][ref] - kv[1][n])[:5]
        print("   largest wins:", [(k, round(v[n] - v[ref], 2)) for k, v in best if v[n] - v[ref] > 0.5])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        scores = json.loads(Path(sys.argv[2]).read_text())
        report(scores, sys.argv[3].split(","))
    else:
        main()
