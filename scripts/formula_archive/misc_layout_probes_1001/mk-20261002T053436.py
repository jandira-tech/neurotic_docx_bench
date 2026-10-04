# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
def mk(path, body, headers):
    ct='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    ct+=''.join(f'<Override PartName="/word/header{i+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>' for i in range(len(headers)))+'</Types>'
    rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="rIdH{i+1}" Type="{R}/header" Target="header{i+1}.xml"/>' for i in range(len(headers)))+'</Relationships>'
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml',ct)
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/document.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}" xmlns:r="{R}"><w:body>{body}</w:body></w:document>')
    z.writestr('word/_rels/document.xml.rels',rels)
    for i,h in enumerate(headers):
        z.writestr(f'word/header{i+1}.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="{W}" xmlns:r="{R}"><w:p><w:r><w:t>{h}</w:t></w:r></w:p></w:hdr>')
    z.close()
sp=lambda h:f'<w:sectPr><w:headerReference w:type="default" r:id="rIdH{h}"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
# hs1: A two sections, B one section (section break deleted)
mk('a/hs1.docx',f'<w:p><w:pPr>{sp(1)}</w:pPr><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp(2)}',['First head','Second head'])
mk('b/hs1.docx',f'<w:p><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp(1)}',['Bravo head'])
# hs2: A two sections, B two sections, each header changed (control)
mk('a/hs2.docx',f'<w:p><w:pPr>{sp(1)}</w:pPr><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp(2)}',['First head','Second head'])
mk('b/hs2.docx',f'<w:p><w:pPr>{sp(1)}</w:pPr><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p>{sp(2)}',['First head changed','Second head changed'])
# hs3: A three sections, B two (middle break kept? B keeps first break)
mk('a/hs3.docx',f'<w:p><w:pPr>{sp(1)}</w:pPr><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:pPr>{sp(2)}</w:pPr><w:r><w:t>Alpha body two.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body three.</w:t></w:r></w:p>{sp(3)}',['First head','Second head','Third head'])
mk('b/hs3.docx',f'<w:p><w:pPr>{sp(1)}</w:pPr><w:r><w:t>Alpha body one.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body two.</w:t></w:r></w:p><w:p><w:r><w:t>Alpha body three.</w:t></w:r></w:p>{sp(2)}',['Bravo one','Bravo last'])