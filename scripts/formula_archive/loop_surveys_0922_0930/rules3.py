# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""rules3.py STEM BIN_A BIN_B [page]: horizontal rule y0s (Word | A | B) on a page."""
import pymupdf as f,glob,sys,subprocess
stem,a,b=sys.argv[1:4]; pg=int(sys.argv[4]) if len(sys.argv)>4 else 0
G='/Users/arthrod/temp/T/neurotic_docx_bench/grok_run'
src=glob.glob(f'{G}/fixtures_500/{stem}*.docx')[0]; W=glob.glob(f'{G}/fixtures_500_pdf/{stem}*.pdf')[0]
for n in (a,b): subprocess.run([f'./jubarte-{n}','convert',src,'-o',f'sd/r_{n}.pdf','--force'],capture_output=True)
def rules(p):
    d=f.open(p)
    if pg>=len(d): return []
    return sorted(set(round(r['rect'].y0,2) for r in d[pg].get_drawings() if r['rect'].height<2.5 and r['rect'].width>15))
def base(p):
    d=f.open(p)
    if pg>=len(d): return []
    return sorted(set(round(l['spans'][0]['origin'][1],1) for bl in d[pg].get_text('dict')['blocks'] for l in bl.get('lines',[])))
R=[rules(W),rules(f'sd/r_{a}.pdf'),rules(f'sd/r_{b}.pdf')]
print('RULES'); [print('  |  '.join(f'{L[i]:8.2f}' if i<len(L) else ' '*8 for L in R)) for i in range(max(map(len,R)))]
B=[base(W),base(f'sd/r_{a}.pdf'),base(f'sd/r_{b}.pdf')]
print('BASE'); [print('  |  '.join(f'{L[i]:8.1f}' if i<len(L) else ' '*8 for L in B)) for i in range(min(40,max(map(len,B))))]
