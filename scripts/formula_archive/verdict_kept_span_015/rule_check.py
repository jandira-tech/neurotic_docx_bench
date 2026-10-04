#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""For every row of /tmp/jub_baseline.csv: LCS kept-char ratio of the paragraph pair
(Word's rule applied to an LCS alignment), the Step-G ratio (longest run / max words),
and what the 0.12 rule would predict. Reports how often the rule matches Word and jubarte."""
import csv, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra

ROOT = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes")
rows = list(csv.DictReader(open(sys.argv[1] if len(sys.argv) > 1 else "/tmp/jub_baseline.csv")))
cache = {}
def texts(s, n):
    if (s, n) not in cache:
        A = ra.paragraphs(ROOT / s / "A" / f"{n}.docx"); B = ra.paragraphs(ROOT / s / "B" / f"{n}.docx")
        cache[(s, n)] = ([p.text("orig") for p in A], [p.text("orig") for p in B])
    return cache[(s, n)]

def longest_run(pairs):
    best = 0
    for i, j in pairs:
        if (i - 1, j - 1) in pairs:
            continue
        k = 0
        while (i + k, j + k) in pairs:
            k += 1
        best = max(best, k)
    return best

out = []
for r in rows:
    if r["word"] not in ("word-level", "replaced") or not r["para"].startswith("a"):
        continue
    ai = int(r["para"][1:]); A, B = texts(r["set"], r["name"])
    # pair the paragraph by index: probe sets have equal paragraph counts; real set uses ra.pair_paragraphs
    if len(A) == len(B):
        bi = ai
    else:
        pp = dict(ra.pair_paragraphs(ra.paragraphs(ROOT / r["set"] / "A" / f"{r['name']}.docx"), ra.paragraphs(ROOT / r["set"] / "B" / f"{r['name']}.docx")))
        bi = pp.get(ai)
        if bi is None:
            continue
    ta, tb = A[ai], B[bi]
    a, b = ra.words(ta), ra.words(tb)
    pairs = ra.lcs_pairs(a, b)
    mx = max(len(ta), len(tb), 1)
    kept = sum(len(a[i]) for i, _ in pairs) / mx
    lr = longest_run(pairs); stepg = lr / max(len(a), len(b), 1)
    pred = "word-level" if kept >= 0.12 else "replaced"
    out.append({**r, "lcs_kept": round(kept, 3), "longest_run": lr, "stepg": round(stepg, 4), "rule": pred})

print(f"{len(out)} word-level/replaced paragraphs")
agree_rule = Counter((r["word"], r["rule"]) for r in out)
print("rule(0.12 on LCS) vs Word:", dict(agree_rule), f"→ {sum(v for (w, p), v in agree_rule.items() if w == p) / len(out):.3f}")
# where Step G explains jubarte's verdict
c = Counter()
for r in out:
    c[(r["jubarte"], "stepg<0.02" if r["stepg"] < 0.02 else "stepg≥0.02")] += 1
print("jubarte verdict vs Step-G ratio:", dict(c))
by = defaultdict(list)
for r in out:
    by[r["set"]].append(r)
print("\nper set: rule-vs-Word agreement, and the margins of the rule's misses")
for s, rs in by.items():
    miss = [r for r in rs if r["word"] != r["rule"]]
    print(f"  {s:10} n={len(rs):4} rule ok {1 - len(miss) / len(rs):.3f}  misses: " + ", ".join(f"{r['name']}({r['word'][0]} kept {r['lcs_kept']})" for r in miss[:8]))
with open("/tmp/rule_check.csv", "w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(out[0])); wr.writeheader(); wr.writerows(out)
