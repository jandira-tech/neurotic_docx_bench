"""The fixed evaluation sets (plan 7.1, #128): convert_860 and redline_600.

Everything here runs on small synthetic worlds under tmp_path — a bench root
with a miniature corpus and oracle PDFs, synthetic gen/sample/site/pool CSVs,
a synthetic cases-redline.json and a fake hub — so no test needs the real
corpus, Word, the network or git. The one test that reads the committed
results/sets/ skips while it does not exist (before `bench sets build` ran).

What is pinned, per issue #128:

* redline_600 holds every jubarte.pro case pair (the 234, origin jubarte_pro)
  plus pairs drawn from the 0.17.0 sample with draw_balanced — scarce states
  whole, tracking_without_comments spread over document families — exactly
  600 distinct pairs, seeded (20261103), so the same inputs give the same
  bytes;
* a pair whose oracle exists neither on disk nor on the hub is excluded
  (listed in sets.json with the reason) and replaced from the sample pool so
  the total stays;
* convert_860 is every site_fixtures_860.csv row plus each input's sha256;
* inputs missing locally are looked up on the hub (source=hf).
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from neurotic_docx_bench import fixed_sets as fs
from neurotic_docx_bench.jubarte_release_info import GEN_FIELDS, REDLINE_HEADER, read_csv

REPO = Path(__file__).resolve().parents[1]
SEED = 20261103
TOTAL = 12  # the scaled 600


def put(root: Path, rel: str, data: bytes | None = None) -> str:
    """Write a file under the bench root; return its sha256."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if data is not None else rel.encode())
    return hashlib.sha256(path.read_bytes()).hexdigest()


def gen_row(key: str, base: str, nxt: str, state: str, id_: str) -> dict:
    """A gen_pairs.csv row (paths relative to corpus/word, no extension)."""
    return {'key': key, 'base': base, 'next': nxt, 'state': state, 'id': id_, 'sets': 'synthetic',
            'docx': f'{state}/docx/{key}.docx', 'pdf': f'{state}/pdf/{key}.pdf'}


def sample_row(key: str, base: str, nxt: str, state: str, id_: str) -> dict:
    """A sample-CSV row (bench-root-relative paths, the release layout)."""
    return {'key': key, 'base': f'corpus/word/{base}.docx', 'next': f'corpus/word/{nxt}.docx',
            'docx': f'corpus/word/{state}/docx/{key}.docx', 'pdf': f'corpus/word/{state}/pdf/{key}.pdf',
            'state': state, 'id': id_, 'sets': 'synthetic', 'oracle': 'corpus',
            'oracle_pdf': f'results/redlines_0929_full/oracle_pdf/{key}.pdf'}


PRO = [
    gen_row('fam_a_one__vs__fam_a_two_redline_a000000001', 'clean/docx/fam_a_one', 'clean/docx/fam_a_two',
            'tracking_without_comments', 'a000000001'),
    gen_row('fam_b_one__vs__fam_b_two_redline_a000000002', 'clean/docx/fam_b_one', 'clean/docx/fam_b_two',
            'tracking_without_comments', 'a000000002'),
    gen_row('fam_c_one__vs__fam_c_two_redline_a000000003', 'clean/docx/fam_c_one', 'clean/docx/fam_c_two',
            'tracking_without_comments', 'a000000003'),
    gen_row('fam_d_one__vs__fam_d_two_redline_a000000004', 'clean/docx/fam_d_one', 'clean/docx/fam_d_two',
            'clean', 'a000000004'),
    gen_row('fam_e_one__vs__fam_e_two_redline_a000000005', 'clean/docx/fam_e_one', 'clean/docx/fam_e_two',
            'tracking_without_comments', 'a000000005'),
]
SAMPLE = [
    # the same pair (and the same id) as PRO[0]: counts among the 234, never among the drawn
    sample_row('smp_same_id_redline_a000000001', 'clean/docx/fam_a_one', 'clean/docx/fam_a_two',
               'tracking_without_comments', 'a000000001'),
    # the same pair as PRO[1] under another compare id: still one pair, still among the 234
    sample_row('smp_same_pair_redline_b000000002', 'clean/docx/fam_b_one', 'clean/docx/fam_b_two',
               'tracking_without_comments', 'b000000002'),
    # scarce states: everything but tracking_without_comments, kept whole
    *[sample_row(f'smp_wct_{i}_redline_b10000000{i}', f'clean/docx/fam_f_{i}', f'clean/docx/fam_g_{i}',
                 'with_comments_tracking', f'b10000000{i}') for i in range(1, 5)],
    sample_row('smp_clean_redline_b200000001', 'clean/docx/fam_j_1', 'clean/docx/fam_j_2', 'clean', 'b200000001'),
    # the plentiful state the draw fills with
    *[sample_row(f'smp_fill_{i}_redline_b30000000{i}', f'clean/docx/fam_k{i}_one', f'clean/docx/fam_k{i}_two',
                 'tracking_without_comments', f'b30000000{i}') for i in range(1, 7)],
    # no oracle anywhere: excluded, never drawn
    sample_row('smp_dead_oracle_redline_b400000001', 'clean/docx/fam_z_1', 'clean/docx/fam_z_2',
               'tracking_without_comments', 'b400000001'),
]
PRO_IDS = [r['id'] for r in PRO]


def site_rows() -> list[dict]:
    return [
        {'stem': 'tracking_without_comments__smp_same_id_redline_a000000001',
         'state': 'tracking_without_comments', 'pages': '3', 'jubarte_score': '88.5'},
        {'stem': 'clean__fam_b_one', 'state': 'clean', 'pages': '2', 'jubarte_score': '90.0'},
        {'stem': 'clean__fam_a_one', 'state': 'clean', 'pages': '4', 'jubarte_score': '91.2'},
        {'stem': 'with_comments_tracking__fam_f_1', 'state': 'with_comments_tracking',
         'pages': '5', 'jubarte_score': '70.0'},
    ]


def seed_row_files(bench: Path, row: dict, *, oracle: bool = True) -> None:
    """Every file a shaped row names: base, next, the compare docx/pdf, the oracle PDF."""
    for rel in (row['base'], row['next'], row['docx'], row['pdf']):
        put(bench, rel)
    if oracle:
        put(bench, row['oracle_pdf'])


def seed_gen_row(bench: Path, row: dict, *, oracle: bool = True) -> None:
    """The same for a gen_pairs row: corpus/word-relative paths, the oracle keyed by key."""
    seed_row_files(bench, {**row,
                           'base': f"corpus/word/{row['base']}.docx",
                           'next': f"corpus/word/{row['next']}.docx",
                           'docx': f"corpus/word/{row['docx']}",
                           'pdf': f"corpus/word/{row['pdf']}",
                           'oracle_pdf': f"results/redlines_0929_full/oracle_pdf/{row['key']}.pdf"},
                   oracle=oracle)


def seed_site_files(bench: Path) -> None:
    for row in site_rows():
        stem = row['stem'].split('__', 1)[1]
        put(bench, f"corpus/word/{row['state']}/docx/{stem}.docx")
        put(bench, f"corpus/word/{row['state']}/pdf/{stem}.pdf")


@pytest.fixture()
def world(tmp_path):
    """A bench root with every file the rows name — except the dead oracle."""
    bench = tmp_path / 'bench'
    for row in PRO:
        seed_gen_row(bench, row)
    for row in SAMPLE:
        seed_row_files(bench, row, oracle=row['id'] != 'b400000001')
    seed_site_files(bench)
    return bench


def resolver(bench: Path, known: dict[str, str] | None = None) -> fs.Resolver:
    return fs.Resolver(bench, fake_hub(known or {}))


def fake_hub(known: dict[str, str]):
    """A hub lookup: hub path -> LFS sha256, only for the paths it knows."""
    def lookup(repo_id: str, paths: list[str]) -> dict[str, str]:
        return {p: known[p] for p in paths if p in known}
    return lookup


# --------------------------------------------------------------------------- resolver

def test_hub_path_mapping():
    """corpus/word/... is the fixtures dataset's word/...; the 0929 oracle lives under outputs/."""
    assert fs.Resolver.hub_path('corpus/word/clean/docx/a.docx') == (
        'arthrod/neurotic_docx_bench-fixtures', 'word/clean/docx/a.docx')
    assert fs.Resolver.hub_path('results/redlines_0929_full/oracle_pdf/k.pdf') == (
        'arthrod/neurotic_docx_bench', 'outputs/redlines_0929_full/oracle_pdf/k.pdf')
    assert fs.Resolver.hub_path('results/other/x.pdf') is None


def test_resolver_local_first_then_hub(tmp_path):
    bench = tmp_path
    sha = put(bench, 'corpus/word/clean/docx/a.docx')
    hub_sha = 'f' * 64
    res = fs.Resolver(bench, fake_hub({'word/clean/pdf/a.pdf': hub_sha}))
    got = res.resolve_all(['corpus/word/clean/docx/a.docx',
                           'corpus/word/clean/pdf/a.pdf',
                           'corpus/word/clean/docx/gone.docx'])
    assert got['corpus/word/clean/docx/a.docx'] == (sha, 'local')
    assert got['corpus/word/clean/pdf/a.pdf'] == (hub_sha, 'hf')
    assert got['corpus/word/clean/docx/gone.docx'] is None
    # the hub was asked once per repo, for the misses only, and the answer is cached
    assert res.hf_calls == [('arthrod/neurotic_docx_bench-fixtures',
                             ['word/clean/docx/gone.docx', 'word/clean/pdf/a.pdf'])]
    assert res.resolve_all(['corpus/word/clean/pdf/a.pdf'])['corpus/word/clean/pdf/a.pdf'] == (hub_sha, 'hf')
    assert len(res.hf_calls) == 1


# --------------------------------------------------------------------------- convert_860

def test_convert_rows_shas_sort_and_hf(world):
    rows = site_rows()
    # this row's Word PDF is nowhere on disk; the hub has it
    (world / 'corpus/word/tracking_without_comments/pdf/smp_same_id_redline_a000000001.pdf').unlink()
    hub_sha = 'a' * 64
    out = fs.build_convert(rows, resolver(world, {
        'word/tracking_without_comments/pdf/smp_same_id_redline_a000000001.pdf': hub_sha}))
    assert [(r['state'], r['stem']) for r in out] == sorted((r['state'], r['stem']) for r in out)
    for row in out:
        assert row['docx'] == f"corpus/word/{row['state']}/docx/{row['stem'].split('__', 1)[1]}.docx"
        assert row['word_pdf'] == f"corpus/word/{row['state']}/pdf/{row['stem'].split('__', 1)[1]}.pdf"
        assert row['docx_sha256'] == hashlib.sha256((world / row['docx']).read_bytes()).hexdigest()
        assert row['pages'] and row['jubarte_score']  # the source row rides along
        if row['source'] == 'local':
            assert row['word_pdf_sha256'] == hashlib.sha256(
                (world / row['word_pdf']).read_bytes()).hexdigest()
    by_stem = {r['stem']: r for r in out}
    assert by_stem['clean__fam_b_one']['source'] == 'local'
    assert by_stem['tracking_without_comments__smp_same_id_redline_a000000001']['source'] == 'hf'
    assert by_stem['tracking_without_comments__smp_same_id_redline_a000000001']['word_pdf_sha256'] == hub_sha


def test_convert_rows_refuse_input_found_nowhere(world):
    rows = [{'stem': 'clean__nowhere', 'state': 'clean', 'pages': '1', 'jubarte_score': '0.0'}]
    with pytest.raises(RuntimeError, match='nowhere'):
        fs.build_convert(rows, resolver(world))


# --------------------------------------------------------------------------- redline_600

def draw(world, *, total=TOTAL, dead_pro=()):
    """build_redline over the synthetic world; dead_pro ids get no oracle file."""
    for row in PRO:
        if row['id'] in dead_pro:
            dead = world / 'results/redlines_0929_full/oracle_pdf' / f'{row["key"]}.pdf'
            if dead.is_file():
                dead.unlink()
    return fs.build_redline(fs.pro_rows(PRO, PRO_IDS), [dict(r) for r in SAMPLE],
                            total, SEED, resolver(world))


def test_redline_holds_every_pro_pair(world):
    rows, excluded = draw(world)
    ids = {r['id'] for r in rows}
    assert set(PRO_IDS) <= ids
    assert all(r['origin'] == fs.ORIGIN_PRO for r in rows if r['id'] in set(PRO_IDS))


def test_redline_total_exactly_and_distinct_pairs(world):
    rows, excluded = draw(world)
    assert len(rows) == TOTAL
    assert len({r['id'] for r in rows}) == TOTAL
    assert len({fs.pair_of(r) for r in rows}) == TOTAL
    assert [r['id'] for r in rows] == sorted(r['id'] for r in rows)


def test_redline_overlap_counts_among_the_pro_pairs(world):
    """The sample rows of an already-held pair are not drawn again: one pair, once."""
    rows, _ = draw(world)
    by_pair: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        by_pair.setdefault(fs.pair_of(row), []).append(row)
    assert all(len(rows_) == 1 for rows_ in by_pair.values())
    pro0 = [r for r in rows if r['id'] == 'a000000001']
    assert len(pro0) == 1 and pro0[0]['origin'] == fs.ORIGIN_PRO
    # the same pair as PRO[1] under another compare id never entered as a sample row
    assert 'b000000002' not in {r['id'] for r in rows}


def test_redline_scarce_states_whole(world):
    rows, _ = draw(world)
    chosen = {r['id'] for r in rows if r['origin'] == fs.ORIGIN_SAMPLE}
    scarce = {r['id'] for r in SAMPLE if r['state'] != 'tracking_without_comments'}
    assert scarce <= chosen  # all five, always


def test_redline_missing_oracle_excluded_and_replaced(world):
    rows, excluded = draw(world, dead_pro={'a000000005'})
    assert len(rows) == TOTAL
    assert 'a000000005' not in {r['id'] for r in rows}
    assert fs.pair_of({'base': 'corpus/word/clean/docx/fam_e_one.docx',
                       'next': 'corpus/word/clean/docx/fam_e_two.docx'}) not in {fs.pair_of(r) for r in rows}
    reasons = {e['key']: e for e in excluded}
    dead = reasons['fam_e_one__vs__fam_e_two_redline_a000000005']
    assert 'oracle' in dead['reason'] and dead['origin'] == fs.ORIGIN_PRO
    assert 'smp_dead_oracle_redline_b400000001' in reasons  # the dead sample candidate is named too
    assert sum(1 for r in rows if r['origin'] == fs.ORIGIN_SAMPLE) == TOTAL - 4  # its slot was replaced


def test_redline_deterministic_for_the_same_seed(world):
    first, _ = draw(world)
    again, _ = draw(world)
    assert first == again


def test_redline_recorded_sha_drift_is_refused(world):
    sample = [dict(r) for r in SAMPLE]
    for row in sample:
        if row['id'] == 'b100000001':
            row['base_sha256'] = 'deadbeef' * 8
    with pytest.raises(RuntimeError, match='b100000001'):
        fs.build_redline(fs.pro_rows(PRO, PRO_IDS), sample, TOTAL, SEED, resolver(world))


def test_redline_sha_columns_filled(world):
    rows, _ = draw(world)
    for row in rows:
        for col, rel in (('base_sha256', 'base'), ('next_sha256', 'next'),
                         ('docx_sha256', 'docx'), ('pdf_sha256', 'pdf'),
                         ('oracle_pdf_sha256', 'oracle_pdf'), ('oracle_sha256', 'oracle_pdf')):
            assert row[col] == hashlib.sha256((world / row[rel]).read_bytes()).hexdigest(), (row['id'], col)
        assert row['source'] == 'local'


def test_redline_hf_source(world):
    """A pro pair whose base docx is only on the hub still carries its sha and source=hf."""
    (world / 'corpus/word/clean/docx/fam_a_one.docx').unlink()
    hub_sha = hashlib.sha256(b'corpus/word/clean/docx/fam_a_one.docx').hexdigest()
    rows, _ = fs.build_redline(fs.pro_rows(PRO, PRO_IDS), [dict(r) for r in SAMPLE], TOTAL, SEED,
                               resolver(world, {'word/clean/docx/fam_a_one.docx': hub_sha}))
    row = next(r for r in rows if r['id'] == 'a000000001')
    assert row['base_sha256'] == hub_sha
    assert row['source'] == 'hf'


# --------------------------------------------------------------------------- build end to end

def write_inputs(tmp: Path) -> dict[str, Path]:
    """The five inputs of `bench sets build`, at bench scale."""
    inputs = tmp / 'inputs'
    inputs.mkdir()
    site_csv = inputs / 'site.csv'
    with site_csv.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=['stem', 'state', 'pages', 'jubarte_score'])
        writer.writeheader()
        writer.writerows(site_rows())
    sample_csv = inputs / 'sample.csv'
    with sample_csv.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=REDLINE_HEADER)
        writer.writeheader()
        writer.writerows(SAMPLE)
    gen_csv = inputs / 'gen_pairs.csv'
    with gen_csv.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=GEN_FIELDS)
        writer.writeheader()
        writer.writerows(PRO)
    pool_csv = inputs / 'pool_pairs.csv'
    _write_pool(pool_csv)
    cases = inputs / 'cases-redline.json'
    cases.write_text(json.dumps({'cases': [{'id': f'r-{id_}'} for id_ in PRO_IDS]}))
    return {'site_csv': site_csv, 'sample_csv': sample_csv, 'gen_pairs_csv': gen_csv,
            'pool_pairs_csv': pool_csv, 'cases_json': cases}


def _write_pool(pool_csv: Path, *, forget_key: str | None = None) -> None:
    rows = []
    for row in [*PRO, *SAMPLE]:
        rows.append({'key': row['key'],
                     'base': row['base'].removeprefix('corpus/word/').removesuffix('.docx'),
                     'next': row['next'].removeprefix('corpus/word/').removesuffix('.docx'),
                     'docx': row['docx'].removeprefix('corpus/word/'),
                     'pdf': row['pdf'].removeprefix('corpus/word/'),
                     'state': row['state'], 'id': row['id'], 'sets': 'synthetic'})
    if forget_key is not None:
        next(row for row in rows if row['key'] == forget_key)['key'] = 'not_a_pool_key'
    with pool_csv.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=GEN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_build_writes_the_three_files(tmp_path, world):
    paths = write_inputs(tmp_path)
    out = tmp_path / 'sets'
    summary = fs.build(bench_root=world, out=out, total=TOTAL, seed=SEED,
                       resolver=resolver(world), **paths)
    convert = read_csv(out / 'convert_860.csv')
    redline = read_csv(out / 'redline_600.csv')
    sets = json.loads((out / 'sets.json').read_text())
    assert len(convert) == 4 and len(redline) == TOTAL
    assert sets['set_version'] == '2026-11-03.1'
    assert sets['seed'] == SEED
    assert [s['path'] for s in sets['sources']] == [str(paths[k]) for k in
                                                    ('site_csv', 'sample_csv', 'gen_pairs_csv',
                                                     'pool_pairs_csv', 'cases_json')]
    assert all(len(s['sha256']) == 64 for s in sets['sources'])
    assert sets['counts']['convert_860'] == {'clean': 2, 'tracking_without_comments': 1,
                                             'with_comments_tracking': 1}
    assert sum(sets['counts']['redline_600'].values()) == TOTAL
    assert sets['totals'] == {'convert_860': 4, 'redline_600': TOTAL}
    assert sets['origins'] == {fs.ORIGIN_PRO: 5, fs.ORIGIN_SAMPLE: TOTAL - 5}
    assert any(e['key'] == 'smp_dead_oracle_redline_b400000001' for e in sets['excluded'])
    assert summary['redline_rows'] == TOTAL and summary['convert_rows'] == 4


def test_build_is_deterministic(tmp_path, world):
    paths = write_inputs(tmp_path)
    outs = []
    for name in ('out1', 'out2'):
        out = tmp_path / name
        fs.build(bench_root=world, out=out, total=TOTAL, seed=SEED, resolver=resolver(world), **paths)
        outs.append(out)
    for name in ('convert_860.csv', 'redline_600.csv', 'sets.json'):
        assert (outs[0] / name).read_bytes() == (outs[1] / name).read_bytes(), name


def test_build_refuses_sample_keys_outside_the_pool(tmp_path, world):
    paths = write_inputs(tmp_path)
    _write_pool(paths['pool_pairs_csv'], forget_key=SAMPLE[0]['key'])
    with pytest.raises(RuntimeError, match='pool'):
        fs.build(bench_root=world, out=tmp_path / 'sets', total=TOTAL, seed=SEED,
                 resolver=resolver(world), **paths)


# --------------------------------------------------------------------------- the committed sets

COMMITTED = REPO / 'results/sets'


@pytest.mark.skipif(not (COMMITTED / 'redline_600.csv').is_file(), reason='results/sets/ not built yet')
def test_committed_sets():
    convert = read_csv(COMMITTED / 'convert_860.csv')
    redline = read_csv(COMMITTED / 'redline_600.csv')
    sets = json.loads((COMMITTED / 'sets.json').read_text())
    assert len(convert) == 860
    assert len({r['stem'] for r in convert}) == 860
    assert [(r['state'], r['stem']) for r in convert] == sorted((r['state'], r['stem']) for r in convert)
    assert len(redline) == 600
    assert len({r['id'] for r in redline}) == 600
    assert len({fs.pair_of(r) for r in redline}) == 600
    assert [r['id'] for r in redline] == sorted(r['id'] for r in redline)
    assert sets['set_version'] == '2026-11-03.1' and sets['seed'] == 20261103
    assert sets['counts']['convert_860'] == {s: sum(1 for r in convert if r['state'] == s)
                                             for s in sets['counts']['convert_860']}
    assert sum(sets['counts']['convert_860'].values()) == 860
    assert sets['counts']['redline_600'] == {s: sum(1 for r in redline if r['state'] == s)
                                             for s in sets['counts']['redline_600']}
    assert sum(sets['counts']['redline_600'].values()) == 600
    assert sets['totals'] == {'convert_860': 860, 'redline_600': 600}
    for row in redline:
        assert row['base_sha256'] and row['next_sha256'] and row['oracle_sha256'] and row['origin']
    for row in convert:
        assert row['docx_sha256'] and row['word_pdf_sha256'] and row['source'] in ('local', 'hf')
