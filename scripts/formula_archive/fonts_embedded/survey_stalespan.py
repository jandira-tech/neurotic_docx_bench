# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, glob, os, json, sys
from lxml import etree
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
sample=open('/tmp/pdf-300/list.txt').read()
hits=[]
for state in ['clean','tracking_without_comments','with_comments_clean','with_comments_tracking']:
    for p in sorted(glob.glob(f'corpus/word/{state}/docx/*.docx')):
        try: root=etree.fromstring(zipfile.ZipFile(p).read('word/document.xml'))
        except Exception: continue
        n_tables=0; n_rows=0; worst=0.0
        for tbl in root.iter(W+'tbl'):
            grid=tbl.find(W+'tblGrid')
            if grid is None: continue
            cols=[]
            for c in grid.findall(W+'gridCol'):
                try: cols.append(int(c.get(W+'w'))/20)
                except: cols.append(None)
            if not cols or any(c is None for c in cols): continue
            found=False
            for tr in tbl.findall(W+'tr'):
                col=0; stale=False
                for tc in tr.findall(W+'tc'):
                    tcPr=tc.find(W+'tcPr'); span=1; tcw=None
                    if tcPr is not None:
                        g=tcPr.find(W+'gridSpan'); 
                        if g is not None:
                            try: span=int(g.get(W+'val'))
                            except: pass
                        tw=tcPr.find(W+'tcW')
                        if tw is not None and tw.get(W+'type','dxa')=='dxa':
                            try: tcw=int(tw.get(W+'w'))/20
                            except: pass
                    own=sum(cols[col:col+span]) if col < len(cols) else 0
                    if tcw and col+span < len(cols) and tcw - own > 20:
                        stale=True; worst=max(worst, tcw-own)
                    col+=span
                if stale and col < len(cols): n_rows+=1; found=True
            if found: n_tables+=1
        if n_tables:
            hits.append(dict(id=os.path.basename(p)[:10], state=state, tables=n_tables, rows=n_rows, worst=round(worst,1), in_sample=os.path.basename(p)[:10] in sample))
json.dump(hits, open('/tmp/survey_stalespan.json','w'), indent=1)
print('docs with a short row whose cell tcW outruns its grid columns by >20pt:', len(hits), 'in sample:', sum(h['in_sample'] for h in hits))
for h in hits[:40]: print(h)