#!/usr/bin/env python3
"""Does a page break that ends the document's last paragraph make a page in Word?

Hypothesis under test (from queue rank 1, ea023ca156_r4_05_tbl_and_ref_only:
Word 1 page, jubarte 2): "when the last body paragraph ends in
<w:br w:type="page"/> with nothing painted after it, Word's PDF has no page
for the empty remainder".

No Word run is needed: the corpus holds Word's own PDF of every document.
Every corpus DOCX is classified by how its last body paragraph ends:

  trailing   the paragraph's last painted thing is a page break
  inner      the last paragraph holds a page break with text after it
  none       no page break in the last paragraph (the base rate)

and each class's documents are converted with the given jubarte binary
(--revisions word). The hypothesis predicts jubarte − Word = +1 page on the
trailing class far above the base rate of the other two. If the trailing
class splits, the split is reported by what else the paragraph holds, so a
narrower rule can be read off instead of guessed.

usage (from the bench root):
  python3 scripts/probe_trailing_page_break.py JUBARTE_BIN OUT_DIR [--base N]
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import re
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PARA = re.compile(r"<w:p[ >].*?</w:p>|<w:p/>", re.S)
PAGE_BREAK = re.compile(r'<w:br\b[^>]*w:type="page"[^>]*/>')
# What a reader sees after the break: text, a tab, a drawing, a field result…
PAINTED = re.compile(r"<w:t[ >][^<]|<w:tab/>|<w:drawing|<w:pict|<w:object|<w:sym |<w:br\b|<w:noBreakHyphen|<w:fldSimple")


def classify(docx: Path) -> dict | None:
    try:
        with zipfile.ZipFile(docx) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (zipfile.BadZipFile, KeyError, OSError):
        return None
    start = xml.find("<w:body>")
    if start < 0:
        return None
    body = xml[start:]
    # The last paragraph that is a child of the body: cut tables and text
    # boxes out first, so a cell's or a shape's paragraph is not taken.
    flat = re.sub(r"<w:tbl>.*</w:tbl>", "<w:TBL/>", body, flags=re.S)
    flat = re.sub(r"<w:txbxContent>.*?</w:txbxContent>", "", flat, flags=re.S)
    paras = PARA.findall(flat)
    if not paras:
        return None
    last = paras[-1]
    breaks = list(PAGE_BREAK.finditer(last))
    if not breaks:
        return {"class": "none"}
    after = last[breaks[-1].end():]
    before = last[: breaks[-1].start()]
    if PAINTED.search(after):
        return {"class": "inner"}
    return {
        "class": "trailing",
        "text_before": bool(re.search(r"<w:t[ >][^<]", before)),
        "comment_ref": "<w:commentReference" in last,
        "after_table": flat.rstrip().rfind("<w:TBL/>") > flat.rfind("</w:p>", 0, flat.rfind(last)) if "<w:TBL/>" in flat else False,
        "paragraphs": len(paras),
        "sect_in_para": "<w:sectPr" in last,
    }


def pages(pdf: Path) -> int | None:
    if not pdf.is_file():
        return None
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True)
    for line in out.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("binary", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--base", type=int, default=300, help="documents of class none converted for the base rate")
    ap.add_argument("--seed", type=int, default=20261003)
    args = ap.parse_args()

    docs = sorted(Path("corpus/word").glob("*/docx/*.docx"))
    with ThreadPoolExecutor(8) as pool:
        kinds = list(pool.map(classify, docs))
    by_class: dict[str, list[tuple[Path, dict]]] = collections.defaultdict(list)
    for d, k in zip(docs, kinds):
        if k is not None and (d.parent.parent / "pdf" / (d.stem + ".pdf")).is_file():
            by_class[k["class"]].append((d, k))
    rng = random.Random(args.seed)
    chosen = by_class["trailing"] + by_class["inner"] + rng.sample(by_class["none"], min(args.base, len(by_class["none"])))

    pdf_dir = args.out_dir / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    def convert(item: tuple[Path, dict]) -> dict:
        docx, kind = item
        state = docx.parent.parent.name
        out = pdf_dir / f"{state}__{docx.stem[:80]}.pdf"
        if not out.is_file():
            subprocess.run([str(args.binary), "convert", str(docx), "-o", str(out), "--revisions", "word", "--force"],
                           capture_output=True, timeout=300)
        word = pages(docx.parent.parent / "pdf" / (docx.stem + ".pdf"))
        mine = pages(out)
        return {"state": state, "stem": docx.stem, **kind, "word_pages": word, "jubarte_pages": mine,
                "delta": None if word is None or mine is None else mine - word}

    with ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(convert, chosen))

    def tally(group: list[dict]) -> dict:
        deltas = collections.Counter("fail" if r["delta"] is None else ("+1" if r["delta"] == 1 else "0" if r["delta"] == 0 else "other") for r in group)
        n = len(group)
        return {"n": n, **deltas, "plus_one_share": round(deltas["+1"] / n, 3) if n else None}

    report = {
        "stated": "a page break ending the last body paragraph makes no page in Word: jubarte − Word = +1 on the trailing class, far above the base rate",
        "corpus": {k: len(v) for k, v in by_class.items()},
        "trailing": tally([r for r in rows if r["class"] == "trailing"]),
        "inner": tally([r for r in rows if r["class"] == "inner"]),
        "none": tally([r for r in rows if r["class"] == "none"]),
        "trailing_split": {},
    }
    for key in ("text_before", "comment_ref", "sect_in_para"):
        for val in (True, False):
            report["trailing_split"][f"{key}={val}"] = tally([r for r in rows if r["class"] == "trailing" and r.get(key) is val])
    by_state = collections.defaultdict(list)
    for r in rows:
        if r["class"] == "trailing":
            by_state[r["state"]].append(r)
    report["trailing_by_state"] = {s: tally(g) for s, g in sorted(by_state.items())}

    (args.out_dir / "rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (args.out_dir / "report.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
