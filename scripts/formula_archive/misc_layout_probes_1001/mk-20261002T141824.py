# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
def r(t, sz=24):
    return f'<w:r><w:rPr><w:rFonts w:ascii="MS Mincho" w:hAnsi="MS Mincho" w:eastAsia="MS Mincho" w:hint="eastAsia"/><w:sz w:val="{sz}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>'
def p(label, t, jc=None):
    j=f'<w:jc w:val="{jc}"/>' if jc else ''
    return f'<w:p><w:pPr><w:spacing w:after="120"/>{j}</w:pPr>{r(label)}{r(t)}</w:p>'
lines=[
 ('A','あ、い。う「え」お（か）き・く'),
 ('B','あ」「い。」う）（え、「お'),
 ('C','「あいう」'),
 ('D','あ　い　　う'),
 ('E','かなカナひらがなカタカナ'),
]
long='日本語の文章、「括弧」と（丸括弧）が、句読点。を含む長い行を両端揃えで折り返すための文。'*3
for name,ctl in [('nc','doNotCompress'),('cp','compressPunctuation'),('ck','compressPunctuationAndJapaneseKana')]:
    L=[p(a,t) for a,t in lines]+[p('J',long,'both'),p('K',long,'left')]
    settings=f'<w:characterSpacingControl w:val="{ctl}"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
    subprocess.run(['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py',f'src/{name}.docx',''.join(L),'--compat','15','--settings',settings],check=True)