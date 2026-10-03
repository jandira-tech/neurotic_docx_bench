# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, subprocess
import pymupdf as fitz
NS='xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
def cell(t): return f'<w:tc><w:tcPr><w:tcW w:w="3000" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>{t}</w:t></w:r></w:p></w:tc>'
def sdt(inner, name): return f'<w:sdt><w:sdtPr><w:alias w:val="{name}"/><w:tag w:val="{name}"/><w:id w:val="123"/></w:sdtPr><w:sdtEndPr/><w:sdtContent>{inner}</w:sdtContent></w:sdt>'
def tbl(rows): return '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/></w:tblPr><w:tblGrid><w:gridCol w:w="3000"/><w:gridCol w:w="3000"/></w:tblGrid>'+''.join(rows)+'</w:tbl>'
def row(cells): return '<w:tr>'+''.join(cells)+'</w:tr>'
P='<w:p><w:r><w:t>Before the table.</w:t></w:r></w:p>'
sect='<w:p><w:pPr><w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:pPr></w:p>'
variants={
 'plain': P+tbl([row([cell('ALPHA1'),cell('BRAVO1')]), row([cell('CHARLIE1'),cell('DELTA1')])]),
 'sdtrow': P+tbl([sdt(row([cell('ALPHA2'),cell('BRAVO2')]),'MyTable'), row([cell('CHARLIE2'),cell('DELTA2')])]),
 'sdtcell': P+tbl([row([sdt(cell('ALPHA3'),'Latin1'),cell('BRAVO3')]), row([cell('CHARLIE3'),cell('DELTA3')])]),
 'sdtrowcell': P+tbl([sdt(row([sdt(cell('ALPHA4'),'Latin1'),cell('BRAVO4')]),'MyTable'), row([cell('CHARLIE4'),cell('DELTA4')])]),
 'aftersect': P+sect+tbl([row([cell('ALPHA5'),cell('BRAVO5')]), row([cell('CHARLIE5'),cell('DELTA5')])]),
 'sdttable': P+sdt(tbl([row([cell('ALPHA6'),cell('BRAVO6')]), row([cell('CHARLIE6'),cell('DELTA6')])]),'Whole'),
}
for name,body in variants.items():
    doc=f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {NS}><w:body>{body}<w:p><w:r><w:t>After the table.</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>'
    p=f'/tmp/sdt_{name}.docx'
    with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml',doc)
    r=subprocess.run(['/tmp/jubarte-main','convert',p,'-o',p.replace('.docx','.pdf'),'--force'],capture_output=True,text=True)
    try:
        d=fitz.open(p.replace('.docx','.pdf')); t=' '.join(pg.get_text() for pg in d)
        print(f"{name:11} pages {len(d)}  ALPHA {'ALPHA' in t}  CHARLIE {'CHARLIE' in t}  After {'After the' in t}")
    except Exception as e: print(name, 'ERR', e, r.stderr[-200:])