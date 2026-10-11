# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, glob, os, json
from lxml import etree
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
sample=open('/tmp/pdf-300/list.txt').read()
hits=[]
for state in ['clean','tracking_without_comments','with_comments_clean','with_comments_tracking']:
    for p in sorted(glob.glob(f'corpus/word/{state}/docx/*.docx')):
        try:
            z=zipfile.ZipFile(p); root=etree.fromstring(z.read('word/document.xml'))
        except Exception: continue
        seen={}  # numId -> set of levels seen
        n=0
        for para in root.iter(W+'p'):
            ppr=para.find(W+'pPr')
            if ppr is None: continue
            np_=ppr.find(W+'numPr')
            if np_ is None: continue
            nid=np_.find(W+'numId'); il=np_.find(W+'ilvl')
            if nid is None or nid.get(W+'val') in (None,'0'): continue
            lvl=int(il.get(W+'val')) if il is not None and il.get(W+'val','').isdigit() else 0
            s=seen.setdefault(nid.get(W+'val'), set())
            if lvl>0 and not any(l<lvl for l in s): n+=1
            s.add(lvl)
        if n: hits.append(dict(id=os.path.basename(p)[:10], state=state, deeper_first=n, in_sample=os.path.basename(p)[:10] in sample))
json.dump(hits, open('/tmp/survey_deeperfirst.json','w'), indent=1)
print('docs with a list opening at a deeper level:', len(hits), 'in sample', sum(h['in_sample'] for h in hits))
print([h['id'] for h in hits if h['in_sample']])