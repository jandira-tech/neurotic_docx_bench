# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, ea=None, ascii='Times New Roman', sz=24, hint=None):
    f=f'<w:rFonts w:ascii="{ascii}" w:hAnsi="{ascii}"' + (f' w:eastAsia="{ea}"' if ea else '') + (f' w:hint="{hint}"' if hint else '') + '/>'
    return f'<w:r><w:rPr>{f}<w:sz w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(label, runs, jc=None):
    j=f'<w:jc w:val="{jc}"/>' if jc else ''
    return f'<w:p><w:pPr><w:spacing w:after="120"/>{j}</w:pPr>{r(label+" ")}{"".join(runs)}</w:p>'
def body(fake):
    L=[]
    L.append(p('L1', [r('a b|c  d|e   f', fake)]))
    L.append(p('L2', [r('a b|c  d|e   f', None, 'Calibri')]))
    L.append(p('L3', [r('a ', fake), r(' d', fake)]))
    L.append(p('L4', [r('a', fake), r('  ', fake), r('d', fake), r(' ', fake), r('f', fake)]))
    L.append(p('L5', [r('a b|c  d|e   f', 'MS Mincho')]))
    L.append(p('L6', [r('a b|c  d|e   f', fake, sz=28)]))
    L.append(p('L7', [r('中 文|中  文', 'MS Mincho', hint='eastAsia')]))
    L.append(p('L8', [r('a b|c  d|e   f ' + 'filler words to make this line long enough to wrap across the measure so justification applies here ok', fake)], jc='both'))
    L.append(p('L9', [r('a  b|c  d', fake)]))
    return ''.join(L)
ST=('<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">')
for name,fake,compat,flag in [('v1_flag15','PrbKaiQ1',15,True),('v2_noflag15','PrbKaiQ2',15,False),('v3_flag12','PrbKaiQ3',12,True)]:
    settings='<w:compat>'+('<w:balanceSingleByteDoubleByteWidth/>' if flag else '')+f'<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="{compat}"/></w:compat>'
    subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py',f'src/{name}.docx',body(fake),'--compat',str(compat),'--settings',settings],check=True)