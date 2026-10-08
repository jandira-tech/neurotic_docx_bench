"""Extend the two 0.11.2 release samples from 500 to 600, spread over document sources.

The 500-compare redline sample was balanced by compare state only; 54 of the pool's 123
document families had no compare in it. The extra 100 are drawn by
``jubarte_release_info.extend_by_family``: new pairs only, each with its Word oracle on
disk, one compare from every family the sample lacks, then the families furthest below
their share of the pool.

The conversion sample (150 / 150 / 100 / 100 by state) takes every remaining
``with_comments_clean`` fixture the corpus has (17) and 83 more ``with_comments_tracking``
ones, the same family rule inside each state.

Run from the bench root:  uv run python results/release_0.11.2/extend_samples_to_600.py
Writes results/redlines_0929_full/sample600_balanced.csv and
results/release_0.11.2/convert600.txt; prints what it added.
"""
from collections import Counter
from pathlib import Path

from neurotic_docx_bench import jubarte_release_info as jri

SEED = 20261003
ROOT = Path()
RUN = ROOT / jri.RUN_DIR
FRESH = jri.COMPARE_REGEN / 'out'


def redline() -> None:
    gen = jri.read_csv(RUN / 'gen_pairs.csv')
    first = jri.first_keys(gen)
    pool = [r for r in jri.read_csv(RUN / 'pool_pairs.csv')
            if (r['base'], r['next']) in first and jri.oracle_for(r, FRESH, ROOT)[1].is_file()]
    by_key = {r['key']: r for r in pool}
    sample = [by_key[r['key']] for r in jri.read_csv(RUN / 'sample500_balanced.csv')]
    covered = {r['key'] for r in gen if jri.docxodus_pdf(ROOT, r['key']).is_file()}
    out = jri.extend_by_family(sample, pool, 100, SEED, covered, first)
    added = out[len(sample):]
    assert len(out) == 600 and len({r['key'] for r in out}) == 600
    jri.write_csv(RUN / 'sample600_balanced.csv', jri.GEN_FIELDS, out)
    fam = lambda rows: Counter(jri.family(r['base']) for r in rows)  # noqa: E731
    print(f'redline: {len(pool)} eligible compares, {len(fam(pool))} families; sample families '
          f'{len(fam(sample))} -> {len(fam(out))}; pairs {len({(r["base"], r["next"]) for r in out})}')
    print('  added by state', dict(Counter(r['state'] for r in added)))
    print('  added by family', dict(fam(added).most_common(12)), '...')
    print('  added with a docxodus Word PDF already:', sum(first[r['base'], r['next']] in covered for r in added))
    print('  sample by state', dict(Counter(r['state'] for r in out)))


def conversion() -> None:
    have = [line.strip() for line in (ROOT / 'results/release_0.11.2/convert500.txt').read_text().splitlines()
            if line.strip()]
    out = list(have)
    for state, extra in (('with_comments_clean', 17), ('with_comments_tracking', 83)):
        def row(docx: Path) -> dict:
            return {'key': docx.stem, 'base': docx.stem, 'next': docx.stem, 'state': jri.FILL_STATE}
        folder = ROOT / 'corpus/word' / state
        pool = [row(d) for d in sorted((folder / 'docx').glob('*.docx')) if (folder / 'pdf' / f'{d.stem}.pdf').is_file()]
        held = {Path(h).stem for h in have if h.startswith(f'corpus/word/{state}/')}
        sample = [r for r in pool if r['key'] in held]
        grown = jri.extend_by_family(sample, pool, extra, SEED)
        added = grown[len(sample):]
        assert len(added) == extra, (state, len(added))
        out += [f'corpus/word/{state}/docx/{r["key"]}.docx' for r in added]
        print(f'conversion {state}: {len(sample)} -> {len(grown)} of {len(pool)}; families '
              f'{len({jri.family(r["base"]) for r in sample})} -> {len({jri.family(r["base"]) for r in grown})}')
    assert len(out) == len(set(out)) == 600
    (ROOT / 'results/release_0.11.2/convert600.txt').write_text('\n'.join(out) + '\n')
    print('  by state', dict(Counter(line.split('/')[2] for line in out)))


if __name__ == '__main__':
    redline()
    conversion()
