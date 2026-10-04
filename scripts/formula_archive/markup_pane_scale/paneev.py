# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,re,glob,os
import pymupdf as fitz
G='/Users/arthrod/temp/T/neurotic_docx_bench/grok_run'
rows=[]
for f in sorted(glob.glob(G+'/fixtures_500/*.docx')):
    stem=os.path.basename(f)[:-5]
    try:
        z=zipfile.ZipFile(f); names=set(z.namelist())
        d=z.read('word/document.xml').decode('utf8','ignore')
        st=z.read('word/settings.xml').decode('utf8','ignore') if 'word/settings.xml' in names else ''
    except Exception: continue
    ncom=d.count('<w:commentReference')
    nins=len(re.findall(r'<w:ins\b',d)); ndel=len(re.findall(r'<w:del\b',d))
    nfmt=len(re.findall(r'<w:rPrChange\b|<w:pPrChange\b',d))
    tr='<w:trackRevisions' in st
    try:
        doc=fitz.open(f'{G}/fixtures_500_pdf/{stem}.pdf')
        txt=''.join(doc[i].get_text() for i in range(min(3,len(doc))))
    except Exception: continue
    pane=('Commented [' in txt) or ('Deleted:' in txt) or ('Formatted:' in txt) or ('Inserted:' in txt)
    if ncom or nins or ndel or nfmt or pane:
        rows.append((stem[:10],pane,ncom,nins,ndel,nfmt,tr))
for r in rows: print(r)
print(len(rows))
