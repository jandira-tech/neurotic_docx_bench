# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# validation set: every comment doc in the corpus with a Word PDF: first-page pane top & height, page geometry from the FIRST section
import fitz, glob, json, zipfile, re, math
out=[]
for state in ('with_comments_clean','with_comments_tracking'):
    for dp in sorted(glob.glob(f'corpus/word/{state}/docx/*.docx'))[:400]:
        stem=dp.split('/')[-1][:-5]; wp=f'corpus/word/{state}/pdf/{stem}.pdf'
        if not glob.glob(wp): continue
        try: doc=zipfile.ZipFile(dp).read('word/document.xml').decode('utf8','ignore')
        except Exception: continue
        sects=re.findall(r'<w:sectPr.*?</w:sectPr>',doc,re.S)
        if not sects: continue
        sect=sects[0]
        m=re.search(r'<w:pgSz([^>]*)>',sect); mar=re.search(r'<w:pgMar([^>]*)>',sect)
        if not m or not mar: continue
        def a(s,name):
            r=re.search(r'w:'+name+r'="(-?\d+)"', s); return int(r.group(1))/20 if r else None
        W_,H_,mr=a(m.group(1),'w'),a(m.group(1),'h'),a(mar.group(1),'right')
        if None in (W_,H_,mr): continue
        try: w=fitz.open(wp)
        except Exception: continue
        pg=w[0]
        if abs(pg.rect.width-W_)>0.5 or abs(pg.rect.height-H_)>0.5: continue
        pane=None
        for d in pg.get_drawings():
            if d['type']=='f' and d['fill'] and abs(d['fill'][0]-0.949)<0.01: pane=tuple(round(v,3) for v in d['rect']); break
        if not pane: continue
        out.append(dict(stem=stem[:10],W=W_,H=H_,mr=mr,pane=pane))
json.dump(out,open('/tmp/pane_val.json','w')); print(len(out),'docs')
import collections
print(collections.Counter((o['W'],o['H'],o['mr'],round(o['pane'][1],2)) for o in out).most_common(25))