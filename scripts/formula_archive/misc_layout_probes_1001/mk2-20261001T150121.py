# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, json
X=[('xα','y','z'),('xж','y','z'),('xא','y','z'),('xก','y','z'),('x가','y','z'),('xあ','y','z'),('xア','y','z'),('xक','y','z'),('x٣','y','z'),('xé','y','z'),('xß','y','z'),('xł','y','z'),('xə','y','z'),('xﬁ','y','z'),('xℓ','y','z'),('x²','y','z'),('xª','y','z'),('xº','y','z'),('xµ','y','z'),('xÆ','y','z'),('xǅ','y','z'),('xʰ','y','z'),('xᴀ','y','z'),('xḁ','y','z'),('xⱠ','y','z'),('xꜰ','y','z'),('xＡ','y','z'),('x­','y','z'),('x‍','y','z'),('xⓐ','y','z'),
   ('αβ','γ','δ'),('жз','и','к'),('אב','ג','ד'),('عب','ت','ث'),('กข','ค','ง'),('가나','다','라'),('あい','う','え'),('アイ','ウ','エ'),('कख','ग','घ'),('ⰀⰁ','Ⰲ','Ⰳ'),('ⅠⅡ','Ⅲ','Ⅳ'),('٣٤','٥','٦'),('ԱԲ','Գ','Դ'),('აბ','გ','დ'),('α1','2','3'),('ж1','2','3'),('1α','β','γ'),('αx','y','z'),('ⓐⓑ','ⓒ','ⓓ'),('²³','¹','⁴')]
json.dump(X,open('cases2.json','w'),ensure_ascii=False)
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')
def mk(path, which):
    body=''.join(f'<w:p><w:r><w:t xml:space="preserve">{esc(p+(a if which=="a" else b))} tail{i}</w:t></w:r></w:p>' for i,(p,a,b) in enumerate(X))
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/document.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    z.close()
mk('a2/scripts.docx','a'); mk('b2/scripts.docx','b')