#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Wave 7 table: Word's verdict and kept fraction per probe, beside the law. Skips pairs Word has not produced yet."""
import csv, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
STOP = set("the and of to a in that for is on with as".split())

P = Path(sys.argv[1])
rows = []
for m in csv.DictReader((P / "manifest.csv").open()):
    n = m["name"]
    r = P / "word" / f"{n}__vs__{n}.docx"
    if not r.exists():
        continue
    pa, pb, pr = ra.paragraphs(P / "A" / f"{n}.docx"), ra.paragraphs(P / "B" / f"{n}.docx"), ra.paragraphs(r)
    ta, tb = pa[2].text("orig"), pb[2].text("rev")
    vs = [v for v in ra.verdicts(pr) if v.verdict != "unchanged" and (v.a_index == 2 or (v.a_index is None and v.b_index == 2))]
    verdict = "/".join(sorted({v.verdict for v in vs})) or "unchanged"
    if verdict == "replaced":
        wk, wk_clean, wruns = 0, 0, 0
    else:
        eq = [s.text for p in pr for s in p.segments if s.kind == "eq" and p.text("orig") and ra.words(p.text("orig"))[:2] == ra.words(ta)[:2]]
        eqw = [w for t in eq for w in ra.words(t)]
        wk = sum(len(w) for w in eqw); wk_clean = sum(len(w) for w in eqw if w not in STOP); wruns = len([t for t in eq if ra.words(t)])
    pred = ra.predict_pair(ta, tb)
    mx = pred["max_chars"]
    a, b = ra.words(ta), ra.words(tb)
    s = ra.lcs_pairs(a, b)
    clean = sum(len(a[i]) for i, _ in s if a[i] not in STOP)
    rows.append({**m, "verdict": verdict, "ins": sum(v.ins for v in vs), "del": sum(v.dele for v in vs), "islands": sum(v.islands for v in vs),
                 "max_chars": mx, "lcs_kept": round(pred["kept_frac"], 4), "lcs_runs": pred["runs"], "lcs_clean_kept": round(clean / mx, 4),
                 "word_kept": round(wk / mx, 4), "word_clean_kept": round(wk_clean / mx, 4), "word_runs": wruns,
                 "floor": round(pred["floor"], 4), "law": pred["predicted"]})

with (P / "summary.csv").open("w", newline="") as fh:
    wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
    wr.writeheader(); wr.writerows(rows)

by = defaultdict(list)
for r in rows:
    by[(r["group"], r.get("density", ""), int(r["words"]), int(r["run"]))].append(r)
print(f"{len(rows)} pairs with a Word redline")
for key, rs in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][3])):
    rs.sort(key=lambda r: float(r["keep"]))
    strip = " ".join(f"{int(float(r['keep']) * 100):02d}{'W' if r['verdict'] == 'word-level' else '.' if r['verdict'] == 'replaced' else '?'}" for r in rs)
    first = next((r for r in rs if r["verdict"] == "word-level"), None)
    law_first = next((r for r in rs if r["law"] == "word-level"), None)
    extra = ""
    if first:
        extra = f" first W: keep {float(first['keep']):.2f} lcs_kept {first['lcs_kept']:.3f} word_kept {first['word_kept']:.3f} runs {first['lcs_runs']}/{first['word_runs']} floor {first['floor']:.3f}"
    if law_first:
        extra += f" | law first W keep {float(law_first['keep']):.2f}"
    print(f"{key[0]:12} d={key[1] or '-':4} L={key[2]:5} r={key[3]:2}  {strip}{extra}")
