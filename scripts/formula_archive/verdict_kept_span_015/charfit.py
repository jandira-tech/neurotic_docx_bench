# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Fit Word's whole-vs-word rule in character space over the clean probes."""
import csv
import difflib
import itertools
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
from redline_anatomy import paragraphs, tokenize  # noqa: E402

BASE = Path("/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow")


def load(waves=("wave3", "wave4", "wave5"), only_clean=True):
    rows = []
    for wave in waves:
        f = BASE / "probes" / wave / "features.csv"
        for r in csv.DictReader(open(f)):
            name = r["redline"].split("__")[0]
            if only_clean and "_dj" not in name:
                continue
            A = paragraphs(BASE / "probes" / wave / "A" / f"{name}.docx")[int(r["a_index"])].text("rev")
            B = paragraphs(BASE / "probes" / wave / "B" / f"{name}.docx")[int(r["b_index"])].text("rev")
            ua = [u for u in tokenize(A) if u.kind == "w"]
            ub = [u for u in tokenize(B) if u.kind == "w"]
            a = [u.text.lower() for u in ua]
            b = [u.text.lower() for u in ub]
            sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
            blocks = [bl for bl in sm.get_matching_blocks() if bl.size]
            kept_w = sum(bl.size for bl in blocks)
            kept_c = sum(len(a[bl.a + k]) for bl in blocks for k in range(bl.size))
            kept_c_sp = kept_c + sum(bl.size - 1 for bl in blocks)  # + spaces inside runs
            rows.append({
                "name": name, "verdict": r["verdict"], "wave": wave,
                "Lw": max(len(a), len(b)), "law": len(a), "lbw": len(b),
                "Lc": max(len(A), len(B)), "lac": len(A), "lbc": len(B),
                "lac_ns": sum(map(len, a)), "lbc_ns": sum(map(len, b)),
                "R": len(blocks), "kept_w": kept_w, "kept_c": kept_c, "kept_c_sp": kept_c_sp,
            })
    return rows


def evaluate(rows, score_fn):
    """Return (best accuracy, threshold, margin) for rule score ≤ t ⇒ word-level."""
    xs = [(score_fn(r), r["verdict"] == "word-level") for r in rows]
    xs.sort()
    best = (0, None, 0)
    vals = [x for x, _ in xs]
    for i in range(len(xs) - 1):
        t = (vals[i] + vals[i + 1]) / 2
        acc = sum((x <= t) == y for x, y in xs) / len(xs)
        if acc > best[0] or (acc == best[0] and vals[i + 1] - vals[i] > best[2]):
            best = (acc, t, vals[i + 1] - vals[i])
    return best


if __name__ == "__main__":
    cache = BASE / "probes/charfit_rows.json"
    rows = json.loads(cache.read_text()) if cache.exists() and "--rebuild" not in sys.argv else load()
    cache.write_text(json.dumps(rows))
    print(f"{len(rows)} clean pairs: {sum(r['verdict']=='word-level' for r in rows)} word-level")
    models = {}
    for kept_key in ("kept_w", "kept_c", "kept_c_sp"):
        for denom in ("Lw", "Lc", "lac+lbc", "law+lbw"):
            def den(r, denom=denom):
                return r[denom] if denom in r else r[denom.split("+")[0]] + r[denom.split("+")[1]]
            for c in (0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 6, 8):
                # rule: (edits + c·R) / denom ≤ β  where edits are in the kept_key's unit
                def edits(r, kept_key=kept_key):
                    if kept_key == "kept_w":
                        return r["law"] + r["lbw"] - 2 * r["kept_w"]
                    return r["lac"] + r["lbc"] - 2 * r[kept_key]
                fn = lambda r, c=c, den=den, edits=edits: (edits(r) + c * r["R"]) / den(r)
                models[f"({kept_key} edits + {c}·R)/{denom}"] = evaluate(rows, fn)
            # pure kept fraction (higher = word-level): use negative
            models[f"-{kept_key}/{denom}"] = evaluate(rows, lambda r, den=den, k=kept_key: -r[k] / den(r))
    # quadratic-ish: edits·(1 + R/m)
    for m in (300, 600, 1100, 2000, 4000):
        models[f"kept_c edits·(1+R/{m})/Lc"] = evaluate(rows, lambda r, m=m: (r["lac"] + r["lbc"] - 2 * r["kept_c"]) * (1 + r["R"] / m) / r["Lc"])
        models[f"kept_c edits·(1+R/{m})/(lac+lbc)"] = evaluate(rows, lambda r, m=m: (r["lac"] + r["lbc"] - 2 * r["kept_c"]) * (1 + r["R"] / m) / (r["lac"] + r["lbc"]))
    ranked = sorted(models.items(), key=lambda kv: (-kv[1][0], -kv[1][2]))
    for name, (acc, t, margin) in ranked[:25]:
        print(f"  {acc:6.1%}  t={t:.4f} margin={margin:.4f}  {name}")
    # per-wave breakdown for the best
    name, (acc, t, margin) = ranked[0]
    print("\nbest model by wave / length:")
