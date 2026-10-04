# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
from mkbase import mk
BD='<w:tblBorders>'+''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>' for s in ['top','left','bottom','right','insideH','insideV'])+'</w:tblBorders>'
NIL='<w:tblBorders>'+''.join(f'<w:{s} w:val="nil"/>' for s in ['top','left','bottom','right','insideH','insideV'])+'</w:tblBorders>'
def tc(w,txt): return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr><w:p><w:r><w:t xml:space="preserve">{txt}</w:t></w:r></w:p></w:tc>'
def tbl(grid, rows, jc='center', tblw='<w:tblW w:w="0" w:type="auto"/>', bd=BD, extra=''):
    g=''.join(f'<w:gridCol w:w="{x}"/>' for x in grid)
    jcx=f'<w:jc w:val="{jc}"/>' if jc else ''
    trs=''.join('<w:tr>'+''.join(tc(w,t) for w,t in r)+'</w:tr>' for r in rows)
    return f'<w:tbl><w:tblPr>{tblw}{jcx}{bd}{extra}</w:tblPr><w:tblGrid>{g}</w:tblGrid>{trs}</w:tbl>'
A=tbl([1866,2872,2330,1994],[[(1866,'A1'),(2872,'A2'),(2330,'A3'),(1994,'A4')]])
rowsB=[[(2745,'B1'),(6068,'B2')]]
V={'j6_Bfixed':tbl([2745,6068],rowsB,extra='<w:tblLayout w:type="fixed"/>'),
   'j7_Bnil':tbl([2745,6068],rowsB,bd=NIL),
   'j8_Bdxa':tbl([2745,6068],rowsB,tblw='<w:tblW w:w="8813" w:type="dxa"/>'),
   'j9_Bwide':tbl([3000,7695],[[(3000,'B1'),(7695,'B2')]],tblw='<w:tblW w:w="10695" w:type="dxa"/>',bd=NIL,extra='<w:tblLayout w:type="fixed"/>'),
   'j10_Bmar':tbl([2745,6068],rowsB,extra='<w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar>'),
}
P='<w:p><w:r><w:t>Lead</w:t></w:r></w:p>'
for k,b in V.items(): mk(f'src2/{k}.docx',P+A+b+'<w:p/>',15)