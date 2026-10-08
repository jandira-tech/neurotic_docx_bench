# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import math
G=[(595.2,841.92,45.35,215,118.56),(595.2,841.92,56.70,218,114.24),(595.2,841.92,72.0,223,108.48),(595.2,841.92,76.55,224,106.56),(595.2,841.92,85.05,226,103.20),(595.2,841.92,89.85,228,101.28),(595.2,841.92,120.25,237,88.08),(612.0,792.0,54.0,219,106.32),(612.0,792.0,70.9,224,100.08),(612.0,792.0,72.0,224,99.84),(612.0,792.0,90.0,229,93.12),(612.0,792.0,108.0,235,85.92),(595.0,842.0,72.45,223,108.24),(841.92,595.2,72.0,241,58.56)]
px=lambda pt: round(pt*300/72)
P=[(px(W),px(H),px(mr),n,px(y0)) for (W,H,mr,n,y0) in G]
print([ (w,h,m,n,y) for (w,h,m,n,y) in P])
# scale: n = floor(300*(Wpx-a)/(Wpx-mr+b)) for integer a,b
feas=[]
for a in range(0,80):
    for b in range(1000,1200):
        m=9
        for (w,h,mr,n,y) in P:
            v=300*(w-a)/(w-mr+b)
            d=min(v-n,n+1-v)
            m=min(m,d)
            if m<=0: break
        if m>0: feas.append((m,a,b))
feas.sort(reverse=True)
print("scale feasible:",len(feas)," best:",feas[:6])
# page top in px: y = f((h - h*e)/2 + d) or with k=n/300, f in floor/round/ceil, d in half-px steps
best=[]
for (m,a,b) in feas[:60]:
    for base in ("e","k"):
        for fn_name,fn in (("floor",math.floor),("round",round),("ceil",math.ceil)):
            for di in range(-40,41):
                d=di*0.25
                ok=0; margin=9
                for (w,h,mr,n,y) in P:
                    e=(w-a)/(w-mr+b); s = e if base=="e" else n/300
                    raw=(h-h*s)/2+d
                    ty=fn(raw)
                    if ty==y: ok+=1
                    fr=raw-math.floor(raw)
                    margin=min(margin, min(fr,1-fr) if fn_name!="round" else abs(fr-0.5))
                best.append((ok,round(margin,3),m,a,b,base,fn_name,d))
best.sort(reverse=True)
for r in best[:15]: print(r)