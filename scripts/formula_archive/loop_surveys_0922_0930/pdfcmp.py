# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Compare Word's PDF with jubarte's, mechanically: what a low score hides.

    pdfcmp.py WORD.pdf OURS.pdf
    pdfcmp.py --key KEY --run w4        # _word_pdf/KEY.pdf vs runs/tip_w4/pdf/KEY.pdf

Prints, for both PDFs side by side:
- page counts;
- embedded fonts (subset prefix dropped): only in Word, only in ours;
- per page: text colours (by characters), fill colours (by area, pt²;
  table/cell shading, highlight and paragraph fills show up here), the
  first and last text line (y from the page top), and the text in the top
  and bottom bands (headers, footers, page numbers, footnotes).
Only differences are printed per page unless -v.

Pair it with `jubarte debug DOCX --check render`, which lists what the docx
asks for (tables, shading, highlight, colours, fonts and substitutes,
fields, ins/del order) across every story part.
"""
import pathlib
import re
import sys
from collections import Counter

import fitz

D = pathlib.Path("/Users/arthrod/temp/T/jubarte-redlines/_to_improve_docx_to_pdf")
L = pathlib.Path("/Users/arthrod/temp/T/jubarte-loop")
BAND = 0.12  # top/bottom share of the page read as header/footer bands


def hexcolor(c):
    if c is None:
        return None
    if isinstance(c, int):
        return f"{c:06X}"
    if len(c) == 1:
        c = (c[0], c[0], c[0])
    if len(c) == 4:  # CMYK
        k = c[3]
        c = tuple((1 - x) * (1 - k) for x in c[:3])
    return "".join(f"{round(x * 255):02X}" for x in c[:3])


def fonts(doc):
    out = set()
    for i in range(len(doc)):
        for f in doc.get_page_fonts(i):
            out.add(re.sub(r"^[A-Z]{6}\+", "", f[3]))
    return out


def page_facts(page):
    h = page.rect.height
    text, lines, top, bottom = Counter(), [], [], []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            s = "".join(sp["text"] for sp in line["spans"]).strip()
            if not s:
                continue
            y = line["bbox"][1]
            lines.append((round(y, 1), s))
            for sp in line["spans"]:
                text[hexcolor(sp["color"])] += len(sp["text"].strip())
            if y < h * BAND:
                top.append(s)
            elif y > h * (1 - BAND):
                bottom.append(s)
    fills = Counter()
    for d in page.get_drawings():
        if d.get("fill") is not None and d["type"] in ("f", "fs"):
            r = d["rect"]
            fills[hexcolor(d["fill"])] += round(r.width * r.height)
    fills.pop("FFFFFF", None)
    lines.sort()
    return {
        "text": text,
        "fills": fills,
        "first": lines[0] if lines else None,
        "last": lines[-1] if lines else None,
        "top": " / ".join(top)[:120],
        "bottom": " / ".join(bottom)[:120],
    }


def top_items(c, n=6):
    return ", ".join(f"{k}:{v}" for k, v in c.most_common(n)) or "-"


def main(args):
    verbose = "-v" in args
    args = [a for a in args if a != "-v"]
    if "--key" in args:
        k = args[args.index("--key") + 1]
        run = args[args.index("--run") + 1] if "--run" in args else None
        word = D / "_word_pdf" / f"{k}.pdf"
        ours = L / "runs" / f"tip_{run}" / "pdf" / f"{k}.pdf" if run else D / "_jubarte_pdf" / f"{k}.pdf"
    else:
        word, ours = map(pathlib.Path, args[:2])
    w, j = fitz.open(word), fitz.open(ours)
    print(f"pages   word {len(w)}  ours {len(j)}{'' if len(w) == len(j) else '  <-- differ'}")
    fw, fj = fonts(w), fonts(j)
    print(f"fonts   common: {', '.join(sorted(fw & fj)) or '-'}")
    if fw - fj:
        print(f"        only word: {', '.join(sorted(fw - fj))}")
    if fj - fw:
        print(f"        only ours: {', '.join(sorted(fj - fw))}")
    for i in range(max(len(w), len(j))):
        a = page_facts(w[i]) if i < len(w) else None
        b = page_facts(j[i]) if i < len(j) else None
        rows = []
        for label in ("text", "fills"):
            ka = set(a[label]) if a else set()
            kb = set(b[label]) if b else set()
            if verbose or ka != kb:
                rows.append(f"  {label:6} word {top_items(a[label]) if a else '(no page)'}")
                rows.append(f"  {'':6} ours {top_items(b[label]) if b else '(no page)'}")
        for label in ("first", "last", "top", "bottom"):
            va, vb = (a or {}).get(label), (b or {}).get(label)
            same = va == vb
            if label in ("first", "last") and va and vb:
                same = abs(va[0] - vb[0]) < 2 and va[1][:30] == vb[1][:30]
            if verbose or not same:
                rows.append(f"  {label:6} word {va!s:.110}")
                rows.append(f"  {'':6} ours {vb!s:.110}")
        if rows:
            print(f"page {i + 1}")
            print("\n".join(rows))


if __name__ == "__main__":
    main(sys.argv[1:])
