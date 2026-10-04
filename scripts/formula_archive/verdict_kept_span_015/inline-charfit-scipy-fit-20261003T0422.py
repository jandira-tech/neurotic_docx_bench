# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, numpy as np
from scipy.optimize import minimize
rows=json.load(open('/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes/charfit_rows.json'))
y=np.array([1.0 if r['verdict']=='word-level' else -1.0 for r in rows])
def feats(r, kind):
    kc=r['kept_c']/r['Lc']; kcs=r['kept_c_sp']/r['Lc']; kw=r['kept_w']/r['Lw']
    R=r['R']; Lc=r['Lc']; Lw=r['Lw']
    return {
      'kc,R,Lc':      [kc, R/100, Lc/1000, 1],
      'kc,R/L,Lc':    [kc, R/Lw, Lc/1000, 1],
      'kc,R,log L':   [kc, R/100, np.log(Lc), 1],
      'kc,R':         [kc, R/100, 1],
      'kc,Lc':        [kc, Lc/1000, 1],
      'kcs,R,Lc':     [kcs, R/100, Lc/1000, 1],
      'kw,R,Lw':      [kw, R/100, Lw/1000, 1],
      'kc,R·L':       [kc, R*Lc/1e5, 1],
      'kc,R,Lc,R·L':  [kc, R/100, Lc/1000, R*Lc/1e5, 1],
    }[kind]
for kind in ['kc,R,Lc','kc,R/L,Lc','kc,R,log L','kc,R','kc,Lc','kcs,R,Lc','kw,R,Lw','kc,R·L','kc,R,Lc,R·L']:
    X=np.array([feats(r,kind) for r in rows])
    def loss(w): 
        m=y*(X@w); return np.sum(np.maximum(0,1-m))+1e-4*np.sum(w[:-1]**2)
    best=None
    rng=np.random.default_rng(0)
    for s in range(12):
        w0=rng.normal(size=X.shape[1])*5; w0[0]=abs(w0[0])*10
        res=minimize(loss,w0,method='Nelder-Mead',options={'maxiter':20000,'xatol':1e-6,'fatol':1e-6})
        acc=np.mean(np.sign(X@res.x)==y)
        if best is None or acc>best[0] or (acc==best[0] and res.fun<best[1]): best=(acc,res.fun,res.x)
    acc,_,w=best
    w=w/abs(w[0])  # normalize: kept-fraction coefficient = 1
    print(f"{kind:14} acc={acc:.3f}  rule: kept_frac ≥ " + " + ".join(f"{-c:+.4f}·{n}" for c,n in zip(w[1:], kind.split(',')[1:]+['1'])).replace('+ -','- '))