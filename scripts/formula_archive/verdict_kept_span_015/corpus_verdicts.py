#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""jubarte's paragraph verdicts against Word's on every Word compare of the corpus.

    corpus_verdicts.py --bin BIN --out DIR [--csv FILE] [--sets a,b] [--limit N] [--jobs N]

Walks ``corpus/word/comparisons.csv`` (every Word redline with its base and
next document per ``documents.csv``), runs ``BIN base next -o OUT`` per pair
(existing outputs are kept unless ``--force``), classifies every changed
paragraph of Word's redline and of jubarte's with
``redline_anatomy.verdicts`` and reports agreement overall, per set, and the
confusion of the disagreements. The CSV holds one row per changed paragraph
(set, key, para, word, jubarte, agree); a jubarte failure is one row with
``jubarte = ERROR``.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORD = ROOT / "corpus" / "word"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import redline_anatomy as ra  # noqa: E402


def pairs(sets: set[str] | None):
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
        out.append((s, r["key"], base, nxt, WORD / r["docx"]))
    return out


def run(job):
    bin_, a, b, o, force = job
    if o.exists() and not force:
        return None
    o.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run([bin_, str(a), str(b), "-o", str(o), "--force", "-q"],
                           capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    return f"{r.returncode} {r.stderr.strip()[-200:]}" if r.returncode or not o.exists() else None


def changed(path):
    out = {}
    for v in ra.verdicts(ra.paragraphs(path)):
        if v.verdict in ("unchanged", "mark-only"):
            continue
        key = ("a", v.a_index) if v.a_index is not None else ("b", v.b_index)
        out[key] = v.verdict
    return out


def judge(job):
    s, key, wr, o, err = job
    if err:
        return [{"set": s, "key": key, "para": "", "word": "", "jubarte": f"ERROR {err}", "agree": False}]
    try:
        W, J = changed(wr), changed(o)
    except Exception as e:  # noqa: BLE001
        return [{"set": s, "key": key, "para": "", "word": "", "jubarte": f"PARSE {str(e)[:80]}", "agree": False}]
    rows = []
    for k in sorted(set(W) | set(J), key=str):
        w, j = W.get(k, "unchanged"), J.get(k, "unchanged")
        rows.append({"set": s, "key": key, "para": f"{k[0]}{k[1]}", "word": w, "jubarte": j, "agree": w == j})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--csv")
    ap.add_argument("--sets", help="comma-separated corpus set names (default: all)")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ps = pairs(set(args.sets.split(",")) if args.sets else None)
    if args.limit:
        ps = ps[: args.limit]
    out = Path(args.out)
    jobs = [(args.bin, a, b, out / f"{key}.docx", args.force) for _, key, a, b, _ in ps]
    with ThreadPoolExecutor(args.jobs) as ex:
        errs = list(ex.map(run, jobs))
    with ProcessPoolExecutor(args.jobs) as ex:
        rows = [r for rs in ex.map(judge, [(s, key, wr, out / f"{key}.docx", e)
                                           for (s, key, _, _, wr), e in zip(ps, errs)], chunksize=8) for r in rs]
    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    by = defaultdict(list)
    for r in rows:
        by[r["set"]].append(r)
    print(f"{len(ps)} pairs, {sum(1 for e in errs if e)} jubarte failures")
    print(f"{'set':28} {'pairs':>5} {'paras':>6} {'agree':>6} {'rate':>6}   disagreements (word→jubarte)")
    tot = ok = 0
    for s, rs in sorted(by.items()):
        c = Counter((r["word"], r["jubarte"].split(" ")[0]) for r in rs if not r["agree"])
        n, k = len(rs), sum(r["agree"] for r in rs)
        tot += n
        ok += k
        np = len({r["key"] for r in rs})
        print(f"{s:28} {np:5} {n:6} {k:6} {k / max(n, 1):6.3f}   "
              + ", ".join(f"{w}→{j} {c_}" for (w, j), c_ in c.most_common(5)))
    print(f"{'ALL':28} {len(ps):5} {tot:6} {ok:6} {ok / max(tot, 1):6.3f}")


if __name__ == "__main__":
    main()
