# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""What Word does with a page break (`w:br w:type="page"`) inside a header
or footer paragraph, where no page can break.

4910ce2060 (Letter, top margin 1440, header 288): the default header's
second paragraph opens with a page break in a 9.5pt run, then a bold 14pt
title. Word's PDF puts that title 27.1pt under the header's first line,
ours 16.1: a 14pt Arial line (16.1) plus 11.0, which is a 9.5pt Arial line
(10.9). The body under it starts 3.3pt lower in Word's PDF too.

Each probe is a two-paragraph header (a bold 14pt title, then the probed
paragraph) over a 12pt body; the top margin is 36pt and the header 18pt,
so the header's height sets the body top and every extra line shows twice:
in the header's second paragraph and in the body's first line.

Usage: uv run python scripts/probe_header_br.py OUTDIR            (build)
       uv run python scripts/probe_header_br.py --measure OUTDIR  (read the PDFs)
"""
import json, os, sys, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

ARIAL = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>'
BOLD14 = f'<w:rPr>{ARIAL}<w:b/><w:sz w:val="28"/></w:rPr>'

def run(text, rpr=BOLD14):
    return f'<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>'

def br(sz, kind="page"):
    t = f' w:type="{kind}"' if kind else ""
    return f'<w:r><w:rPr>{ARIAL}<w:sz w:val="{sz}"/></w:rPr><w:br{t}/></w:r>'

def para(runs, ppr='<w:jc w:val="center"/>', mark_rpr=f'{ARIAL}<w:sz w:val="28"/>'):
    return f'<w:p><w:pPr>{ppr}<w:rPr>{mark_rpr}</w:rPr></w:pPr>{runs}</w:p>'

TITLE = para(run("Title"))
BODY = "".join(para(run(f"Body{i}", f'<w:rPr>{ARIAL}<w:sz w:val="24"/></w:rPr>'), '<w:spacing w:after="0"/>') for i in range(1, 4))

def parts(second, top=720, where="header"):
    hdr_paras = TITLE + (second if where == "header" else "")
    ftr_paras = TITLE + (second if where == "footer" else "")
    refs = '<w:headerReference w:type="default" r:id="rIdHdr"/><w:footerReference w:type="default" r:id="rIdFtr"/>'
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{BODY}'
           f'<w:sectPr>{refs}<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="{top}" w:right="1440" w:bottom="1440" w:left="1440" '
           f'w:header="360" w:footer="360" w:gutter="0"/></w:sectPr></w:body></w:document>')
    hdr = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{W}" xmlns:r="{R}">{hdr_paras}</w:hdr>'
    ftr = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="{W}" xmlns:r="{R}">{ftr_paras}</w:ftr>'
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
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
          '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
             '<Relationship Id="rIdHdr" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
             '<Relationship Id="rIdFtr" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>')
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/document.xml": doc, "word/_rels/document.xml.rels": drels,
            "word/styles.xml": styles, "word/settings.xml": settings, "word/header1.xml": hdr, "word/footer1.xml": ftr}

KEY = run("Location Code Key")
PROBES = {
    "hb0_nobr": dict(second=para(KEY)),
    "hb1_page19": dict(second=para(br(19) + KEY)),
    "hb2_page40": dict(second=para(br(40) + KEY)),
    "hb3_page19_mark19": dict(second=para(br(19) + KEY, mark_rpr=f'{ARIAL}<w:sz w:val="19"/>')),
    "hb4_textwrap19": dict(second=para(br(19, None) + KEY)),
    "hb5_page19_mid": dict(second=para(run("Location") + br(19) + run("Code Key"))),
    "hb6_column19": dict(second=para(br(19, "column") + KEY)),
    "hb7_page19_fits": dict(second=para(br(19) + KEY), top=1440),
    "hb8_page19_only": dict(second=para(br(19))),
    "fb1_page19": dict(second=para(br(19) + KEY), where="footer"),
    "fb0_nobr": dict(second=para(KEY), where="footer"),
}

def measure(out):
    import fitz
    for fid in PROBES:
        p = os.path.join(out, "pdf", fid + ".pdf")
        if not os.path.exists(p):
            print(fid, "NO PDF"); continue
        doc = fitz.open(p)
        print(f"{fid}: {len(doc)} page(s)")
        for bl in doc[0].get_text("dict")["blocks"]:
            for l in bl.get("lines", []):
                text = "".join(sp["text"] for sp in l["spans"]).strip()
                if text:
                    sp = l["spans"][0]
                    print(f"   top {l['bbox'][1]:6.1f} base {sp['origin'][1]:6.1f} size {sp['size']:4.1f} x {l['bbox'][0]:6.1f} {text!r}")

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
