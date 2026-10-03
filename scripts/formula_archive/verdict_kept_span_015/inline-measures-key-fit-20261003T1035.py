# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import csv, collections
rows=[{k:(int(v) if k not in ("file","word","set") else v) for k,v in r.items()} for r in csv.DictReader(open('/tmp/measure_rows2.csv'))]
key=lambda r: (r['kept']+r['kw']+r['runs'])/max(r['ca'],r['cb'])
key0=lambda r: r['kept']/max(r['ca'],r['cb'])
wl=lambda r: r['word']=='word-level'
def agree(rs,k,t): return sum((k(r)>=t)==wl(r) for r in rs)/len(rs)
runlen=lambda r: r['kw']/max(r['runs'],1)
groups={'denom1 r1':[r for r in rows if r['set']=='denom1' and runlen(r)<2],'denom1 r4':[r for r in rows if r['set']=='denom1' and runlen(r)>=2],
 'short1':[r for r in rows if r['set']=='short1'],'asym1':[r for r in rows if r['set']=='asym1'],'wave7':[r for r in rows if r['set']=='wave7'],
 'wave7b+8+var2+tok':[r for r in rows if r['set'] in ('wave7b','wave8','variants2','tokens')],
 'clean (no wave3/4)':[r for r in rows if r['set'] not in ('wave3','wave4')],'wave3+4':[r for r in rows if r['set'] in ('wave3','wave4')],'ALL':rows}
ts=[0.13,0.135,0.14,0.145,0.15,0.155,0.16,0.165,0.17]
print(f"{'(kept+kw+runs)/max':>20} "+" ".join(f"{t:>6}" for t in ts)+"   | kept/max@.105 @.12")
for g,rs in groups.items():
    print(f"{g:>20} "+" ".join(f"{agree(rs,key,t):6.3f}" for t in ts)+f"   | {agree(rs,key0,0.105):.3f} {agree(rs,key0,0.12):.3f}  n={len(rs)}")
clean=groups['clean (no wave3/4)']
best=max((agree(clean,key,t/1000),t/1000) for t in range(120,180))
print("clean best:",best)
# band per group at the best
for g,rs in groups.items():
    rep=[key(r) for r in rs if not wl(r)]; w=[key(r) for r in rs if wl(r)]
    if rep and w: print(f"  {g:>20} replaced max {max(rep):.4f} | word-level min {min(w):.4f}")