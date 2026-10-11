# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz,sys
for path in sys.argv[1:]:
    d=fitz.open(path); out=[]
    for i,p in enumerate(d):
        for w in ('ANCHOR','General','After 0','After 2','Filler line 19'):
            for r in p.search_for(w): out.append(f'{w}@p{i+1}:{r.y0:.0f}')
        for dr in p.get_drawings():
            r=dr['rect']
            if r.height>20 and r.width>100: out.append(f'box@p{i+1}:{r.y0:.0f}-{r.y1:.0f}')
    print(path.split('/')[-2][:4], path.split('/')[-1][:20], len(d), ' '.join(out))