# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob, os, zipfile, json, sys, collections
sample=open('/tmp/pdf-300/list.txt').read().split()
ids=sys.argv[1:] or ['0f4baf4982','4ee88e44b6','d47fd711cd','ff8d102eb8','75252a6bb0','115a9fa36c','bd962090cd','468d82c575','f6b4dee45a','636ef078e7','936c03fb11','5ad6e6d44f','527ec4ed07','a4c38b1bf5','4910ce2060','2bd19faf20','ef910057dc','ed36b607e8','cc8a672efd','f23fc5de2e']
accepted=[]; rejected=[]
for i in ids:
    pdfs=glob.glob(f'/tmp/pdf-300/work/oracle/*{i}*')
    if not pdfs: continue
    doc=fitz.open(pdfs[0])
    # natural space width per (font,size): the minimum space char width seen
    spw={}
    pages=[]
    for p in doc:
        lines=[]
        for b in p.get_text('rawdict')['blocks']:
            for l in b.get('lines',[]):
                chars=[(c,s) for s in l['spans'] for c in s['chars']]
                if not chars: continue
                for c,s in chars:
                    if c['c']==' ':
                        k=(s['font'],round(s['size'],1)); w=c['bbox'][2]-c['bbox'][0]
                        if w>0.3: spw[k]=min(spw.get(k,99),w)
                lines.append((l['bbox'], chars))
        pages.append(lines)
    for lines in pages:
        if not lines: continue
        # body lines only (left half start), estimate the right margin as the most common rounded x1 among lines reaching far right
        x1s=collections.Counter(round(bb[2],0) for bb,ch in lines if bb[2]-bb[0]>200)
        if not x1s: continue
        margin=max(k for k,v in x1s.items() if v>=max(2, 0.2*max(x1s.values())))
        lines.sort(key=lambda t:(round(t[0][1]),t[0][0]))
        for idx,(bb,chars) in enumerate(lines):
            txt=''.join(c['c'] for c,s in chars)
            stripped=txt.rstrip(' ')
            if len(stripped)<30: continue
            core=[(c,s) for c,s in chars][:len(stripped)]
            spaces=[(c,s) for c,s in core if c['c']==' ']
            if len(spaces)<3: continue
            words=[(c,s) for c,s in core if c['c']!=' ']
            natural=sum(c['bbox'][2]-c['bbox'][0] for c,s in words)+sum(spw.get((s['font'],round(s['size'],1)),3.0) for c,s in spaces)
            x0=core[0][0]['bbox'][0]; xend=core[-1][0]['bbox'][2]
            measure=margin-x0
            full = abs(xend-margin)<0.6
            if not full: continue
            nsp=len(spaces); spn=sum(spw.get((s['font'],round(s['size'],1)),3.0) for c,s in spaces)/nsp
            over=natural-measure
            if over>0.05:
                accepted.append((round(over/(nsp*spn),3), round(over,2), nsp, i))
            # the next line's first word, if it belongs to the same paragraph (same x0 and not indented)
            if idx+1<len(lines):
                nb,nch=lines[idx+1]
                if abs(nb[0]-x0)<0.6 and abs(nb[1]-bb[1])<30:
                    nt=''.join(c['c'] for c,s in nch); first=nt.split(' ')[0]
                    if first and nch:
                        fw=sum(c['bbox'][2]-c['bbox'][0] for c,s in nch[:len(first)])
                        need=natural+spn+fw-measure
                        if need>0.05:
                            rejected.append((round(need/((nsp+1)*spn),3), round(need,2), nsp+1, i))
accepted.sort(); rejected.sort()
print('accepted squeezes (share of space width):', len(accepted), 'max', accepted[-5:] if accepted else None)
print('rejected (would-be) squeezes:', len(rejected), 'min', rejected[:8])
print('accepted distribution', collections.Counter(round(a[0],1) for a in accepted).most_common(8))