# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import pymupdf,pathlib,collections,subprocess,concurrent.futures as cf,re
G=pathlib.Path('/Users/arthrod/temp/T/neurotic_docx_bench/grok_run')
out=pathlib.Path('/tmp/fscan'); out.mkdir(exist_ok=True)
stems=open('/Users/arthrod/temp/T/jubarte-loop/all500.txt').read().split()
def norm(n): n=n.split('+')[-1]; n=re.sub(r'[-,].*','',n); n=re.sub(r'(PS)?(MT|PSMT)$','',n); return n.lower()
def fonts(p):
    try: d=pymupdf.open(p)
    except Exception: return set()
    s=set()
    for pg in d:
        for f in pg.get_fonts(): s.add(norm(f[3]))
    return s
def one(st):
    j=out/f'{st}.pdf'
    subprocess.run(['/Users/arthrod/temp/T/jubarte-loop/jubarte-cur2','convert',str(G/'fixtures_500'/f'{st}.docx'),'-o',str(j),'--force','--revisions','word'],capture_output=True,timeout=300)
    w=fonts(G/'fixtures_500_pdf'/f'{st}.pdf'); jj=fonts(j)
    return st,w-jj
miss=collections.Counter(); ex={}
with cf.ThreadPoolExecutor(10) as ex_:
    for st,m in ex_.map(one,stems):
        for f in m: miss[f]+=1; ex.setdefault(f,st)
for f,n in miss.most_common(40): print(n,f,ex[f][:8])