#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Does one threshold on a Heckel-aligned kept fraction separate Word's verdicts across every wave?
For each probe (and the real pairs): target paragraph verdict from Word's redline; Heckel kept chars
(with and without the spaces inside kept runs) over max/min side chars; LCS kept for comparison."""
import csv, json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, "/tmp"); sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
from aligners import heckel, lcs_dp, word_pairs

base = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow")
waves = [d for d in sorted((base / "probes").iterdir()) if (d / "word").is_dir() and (d / "A").is_dir()]


def kept_chars(a, pairs):
    ps = sorted(pairs)
    chars = sum(len(a[i]) for i, _ in ps)
    spaces = sum(1 for k in range(1, len(ps)) if ps[k] == (ps[k - 1][0] + 1, ps[k - 1][1] + 1))
    runs = len(ps) - spaces
    return chars, chars + spaces, runs


rows = []


def add(tag, name, ta, tb, verdict, R=None):
    a, b = ra.words(ta), ra.words(tb)
    mx, mn = max(len(ta), len(tb), 1), max(min(len(ta), len(tb)), 1)
    hk = heckel(a, b); lc = lcs_dp(a, b)
    hc, hcs, hr = kept_chars(a, hk); lcc, lcs_, lr = kept_chars(a, lc)
    row = {"wave": tag, "name": name, "verdict": verdict, "a_words": len(a), "b_words": len(b), "max_chars": mx,
           "hk_max": hc / mx, "hks_max": hcs / mx, "hks_min": hcs / mn, "hk_runs": hr, "hk_words": len(hk),
           "lcs_max": lcc / mx, "lcss_max": lcs_ / mx, "lcs_runs": lr}
    if R is not None and verdict == "word-level":
        wp = word_pairs(R, ta); wc, wcs, wr = kept_chars(a, wp)
        row.update({"w_max": wc / mx, "ws_max": wcs / mx, "w_runs": wr, "w_words": len(wp)})
    rows.append(row)


for wd in waves:
    for r in sorted((wd / "word").glob("*.docx")):
        stem = r.name.split("__vs__")[0]
        pa, pb = wd / "A" / f"{stem}.docx", wd / "B" / f"{stem}.docx"
        if not (pa.exists() and pb.exists()):
            continue
        A, B, Rp = ra.paragraphs(pa), ra.paragraphs(pb), ra.paragraphs(r)
        # target = longest A paragraph
        ti = max(range(len(A)), key=lambda i: len(A[i].text("orig")))
        ta = A[ti].text("orig")
        tb = B[ti].text("rev") if ti < len(B) else ""
        vs = [v for v in ra.verdicts(Rp) if v.verdict != "unchanged" and (v.a_index == ti or (v.a_index is None and v.b_index == ti))]
        verdict = "/".join(sorted({v.verdict for v in vs})) or "unchanged"
        if verdict not in ("word-level", "replaced"):
            continue
        R = next((p for p in Rp if p.text("orig") == ta), None)
        add(wd.name, stem, ta, tb, verdict, R)

# real pairs
reals = [("real", "letters p5", "inputs/55_Traversal_cover_letter.docx", "inputs/56_Flow_cover_letter.docx", "word-docx/2_c55-v-c56__word.docx", 5)]
for i in (3, 6, 9, 12, 14):
    reals.append(("real", f"metadata p{i}", "inputs/55_Traversal_metadata.docx", "inputs/56_Flow_metadata.docx", "word-docx/3_m55-v-m56__word.docx", i))
for tag, name, pa, pb, pr, idx in reals:
    A, B, Rp = ra.paragraphs(base / pa), ra.paragraphs(base / pb), ra.paragraphs(base / pr)
    ta, tb = A[idx].text("orig"), B[idx].text("rev")
    vs = [v for v in ra.verdicts(Rp) if v.verdict != "unchanged" and (v.a_index == idx or (v.a_index is None and v.b_index == idx))]
    verdict = "/".join(sorted({v.verdict for v in vs}))
    R = next((p for p in Rp if p.text("orig") == ta), None)
    add(tag, name, ta, tb, verdict, R)

json.dump(rows, open("/tmp/heckel_rows.json", "w"), indent=0)
print(f"{len(rows)} pairs; by wave:", dict(sorted(defaultdict(int, {w: sum(1 for r in rows if r['wave'] == w) for w in {r['wave'] for r in rows}}).items())))


def best_threshold(key, rs):
    pts = sorted((r[key], r["verdict"] == "word-level") for r in rs)
    best = (0, None)
    cands = sorted({p[0] for p in pts})
    for t in cands + [cands[-1] + 1e-9]:
        acc = sum((v >= t) == w for v, w in pts)
        if acc > best[0]:
            best = (acc, t)
    return best[0] / len(pts), best[1]


print("\nsingle-threshold accuracy per measure (all pairs):")
for key in ("hk_max", "hks_max", "hks_min", "lcs_max", "lcss_max"):
    acc, t = best_threshold(key, rows)
    print(f"  {key:9} acc={acc:.3f} at t={t:.4f}")
print("\nper wave, measure hks_max at the global threshold vs its own best:")
acc_g, t_g = best_threshold("hks_max", rows)
for w in sorted({r["wave"] for r in rows}):
    rs = [r for r in rows if r["wave"] == w]
    acc_w, t_w = best_threshold("hks_max", rs)
    at_g = sum((r["hks_max"] >= t_g) == (r["verdict"] == "word-level") for r in rs) / len(rs)
    wl = [r["hks_max"] for r in rs if r["verdict"] == "word-level"]; rp = [r["hks_max"] for r in rs if r["verdict"] == "replaced"]
    print(f"  {w:12} n={len(rs):3} at global t: {at_g:.3f}  own best {acc_w:.3f} @ {t_w:.3f}   min W={min(wl) if wl else float('nan'):.3f} max R={max(rp) if rp else float('nan'):.3f}")
print("\nreal pairs:")
for r in rows:
    if r["wave"] == "real":
        print(f"  {r['name']:14} {r['verdict']:10} hks_max={r['hks_max']:.3f} hk_max={r['hk_max']:.3f} lcs_max={r['lcs_max']:.3f}" + (f" word ws_max={r['ws_max']:.3f}" if "ws_max" in r else ""))
print("\nmisclassified at the global hks_max threshold:")
for r in rows:
    if (r["hks_max"] >= t_g) != (r["verdict"] == "word-level"):
        print(f"  {r['wave']:12} {r['name']:28} {r['verdict']:10} hks_max={r['hks_max']:.3f}")
