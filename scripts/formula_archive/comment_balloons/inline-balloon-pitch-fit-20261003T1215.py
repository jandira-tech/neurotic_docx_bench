# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, collections, glob, zipfile, re
import numpy as np
rows=json.load(open('/tmp/balloon_spec.json'))
# 1. pitch: box height (layout units) vs n_lines
xs=[];ys=[]
for r in rows:
    if r['label_size'] is None: continue
    k=(r['pane'][2]-r['pane'][0])/257.3
    ls=round(r['label_size']/k,1)
    if ls!=9.1: continue
    h=(r['box'][3]-r['box'][1])/k
    xs.append(r['n_lines']); ys.append(h)
xs=np.array(xs); ys=np.array(ys)
A=np.vstack([xs,np.ones_like(xs)]).T
p,res,_,_=np.linalg.lstsq(A,ys,rcond=None)
print('9.1pt docs: box_h = %.3f * n + %.3f  (n=%d)'%(p[0],p[1],len(xs)))
for n in sorted(set(xs)):
    v=ys[xs==n]; print('  n=%d median h=%.2f  min %.2f max %.2f count %d'%(n,np.median(v),v.min(),v.max(),len(v)))
# label bbox top relative to box top, label baseline estimate
tops=[];
for r in rows:
    if r['label_size'] is None or r['label_bbox'] is None: continue
    k=(r['pane'][2]-r['pane'][0])/257.3
    if round(r['label_size']/k,1)!=9.1: continue
    tops.append(((r['label_bbox'][1]-r['box'][1])/k, (r['label_bbox'][3]-r['box'][1])/k, (r['text_x0']-r['box'][0])/k if r['text_x0'] else None))
t=np.array([[a,b] for a,b,c in tops]); print('label bbox top-box top median %.2f, bbox bottom-box top median %.2f'%(np.median(t[:,0]),np.median(t[:,1])))
# 2. author colours
pal=['D13438','0078D4','5C2E91','498205','CC3595','7160E8','038387','6D5700','CF0F1F','4E6AED','B146C2','394146','0B6A0B']
def hexc(c): return '%02X%02X%02X'%tuple(int(round(v*255)) for v in c)
docs=collections.defaultdict(dict)
for r in rows:
    m=re.match(r'Commented \[(.*?)(\d+)\]', r['label_text'])
    if not m: continue
    docs[(r['doc'],r['state'])][int(m.group(2))]=(m.group(1),hexc(r['stroke']))
agree=collections.Counter(); shown=0
for (doc,state),seqs in docs.items():
    paths=glob.glob(f'corpus/word/{state}/docx/{doc}_*.docx')
    if not paths: continue
    z=zipfile.ZipFile(paths[0])
    try: c=z.read('word/comments.xml').decode('utf8','replace'); d=z.read('word/document.xml').decode('utf8','replace')
    except KeyError: continue
    meta={}
    for m in re.finditer(r'<w:comment [^>]*>', c):
        a=m.group(0); i=re.search(r'w:id="([^"]+)"',a); au=re.search(r'w:author="([^"]*)"',a); ini=re.search(r'w:initials="([^"]*)"',a)
        meta[i.group(1)]=(au.group(1) if au else '', ini.group(1) if ini else '')
    refs=re.findall(r'<w:commentReference w:id="([^"]+)"', d)
    order=[]  # authors in order of first reference
    for rid in refs:
        au=meta.get(rid,('?',''))[0]
        if au not in order: order.append(au)
    # authors by comments.xml order
    corder=[]
    for rid,(au,ini) in meta.items():
        if au not in corder: corder.append(au)
    for seq,(ini,col) in sorted(seqs.items()):
        if seq-1>=len(refs): continue
        au=meta.get(refs[seq-1],('?',''))[0]
        pi=pal.index(col) if col in pal else -1
        agree['ref_order']+= (order.index(au)==pi)
        agree['cxml_order']+= (corder.index(au)==pi)
        agree['n']+=1
        if shown<40 and (order.index(au)!=pi):
            print(doc, 'seq',seq,'author',repr(au[:25]),'ref-order',order.index(au),'cxml-order',corder.index(au),'palette',pi,col, '| n_authors',len(order)); shown+=1
print(agree)