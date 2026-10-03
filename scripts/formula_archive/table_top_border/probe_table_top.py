# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Where Word puts a table's first text under the paragraph above it, by
the first row's top border and the cells' space before.

4910ce2060 (Letter, Arial 12): "Compliance Period" line, an empty
paragraph, then a fixed table whose first row has a double sz=6 top
border and cells with before=90 after=54. Word's "LEAD SAMPLES" sits
34.3pt under the line above, ours 32.8; every row after keeps the 1.5.

Each probe: "Alpha" (Arial 12, after 0), an empty Arial 12 paragraph,
then a one-row table (cell margins left/right 120) whose cell holds
"LEAD" under the probed border and spacing.

Usage: uv run python scripts/probe_table_top.py OUTDIR            (build)
       uv run python scripts/probe_table_top.py --measure DIR     (read DIR/pdf)
"""
import json, os, sys, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ARIAL = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="24"/>'

def para(text, ppr='<w:spacing w:after="0"/>'):
    run = f'<w:r><w:rPr>{ARIAL}</w:rPr><w:t>{text}</w:t></w:r>' if text else ""
    return f'<w:p><w:pPr>{ppr}<w:rPr>{ARIAL}</w:rPr></w:pPr>{run}</w:p>'

def table(top_border, before, after, bottom_border="", second_row=False, empty_para=True):
    tcb = ""
    if top_border or bottom_border:
        tcb = f"<w:tcBorders>{top_border}{bottom_border}</w:tcBorders>"
    sp = f'<w:spacing w:before="{before}" w:after="{after}"/>'
    cell = (f'<w:tc><w:tcPr><w:tcW w:w="5040" w:type="dxa"/>{tcb}</w:tcPr>'
            f'{para("LEAD", sp)}</w:tc>')
    rows = f"<w:tr>{cell}</w:tr>"
    if second_row:
        rows += f'<w:tr>{cell.replace("LEAD", "NEXT")}</w:tr>'
    return (f'<w:tbl><w:tblPr><w:tblW w:w="5040" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
            f'<w:tblCellMar><w:left w:w="120" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="5040"/></w:tblGrid>{rows}</w:tbl>')

def parts(top_border="", before=0, after=0, bottom_border="", second_row=False, empty_para=True):
    body = para("Alpha") + (para("") if empty_para else "") + table(top_border, before, after, bottom_border, second_row) + para("Omega")
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{body}'
           f'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="864" w:bottom="720" w:left="720" '
           f'w:header="288" w:footer="288" w:gutter="0"/></w:sectPr></w:body></w:document>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
              f'<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
              f'<w:pPrDefault><w:pPr/></w:pPrDefault></w:docDefaults>'
              f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style></w:styles>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}">'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>')
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/document.xml": doc, "word/_rels/document.xml.rels": drels,
            "word/styles.xml": styles, "word/settings.xml": settings}

DOUBLE = '<w:top w:val="double" w:sz="6" w:space="0" w:color="auto"/>'
SINGLE = '<w:top w:val="single" w:sz="6" w:space="0" w:color="auto"/>'
THICK = '<w:top w:val="single" w:sz="24" w:space="0" w:color="auto"/>'
PROBES = {
    "tt0_none": dict(),
    "tt1_single6": dict(top_border=SINGLE),
    "tt2_double6": dict(top_border=DOUBLE),
    "tt3_thick24": dict(top_border=THICK),
    "tt4_double6_before90_after54": dict(top_border=DOUBLE, before=90, after=54),
    "tt5_none_before90_after54": dict(before=90, after=54),
    "tt6_double6_two_rows": dict(top_border=DOUBLE, before=90, after=54, second_row=True),
    "tt7_double6_no_empty_para": dict(top_border=DOUBLE, before=90, after=54, empty_para=False),
    "tt8_single6_bottom_single6": dict(top_border=SINGLE, bottom_border='<w:bottom w:val="single" w:sz="6" w:space="0" w:color="auto"/>'),
}

def measure(d):
    import fitz
    for fid in PROBES:
        p = os.path.join(d, fid + ".pdf")
        if not os.path.exists(p):
            print(fid, "NO PDF"); continue
        tops = {}
        for bl in fitz.open(p)[0].get_text("dict")["blocks"]:
            for l in bl.get("lines", []):
                text = "".join(sp["text"] for sp in l["spans"]).strip()
                if text:
                    tops.setdefault(text, round(l["bbox"][1], 2))
        a = tops.get("Alpha", 0.0)
        print(f"{fid:32s}", " ".join(f"{k} {v - a:+6.2f}" for k, v in tops.items() if k != "Alpha"), f"(Alpha {a:.2f})")

def main():
    if sys.argv[1] == "--measure":
        measure(sys.argv[2]); return
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    for fid, spec in PROBES.items():
        with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in parts(**spec).items():
                z.writestr(name, data)
    json.dump(list(PROBES), open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(PROBES), "probes")

if __name__ == "__main__":
    main()
