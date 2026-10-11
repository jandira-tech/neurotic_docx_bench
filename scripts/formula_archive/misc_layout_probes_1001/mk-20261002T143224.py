# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, ea=None, lang=None, sz=24):
    f='<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"' + (f' w:eastAsia="{ea}"' if ea else '') + '/>'
    l=f'<w:lang w:eastAsia="{lang}"/>' if lang else ''
    return f'<w:r><w:rPr>{f}<w:sz w:val="{sz}"/>{l}</w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(label, runs):
    return f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>{r(label+" ")}{"".join(runs)}</w:p>'
V=[('V1','Times New Roman',None),('V2',None,'en-US'),('V3','MS Mincho','en-US'),('V4',None,None),('V5','Arial',None),('V6','Times New Roman','en-AU'),('V7','MS Mincho',None),('V8','PrbSix',None),('V9','PrbSix','en-US'),('VA',None,'ja-JP'),('VB','Times New Roman','ja-JP')]
L=[p(n,[r('a  b  c  d',ea,lang)]) for n,ea,lang in V]
settings='<w:compat><w:balanceSingleByteDoubleByteWidth/><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py','src/lang.docx',''.join(L),'--compat','15','--settings',settings],check=True)