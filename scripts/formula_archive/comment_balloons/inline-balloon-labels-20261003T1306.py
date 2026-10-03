# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, re, collections
rows=json.load(open('/tmp/balloon_spec.json'))
labels=collections.defaultdict(list)
for r in rows:
    if r.get('label_text'): labels[(r['doc'],r['state'])].append((r['page'], round(r['box'][1],1), r['label_text'].strip()))
n=0
for k,v in labels.items():
    v.sort()
    tags=[t for _,_,t in v]
    if any('R' in re.sub(r'^Commented \[','',t).split(']')[0][1:] for t in tags) or len(set(re.search(r'\[([A-Za-z]*)',t).group(1) for t in tags))>1:
        print(k[0], tags[:12]); n+=1
    if n>=14: break