# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, ascii, ea, sz):
    f=f'<w:rFonts w:ascii="{ascii}" w:hAnsi="{ascii}"' + (f' w:eastAsia="{ea}"' if ea else '') + '/>'
    return f'<w:r><w:rPr>{f}<w:sz w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
L=[]
for ascii,ea in [('Times New Roman',None),('Calibri',None),('Arial',None),('Times New Roman','MS Mincho'),('Calibri','MS Gothic')]:
    for sz in (16,20,22,24,28,32,40):
        lab=f'{ascii[:3]}{(ea or "-")[:4]}{sz}'.replace(' ','')
        L.append(f'<w:p><w:pPr><w:spacing w:after="0"/></w:pPr>{r(lab+" x", ascii, ea, sz)}{r("  y    z", ascii, ea, sz)}</w:p>')
settings='<w:compat><w:balanceSingleByteDoubleByteWidth/><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py','src/sw.docx',''.join(L),'--compat','15','--settings',settings],check=True)