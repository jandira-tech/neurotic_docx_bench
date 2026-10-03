"""Exact kept-span measures from Word's own equal segments across every wave.
For each paragraph pair: span = chars of kept words + inner blanks of a kept
run + the blank either side of a run when both sides have one (what Word's
eq segments carry). Variants: +mark (the paragraph mark counts as a kept
unit of 1 char on both sides, joining a run that ends at the last word),
and the plain letters-only measure. Rows -> $ROWS (default /tmp/measure_rows3.csv); probes under $PROBES.

    probe_span_measures.py            # compute rows and report
    probe_span_measures.py --report   # re-report from the rows
"""
import csv, sys, glob, collections, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import redline_anatomy as ra
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
R=os.environ.get('PROBES', os.path.expanduser('~/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes'))
ROWS=os.environ.get('ROWS', '/tmp/measure_rows3.csv')
SETS=['short1','asym1','denom1','edge1','wave1','wave3','wave4','wave5','wave7','wave7b','wave8','variants','variants2','tokens','punct1','short2']
def alnum(w): return any(c.isalnum() for c in w)
def blank(w): return w.strip()==''
def span_measures(a,b):
    """a,b: token lists (words and separators). Alignment: LCS over tokens
    with blanks neutral (only non-blank tokens may pair); runs join through
    equal, all-blank gaps."""
    ka=[w if not blank(w) else None for w in a]; kb=[w if not blank(w) else None for w in b]
    pairs=sorted((i,j) for i,j in ra.lcs_pairs(a,b) if not blank(a[i]))
    # group into runs: consecutive pairs whose gaps on both sides are equal and all blank
    runs=[]
    for i,j in pairs:
        if runs:
            pi,pj=runs[-1][-1]
            ga=a[pi+1:i]; gb=b[pj+1:j]
            if len(ga)==len(gb) and all(blank(x) for x in ga) and all(blank(x) for x in gb) and ga==gb:
                runs[-1].append((i,j)); continue
        runs.append([(i,j)])
    span=0; span_words=0
    for run in runs:
        i0,j0=run[0]; i1,j1=run[-1]
        inner=sum(len(a[k]) for k in range(i0,i1+1))  # words + inner blanks (left side)
        before = 1 if i0>0 and j0>0 and blank(a[i0-1]) and blank(b[j0-1]) else 0
        after  = 1 if i1+1<len(a) and j1+1<len(b) and blank(a[i1+1]) and blank(b[j1+1]) else 0
        span+=inner+before+after
        span_words+=sum(len(a[k]) for k,_ in run)
    last_kept = bool(pairs) and pairs[-1][0]==len(a)-1 and pairs[-1][1]==len(b)-1
    letters=sum(len(a[i]) for i,_ in pairs if alnum(a[i]))
    return dict(span=span, span_words=span_words, kw=len(pairs), runs=len(runs), last_kept=int(last_kept), letters=letters)
def feats(path):
    out=[]
    try:
        paras=ra.paragraphs(Path(path)); vs=ra.verdicts(paras)
    except Exception:
        return []
    for v in vs:
        if v.verdict=='word-level':
            p=paras[v.index]; ta,tb=p.text('orig'),p.text('rev')
        elif v.verdict=='replaced' and v.block=='1×1' and v.partner is not None:
            p=paras[v.index]; ta=p.text('orig')
            if not ta.strip(): continue
            tb=paras[v.partner].text('rev')
        else: continue
        a,b=[u.text for u in ra.tokenize(ta)],[u.text for u in ra.tokenize(tb)]
        if not a or not b or max(len(a),len(b))>1500: continue
        m=span_measures(a,b)
        m.update(file=Path(path).name[:60], word=v.verdict, ca=len(ta), cb=len(tb),
                 wa=sum(1 for w in a if alnum(w)), wb=sum(1 for w in b if alnum(w)))
        out.append(m)
    return out
def main():
    rows=[]
    for s in SETS:
        files=sorted(glob.glob(f'{R}/{s}/word/*.docx'))
        if not files: continue
        with ProcessPoolExecutor(6) as ex:
            for rs in ex.map(feats, files, chunksize=8):
                for r in rs: r['set']=s; rows.append(r)
    with open(ROWS,'w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    report(rows)
def report(rows):
    M={
     'letters/max':        lambda r: r['letters']/max(r['ca'],r['cb']),
     'span/max':           lambda r: r['span']/max(r['ca'],r['cb']),
     '(span+1)/(max+1)':   lambda r: (r['span']+1)/(max(r['ca'],r['cb'])+1),
     '(span+mark)/(max+1)':lambda r: (r['span']+r['last_kept'])/(max(r['ca'],r['cb'])+1),
     '(span+mark+1)/(max+1)':lambda r: (r['span']+r['last_kept']+1)/(max(r['ca'],r['cb'])+1),
     'span/(max-1)':       lambda r: r['span']/(max(r['ca'],r['cb'])-1),
     'span_words/max':     lambda r: r['span_words']/max(r['ca'],r['cb']),
    }
    def agree(rs,key,t): return sum((key(r)>=t)==(r['word']=='word-level') for r in rs)/len(rs)
    def best(rs,key): return max((agree(rs,key,t/1000),t/1000) for t in range(80,260))
    def band(rs,key):
        rep=[key(r) for r in rs if r['word']=='replaced']; wl=[key(r) for r in rs if r['word']=='word-level']
        return (max(rep) if rep else 0, min(wl) if wl else 9)
    sets=sorted({r['set'] for r in rows})
    groups={s:[r for r in rows if r['set']==s] for s in sets}
    groups['short<=40w']=[r for r in rows if max(r['wa'],r['wb'])<=40]
    groups['ALL']=rows
    print(f"{'measure':>22} "+" ".join(f"{g:>12}" for g in groups))
    for name,key in M.items():
        print(f"{name:>22} "+" ".join((lambda b: f"{b[0]:.3f}@{b[1]:.3f}")(best(rs,key)) if rs else f"{'-':>12}" for rs in groups.values()))
    print("\nfixed thresholds, agreement per group:")
    for name in M:
        key=M[name]
        for t in (0.14,0.145,0.15,0.155,0.16):
            print(f"{name:>22} @{t:.3f}: "+" ".join(f"{agree(rs,key,t):.3f}" if rs else '  -  ' for rs in groups.values()))
    print("\nbands (replaced max | word-level min) per group:")
    for name in ['span/max','(span+mark+1)/(max+1)']:
        key=M[name]
        print(f"{name:>22} "+" ".join((lambda b: f"{b[0]:.3f}|{b[1]:.3f}")(band(rs,key)) if rs else '-' for rs in groups.values()))
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--report':
        rows=[]
        for r in csv.DictReader(open(ROWS)):
            for k in ('span','span_words','kw','runs','last_kept','letters','ca','cb','wa','wb'): r[k]=int(r[k])
            rows.append(r)
        report(rows)
    else: main()
