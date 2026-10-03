# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
from mkbase import mk
R='<w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:sz w:val="24"/></w:rPr>'
def cell(w, txt, tcw):
    tcpr=f'<w:tcPr><w:tcW w:w="{tcw}" w:type="dxa"/></w:tcPr>'
    return f'<w:tc>{tcpr}<w:p><w:r>{R}<w:t>{w}</w:t></w:r></w:p><w:p><w:r>{R}<w:t>{txt}</w:t></w:r></w:p></w:tc>'
def tbl(tblw, layout, words, tcws, grid):
    lay='<w:tblLayout w:type="fixed"/>' if layout else ''
    bd='<w:tblBorders>'+''.join(f'<w:{s} w:val="single" w:sz="4" w:space="0" w:color="auto"/>' for s in ['top','left','bottom','right','insideH','insideV'])+'</w:tblBorders>'
    g=''.join(f'<w:gridCol w:w="{x}"/>' for x in grid)
    cells=''.join(cell(w,f'C{i}',t) for i,(w,t) in enumerate(zip(words,tcws)))
    return f'<w:tbl><w:tblPr>{tblw}{bd}{lay}</w:tblPr><w:tblGrid>{g}</w:tblGrid><w:tr>{cells}</w:tr></w:tbl><w:p/>'
U=lambda n:'_'*n
D='<w:tblW w:w="9360" w:type="dxa"/>'
P='<w:tblW w:w="5000" w:type="pct"/>'
A='<w:tblW w:w="0" w:type="auto"/>'
w2=[U(30),U(40)]
V={
 'a1_dxa':tbl(D,False,w2,[4680,4680],[4680,4680]),
 'a2_pct':tbl(P,False,w2,[4680,4680],[4680,4680]),
 'a3_auto':tbl(A,False,w2,[4680,4680],[4680,4680]),
 'a4_fixed':tbl(D,True,w2,[4680,4680],[4680,4680]),
 'a5_ee7':tbl('<w:tblW w:w="9422" w:type="dxa"/>',False,[U(33),'Environmental',U(36),'Sciences'],[4321,720,4381,4381],[3945,1535,4304,989]),
 'a6_ee7grid':tbl('<w:tblW w:w="9422" w:type="dxa"/>',False,[U(33),'Environmental',U(36),'Sciences'],[4321,720,4381,4381],[2355,2355,2356,2356]),
 'a7_fitmins':tbl(D,False,[U(20),U(25)],[8000,1360],[8000,1360]),
}
for k,b in V.items(): mk(f'src/{k}.docx',b,15)