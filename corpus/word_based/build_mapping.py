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


# docx_accepted_word files carry the REDLINE names (`…_redline.docx` /
# `…_word_redline.docx`): they are the redlines with all changes applied. The
# old `_word_redline_accepted.docx` suffix matched zero files, so every row
# recorded accepted_docx=MISSING.
red_stems = extract_stems(redline_docx, ["_word_redline.docx", "_redline.docx"])
acc_stems = extract_stems(accepted_docx, ["_word_redline.docx", "_redline.docx"])
pdf_r_stems = extract_stems(pdf_red_all, ["_word_redline.pdf", "_redline.pdf"])
pdf_a_stems = extract_stems(pdf_acc_all, ["_word_redline_accepted.pdf"])

all_stems = sorted(red_stems | acc_stems)


def split_core(core, source_ci=source_ci, src_stems_lower=src_stems_lower):
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
    pa_name = f"{stem}_word_redline_accepted.pdf"

    rl_ok = rl_name in redline_docx
    rlw_ok = rlw_name in redline_docx
    # Accepted docx carry the redline names; the `_word_redline` variant is the
    # provenance-matching Word capture and wins when both exist.
    acc_name = next(
        (n for n in (rlw_name, rl_name) if n in accepted_docx), "",
    )
    acc_ok = bool(acc_name)
    # 43 pairs only exist as the `_word_redline.pdf` capture — the old code
    # recorded a stale `_redline.pdf` name for them.
    pr_name = next(
        (n for n in (f"{stem}_word_redline.pdf", f"{stem}_redline.pdf") if n in pdf_red_all),
        "",
    )
    pr_ok = bool(pr_name)
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

# ---- Randomized chain corpus (file_N → file_M) ----
# Same schema, separate CSV: sources in docx_source_randomized, redlines in
# docx_redlines_randomized, oracle PDFs in pdf_redlines_randomized/pdf. No
# accepted artifacts exist for this corpus (accepted_docx/pdf_accepted MISSING).
RAND_DIRS = {
    "source": os.path.join(BASE, "docx_source_randomized"),
    "redline": os.path.join(BASE, "docx_redlines_randomized"),
    "pdf_red": os.path.join(BASE, "pdf_redlines_randomized", "pdf"),
}
rand_source = {f for f in list_dir(RAND_DIRS["source"]) if f.endswith(".docx")}
rand_redline = {f for f in list_dir(RAND_DIRS["redline"]) if f.endswith(".docx")}
rand_pdf = {f for f in list_dir(RAND_DIRS["pdf_red"]) if f.endswith(".pdf")}

rand_ci = {}
for f in rand_source:
    rand_ci[f[:-5].lower()] = f
rand_stems_lower = sorted(rand_ci.keys(), key=len, reverse=True)

rand_results = []
for stem in sorted(extract_stems(rand_redline, ["_redline.docx"])):
    base, nxt = split_core(stem, source_ci=rand_ci, src_stems_lower=rand_stems_lower)
    base_src = f"{base}.docx" if f"{base}.docx" in rand_source else rand_ci.get(base.lower())
    next_src = f"{nxt}.docx" if f"{nxt}.docx" in rand_source else rand_ci.get(nxt.lower())
    pr_name = f"{stem}_redline.pdf"
    pr_ok = pr_name in rand_pdf

    missing = ["accepted_docx", "pdf_accepted"]
    if base and not base_src:
        missing.insert(0, "source_base")
    if nxt and not next_src:
        missing.insert(0, "source_next")
    if not pr_ok:
        missing.insert(0, "pdf_redline")

    rand_results.append({
        "pair_stem": stem,
        "base": base,
        "next": nxt,
        "origin": "randomized_chain",
        "docx_source_base": base_src or (f"MISSING:{base}.docx" if base else ""),
        "docx_source_next": next_src or (f"MISSING:{nxt}.docx" if nxt else ""),
        "redline_docx": f"{stem}_redline.docx",
        "redline_docx_word": "",
        "accepted_docx": "MISSING",
        "pdf_redline": pr_name if pr_ok else "MISSING",
        "pdf_accepted": "MISSING",
        "missing": "; ".join(missing),
    })

rand_csv_path = os.path.join(BASE, "centralized_mapping_randomized.csv")
with pathlib.Path(rand_csv_path).open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rand_results)

print(f"\n{'=' * 70}")
print("RANDOMIZED CHAIN CORPUS")
print("=" * 70)
print(f"  source .docx          {len(rand_source)}")
print(f"  redline .docx         {len(rand_redline)}")
print(f"  oracle .pdf           {len(rand_pdf)}")
print(f"  Pairs:                {len(rand_results)}")
print(f"  Missing oracle pdf:   {sum(1 for r in rand_results if r['pdf_redline'] == 'MISSING')}")
print(f"\nCSV: {rand_csv_path}")
