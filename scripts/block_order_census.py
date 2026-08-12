#!/usr/bin/env python3
"""Task #8: mine Word's ins-block vs del-block ORDER in redline oracles.

For every oracle document.xml, walk body-level blocks (w:p / w:tbl) and
classify each as D (del-marked para: mark rPr w:del or all-del runs),
I (ins-marked para or table with all-ins rows), E (everything else).
Collapse runs of identical letters into a pattern string (e.g. "E I D I E").
Report the distribution of D/I adjacency orders: for each maximal mixed
del+ins cluster, record the pattern (e.g. "DI", "ID", "IDI", "DID").

Then do the same for OUR bench15 outputs (runs/<run>/docx) and print pairs
whose cluster patterns differ from the oracle — the class members.

Usage: uv run python scripts/block_order_census.py [run_dir_name]
"""

from __future__ import annotations

import csv
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]

CORPORA = [
    ("corpus/word_based/centralized_mapping.csv",
     "corpus/word_based/docx_redlines_word", "{stem}_word_redline.docx|{stem}_redline.docx"),
    ("corpus/word_based/centralized_mapping_randomized.csv",
     "corpus/word_based/docx_redlines_randomized", "{stem}_redline.docx"),
    ("corpus/word_redlines_superdoc/centralized_mapping.csv",
     "corpus/word_redlines_superdoc/docx_redlines_word", "{stem}_redline.docx"),
]

BLOCK_RE = re.compile(r'<w:(p|tbl)[ >].*?</w:\1>', re.S)


def classify(seg: str, kind: str) -> str:
    if kind == "tbl":
        has_ins = "<w:ins " in seg
        has_del = "<w:del " in seg or "w:delText" in seg
        if has_ins and not has_del:
            return "I"
        if has_del and not has_ins:
            return "D"
        return "E"
    ppr_end = seg.find("</w:pPr>")
    mark = seg[:ppr_end] if ppr_end > 0 else ""
    mark_ins = "<w:ins " in mark
    mark_del = "<w:del " in mark
    body = seg[ppr_end:] if ppr_end > 0 else seg
    has_text = "<w:t>" in body or "<w:t " in body
    has_deltext = "w:delText" in body
    ins_runs = "<w:ins " in body
    if mark_del or (has_deltext and not has_text and not ins_runs):
        return "D"
    if mark_ins or (ins_runs and not has_deltext and not has_text):
        return "I"
    return "E"


def pattern(path):
    try:
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    except Exception:
        return None
    body_start = xml.find("<w:body>")
    letters = []
    # body-level only: skip blocks nested in tables by tracking depth crudely
    depth = 0
    for m in re.finditer(r'<w:tbl[ >]|</w:tbl>|<w:p [^>]*>|<w:p>|</w:p>', xml[body_start:]):
        t = m.group(0)
        if t.startswith("<w:tbl"):
            if depth == 0:
                letters.append(("tbl", m.start()))
            depth += 1
        elif t == "</w:tbl>":
            depth -= 1
        elif t.startswith("<w:p") and depth == 0:
            letters.append(("p", m.start()))
    # classify each body-level block by slicing to next sibling start
    out = []
    xs = xml[body_start:]
    for i, (kind, pos) in enumerate(letters):
        end = letters[i + 1][1] if i + 1 < len(letters) else len(xs)
        out.append(classify(xs[pos:end], kind))
    return "".join(out)


def clusters(p: str):
    """maximal substrings of D/I (len>=2 with both letters present)."""
    out = []
    for m in re.finditer(r'[DI]{2,}', p):
        s = m.group(0)
        if "D" in s and "I" in s:
            # collapse runs: DDII -> DI
            out.append(re.sub(r'(.)\1+', r'\1', s))
    return out


def main():
    run = sys.argv[1] if len(sys.argv) > 1 else "jubarte-rust_2026-08-12_12-01"
    ours_dir = BENCH_ROOT / "runs" / run / "docx"
    orc_pat = Counter()
    mismatches = []
    n = 0
    for man, odir, pat in CORPORA:
        mp = BENCH_ROOT / man
        if not mp.exists():
            continue
        for row in csv.DictReader(mp.open()):
            stem = row["pair_stem"]
            oracle = None
            for cand in pat.format(stem=stem).split("|"):
                q = BENCH_ROOT / odir / cand
                if q.exists():
                    oracle = q
                    break
            ours = ours_dir / f"{stem}_jubarte-rust_redline.docx"
            if not oracle or not ours.exists():
                continue
            po, pu = pattern(oracle), pattern(ours)
            if po is None or pu is None:
                continue
            n += 1
            co, cu = clusters(po), clusters(pu)
            for c in co:
                orc_pat[c] += 1
            if co != cu:
                mismatches.append((stem, co, cu))
    print(f"pairs scanned: {n}")
    print("\nORACLE mixed-cluster patterns (collapsed):")
    for k, v in orc_pat.most_common(12):
        print(f"  {k:8} x{v}")
    print(f"\npairs where OUR cluster patterns differ from oracle: {len(mismatches)}")
    for stem, co, cu in mismatches[:20]:
        print(f"  {stem[:56]:56} oracle={co} ours={cu}")


if __name__ == "__main__":
    main()
