# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, re, collections
rows=json.load(open('/Users/arthrod/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes/charfit_rows.json'))
def show(label, fn, t, word_if_le=True):
    wrong=[]
    for r in rows:
        pred = (fn(r)<=t) if word_if_le else (fn(r)>=t)
        if pred != (r['verdict']=='word-level'): wrong.append((r['name'], r['verdict'][:4], round(fn(r),4), r['Lw'], r['R']))
    print(f"== {label}: {len(wrong)} wrong of {len(rows)}")
    by=collections.Counter((re.match(r'w(\d+)',w[0])[1], re.search(r'_r(\d+)',w[0])[1], w[1]) for w in wrong)
    for k,v in sorted(by.items(), key=lambda kv:(int(kv[0][0]),int(kv[0][1]))): print(f"   L={k[0]:>5} r={k[1]:>2} {k[2]}: {v}")
    print("   e.g.", wrong[:6])
show("kept_c/Lc ≥ 0.1486", lambda r:r['kept_c']/r['Lc'], 0.1486, word_if_le=False)
show("edits·(1+R/1100)/(lac+lbc) ≤ 0.8826", lambda r:(r['lac']+r['lbc']-2*r['kept_c'])*(1+r['R']/1100)/(r['lac']+r['lbc']), 0.8826)
# boundary table in char terms: for each (L, r) the kept_c/Lc of the last replaced and first word-level
grid=collections.defaultdict(list)
for r in rows:
    m=re.match(r'w(\d+)_k(\d+)_r(\d+)(.*)',r['name']); grid[(int(m[1]),int(m[3]),m[4])].append((r['kept_c']/r['Lc'], r['R'], r['verdict']=='word-level'))
print("\nboundary in kept-char fraction (last replaced → first word-level), with R:")
for k in sorted(grid):
    pts=sorted(grid[k]); rep=[p for p in pts if not p[2]]; wl=[p for p in pts if p[2]]
    if rep and wl: print(f"   L={k[0]:>5} r={k[1]:>2} {k[2]:10}  replaced ≤ {rep[-1][0]:.3f} (R={rep[-1][1]})   word-level ≥ {wl[0][0]:.3f} (R={wl[0][1]})   {'OVERLAP' if rep[-1][0]>wl[0][0] else ''}")