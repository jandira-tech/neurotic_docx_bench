# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, ea=None, ascii='Times New Roman', sz=24):
    f=f'<w:rFonts w:ascii="{ascii}" w:hAnsi="{ascii}"' + (f' w:eastAsia="{ea}"' if ea else '') + '/>'
    return f'<w:r><w:rPr>{f}<w:sz w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(label, runs):
    return f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>{r(label+" ")}{"".join(runs)}</w:p>'
settings='<w:compat><w:balanceSingleByteDoubleByteWidth/><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
for name,extra in [('a',[]),('b',[('LM',[r('x  y','MS Mincho',sz=28)])]),('c',[('LG',[r('x  y','MS Gothic',sz=24)])]),('d',[('LK',[r('中  文','MS Mincho',sz=28)])])]:
    fake='PrbS4'+name
    L=[p(f'L{i}',[r('a  b  c  d',fake,sz=sz)]) for i,sz in enumerate([20,24,28])]
    L+= [p(l,rs) for l,rs in extra]
    subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py',f'src/{name}.docx',''.join(L),'--compat','15','--settings',settings],check=True)