"""Draw the 2026-10-11 site samples: 800 new DOCX->PDF documents, 1000 new redline pairs.

Hard quotas: every Portuguese document/pair, 50% English, the rest spread over the other
languages (weight 1/sqrt(language count)). Soft targets via weighted sampling without
replacement (Efraimidis-Spirakis, seed 20261011): state, page bin, document type, and for
pairs the corpus set (unrelated-document pairs of redlines_a100_b10 down-weighted).
Excludes everything the published site already shows.
"""
import csv, json, math, random, collections
from pathlib import Path
H = Path(__file__).parent
SEED = 20261011
pb = lambda p: '1' if p <= 1 else '2-3' if p <= 3 else '4-10' if p <= 10 else '11+'
def shares(rows, key):
    c = collections.Counter(key(r) for r in rows); n = len(rows); return {k: v / n for k, v in c.items()}
def draw(rows, n, targets, rng):
    """targets: list of (keyfn, {value: share}); weight = prod(target/available)."""
    av = [shares(rows, k) for k, _ in targets]
    def w(r):
        x = 1.0
        for (k, t), a in zip(targets, av):
            v = k(r)
            if t.get(v) is not None: x *= t[v] / a[v]  # a target share
            elif v not in t and '*' not in t: x *= 1e-9  # not wanted
            # else: '*' -> left at its natural share
        return x
    keyed = sorted(rows, key=lambda r: -(rng.random() ** (1 / w(r))))
    return keyed[:n]
def lang_draw(rows, n, targets, rng):
    pt = [r for r in rows if r['lang'] == 'pt']
    en = [r for r in rows if r['lang'] == 'en']
    rest = [r for r in rows if r['lang'] not in ('pt', 'en')]
    n_en = n // 2
    lc = collections.Counter(r['lang'] for r in rest)
    tl = {l: 1 / math.sqrt(c) for l, c in lc.items()}; s = sum(tl[l] * lc[l] for l in lc)
    tl = {l: tl[l] * lc[l] / s for l in lc}
    return pt + draw(en, n_en, targets, rng) + draw(rest, n - n_en - len(pt), targets + [(lambda r: r['lang'], tl)], rng)
def main():
    rng = random.Random(SEED)
    d = list(csv.DictReader(open(H / 'inv_documents.csv'))); c = list(csv.DictReader(open(H / 'inv_comparisons.csv')))
    old = set(json.load(open('/tmp/grokclean/old_d2p_stems.json')))
    oldc = {x['case'] for x in json.load(open('/tmp/grokclean/old_redline_cases.json'))}
    d = [r for r in d if r['pdf'] and int(r['pages']) > 0 and f"{r['state']}__{r['stem']}" not in old]
    seen, g = set(), []
    for r in sorted(c, key=lambda r: r['id']):
        if not (r['base'] and r['next'] and int(r['pages']) > 0) or r['id'] in oldc or (r['base'], r['next']) in seen: continue
        seen.add((r['base'], r['next'])); g.append(r)
    page = lambda r: pb(int(r['pages']))
    synth = lambda r: 'synthetic' if r['type'] == 'synthetic' else 'real'
    d2p = lang_draw(d, 800, [(lambda r: r['state'], {'clean': .55, 'tracking_without_comments': .2, 'with_comments_clean': .1, 'with_comments_tracking': .15}),
                             (page, {'1': .3, '2-3': .3, '4-10': .25, '11+': .15}), (synth, {'synthetic': .3, 'real': .7})], rng)
    red = lang_draw(g, 1000, [(lambda r: r['state'], {'tracking_without_comments': .82, 'with_comments_tracking': .15, '*': None}),
                              (page, {'1': .25, '2-3': .3, '4-10': .3, '11+': .15}), (synth, {'synthetic': .35, 'real': .65}),
                              (lambda r: r['sets'].split(';')[0], {'redlines_a100_b10': .15, '*': None})], rng)
    for name, rows in (('sample_docx_to_pdf.csv', d2p), ('sample_redlines.csv', red)):
        rows = sorted(rows, key=lambda r: r['id'])
        with open(H / name, 'w', newline='') as f:
            w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
        print(name, len(rows))
        for k in ('lang', 'state', 'type'): print(' ', k, collections.Counter(r[k] for r in rows).most_common(10))
        print('  pages', sorted(collections.Counter(page(r) for r in rows).items()))
        if 'sets' in rows[0]: print('  sets', collections.Counter(r['sets'].split(';')[0] for r in rows).most_common(6))
main()
