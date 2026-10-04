# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Does a list paragraph's label (a Symbol bullet, a big number) raise its
first line, and does Word paint the label of a deleted list paragraph?

25f1d311bd (Cambria 8.5 at 1.15, Symbol bullets, every list paragraph
deleted by a tracked change): Word's first lines keep the wrapped lines'
pitch (11.2-11.4) and no bullet glyph reaches the PDF text; ours stand
0.4-0.6 taller per paragraph (the SymbolMT label's line) and page 7 ends
a block short by the tenth item.

Each probe: four two-line list paragraphs then "Omega"; the label font
and size, the text font, and the tracked deletion vary.

Usage: uv run python scripts/probe_list_label.py OUTDIR            (build)
       uv run python scripts/probe_list_label.py --measure DIR     (read DIR/pdf)
"""
import json, os, sys, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DEL = 'w:id="{id}" w:author="Redline" w:date="1970-01-01T00:00:00Z"'

TEXTS = [
    "Coauthor in real time from Word for the web or desktop with files stored in OneDrive or SharePoint for the team to share",
    "Use comments, replies, mentions, and explicit permissions to keep every reviewer accountable for the changes they ask for",
    "Keep one authoritative file rather than emailing attachments around the organisation and merging the replies by hand",
    "Track changes is more granular and formal than lightweight suggestion modes and supports accept and reject by reviewer",
]

def rfonts(font):
    return f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'

def para(text, num_id, font, sz, deleted, i, via_style=False):
    rpr = f'<w:rPr>{rfonts(font)}<w:sz w:val="{sz}"/></w:rPr>'
    numbering = ('<w:pStyle w:val="ListBullet"/>' if via_style
                 else f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/></w:numPr>')
    ppr = (f'<w:pPr>{numbering}'
           f'<w:spacing w:after="0" w:line="276" w:lineRule="auto"/>')
    if deleted:
        ppr += f'<w:rPr><w:del {DEL.format(id=1000 + i)}/>{rfonts(font)}<w:sz w:val="{sz}"/></w:rPr></w:pPr>'
        run = f'<w:del {DEL.format(id=2000 + i)}><w:r>{rpr}<w:delText xml:space="preserve">{text}</w:delText></w:r></w:del>'
    else:
        ppr += f'<w:rPr>{rfonts(font)}<w:sz w:val="{sz}"/></w:rPr></w:pPr>'
        run = f'<w:r>{rpr}<w:t xml:space="preserve">{text}</w:t></w:r>'
    return f"<w:p>{ppr}{run}</w:p>"

def lvl(fmt, text, font, sz, link=False):
    rpr = rfonts(font) + (f'<w:sz w:val="{sz}"/>' if sz else "")
    pstyle = '<w:pStyle w:val="ListBullet"/>' if link else ""
    return (f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/>{pstyle}<w:lvlText w:val="{text}"/><w:lvlJc w:val="left"/>'
            f'<w:pPr><w:tabs><w:tab w:val="num" w:pos="1440"/></w:tabs><w:ind w:left="1440" w:hanging="360"/></w:pPr>'
            f'<w:rPr>{rpr}</w:rPr></w:lvl>')

ABSTRACTS = {
    1: lvl("bullet", "", "Symbol", None),      # the document's bullet
    2: lvl("bullet", "", "Symbol", 40),        # a 20pt bullet
    3: lvl("decimal", "%1.", "Calibri", 40),         # a 20pt number in another face
    4: lvl("decimal", "%1.", "Cambria", None),       # a number in the text's face
    5: lvl("bullet", "", "Wingdings", None),   # a Wingdings square
}

def parts(num_id=1, font="Cambria", sz=17, deleted=False, via_style=False):
    body = "".join(para(t, num_id, font, sz, deleted, i, via_style) for i, t in enumerate(TEXTS))
    body += f'<w:p><w:pPr><w:spacing w:after="0" w:line="276" w:lineRule="auto"/></w:pPr><w:r><w:rPr>{rfonts(font)}<w:sz w:val="{sz}"/></w:rPr><w:t>Omega</w:t></w:r></w:p>'
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{body}'
           f'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
           f'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    numbering = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="{W}">'
                 + "".join(f'<w:abstractNum w:abstractNumId="{k}"><w:multiLevelType w:val="singleLevel"/>{v}</w:abstractNum>' for k, v in ABSTRACTS.items())
                 + "".join(f'<w:num w:numId="{k}"><w:abstractNumId w:val="{k}"/></w:num>' for k in ABSTRACTS)
                 + '</w:numbering>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
              f'{rfonts("Cambria")}<w:sz w:val="17"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
              f'<w:pPrDefault><w:pPr/></w:pPrDefault></w:docDefaults>'
              f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
              f'<w:style w:type="paragraph" w:styleId="ListBullet"><w:name w:val="List Bullet"/><w:basedOn w:val="Normal"/>'
              f'<w:pPr><w:numPr><w:numId w:val="6"/></w:numPr><w:contextualSpacing/></w:pPr></w:style></w:styles>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}">'
                '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
             '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/></Relationships>')
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/document.xml": doc, "word/_rels/document.xml.rels": drels,
            "word/styles.xml": styles, "word/settings.xml": settings, "word/numbering.xml": numbering}

PROBES = {
    "ll0_symbol_cambria": dict(num_id=1),
    "ll1_symbol_cambria_deleted": dict(num_id=1, deleted=True),
    "ll2_symbol_arial11": dict(num_id=1, font="Arial", sz=22),
    "ll3_symbol20_cambria": dict(num_id=2),
    "ll4_calibri20_number_cambria": dict(num_id=3),
    "ll5_cambria_number": dict(num_id=4),
    "ll6_wingdings_cambria": dict(num_id=5),
    "ll7_symbol20_cambria_deleted": dict(num_id=2, deleted=True),
    "ll8_symbol_arial11_deleted": dict(num_id=1, font="Arial", sz=22, deleted=True),
    # round 2 (25f1d311bd reduced in place: a deleted mark loses its bullet there, not in ll1):
    # the level linked to the paragraph style, numbering through the style or direct
    "ll9_linked_via_style_deleted": dict(num_id=6, via_style=True, deleted=True),
    "ll10_linked_via_style": dict(num_id=6, via_style=True),
    "ll11_linked_direct_deleted": dict(num_id=6, deleted=True),
    "ll12_unlinked_direct_deleted_one": dict(num_id=1, deleted=True),
}

def measure(d):
    import fitz
    for fid in PROBES:
        p = os.path.join(d, fid + ".pdf")
        if not os.path.exists(p):
            print(fid, "NO PDF"); continue
        rows = []
        for bl in fitz.open(p)[0].get_text("dict")["blocks"]:
            for l in bl.get("lines", []):
                text = "".join(sp["text"] for sp in l["spans"])
                if text.strip():
                    rows.append((round(l["bbox"][1], 2), round(l["bbox"][0], 1), l["spans"][0]["font"][:10], round(l["spans"][0]["size"], 1), text.strip()[:14]))
        rows.sort()
        labels = [r for r in rows if r[1] < 135.0]
        tops = [r[0] for r in rows if r[1] >= 135.0]
        pitches = [round(b - a, 2) for a, b in zip(tops, tops[1:])]
        print(f"{fid:30s} labels {[(r[2], r[3], r[4]) for r in labels][:2]} n={len(labels)}  pitches {pitches}")

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
