# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def tc(w,span,t):
    tw=f'<w:tcW w:w="{w}" w:type="dxa"/>' if w else '<w:tcW w:w="0" w:type="auto"/>'
    gs=f'<w:gridSpan w:val="{span}"/>' if span>1 else ''
    return f'<w:tc><w:tcPr>{tw}{gs}</w:tcPr><w:p><w:r><w:t>{t}</w:t></w:r></w:p></w:tc>'
def doc(path,grid,cells):
    b=''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>' for s in ('top','left','bottom','right','insideH','insideV'))
    rows=''.join('<w:tr>'+''.join(tc(w,sp,f'{t}{r}') for w,sp,t in cells)+'</w:tr>' for r in range(3))
    g=''.join(f'<w:gridCol w:w="{x}"/>' for x in grid)
    body=f'<w:p><w:r><w:t>Before</w:t></w:r></w:p><w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:jc w:val="center"/><w:tblBorders>{b}</w:tblBorders><w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr><w:tblGrid>{g}</w:tblGrid>{rows}</w:tbl><w:p><w:r><w:t>After</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/_rels/document.xml.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>')
    z.writestr('word/settings.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}"><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat></w:settings>')
    z.writestr('word/document.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
    z.close()
G4=[2563,3280,1839,1530]
big=[(2745,3,'A'),(6068,1,'B'),(6068,3,'C'),(6068,1,'D')]
doc('/tmp/conejo/gp/src/p1pad_big.docx',G4,big)
doc('/tmp/conejo/gp/src/p2full_big.docx',[915,915,915,6068,2023,2023,2022,6068],big)
doc('/tmp/conejo/gp/src/p3pad_auto.docx',G4,[(0,3,'A'),(0,1,'B'),(0,3,'C'),(0,1,'D')])
doc('/tmp/conejo/gp/src/p4pad_small.docx',G4,[(2000,3,'A'),(2000,1,'B'),(2000,3,'C'),(2000,1,'D')])
doc('/tmp/conejo/gp/src/p5grid_big.docx',G4,[(6068,1,'A'),(6068,1,'B'),(6068,1,'C'),(6068,1,'D')])