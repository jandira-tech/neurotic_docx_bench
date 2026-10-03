# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, re, glob
for i in ['6d510ca476','eb6c0a6b3d','715d3d2b67','a4dedaa05a','0a1badc333','43432ba9ab']:
    p=glob.glob(f'corpus/word/*/docx/{i}*.docx')[0]
    z=zipfile.ZipFile(p); s=z.read('word/styles.xml').decode('utf8','replace')
    dd=re.search(r'<w:docDefaults.*?</w:docDefaults>', s, re.S)
    th=[n for n in z.namelist() if 'theme' in n]
    minor=None
    if th:
        t=z.read(th[0]).decode('utf8','replace')
        m=re.search(r'<a:minorFont>\s*<a:latin typeface="([^"]*)"', t); minor=m and m.group(1)
    normal=re.search(r'<w:style [^>]*w:default="1"[^>]*w:type="paragraph".*?</w:style>|<w:style [^>]*w:type="paragraph"[^>]*w:default="1".*?</w:style>', s, re.S)
    d=z.read('word/document.xml').decode('utf8','replace')
    print(i, 'minor=',minor, '\n  dd:', dd.group(0)[:260] if dd else None, '\n  normal:', normal.group(0)[:200] if normal else None, '\n  runs with rFonts:', len(re.findall(r'<w:rFonts', d)), 'runs:', len(re.findall(r'<w:r>|<w:r ', d)))