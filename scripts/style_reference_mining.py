#!/usr/bin/env python3
"""M480 discriminator mining, round 3: does "the style is REFERENCED by
document content" separate Word's verbatim-copy heading pairs from its
neutralized heading pairs?

For every heading-family row in the bake matrix, look up whether the style is
referenced (<w:pStyle w:val="SID">) in A's document.xml, B's document.xml,
and the oracle's document.xml. Cross-tab reference presence x verdict at row
level and at pure-pair-class level.

Render-free: reads source + oracle docx only.

Usage: uv run python scripts/style_reference_mining.py <bake_matrix.json>
"""

from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ("corpus/word_based/centralized_mapping.csv", "corpus/word_based/docx_source",
     "corpus/word_based/docx_redlines_word", "{stem}_word_redline.docx|{stem}_redline.docx"),
    ("corpus/word_based/centralized_mapping_randomized.csv", "corpus/word_based/docx_source_randomized",
     "corpus/word_based/docx_redlines_randomized", "{stem}_redline.docx"),
    ("corpus/word_redlines_superdoc/centralized_mapping.csv", "corpus/word_redlines_superdoc/docx_source",
     "corpus/word_redlines_superdoc/docx_redlines_word", "{stem}_redline.docx"),
]


def pair_paths():
    out = {}
    for man, src, odir, pat in CORPORA:
        mp = BENCH_ROOT / man
        if not mp.exists():
            continue
        for row in csv.DictReader(mp.open()):
            stem = row["pair_stem"]
            oracle = None
            for cand in pat.format(stem=stem).split("|"):
                p = BENCH_ROOT / odir / cand
                if p.exists():
                    oracle = p
                    break
            if oracle and stem not in out:
                out[stem] = (BENCH_ROOT / src / row["docx_source_base"],
                             BENCH_ROOT / src / row["docx_source_next"], oracle)
    return out


def doc_xml(path):
    try:
        return zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    except Exception:
        return ""


def refs_of(xml):
    return set(re.findall(r'<w:pStyle w:val="([^"]*)"', xml))


def main():
    matrix = json.load(open(sys.argv[1]))
    rows = [r for r in matrix if r["family"] == "heading"]
    paths = pair_paths()

    # per-pair verdict profile over heading rows
    prof = defaultdict(Counter)
    for r in rows:
        prof[r["pair"]][r["verdict"]] += 1
    pure_v = {p for p, c in prof.items() if c.get("verbatim") and not c.get("neutralized")}
    pure_n = {p for p, c in prof.items() if c.get("neutralized") and not c.get("verbatim")}
    print(f"heading rows: {len(rows)}  pairs: {len(prof)}  pureV: {len(pure_v)}  pureN: {len(pure_n)}")

    ref_cache = {}
    def refs(pair):
        if pair not in ref_cache:
            if pair not in paths:
                ref_cache[pair] = None
            else:
                a_p, b_p, o_p = paths[pair]
                ref_cache[pair] = (refs_of(doc_xml(a_p)), refs_of(doc_xml(b_p)), refs_of(doc_xml(o_p)))
        return ref_cache[pair]

    # row-level cross-tab
    tab = Counter()
    for r in rows:
        rr = refs(r["pair"])
        if rr is None:
            continue
        a_ref, b_ref, o_ref = (r["style"] in s for s in rr)
        tab[(r["verdict"], "b_ref" if b_ref else "b_unref")] += 1
        tab[(r["verdict"], "a_ref" if a_ref else "a_unref")] += 1
        tab[(r["verdict"], "o_ref" if o_ref else "o_unref")] += 1
    print("\nrow-level verdict x reference:")
    for k in sorted(tab):
        print(f"  {k[0]:11} {k[1]:8} {tab[k]}")

    # pure-pair-class level: share of the pair's matrix heading styles referenced in B
    print("\npair-class profiles (styles-in-matrix referenced in B / A / oracle):")
    for label, cls in [("pureV", pure_v), ("pureN", pure_n)]:
        counts = Counter()
        for p in sorted(cls):
            rr = refs(p)
            if rr is None:
                continue
            sids = {r["style"] for r in rows if r["pair"] == p}
            nb = len(sids & rr[1]); na = len(sids & rr[0]); no = len(sids & rr[2])
            key = (nb > 0, na > 0, no > 0)
            counts[key] += 1
            print(f"  {label} {p[:58]:58} styles={len(sids)} refA={na} refB={nb} refO={no}")
        print(f"  {label} summary (anyB,anyA,anyO): {dict(counts)}")


if __name__ == "__main__":
    main()
