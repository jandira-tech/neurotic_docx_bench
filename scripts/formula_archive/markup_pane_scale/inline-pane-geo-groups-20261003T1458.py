# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, math, collections
import numpy as np
val=json.load(open('/tmp/pane_val.json'))
geos={}
for o in val:
    key=(o['W'],o['H'],o['mr'])
    pane=o['pane']; kn=round((pane[3]-pane[1])/o['H']*300); top=round(pane[1]/0.24)
    geos.setdefault(key,collections.Counter())[(kn,top)]+=1
G=[]
for key,c in sorted(geos.items()):
    (kn,top),n=c.most_common(1)[0]
    if len(c)>1: print('geometry with several results', key, dict(c))
    G.append((key[0],key[1],key[2],kn,top,n))
print(len(G),'geometries'); 
for g in G: print(g)
R={'floor':lambda v: math.floor(v+1e-7),'round':lambda v: math.floor(v+0.5+1e-7),'ceil':lambda v: math.ceil(v-1e-7)}
best=[]
for a in np.arange(4.0,14.01,0.05):
    for b in np.arange(258.0,272.01,0.05):
        for kr in ('floor','round'):
            ks=[R[kr](300*(W-a)/(W-mr+b)) for W,H,mr,kn,top,n in G]
            if any(k!=kn for k,(W,H,mr,kn,top,n) in zip(ks,G)): continue
            for tr in ('floor','round','ceil'):
                for c in np.arange(-0.6,0.61,0.04):
                    ok=0; bad=[]
                    for W,H,mr,kn,top,n in G:
                        ke=(W-a)/(W-mr+b); t=R[tr]((H*(1-ke)/2+c)/0.24)
                        if t==top: ok+=1
                        else: bad.append((W,H,mr,t,top))
                    best.append((ok,round(a,2),round(b,2),kr,tr,round(c,2),bad))
best.sort(key=lambda b:-b[0])
print('best fits:')
for b in best[:8]: print(b[0],'/',len(G),b[1:6],b[6][:3])