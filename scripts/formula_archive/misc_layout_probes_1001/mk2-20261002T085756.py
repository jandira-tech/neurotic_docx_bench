# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys; sys.path.insert(0,'/tmp/conejo/gp')
src=open('/tmp/conejo/gp/mk.py').read().split("G4=[")[0]
exec(src)
G4=[2563,3280,1839,1530]
big=[(2745,3,'A'),(6068,1,'B'),(6068,3,'C'),(6068,1,'D')]
import zipfile
def patch(name,old,new):
    doc('/tmp/conejo/gp/src2/'+name+'.docx',G4,big)
    p='/tmp/conejo/gp/src2/'+name+'.docx'
    z=zipfile.ZipFile(p); items={i.filename:z.read(i.filename) for i in z.infolist()}; z.close()
    d=items['word/document.xml'].decode(); assert old in d; items['word/document.xml']=d.replace(old,new,1).encode()
    z=zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED)
    for k,v in items.items(): z.writestr(k,v)
    z.close()
A='<w:tblCellMar>'
CH='<w:tblPrChange w:id="9" w:author="A" w:date="2026-01-01T00:00:00Z"><w:tblPr>{}</w:tblPr></w:tblPrChange>'
patch('c1chg_fixed_pct',A,CH.format('<w:tblW w:w="5000" w:type="pct"/><w:tblLayout w:type="fixed"/>')+A)
patch('c2chg_fixed',A,CH.format('<w:tblLayout w:type="fixed"/>')+A)
patch('c3chg_pct',A,CH.format('<w:tblW w:w="5000" w:type="pct"/>')+A)
patch('c4live_fixed',A,'<w:tblLayout w:type="fixed"/>'+A)