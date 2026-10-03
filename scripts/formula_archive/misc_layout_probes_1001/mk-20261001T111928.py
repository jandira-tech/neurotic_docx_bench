# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
from mkbase import mk
def p(text, before=0, after=0, ctx=False):
    c='<w:contextualSpacing/>' if ctx else ''
    return f'<w:p><w:pPr><w:spacing w:before="{before*20}" w:after="{after*20}" w:line="240" w:lineRule="auto"/>{c}</w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'
cases={
 # A ctx, B plain
 'c1': p('A',0,20,True)+p('B',6,0,False),
 'c2': p('A',0,6,True)+p('B',20,0,False),
 # A plain, B ctx
 'c3': p('A',0,20,False)+p('B',6,0,True),
 'c4': p('A',0,6,False)+p('B',20,0,True),
 # both ctx
 'c5': p('A',0,20,True)+p('B',6,0,True),
 # neither
 'c6': p('A',0,20,False)+p('B',6,0,False),
}
for k,v in cases.items(): mk(f'src/{k}.docx',v,15)