# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, collections, itertools
rows=json.load(open('/tmp/justify4_eval.json'))+json.load(open('/tmp/justify3_eval.json'))
size={'Calibri':11,'Calibri14':14,'Times New Roman':11,'Times12':12}
g=collections.defaultdict(list)
for r in rows: g[(r['face'],r['last'])].append(r)
cons=[]
for k,rs in g.items():
    sz=size.get(k[0], rs[0]['size']); w=rs[0]['last_w']; sp=rs[0]['space']
    mk=max((r['over'] for r in rs if r['kept']), default=None); mw=min((r['over'] for r in rs if not r['kept']), default=None)
    if mw is None: continue  # share-bound hit, uninformative upper
    cons.append((k, w, sp, sz, mk if mk is not None else 0.0, mw))
print(len(cons),'constraints')
def feasible(f):
    bad=[c for c in cons if not (c[4] <= f(c) < c[5])]
    return bad
import numpy as np
best=None; feas=[]
for a in np.arange(0.30,0.40,0.0025):
    for b in np.arange(0.0,0.6,0.01):
        bad=feasible(lambda c: a*c[1]+b*c[2])
        if not bad: feas.append((round(a,4),round(b,3)))
print('a*w + b*space feasible:', feas[:40], len(feas))
feas2=[]
for a in np.arange(0.30,0.40,0.0025):
    for b in np.arange(0.0,0.15,0.0025):
        if not feasible(lambda c: a*c[1]+b*c[3]): feas2.append((round(a,4),round(b,4)))
print('a*w + b*size feasible:', feas2[:40], len(feas2))
feas3=[]
for a in np.arange(0.30,0.40,0.0025):
    for b in np.arange(0.0,2.0,0.05):
        if not feasible(lambda c: a*c[1]+b): feas3.append((round(a,4),round(b,3)))
print('a*w + const feasible:', feas3[:40], len(feas3))
# single-parameter forms
for name,f in [('(w+space)/3',lambda c:(c[1]+c[2])/3),('(w+2sp)/3',lambda c:(c[1]+2*c[2])/3),('0.35w+0.29sp',lambda c:0.35*c[1]+0.29*c[2]),('(w+space)*0.35',lambda c:(c[1]+c[2])*0.35),('(w+0.8sp)*0.35',lambda c:(c[1]+0.8*c[2])*0.35),('0.35w+0.3sp',lambda c:0.35*c[1]+0.3*c[2]),('(w+sp)*7/20',lambda c:(c[1]+c[2])*0.35)]:
    bad=feasible(f); print(f'{name:16} violations {len(bad)}', [(c[0][0][:3],c[0][1],round(f(c),2),c[4],c[5]) for c in bad][:4])