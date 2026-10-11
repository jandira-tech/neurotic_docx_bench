# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile
def mk(path, body, compat=None):
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    so='<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>' if compat else ''
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'+so+'</Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/_rels/document.xml.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+('<Relationship Id="rIdSet" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>' if compat else '')+'</Relationships>')
    z.writestr('word/document.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    if compat: z.writestr('word/settings.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="{compat}"/></w:compat></w:settings>')
    z.close()
def doc(first_ppr, last_ppr):
    rows=''.join(f'<w:tr><w:tc><w:tcPr><w:tcW w:w="9000" w:type="dxa"/></w:tcPr><w:p><w:r><w:t>Filler{i:02}</w:t></w:r></w:p></w:tc></w:tr>' for i in range(30))
    cell=f'<w:p><w:pPr>{first_ppr}</w:pPr><w:r><w:t>KeepHead</w:t></w:r></w:p>'+''.join(f'<w:p><w:r><w:t>Body{i:02}</w:t></w:r></w:p>' for i in range(30))+f'<w:p><w:pPr>{last_ppr}</w:pPr><w:r><w:t>LastPara</w:t></w:r></w:p>'
    rows+=f'<w:tr><w:tc><w:tcPr><w:tcW w:w="9000" w:type="dxa"/></w:tcPr>{cell}</w:tc></w:tr>'
    return f'<w:tbl><w:tblPr><w:tblW w:w="9000" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="9000"/></w:tblGrid>{rows}</w:tbl><w:p/>'
V={'k1':('<w:keepLines/>',''),'k2':('<w:keepNext/>',''),'k3':('<w:keepNext/><w:keepLines/>',''),'k4':('','<w:keepLines/>')}
for k,(a,b) in V.items():
    mk(f'src/{k}_c15.docx',doc(a,b),15)
    mk(f'src/{k}_leg.docx',doc(a,b))