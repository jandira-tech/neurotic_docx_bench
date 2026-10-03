# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
import fitz, glob, collections, json, os
ids=['d192336305','cbb3bab843','0edc50c464','9134397db6']
def fonts(path):
    c=collections.Counter()
    for p in fitz.open(path):
        for b in p.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']:
                    c[(s['font'],round(s['size'],1))]+=len(s['text'])
    return c.most_common(3)
for i in ids:
    o=glob.glob(f'/tmp/pdf-300/work/oracle/*{i}*')
    ours=glob.glob(f'/tmp/pdf-300/work-pdf3/jubarte/*{i}*.pdf')+glob.glob(f'/tmp/pdf-300/work*/jubarte/**/*{i}*.pdf', recursive=True)
    print(i, 'word', fonts(o[0]) if o else None)
    print(i, 'ours', fonts(ours[0]) if ours else ('none', ))
    for line in open('/tmp/pdf-300/work-pdf3/jubarte/scores.checkpoint.jsonl') if os.path.exists('/tmp/pdf-300/work-pdf3/jubarte/scores.checkpoint.jsonl') else []:
        if i in line:
            r=json.loads(line); print('   score', round(r['result']['overall_score'],1), r['result'].get('page_count_oracle'), r['result'].get('page_count_candidate'))