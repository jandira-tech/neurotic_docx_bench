# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob, json, zipfile, re
keys=[l.strip() for l in open('/tmp/pdf-300/list.txt') if l.startswith('with_comments')]
def pane(pg):
    for d in pg.get_drawings():
        if d['type']=='f' and d['fill'] and abs(d['fill'][0]-0.949)<0.01: return [round(v,2) for v in d['rect']]
    return None
def first_text(pg):
    best=None
    for b in pg.get_text('rawdict')['blocks']:
        for l in b.get('lines',[]):
            s=l['spans'][0]
            if l['bbox'][0] < 380:
                o=(round(s['origin'][0],2), round(s['origin'][1],2), round(s['size'],2))
                if best is None or o[1]<best[1]: best=o
    return best
n=0
for k in keys:
    state, stem = k.split('__',1)
    wp=glob.glob(f'corpus/word/{state}/pdf/{stem}*.pdf'); op=glob.glob(f'/tmp/pdf-300/work-pdf10/jubarte/candidate/{k}*.pdf'); dp=glob.glob(f'corpus/word/{state}/docx/{stem}*.docx')
    if not wp or not op or not dp: continue
    w=fitz.open(wp[0]); o=fitz.open(op[0])
    pw=pane(w[0]); po=pane(o[0])
    if not pw: continue
    doc=zipfile.ZipFile(dp[0]).read('word/document.xml').decode('utf8','ignore')
    m=re.search(r'<w:pgSz[^>]*w:w="(\d+)"[^>]*w:h="(\d+)"',doc); mar=re.search(r'<w:pgMar[^>]*w:top="(-?\d+)"[^>]*w:right="(\d+)"[^>]*w:bottom="(-?\d+)"[^>]*w:left="(\d+)"',doc)
    pg=(int(m.group(1))/20, int(m.group(2))/20) if m else None
    print(f"{k[:40]:40} page={pg} W pane={pw} rect={tuple(round(v) for v in w[0].rect[2:])} | O pane={po} | Wtext={first_text(w[0])} Otext={first_text(o[0])}")
    n+=1
    if n>=16: break