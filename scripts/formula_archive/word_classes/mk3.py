# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, json
X=[('−−','−','≤'),('→→','→','←'),('●●','●','■'),('✓✓','✓','✗'),('™™','™','℠'),('、、','、','。'),('¬¬','¬','±'),('§§','§','¶'),('——','—','–'),('““','“','”'),
   ('漢字','字','子'),('あ漢','字','子'),('漢あ','い','う'),('アあ','い','う'),('あア','イ','ウ'),('가漢','字','子'),('ーア','イ','ウ'),
   ('x₂','y','z'),('H₂','O','Q'),('x⁴','y','z'),('xⁿ','y','z'),('x⅓','y','z'),('x℃','y','z'),('xℕ','y','z'),('xΩ','y','z'),('xÅ','y','z'),
   ('xἀ','y','z'),('xƀ','y','z'),('xˈ','y','z'),('xԱ','y','z'),('xა','y','z'),('xத','y','z'),('xব','y','z'),('xසි','y','z'),('xཀ','y','z'),('xက','y','z'),('xក','y','z'),('xᠠ','y','z'),('xܐ','y','z'),('xހ','y','z'),('xߊ','y','z'),('xሀ','y','z'),('xԀ','y','z'),('xᎠ','y','z'),('xᐁ','y','z'),('xب','y','z'),('xﭐ','y','z'),('xיִ','y','z'),('x𝑥','y','z'),('x😀','y','z'),('xກ','y','z'),('x๓','y','z'),('xⅰ','y','z'),('xั','y','z'),
   ('ກຂ','ຄ','ງ'),('₂₃','₄','₅'),('ᴀʙ','ᴄ','ᴅ'),('Ⱡⱡ','Ɫ','Ᵽ')]
json.dump(X,open('cases3.json','w'),ensure_ascii=False)
def esc(s): return s.replace('&','&amp;').replace('<','&lt;')
def mk(path, which):
    body=''.join(f'<w:p><w:r><w:t xml:space="preserve">{esc(p+(a if which=="a" else b))} tail{i}</w:t></w:r></w:p>' for i,(p,a,b) in enumerate(X))
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/document.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    z.close()
mk('a3/runs.docx','a'); mk('b3/runs.docx','b')