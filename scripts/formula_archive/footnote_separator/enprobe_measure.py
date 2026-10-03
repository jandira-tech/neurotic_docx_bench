# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob, os, sys
d = sys.argv[1] if len(sys.argv) > 1 else '/tmp/enprobe/pdf'
for f in sorted(glob.glob(d + '/*.pdf')):
    doc = fitz.open(f)
    p = doc[0]
    rules = [(round(r['rect'].y0, 2), round(r['rect'].y1 - r['rect'].y0, 2), round(r['rect'].x0, 2), round(r['rect'].x1 - r['rect'].x0, 2)) for r in p.get_drawings()]
    lines = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                lines.append((round(s['origin'][1], 2), round(s['size'], 2), s['text'][:28]))
    lines.sort()
    print(os.path.basename(f), 'pages', doc.page_count, 'rules', rules)
    for y, sz, t in lines:
        print(f'    y {y:7.2f} sz {sz:5.2f} {t!r}')
