# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, collections
import numpy as np
m3={r['id']:r for r in json.load(open('/Users/arthrod/temp/T/grok_run_archive/justify3_1003/docx/manifest.json'))}
m4={r['id']:r for r in json.load(open('/Users/arthrod/temp/T/grok_run_archive/justify4_1003/docx/manifest.json'))}
rows=[]
for r in json.load(open('/tmp/justify4_eval.json')): r['size']=m4[r['id']]['size']; rows.append(r)
for r in json.load(open('/tmp/justify3_eval.json')): r['size']=m3[r['id']]['size']; r['face']=r['face']+'@3'; rows.append(r)
g=collections.defaultdict(list)
for r in rows: g[(r['face'],r['last'])].append(r)
cons=[]
for k,rs in g.items():
    w=rs[0]['last_w']; sp=rs[0]['space']; sz=rs[0]['size']
    mk=max((r['over'] for r in rs if r['kept']), default=0.0); mw=min((r['over'] for r in rs if not r['kept']), default=None)
    if mw is None: continue
    cons.append((k, w, sp, sz, mk, mw))
print(len(cons),'constraints')
def bad(f): return [c for c in cons if not (c[4] <= f(c) < c[5])]
for label,grid,f in [('a*w+b*space',(np.arange(0.30,0.40,0.0025),np.arange(0.0,0.6,0.01)),lambda a,b:(lambda c:a*c[1]+b*c[2])),
                     ('a*w+b*size',(np.arange(0.30,0.40,0.0025),np.arange(0.0,0.15,0.0025)),lambda a,b:(lambda c:a*c[1]+b*c[3])),
                     ('a*w+const',(np.arange(0.30,0.40,0.0025),np.arange(0.0,2.0,0.05)),lambda a,b:(lambda c:a*c[1]+b))]:
    feas=[(round(a,4),round(b,4)) for a in grid[0] for b in grid[1] if not bad(f(a,b))]
    print(label,'feasible',len(feas), feas[:12], '...', feas[-6:])
for name,f in [('(w+space)/3',lambda c:(c[1]+c[2])/3),('(w+2sp)/3',lambda c:(c[1]+2*c[2])/3),('0.35w+0.29sp',lambda c:0.35*c[1]+0.29*c[2]),('(w+sp)*0.35',lambda c:(c[1]+c[2])*0.35),('0.35w+0.3sp',lambda c:0.35*c[1]+0.3*c[2]),('0.35w+0.75',lambda c:0.35*c[1]+0.75)]:
    b=bad(f); print(f'{name:14} violations {len(b)}', [(c[0][0][:4],c[0][1],round(f(c),2),c[4],c[5]) for c in b][:5])