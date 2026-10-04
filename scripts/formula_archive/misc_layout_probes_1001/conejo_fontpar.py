# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""fontpar.py WORD_DIR JUB_DIR stems... : base-font char counts, Word vs jubarte, per doc"""
import sys,fitz,collections,re
def fonts(p):
    c=collections.Counter()
    try: d=fitz.open(p)
    except Exception: return None
    for pg in d:
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']:
                    f=re.sub(r'^[A-Z]{6}\+','',s['font']).split('-')[0].replace('PSMT','').replace('MT','').replace('PS','')
                    c[f]+=len(s['text'].strip())
    return c
wd,jd=sys.argv[1],sys.argv[2]
for st in sys.argv[3:]:
    w,j=fonts(f'{wd}/{st}.pdf'),fonts(f'{jd}/{st}.pdf')
    if w is None or j is None: print('MISSING',st); continue
    tw,tj=sum(w.values()) or 1,sum(j.values()) or 1
    keys=set(k for k,v in w.items() if v/tw>0.02)|set(k for k,v in j.items() if v/tj>0.02)
    diff=[(k,round(100*w[k]/tw),round(100*j[k]/tj)) for k in sorted(keys) if abs(w[k]/tw-j[k]/tj)>0.05]
    if diff: print(st[:60],diff)