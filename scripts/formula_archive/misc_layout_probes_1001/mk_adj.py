# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
from mkbase import mk
BD='<w:tblBorders>'+''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>' for s in ['top','left','bottom','right','insideH','insideV'])+'</w:tblBorders>'
def tc(w,txt): return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/></w:tcPr><w:p><w:r><w:t xml:space="preserve">{txt}</w:t></w:r></w:p></w:tc>'
def tbl(grid, rows, jc='center', extra=''):
    g=''.join(f'<w:gridCol w:w="{x}"/>' for x in grid)
    jcx=f'<w:jc w:val="{jc}"/>' if jc else ''
    trs=''.join('<w:tr>'+''.join(tc(w,t) for w,t in r)+'</w:tr>' for r in rows)
    return f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>{jcx}{BD}{extra}</w:tblPr><w:tblGrid>{g}</w:tblGrid>{trs}</w:tbl>'
A=tbl([1866,2872,2330,1994],[[(1866,'A1'),(2872,'A2'),(2330,'A3'),(1994,'A4')]])
A628=tbl([1866,2872,2330,1994],[[(2745,'A1'),(6068,'A2'),(6068,'A3'),(6068,'A4')]])
B=lambda jc='center': tbl([2745,6068],[[(2745,'B1'),(6068,'B2')],[(2745,'C1'),(6068,'C2 some longer words in this cell')]],jc)
P='<w:p><w:r><w:t>Lead</w:t></w:r></w:p>'
V={'j1_adjacent':P+A+B()+'<w:p/>',
   'j2_628shape':P+A628+B()+'<w:p/>',
   'j3_Bleft':P+A+B(None)+'<w:p/>',
   'j4_separated':P+A+'<w:p/>'+B()+'<w:p/>',
   'j5_Bonly':P+B()+'<w:p/>'}
for k,b in V.items(): mk(f'src/{k}.docx',b,15)