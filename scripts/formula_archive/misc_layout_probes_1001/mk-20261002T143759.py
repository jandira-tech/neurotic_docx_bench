# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, ea=None, ascii='Times New Roman', sz=24):
    f=f'<w:rFonts w:ascii="{ascii}" w:hAnsi="{ascii}"' + (f' w:eastAsia="{ea}"' if ea else '') + '/>'
    return f'<w:r><w:rPr>{f}<w:sz w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(label, runs):
    return f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>{r(label+" ")}{"".join(runs)}</w:p>'
L=[
 p('L1',[r('a  b  c','PrbNine','Arial',24)]),   # Arial absent, Gothic@12
 p('L2',[r('a  b  c','PrbNine','Times New Roman',28)]),   # TNR absent, Gothic@14
 p('L3',[r('a  b  c','PrbNine','Arial',32)]),   # Arial absent, Mincho@16
 p('L4',[r('a  b  c','PrbNine','Arial',40)]),   # Arial absent, Gothic@20 + Mincho@20
 p('L5',[r('a  b  c','PrbNine','Times New Roman',40)]),
 p('G1',[r('x  y','MS Gothic','Arial',24)]),
 p('G2',[r('x  y','MS Gothic','Arial',28)]),
 p('M3',[r('x  y','MS Mincho','Times New Roman',32)]),
 p('G4',[r('x  y','MS Gothic','Arial',40)]),
 p('M4',[r('x  y','MS Mincho','Times New Roman',40)]),
]
settings='<w:compat><w:balanceSingleByteDoubleByteWidth/><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py','src/pair.docx',''.join(L),'--compat','15','--settings',settings],check=True)