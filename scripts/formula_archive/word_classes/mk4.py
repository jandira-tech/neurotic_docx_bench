# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, json
# (prefix, lastA, lastB, eastAsia lang or None)
X=[('a)','.','!',None),('a.','”','"',None),('a-','-','+',None),('a?','!','.',None),('a,','“','‘',None),('a§','.',',',None),('a−','.',',',None),('a→','.',',',None),('a●','.',',',None),('a、','。','，',None),
   ('a(','(','[',None),('a.','.',',',None),('a$','%','#',None),('a—','“','‘',None),('a…','.',',',None),('a’','s','t',None),("a'",'s','t',None),('a.','1','2',None),('a²','.',',',None),('aⓐ','.',',',None),
   ('我们的','合同','合约','zh-CN'),('我们的合','同','约','zh-CN'),('私たちの','契約','規約','ja-JP'),('私たちの契','約','規','ja-JP'),('우리의','계약','규약','ko-KR'),('สัญญาของ','เรา','ท่าน','th-TH'),('สัญญาของเ','ร','ท','th-TH'),('漢字','字','子','zh-CN'),('漢字','字','子','ja-JP')]
json.dump(X,open('cases4.json','w'),ensure_ascii=False)
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')
def mk(path, which):
    def para(i,p,a,b,lang):
        rpr=f'<w:rPr><w:lang w:eastAsia="{lang}" w:bidi="{lang}"/></w:rPr>' if lang else ''
        return f'<w:p><w:r>{rpr}<w:t xml:space="preserve">{esc(p+(a if which=="a" else b))}</w:t></w:r><w:r><w:t xml:space="preserve"> tail{i}</w:t></w:r></w:p>'
    body=''.join(para(i,*c) for i,c in enumerate(X))
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/document.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    z.close()
mk('a4/punct.docx','a'); mk('b4/punct.docx','b')