# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Where Word starts the body under a header taller than the top margin,
and where a line's multiple-spacing extra goes.

75252a6bb0 (A4, margins 720, header 708, Normal = Arial 11 after 120 at
line 276): a first-page header of a 75pt picture paragraph, an empty bold
paragraph and an empty Header-style paragraph; Word's title baseline is
6.7pt under ours. These documents isolate the terms: the header's
paragraph heights, its trailing space after, the body's first space
before, the position of the 1.15 extra inside a line, and a picture
line's descent.

Usage: uv run python scripts/probe_header_push.py OUTDIR
"""
import base64, json, os, sys, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
# 1×1 red PNG
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
)

def para(text, ppr="", rpr=""):
    run = f'<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>' if text else ""
    return f"<w:p><w:pPr>{ppr}</w:pPr>{run}</w:p>"

def picture(cy_pt, ppr=""):
    emu = int(cy_pt * 12700)
    return (f'<w:p><w:pPr>{ppr}</w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0" '
            f'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing">'
            f'<wp:extent cx="{emu}" cy="{emu}"/><wp:docPr id="1" name="Picture 1"/>'
            f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:nvPicPr><pic:cNvPr id="0" name="p.png"/><pic:cNvPicPr/></pic:nvPicPr>'
            f'<pic:blipFill><a:blip r:embed="rIdPic"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{emu}" cy="{emu}"/></a:xfrm>'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
            f'</wp:inline></w:drawing></w:r></w:p>')

TITLE_RPR = '<w:rPr><w:b/><w:sz w:val="44"/></w:rPr>'
BODY_TAIL = "".join(para(f"L{i:04d}", '<w:spacing w:after="0" w:line="10" w:lineRule="exact"/>') for i in range(1, 30))

def parts(header_paras, body_first_ppr='<w:spacing w:before="240" w:after="240"/>', body_first=None, header_pic=False,
          docgrid="", title_pg=False, a4=False):
    body_first = body_first or para("Title", body_first_ppr, TITLE_RPR)
    hdr_ref = '<w:headerReference w:type="first" r:id="rIdHdr"/>' if title_pg else '<w:headerReference w:type="default" r:id="rIdHdr"/>'
    pg = ('<w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720" w:header="708" w:footer="708" w:gutter="0"/>'
          if a4 else '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720" w:header="360" w:footer="360" w:gutter="0"/>')
    title = "<w:titlePg/>" if title_pg else ""
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>'
           f'{body_first}{BODY_TAIL}'
           f'<w:sectPr>{hdr_ref}{pg}{title}{docgrid}</w:sectPr></w:body></w:document>')
    hdr = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{W}" xmlns:r="{R}">{header_paras}</w:hdr>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
              f'<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
              f'<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
              f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
              f'<w:style w:type="paragraph" w:styleId="Header"><w:name w:val="header"/><w:basedOn w:val="Normal"/>'
              f'<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:style></w:styles>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}">'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Default Extension="png" ContentType="image/png"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
             '<Relationship Id="rIdHdr" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>'
             '<Relationship Id="rIdPic" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/p.png"/></Relationships>')
    hrels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rIdPic" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/p.png"/></Relationships>')
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/document.xml": doc, "word/_rels/document.xml.rels": drels,
            "word/styles.xml": styles, "word/settings.xml": settings, "word/header1.xml": hdr,
            "word/_rels/header1.xml.rels": hrels, "word/media/p.png": PNG}

EXACT30 = '<w:spacing w:after="0" w:line="600" w:lineRule="exact"/>'
PROBES = {
    # a header that fits the margin: does the body's first space before count at the page top?
    "h0_short_header_before_240": dict(header_paras=para("Hdr", '<w:pStyle w:val="Header"/>')),
    "h1_short_header_before_0": dict(header_paras=para("Hdr", '<w:pStyle w:val="Header"/>'), body_first_ppr='<w:spacing w:before="0" w:after="240"/>'),
    # a tall header of exact paragraphs: body top vs header bottom, with and without a trailing after
    "h2_tall_exact_after_0": dict(header_paras=para("H1", EXACT30) + para("H2", EXACT30) + para("H3", EXACT30)),
    "h3_tall_exact_after_400": dict(header_paras=para("H1", EXACT30) + para("H2", EXACT30) + para("H3", '<w:spacing w:after="400" w:line="600" w:lineRule="exact"/>')),
    "h4_tall_exact_before_0": dict(header_paras=para("H1", EXACT30) + para("H2", EXACT30) + para("H3", EXACT30), body_first_ppr='<w:spacing w:before="0" w:after="240"/>'),
    # the document's own shape: picture paragraph, empty bold paragraph, empty Header paragraph
    "h5_doc_shape": dict(header_paras=picture(75.1, '<w:spacing w:before="120"/>') + para("", "", "") + para("", '<w:pStyle w:val="Header"/>')),
    # the 1.15 extra: a double-spaced line before a single one; a 50pt picture line at 1.15 before a text line
    "h6_double_then_single": dict(header_paras=para("Hdr", '<w:pStyle w:val="Header"/>'), body_first_ppr="",
                                   body_first=para("Alpha", '<w:spacing w:after="0" w:line="480" w:lineRule="auto"/>') + para("Beta", '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>')),
    "h7_picture_then_text": dict(header_paras=para("Hdr", '<w:pStyle w:val="Header"/>'), body_first_ppr="",
                                  body_first=picture(50.0, '<w:spacing w:after="0"/>') + para("Beta", '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>')),
    "h8_picture_115_then_text": dict(header_paras=para("Hdr", '<w:pStyle w:val="Header"/>'), body_first_ppr="",
                                      body_first=picture(50.0, '<w:spacing w:after="0" w:line="276" w:lineRule="auto"/>') + para("Beta", '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>')),
    # round 2: what 75252a6bb0 has that h5 lacks (its title sits 15.0 under the last header mark, h5's 35.0)
    "h9_doc_shape_docgrid": dict(header_paras=picture(75.1, '<w:spacing w:before="120"/>') + para("", "", "") + para("", '<w:pStyle w:val="Header"/>'),
                                 docgrid='<w:docGrid w:linePitch="360"/>'),
    "h10_doc_shape_titlepg": dict(header_paras=picture(75.1, '<w:spacing w:before="120"/>') + para("", "", "") + para("", '<w:pStyle w:val="Header"/>'),
                                  title_pg=True),
    "h11_doc_shape_contextual": dict(header_paras=picture(75.1, '<w:spacing w:before="120"/>') + para("", "", "") + para("", '<w:pStyle w:val="Header"/>'),
                                     body_first_ppr='<w:spacing w:before="240" w:after="240"/><w:contextualSpacing/><w:outlineLvl w:val="0"/>'),
    "h12_doc_shape_a4": dict(header_paras=picture(75.1, '<w:spacing w:before="120"/>') + para("", "", "") + para("", '<w:pStyle w:val="Header"/>'),
                             a4=True),
    "h13_doc_shape_all": dict(header_paras=picture(75.1, '<w:spacing w:before="120"/>') + para("", "", "") + para("", '<w:pStyle w:val="Header"/>'),
                              body_first_ppr='<w:spacing w:before="240" w:after="240"/><w:contextualSpacing/><w:outlineLvl w:val="0"/>',
                              docgrid='<w:docGrid w:linePitch="360"/>', title_pg=True, a4=True),
    # the last header paragraph is empty: does an empty trailing paragraph count? (h2 with an empty exact paragraph appended)
    "h14_tall_exact_plus_empty": dict(header_paras=para("H1", EXACT30) + para("H2", EXACT30) + para("H3", EXACT30) + para("", '<w:pStyle w:val="Header"/>')),
}

def main():
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
