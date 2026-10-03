# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""holdcmp.py OLD NEW : per-file deltas between two hold.sh tags (both holdouts), then the means."""
import json, pathlib, sys

L = pathlib.Path(__file__).parent
old, new = sys.argv[1:3]


def load(name):
    p = L / "runs" / name / "rows.json"
    return json.load(open(p)) if p.exists() else {}


a, b = load(f"tip_h_{old}"), load(f"tip_h_{new}")
d = sorted(((b[k]["pixel"] + b[k]["jaccard"]) - (a[k]["pixel"] + a[k]["jaccard"]), k) for k in b if k in a)
for x, k in d:
    if abs(x) > 0.05:
        print(f"tip {x:+.2f} {k[:40]}…{k[-10:]}  {a[k]['pixel']:.2f}/{a[k]['jaccard']:.2f} -> {b[k]['pixel']:.2f}/{b[k]['jaccard']:.2f}")
if b:
    n = len(b)
    print(f"tip holdout n={n} pixel {sum(v['pixel'] for v in a.values())/max(len(a),1):.2f} -> {sum(v['pixel'] for v in b.values())/n:.2f}"
          f"  jaccard {sum(v['jaccard'] for v in a.values())/max(len(a),1):.2f} -> {sum(v['jaccard'] for v in b.values())/n:.2f}")
for p in "abr":
    a, b = load(f"en{p}_hold_{old}"), load(f"en{p}_hold_{new}")
    for k in sorted(b, key=lambda k: b[k]["jubarte"] - a.get(k, {}).get("jubarte", 0)):
        if k in a and abs(b[k]["jubarte"] - a[k]["jubarte"]) > 0.002:
            print(f"en{p} {b[k]['jubarte'] - a[k]['jubarte']:+.3f} {k[:12]} {a[k]['jubarte']:.3f} -> {b[k]['jubarte']:.3f} best {b[k]['best']:.3f}")
    if b:
        print(f"en{p} holdout n={len(b)} mean {sum(v['jubarte'] for v in a.values())/max(len(a),1):.3f} -> "
              f"{sum(v['jubarte'] for v in b.values())/len(b):.3f}  wins {sum(v['win'] for v in a.values())} -> {sum(v['win'] for v in b.values())}")

# Page gate: every control-group file's page count against Word's. A file further from Word's
# count than under OLD is a regression and fails the gate (exit 1).
from pages import counts, gate  # noqa: E402
from metrics4 import scored  # noqa: E402

D = pathlib.Path("/Users/arthrod/temp/T/jubarte-redlines/_to_improve_docx_to_pdf")
# en holdout: corpus/word's docx and Word PDFs (grok_run was removed 2026-09-30, neurotic d854977a4).
EN = [l.rstrip("\n").split("\t") for l in open(L / "en_holdout_corpus.tsv") if not l.startswith("#")]
sets = {"tip": ([k.strip() for k in open(L / "tip_holdout.txt") if k.strip()],
                lambda t, k: L / "runs" / f"tip_h_{t}" / "pdf" / f"{k}.pdf", lambda k: D / "_word_pdf" / f"{k}.pdf")}
for p in "abr":
    ref = {r[1]: pathlib.Path(r[3]) for r in EN if r[0] == p}
    sets[f"en{p}"] = (sorted(ref), lambda t, s, p=p: L / "runs" / f"en_hold_{p}_{t}" / "pdf" / f"{s}.pdf",
                      lambda s, ref=ref: ref[s])
failed = 0
M4 = ("jaccard", "ssim", "text_boundary")
for name, (keys, cand, word) in sets.items():
    o, n, w = counts(cand(old, k) for k in keys), counts(cand(new, k) for k in keys), counts(word(k) for k in keys)
    worse, mo, mn = gate({k: t for k, t in zip(keys, zip(o, n, w))})
    # Nothing to compare is a failure, not a pass: missing Word references
    # or a new run that wrote no PDFs (grok_run's removal hid both, b31).
    blind = [what for what, got in (("Word references", w), (f"{new} PDFs", n)) if all(c is None for c in got)]
    for what in blind:
        print(f"PAGE GATE BLIND {name}: no {what}")
    failed += len(blind)
    for d, k, po, pn, pw in worse:
        print(f"PAGE REGRESSION {name} {k[:40]}…{k[-10:]} pages {po} -> {pn} (Word {pw})")
    print(f"{name} pages match Word {mo} -> {mn} of {len(keys)}; regressions {len(worse)}")
    failed += len(worse)
    # The four page-metrics values (the priority folder's scorer), per file and mean.
    mo4 = scored({k: (word(k), cand(old, k)) for k in keys}, L / "runs" / f"m4_{name}_{old}.json")
    mn4 = scored({k: (word(k), cand(new, k)) for k in keys}, L / "runs" / f"m4_{name}_{new}.json")
    for k in keys:
        dt = {m: (mn4[k][m] or 0.0) - (mo4[k][m] or 0.0) for m in M4}
        do, dn = mo4[k]["max_break_drift"], mn4[k]["max_break_drift"]
        drift_worse = do is not None and dn is not None and abs(dn) > abs(do)
        if any(abs(v) > 0.5 for v in dt.values()) or (do != dn and do is not None and dn is not None):
            tag = "M4 WORSE" if min(dt.values()) < -0.5 or drift_worse else "m4"
            print(f"{tag} {name} {k[:40]}…{k[-10:]} " + " ".join(f"{m[:4]} {mo4[k][m]}->{mn4[k][m]}" for m in M4)
                  + f" drift {do}->{dn}")
    mean = lambda d, m: sum(d[k][m] or 0.0 for k in keys) / len(keys)
    exact = lambda d: sum(d[k]["max_break_drift"] == 0 for k in keys)
    print(f"{name} m4 " + "  ".join(f"{m} {mean(mo4, m):.2f}->{mean(mn4, m):.2f}" for m in M4)
          + f"  breaks-on-Word {exact(mo4)}->{exact(mn4)}")
print("PAGE GATE " + ("FAIL" if failed else "PASS"))
sys.exit(1 if failed else 0)
