#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
"""Pick the untouched holdout gate from the candidate pool.

Per category (comments+tracking, comments-clean, tracking, clean, long):
5 documents drawn at random from the lowest-scoring 40 % of the pool on the
main baseline, 5 from the rest. Writes /tmp/pdf-hold/list.txt and a
holdout.json manifest with the category and baseline score of each pick.
"""
import json, os, random, glob, re
from pathlib import Path

pool = json.load(open('/tmp/pdf-holdout-pool.json'))
rows = {}
for line in open('/tmp/pdf-hold/work-pool-main/jubarte/scores.checkpoint.jsonl'):
    r = json.loads(line)
    rows[r['key']] = r['result']['overall_score']
res = json.load(open('/tmp/pdf-hold/pool-main.json'))
tool = next(iter(res['tools'].values()))
per = dict(tool['per_doc'])
fails = {f['doc'] for f in tool.get('generate_failures', [])}

def key_for(path):
    # bench stem: <state>__<id>_<stem prefix>; match by the sha prefix in the filename
    st = Path(path).parts[-3]
    stem = Path(path).stem
    cands = [k for k in per if k.startswith(st + '__') and k.split('__', 1)[1].split('_', 1)[0] in stem]
    if not cands:
        cands = [k for k in per if k.split('__', 1)[1][11:] and k.split('__', 1)[1][11:] in stem.replace(' ', '_')]
    return cands[0] if len(cands) == 1 else None

rng = random.Random(51)
picks = {}
used = set()
for cat, docs in pool.items():
    scored = []
    for d in docs:
        k = key_for(d)
        if k is None or d in used:
            continue
        scored.append((per[k], d, k))
    scored.sort()
    n = len(scored)
    cut = max(1, int(n * 0.4))
    low, high = scored[:cut], scored[cut:]
    sel = rng.sample(low, min(5, len(low))) + rng.sample(high, min(5, len(high)))
    picks[cat] = [{'doc': os.path.abspath(d), 'key': k, 'main': round(s, 2)} for s, d, k in sel]
    used.update(d for _, d, _ in sel)
    print(f'{cat:28s} pool {n:3d} low-cut {scored[cut-1][0]:.1f}  picked {len(sel)}: '
          + ', '.join(f'{s:.0f}' for s, _, _ in sel))

json.dump(picks, open('/tmp/pdf-hold/holdout.json', 'w'), indent=1)
with open('/tmp/pdf-hold/list.txt', 'w') as f:
    for cat in picks:
        for p in picks[cat]:
            f.write(p['doc'] + '\n')
allp = [p for c in picks.values() for p in c]
print('holdout', len(allp), 'docs; main mean', round(sum(p['main'] for p in allp) / len(allp), 2))
