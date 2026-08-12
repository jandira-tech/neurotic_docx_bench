#!/usr/bin/env python3
"""Granularity proxy: generate all pairs with a given binary, score the
body-block letter pattern (D/I/P/E, from pair_vs_replace_matrix.blocks)
against the oracle's via normalized edit distance. Render-free objective
for tuning the pair-vs-replace gates.

Usage: uv run python scripts/granularity_proxy.py <binary> <workdir> [--jobs N]
"""

from __future__ import annotations

import csv
import subprocess
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH_ROOT / "scripts"))
from pair_vs_replace_matrix import blocks  # noqa: E402

CORPORA = [
    ("corpus/word_based/centralized_mapping.csv", "corpus/word_based/docx_source",
     "corpus/word_based/docx_redlines_word", "{stem}_word_redline.docx|{stem}_redline.docx"),
    ("corpus/word_based/centralized_mapping_randomized.csv", "corpus/word_based/docx_source_randomized",
     "corpus/word_based/docx_redlines_randomized", "{stem}_redline.docx"),
    ("corpus/word_redlines_superdoc/centralized_mapping.csv", "corpus/word_redlines_superdoc/docx_source",
     "corpus/word_redlines_superdoc/docx_redlines_word", "{stem}_redline.docx"),
]


def letters(path):
    try:
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    except Exception:
        return None
    return "".join(l for l, _a, _b in blocks(xml))


def lev(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def one(args):
    stem, a, b, oracle, bin_, wd = args
    out = f"{wd}/{stem}.docx"
    r = subprocess.run([bin_, a, b, "-o", out, "--force", "--quiet"], capture_output=True)
    if r.returncode != 0:
        return (stem, None)
    po, pu = letters(oracle), letters(out)
    if po is None or pu is None:
        return (stem, None)
    d = lev(po, pu)
    return (stem, (d, max(len(po), len(pu), 1), po, pu))


def main():
    bin_, wd = sys.argv[1], sys.argv[2]
    Path(wd).mkdir(parents=True, exist_ok=True)
    jobs = []
    for man, src, odir, pat in CORPORA:
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
            if oracle:
                jobs.append((stem, str(BENCH_ROOT / src / row["docx_source_base"]),
                             str(BENCH_ROOT / src / row["docx_source_next"]), str(oracle), bin_, wd))
    seen = set()
    jobs = [j for j in jobs if not (j[0] in seen or seen.add(j[0]))]
    total_d = total_n = exact = fails = 0
    worst = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for stem, res in ex.map(one, jobs, chunksize=8):
            if res is None:
                fails += 1
                continue
            d, n, po, pu = res
            total_d += d
            total_n += n
            if d == 0:
                exact += 1
            else:
                worst.append((d, stem, po[:40], pu[:40]))
    worst.sort(reverse=True)
    print(f"pairs {len(jobs)}  fails {fails}  EXACT {exact}  "
          f"sum-lev {total_d}  agreement {1 - total_d / max(total_n, 1):.4f}")
    for d, stem, po, pu in worst[:10]:
        print(f"  lev={d:3}  {stem[:48]:48} O={po} U={pu}")


if __name__ == "__main__":
    main()
