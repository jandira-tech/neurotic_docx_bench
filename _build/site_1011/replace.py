"""Replace the redline pairs Word 16.115 could not compare or print (2026-10-11).

    python3 -I replace.py stage     # 3 ranked candidates per failed pair -> word_compare_r/{A,B}
    python3 -I replace.py pick      # after Word: first candidate Word redlined replaces each failure

Word's own compare is the reference, so a pair without it cannot be scored. A replacement
comes from the failed pair's stratum: language group (en / other; Portuguese pairs are all
in the sample already), state, page bin and synthetic/real; never a pair already sampled,
already published, or with the same base and next. Ranked by a seeded shuffle (20261012).
`pick` keeps sample_redlines_v1.csv, writes the new sample_redlines.csv and moves the
replacements' Word redline and PDF into word_compare/{docx,out}.
"""
import csv, json, random, shutil, sys
from pathlib import Path
H = Path(__file__).parent
B = Path('/Users/arthrod/temp/T/neurotic_docx_bench')
C = B / 'corpus/word'
R = B / 'results/site_1011'
WR = R / 'word_compare_r'
pb = lambda p: '1' if p <= 1 else '2-3' if p <= 3 else '4-10' if p <= 10 else '11+'
def stratum(r):
    return ('en' if r['lang'] == 'en' else 'other', r['state'], pb(int(r['pages'])), r['type'] == 'synthetic')
def failed(rows):
    ok = {p.name.split('__vs__')[0] for p in (R / 'word_compare/out').glob('*.pdf')}
    return [r for r in rows if r['id'] not in ok]
def stage():
    rows = list(csv.DictReader(open(H / 'sample_redlines.csv')))
    oldc = {x['case'] for x in json.load(open('/tmp/grokclean/old_redline_cases.json'))}
    used = {r['id'] for r in rows} | oldc
    pairs = {(r['base'], r['next']) for r in rows}
    pool = []
    for r in sorted(csv.DictReader(open(H / 'inv_comparisons.csv')), key=lambda r: r['id']):
        if r['base'] and r['next'] and int(r['pages']) > 0 and r['id'] not in used and (r['base'], r['next']) not in pairs:
            pairs.add((r['base'], r['next'])); pool.append(r)
    rng = random.Random(20261012); rng.shuffle(pool)
    plan, taken = {}, set()
    for f in failed(rows):
        cands = [r for r in pool if stratum(r) == stratum(f) and r['id'] not in taken][:3]
        if len(cands) < 3:  # a thin stratum: relax the page bin, then synthetic/real
            cands += [r for r in pool if stratum(r)[:2] == stratum(f)[:2] and r['id'] not in taken and r not in cands][:3 - len(cands)]
        taken |= {r['id'] for r in cands}
        plan[f['id']] = [r['id'] for r in cands]
    for d in ('A', 'B'): (WR / d).mkdir(parents=True, exist_ok=True)
    byid = {r['id']: r for r in pool}
    for cid in taken:
        shutil.copy(C / (byid[cid]['base'] + '.docx'), WR / 'A' / f'{cid}.docx')
        shutil.copy(C / (byid[cid]['next'] + '.docx'), WR / 'B' / f'{cid}.docx')
    json.dump({'plan': plan, 'rows': {i: byid[i] for i in taken}}, open(H / 'replace_plan.json', 'w'), indent=1)
    print(f"{len(plan)} failed pairs, {len(taken)} candidates staged; short: {[k for k, v in plan.items() if len(v) < 3]}")
def pick():
    rows = list(csv.DictReader(open(H / 'sample_redlines.csv')))
    p = json.load(open(H / 'replace_plan.json'))
    ok = {x.name.split('__vs__')[0] for x in (WR / 'out').glob('*.pdf')}
    new, missing = {}, []
    for fid, cands in p['plan'].items():
        hit = next((c for c in cands if c in ok), None)
        if hit: new[fid] = p['rows'][hit]
        else: missing.append(fid)
    if not (H / 'sample_redlines_v1.csv').exists(): shutil.copy(H / 'sample_redlines.csv', H / 'sample_redlines_v1.csv')
    out = sorted([r for r in rows if r['id'] not in p['plan']] + list(new.values()), key=lambda r: r['id'])
    with open(H / 'sample_redlines.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(out)
    for r in new.values():
        for sub in ('out', 'docx'):
            for x in (WR / sub).glob(f"{r['id']}__vs__*"): shutil.copy(x, R / 'word_compare' / sub / x.name)
    print(f"replaced {len(new)}/{len(p['plan'])}; still without Word: {missing}; sample {len(out)} pairs")
{'stage': stage, 'pick': pick}[sys.argv[1]]()
