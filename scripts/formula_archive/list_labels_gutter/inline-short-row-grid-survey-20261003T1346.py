# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, glob
from lxml import etree
src=glob.glob('corpus/word/with_comments_tracking/docx/25f1d311bd*')[0]
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
root=etree.fromstring(zipfile.ZipFile(src).read('word/document.xml'))
TEXT=(W+'t', W+'delText')
def text(el): return ''.join(t.text or '' for t in el.iter(*TEXT))
target=None
for needle in ['lifecycle','browser-first','brainstorming']:
    for t in root.iter(*TEXT):
        if t.text and needle in t.text: target=t; break
    if target is not None: print('needle', needle, t.tag.replace(W,'w:')); break
anc=[a.tag.replace(W,'w:') for a in target.iterancestors()]
print('ancestors:', anc[:8])
para=next(a for a in target.iterancestors() if a.tag==W+'p')
print('para text:', text(para)[:220])
print('para pPr:', etree.tostring(para.find(W+'pPr')).decode()[:300] if para.find(W+'pPr') is not None else None)
tbl=next((a for a in target.iterancestors() if a.tag==W+'tbl'), None)
body=root.find(W+'body')
if tbl is None:
    top=para
    while top.getparent() is not body: top=top.getparent()
    kids=list(body); i=kids.index(top)
    for j in range(i-3,i+3):
        k=kids[j]; print(j-i, k.tag.replace(W,'w:'), repr(text(k)[:60]), 'grid', [c.get(W+'w') for c in k.find(W+'tblGrid')] if k.tag==W+'tbl' and k.find(W+'tblGrid') is not None else '', 'ppr', etree.tostring(k.find(W+'pPr')).decode()[:160] if k.tag==W+'p' and k.find(W+'pPr') is not None else '')
    raise SystemExit
tblPr=tbl.find(W+'tblPr'); print('tblPr:', etree.tostring(tblPr).decode()[:500] if tblPr is not None else None)
grid=tbl.find(W+'tblGrid'); print('grid:', [c.get(W+'w') for c in grid] if grid is not None else None)
for ri,tr in enumerate(tbl.findall(W+'tr')):
    cells=[]
    for tc in tr.findall(W+'tc'):
        tcPr=tc.find(W+'tcPr'); tcw=tcPr.find(W+'tcW') if tcPr is not None else None; span=tcPr.find(W+'gridSpan') if tcPr is not None else None
        cells.append((tcw.get(W+'w') if tcw is not None else None, tcw.get(W+'type') if tcw is not None else None, span.get(W+'val') if span is not None else None, text(tc)[:28]))
    trPr=tr.find(W+'trPr')
    print('row', ri, [c.tag.replace(W,'w:') for c in trPr] if trPr is not None else [], cells)