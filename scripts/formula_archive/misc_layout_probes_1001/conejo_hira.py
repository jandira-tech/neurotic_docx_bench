# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile,glob,re,sys,collections
c=collections.Counter(); ex=collections.defaultdict(list)
for f in glob.glob('word/*/docx/*.docx'):
    try:
        z=zipfile.ZipFile(f)
        for part in ('word/fontTable.xml','word/styles.xml','word/document.xml','word/theme/theme1.xml'):
            try: s=z.read(part).decode('utf-8','ignore')
            except Exception: continue
            for m in re.findall(r'(?:w:val|w:ascii|w:hAnsi|w:eastAsia|typeface|w:name)="(Hiragino[^"]*|ヒラギノ[^"]*)"',s):
                c[(part.split('/')[-1],m)]+=1; ex[m].append(f)
    except Exception as e: pass
for k,v in c.most_common(40): print(v,k)
for m,fs in ex.items(): print(m, len(set(fs)), sorted(set(fs))[:3])