#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Wave 8: Word's own alignment inside the original region of pairs that were replaced
(forced to word-level by an identical 150-word tail). Reports Word's kept fraction of the
original region beside recursive-Heckel and LCS proxies, and the original verdict."""
import json, sys
from pathlib import Path
sys.path.insert(0, "/tmp"); sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
from aligners import word_pairs

P = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes/wave8")
meta = json.load(open(P / "meta.json"))
print(f"{'pair':20} {'orig verdict':12} {'tail verdict':12} {'word kept':>9} {'heckel-rec':>10} {'lcs':>6} {'runs W/H/L':>12}  rule(0.12)")
for name, m in meta.items():
    r = P / "word" / f"{name}__vs__{name}.docx"
    if not r.exists():
        print(f"{name:20} (no redline)"); continue
    A, B, R = ra.paragraphs(P / "A" / f"{name}.docx"), ra.paragraphs(P / "B" / f"{name}.docx"), ra.paragraphs(r)
    ta, tb = A[2].text("orig"), B[2].text("rev")
    vs = [v for v in ra.verdicts(R) if v.verdict != "unchanged" and (v.a_index == 2 or (v.a_index is None and v.b_index == 2))]
    tv = "/".join(sorted({v.verdict for v in vs})) or "unchanged"
    a, b = ra.words(ta), ra.words(tb)
    na, nb = m["a_words"], m["b_words"]
    mx = max(m["a_chars"], m["b_chars"])
    Rp = next((p for p in R if p.text("orig") == ta), None)
    wk = "-"; wr = "-"
    if Rp is not None and tv == "word-level":
        wp = {(i, j) for i, j in word_pairs(Rp, ta) if i < na and j < nb}
        wk = sum(len(a[i]) for i, _ in wp) / mx
        wr = sum(1 for i, j in wp if (i - 1, j - 1) not in wp)
    hk = {(i, j) for i, j in ra.heckel_pairs(a[:na], b[:nb])}
    lc = ra.lcs_pairs(a[:na], b[:nb])
    hkf = sum(len(a[i]) for i, _ in hk) / mx; lcf = sum(len(a[i]) for i, _ in lc) / mx
    hr = sum(1 for i, j in hk if (i - 1, j - 1) not in hk); lr = sum(1 for i, j in lc if (i - 1, j - 1) not in lc)
    rule = "-" if wk == "-" else ("word-level" if wk >= 0.12 else "replaced")
    ok = "" if wk == "-" else ("  ✓" if rule == m["orig_verdict"] else "  ✗")
    wks = f"{wk:9.3f}" if wk != "-" else f"{'-':>9}"
    print(f"{name:20} {m['orig_verdict']:12} {tv:12} {wks} {hkf:10.3f} {lcf:6.3f} {str(wr):>4}/{hr:3}/{lr:3}  {rule}{ok}")
