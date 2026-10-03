# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import math
geos=[(595.32,841.92,45.35,215),(595.32,841.92,56.70,218),(595.32,841.92,72.0,223),(595.32,841.92,76.55,224),(595.32,841.92,85.05,226),(595.32,841.92,89.85,228),(595.32,841.92,120.25,237),(612.0,792.0,54.0,219),(612.0,792.0,70.9,224),(612.0,792.0,72.0,224),(612.0,792.0,90.0,229),(612.0,792.0,108.0,235),(595.0,842.0,72.45,223)]
def e(W,mr,inset=8.05,span=266.7): return (W-inset)/(W-mr+span)
for Wa4 in (595.32,595.3,595.2):
    print("A4 width", Wa4)
    for (W,H,mr,n) in geos:
        Wx = Wa4 if abs(W-595.32)<0.01 else W
        v=e(Wx,mr)*300
        print(f"  W={Wx} mr={mr:7.2f} want {n}  e*300={v:8.3f}  floor {math.floor(v)} {'OK' if math.floor(v)==n else 'XX'}  round {round(v)} {'OK' if round(v)==n else 'XX'}  frac {v-math.floor(v):.3f}")