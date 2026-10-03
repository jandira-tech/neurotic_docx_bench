# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, re, glob, os, fitz, collections
rows=[]
for line in open('/tmp/pdf-300/list.txt'):
    d=line.strip()
    if not d: continue
    try: z=zipfile.ZipFile(d)
    except Exception: continue
    st=z.read('word/styles.xml').decode('utf8','replace') if 'word/styles.xml' in z.namelist() else ''
    dd=re.search(r'<w:rPrDefault>(.*?)</w:rPrDefault>', st, re.S)
    fam=re.findall(r'w:ascii="([^"]+)"', dd.group(1)) if dd else []
    theme=re.findall(r'w:asciiTheme="([^"]+)"', dd.group(1)) if dd else []
    sz=re.findall(r'<w:sz w:val="(\d+)"', dd.group(1)) if dd else []
    normal=re.search(r'<w:style [^>]*w:styleId="Normal"[^>]*>(.*?)</w:style>', st, re.S)
    nfam=re.findall(r'w:ascii="([^"]+)"', normal.group(1)) if normal else []
    if not fam and not theme and not nfam:
        key=os.path.basename(d)[:-5]; state=d.split('/')[2]
        o=glob.glob(f'/tmp/pdf-300/work/oracle/{state}__{key}.pdf')
        fonts=collections.Counter()
        if o:
            p=fitz.open(o[0])[0]
            for b in p.get_text('dict')['blocks']:
                for l in b.get('lines',[]):
                    for s in l['spans']:
                        if s['bbox'][0]<400: fonts[(s['font'],round(s['size']/0.75,1) if 'comments' in state else round(s['size'],1))]+=len(s['text'])
        rows.append((key[:48], sz, fonts.most_common(2)))
print(len(rows),'sample docs without any default/Normal family')
for r in rows[:25]: print(r)