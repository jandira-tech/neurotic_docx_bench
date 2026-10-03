#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Prose waves: per pair, Word's verdict on the target paragraph, Word's kept fraction
(true-labelled against the construction), lost runs and leaps; per cell, the boundary.
Usage: prose_summary.py PROBE_DIR  → writes PROBE_DIR/summary.csv and prints cell strips."""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "/tmp"); sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
from aligners import word_pairs

P = Path(sys.argv[1])
truth = json.load(open(P / "truth.json"))
rows = []
for m in csv.DictReader((P / "manifest.csv").open()):
    n = m["name"]; r = P / "word" / f"{n}__vs__{n}.docx"
    if not r.exists():
        continue
    t = truth[n]
    A, B, R = ra.paragraphs(P / "A" / f"{n}.docx"), ra.paragraphs(P / "B" / f"{n}.docx"), ra.paragraphs(r)
    ta, tb = A[2].text("orig"), B[2].text("rev")
    a, b = ra.words(ta), ra.words(tb)
    # construction words vs tokenizer words differ (punctuation units); map construction word k → token index range
    def tokmap(text_words):
        idx = []; pos = 0
        for w in text_words:
            n_ = len(ra.words(w)); idx.append((pos, pos + n_)); pos += n_
        return idx
    aw, bw = " ".join(ta.split()).split(" "), " ".join(tb.split()).split(" ")
    ma, mb = tokmap(aw), tokmap(bw)
    true = set()
    for i, j in t["pairs"]:
        for k in range(ma[i][1] - ma[i][0]):
            true.add((ma[i][0] + k, mb[j][0] + k))
    vs = [v for v in ra.verdicts(R) if v.verdict != "unchanged" and (v.a_index == 2 or (v.a_index is None and v.b_index == 2))]
    verdict = "/".join(sorted({v.verdict for v in vs})) or "unchanged"
    mx = max(len(ta), len(tb), 1)
    true_kept = sum(len(a[i]) for i, _ in true) / mx
    rec = {**m, "verdict": verdict, "max_chars": mx, "true_kept": round(true_kept, 4), "true_runs": sum(1 for i, j in true if (i - 1, j - 1) not in true)}
    if verdict == "word-level":
        Rp = [p for p in R if len(ra.words(p.text("orig"))) == len(a)]
        if len(Rp) == 1:
            wp = word_pairs(Rp[0], ta)
            found = wp & true; spur = wp - true; lost = true - wp
            rec.update({"word_kept": round(sum(len(a[i]) for i, _ in wp) / mx, 4), "word_true_kept": round(sum(len(a[i]) for i, _ in found) / mx, 4),
                        "spurious": len(spur), "lost": len(lost), "recall": round(len(found) / max(len(true), 1), 4), "precision": round(len(found) / max(len(wp), 1), 4),
                        "leaps": sum(1 for i, j in spur if (i - 1, j - 1) not in wp and (i + 1, j + 1) not in wp)})
    rows.append(rec)

keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in rows[0], k))
with (P / "summary.csv").open("w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=keys); wr.writeheader(); wr.writerows(rows)
print(f"{len(rows)} pairs with a redline")
cells = defaultdict(list)
for r in rows:
    cells[(r["corpus"], r["forced"], int(r["words"]), int(r["run"]))].append(r)
for key, rs in sorted(cells.items()):
    rs.sort(key=lambda r: float(r["keep"]))
    strip = " ".join(f"{int(float(r['keep']) * 100):02d}{'W' if r['verdict'] == 'word-level' else '.' if r['verdict'] == 'replaced' else '?'}" for r in rs)
    first = next((r for r in rs if r["verdict"] == "word-level"), None)
    ex = f" first W keep {float(first['keep']):.2f} true_kept {first['true_kept']:.3f} word_kept {first.get('word_kept', float('nan')):.3f} recall {first.get('recall', float('nan')):.2f}" if first else ""
    print(f"{key[0]:6} {'tail' if key[1] == 'True' else '    '} L={key[2]:4} r={key[3]:2}  {strip}{ex}")
# recall of Word's alignment by corpus, word-level pairs only
print("\nWord alignment recall/precision on word-level pairs, by corpus:")
for c in sorted({r["corpus"] for r in rows}):
    rs = [r for r in rows if r["corpus"] == c and "recall" in r]
    if rs:
        import statistics
        print(f"  {c:6} n={len(rs):3} recall mean {statistics.mean(r['recall'] for r in rs):.3f} min {min(r['recall'] for r in rs):.3f}  precision mean {statistics.mean(r['precision'] for r in rs):.3f}  leaps/pair {statistics.mean(r['leaps'] for r in rs):.1f}")
