# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
exec(open('gen2.py').read().split("last1=auto_row")[0])
def doc3(own_ref, floating=True):
    tp = '<w:tblpPr w:leftFromText="180" w:rightFromText="180" w:vertAnchor="page" w:horzAnchor="margin" w:tblpY="1440"/>' if floating else ''
    tbl = f'<w:tbl><w:tblPr>{tp}<w:tblW w:w="9000" w:type="dxa"/></w:tblPr><w:tblGrid><w:gridCol w:w="9000"/></w:tblGrid>{rows(31)}{auto_row(["LastA"])}</w:tbl>'
    ref = '<w:footerReference w:type="default" r:id="rId30"/>'
    pg = '<w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/>'
    return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {W}><w:body>'
            f'<w:p><w:pPr><w:sectPr>{ref}{pg}</w:sectPr></w:pPr><w:r><w:t>First</w:t></w:r></w:p>'
            f'{tbl}<w:p><w:r><w:t>After</w:t></w:r></w:p>'
            f'<w:sectPr>{ref if own_ref else ""}{pg}</w:sectPr></w:body></w:document>')
for c in ('14','15'):
    mk(f'src3/h_own_c{c}.docx', doc3(True), FOOT['fa'], c)
    mk(f'src3/h_inh_c{c}.docx', doc3(False), FOOT['fa'], c)
    mk(f'src3/h_inhinl_c{c}.docx', doc3(False, False), FOOT['fa'], c)