# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,os
base='x'
doc=open('x/word/document.xml',encoding='utf-8').read()
old='<w:del w:id="216" w:author="Author" w:date="2026-06-29T11:25:00Z" w16du:dateUtc="2026-06-29T15:25:00Z"><w:r><w:delText>R2C1</w:delText></w:r><w:r><w:delText>thiscellhassomewidecontent</w:delText></w:r></w:del>'
assert doc.count(old)==1
V={'w0_ctrl':doc,
 'w1_plain2runs':doc.replace(old,'<w:r><w:t>R2C1</w:t></w:r><w:r><w:t>thiscellhassomewidecontent</w:t></w:r>'),
 'w2_del1run':doc.replace(old,old.replace('R2C1</w:delText></w:r><w:r><w:delText>','R2C1')),
 'w3_plain1run':doc.replace(old,'<w:r><w:t>R2C1thiscellhassomewidecontent</w:t></w:r>'),
}
files=[]
for r,_,fs in os.walk(base):
    for f in fs: files.append(os.path.relpath(os.path.join(r,f),base))
files.sort(key=lambda f:(f!='[Content_Types].xml',f))
for k,d in V.items():
    o=zipfile.ZipFile(f'src/{k}.docx','w',zipfile.ZIP_DEFLATED)
    for f in files:
        o.writestr(f, d.encode() if f=='word/document.xml' else open(os.path.join(base,f),'rb').read())
    o.close()