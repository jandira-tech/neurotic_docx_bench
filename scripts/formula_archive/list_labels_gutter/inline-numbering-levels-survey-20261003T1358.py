# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, glob, re
from lxml import etree
src=glob.glob('corpus/word/*/docx/ed36b607e8*')[0]; z=zipfile.ZipFile(src)
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
root=etree.fromstring(z.read('word/document.xml'))
TEXT=(W+'t',W+'delText')
def text(el): return ''.join(t.text or '' for t in el.iter(*TEXT))
def ppr_brief(p):
    ppr=p.find(W+'pPr')
    if ppr is None: return 'no pPr'
    s=etree.tostring(ppr).decode()
    s=re.sub(r' xmlns:\w+="[^"]*"','',s)
    return s[:420]
wanted=['Basic Allowance','The Basic Allowance includes','Special Responsibility Allowance (','Chairperson/Vice']
for p in root.iter(W+'p'):
    t=text(p)
    for w in wanted:
        if t.startswith(w) or (w in t and len(t)<80):
            print('PARA', repr(t[:50])); print('   ', ppr_brief(p)); wanted.remove(w); break
num=etree.fromstring(z.read('word/numbering.xml'))
nums={n.get(W+'numId'):n for n in num.iter(W+'num')}
for nid in ['1','2','3','4','5','6']:
    n=nums.get(nid)
    if n is None: continue
    aid=n.find(W+'abstractNumId').get(W+'val')
    ovr=[(o.get(W+'ilvl'), etree.tostring(o).decode()[:120]) for o in n.iter(W+'lvlOverride')]
    print('num', nid, 'abstract', aid, 'overrides', ovr[:3])
for a in num.iter(W+'abstractNum'):
    lv=[]
    for l in a.iter(W+'lvl')[:3] if False else list(a.iter(W+'lvl'))[:3]:
        st=l.find(W+'start'); fmt=l.find(W+'numFmt'); txt=l.find(W+'lvlText'); rs=l.find(W+'lvlRestart')
        lv.append((l.get(W+'ilvl'), st.get(W+'val') if st is not None else None, fmt.get(W+'val') if fmt is not None else None, txt.get(W+'val') if txt is not None else None, rs.get(W+'val') if rs is not None else None))
    print('abstract', a.get(W+'abstractNumId'), lv)