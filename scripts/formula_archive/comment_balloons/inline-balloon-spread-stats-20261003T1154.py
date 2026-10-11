# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import json, statistics
rows=json.load(open('/tmp/balloon_spec.json'))
def spread(xs): return (round(statistics.median(xs),3), round(min(xs),3), round(max(xs),3), round(statistics.pstdev(xs),3))
print('bx page units      ', spread([r['bx'] for r in rows]))
print('bx layout units    ', spread([r['bx']/r['sc'] for r in rows]))
print('bx1 page           ', spread([r['bx1'] for r in rows]), ' layout', spread([r['bx1']/r['sc'] for r in rows]))
print('tx page            ', spread([r['tx'] for r in rows]), ' layout', spread([r['tx']/r['sc'] for r in rows]))
ls=[r for r in rows if r['label_size']]
print('label size page    ', spread([r['label_size'] for r in ls]), ' layout', spread([r['label_size']/r['sc'] for r in ls]))
pt=[r for r in rows if r['pitch']]
print('pitch page         ', spread([r['pitch'] for r in pt]), ' layout', spread([r['pitch']/r['sc'] for r in pt]))
print('stroke page        ', spread([r['stroke_w'] for r in rows if r['stroke_w']]), ' layout', spread([r['stroke_w']/r['sc'] for r in rows if r['stroke_w']]))
print('conn w page        ', spread([r['conn_w'] for r in rows if r['conn_w']]), ' layout', spread([r['conn_w']/r['sc'] for r in rows if r['conn_w']]))
print('pane width page    ', spread([r['pane'][2]-r['pane'][0] for r in rows]), ' layout', spread([(r['pane'][2]-r['pane'][0])/r['sc'] for r in rows]))
print('ty (first line top - box top) page', spread([r['ty'] for r in rows if r['ty'] is not None]))
print('box h per line page', spread([r['hl'] for r in rows]), ' layout', spread([r['hl']/r['sc'] for r in rows]))
one=[r for r in rows if r['n_lines']==1]; print('1-line box height page', spread([r['box'][3]-r['box'][1] for r in one]), ' layout', spread([(r['box'][3]-r['box'][1])/r['sc'] for r in one]))
# label text pattern
import re, collections
print(collections.Counter(re.sub(r'\[.*?\]','[X]',r['label_text'] or '').strip() for r in rows).most_common(3))
print([r['label_text'] for r in rows if r['label_text']][:6])