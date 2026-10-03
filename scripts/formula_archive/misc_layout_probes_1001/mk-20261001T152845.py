# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile
W='xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
def body(rpr):
    out=''
    for j in range(20,46):
        txt='ab '*30+'i'*j+' tail'
        out+=f'<w:p><w:pPr><w:spacing w:after="0"/><w:jc w:val="both"/></w:pPr><w:r><w:rPr>{rpr}<w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{txt}</w:t></w:r></w:p>'
    return out
def mk(name, rpr, styles, csc='compressPunctuation'):
    z=zipfile.ZipFile(f'src/{name}.docx','w',zipfile.ZIP_DEFLATED)
    ov='<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' if styles else ''
    z.writestr('[Content_Types].xml',f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>{ov}</Types>')
    z.writestr('_rels/.rels','<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
    sr='<Relationship Id="rIdSty" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' if styles else ''
    z.writestr('word/_rels/document.xml.rels',f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdSet" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>{sr}</Relationships>')
    z.writestr('word/document.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>'+body(rpr)+'<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="720" w:right="1440" w:bottom="720" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr></w:body></w:document>')
    z.writestr('word/settings.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:settings {W}><w:characterSpacingControl w:val="{csc}"/><w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="14"/></w:compat></w:settings>')
    if styles: z.writestr('word/styles.xml',f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles {W}>{styles}<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style></w:styles>')
    z.close()
TNR='<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
def dd(r): return f'<w:docDefaults><w:rPrDefault><w:rPr>{r}</w:rPr></w:rPrDefault></w:docDefaults>'
mk('a_run_tnr', TNR, None); mk('a_run_tnr_dnc', TNR, None, 'doNotCompress')
mk('b_dd_tnr', '', dd('<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'))
mk('c_dd_tnr_ea', '', dd('<w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>'))
mk('d_dd_tnr_lang', '', dd('<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/><w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/>'))
mk('e_dd_full', '', dd('<w:rFonts w:ascii="Times New Roman" w:eastAsia="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/><w:sz w:val="24"/><w:szCs w:val="24"/><w:lang w:val="en-US" w:eastAsia="en-US" w:bidi="ar-SA"/>'))
mk('f_run_tnr_emptystyles', TNR, '<w:docDefaults/>')