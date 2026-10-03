# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
def doc(name, ea='Times New Roman', tfl='', lang='', text='日時：8月21日土曜日　雨天決行', bold=True, hint=True):
    rpr=f'<w:rFonts w:ascii="Verdana" w:eastAsia="{ea}" w:hAnsi="Verdana"{" w:hint=\"eastAsia\"" if hint else ""}/>'+('<w:b/>' if bold else '')+'<w:sz w:val="36"/>'+(f'<w:lang w:eastAsia="{lang}"/>' if lang else '')
    paras=''.join(f'<w:p><w:r><w:rPr>{rpr}</w:rPr><w:t>{text}</w:t></w:r></w:p>' for _ in range(3))
    body=paras+'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1417" w:right="1417" w:bottom="1417" w:left="1417" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
    st=f'<w:themeFontLang w:val="en-US" w:eastAsia="{tfl}"/>' if tfl else ''
    z=zipfile.ZipFile(f'src/{name}.docx','w',zipfile.ZIP_DEFLATED)
    z.writestr('[Content_Types].xml','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/></Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    z.writestr('word/_rels/document.xml.rels','<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/></Relationships>')
    z.writestr('word/settings.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings xmlns:w="{W}">{st}<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="12"/></w:compat></w:settings>')
    z.writestr('word/document.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>')
    z.close()
doc('f1_tfl_ja','Times New Roman','ja-JP')
doc('f2_no_tfl','Times New Roman')
doc('f3_tfl_ja_lang_tr','Times New Roman','ja-JP','tr-TR')
doc('f4_tfl_zh','Times New Roman','zh-CN')
doc('f5_lang_ja','Times New Roman','','ja-JP')
doc('f6_ea_verdana_tfl_ja','Verdana','ja-JP')
doc('f7_kanji_only_no_tfl','Times New Roman',text='日時土曜日雨天決行')
doc('f8_regular_no_tfl','Times New Roman',bold=False)
doc('f9_nohint_no_tfl','Times New Roman',hint=False)
doc('f10_lang_zh','Times New Roman','','zh-CN')