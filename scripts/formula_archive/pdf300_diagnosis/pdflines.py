# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys, glob, fitz
key=sys.argv[1]; build=sys.argv[2]; pi=int(sys.argv[3]); a=int(sys.argv[4]); b=int(sys.argv[5])
state, stem = key.split('__',1)
W=fitz.open(glob.glob(f'/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word/{state}/pdf/{stem}*.pdf')[0])
O=fitz.open(glob.glob(f'/tmp/pdf-300/work-{build}/jubarte/candidate/{key}*.pdf')[0])
def lines(pg):
    out=[]
    for bl in pg.get_text('dict')['blocks']:
        for l in bl.get('lines',[]):
            t=''.join(s['text'] for s in l['spans']).strip()
            if t: out.append((round(l['bbox'][1],1), round(l['bbox'][0],1), round(l['bbox'][2],1), t, round(l['spans'][0]['size'],1), l['spans'][0]['font'][:14]))
    out.sort(); return out
for tag, doc in (('W', W), ('O', O)):
    ls = lines(doc[pi])
    print(f'{tag} page {pi+1}: {len(ls)} lines')
    for l in ls[a:b]:
        print(f'  {tag} {l[0]:>6} x{l[1]:>6}-{l[2]:>6} {l[4]} {l[5]} {l[3][:70]!r}')