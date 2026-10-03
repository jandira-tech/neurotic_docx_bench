# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, collections, statistics as st
rows=json.load(open('/tmp/balloon_spec.json'))
print(sorted(rows[0].keys()))
by=collections.Counter()
out=[]
for r in rows:
    k=(r['pane'][2]-r['pane'][0])/257.3
    out.append((r['doc'], r['state'], r['label_font'], round(r['label_size']/k,2), r['text_fonts'], round(r['text_size']/k,2), round(k,4), r['label_text'].strip(), tuple(round(c,3) for c in r['stroke'])))
for o in out[:40]: print(o)
print('label sizes layout:', collections.Counter(round(o[3]) for o in out).most_common())
print('text sizes layout:', collections.Counter(round(o[5]) for o in out).most_common())
print('label fonts:', collections.Counter(o[2] for o in out).most_common())