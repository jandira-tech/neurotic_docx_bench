# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pymupdf,sys
def spans(f,pg):
    p=pymupdf.open(f)[pg];out=[]
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                t=s['text'].strip()
                if t: out.append((round(s['origin'][1],2),round(s['origin'][0],1),t[:24],round(s['size'],1)))
    return out
pg=int(sys.argv[3]) if len(sys.argv)>3 else 0
a=spans(sys.argv[1],pg);b=spans(sys.argv[2],pg)
used=set()
for x in a[:int(sys.argv[4]) if len(sys.argv)>4 else 40]:
    c=[(i,y) for i,y in enumerate(b) if y[2]==x[2] and i not in used]
    if c:
        i,y=min(c,key=lambda t:abs(t[1][0]-x[0])); used.add(i)
        print(f"{x[2]:24} W {x[0]:7} {x[1]:6} sz{x[3]} | J {y[0]:7} {y[1]:6} dy={y[0]-x[0]:+.2f} dx={y[1]-x[1]:+.1f}")
    else: print(f"{x[2]:24} W {x[0]:7} MISSING")
