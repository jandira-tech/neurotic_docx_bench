# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob, os, zipfile, re, json, statistics
out=[]
for state in ['clean','tracking_without_comments','with_comments_clean','with_comments_tracking']:
    for pdf in sorted(glob.glob(f'corpus/word/{state}/pdf/*.pdf')):
        stem=os.path.basename(pdf)[:-4]
        if '_vs_' in stem: continue
        try: doc=fitz.open(pdf)
        except Exception: continue
        pitches=[]
        for p in doc[:2]:
            for b in p.get_text('rawdict')['blocks']:
                for l in b.get('lines',[]):
                    for s in l['spans']:
                        if 'Courier' in s['font'] and abs(s['size']-12.0)<0.3 and len(s['chars'])>=12:
                            xs=[c['bbox'][0] for c in s['chars']]
                            d=[round(b_-a_,2) for a_,b_ in zip(xs,xs[1:]) if 6<b_-a_<9]
                            pitches.extend(d)
        if len(pitches)<20: continue
        docx=f'corpus/word/{state}/docx/{stem}.docx'
        flags=''
        try:
            z=zipfile.ZipFile(docx); st=z.read('word/settings.xml').decode() if 'word/settings.xml' in z.namelist() else ''
            flags=','.join(f for f in ['usePrinterMetrics','truncateFontHeightsLikeWP6','subFontBySize','useWord97LineBreakRules'] if f in st)
            mode=re.search(r'compatibilityMode"[^>]*w:val="(\d+)"', st); flags+=' mode='+(mode.group(1) if mode else '?')
        except Exception: pass
        out.append(dict(id=stem[:10], state=state, median=statistics.median(pitches), n=len(pitches), flags=flags))
json.dump(out, open('/tmp/survey_courier.json','w'), indent=1)
for r in out: print(r)
print('n', len(out))