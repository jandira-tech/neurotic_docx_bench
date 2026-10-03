# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, re, sys
SRC='p49b/src/g_300_h250.docx'
z=zipfile.ZipFile(SRC); doc=z.read('word/document.xml').decode()
a=doc.find('<mc:AlternateContent'); rs=doc.rfind('<w:r>',0,a); rs2=doc.rfind('<w:r ',0,a); rs=max(rs,rs2)
ae=doc.find('</mc:AlternateContent></w:r>',a)+len('</mc:AlternateContent></w:r>')
run=doc[rs:ae]
def sib(off_pt,h_pt,overlap='1',idn=900):
    r=re.sub(r'<mc:Fallback>.*?</mc:Fallback>','',run,flags=re.S)
    r=re.sub(r'(<wp:positionV relativeFrom="paragraph"><wp:posOffset>)\d+',lambda m:m.group(1)+str(int(off_pt*12700)),r)
    cy=str(int(h_pt*12700))
    r=re.sub(r'(<wp:extent cx="\d+" cy=")\d+',lambda m:m.group(1)+cy,r)
    r=re.sub(r'(<a:ext cx="\d+" cy=")\d+',lambda m:m.group(1)+cy,r)
    r=re.sub(r'<wp:docPr id="\d+" name="[^"]*"','<wp:docPr id="%d" name="Sib %d"'%(idn,idn),r)
    r=re.sub(r'wp14:anchorId="[0-9A-F]+"','wp14:anchorId="7A00%04X"'%idn,r)
    r=re.sub(r'wp14:editId="[0-9A-F]+"','wp14:editId="7B00%04X"'%idn,r)
    r=re.sub(r'relativeHeight="\d+"','relativeHeight="%d"'%(251660000+idn),r)
    r=re.sub(r'allowOverlap="\d"','allowOverlap="%s"'%overlap,r)
    r=r.replace('General Comments','SIBLING')
    r=re.sub(r'w14:paraId="[0-9A-F]+"','',r); r=re.sub(r'w14:textId="[0-9A-F]+"','',r)
    return r
def write(name,d):
    out=f'p49d/src/{name}.docx'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as o:
        for it in z.infolist():
            o.writestr(it, d.encode() if it.filename=='word/document.xml' else z.read(it.filename))
# s1: sibling in the anchor paragraph overlapping the lifted spot
write('s1_sib_overlap', doc[:ae]+sib(20,150)+doc[ae:])
# s2: same, allowOverlap=0 on both
d2=doc[:ae]+sib(20,150,'0')+doc[ae:]
d2=d2.replace('allowOverlap="1"','allowOverlap="0"')
write('s2_sib_overlap_no', d2)
# s3: control sibling above the lifted spot
write('s3_sib_clear', doc[:ae]+sib(20,30)+doc[ae:])
# s4: sibling anchored in the previous paragraph (Filler line 19), overlapping
fl=doc.find('Filler line 19'); ps=doc.rfind('<w:p>',0,fl); ps2=doc.rfind('<w:p ',0,fl); ps=max(ps,ps2)
pe=doc.find('>',ps)+1
write('s4_sib_prev_para', doc[:pe]+sib(43,150,'1',901)+doc[pe:])