# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, zipfile
from fontTools.ttLib import TTFont
F={'Times New Roman':'/System/Library/Fonts/Supplemental/Times New Roman.ttf','Calibri':'/Applications/Microsoft Word.app/Contents/Resources/DFonts/Calibri.ttf',
   'Arial':'/System/Library/Fonts/Supplemental/Arial.ttf','Courier New':'/System/Library/Fonts/Supplemental/Courier New.ttf',
   'Georgia':'/System/Library/Fonts/Supplemental/Georgia.ttf','Verdana':'/System/Library/Fonts/Supplemental/Verdana.ttf'}
W=468.0; SZ=12.0
cases=[]; body=''
for name,path in F.items():
    f=TTFont(path); cm=f.getBestCmap(); hm=f['hmtx']; upm=f['head'].unitsPerEm
    adv=lambda s: sum(hm[cm[ord(c)]][0] for c in s)*SZ/upm
    sp=adv(' '); i=adv('i')
    K=int(0.8*W/adv('ab '))
    base=adv('ab '*K)+adv(' tail')
    # overflow(j) = base + j*i - W ; sweep from -2pt to 0.5*(K+1)*sp
    j0=max(0,int((W-base-2)/i)); j1=int((W-base+0.5*(K+1)*sp)/i)+1
    step=max(1,(j1-j0)//28)
    for j in range(j0,j1+1,step):
        ov=base+j*i-W
        cases.append(dict(font=name,K=K,j=j,ov=round(ov,3),sp=round(sp,4),spaces=K+1,em=SZ))
        rpr=f'<w:rPr><w:rFonts w:ascii="{name}" w:hAnsi="{name}"/><w:sz w:val="24"/></w:rPr>'
        body+=f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r>{rpr}<w:t xml:space="preserve">{"ab "*K}{"i"*j} tail</w:t></w:r></w:p>'
json.dump(cases,open('cases.json','w'))
def mk(path,csc):
    z=zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/_rels/document.xml.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdSet" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>')
    z.writestr('word/document.xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+body+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="720" w:right="1440" w:bottom="720" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    z.writestr('word/settings.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:characterSpacingControl w:val="{csc}"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"/></w:compat></w:settings>')
    z.close()
mk('src/fonts_cp.docx','compressPunctuation'); mk('src/fonts_dnc.docx','doNotCompress')
print(len(cases))