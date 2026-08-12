#!/usr/bin/env python3
"""Effective-style comparator: resolve each paragraph style through its
basedOn chain + docDefaults to concrete rendered values and diff OURS vs the
Word-oracle redline. Raw styles.xml diffs mislead — Word often expresses a
look via the promoted Normal while we bake per-style (file_198 hit pixel 100
with a very different styles.xml). Only EFFECTIVE divergence moves pixels.

Usage:
  uv run python scripts/effective_styles_diff.py <ours.docx> <oracle.docx>
  uv run python scripts/effective_styles_diff.py --pair <pair_stem> [--bin BIN]
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BIN = BENCH_ROOT / "src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline"

CORPORA = [
    ("corpus/word_based/centralized_mapping.csv", "corpus/word_based/docx_source",
     "corpus/word_based/docx_redlines_word", "{stem}_word_redline.docx|{stem}_redline.docx"),
    ("corpus/word_based/centralized_mapping_randomized.csv", "corpus/word_based/docx_source_randomized",
     "corpus/word_based/docx_redlines_randomized", "{stem}_redline.docx"),
    ("corpus/word_redlines_superdoc/centralized_mapping.csv", "corpus/word_redlines_superdoc/docx_source",
     "corpus/word_redlines_superdoc/docx_redlines_word", "{stem}_redline.docx"),
]

STYLE_RE = re.compile(r'<w:style [^>]*?w:styleId="([^"]*)".*?</w:style>', re.S)
ATTR = lambda el, a: re.search(rf'{a}="([^"]*)"', el)


def parse_styles(xml: str):
    """styleId -> dict(basedOn, declared rPr/pPr scalar props, live only)."""
    out = {}
    for m in re.finditer(r'<w:style [^>]*?w:styleId="[^"]*".*?</w:style>', xml, re.S):
        s = m.group(0)
        sid = re.search(r'w:styleId="([^"]*)"', s).group(1)
        d = {"basedOn": None}
        b = re.search(r'<w:basedOn w:val="([^"]*)"', s)
        if b:
            d["basedOn"] = b.group(1)
        # live blocks only: cut *Change records
        live = re.sub(r'<w:pPrChange.*?</w:pPrChange>|<w:rPrChange.*?</w:rPrChange>', '', s, flags=re.S)
        rf = re.search(r'<w:rFonts([^/]*)/>', live)
        if rf:
            a = re.search(r'w:ascii(?:Theme)?="([^"]*)"', rf.group(1))
            if a:
                d["font"] = a.group(1)
        for name in ["sz", "b", "i", "color", "kern"]:
            e = re.search(rf'<w:{name}(?: w:val="([^"]*)")? ?/>', live)
            if e:
                d[name] = e.group(1) if e.group(1) is not None else "on"
        sp = re.search(r'<w:spacing([^/]*)/>', live)
        if sp:
            for a in ["before", "after", "line"]:
                v = re.search(rf'w:{a}="([^"]*)"', sp.group(1))
                if v:
                    d[f"sp_{a}"] = v.group(1)
        out[sid] = d
    return out


def parse_dd(xml: str):
    d = {}
    m = re.search(r'<w:docDefaults>.*?</w:docDefaults>', xml, re.S)
    if not m:
        return d
    dd = m.group(0)
    rf = re.search(r'<w:rFonts([^/]*)/>', dd)
    if rf:
        a = re.search(r'w:ascii(?:Theme)?="([^"]*)"', rf.group(1))
        if a:
            d["font"] = a.group(1)
    for name in ["sz", "kern"]:
        e = re.search(rf'<w:{name} w:val="([^"]*)"', dd)
        d[name] = e.group(1) if e else ("20" if name == "sz" else None)
    sp = re.search(r'<w:pPrDefault>.*?<w:spacing([^/]*)/>', dd, re.S)
    if sp:
        for a in ["before", "after", "line"]:
            v = re.search(rf'w:{a}="([^"]*)"', sp.group(1))
            if v:
                d[f"sp_{a}"] = v.group(1)
    return d


KEYS = ["font", "sz", "b", "i", "color", "kern", "sp_before", "sp_after", "sp_line"]


def effective(styles: dict, dd: dict, sid: str):
    vals = {}
    chain, s = [], sid
    for _ in range(12):
        if s not in styles:
            break
        chain.append(s)
        s = styles[s]["basedOn"]
        if s is None:
            break
    for k in KEYS:
        v = None
        for cs in chain:  # nearest declaration wins
            if k in styles[cs]:
                v = styles[cs][k]
                break
        if v is None:
            v = dd.get(k)
        vals[k] = v
    return vals


def doc_styles(path: Path):
    xml = zipfile.ZipFile(path).read("word/styles.xml").decode("utf8", "ignore")
    return parse_styles(xml), parse_dd(xml)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docs", nargs="*", help="ours.docx oracle.docx")
    ap.add_argument("--pair", help="pair stem: generate ours, locate oracle")
    ap.add_argument("--bin", type=Path, default=DEFAULT_BIN)
    a = ap.parse_args()

    if a.pair:
        for man, src, odir, pat in CORPORA:
            mp = BENCH_ROOT / man
            if not mp.exists():
                continue
            for row in csv.DictReader(mp.open()):
                if row["pair_stem"] != a.pair:
                    continue
                oracle = None
                for cand in pat.format(stem=a.pair).split("|"):
                    p = BENCH_ROOT / odir / cand
                    if p.exists():
                        oracle = p
                        break
                if oracle is None:
                    sys.exit("oracle docx not found")
                ours = Path(tempfile.mkdtemp()) / "ours.docx"
                r = subprocess.run(
                    [str(a.bin), str(BENCH_ROOT / src / row["docx_source_base"]),
                     str(BENCH_ROOT / src / row["docx_source_next"]), "-o", str(ours),
                     "--force", "--quiet"], capture_output=True)
                if r.returncode != 0:
                    sys.exit(f"generate failed: {r.stderr[:200]}")
                a.docs = [str(ours), str(oracle)]
                break
            if a.docs:
                break
    if len(a.docs) != 2:
        sys.exit("need ours.docx oracle.docx (or --pair)")

    (os_, od), (rs, rd) = doc_styles(Path(a.docs[0])), doc_styles(Path(a.docs[1]))
    shared = sorted(set(os_) & set(rs))
    n_diff = 0
    for sid in shared:
        eo, er = effective(os_, od, sid), effective(rs, rd, sid)
        norm = lambda k, v: (None if v in ("auto",) and k == "color" else v)
        deltas = {k: (er[k], eo[k]) for k in KEYS if norm(k, er[k]) != norm(k, eo[k])}
        if deltas:
            n_diff += 1
            print(f"{sid}: " + "  ".join(f"{k}: oracle={v[0]} ours={v[1]}" for k, v in deltas.items()))
    only_o = sorted(set(os_) - set(rs))
    only_r = sorted(set(rs) - set(os_))
    if only_o:
        print(f"(only in ours: {only_o[:8]})")
    if only_r:
        print(f"(only in oracle: {only_r[:8]})")
    print(f"== {n_diff}/{len(shared)} shared styles effectively differ ==")


if __name__ == "__main__":
    main()
