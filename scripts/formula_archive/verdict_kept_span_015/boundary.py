# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import csv, sys, glob, collections
sys.path.insert(0,'/tmp'); sys.path.insert(0,'/Users/arthrod/T/neurotic_docx_bench/scripts')
from real_rule_check2 import one
from concurrent.futures import ProcessPoolExecutor
R='/Users/arthrod/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes'
def main():
    sets=sys.argv[1:] or ['short1']
    rows=[]
    for s in sets:
        files=sorted(glob.glob(f'{R}/{s}/word/*.docx'))
        with ProcessPoolExecutor(6) as ex:
            for f,rs in zip(files, ex.map(one, files, chunksize=8)):
                for r in rs:
                    if 'error' in r: continue
                    r['set']=s; rows.append(r)
    with open('/tmp/boundary_rows.csv','w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    probes=[{k:(int(v) if k not in ("file","word","set") else v) for k,v in r.items()} for r in csv.DictReader(open('/tmp/probe_rows.csv'))]
    allr=rows+probes
    def rmax(r): return r['kept_all']/max(r['chars_a'],r['chars_b'],1)
    by=collections.defaultdict(list)
    for r in allr: by[max(r['aw'],r['bw'])].append(r)
    def agree(rs,t): return sum((rmax(r)>=t)==(r['word']=='word-level') for r in rs)/len(rs)
    print(f"{'n words':>8} {'sets':>14} {'pairs':>5} {'rep max':>8} {'wl min':>8}  {'best thr':>12} {'@0.105':>7} {'@0.12':>6}")
    for n in sorted(by):
        rs=by[n]
        if len(rs)<4: continue
        rep=[rmax(r) for r in rs if r['word']=='replaced']; wl=[rmax(r) for r in rs if r['word']=='word-level']
        if not rep or not wl: continue
        sets=','.join(sorted({r['set'] for r in rs}))[:14]
        best=max((agree(rs,k/1000),k/1000) for k in range(50,200,2))
        print(f"{n:>8} {sets:>14} {len(rs):>5} {max(rep):>8.4f} {min(wl):>8.4f}  {best[0]:.3f}@{best[1]:<6} {agree(rs,0.105):>7.3f} {agree(rs,0.12):>6.3f}")
if __name__=='__main__': main()