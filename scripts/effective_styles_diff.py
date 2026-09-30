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
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from neurotic_docx_bench import corpus_paths

BENCH_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BIN = BENCH_ROOT / "src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline"


def oracle_pairs():
    """One Word compare per pair stem over the three redline sets."""
    for set_name in corpus_paths.REDLINE_SETS:
        yield from corpus_paths.by_stem(set_name, word=BENCH_ROOT / corpus_paths.WORD,
                                        libreoffice=BENCH_ROOT / corpus_paths.LIBREOFFICE).values()


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
        for p in oracle_pairs():
            if p.stem != a.pair:
                continue
            if not p.redline.exists():
                sys.exit("oracle docx not found")
            ours = Path(tempfile.mkdtemp()) / "ours.docx"
            r = subprocess.run(
                [str(a.bin), str(p.base), str(p.next), "-o", str(ours),
                 "--force", "--quiet"], capture_output=True)
            if r.returncode != 0:
                sys.exit(f"generate failed: {r.stderr[:200]}")
            a.docs = [str(ours), str(p.redline)]
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
