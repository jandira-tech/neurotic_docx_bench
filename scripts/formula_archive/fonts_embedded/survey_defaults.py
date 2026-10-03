# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, re, glob, os, collections, sys, json
import fitz
out=[]
for state in ['clean','tracking_without_comments','with_comments_clean','with_comments_tracking']:
    for p in sorted(glob.glob(f'corpus/word/{state}/docx/*.docx')):
        try:
            z=zipfile.ZipFile(p); names=set(z.namelist())
        except Exception: continue
        if 'word/styles.xml' not in names: continue
        s=z.read('word/styles.xml').decode('utf8','replace')
        dd=re.search(r'<w:docDefaults.*?</w:docDefaults>|<w:docDefaults\s*/>', s, re.S)
        rpd=dd and re.search(r'<w:rPrDefault.*?</w:rPrDefault>|<w:rPrDefault\s*/>', dd.group(0), re.S)
        normal=re.search(r'<w:style [^>]*w:type="paragraph"[^>]*w:default="1".*?</w:style>|<w:style [^>]*w:default="1"[^>]*w:type="paragraph".*?</w:style>', s, re.S)
        no_dd_font = rpd is not None and 'rFonts' not in rpd.group(0)
        normal_font = normal is not None and 'rFonts' in normal.group(0)
        theme = any(n.startswith('word/theme') for n in names)
        doc=z.read('word/document.xml').decode('utf8','replace')
        widthless = len(re.findall(r'<w:gridCol\s*/>', doc)) + len(re.findall(r'<w:gridCol(?![^>]*w:w=)[^>]*/>', doc))
        if no_dd_font and not normal_font or widthless:
            stem=os.path.basename(p)[:-5]
            pdf=f'corpus/word/{state}/pdf/{stem}.pdf'
            font=None
            if os.path.exists(pdf):
                c=collections.Counter()
                for pg in fitz.open(pdf):
                    for b in pg.get_text('dict')['blocks']:
                        for l in b.get('lines',[]):
                            for sp in l['spans']: c[sp['font']]+=len(sp['text'])
                font=c.most_common(2)
            out.append(dict(id=stem[:10], state=state, no_dd_font=no_dd_font, normal_font=normal_font, theme=theme, widthless=widthless, font=font, has_pdf=os.path.exists(pdf)))
json.dump(out, open('/tmp/survey_defaults.json','w'), indent=1)
for r in out: print(r)
print('n', len(out))