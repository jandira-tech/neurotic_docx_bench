# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import math
# engine page sizes (Word's PDF MediaBox): A4 595.2 x 841.92, Letter 612 x 792, custom 595 x 842, A4 landscape 841.92 x 595.2
G=[(595.2,841.92,45.35,215,118.56),(595.2,841.92,56.70,218,114.24),(595.2,841.92,72.0,223,108.48),(595.2,841.92,76.55,224,106.56),(595.2,841.92,85.05,226,103.20),(595.2,841.92,89.85,228,101.28),(595.2,841.92,120.25,237,88.08),(612.0,792.0,54.0,219,106.32),(612.0,792.0,70.9,224,100.08),(612.0,792.0,72.0,224,99.84),(612.0,792.0,90.0,229,93.12),(612.0,792.0,108.0,235,85.92),(595.0,842.0,72.45,223,108.24),(841.92,595.2,72.0,241,58.56)]
best=[]
for i in range(0,400):
    inset=i*0.05
    for s in range(0,800):
        span=250+s*0.05
        m=9
        for (W,H,mr,n,y0) in G:
            v=(W-inset)/(W-mr+span)*300
            d=min(v-n, n+1-v)
            if d<m: m=d
            if m<=0: break
        if m>0: best.append((m,inset,span))
best.sort(reverse=True)
print("floor rule, top fits (margin, inset, span):")
for b in best[:8]: print("  %.3f inset=%.2f span=%.2f"%b)
# ty check for the top fit
m,inset,span=best[0]
for drop in (0.0,0.24,0.36,0.48,0.6):
    ok=0; worst=9
    for (W,H,mr,n,y0) in G:
        e=(W-inset)/(W-mr+span)
        raw=(H*(1-e)/2+drop)/0.24
        ty=math.floor(raw)*0.24
        if abs(ty-y0)<0.01: ok+=1
        worst=min(worst, min(raw-math.floor(raw), 1-(raw-math.floor(raw))))
    print("drop",drop,"ty matches",ok,"/",len(G),"min margin %.3f"%worst)