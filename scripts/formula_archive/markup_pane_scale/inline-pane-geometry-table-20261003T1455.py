# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import math, itertools
# (W, H, mr, k_num, observed top units)
D=[(595.0,842.0,72.45,223,451),(595.3,841.9,72.0,223,452),(595.3,841.9,89.85,228,422),(612.0,792.0,54.0,219,443),(612.0,792.0,70.9,224,417),(612.0,792.0,72.0,224,416),(612.0,792.0,90.0,229,388)]
# note: mr 70.9 and 72.0 share k=224, same page, different tops (417 vs 416) -> top must depend on mr or on something else; test mr-dependence
def variants():
    rnds={'floor':math.floor,'round':lambda v: math.floor(v+0.5),'ceil':math.ceil,'trunc':int}
    for hr in rnds:
        for ghr in rnds:
            for tr in rnds:
                for c in [x*0.5 for x in range(-8,9)]:
                    yield hr,ghr,tr,c
best=[]
for hr,ghr,tr,c in variants():
    import math as m
    R={'floor':m.floor,'round':lambda v: m.floor(v+0.5),'ceil':m.ceil,'trunc':int}
    ok=0; miss=[]
    for W,H,mr,kn,top in D:
        Hpx=R[hr](H/0.24); gh=R[ghr](Hpx*kn/300)
        t=R[tr]((Hpx-gh)/2+c)
        if t==top: ok+=1
        else: miss.append((W,H,mr,t,top))
    best.append((ok,hr,ghr,tr,c,miss))
best.sort(key=lambda b:-b[0])
for b in best[:6]: print(b[0],b[1:5],b[5][:3])
# dependence on right margin: top vs mr for Letter
print('Letter: mr->top', [(d[2],d[4]) for d in D if d[0]==612])
# test: top = centered of (H - gh) where gh uses k computed with span including a different pane width? compute implied gh for each from symmetric centering: H_px - 2*top
for W,H,mr,kn,top in D:
    Hpx=H/0.24; print(W,H,mr,kn,'top',top,'implied gh if centered',Hpx-2*top,'actual gh',Hpx*kn/300, 'diff', round(Hpx-2*top-Hpx*kn/300,2))