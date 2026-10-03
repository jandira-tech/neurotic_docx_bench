# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,os,re
base='x'
doc=open('x/word/document.xml',encoding='utf-8').read()
R='<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>'
sp='<w:r w:rsidRPr="0045650A"><w:rPr><w:bCs/></w:rPr><w:t xml:space="preserve"> </w:t></w:r><w:r w:rsidRPr="0045650A">'+R+'<w:t>gastro-</w:t></w:r>'
two='<w:r w:rsidRPr="0045650A">'+R+'<w:t>gastro-</w:t></w:r><w:proofErr w:type="spellStart"/><w:r w:rsidRPr="0045650A">'+R+'<w:t>oesophageal</w:t></w:r>'
i=doc.find(sp); assert i>0
j=doc.find(two,i); assert j==i+len(sp)-len('<w:r w:rsidRPr="0045650A">'+R+'<w:t>gastro-</w:t></w:r>'), (i,j)
V={'v4_spjoin':doc[:i]+'<w:r w:rsidRPr="0045650A">'+R+'<w:t xml:space="preserve"> gastro-</w:t></w:r>'+doc[i+len(sp):],
   'v5_onerun':doc[:j]+'<w:r w:rsidRPr="0045650A">'+R+'<w:t>gastro-oesophageal</w:t></w:r><w:proofErr w:type="spellStart"/>'+doc[j+len(two):]}
files=[]
for r,_,fs in os.walk(base):
    for f in fs: files.append(os.path.relpath(os.path.join(r,f),base))
files.sort(key=lambda f:(f!='[Content_Types].xml',f))
os.makedirs('src2',exist_ok=True)
for k,d in V.items():
    o=zipfile.ZipFile(f'src2/{k}.docx','w',zipfile.ZIP_DEFLATED)
    for f in files: o.writestr(f, d.encode() if f=='word/document.xml' else open(os.path.join(base,f),'rb').read())
    o.close()