# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json
rows=json.load(open('/tmp/justify3_eval.json'))
# boundary per (face,last): max kept over, min wrapped over, and any inversions
import collections
g=collections.defaultdict(list)
for r in rows: g[(r['face'],r['last'],r['last_w'],r['space'])].append(r)
for k in sorted(g, key=lambda k:(k[0],k[2])):
    rs=sorted(g[k], key=lambda r:r['over'])
    seq=''.join('K' if r['kept'] else 'w' for r in rs)
    mk=max((r['over'] for r in rs if r['kept']), default=None); mw=min((r['over'] for r in rs if not r['kept']), default=None)
    print(f"{k[0][:7]:7} {k[1]:12} w={k[2]:5.1f} sp={k[3]:.2f} kept<={mk} wrapped>={mw}  {seq}  cap/w={(mk or 0)/k[2]:.3f}..{(mw or 0)/k[2]:.3f}")