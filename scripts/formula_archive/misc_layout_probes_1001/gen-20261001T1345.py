# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys
sys.path.insert(0,'/tmp/conejo/probe_sum')
from mk import mk
def bd(name, sz): return f'<w:{name} w:val="single" w:sz="{sz}" w:space="0" w:color="auto"/>'
def tbl(tblb='', fixed=False, tcb='', jc='center'):
    jcx = f'<w:jc w:val="{jc}"/>' if jc else ''
    lay = '<w:tblLayout w:type="fixed"/>' if fixed else ''
    tb = f'<w:tblBorders>{tblb}</w:tblBorders>' if tblb else ''
    cell = lambda w,t: f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{tcb}</w:tcPr><w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:t>{t}</w:t></w:r></w:p></w:tc>'
    return (f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/>{jcx}{tb}{lay}<w:tblCellMar><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar></w:tblPr>'
            f'<w:tblGrid><w:gridCol w:w="2745"/><w:gridCol w:w="6068"/></w:tblGrid><w:tr>{cell(2745,"Hx")}{cell(6068,"Hy")}</w:tr><w:tr>{cell(2745,"Hz")}{cell(6068,"Hw")}</w:tr></w:tbl><w:p/>')
all4 = ''.join(bd(n,4) for n in ['top','left','bottom','right','insideH','insideV'])
all24 = ''.join(bd(n,24) for n in ['top','left','bottom','right','insideH','insideV'])
mixed = bd('top',4)+bd('left',4)+bd('bottom',4)+bd('right',4)+bd('insideH',4)+bd('insideV',24)
tc4 = '<w:tcBorders>'+bd('left',4)+bd('right',4)+'</w:tcBorders>'
V={'r1':tbl(all4),'r2':tbl(all4,fixed=True),'r3':tbl(tcb=tc4),'r4':tbl(all24),'r5':tbl(mixed),'r6':tbl(all24,fixed=True),'r7':tbl(mixed,jc=None),'r8':tbl(tcb='<w:tcBorders>'+bd('left',24)+bd('right',24)+'</w:tcBorders>')}
for k,b in V.items(): mk(f'src/{k}.docx',b,grid=False)