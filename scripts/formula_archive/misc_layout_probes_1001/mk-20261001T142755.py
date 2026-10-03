# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,os,re
base='x'
doc=open('x/word/document.xml',encoding='utf-8').read()
sty=open('x/word/styles.xml',encoding='utf-8').read()
sp="<w:r w:rsidRPr=\"0045650A\"><w:rPr><w:bCs/></w:rPr><w:t xml:space=\"preserve\"> </w:t></w:r><w:r w:rsidRPr=\"0045650A\"><w:rPr><w:rFonts w:ascii=\"Times New Roman\" w:hAnsi=\"Times New Roman\" w:cs=\"Times New Roman\"/><w:bCs/><w:sz w:val=\"24\"/><w:szCs w:val=\"24\"/></w:rPr><w:t>gastro-</w:t></w:r>"
print(doc.count(sp))
V={'v0_ctrl':(doc,sty),
 'v1_noproof':(re.sub(r'<w:proofErr [^>]*/>','',doc),sty),
 'v2_tnrspace':(doc.replace(sp,sp.replace('<w:rPr><w:bCs/></w:rPr><w:t xml:space="preserve"> </w:t>','<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr><w:t xml:space="preserve"> </w:t>')),sty),
 'v3_nozh':(doc,sty.replace('w:eastAsia="zh-CN"','w:eastAsia="en-US"')),
}
files=[]
for r,_,fs in os.walk(base):
    for f in fs: files.append(os.path.relpath(os.path.join(r,f),base))
files.sort(key=lambda f:(f!='[Content_Types].xml',f))
for k,(d,s) in V.items():
    o=zipfile.ZipFile(f'src/{k}.docx','w',zipfile.ZIP_DEFLATED)
    for f in files:
        data = d.encode() if f=='word/document.xml' else s.encode() if f=='word/styles.xml' else open(os.path.join(base,f),'rb').read()
        o.writestr(f,data)
    o.close()