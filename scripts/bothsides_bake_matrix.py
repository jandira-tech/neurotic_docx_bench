#!/usr/bin/env python3
"""M480 evidence matrix: for every pair, classify how the WORD ORACLE treats
both-sides styles whose declarations differ between A and B — does the live
block carry dd-delta NEUTRALIZERS (values matching B-docDefaults where the
two docDefaults disagree), or is it a VERBATIM copy of B's declaration?

Emits one row per (pair, style) with features for discriminator mining:
  pair, style, family (heading/table/other), a_declares, b_declares,
  oracle_kern, b_dd_kern, a_dd_kern, verdict (neutralized|verbatim|other)

Render-free: reads source + oracle docx only.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
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


def styles_of(path):
    try:
        xml = zipfile.ZipFile(path).read("word/styles.xml").decode("utf8", "ignore")
    except Exception:
        return None, None
    d = {}
    for m in re.finditer(r'<w:style [^>]*?w:styleId="[^"]*".*?</w:style>', xml, re.S):
        s = m.group(0)
        sid = re.search(r'w:styleId="([^"]*)"', s).group(1)
        live = re.sub(r'<w:pPrChange.*?</w:pPrChange>|<w:rPrChange.*?</w:rPrChange>', '', s, flags=re.S)
        d[sid] = live
    dd = re.search(r'<w:docDefaults>.*?</w:docDefaults>', xml, re.S)
    return d, (dd.group(0) if dd else "")


def dd_val(dd, name, dflt):
    m = re.search(rf'<w:{name} w:val="([^"]*)"', dd)
    return m.group(1) if m else dflt


def declared_val(style_live, name):
    m = re.search(rf'<w:{name} w:val="([^"]*)"', style_live)
    return m.group(1) if m else None


def one(item):
    stem, a_p, b_p, o_p = item
    a_s, a_dd = styles_of(a_p)
    b_s, b_dd = styles_of(b_p)
    o_s, _ = styles_of(o_p)
    if not (a_s and b_s and o_s):
        return []
    a_kern, b_kern = dd_val(a_dd, "kern", "0"), dd_val(b_dd, "kern", "0")
    if a_kern == b_kern:
        return []  # no dd kern delta → neutralizer question moot for this pair
    rows = []
    for sid in set(a_s) & set(b_s) & set(o_s):
        # only styles where declarations differ (the merge fires)
        if re.sub(r'\s+|w:rsid\w*="[^"]*"', '', a_s[sid]) == re.sub(r'\s+|w:rsid\w*="[^"]*"', '', b_s[sid]):
            continue
        ok = declared_val(o_s[sid], "kern")
        bk = declared_val(b_s[sid], "kern")
        ak = declared_val(a_s[sid], "kern")
        if ok is not None and bk is None and ok == b_kern:
            verdict = "neutralized"
        elif ok == bk or (ok is None and bk is None):
            verdict = "verbatim"
        else:
            verdict = "other"
        fam = ("heading" if re.match(r'Heading\d|Title|Subtitle|Quote|IntenseQuote', sid)
               else "table" if "Table" in sid or "table" in sid
               else "char" if sid.endswith("Char")
               else "other")
        rows.append({"pair": stem, "style": sid, "family": fam,
                     "a_declares_kern": ak, "b_declares_kern": bk, "oracle_kern": ok,
                     "a_dd_kern": a_kern, "b_dd_kern": b_kern, "verdict": verdict})
    return rows


def main():
    pairs = []
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
            if oracle:
                pairs.append((stem, BENCH_ROOT / src / row["docx_source_base"],
                              BENCH_ROOT / src / row["docx_source_next"], oracle))
    all_rows = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for rows in ex.map(one, pairs):
            all_rows.extend(rows)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else BENCH_ROOT / "results" / "bothsides_bake_matrix.json"
    json.dump(all_rows, out.open("w"), indent=0)
    from collections import Counter
    v = Counter(r["verdict"] for r in all_rows)
    print(f"rows: {len(all_rows)} over {len(set(r['pair'] for r in all_rows))} pairs  verdicts: {dict(v)}")
    by_fam = Counter((r["family"], r["verdict"]) for r in all_rows)
    for k in sorted(by_fam):
        print(f"  {k[0]:8} {k[1]:11} {by_fam[k]}")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
