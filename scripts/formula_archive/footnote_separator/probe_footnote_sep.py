# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Word's footnote area: how much of the page the separator note takes.

636ef078e7 (Aptos 11, pPrDefault after 160 / line 259, a separator note
of `after 0 / line 240 auto`): Word's page 3 ends its body 44pt above the
first footnote's line and pushes two lines that would have ended 15pt
above it to page 4; jubarte reserves a fixed 12pt over the notes
(`FOOTNOTE_SEP_GAP`) and keeps them. These probes measure the reservation
directly: a body of 0.5pt-exact paragraphs (`L0001`…), the first holding
the footnote reference, so the last paragraph Word keeps on page 1 gives
the body floor to half a point; the notes and the separator rule are
read from the PDF. Variants change only the separator note (its run
size, spacing, line rule) and the footnote paragraph's spacing.

Usage: uv run python scripts/probe_footnote_sep.py OUTDIR
"""
import json, os, sys, zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NPARAS = 1400

def parts(sep_ppr, sep_rpr, fn_ppr, ppr_default, body_size=22, fn_rpr="", fn_lines=1, no_sep=False):
    body = ('<w:p><w:pPr><w:spacing w:after="0" w:line="10" w:lineRule="exact"/></w:pPr>'
            '<w:r><w:t xml:space="preserve">L0001 </w:t></w:r>'
            '<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:footnoteReference w:id="1"/></w:r></w:p>')
    body += ''.join(f'<w:p><w:pPr><w:spacing w:after="0" w:line="10" w:lineRule="exact"/></w:pPr><w:r><w:t>L{i:04d}</w:t></w:r></w:p>'
                    for i in range(2, NPARAS + 1))
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{body}'
           f'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    note_text = ' '.join(f'note{k}' for k in range(1, 1 + 9 * fn_lines))
    seps = '' if no_sep else (
        f'<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr>{sep_ppr}</w:pPr><w:r>{sep_rpr}<w:separator/></w:r></w:p></w:footnote>'
        f'<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr>{sep_ppr}</w:pPr><w:r>{sep_rpr}<w:continuationSeparator/></w:r></w:p></w:footnote>')
    footnotes = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:footnotes xmlns:w="{W}">{seps}'
                 f'<w:footnote w:id="1"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/>{fn_ppr}</w:pPr>'
                 f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>'
                 f'<w:r>{fn_rpr}<w:t xml:space="preserve"> {note_text}</w:t></w:r></w:p></w:footnote></w:footnotes>')
    styles = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
              f'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="{body_size}"/><w:szCs w:val="{body_size}"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>'
              f'<w:pPrDefault><w:pPr>{ppr_default}</w:pPr></w:pPrDefault></w:docDefaults>'
              f'<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
              f'<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/><w:basedOn w:val="Normal"/>'
              f'<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>'
              f'<w:style w:type="character" w:styleId="FootnoteReference"><w:name w:val="footnote reference"/><w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>'
              f'</w:styles>')
    settings = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}">'
                + ('' if no_sep else '<w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>')
                + '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
          '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
          '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>'
             '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes" Target="footnotes.xml"/></Relationships>')
    return {"[Content_Types].xml": ct, "_rels/.rels": rels, "word/document.xml": doc, "word/_rels/document.xml.rels": drels,
            "word/styles.xml": styles, "word/settings.xml": settings, "word/footnotes.xml": footnotes}

SEP240 = '<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
PROBES = {
    # the separator note as Word writes it, docDefaults without spacing
    "s0_plain": dict(sep_ppr=SEP240, sep_rpr="", fn_ppr="", ppr_default=""),
    # 636ef078e7's defaults: after 160 / line 259 on every paragraph
    "s1_defaults_259": dict(sep_ppr=SEP240, sep_rpr="", fn_ppr="", ppr_default='<w:spacing w:after="160" w:line="259" w:lineRule="auto"/>'),
    # the separator run at 20pt: does the reservation follow its font?
    "s2_run_40": dict(sep_ppr=SEP240, sep_rpr='<w:rPr><w:sz w:val="40"/></w:rPr>', fn_ppr="", ppr_default=""),
    # the separator paragraph mark at 20pt, run default
    "s3_mark_40": dict(sep_ppr=SEP240 + '<w:rPr><w:sz w:val="40"/></w:rPr>', sep_rpr="", fn_ppr="", ppr_default=""),
    # spacing before / after on the separator paragraph
    "s4_before_200": dict(sep_ppr='<w:spacing w:before="200" w:after="0" w:line="240" w:lineRule="auto"/>', sep_rpr="", fn_ppr="", ppr_default=""),
    "s5_after_200": dict(sep_ppr='<w:spacing w:after="200" w:line="240" w:lineRule="auto"/>', sep_rpr="", fn_ppr="", ppr_default=""),
    # exact and double line rules on the separator paragraph
    "s6_exact_600": dict(sep_ppr='<w:spacing w:after="0" w:line="600" w:lineRule="exact"/>', sep_rpr="", fn_ppr="", ppr_default=""),
    "s7_double": dict(sep_ppr='<w:spacing w:after="0" w:line="480" w:lineRule="auto"/>', sep_rpr="", fn_ppr="", ppr_default=""),
    # no separator note at all
    "s8_no_sep": dict(sep_ppr="", sep_rpr="", fn_ppr="", ppr_default="", no_sep=True),
    # the footnote paragraph's own spacing before / after
    "t1_fn_before_200": dict(sep_ppr=SEP240, sep_rpr="", fn_ppr='<w:spacing w:before="200" w:after="0" w:line="240" w:lineRule="auto"/>', ppr_default=""),
    "t2_fn_after_200": dict(sep_ppr=SEP240, sep_rpr="", fn_ppr='<w:spacing w:after="200" w:line="240" w:lineRule="auto"/>', ppr_default=""),
    # a two-line note, and a note whose glyphs are 6pt under a 10pt mark (636ef078e7)
    "t3_fn_two_lines": dict(sep_ppr=SEP240, sep_rpr="", fn_ppr="", ppr_default="", fn_lines=2),
    "t4_fn_glyphs_12": dict(sep_ppr=SEP240, sep_rpr="", fn_ppr="", ppr_default="", fn_rpr='<w:rPr><w:sz w:val="12"/></w:rPr>'),
}

def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    manifest = []
    for fid, spec in PROBES.items():
        with zipfile.ZipFile(os.path.join(out, fid + ".docx"), "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in parts(**spec).items():
                z.writestr(name, data)
        manifest.append(dict(id=fid, **{k: v for k, v in spec.items()}))
    json.dump(manifest, open(os.path.join(out, "manifest.json"), "w"), indent=1)
    print(len(manifest), "probes")

if __name__ == "__main__":
    main()
