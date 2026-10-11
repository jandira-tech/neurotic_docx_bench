"""Make the 600-compare redline sample 600 distinct document pairs.

sample600_balanced.csv held 600 compares of 521 pairs: 77 pairs twice and one three times
(separate Word compare runs of the same two documents). A pair counted twice scores one
tool output twice. This keeps one compare per pair (the pair's first key in gen_pairs.csv
when the sample holds it, else the first listed) and draws 79 new pairs with
``extend_by_family``: unused pairs of the scarce states first (comments + tracking), then
spread over document families. Every compare has its Word oracle on disk.

Run from the bench root:  uv run python results/release_0.11.2/distinct_pairs_600.py
Writes results/redlines_0929_full/sample600_pairs.csv.
"""
from collections import Counter
from pathlib import Path

from neurotic_docx_bench import jubarte_release_info as jri

SEED = 20261003
ROOT = Path()
RUN = ROOT / jri.RUN_DIR
FRESH = jri.COMPARE_REGEN / 'out'

gen = jri.read_csv(RUN / 'gen_pairs.csv')
first = jri.first_keys(gen)
pool = [r for r in jri.read_csv(RUN / 'pool_pairs.csv')
        if (r['base'], r['next']) in first and jri.oracle_for(r, FRESH, ROOT)[1].is_file()]
by_key = {r['key']: r for r in pool}
held = [by_key[r['key']] for r in jri.read_csv(RUN / 'sample600_balanced.csv')]
kept: dict[tuple[str, str], dict] = {}
for r in held:
    pair = (r['base'], r['next'])
    if pair not in kept or r['key'] == first[pair]:
        kept[pair] = r
sample = list(kept.values())
covered = {r['key'] for r in gen if jri.docxodus_pdf(ROOT, r['key']).is_file()}
want = 600 - len(sample)
scarce = [r for r in pool if r['state'] != jri.FILL_STATE]
grown = jri.extend_by_family(sample, [*sample, *scarce], want, SEED, covered, first)
out = jri.extend_by_family(grown, pool, 600 - len(grown), SEED, covered, first)
added = out[len(sample):]
pairs = {(r['base'], r['next']) for r in out}
assert len(out) == len(pairs) == len({r['key'] for r in out}) == 600, (len(out), len(pairs))
jri.write_csv(RUN / 'sample600_pairs.csv', jri.GEN_FIELDS, out)
print(f'kept {len(sample)} of {len(held)} compares (one per pair); added {len(added)} new pairs '
      f'({len(grown) - len(sample)} from scarce states, {len(out) - len(grown)} by family)')
print('added by state', dict(Counter(r['state'] for r in added)))
print('sample by state', dict(Counter(r['state'] for r in out)))
print('families', len({jri.family(r['base']) for r in out}), 'of', len({jri.family(r['base']) for r in pool}))
print('new pairs with a docxodus Word PDF already:', sum(first[r['base'], r['next']] in covered for r in added))
print('new pairs with a jubarte redline already:',
      sum((RUN / 'jubarte-0.11.2/docx' / f'{first[r["base"], r["next"]]}_jubarte-0.11.2.docx').is_file() for r in added))
