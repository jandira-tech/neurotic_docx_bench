# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,sys
W='xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"'
R='<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="20"/></w:rPr>'
def box(h_emu, text, fill='F1D9A9'):
    return (f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r>{R}<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="5080000" cy="{h_emu}"/><wp:docPr id="1" name="Box 1"/>'
      f'<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"><wps:wsp><wps:cNvSpPr/><wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="5080000" cy="{h_emu}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="{fill}"/></a:solidFill><a:ln><a:noFill/></a:ln></wps:spPr>'
      f'<wps:txbx><w:txbxContent><w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r>{R}<w:t>{text}</w:t></w:r></w:p></w:txbxContent></wps:txbx><wps:bodyPr lIns="18000" tIns="18000" rIns="18000" bIns="18000" anchor="t"><a:noAutofit/></wps:bodyPr></wps:wsp></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>')
def doc(path, hdr_inner):
    top = f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r>{R}<w:t>HdrTop</w:t></w:r></w:p>'
    d=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body><w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r>{R}<w:t>BodyX</w:t></w:r></w:p><w:sectPr><w:headerReference w:type="default" r:id="rIdH1"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="720" w:right="1440" w:bottom="1440" w:left="1440" w:header="360" w:footer="720"/></w:sectPr></w:body></w:document>'
    h=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr {W}>{top}{hdr_inner}</w:hdr>'
    ct='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/></Types>'
    rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    drels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdH1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/></Relationships>'
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('[Content_Types].xml',ct); z.writestr('_rels/.rels',rels); z.writestr('word/document.xml',d)
        z.writestr('word/_rels/document.xml.rels',drels); z.writestr('word/header1.xml',h)
doc('src/hb0.docx','')
doc('src/hb15.docx',box(190500,'Boxed note'))
doc('src/hb40.docx',box(508000,'Boxed note'))