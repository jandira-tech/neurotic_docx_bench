# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, ea=None, ascii='Times New Roman', sz=24):
    f=f'<w:rFonts w:ascii="{ascii}" w:hAnsi="{ascii}"' + (f' w:eastAsia="{ea}"' if ea else '') + '/>'
    return f'<w:r><w:rPr>{f}<w:sz w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(label, runs):
    return f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>{r(label+" ")}{"".join(runs)}</w:p>'
L=[]
for i,sz in enumerate([16,18,20,22,24,26,28,32,40,48]):
    L.append(p(f'L{i}', [r('a  b  c  d', 'PrbSzA', sz=sz)]))
for i,sz in enumerate([20,24,28,40]):
    L.append(p(f'LA{i}', [r('a  b  c  d', 'PrbSzB', 'Arial', sz=sz)]))
for i,sz in enumerate([20,24,28,40]):
    L.append(p(f'LC{i}', [r('a  b  c  d', 'MS Mincho', sz=sz)]))
for i,sz in enumerate([20,24,28,40]):
    L.append(p(f'LN{i}', [r('a  b  c  d', None, sz=sz)]))
settings='<w:compat><w:balanceSingleByteDoubleByteWidth/><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py','src/sz.docx',''.join(L),'--compat','15','--settings',settings],check=True)