# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import math, itertools
D=[(595.0,842.0,72.45,223,451),(595.3,841.9,72.0,223,452),(595.3,841.9,89.85,228,422),(612.0,792.0,54.0,219,443),(612.0,792.0,70.9,224,417),(612.0,792.0,72.0,224,416),(612.0,792.0,90.0,229,388)]
K=[(792.0,36.0,230)]  # landscape letter mr 36 -> 230 (engine doc comment)
def kfloor(W,mr,a,b): return math.floor(300*(W-a)/(W-mr+b)+1e-9)
sols=[]
import numpy as np
for a in np.arange(6.0,12.01,0.1):
    for b in np.arange(262.0,268.01,0.1):
        if any(kfloor(W,mr,a,b)!=kn for W,H,mr,kn,_ in D) or any(kfloor(W,mr,a,b)!=kn for W,mr,kn in K): continue
        for c in np.arange(0.0,1.01,0.02):
            for rname,rf in (('floor',math.floor),('round',lambda v: math.floor(v+0.5))):
                ok=True
                for W,H,mr,kn,top in D:
                    ke=(W-a)/(W-mr+b); t=H*(1-ke)/2+c
                    if rf(t/0.24+1e-9)!=top: ok=False; break
                if ok: sols.append((round(a,2),round(b,2),round(c,2),rname))
print(len(sols),'solutions'); 
import collections
print('a range', min(s[0] for s in sols) if sols else None, max(s[0] for s in sols) if sols else None)
print('b range', min(s[1] for s in sols) if sols else None, max(s[1] for s in sols) if sols else None)
print('c range', min(s[2] for s in sols) if sols else None, max(s[2] for s in sols) if sols else None)
print(collections.Counter(s[3] for s in sols))
print(sols[:10]); print(sols[-5:])