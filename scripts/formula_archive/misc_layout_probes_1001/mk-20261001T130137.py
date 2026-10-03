# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile
def mk(path, body, grid=True):
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/_rels/document.xml.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdSet" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>')
    g='<w:docGrid w:type="lines" w:linePitch="360"/>' if grid else ''
    z.writestr('word/document.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'+g+'</w:sectPr></w:body></w:document>')
    z.writestr('word/settings.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    z.close()
def p(t, sp):
    return f'<w:p><w:pPr><w:spacing {sp}/></w:pPr><w:r><w:t>{t}</w:t></w:r></w:p>'
def paras(sp): return ''.join(p(t,sp) for t in ['Aone','Btwo','Cthree','Dfour'])
def cell(x): return '<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="5000"/></w:tblGrid><w:tr><w:tc><w:tcPr><w:tcW w:w="5000" w:type="dxa"/></w:tcPr>'+x+'</w:tc></w:tr></w:tbl><w:p/>'
EX='w:before="120" w:after="120" w:line="400" w:lineRule="exact"'
EXL='w:beforeLines="10" w:before="36" w:afterLines="10" w:after="36" w:line="400" w:lineRule="exact"'
AU='w:before="120" w:after="120"'
V={'q1_body_exact':paras(EX),'q2_body_lines':paras(EXL),'q3_cell_exact':cell(paras(EX)),'q4_cell_lines':cell(paras(EXL)),
   'q5_body_auto':paras(AU),'q6_cell_auto':cell(paras(AU))}
for k,b in V.items(): mk(f'src/{k}.docx',b)
mk('src/q7_body_exact_nogrid.docx',paras(EX),grid=False)