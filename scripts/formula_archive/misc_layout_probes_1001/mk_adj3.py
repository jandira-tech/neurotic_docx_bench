# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk_adj2.py').read().split("A=tbl(")[0])
A=tbl([1866,2872,2330,1994],[[(1866,'A1'),(2872,'A2'),(2330,'A3'),(1994,'A4')]])
B=tbl([2745,6068],[[(2745,'B1'),(6068,'B2')]])
Bjc=B.replace('<w:tr>','<w:tr><w:trPr><w:jc w:val="center"/></w:trPr>')
Bjl=B.replace('<w:tr>','<w:tr><w:trPr><w:jc w:val="left"/></w:trPr>')
P='<w:p><w:r><w:t>Lead</w:t></w:r></w:p>'
mk('src3/j11_Browjc.docx',P+A+Bjc+'<w:p/>',15)
mk('src3/j12_Browleft.docx',P+A+Bjl+'<w:p/>',15)
mk('src3/j13_Browjc_alone.docx',P+Bjc.replace('<w:jc w:val="center"/></w:tblPr>','</w:tblPr>')+'<w:p/>',15)