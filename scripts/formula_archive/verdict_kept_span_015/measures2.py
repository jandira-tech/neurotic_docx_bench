# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Per-wave and per-run-length best thresholds for several kept measures (denom1, short1, asym1, wave7)."""
import csv, sys, glob, collections
sys.path.insert(0,'/tmp')
from measures import feats, R
from concurrent.futures import ProcessPoolExecutor
SETS=['denom1','short1','asym1','wave7','wave7b','wave8','variants2','tokens','wave3','wave4']
def main():
    rows=[]
    for s in SETS:
        files=sorted(glob.glob(f'{R}/{s}/word/*.docx'))
        with ProcessPoolExecutor(6) as ex:
            for rs in ex.map(feats, files, chunksize=8):
                for r in rs: r['set']=s; rows.append(r)
    with open('/tmp/measure_rows2.csv','w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    M={
     'kept/max':        lambda r: r['kept']/max(r['ca'],r['cb']),
     '(kept+kw)/max':   lambda r: (r['kept']+r['kw'])/max(r['ca'],r['cb']),
     '(kept+2kw)/max':  lambda r: (r['kept']+2*r['kw'])/max(r['ca'],r['cb']),
     '(kept+runs)/max': lambda r: (r['kept']+r['runs'])/max(r['ca'],r['cb']),
     '(kept+2runs)/max':lambda r: (r['kept']+2*r['runs'])/max(r['ca'],r['cb']),
     '(kept+kw+runs)/max': lambda r: (r['kept']+r['kw']+r['runs'])/max(r['ca'],r['cb']),
     '(kept+kw-runs)/max': lambda r: (r['kept']+r['kw']-r['runs'])/max(r['ca'],r['cb']),
     'kw/maxwords':     lambda r: r['kw']/max(r['wa'],r['wb']),
    }
    def agree(rs,key,t): return sum((key(r)>=t)==(r['word']=='word-level') for r in rs)/len(rs)
    def best(rs,key): return max((agree(rs,key,t/1000),t/1000) for t in range(60,260))
    def runlen(r): return r['kw']/max(r['runs'],1)
    groups={'denom1 r1':[r for r in rows if r['set']=='denom1' and runlen(r)<2],
            'denom1 r4':[r for r in rows if r['set']=='denom1' and runlen(r)>=2],
            'short1':[r for r in rows if r['set']=='short1'],
            'asym1':[r for r in rows if r['set']=='asym1'],
            'wave7 r4':[r for r in rows if r['set']=='wave7' and 2<=runlen(r)<8],
            'wave7 r16':[r for r in rows if r['set']=='wave7' and runlen(r)>=8],
            'ALL':rows}
    print(f"{'measure':>20} "+" ".join(f"{g:>13}" for g in groups))
    for name,key in M.items():
        print(f"{name:>20} "+" ".join((lambda b: f"{b[0]:.3f}@{b[1]:.3f}")(best(rs,key)) if rs else f"{'-':>13}" for rs in groups.values()))
    # agreement of fixed thresholds per group for the top candidates
    print()
    for name in ['kept/max','(kept+kw)/max','(kept+2kw)/max','(kept+kw+runs)/max']:
        key=M[name]; b=best(rows,key)[1]
        print(f"{name:>20} @{b:.3f}: "+" ".join(f"{agree(rs,key,b):.3f}" for rs in groups.values() if rs))
if __name__=='__main__': main()