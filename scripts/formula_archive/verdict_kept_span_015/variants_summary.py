#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Per-probe summary of the variants wave: Word's verdict on the target paragraph,
mark (pPr/rPr) revisions, the law's prediction, and the page the target lands on."""
import csv, re, subprocess, sys, zipfile
from pathlib import Path
sys.path.insert(0, "/Users/arthrod/T/neurotic_docx_bench/scripts")
import redline_anatomy as ra
import probe_variants as pv

P = Path(sys.argv[1])
VA = set(pv.VA)
rows = []
for m in csv.DictReader((P / "manifest.csv").open()):
    n = m["name"]
    a, b, r = P / "A" / f"{n}.docx", P / "B" / f"{n}.docx", P / "word" / f"{n}__vs__{n}.docx"
    pa, pb, pr = ra.paragraphs(a), ra.paragraphs(b), ra.paragraphs(r)
    # target = the A paragraph drawn from vocabulary A
    ti = next(i for i, p in enumerate(pa) if (ws := ra.words(ra.text_of(p, "orig") if hasattr(ra, "text_of") else p.text)) and sum(w.lower().strip('",.') in VA for w in ws) / len(ws) > 0.5)
    vs = [v for v in ra.verdicts(pr) if v.verdict != "unchanged"]
    tv = [v for v in vs if v.a_index == ti or (v.a_index is None and v.b_index == ti)]
    xml = zipfile.ZipFile(r).read("word/document.xml").decode()
    marks = f"pPr={xml.count('<w:pPrChange')} rPr={xml.count('<w:rPrChange')}"
    verdict = "/".join(sorted({v.verdict for v in tv})) or "unchanged"
    ins = sum(v.ins for v in tv); dele = sum(v.dele for v in tv); isl = sum(v.islands for v in tv)
    pred = ra.predict_pair(pa[ti].text, pb[ti].text) if hasattr(pa[ti], "text") else {}
    # page of the target paragraph in Word's PDF
    page = "-"
    pdf = r.with_suffix(".pdf")
    if pdf.exists():
        txt = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
        pages = txt.split("\f")
        first = ra.words(pa[ti].text)[:3]
        pat = re.compile(r"\s+".join(re.escape(w) for w in first), re.I)
        page = ",".join(str(i + 1) for i, pg in enumerate(pages) if pat.search(pg)) or "?"
        npages = len([p for p in pages if p.strip()])
        page = f"{page}/{npages}"
    rows.append((m["group"], n, verdict, ins, dele, isl, marks, pred.get("kept_frac"), pred.get("floor"), pred.get("predicted"), page, m["note"]))

cur = None
for g, n, v, i, d, isl, marks, kf, fl, pr, page, note in rows:
    if g != cur:
        print(f"\n## {g}\n{'probe':30} {'word verdict':12} {'ins':>4}{'del':>4}{'isl':>4}  {'marks':14} {'kept':>6} {'floor':>6} {'law':10} {'page':7} note")
        cur = g
    kf = f"{kf:.3f}" if kf is not None else "-"; fl = f"{fl:.3f}" if fl is not None else "-"
    print(f"{n:30} {v:12} {i:4}{d:4}{isl:4}  {marks:14} {kf:>6} {fl:>6} {str(pr):10} {page:7} {note}")
