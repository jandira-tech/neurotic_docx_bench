#!/usr/bin/env python3
"""M480 model validation: predict Word's per-style neutralizer writes with the
minimal-declaration chain rule and score the prediction against every oracle
row in the bake matrix.

Model: output keeps A's docDefaults. For each both-sides style whose A/B
declarations differ (merge fires), processed parents-first, and for each
attribute: target = B-side effective value (B chain + B dd, absent kern == 0,
absent ligatures == none); provided = output-chain value (own B declarations,
then post-merge ancestors' declarations, then A dd). Write target live iff
provided != target. Styles that never merge are untouched.

Prediction per (pair, style) for kern: neutralized / verbatim — compare with
the matrix verdict. Render-free.

Usage: uv run python scripts/m480_chain_predictor.py <bake_matrix.json>
"""

from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
from collections import Counter
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


def load(path):
    """styles: sid -> (basedOn, declared_kern_or_None, norm_decl, is_default); dd_kern."""
    try:
        xml = zipfile.ZipFile(path).read("word/styles.xml").decode("utf8", "ignore")
    except Exception:
        return None
    styles = {}
    for m in re.finditer(r'<w:style [^>]*?w:styleId="[^"]*".*?</w:style>', xml, re.S):
        s = m.group(0)
        sid = re.search(r'w:styleId="([^"]*)"', s).group(1)
        head = s[:s.index(">")]
        is_default = 'w:default="1"' in head or 'w:default="true"' in head
        live = re.sub(r'<w:pPrChange.*?</w:pPrChange>|<w:rPrChange.*?</w:rPrChange>', '', s, flags=re.S)
        based = re.search(r'<w:basedOn w:val="([^"]*)"', live)
        kern = re.search(r'<w:kern w:val="([^"]*)"', live)
        # merge predicate: FORMATTING blocks only (metadata like name/qFormat/
        # semiHidden differences don't trigger Word's tracked redefinition)
        fmt = "".join(mm.group(0) for mm in re.finditer(r'<w:pPr>.*?</w:pPr>|<w:rPr>.*?</w:rPr>', live, re.S))
        norm = re.sub(r'\s+|w:rsid\w*="[^"]*"', '', fmt)
        has_rpr = "<w:rPr>" in live or "<w:rPr " in live
        styles[sid] = (based.group(1) if based else None,
                       kern.group(1) if kern else None, norm, is_default, has_rpr)
    ddm = re.search(r'<w:docDefaults>.*?</w:docDefaults>', xml, re.S)
    dd = ddm.group(0) if ddm else ""
    k = re.search(r'<w:kern w:val="([^"]*)"', dd)
    return styles, (k.group(1) if k else "0")


def chain(styles, sid):
    out, s = [], sid
    for _ in range(12):
        if s not in styles:
            break
        out.append(s)
        s = styles[s][0]
        if s is None:
            break
    return out


def effective_kern(styles, dd_kern, sid, override=None):
    """override: sid -> declared kern replacing stored declaration (post-merge)."""
    for cs in chain(styles, sid):
        v = override.get(cs, styles[cs][1]) if override else styles[cs][1]
        if v is not None:
            return v
    return dd_kern


def predict_pair(a_path, b_path):
    """Return sid -> predicted oracle-declared kern (None = no live declaration)."""
    la, lb = load(a_path), load(b_path)
    if not (la and lb):
        return None
    a_s, a_dd = la
    b_s, b_dd = lb
    merged = {sid for sid in set(a_s) & set(b_s) if a_s[sid][2] != b_s[sid][2]}
    # parents-first order over B's chains
    order, seen = [], set()
    def visit(sid):
        if sid in seen or sid not in b_s:
            return
        seen.add(sid)
        parent = b_s[sid][0]
        if parent:
            visit(parent)
        order.append(sid)
    for sid in b_s:
        visit(sid)
    out_decl = {}  # post-merge declared kern per style in the OUTPUT
    for sid in order:
        if sid not in merged:
            # untouched: output keeps... A's stored declaration for both-sides
            # styles (merge didn't fire), B's for B-only (copied) styles
            out_decl[sid] = a_s[sid][1] if sid in a_s else b_s[sid][1]
            continue
        target = effective_kern(b_s, b_dd, sid)
        own = b_s[sid][1]
        # provided WITHOUT own declaration: post-merge ancestors, then A dd
        without = a_dd
        for cs in chain(b_s, sid)[1:]:
            v = out_decl.get(cs)
            if v is not None:
                without = v
                break
        if own is not None:
            # merge keeps B's declaration unless redundant under output chain
            out_decl[sid] = None if without == target else own
        elif without != target:
            out_decl[sid] = target
        else:
            out_decl[sid] = None
    return out_decl


def main():
    matrix = json.load(open(sys.argv[1]))
    rows = [r for r in matrix if r["family"] == "heading"]
    paths = pair_paths()
    cache = {}
    score = Counter()
    misses = []
    for r in rows:
        pair = r["pair"]
        if pair not in cache:
            cache[pair] = predict_pair(*paths[pair][:2]) if pair in paths else None
        pred_decl = cache[pair]
        if pred_decl is None:
            score["nopath"] += 1
            continue
        pk = pred_decl.get(r["style"])
        # translate to matrix verdict semantics
        bk = r["b_declares_kern"]
        if pk is not None and bk is None and pk == r["b_dd_kern"]:
            pred = "neutralized"
        elif pk == bk:
            pred = "verbatim"
        else:
            pred = "other"
        ok = pred == r["verdict"]
        score["hit" if ok else "miss"] += 1
        if not ok and len(misses) < 25:
            misses.append((pair[:55], r["style"], r["verdict"], pred, pk, bk, r["oracle_kern"]))
    total = score["hit"] + score["miss"]
    print(f"kern-axis prediction: {score['hit']}/{total} = {100*score['hit']/max(total,1):.1f}%  (nopath {score['nopath']})")
    if misses:
        print("\nfirst misses (pair, style, oracle_verdict, predicted, pred_kern, b_kern, oracle_kern):")
        for m in misses:
            print("  " + " | ".join(str(x) for x in m))


if __name__ == "__main__":
    main()
