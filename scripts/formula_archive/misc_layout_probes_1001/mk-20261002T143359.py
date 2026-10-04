# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import subprocess
NS='xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
def styles(dd):
    return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {NS}><w:docDefaults><w:rPrDefault><w:rPr>{dd}</w:rPr></w:rPrDefault><w:pPrDefault/></w:docDefaults><w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>'
body=''.join(f'<w:p><w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:sz w:val="24"/></w:rPr><w:t xml:space="preserve">W{c}  b  c  d</w:t></w:r></w:p>' for c in 'a')
st='<w:compat><w:balanceSingleByteDoubleByteWidth/><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
V={
 'm0':None,
 'm1':open('six/word/styles.xml').read(),
 'm2':styles('<w:lang w:val="en-AU" w:eastAsia="en-AU" w:bidi="ar-SA"/>'),
 'm3':styles('<w:lang w:val="en-AU" w:eastAsia="ja-JP" w:bidi="ar-SA"/>'),
 'm4':styles(''),
 'm5':styles('<w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'),
 'm6':styles('<w:rFonts w:eastAsia="MS Mincho"/><w:lang w:val="en-AU" w:eastAsia="en-AU" w:bidi="ar-SA"/>'),
}
for n,sx in V.items():
    args=['python3','/Users/arthrod/temp/T/jubarte-loop/mkdocx.py',f'src/{n}.docx',body]
    if sx:
        open(f'{n}_styles.xml','w').write(sx); args.append(f'{n}_styles.xml')
    subprocess.run(args+['--compat','15','--settings',st],check=True)