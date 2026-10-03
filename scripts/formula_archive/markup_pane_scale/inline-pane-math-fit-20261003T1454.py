# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob, json, zipfile, re, math
rows=[json.loads(l) for l in open('/tmp/pdf-300/work-pdf10/jubarte/scores.checkpoint.jsonl')]
keys=[r['key'] for r in rows if r['key'].startswith('with_comments')]
def pane(pg):
    for d in pg.get_drawings():
        if d['type']=='f' and d['fill'] and abs(d['fill'][0]-0.949)<0.01: return tuple(round(v,3) for v in d['rect'])
    return None
data={}
for k in keys:
    state, stem = k.split('__',1)
    wp=glob.glob(f'corpus/word/{state}/pdf/{stem}*.pdf'); dp=glob.glob(f'corpus/word/{state}/docx/{stem}*.docx')
    if not wp or not dp: continue
    doc=zipfile.ZipFile(dp[0]).read('word/document.xml').decode('utf8','ignore')
    sects=re.findall(r'<w:sectPr.*?</w:sectPr>',doc,re.S)
    if len(sects)!=1: continue   # one section only: first page geometry certain
    sect=sects[0]
    m=re.search(r'<w:pgSz([^>]*)>',sect); mar=re.search(r'<w:pgMar([^>]*)>',sect)
    if not m or not mar: continue
    def a(s,name):
        r=re.search(r'w:'+name+r'="(-?\d+)"', s); return int(r.group(1))/20 if r else None
    W_,H_,mr=a(m.group(1),'w'),a(m.group(1),'h'),a(mar.group(1),'right')
    if None in (W_,H_,mr): continue
    orient='landscape' in m.group(1)
    w=fitz.open(wp[0]); pw=pane(w[0])
    if not pw: continue
    if abs(w[0].rect.width-W_)>0.5: continue
    geo=(W_,H_,mr)
    if geo in data: continue
    data[geo]=pw
print(len(data),'geometries')
res=[]
for (W_,H_,mr),pw in sorted(data.items()):
    span=W_-mr+9.15+257.3
    k=math.floor((W_-8)/span*300)/300
    gh=H_*k
    ok_h=abs((pw[3]-pw[1])-gh)<0.3
    top_units=pw[1]/0.24
    centered=(H_-gh)/2
    res.append((W_,H_,mr,round(k*300),round(gh,2),round(pw[3]-pw[1],2),ok_h,round(pw[1],2),round(top_units,2),round(centered,2),round((centered-pw[1])/0.24,2)))
    print(f"W={W_} H={H_} mr={mr} k={round(k*300)}/300 gh={gh:.2f} paneH={pw[3]-pw[1]:.2f} {'OK' if ok_h else 'K?'} top={pw[1]:.2f} ({top_units:.2f}u) centered={centered:.2f} diff_units={(centered-pw[1])/0.24:.2f} x0={pw[0]:.2f} gx_model={0.96+(W_-mr+9.15)*k:.2f}")
json.dump([list(map(float,r[:3]))+[r[7]] for r in res], open('/tmp/pane_geo.json','w'))