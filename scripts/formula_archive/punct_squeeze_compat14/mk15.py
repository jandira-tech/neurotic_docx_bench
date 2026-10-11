# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('mk3.py').read().split("cx='<w:compat")[0])
import os,re
os.makedirs('src15',exist_ok=True)
cx='<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"/>'
CSC='<w:characterSpacingControl w:val="compressPunctuation"/>'
DNC='<w:characterSpacingControl w:val="doNotCompress"/>'
n=[0]
def dele(m):
    n[0]+=1; t=m.group(0).replace('<w:t ','<w:delText ').replace('</w:t>','</w:delText>')
    return f'<w:del w:id="{n[0]}" w:author="A" w:date="2026-01-01T00:00:00Z">{t}</w:del>'
for jc in ('left','both'):
    base=sq(jc)
    d=re.sub(r'<w:r>.*?</w:r>',dele,base)
    mk2(f'src15/del_{jc}_cp.docx',d,cx,CSC); mk2(f'src15/del_{jc}_dnc.docx',d,cx,DNC)
# 11pt: scale the sweep
def sq11(jc):
    out=''
    for j in range(20,46):
        txt='ab '*30+'i'*j+' tail'
        out+=f'<w:p><w:pPr><w:spacing w:after="0"/><w:jc w:val="{jc}"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{txt}</w:t></w:r></w:p>'
    return out
mk2('src15/s11_both_cp.docx',sq11('both'),cx,CSC); mk2('src15/s11_both_dnc.docx',sq11('both'),cx,DNC)