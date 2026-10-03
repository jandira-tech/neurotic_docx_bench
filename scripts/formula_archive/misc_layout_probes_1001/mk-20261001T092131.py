# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys; sys.path.insert(0,'/tmp/conejo'); from mkp import mk
F='<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/>'
def r(t,sz): return f'<w:r><w:rPr>{F}<w:sz w:val="{sz}"/></w:rPr><w:t>{t}</w:t></w:r>'
def br(sz): return f'<w:r><w:rPr>{F}<w:sz w:val="{sz}"/></w:rPr><w:br/></w:r>'
P='<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
def p(x): return f'<w:p>{P}{x}</w:p>'
cases={'bra':r('Top',22)+br(40)+r('Bottom',22),
       'brb':r('Top',22)+br(22)+br(40)+r('Bottom',22),
       'brc':r('Top',56)+br(72)+r('Bottom',32),
       'brd':r('Top',22)+br(22)+r('Bottom',22)}
for k,v in cases.items(): mk(f'{k}.docx', p(v)+p(r('End',22)))