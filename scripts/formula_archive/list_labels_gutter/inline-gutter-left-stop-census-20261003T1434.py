# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# how many corpus paragraphs have a LEFT (typed) stop inside a numbering hanging gutter, vs num stops
import zipfile, glob, re, collections
from lxml import etree
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
files=sorted(glob.glob('corpus/word/*/docx/*.docx'))
docs=collections.Counter(); paras=collections.Counter(); ex=[]
for f in files:
    try:
        z=zipfile.ZipFile(f); d=etree.fromstring(z.read('word/document.xml'))
    except Exception: continue
    hit=set()
    for p in d.iter(W+'p'):
        ppr=p.find(W+'pPr')
        if ppr is None or ppr.find(W+'numPr') is None: continue
        ind=ppr.find(W+'ind')
        if ind is None or ind.get(W+'hanging') is None: continue
        hang=int(ind.get(W+'hanging')); left=int(ind.get(W+'left') or 0)
        tabs=ppr.find(W+'tabs')
        if tabs is None: continue
        for t in tabs.findall(W+'tab'):
            kind=t.get(W+'val'); pos=int(t.get(W+'pos') or 0)
            if left-hang < pos < left:
                paras[kind]+=1; hit.add(kind)
                if kind=='left' and len(ex)<6: ex.append((f.split('/')[-1][:10], left, hang, pos))
    for k in hit: docs[k]+=1
print('docs',dict(docs)); print('paras',dict(paras)); print(ex)