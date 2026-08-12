#!/usr/bin/env python3
"""Task #8 phase 2: mine Word's pair-vs-replace threshold.

From every oracle redline, collect two verdict populations:
  PAIRED  — body paragraphs containing BOTH ins and del runs (Word paired
            A-para with B-para and edited inside). A-text = EQ + delText,
            B-text = EQ + ins text.
  REPLACED — maximal I-block + D-block clusters (Word refused to pair).
            For each D-para take the best-similarity I-para in the same
            cluster as its candidate counterpart.
Similarity = SequenceMatcher ratio on whitespace-normalized text.
If Word uses a similarity threshold for pairing, the PAIRED distribution
should sit above it and the REPLACED best-candidate distribution below.

Usage: uv run python scripts/pair_vs_replace_matrix.py [out.json]
"""

from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from difflib import SequenceMatcher
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


def para_texts(seg: str):
    """(a_text, b_text, has_ins, has_del) for one w:p element."""
    ppr_end = seg.find("</w:pPr>")
    body = seg[ppr_end:] if ppr_end > 0 else seg
    a_parts, b_parts = [], []
    pos = 0
    for m in re.finditer(r'<w:ins [^>]*>.*?</w:ins>|<w:del [^>]*>.*?</w:del>', body, re.S):
        eq_zone = body[pos:m.start()]
        eq = "".join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', eq_zone))
        a_parts.append(eq)
        b_parts.append(eq)
        blk = m.group(0)
        if blk.startswith("<w:ins"):
            b_parts.append("".join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', blk)))
        else:
            a_parts.append("".join(re.findall(r'<w:delText[^>]*>([^<]*)</w:delText>', blk)))
        pos = m.end()
    tail = "".join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', body[pos:]))
    a_parts.append(tail)
    b_parts.append(tail)
    has_ins = "<w:ins " in body
    has_del = "<w:del " in body or "w:delText" in body
    norm = lambda parts: re.sub(r'\s+', ' ', "".join(parts)).strip()
    return norm(a_parts), norm(b_parts), has_ins, has_del


def blocks(xml: str):
    """body-level paragraphs only: (kind_letter, a_text, b_text)."""
    body_start = xml.find("<w:body>")
    xs = xml[body_start:]
    marks = []
    depth = 0
    for m in re.finditer(r'<w:tbl[ >]|</w:tbl>|<w:p [^>]*>|<w:p>|</w:p>', xs):
        t = m.group(0)
        if t.startswith("<w:tbl"):
            depth += 1
        elif t == "</w:tbl>":
            depth -= 1
        elif t.startswith("<w:p") and depth == 0:
            marks.append(m.start())
    out = []
    for i, pos in enumerate(marks):
        end = marks[i + 1] if i + 1 < len(marks) else len(xs)
        seg = xs[pos:end]
        ppr_end = seg.find("</w:pPr>")
        mark = seg[:ppr_end] if ppr_end > 0 else ""
        a, b, hi, hd = para_texts(seg)
        if "<w:del " in mark or (hd and not hi and not ("<w:t>" in seg[ppr_end:] or "<w:t " in seg[ppr_end:])):
            letter = "D"
        elif "<w:ins " in mark and not hd:
            letter = "I"
        elif hi and hd:
            letter = "P"  # paired: intra-para edit
        else:
            letter = "E"
        out.append((letter, a, b))
    return out


def main():
    paired_sims, replaced_sims = [], []
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
            if not oracle:
                continue
            try:
                xml = zipfile.ZipFile(oracle).read("word/document.xml").decode("utf8", "ignore")
            except Exception:
                continue
            bl = blocks(xml)
            for letter, a, b in bl:
                if letter == "P" and a and b:
                    paired_sims.append(round(SequenceMatcher(None, a, b).ratio(), 3))
            # replaced clusters: adjacent runs of D/I
            i = 0
            while i < len(bl):
                if bl[i][0] in "DI":
                    j = i
                    while j < len(bl) and bl[j][0] in "DI":
                        j += 1
                    ds = [x for x in bl[i:j] if x[0] == "D" and x[1]]
                    is_ = [x for x in bl[i:j] if x[0] == "I" and x[2]]
                    for _, da, _2 in ds:
                        best = max((SequenceMatcher(None, da, ib).ratio() for _3, _4, ib in is_), default=None)
                        if best is not None:
                            replaced_sims.append(round(best, 3))
                    i = j
                else:
                    i += 1
    out = {"paired": paired_sims, "replaced_best": replaced_sims}
    dst = sys.argv[1] if len(sys.argv) > 1 else "/tmp/pair_vs_replace.json"
    json.dump(out, open(dst, "w"))
    import statistics
    for k, v in out.items():
        if v:
            v2 = sorted(v)
            print(f"{k}: n={len(v)} p10={v2[len(v)//10]:.2f} median={statistics.median(v):.2f} p90={v2[9*len(v)//10]:.2f}")
    # overlap: what fraction of replaced_best exceeds the paired p10?
    if paired_sims and replaced_sims:
        p10 = sorted(paired_sims)[len(paired_sims)//10]
        above = sum(1 for x in replaced_sims if x >= p10)
        print(f"replaced_best >= paired-p10 ({p10:.2f}): {above}/{len(replaced_sims)}")
    print("wrote", dst)


if __name__ == "__main__":
    main()
