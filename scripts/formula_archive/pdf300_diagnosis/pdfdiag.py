# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import sys, glob, os, fitz
key=sys.argv[1]; build=sys.argv[2] if len(sys.argv)>2 else 'pdf10'; page_sel=int(sys.argv[3]) if len(sys.argv)>3 else None
state, rest = key.split('__',1)
stem = rest
cands=glob.glob(f'/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word/{state}/pdf/{stem}*.pdf')
ours=glob.glob(f'/tmp/pdf-300/work-{build}/jubarte/**/{stem}*.pdf', recursive=True)+glob.glob(f'/tmp/pdf-300/work-{build}/**/{key}*.pdf', recursive=True)
if not cands or not ours:
    print('missing', cands[:1], ours[:1]); sys.exit(1)
W=fitz.open(cands[0]); O=fitz.open(ours[0])
print('WORD', os.path.basename(cands[0])[:50], W.page_count, 'pages', [tuple(round(v) for v in W[i].rect[2:]) for i in range(min(3,W.page_count))])
print('OURS', ours[0][-60:], O.page_count, 'pages', [tuple(round(v) for v in O[i].rect[2:]) for i in range(min(3,O.page_count))])
def lines(pg):
    out=[]
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            t=''.join(s['text'] for s in l['spans']).strip()
            if t: out.append((round(l['bbox'][1],1), round(l['bbox'][0],1), round(l['bbox'][2],1), t, round(l['spans'][0]['size'],1), l['spans'][0]['font'][:14]))
    out.sort(); return out
pages = [page_sel] if page_sel is not None else range(min(W.page_count,O.page_count))
for i in pages:
    a=lines(W[i]); b=lines(O[i])
    print(f'--- page {i+1}: Word {len(a)} lines, ours {len(b)} lines')
    n=max(len(a),len(b)); shown=0; div=None
    for j in range(n):
        la=a[j] if j<len(a) else None; lb=b[j] if j<len(b) else None
        same = la and lb and la[3][:25]==lb[3][:25] and abs(la[0]-lb[0])<2.5 and abs(la[1]-lb[1])<2.5
        if not same and div is None: div=j
        if div is not None and shown<10:
            print(f"  W {la[0] if la else '':>6} x{la[1] if la else '':>6}-{la[2] if la else '':>6} {la[4] if la else ''} {la[5] if la else ''} {la[3][:45]!r}" if la else '  W  (none)')
            print(f"  O {lb[0] if lb else '':>6} x{lb[1] if lb else '':>6}-{lb[2] if lb else '':>6} {lb[4] if lb else ''} {lb[5] if lb else ''} {lb[3][:45]!r}" if lb else '  O  (none)')
            shown+=1
    if div is None: print('  no divergence in text/positions')
    else: print(f'  first divergence at line {div+1}')