# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, sz=24, ascii='MS Mincho'):
    return f'<w:r><w:rPr><w:rFonts w:ascii="{ascii}" w:hAnsi="{ascii}" w:eastAsia="MS Mincho" w:hint="eastAsia"/><w:sz w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(label, runs):
    return f'<w:p><w:pPr><w:spacing w:after="120"/></w:pPr>{r(label)}{"".join(runs)}</w:p>'
L=[
 p('A',[r('あ」（い）「う』【え】『お〕〔か》《き〉〈く］［け｝｛こ')]),
 p('B',[r('あ」）い）」う。「え、（お」。か）、き・「く！（け？「こ')]),
 p('C',[r('あ」'),r('「い）'),r('（う')]),
 p('D',[r('あ」「い', ascii='Times New Roman')]),
 p('E',[r('あ「「い」」う（（え））お')]),
 p('F',[r('あ“”い‘’う')]),
]
settings='<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py','src/pairs.docx',''.join(L),'--compat','15','--settings',settings],check=True)