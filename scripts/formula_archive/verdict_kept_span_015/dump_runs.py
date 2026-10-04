#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Print each body paragraph of a docx as its runs: eq[...] ins[...] del[...], with the mark kind."""
import re, sys, zipfile
for path in sys.argv[1:]:
    x = zipfile.ZipFile(path).read('word/document.xml').decode()
    print('==', path.split('/')[-1][:90])
    for p in re.findall(r'<w:p[ >].*?</w:p>', x, re.S):
        out = []
        for m in re.finditer(r'<w:(ins|del) [^>]*>(.*?)</w:\1>|<w:r>(.*?)</w:r>|<w:r [^>]*>(.*?)</w:r>', p, re.S):
            kind = m.group(1) or 'eq'
            body = m.group(2) or m.group(3) or m.group(4) or ''
            t = ''.join(re.findall(r'<w:(?:t|delText)[^>]*>([^<]*)</w:(?:t|delText)>', body))
            if t:
                out.append(f'{kind}[{t}]')
        head = p.split('</w:pPr>')[0] if '</w:pPr>' in p else ''
        mark = 'ins¶' if '<w:ins ' in head else ('del¶' if '<w:del ' in head else '¶')
        print(' ', mark, ' '.join(out))
