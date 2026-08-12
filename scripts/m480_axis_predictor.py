#!/usr/bin/env python3
"""M480 axis generalization: validate the chain-rule model (v6, 98.7% on
kern) on other docDefaults-delta axes — sz (rPr) and line (pPr spacing).

For every manifest pair whose docDefaults disagree on the axis, predict the
oracle's per-style declared value with the minimal-chain rule:
  - merge predicate: live FORMATTING blocks (pPr+rPr) differ, rsid/meta noise
    stripped;
  - target = B-side effective (B chain then B dd);
  - provided-without-own = nearest post-merge ancestor declaration
    (char styles fall through to post-merge Normal — the paragraph layer),
    else A's dd (the output keeps A's docDefaults);
  - B-declared own value survives unless redundant (== provided-without);
  - undeclared + provided != target => write target.
Score prediction vs oracle declaration; report miss pairs and pairs where
Word wrote NOTHING despite drift (the skip class), split by direction.

Usage: uv run python scripts/m480_axis_predictor.py sz|line|kern
"""

from __future__ import annotations

import csv
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

AXES = {
    # (block, extractor-regex on live style xml, dd-extractor, implicit default)
    "kern": ("rPr", r'<w:kern w:val="([^"]*)"', r'<w:rPrDefault>.*?<w:kern w:val="([^"]*)"', "0"),
    "sz":   ("rPr", r'<w:sz w:val="([^"]*)"', r'<w:rPrDefault>.*?<w:sz w:val="([^"]*)"', "20"),
    "line": ("pPr", r'<w:spacing[^/>]*w:line="([^"]*)"', r'<w:pPrDefault>.*?<w:spacing[^/>]*w:line="([^"]*)"', "240"),
}


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


def load(path, axis):
    block, val_re, dd_re, dflt = AXES[axis]
    try:
        xml = zipfile.ZipFile(path).read("word/styles.xml").decode("utf8", "ignore")
    except Exception:
        return None
    styles = {}
    for m in re.finditer(r'<w:style [^>]*?w:styleId="[^"]*".*?</w:style>', xml, re.S):
        s = m.group(0)
        sid = re.search(r'w:styleId="([^"]*)"', s).group(1)
        head = s[:s.index(">")]
        stype = (re.search(r'w:type="([^"]*)"', head) or [None, "?"])[1]
        live = re.sub(r'<w:pPrChange.*?</w:pPrChange>|<w:rPrChange.*?</w:rPrChange>', '', s, flags=re.S)
        based = re.search(r'<w:basedOn w:val="([^"]*)"', live)
        # search only within the relevant block to avoid cross-block hits
        blk = re.search(rf'<w:{block}>.*?</w:{block}>|<w:{block} ?/>', live, re.S)
        v = re.search(val_re, blk.group(0)) if blk else None
        fmt = "".join(mm.group(0) for mm in re.finditer(r'<w:pPr>.*?</w:pPr>|<w:rPr>.*?</w:rPr>', live, re.S))
        norm = re.sub(r'\s+|w:rsid\w*="[^"]*"', '', fmt)
        styles[sid] = {"based": based.group(1) if based else None,
                       "val": v.group(1) if v else None, "norm": norm, "type": stype}
    ddm = re.search(r'<w:docDefaults>.*?</w:docDefaults>', xml, re.S)
    dd = ddm.group(0) if ddm else ""
    k = re.search(dd_re, dd, re.S)
    return styles, (k.group(1) if k else dflt)


def chain(styles, sid):
    out, s = [], sid
    for _ in range(12):
        if s not in styles:
            break
        out.append(s)
        s = styles[s]["based"]
        if s is None:
            break
    return out


def eff(styles, dd, sid):
    for cs in chain(styles, sid):
        if styles[cs]["val"] is not None:
            return styles[cs]["val"]
    return dd


def predict_pair(a, b, axis):
    la, lb = load(a, axis), load(b, axis)
    if not (la and lb):
        return None, None
    a_s, a_dd = la
    b_s, b_dd = lb
    merged = {s for s in set(a_s) & set(b_s) if a_s[s]["norm"] != b_s[s]["norm"]}
    order, seen = [], set()
    def visit(sid):
        if sid in seen or sid not in b_s:
            return
        seen.add(sid)
        if b_s[sid]["based"]:
            visit(b_s[sid]["based"])
        order.append(sid)
    for sid in b_s:
        visit(sid)
    out_decl = {}
    for sid in order:
        if sid not in merged:
            out_decl[sid] = a_s[sid]["val"] if sid in a_s else b_s[sid]["val"]
            continue
        target = eff(b_s, b_dd, sid)
        own = b_s[sid]["val"]
        without = a_dd
        anc = chain(b_s, sid)[1:]
        if b_s[sid]["type"] == "character" and "Normal" not in anc and "Normal" in out_decl:
            anc = anc + ["Normal"]
        for cs in anc:
            v = out_decl.get(cs)
            if v is not None:
                without = v
                break
        if own is not None:
            out_decl[sid] = None if without == target else own
        elif without != target:
            out_decl[sid] = target
        else:
            out_decl[sid] = None
    return out_decl, (a_s, a_dd, b_s, b_dd, merged)


def main():
    axis = sys.argv[1]
    paths = pair_paths()
    hits = misses = 0
    miss_pairs = Counter()
    skip_pairs = []
    n_pairs = 0
    for stem, (a, b, o) in sorted(paths.items()):
        la, lb, lo = load(a, axis), load(b, axis), load(o, axis)
        if not (la and lb and lo):
            continue
        if la[1] == lb[1]:
            continue  # no dd delta on this axis
        n_pairs += 1
        pred, ctx = predict_pair(a, b, axis)
        if pred is None:
            continue
        a_s, a_dd, b_s, b_dd, merged = ctx
        o_s, _ = lo
        pair_pred_writes = pair_orac_writes = 0
        for sid in merged:
            if sid not in o_s or b_s[sid]["type"] in ("table", "numbering"):
                continue
            ov = o_s[sid]["val"]
            pv = pred.get(sid)
            bv = b_s[sid]["val"]
            if pv is not None and pv != bv:
                pair_pred_writes += 1
            if ov is not None and ov != bv:
                pair_orac_writes += 1
            if ov == pv:
                hits += 1
            else:
                misses += 1
                miss_pairs[stem] += 1
        if pair_pred_writes > 0 and pair_orac_writes == 0:
            skip_pairs.append((stem, a_dd, b_dd))
    total = hits + misses
    print(f"axis={axis}: pairs with dd delta: {n_pairs}  prediction {hits}/{total} = {100*hits/max(total,1):.1f}%")
    print(f"\nSKIP pairs (oracle wrote nothing, model wanted writes): {len(skip_pairs)}")
    for s, ad, bd in skip_pairs[:15]:
        print(f"   {s[:62]:62} dd {ad}->{bd}")
    print("\nworst miss pairs:")
    for p, c in miss_pairs.most_common(10):
        print(f"   {c:3}  {p[:64]}")


if __name__ == "__main__":
    main()
