# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Truth table: which document features separate the corpus docs Word draws comment balloons for."""
import re, zipfile, json, sys
from pathlib import Path
import fitz
C = Path("corpus/word")
FEATS = {
    "altcontent_any": lambda b: "mc:AlternateContent" in b,
    "altcontent_body": lambda b: bool(re.search(r"<w:body>.*?(?:</w:p>|<w:body>)\s*<mc:AlternateContent", b, re.S)) or bool(re.search(r"</w:(?:p|tbl)>\s*<mc:AlternateContent", b)),
    "altcontent_run": lambda b: bool(re.search(r"<w:p\b[^>]*>(?:(?!</w:p>).)*<mc:AlternateContent(?:(?!</w:p>).)*</w:p>", b, re.S)),
    "customXml": lambda b: "<w:customXml" in b,
    "sdt": lambda b: "<w:sdt>" in b or "<w:sdt " in b,
    "fldSimple": lambda b: "<w:fldSimple" in b,
    "moveFrom": lambda b: "<w:moveFrom" in b,
    "txbx": lambda b: "txbxContent" in b,
    "math": lambda b: "<m:oMath" in b,
    "tracked": lambda b: "<w:ins " in b or "<w:del " in b,
    "pPrChange": lambda b: "<w:pPrChange" in b,
    "tblGrid_change": lambda b: "tblGridChange" in b,
    "sectPr_mid": lambda b: b.count("<w:sectPr") > 1,
    "rangeEnd_after_tbl": lambda b: bool(re.search(r"</w:tbl>\s*<w:commentRange", b)),
}
rows = []
for st in ("with_comments_tracking", "with_comments_clean"):
    for d in sorted((C / st / "docx").glob("*.docx")):
        if "__vs__" in d.name: continue
        pdf = C / st / "pdf" / (d.stem + ".pdf")
        if not pdf.is_file(): continue
        try:
            z = zipfile.ZipFile(d); n = z.namelist()
            if "word/comments.xml" not in n: continue
            cx, b = z.read("word/comments.xml").decode("utf8", "replace"), z.read("word/document.xml").decode("utf8", "replace")
        except Exception: continue
        if not re.search(r"<w:comment\b", cx): continue
        t = "".join(pg.get_text() for pg in fitz.open(pdf))
        rows.append({"doc": f"{st}/{d.stem}", "balloons": len(re.findall(r"Commented \[", t)), **{k: f(b) for k, f in FEATS.items()}})
zero = [r for r in rows if not r["balloons"]]; some = [r for r in rows if r["balloons"]]
print(f"{'feature':20s} zero(n={len(zero)}) some(n={len(some)})")
for k in FEATS: print(f"{k:20s} {sum(r[k] for r in zero):10d} {sum(r[k] for r in some):10d}")
Path(sys.argv[1] if len(sys.argv) > 1 else "/dev/null").write_text(json.dumps(rows, indent=1))
