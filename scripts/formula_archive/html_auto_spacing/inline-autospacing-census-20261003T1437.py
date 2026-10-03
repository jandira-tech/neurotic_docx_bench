# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import zipfile, glob, re
# all 16 auto+doNot docs: ids
ids=set()
for f in sorted(glob.glob('corpus/word/*/docx/*.docx')):
    z=zipfile.ZipFile(f)
    if 'word/settings.xml' not in z.namelist(): continue
    st=z.read('word/settings.xml').decode('utf8','ignore')
    if 'doNotUseHTMLParagraphAutoSpacing' not in st: continue
    doc=z.read('word/document.xml').decode('utf8','ignore')
    if 'Autospacing="1"' in doc or 'Autospacing="true"' in doc or 'Autospacing="on"' in doc:
        ids.add(f.split('/')[-1][:10])
print(sorted(ids))
sample=open('/tmp/pdf-300/list.txt').read()
print('in sample:', [i for i in ids if i in sample])