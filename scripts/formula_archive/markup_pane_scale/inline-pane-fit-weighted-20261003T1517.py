# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import math
G=[(595.2,841.92,45.35,215,118.56,2),(595.2,841.92,56.70,218,114.24,2),(595.2,841.92,72.0,223,108.48,27),(595.2,841.92,76.55,224,106.56,1),(595.2,841.92,85.05,226,103.20,1),(595.2,841.92,89.85,228,101.28,1),(595.2,841.92,120.25,237,88.08,1),(612.0,792.0,54.0,219,106.32,31),(612.0,792.0,70.9,224,100.08,3),(612.0,792.0,72.0,224,99.84,317),(612.0,792.0,90.0,229,93.12,19),(612.0,792.0,108.0,235,85.92,2),(595.0,842.0,72.45,223,108.24,2),(841.92,595.2,72.0,241,58.56,1)]
for a,b in ((33,1110),(36,1107),(34,1109)):
    inset,span=a*0.24,b*0.24
    # per geometry: the d interval (pt) for which floor((H(1-e)/2+d)/0.24)*0.24 == y0
    ivs=[]
    for (W,H,mr,n,y0,c) in G:
        e=(W-inset)/(W-mr+span); ce=H*(1-e)/2
        lo=y0-ce; hi=y0+0.24-ce
        ivs.append((lo,hi,W,mr,c))
    # best d: maximize min over geometries except excluded ones
    cands=sorted(set([iv[0] for iv in ivs]+[iv[1] for iv in ivs]))
    bestd=None
    for i in range(len(cands)-1):
        d=(cands[i]+cands[i+1])/2
        ok=[iv for iv in ivs if iv[0]<=d<iv[1]]
        fails=[(iv[2],iv[3],iv[4]) for iv in ivs if not (iv[0]<=d<iv[1])]
        margin=min(min(d-iv[0], iv[1]-d) for iv in ok)
        docs=sum(f[2] for f in fails)
        if bestd is None or (len(ok),-docs,margin)>bestd[0]:
            bestd=((len(ok),-docs,margin),d,fails)
    print(f"inset={inset:.2f} span={span:.2f}: ok={bestd[0][0]} docs_missed={-bestd[0][1]} margin={bestd[0][2]*300/72:.3f}px d={bestd[1]:.3f}pt fails={bestd[2]}")