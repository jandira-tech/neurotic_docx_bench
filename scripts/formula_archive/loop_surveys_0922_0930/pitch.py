# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pymupdf, pathlib, collections, statistics, json, sys
G=pathlib.Path('/Users/arthrod/temp/T/neurotic_docx_bench/grok_run')
J=pathlib.Path('/Users/arthrod/.claude/jobs/a44a16de/tmp/all_cur')
stems=[l.strip() for l in open('/Users/arthrod/temp/T/jubarte-loop/all500.txt') if l.strip()]
def lines(f):
    try: d=pymupdf.open(f)
    except Exception: return []
    out=[]
    for pi,p in enumerate(d):
        if pi>2: break
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                sp=l['spans']
                t=''.join(s['text'] for s in sp).strip()
                if len(t)<8: continue
                out.append((pi, sp[0]['origin'][1], t[:24], sp[0]['font'].split('+')[-1].split(',')[0].split('-')[0], round(sp[0]['size'])))
    return out
agg=collections.defaultdict(list)
for s in stems:
    w=lines(G/'fixtures_500_pdf'/f'{s}.pdf'); j=lines(J/f'{s}.pdf')
    jm={}
    for x in j: jm.setdefault((x[0],x[2]),x)
    # consecutive matched pairs on same page: compare pitch
    prev=None
    for x in w:
        y=jm.get((x[0],x[2]))
        if y and prev and prev[0][0]==x[0] and prev[0][3]==x[3] and prev[0][4]==x[4]:
            wp=x[1]-prev[0][1]; jp=y[1]-prev[1][1]
            if 3<wp<60 and 3<jp<60:
                agg[(x[3],x[4])].append((jp/wp, s[:8]))
        prev=(x,y) if y else None
rows=[]
for k,v in agg.items():
    if len(v)<15: continue
    r=[a for a,_ in v]
    files=len(set(b for _,b in v))
    rows.append((statistics.median(r), k, len(v), files))
rows.sort()
for r in rows[:15]+rows[-15:]: print(round(r[0],3), r[1], r[2], 'files',r[3])