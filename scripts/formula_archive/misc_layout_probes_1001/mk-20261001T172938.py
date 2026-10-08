# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,sys
CT='<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
RELS='<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
def docx(path,body):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('[Content_Types].xml',CT); z.writestr('_rels/.rels',RELS)
        z.writestr('word/document.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
p=lambda t:f'<w:p><w:r><w:t>{t}</w:t></w:r></w:p>'
tbl=lambda *cells:'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr><w:tblGrid><w:gridCol w:w="4000"/></w:tblGrid>'+''.join(f'<w:tr><w:tc><w:tcPr><w:tcW w:w="4000" w:type="dxa"/></w:tcPr>{p(c)}</w:tc></w:tr>' for c in cells)+'</w:tbl>'
docx('a.docx',p('square root of x')+p('cube root of three x')+p('empty degree of x'))
docx('b.docx',tbl('Family name','Given name')+'<w:p/>')