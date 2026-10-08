# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, json, glob, os
m=json.load(open('/tmp/oracle30/map.json'))
def lines(pdf, pno):
    out=[]
    for b in pdf[pno].get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            s=l['spans'][0]; t=''.join(sp['text'] for sp in l['spans']).strip()
            if t: out.append((round(s['origin'][1],2), round(s['origin'][0],2), t[:30]))
    out.sort(); return out
same=diff=0
for name,src in sorted(m.items()):
    today=f'/tmp/oracle30/pdf/{name}.pdf'
    if not os.path.exists(today): print(name,'NO PDF today', os.path.basename(src)[:50]); continue
    state=src.split('/')[-3]; stem=os.path.basename(src)[:-5]
    ref=glob.glob(f'{os.path.dirname(os.path.dirname(src))}/pdf/{stem}*.pdf')
    if not ref: print(name,'no corpus pdf'); continue
    a=fitz.open(today); b=fitz.open(ref[0])
    first=None; maxd=0.0
    for pno in range(min(a.page_count,b.page_count)):
        la=lines(a,pno); lb=lines(b,pno)
        for i,(x,y) in enumerate(zip(la,lb)):
            d=abs(x[0]-y[0])
            if x[2]!=y[2] or d>0.5:
                first=first or (pno+1,i+1,x,y)
            maxd=max(maxd,d) if x[2]==y[2] else maxd
        if len(la)!=len(lb): first=first or (pno+1,'count',len(la),len(lb))
    tag='SAME' if first is None and a.page_count==b.page_count else 'DIFF'
    if tag=='SAME': same+=1
    else: diff+=1
    print(f'{name} {tag} pages today {a.page_count} ref {b.page_count} maxd {maxd:.2f} first {first} {state[:12]} {stem[:28]}')
print('same',same,'diff',diff)