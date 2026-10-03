# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""mkdocx.py out.docx BODYXML [styles.xml] [--png FILE] [--page "w h top right bottom left"] [--grid "lines 312"] [--compat N] [--settings XML] [--numbering FILE] [--header XML] : minimal valid docx.

--header XML is the body of word/header1.xml (paragraphs), the default header.

--settings adds XML before w:compat in settings.xml (implies --compat 15 unless given; XML holding
its own <w:compat> replaces the default compat block);
--numbering embeds FILE as word/numbering.xml.

Without --compat there is no settings.xml, which Word lays out as a legacy (pre-15) document:
widow control, for one, does not hold across table row splits there (probe wid_w4/w5 0930).

Letter with 1in margins unless --page (twips). --png embeds FILE as word/media/image1.png under
relationship id rId20, for <a:blip r:embed="rId20"/> in BODYXML.
"""
import argparse, zipfile

ap = argparse.ArgumentParser()
ap.add_argument("out"); ap.add_argument("body"); ap.add_argument("styles", nargs="?")
ap.add_argument("--png"); ap.add_argument("--compat"); ap.add_argument("--settings", default=""); ap.add_argument("--numbering"); ap.add_argument("--page", default="12240 15840 1440 1440 1440 1440"); ap.add_argument("--grid", default=""); ap.add_argument("--header")
a = ap.parse_args()
if a.settings and not a.compat: a.compat = "15"
numbering = open(a.numbering).read() if a.numbering else None
styles = open(a.styles).read() if a.styles else None
pw, ph, mt, mr, mb, ml = a.page.split()
W = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
     'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
     'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
     'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
     'xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office"')
doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>{a.body}'
       f'<w:sectPr>' + ('<w:headerReference w:type="default" r:id="rId30"/>' if a.header else '') + f'<w:pgSz w:w="{pw}" w:h="{ph}"/><w:pgMar w:top="{mt}" w:right="{mr}" w:bottom="{mb}" w:left="{ml}" '
       'w:header="720" w:footer="720" w:gutter="0"/>' + (f'<w:docGrid w:type="{a.grid.split()[0]}" w:linePitch="{a.grid.split()[1]}"/>' if a.grid else '') + '</w:sectPr></w:body></w:document>')
ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      + ('<Default Extension="png" ContentType="image/png"/>' if a.png else '')
      + '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      + ('<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>' if a.compat else '')
      + ('<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>' if a.header else '')
      + ('<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>' if numbering else '')
      + ('<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' if styles else '')
      + '</Types>')
rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         + ('<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' if styles else '')
         + ('<Relationship Id="rId7" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>' if numbering else '')
         + ('<Relationship Id="rId8" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>' if a.compat else '')
         + ('<Relationship Id="rId30" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/>' if a.header else '')
         + ('<Relationship Id="rId20" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>' if a.png else '')
         + '</Relationships>')
z = zipfile.ZipFile(a.out, 'w', zipfile.ZIP_DEFLATED)
z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('word/_rels/document.xml.rels', drels); z.writestr('word/document.xml', doc)
if styles: z.writestr('word/styles.xml', styles)
if numbering: z.writestr('word/numbering.xml', numbering)
if a.header: z.writestr('word/header1.xml', f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {W}>{a.header}</w:hdr>')
if a.compat:
    z.writestr('word/settings.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
               + a.settings + ('' if '<w:compat>' in a.settings else '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="' + a.compat + '"/></w:compat>') + '</w:settings>')
if a.png: z.write(a.png, 'word/media/image1.png')
z.close()
