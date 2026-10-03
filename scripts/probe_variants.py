#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Does Word's whole-vs-word verdict (or its alignment) depend on anything
besides the text? Probe pairs for: pagination (a paragraph that is one or
two lines on page 2 after a full page, and one that straddles the page
break), capitalization and punctuation (alone, and inside the kept runs),
indentation, and paragraph/run styles. Every variant has a control with
the same words and no variant.

    probe_variants.py OUT

Writes OUT/A, OUT/B and OUT/manifest.csv. Minimal Word-valid packages with
a styles part (Normal, Heading1, Quote), no personal data, deterministic.
"""

from __future__ import annotations

import csv
import random
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import long_paragraph_probes as lp  # noqa: E402

lp.PUNCT = False
VA = lp.pseudo_vocab(101, 300, None)
VB = [w for w in lp.pseudo_vocab(202, 400, None) if w not in set(VA)][:300]
VF = [w for w in lp.pseudo_vocab(303, 400, None) if w not in set(VA) | set(VB)][:300]  # filler vocabulary


def para(text: str, ind: int = 0, style: str | None = None, bold: bool = False, font: str | None = None, size: int | None = None, bold_spans: list[tuple[int, int]] | None = None, page_break_before: bool = False) -> str:
    ppr = ""
    if style or ind or page_break_before:
        ppr = "<w:pPr>" + (f'<w:pStyle w:val="{style}"/>' if style else "") + ("<w:pageBreakBefore/>" if page_break_before else "") + (f'<w:ind w:left="{ind}"/>' if ind else "") + "</w:pPr>"
    rpr_bits = ("<w:b/>" if bold else "") + (f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}"/>' if font else "") + (f'<w:sz w:val="{size}"/>' if size else "")
    rpr = f"<w:rPr>{rpr_bits}</w:rPr>" if rpr_bits else ""
    if bold_spans:
        # split text into runs at character spans that get bold
        runs, pos = [], 0
        for s, e in bold_spans:
            if s > pos:
                runs.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text[pos:s])}</w:t></w:r>')
            runs.append(f'<w:r><w:rPr><w:b/>{rpr_bits}</w:rPr><w:t xml:space="preserve">{escape(text[s:e])}</w:t></w:r>')
            pos = e
        if pos < len(text):
            runs.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text[pos:])}</w:t></w:r>')
        return f"<w:p>{ppr}{''.join(runs)}</w:p>"
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:sz w:val="22"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="160" w:line="259" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
    '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
    '<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="0"/><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>'
    '<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:qFormat/>'
    '<w:pPr><w:ind w:left="720" w:right="720"/></w:pPr><w:rPr><w:i/></w:rPr></w:style>'
    "</w:styles>"
)


def docx(path: Path, paras: list[str]) -> None:
    body = "".join(paras)
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f'<w:body>{body}<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
        "</w:sectPr></w:body></w:document>"
    )
    types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        "</Relationships>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/document.xml", document)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr("word/styles.xml", STYLES)


def pair(n: int, keep: float, run: int, seed: int) -> tuple[list[str], list[str], list[tuple[int, int]]]:
    """A words, B words, and the kept runs as (start_in_b, length)."""
    rng = random.Random(seed)
    a = lp.prose(VA, n, rng)
    b, kept_words, runs = lp.revise(a, keep, run, rng)
    # locate kept runs in b by scanning for A's words (vocabularies are disjoint)
    spans, i = [], 0
    while i < len(b):
        if b[i] in set(VA):
            j = i
            while j < len(b) and b[j] in set(VA):
                j += 1
            spans.append((i, j - i))
            i = j
        else:
            i += 1
    return a, b, spans


def char_spans(words: list[str], spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Word spans → character spans in ' '.join(words)."""
    starts, pos = [], 0
    for w in words:
        starts.append(pos)
        pos += len(w) + 1
    return [(starts[s], starts[s + n - 1] + len(words[s + n - 1])) for s, n in spans]


def filler(n: int, seed: int, paras: int = 4) -> list[str]:
    rng = random.Random(seed)
    per = n // paras
    return [" ".join(lp.prose(VF, per, rng)) for _ in range(paras)]


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "probes/variants")
    rows = []

    def emit(name: str, A: list[str], B: list[str], group: str, note: str) -> None:
        docx(out / "A" / f"{name}.docx", A)
        docx(out / "B" / f"{name}.docx", B)
        rows.append({"name": name, "group": group, "note": note})

    labels = [para("Section one"), para("Clause")]
    tail = [para("End of section")]

    # ── 1. pagination ──────────────────────────────────────────────────────
    # a short paragraph (≈2 lines) that lands on page 2 after a full page of unchanged filler
    for keep, run in ((0.25, 2), (0.40, 2), (0.20, 4), (0.50, 4)):
        a, b, _ = pair(24, keep, run, 11)
        tag = f"k{int(keep * 100)}_r{run}"
        emit(f"ctl_short2l_{tag}", labels + [para(" ".join(a))] + tail, labels + [para(" ".join(b))] + tail, "pagination", "24-word paragraph, page 1 (control)")
        for fw in (470, 520):
            f = filler(fw, 5)
            emit(f"pg{fw}_short2l_{tag}", [para(t) for t in f] + [para(" ".join(a))] + tail, [para(t) for t in f] + [para(" ".join(b))] + tail, "pagination", f"24-word paragraph after {fw} filler words (1–2 lines on page 2)")
        f = filler(300, 5)
        emit(f"pgbreak_short2l_{tag}", [para(t) for t in f] + [para(" ".join(a), page_break_before=True)] + tail, [para(t) for t in f] + [para(" ".join(b), page_break_before=True)] + tail, "pagination", "24-word paragraph with pageBreakBefore")
    # a 400-word paragraph at the boundary, straddling the page break
    for keep in (0.16, 0.18, 0.20):
        a, b, _ = pair(400, keep, 4, 12)
        tag = f"k{int(keep * 100)}_r4"
        emit(f"ctl_long_{tag}", labels + [para(" ".join(a))] + tail, labels + [para(" ".join(b))] + tail, "pagination", "400-word paragraph, page 1 (control)")
        for fw in (380, 450):
            f = filler(fw, 6)
            emit(f"pg{fw}_long_{tag}", [para(t) for t in f] + [para(" ".join(a))] + tail, [para(t) for t in f] + [para(" ".join(b))] + tail, "pagination", f"400-word paragraph after {fw} filler words (straddles the break)")

    # ── 2. capitalization and punctuation ───────────────────────────────────
    for keep in (0.20, 0.30):
        a, b, spans = pair(400, keep, 4, 21)
        tag = f"k{int(keep * 100)}_r4"
        A = labels + [para(" ".join(a))] + tail
        emit(f"ctl_caps_{tag}", A, labels + [para(" ".join(b))] + tail, "caps-punct", "control")
        bt = list(b)
        for s, n in spans:
            for k in range(s, s + n):
                bt[k] = bt[k].capitalize()
        emit(f"caps_kept_title_{tag}", A, labels + [para(" ".join(bt))] + tail, "caps-punct", "every kept word Title-cased in B")
        bu = list(b)
        for s, n in spans:
            for k in range(s, s + n):
                bu[k] = bu[k].upper()
        emit(f"caps_kept_upper_{tag}", A, labels + [para(" ".join(bu))] + tail, "caps-punct", "every kept word UPPER in B")
        bp = list(b)
        for s, n in spans:
            bp[s + n - 1] = bp[s + n - 1] + ","
        emit(f"punct_kept_comma_{tag}", A, labels + [para(" ".join(bp))] + tail, "caps-punct", "a comma after the last word of every kept run in B")
        bq = list(b)
        for s, n in spans:
            bq[s] = '"' + bq[s]
            bq[s + n - 1] = bq[s + n - 1] + '"'
        emit(f"punct_kept_quotes_{tag}", A, labels + [para(" ".join(bq))] + tail, "caps-punct", "every kept run quoted in B")
    # case-only and punctuation-only differences on otherwise identical text
    rng = random.Random(31)
    a = lp.prose(VA, 400, rng)
    for frac in (0.05, 0.20, 0.50):
        bc = [w.capitalize() if rng.random() < frac else w for w in a]
        emit(f"caps_only_{int(frac * 100)}", labels + [para(" ".join(a))] + tail, labels + [para(" ".join(bc))] + tail, "caps-punct", f"identical words, {int(frac * 100)}% capitalized in B")
    for every in (7, 3):
        bp = [w + "," if (i + 1) % every == 0 else w for i, w in enumerate(a)]
        emit(f"punct_only_every{every}", labels + [para(" ".join(a))] + tail, labels + [para(" ".join(bp))] + tail, "caps-punct", f"identical words, a comma after every {every}th word in B")
    bs = " ".join(a)
    bs2 = ". ".join(x.capitalize() for x in [bs[i:i + 90] for i in range(0, len(bs), 90)])
    emit("sentences_added", labels + [para(bs)] + tail, labels + [para(bs2)] + tail, "caps-punct", "identical words, sentence periods and capitals inserted every ~90 chars in B")

    # ── 3. indentation ──────────────────────────────────────────────────────
    for keep in (0.0, 0.16, 0.18, 0.20, 0.30):
        a, b, _ = pair(400, keep, 4, 41) if keep else (lp.prose(VA, 400, random.Random(41)),) * 2 + ([],)
        tag = "same" if not keep else f"k{int(keep * 100)}_r4"
        A = labels + [para(" ".join(a))] + tail
        if keep:
            emit(f"ctl_ind_{tag}", A, labels + [para(" ".join(b))] + tail, "indentation", "control")
        emit(f"ind720_{tag}", A, labels + [para(" ".join(b), ind=720)] + tail, "indentation", "B paragraph indented 0.5in")
        emit(f"ind1440_{tag}", A, labels + [para(" ".join(b), ind=1440)] + tail, "indentation", "B paragraph indented 1in")
        emit(f"indboth_{tag}", labels + [para(" ".join(a), ind=720)] + tail, labels + [para(" ".join(b), ind=1440)] + tail, "indentation", "A 0.5in, B 1in")

    # ── 4. styles ───────────────────────────────────────────────────────────
    for keep in (0.0, 0.16, 0.18, 0.20, 0.30):
        if keep:
            a, b, spans = pair(400, keep, 4, 51)
        else:
            a = lp.prose(VA, 400, random.Random(51)); b = list(a)
            spans = [(i, 4) for i in range(0, 400, 20)]
        tag = "same" if not keep else f"k{int(keep * 100)}_r4"
        A = labels + [para(" ".join(a))] + tail
        if keep:
            emit(f"ctl_style_{tag}", A, labels + [para(" ".join(b))] + tail, "styles", "control")
        emit(f"style_heading1_{tag}", A, labels + [para(" ".join(b), style="Heading1")] + tail, "styles", "B paragraph styled Heading 1")
        emit(f"style_quote_{tag}", A, labels + [para(" ".join(b), style="Quote")] + tail, "styles", "B paragraph styled Quote (indent + italic)")
        emit(f"bold_all_{tag}", A, labels + [para(" ".join(b), bold=True)] + tail, "styles", "whole B paragraph bold (direct)")
        emit(f"bold_kept_{tag}", A, labels + [para(" ".join(b), bold_spans=char_spans(b, spans))] + tail, "styles", "only the kept runs bold in B")
        emit(f"font_{tag}", A, labels + [para(" ".join(b), font="Georgia", size=28)] + tail, "styles", "B paragraph Georgia 14pt (direct)")

    with (out / "manifest.csv").open("w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=["name", "group", "note"])
        wr.writeheader()
        wr.writerows(rows)
    print(f"{len(rows)} probe pairs under {out}")


if __name__ == "__main__":
    main()
