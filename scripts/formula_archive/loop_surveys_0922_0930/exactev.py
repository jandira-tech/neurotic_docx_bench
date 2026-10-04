# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,re,glob,os
import pymupdf as fitz
G='/Users/arthrod/temp/T/neurotic_docx_bench/grok_run'
out=[]
for f in sorted(glob.glob(G+'/fixtures_500/*.docx')):
    try:
        z=zipfile.ZipFile(f); d=z.read('word/document.xml').decode('utf8','ignore')
    except Exception: continue
    b=d.find('<w:body>'); 
    m=re.search(r'<w:p[ >].*?</w:p>',d[b:],re.S)
    if not m: continue
    p=m.group(0)
    sp=re.search(r'<w:spacing [^>]*w:lineRule="exact"[^>]*>',p)
    if not sp: continue
    if '<w:tbl' in d[b:b+m.end()]: continue
    t=''.join(re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>',p))
    if len(t.strip())<3: continue
    line=int(re.search(r'w:line="(\d+)"',sp.group(0)).group(1))/20
    bef=re.search(r'w:before="(\d+)"',sp.group(0)); bef=int(bef.group(1))/20 if bef else None
    mar=re.search(r'<w:pgMar [^>]*w:top="(-?\d+)"',d); top=int(mar.group(1))/20 if mar else None
    stem=os.path.basename(f)[:-5]
    try:
        doc=fitz.open(f'{G}/fixtures_500_pdf/{stem}.pdf')
    except Exception: continue
    spans=[s for bl in doc[0].get_text('dict')['blocks'] for l in bl.get('lines',[]) for s in l['spans'] if s['text'].strip()]
    first=[s for s in spans if t.strip()[:4] in s['text']]
    if not first: continue
    s0=first[0]
    out.append((stem[:10],line,bef,top,round(s0['origin'][1],2),round(s0['size'],2),s0['font'],t[:25]))
for o in out: print(o)
