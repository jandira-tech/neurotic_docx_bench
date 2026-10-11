# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import numpy as np, itertools
G=[(595.2,841.92,45.35,215,118.56),(595.2,841.92,56.70,218,114.24),(595.2,841.92,72.0,223,108.48),(595.2,841.92,76.55,224,106.56),(595.2,841.92,85.05,226,103.20),(595.2,841.92,89.85,228,101.28),(595.2,841.92,120.25,237,88.08),(612.0,792.0,54.0,219,106.32),(612.0,792.0,70.9,224,100.08),(612.0,792.0,72.0,224,99.84),(612.0,792.0,90.0,229,93.12),(612.0,792.0,108.0,235,85.92),(595.0,842.0,72.45,223,108.24),(841.92,595.2,72.0,241,58.56)]
px=lambda pt: round(pt*300/72)
P=[(px(W),px(H),px(mr),n,px(y0)) for (W,H,mr,n,y0) in G]
a,b=36,1106
rows=[];ys=[]
for (w,h,mr,n,y) in P:
    e=(w-a)/(w-mr+b); k=n/300
    rows.append([h, h*e, h*k, e, k, w, mr, 1.0]); ys.append(y+0.5)  # y+0.5: centre of the floor cell
A=np.array(rows); Y=np.array(ys)
names=["h","h*e","h*k","e","k","w","mr","1"]
for cols in ([0,1,7],[0,2,7],[0,1,3,7],[0,2,4,7],[0,1,6,7],[0,2,6,7],[0,1,2,7],[0,1,5,7],[0,2,5,7]):
    X=A[:,cols]; coef,res,rk,sv=np.linalg.lstsq(X,Y,rcond=None)
    pred=X@coef; r=Y-pred
    print([names[c] for c in cols], "coef", np.round(coef,4), "resid spread %.2f max|r| %.2f"%(r.max()-r.min(), abs(r).max()))