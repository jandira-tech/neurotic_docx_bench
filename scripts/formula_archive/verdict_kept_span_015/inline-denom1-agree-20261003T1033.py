# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import csv, collections
rows=[r for r in csv.DictReader(open('denom1/verdicts.csv')) if r['word'] in ('word-level','replaced')]
wl=lambda r: r['word']=='word-level'
def agree(rs,key,t): return sum((key(r)>=t)==wl(r) for r in rs)/len(rs)
kmax=lambda r: float(r['ratio_max']); kmin=lambda r: float(r['ratio_min'])
print(f"\nby cell (n × asym): rep max | wl min of ratio_max; @0.12 agreement; discriminating pairs (max<0.12<=min) and how many Word replaced")
by=collections.defaultdict(list)
for r in rows: by[(int(r['n']),float(r['asym']))].append(r)
for (n,a),rs in sorted(by.items()):
    rep=[kmax(r) for r in rs if not wl(r)]; w=[kmax(r) for r in rs if wl(r)]
    disc=[r for r in rs if kmax(r)<0.12<=kmin(r)]
    print(f"  n={n:3} x{a:<4} pairs={len(rs):2}  rep max {max(rep) if rep else float('nan'):.3f} | wl min {min(w) if w else float('nan'):.3f}  @0.12 {agree(rs,kmax,0.12):.2f}  disc {len(disc):2} replaced {sum(not wl(r) for r in disc):2}")
disc=[r for r in rows if kmax(r)<0.12<=kmin(r)]
print(f"\nall discriminating: {len(disc)}, replaced {sum(not wl(r) for r in disc)}, word-level {sum(wl(r) for r in disc)}")
print("word-level ones:", [(r['name'], r['ratio_max'], r['ratio_min']) for r in disc if wl(r)][:20])
for run in ('1','4'):
    rs=[r for r in rows if r['run']==run]
    best=max((agree(rs,kmax,t/1000),t/1000) for t in range(80,160))
    print(f"run {run}: n={len(rs)} ratio_max @0.12 {agree(rs,kmax,0.12):.3f} @0.11 {agree(rs,kmax,0.11):.3f} best {best[0]:.3f}@{best[1]}")
for n in (120,200,300,400,600):
    rs=[r for r in rows if int(r['n'])==n]
    best=max((agree(rs,kmax,t/1000),t/1000) for t in range(80,160))
    rep=[kmax(r) for r in rs if not wl(r)]; w=[kmax(r) for r in rs if wl(r)]
    print(f"n={n}: pairs {len(rs)} rep max {max(rep):.4f} wl min {min(w):.4f} @0.12 {agree(rs,kmax,0.12):.3f} @0.105 {agree(rs,kmax,0.105):.3f} best {best[0]:.3f}@{best[1]}")