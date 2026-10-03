# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, json
X=[('aⅠ','.',','),('a⅓','.',','),('a①','.',','),('a①','②','③'),('aＡＢ','Ｃ','Ｄ'),('a１２','３','４'),('a１','.',','),('a，','.',','),('aー','.',','),('a・','.',','),('a々','.',','),('漢々','字','子'),('aｱｲ','ｳ','ｴ'),
   ('ԀԁԂ','ԃ','Ԅ'),('a⁴','.',','),('aⁿ','.',','),('x​','y','z'),('x ','y','z'),('x ','y','z'),('x　','y','z'),('x⁠','y','z'),('x‎','y','z'),('xⅠ','Ⅱ','Ⅲ'),('a.','­','-'),('ª','º','µ'),('a×','.',','),('á','.',','),('a’','.',','),("a'",'.',','),('a℃','.',','),('aℓ','.',',')]
json.dump(X,open('cases5.json','w'),ensure_ascii=False)
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')
def mk(path, which):
    body=''.join(f'<w:p><w:r><w:t xml:space="preserve">{esc(p+(a if which=="a" else b))} tail{i}</w:t></w:r></w:p>' for i,(p,a,b) in enumerate(X))
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/document.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    z.close()
mk('a5/edge.docx','a'); mk('b5/edge.docx','b')