# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk_adj2.py').read().split("A=tbl(")[0])
W=tbl([1866,2872,2330,1994],[[(1866,'W1'),(2872,'W2'),(2330,'W3'),(1994,'W4')]])
N=tbl([2745,6068],[[(2745,'N1'),(6068,'N2')]])
N3=tbl([2745,6068],[[(2745,'N1'),(6068,'N2')],[(2745,'M1'),(6068,'M2')]])
P='<w:p><w:r><w:t>Lead</w:t></w:r></w:p>'
mk('src4/j14_narrow_wide.docx',P+N+W+'<w:p/>',15)
mk('src4/j15_wide_narrow_wide.docx',P+W+N+W+'<w:p/>',15)
mk('src4/j16_narrow2_wide.docx',P+N3+W+'<w:p/>',15)
mk('src4/j17_narrow_wideL.docx',P+N+W.replace('<w:jc w:val="center"/>','')+'<w:p/>',15)