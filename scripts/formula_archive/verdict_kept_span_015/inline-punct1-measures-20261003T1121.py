# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import csv, collections
meta={r['name']:r for r in csv.DictReader(open('punct1/verdicts.csv'))}
rows=[r for r in csv.DictReader(open('/tmp/measure_rows4.csv')) if r['set']=='punct1']
def key(r): return (int(r['span'])+1)/(max(int(r['ca']),int(r['cb']))+1)
by=collections.defaultdict(lambda:[0,0]); miss=[]
for r in rows:
    name=r['file'].split('__vs__')[0]; m=meta.get(name,{})
    g=(m.get('punct','?'),)
    ok=(key(r)>=0.15)==(r['word']=='word-level')
    by[g][0]+=ok; by[g][1]+=1
    if not ok: miss.append((name, m.get('n'), m.get('target'), r['word'], round(key(r),3), r['kw'], r['runs']))
for g,(a,n) in sorted(by.items()): print(g, f"{a}/{n} = {a/n:.3f}")
print("misses (name, n, target, Word, span+mark ratio, kept words, runs):")
for x in sorted(miss, key=lambda x:x[4]): print("  ", x)
# band by punct
for p in sorted({m['punct'] for m in meta.values()}):
    rs=[r for r in rows if meta.get(r['file'].split('__vs__')[0],{}).get('punct')==p]
    rep=[key(r) for r in rs if r['word']=='replaced']; wl=[key(r) for r in rs if r['word']=='word-level']
    print(f"punct={p}: n={len(rs)} replaced max {max(rep):.3f} | word-level min {min(wl) if wl else 9:.3f}")