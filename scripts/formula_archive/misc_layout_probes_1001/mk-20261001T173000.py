# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
cell=lambda inner:f'<w:tc><w:tcPr><w:tcW w:w="4000" w:type="dxa"/></w:tcPr>{inner}</w:tc>'
T=lambda rows:'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr><w:tblGrid><w:gridCol w:w="4000"/></w:tblGrid>'+''.join(f'<w:tr>{cell(r)}</w:tr>' for r in rows)+'</w:tbl>'
docx('n1.docx',T([p('AAA'),T([p('CCC')])+'<w:p/>'])+'<w:p/>')
docx('n2.docx',T([T([p('CCC')])+'<w:p/>'])+'<w:p/>')
docx('n3.docx',T([p('AAA'),p('BBB')])+'<w:p/>')
docx('n4.docx',T([p('AAA')])+'<w:p/>')