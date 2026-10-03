# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Which kept measure gives one clean threshold across lengths? short1 + all probe waves."""
import csv, sys, glob, collections
sys.path.insert(0,'/Users/arthrod/T/neurotic_docx_bench/scripts')
import redline_anatomy as ra
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
R='/Users/arthrod/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes'
SETS=['short1','wave1','wave3','wave4','wave5','wave7','wave7b','wave8','variants','variants2','tokens']
def alnum(w): return any(c.isalnum() for c in w)
def feats(path):
    out=[]
    try:
        paras=ra.paragraphs(Path(path)); vs=ra.verdicts(paras)
    except Exception as e:
        return []
    for v in vs:
        if v.verdict=='word-level':
            p=paras[v.index]; ta,tb=p.text('orig'),p.text('rev')
        elif v.verdict=='replaced' and v.block=='1×1' and v.partner is not None:
            p=paras[v.index]; ta=p.text('orig')
            if not ta.strip(): continue
            tb=paras[v.partner].text('rev')
        else: continue
        a,b=ra.words(ta),ra.words(tb)
        if not a or not b or max(len(a),len(b))>1500: continue
        pairs=[(i,j) for i,j in ra.lcs_pairs(a,b) if alnum(a[i])]
        kept=sum(len(a[i]) for i,_ in pairs); kw=len(pairs)
        runs=sum(1 for n,(i,j) in enumerate(pairs) if n==0 or pairs[n-1][0]!=i-1 or pairs[n-1][1]!=j-1)
        out.append(dict(file=Path(path).name[:50], word=v.verdict, kept=kept, kw=kw, runs=runs,
            ca=len(ta), cb=len(tb), na=sum(len(w) for w in a if alnum(w)), nb=sum(len(w) for w in b if alnum(w)),
            wa=sum(1 for w in a if alnum(w)), wb=sum(1 for w in b if alnum(w))))
    return out
def main():
    rows=[]
    for s in SETS:
        files=sorted(glob.glob(f'{R}/{s}/word/*.docx'))
        with ProcessPoolExecutor(6) as ex:
            for rs in ex.map(feats, files, chunksize=8):
                for r in rs: r['set']=s; rows.append(r)
    with open('/tmp/measure_rows.csv','w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    M={
     'kept/max':            lambda r: r['kept']/max(r['ca'],r['cb']),
     'kept/min':            lambda r: r['kept']/min(r['ca'],r['cb']),
     'kept/max_nospace':    lambda r: r['kept']/max(r['na'],r['nb']),
     '(kept+runs-1sp)/max': lambda r: (r['kept']+max(r['kw']-r['runs'],0))/max(r['ca'],r['cb']),
     '(kept+kw)/max':       lambda r: (r['kept']+r['kw'])/max(r['ca'],r['cb']),
     '(kept+kw)/(max+1)':   lambda r: (r['kept']+r['kw'])/(max(r['ca'],r['cb'])+1),
     'kw/max_words':        lambda r: r['kw']/max(r['wa'],r['wb']),
     'kept/mean':           lambda r: 2*r['kept']/(r['ca']+r['cb']),
     'kept/(max-kw)':       lambda r: r['kept']/(max(r['ca'],r['cb'])-r['kw']),
    }
    def agree(rs,key,t): return sum((key(r)>=t)==(r['word']=='word-level') for r in rs)/len(rs)
    sub={'all':rows,'short1':[r for r in rows if r['set']=='short1'],'clean long':[r for r in rows if r['set'] in ('wave7','wave7b','wave8','variants2','tokens')],'short1+clean':[r for r in rows if r['set'] in ('short1','wave7','wave7b','wave8','variants2','tokens')]}
    print(f"{'measure':>20} " + " ".join(f"{k:>18}" for k in sub))
    for name,key in M.items():
        cells=[]
        for k,rs in sub.items():
            best=max((agree(rs,key,t/1000),t/1000) for t in range(60,250,1))
            cells.append(f"{best[0]:.3f}@{best[1]:.3f}")
        print(f"{name:>20} " + " ".join(f"{c:>18}" for c in cells))
    # band per length for the best two measures on short1+clean
    rs=sub['short1+clean']
    for name in ['kept/max','(kept+kw)/max','kept/max_nospace']:
        key=M[name]; by=collections.defaultdict(list)
        for r in rs: by[max(r['wa'],r['wb'])//20*20].append(r)
        print(f"\n{name}: per 20-word bucket: replaced max | word-level min")
        for n in sorted(by):
            b=by[n]; rep=[key(r) for r in b if r['word']=='replaced']; wl=[key(r) for r in b if r['word']=='word-level']
            if rep and wl: print(f"  {n:>5} n={len(b):>3}  {max(rep):.4f} | {min(wl):.4f}  {'OVERLAP' if max(rep)>=min(wl) else ''}")
if __name__=='__main__': main()