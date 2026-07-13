#!/usr/bin/env python3
"""Centralized mapping CSV — built purely from filesystem enumeration.
No dependency on batch_log.csv.

Enumerates all unique pair stems from:
  - docx_redlines_word/  (both _redline.docx and _word_redline.docx variants)
  - docx_accepted_word/  (_word_redline_accepted.docx)
  - pdf_redlines_word/   (_redline.pdf — excludes bare source PDFs)
  - pdf_accepted_word/   (_word_redline_accepted.pdf)

For each pair stem, maps: docx_source base/next, both redline variants,
accepted docx, redline PDF, accepted PDF. Reports any missing items.
"""

import csv
import os
import pathlib

BASE = os.path.dirname(os.path.abspath(__file__))
DIRS = {
    "source":   os.path.join(BASE, "docx_source"),
    "redline":  os.path.join(BASE, "docx_redlines_word"),
    "accepted": os.path.join(BASE, "docx_accepted_word"),
    "pdf_red":  os.path.join(BASE, "pdf_redlines_word"),
    "pdf_acc":  os.path.join(BASE, "pdf_accepted_word"),
}


def list_dir(d):
    return set(os.listdir(d)) if pathlib.Path(d).is_dir() else set()


inv = {k: list_dir(v) for k, v in DIRS.items()}
source_docx = {f for f in inv["source"] if f.endswith(".docx")}
redline_docx = {f for f in inv["redline"] if f.endswith(".docx")}
accepted_docx = {f for f in inv["accepted"] if f.endswith(".docx")}
pdf_red_all = {f for f in inv["pdf_red"] if f.endswith(".pdf")}
pdf_acc_all = {f for f in inv["pdf_acc"] if f.endswith(".pdf")}

source_ci = {}
for f in source_docx:
    stem = f[:-5]
    source_ci[stem.lower()] = f
src_stems_lower = sorted(source_ci.keys(), key=len, reverse=True)


def extract_stems(files, suffixes):
    stems = set()
    for f in files:
        for sfx in suffixes:
            if f.endswith(sfx):
                stems.add(f[:-len(sfx)])
                break
    return stems


red_stems = extract_stems(redline_docx, ["_word_redline.docx", "_redline.docx"])
acc_stems = extract_stems(accepted_docx, ["_word_redline_accepted.docx"])
pdf_r_stems = extract_stems(pdf_red_all, ["_word_redline_accepted.pdf", "_redline.pdf"])
pdf_a_stems = extract_stems(pdf_acc_all, ["_word_redline_accepted.pdf"])

all_stems = sorted(red_stems | acc_stems)


def split_core(core):
    cl = core.lower()
    best = None
    for ss in src_stems_lower:
        if cl.endswith("_" + ss) and len(cl) > len(ss) + 1:
            base = core[:-(len(ss) + 1)]
            if not best or len(ss) > len(best[2]):
                best = (base, source_ci[ss][:-5], ss)
    if best:
        return best[0], best[1]
    for ss in src_stems_lower:
        if cl.startswith(ss + "_"):
            return source_ci[ss][:-5], core[len(ss) + 1:]
    return "", core


def find_source(name):
    direct = f"{name}.docx"
    return direct if direct in source_docx else source_ci.get(name.lower())


results = []
for stem in all_stems:
    base, nxt = split_core(stem)
    base_src = find_source(base) if base else ""
    next_src = find_source(nxt) if nxt else ""

    rl_name = f"{stem}_redline.docx"
    rlw_name = f"{stem}_word_redline.docx"
    acc_name = f"{stem}_word_redline_accepted.docx"
    pr_name = f"{stem}_redline.pdf"
    pa_name = f"{stem}_word_redline_accepted.pdf"

    rl_ok = rl_name in redline_docx
    rlw_ok = rlw_name in redline_docx
    acc_ok = acc_name in accepted_docx
    pr_ok = pr_name in pdf_red_all
    pa_ok = pa_name in pdf_acc_all

    missing = []
    if base and not base_src:
        missing.append("source_base")
    if nxt and not next_src:
        missing.append("source_next")
    if not rl_ok and not rlw_ok:
        missing.append("redline_docx")
    if not acc_ok:
        missing.append("accepted_docx")
    if not pr_ok:
        missing.append("pdf_redline")
    if not pa_ok:
        missing.append("pdf_accepted")

    in_red, in_acc = stem in red_stems, stem in acc_stems
    origin = "both" if (in_red and in_acc) else ("redline_only" if in_red else "accepted_only")

    results.append({
        "pair_stem": stem,
        "base": base,
        "next": nxt,
        "origin": origin,
        "docx_source_base": base_src or (f"MISSING:{base}.docx" if base else ""),
        "docx_source_next": next_src or (f"MISSING:{nxt}.docx" if nxt else ""),
        "redline_docx": rl_name if rl_ok else "",
        "redline_docx_word": rlw_name if rlw_ok else "",
        "accepted_docx": acc_name if acc_ok else "MISSING",
        "pdf_redline": pr_name if pr_ok else "MISSING",
        "pdf_accepted": pa_name if pa_ok else "MISSING",
        "missing": "; ".join(missing),
    })

csv_path = os.path.join(BASE, "centralized_mapping.csv")
fields = [
    "pair_stem", "base", "next", "origin",
    "docx_source_base", "docx_source_next",
    "redline_docx", "redline_docx_word",
    "accepted_docx", "pdf_redline", "pdf_accepted", "missing",
]
with pathlib.Path(csv_path).open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(results)

# ---- Summary ----
print("=" * 70)
print("FILE INVENTORY")
print("=" * 70)
print(f"  source .docx          {len(source_docx)}")
print(f"  redline .docx         {len(redline_docx)}")
print(f"  accepted .docx        {len(accepted_docx)}")
print(f"  pdf_red .pdf          {len(pdf_red_all)}")
print(f"  pdf_acc .pdf          {len(pdf_acc_all)}")

print(f"\n{'=' * 70}")
print("MAPPING SUMMARY")
print("=" * 70)
print(f"  Total unique pairs:   {len(results)}")
print(f"  Both red+accepted:    {sum(1 for r in results if r['origin'] == 'both')}")
print(f"  Redline only:         {sum(1 for r in results if r['origin'] == 'redline_only')}")
print(f"  Accepted only:        {sum(1 for r in results if r['origin'] == 'accepted_only')}")

rl_files = sum(1 for r in results if r["redline_docx"]) + sum(1 for r in results if r["redline_docx_word"])
print(f"  Redline docx files:   {rl_files}  (across {sum(1 for r in results if r['redline_docx'] or r['redline_docx_word'])} pairs)")
print(f"  Accepted docx files:  {sum(1 for r in results if r['accepted_docx'] != 'MISSING')}")

mr = [r for r in results if r["missing"]]
print(f"\nRows with missing items: {len(mr)} / {len(results)}")
if mr:
    cats = {}
    for r in mr:
        for m in r["missing"].split("; "):
            cats[m] = cats.get(m, 0) + 1
    for cat, cnt in sorted(cats.items()):
        print(f"  {cat}: {cnt}")

src_miss = [r for r in results if "source_" in r["missing"]]
if src_miss:
    print(f"\n--- Missing docx_source ({len(src_miss)}) ---")
    for r in src_miss:
        print(f"  {r['pair_stem'][:65]:<65} [{r['missing']}]")
else:
    print("\nNo missing source files — all sources accounted for.")

print(f"\nCSV: {csv_path}")
