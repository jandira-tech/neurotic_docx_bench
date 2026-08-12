#!/usr/bin/env python3
"""Render-free structural proxy vs the Word-oracle redline DOCX.

For every corpus pair: generate with the installed jubarte-rust binary,
then compare body-paragraph STRUCTURE against the oracle redline DOCX:
per paragraph (mark-revision, run-kind sequence, normalized text). Reports
a per-doc similarity (SequenceMatcher over paragraph signatures) — NOT the
pixel score, but a steering signal when LibreOffice is unavailable.

Usage:
  uv run python scripts/struct_proxy_jubarte.py [--limit N] [--out FILE]
  uv run python scripts/struct_proxy_jubarte.py --only stem1 stem2 …
"""

from __future__ import annotations

import argparse
import csv
import difflib
import json
import re
import subprocess
import sys
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
BIN = BENCH_ROOT / "src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline"

CORPORA = [
    (
        "corpus/word_based/centralized_mapping.csv",
        "corpus/word_based/docx_source",
        "corpus/word_based/docx_redlines_word",
        "{stem}_word_redline.docx|{stem}_redline.docx",
    ),
    (
        "corpus/word_based/centralized_mapping_randomized.csv",
        "corpus/word_based/docx_source_randomized",
        "corpus/word_based/docx_redlines_randomized",
        "{stem}_redline.docx",
    ),
    (
        "corpus/word_redlines_superdoc/centralized_mapping.csv",
        "corpus/word_redlines_superdoc/docx_source",
        "corpus/word_redlines_superdoc/docx_redlines_word",
        "{stem}_redline.docx",
    ),
]

P_RE = re.compile(r"<w:p[ >].*?</w:p>|<w:p/>", re.S)
T_RE = re.compile(r"<w:(?:t|delText)[^>]*>([^<]*)</w:(?:t|delText)>")
MARK_RE = re.compile(r"<w:rPr>\s*<w:(ins|del)[ /]")


def para_sigs(doc_xml: str) -> list[str]:
    sigs = []
    for m in P_RE.finditer(doc_xml):
        p = m.group(0)
        text = "".join(T_RE.findall(p))
        text = re.sub(r"\s+", " ", text).strip()[:80]
        mark = MARK_RE.search(p)
        has_ins = "<w:ins " in p
        has_del = "<w:del " in p or "<w:delText" in p
        kind = ("I" if has_ins else "") + ("D" if has_del else "")
        sigs.append(f"{mark.group(1) if mark else '-'}|{kind}|{text}")
    return sigs


def doc_xml_of(path: Path) -> str | None:
    try:
        return zipfile.ZipFile(path).read("word/document.xml").decode("utf8", "ignore")
    except Exception:
        return None


def main() -> None:
    global BIN
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", type=Path, default=BENCH_ROOT / "results" / "struct_proxy.json")
    ap.add_argument("--bin", type=Path, default=BIN,
                    help="engine binary (default: installed bench dist)")
    a = ap.parse_args()
    BIN = a.bin

    pairs = []
    for manifest, src, odir, pat in CORPORA:
        mp = BENCH_ROOT / manifest
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
            if oracle is None:
                continue
            pairs.append(
                (
                    stem,
                    BENCH_ROOT / src / row["docx_source_base"],
                    BENCH_ROOT / src / row["docx_source_next"],
                    oracle,
                )
            )
    if a.only:
        pairs = [p for p in pairs if p[0] in set(a.only)]
    if a.limit:
        pairs = pairs[: a.limit]

    tmp = Path(tempfile.mkdtemp(prefix="structproxy-"))
    results: dict[str, float] = {}
    fails: list[str] = []

    def one(item):
        stem, base, nxt, oracle = item
        out = tmp / f"{stem}.docx"
        r = subprocess.run(
            [str(BIN), str(base), str(nxt), "-o", str(out), "--force", "--quiet"],
            capture_output=True,
        )
        if r.returncode != 0 or not out.exists():
            fails.append(stem)
            return
        cx, ox = doc_xml_of(out), doc_xml_of(oracle)
        if cx is None or ox is None:
            fails.append(stem)
            return
        ratio = difflib.SequenceMatcher(None, para_sigs(cx), para_sigs(ox)).ratio()
        results[stem] = round(100 * ratio, 2)
        out.unlink(missing_ok=True)

    with ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(one, pairs))

    vals = sorted(results.values())
    n = len(vals)
    if n:
        mean = sum(vals) / n
        median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
        print(f"structural proxy: n={n} mean {mean:.2f} median {median:.2f} genfails {len(fails)}")
        worst = sorted(results.items(), key=lambda kv: kv[1])[:15]
        for k, v in worst:
            print(f"  {v:6.2f}  {k[:70]}")
    a.out.write_text(json.dumps(results, indent=0, sort_keys=True))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
