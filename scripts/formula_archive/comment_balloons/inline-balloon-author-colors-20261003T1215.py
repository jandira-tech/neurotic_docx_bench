# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, collections, glob, zipfile, re
rows=json.load(open('/tmp/balloon_spec.json'))
pal=['D13438','0078D4','5C2E91','498205','CC3595','7160E8','038387','6D5700','CF0F1F','4E6AED','B146C2','394146','0B6A0B']
def hexc(c): return '%02X%02X%02X'%tuple(int(round(v*255)) for v in c)
docs=collections.defaultdict(dict)
for r in rows:
    if not r.get('label_text'): continue
    m=re.match(r'Commented \[(.*?)(\d+)\]', r['label_text'])
    if not m: continue
    docs[(r['doc'],r['state'])][int(m.group(2))]=(m.group(1),hexc(r['stroke']))
agree=collections.Counter(); shown=0; rows_out=[]
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
    order=[]
    for rid in refs:
        au=meta.get(rid,('?',''))[0]
        if au not in order: order.append(au)
    # authors of tracked changes too (w:ins/w:del) in order of appearance, merged with comment authors by document position
    allau=[]
    for m in re.finditer(r'<w:(?:ins|del|rPrChange|pPrChange|commentReference) [^>]*?(?:w:author="([^"]*)"|w:id="([^"]+)")[^>]*>', d):
        au=m.group(1)
        if au is None:
            au=meta.get(m.group(2),(None,))[0]
        if au and au not in allau: allau.append(au)
    for seq,(ini,col) in sorted(seqs.items()):
        if seq-1>=len(refs): continue
        au=meta.get(refs[seq-1],('?',''))[0]
        pi=pal.index(col) if col in pal else -1
        ro=order.index(au); ao=allau.index(au) if au in allau else -9
        agree['ref_order']+=(ro==pi); agree['all_order']+=(ao==pi); agree['n']+=1
        rows_out.append((doc,seq,au,ro,ao,pi,col,len(order),len(allau)))
        if shown<30 and ao!=pi:
            print(doc,'seq',seq,repr(au[:22]),'ref-order',ro,'all-rev-order',ao,'palette',pi,col,'| authors',len(order),'all',len(allau)); shown+=1
print(agree)
# distribution of palette index for single-author docs
single=collections.Counter(pi for (doc,seq,au,ro,ao,pi,col,n,na) in rows_out if n==1 and na==1)
print('single-author docs palette idx:', single)