"""The release_info flow: which commands each stage runs, in which order, and
the six files it writes.

Commands go through an injected runner, the watchdog through an injected
spawner and the results dataset through an injected hub, so nothing here
needs Word, the network, git or the corpus. The Step/plan/execute structure
is jubarte_bench_release's; these tests keep it honest for the evidence flow.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import jubarte_release_info as jri
from neurotic_docx_bench.jubarte_bench_release import Release, Step, execute

V = '0.11.3'
LANE = f'jubarte-{V}'
REPO = Path(__file__).resolve().parents[1]
CHECKER = Path.home() / 'temp/T/jubarte-loop/release_0.11.2/agents/release_info/B_release_sh/check_release_info.py'


@dataclass
class Proc:
    returncode: int = 0
    stdout: str = ''
    stderr: str = ''


@dataclass
class Dog:
    argv: list[str]
    stopped: bool = False

    def terminate(self) -> None:
        self.stopped = True

    def kill(self) -> None:
        self.stopped = True

    def wait(self, timeout: float | None = None) -> int:
        return 0


@dataclass
class Recorder:
    """Runs steps by answering exit codes by step name; records the order."""

    codes: dict[str, int] = field(default_factory=dict)
    ran: list[str] = field(default_factory=list)

    def run(self, step: Step, root: Path) -> int:
        self.ran.append(step.name)
        return self.codes.get(step.name, 0)

    def spawn(self, argv, root: Path) -> Dog:
        return Dog(list(argv))


@dataclass
class FakeHub:
    """The results dataset: the names it lists, and a record of what was asked."""

    names: list[str]
    listed: int = 0
    fetched: list[str] = field(default_factory=list)
    down: bool = False

    def hub(self) -> jri.Hub:
        return jri.Hub(self.listing, self.fetch)

    def listing(self) -> list[str]:
        self.listed += 1
        if self.down:
            raise ConnectionError('no network')
        return list(self.names)

    def fetch(self, name: str, dest: Path) -> bool:
        self.fetched.append(name)
        if name.startswith('gone'):
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'hub ' + name.encode())
        return True


def _answers(cmd, **_) -> Proc:
    """The runner of a candidate that still reports the previous version."""
    if cmd[-1] == '--version':
        return Proc(0, 'jubarte 0.11.0\n')
    if cmd[0] == 'git':
        return Proc(0, 'c0ffee\n')
    return Proc(1)


def _rel(tmp_path: Path, version: str = V) -> Release:
    return Release(version, tmp_path, cache=tmp_path / 'cache')


def _cmd(steps: list[Step], name: str) -> list[str]:
    return list(next(s for s in steps if s.name == name).argv)


def _act(steps: list[Step], name: str) -> str:
    action = next(s for s in steps if s.name == name).action
    assert action is not None
    return action()


def _row(key: str, state: str, pair: str | None = None) -> dict:
    """A pool compare; ``pair`` names another key's (base, next) to share it."""
    pair = pair or key
    return {'key': key, 'base': f'clean/docx/{pair}_base', 'next': f'{state}/docx/{pair}_next',
            'docx': f'{state}/docx/{key}.docx', 'pdf': f'{state}/pdf/{key}.pdf',
            'state': state, 'id': f'id{key}', 'sets': 'word_based'}


def _put(path: Path, data: bytes | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(path.name.encode() if data is None else data)
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(tmp_path: Path, fill: int = 6, fixtures: int = 3) -> tuple[Path, Path]:
    """A small bench and its compare_regen beside it.

    Pool: four scarce compares (``wct0b`` is a second compare of ``wct0``'s
    pair) and ``fill`` plentiful ones; gen_pairs has each pair once. ``wct1``
    has a fresh oracle outside the root; docxodus has a Word PDF for every
    pair but ``twc0``; each state has ``fixtures`` conversion fixtures
    ``fx<state><i>``; every Word PDF but ``fx00`` has a LibreOffice render.
    """
    root, regen = tmp_path / 'bench', tmp_path / 'compare_regen'
    run = root / jri.RUN_DIR
    pool = [_row('wct0', 'with_comments_tracking'), _row('wct0b', 'with_comments_tracking', pair='wct0'),
            _row('wct1', 'with_comments_tracking'), _row('cle0', 'clean')]
    pool += [_row(f'twc{i}', jri.FILL_STATE) for i in range(fill)]
    gen = [r for r in pool if r['key'] != 'wct0b']
    jri.write_csv(run / 'pool_pairs.csv', jri.GEN_FIELDS, pool)
    jri.write_csv(run / 'gen_pairs.csv', jri.GEN_FIELDS, gen)
    word = root / 'corpus/word'
    for r in pool:
        for name in (f'{r["base"]}.docx', f'{r["next"]}.docx', r['docx'], r['pdf']):
            _put(word / name)
        _put(run / 'oracle_pdf' / f'{r["key"]}.pdf')
    _put(regen / 'out' / 'idwct1__vs__idwct1.pdf')
    for r in gen:
        if r['key'] != 'twc0':
            _put(run / 'docxodus' / 'pdf_by_word' / f'{r["key"]}_docxodus.pdf')
    for s, state in enumerate(jri.CONVERSION_QUOTAS):
        for i in range(fixtures):
            _put(word / state / 'docx' / f'fx{s}{i}.docx')
            _put(word / state / 'pdf' / f'fx{s}{i}.pdf')
    for pdf in word.glob('*/pdf/*.pdf'):
        if pdf.stem != 'fx00':
            _put(root / jri.SOFFICE_WORK / 'candidate' / f'{pdf.parent.parent.name}__{pdf.stem}.pdf')
    (run / 'versions.json').write_text(json.dumps({'docxodus': 'Docxodus 12.6.5 (C#)'}))
    return root, regen


def _plan(root: Path, regen: Path, **kw) -> list[Step]:
    return jri.plan(Release(V, root, cache=root / 'cache'), compare_regen=regen, **kw)


def _sample(root: Path, regen: Path, n: int, **kw) -> list[Step]:
    """The plan after its sample stage ran."""
    steps = _plan(root, regen, n=n, **kw)
    for s in steps:
        if s.stage == 'sample':
            assert s.action is not None
            s.action()
    return steps


# ------------------------------------------------------------------ stages and entry points

def test_stages_are_the_owner_steps_in_order() -> None:
    assert jri.STAGES == ('install', 'sample', 'generate', 'export', 'measure', 'convert', 'score', 'write')
    steps = jri.plan(_rel(Path('/tmp/x')), conversion=['clean/docx/a.docx'])
    assert [s.stage for s in steps] == sorted((s.stage for s in steps), key=jri.STAGES.index)


def test_rejects_a_version_that_is_not_a_release(tmp_path: Path) -> None:
    for bad in ('0.11', 'v0.11.3', '0.11.3-rc1'):
        with pytest.raises(ValueError, match='not a release version'):
            Release(bad, tmp_path)


def test_the_module_and_the_script_are_entry_points(tmp_path: Path) -> None:
    for argv in (['-m', 'neurotic_docx_bench.jubarte_release_info'], ['scripts/jubarte_release_info.py']):
        out = subprocess.run([sys.executable, *argv, V, '--root', str(tmp_path), '--plan', '--only', 'measure'],
                             cwd=REPO, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        lines = out.stdout.splitlines()
        assert len(lines) == 2 and all(line.startswith('measure   uv run python') for line in lines), out.stdout


# ------------------------------------------------------------------ install

def test_a_candidate_binary_may_report_any_version_but_must_run(tmp_path: Path) -> None:
    rel = _rel(tmp_path)
    cand = tmp_path / 'cand'
    step = jri.select(jri.plan(rel, binary=cand, run=_answers), only=['install'])[0]
    assert step.name == 'candidate binary'
    with pytest.raises(RuntimeError, match='no such binary'):
        step.action()
    cand.write_bytes(b'x')
    detail = step.action()  # the candidate predates the version bump: 0.11.0 is accepted
    assert 'reports "jubarte 0.11.0"' in detail and f'recorded as jubarte {V}' in detail
    assert _sha(cand)[:12] in detail
    dead = jri.select(jri.plan(rel, binary=cand, run=lambda cmd, **_: Proc(126)), only=['install'])[0]
    with pytest.raises(RuntimeError, match='does not answer'):
        dead.action()


def test_the_github_release_binary_must_report_the_release(tmp_path: Path, monkeypatch) -> None:
    exe = _put(tmp_path / 'cache' / 'jubarte')
    monkeypatch.setattr(jri.jubarte_release, 'github_download', lambda version, cache, get: exe)
    said = {'out': 'jubarte 0.11.2\n'}
    step = jri.select(jri.plan(_rel(tmp_path), run=lambda cmd, **_: Proc(0, said['out'])), only=['install'])[0]
    assert step.name == 'release binary'
    with pytest.raises(RuntimeError, match=f'says it is 0.11.2, not {V}'):
        step.action()
    said['out'] = f'jubarte {V}\n'
    assert 'sha256 checked' in step.action()
    monkeypatch.setattr(jri.jubarte_release, 'github_download', lambda version, cache, get: None)
    with pytest.raises(RuntimeError, match='pass --binary'):
        step.action()


# ------------------------------------------------------------------ the samples

def test_draw_balanced_takes_every_scarce_state_first_and_fills_seeded() -> None:
    pool = ([_row(f'wct{i}', 'with_comments_tracking') for i in range(3)]
            + [_row(f'wcc{i}', 'with_comments_clean') for i in range(2)]
            + [_row('cle0', 'clean')]
            + [_row(f'twc{i:02d}', jri.FILL_STATE) for i in range(20)])
    covered = {r['key'] for r in pool if r['state'] != jri.FILL_STATE} | {f'twc{i:02d}' for i in range(10)}
    sample = jri.draw_balanced(pool, 12, 20261003, covered)
    states = [r['state'] for r in sample]
    # every scarce compare first (all of them, covered or not), then the fill state
    assert states.count('with_comments_tracking') == 3
    assert states.count('with_comments_clean') == 2
    assert states.count('clean') == 1
    assert states.count(jri.FILL_STATE) == 6
    assert all(r['key'] in covered for r in sample if r['state'] == jri.FILL_STATE)
    # seeded: the same seed draws the same sample
    assert [r['key'] for r in jri.draw_balanced(pool, 12, 20261003, covered)] == [r['key'] for r in sample]
    assert len(jri.draw_balanced(pool, 12, 7, covered)) == 12
    # uncovered fill compares only once the covered ones run out
    wide = jri.draw_balanced(pool, 20, 20261003, covered)
    assert len(wide) == 20 and sum(r['key'] in covered for r in wide) == 16
    # a compare is covered when its pair's first key is
    twin = _row('wct0b', 'with_comments_tracking', pair='wct0')
    first = jri.first_keys(pool)
    assert jri.draw_balanced([twin, *pool[6:]], 1, 1, {'wct0'}, first) == [twin]


def test_the_fill_is_spread_over_document_families_and_takes_new_pairs_only() -> None:
    def row(key: str, name: str, state: str = jri.FILL_STATE) -> dict:
        return _row(key, state) | {'base': f'clean/docx/0123456789_{name}'}

    assert jri.family('clean/docx/0123456789_super_editor__list_def') == 'super_editor'
    assert jri.family('clean/docx/0123456789_file_124') == 'file'
    assert jri.family('clean/docx/0123456789_00b5defcad6e58038eac35472a2d48c8') == 'web'
    pool = ([row(f'w{i:02d}', f'{i:024x}') for i in range(12)]  # the web corpus: 12 of 21
            + [row(f'f{i}', f'file_{i}') for i in range(6)]
            + [row('s0', 'super_editor__a'), row('s1', 'super_editor__b', 'with_comments_tracking')]
            + [row('o0', 'open_sans__a')])
    sample = [r for r in pool if r['key'] in ('w00', 'w01', 'f0')]
    out = jri.extend_by_family(sample, pool, 4, 1, covered={'f3'})
    assert out[:3] == sample
    added = [r['key'] for r in out[3:]]
    # the two families the sample lacks first (the scarce state of one), then the furthest below its
    # share of the pool: web (4 of 7 wanted, 2 held), then file (2 wanted, 1 held), its covered pair
    assert {'s1', 'o0', 'f3'} <= set(added) and 's0' not in added
    assert sum(k.startswith('w') for k in added) == 1 and len(added) == 4
    assert jri.extend_by_family(sample, pool, 4, 1, covered={'f3'}) == out  # seeded
    # a pair the sample holds is never taken again, and the pool can run out
    more = jri.extend_by_family(sample, [*pool, row('f0b', 'file_0') | {'next': sample[2]['next']}], 30, 1, covered={'f3'})
    keys = [r['key'] for r in more]
    assert 'f0b' not in keys and len(keys) == len(set(keys)) == len(pool)


def test_draw_conversion_respects_quotas_and_requires_a_word_pdf(tmp_path: Path) -> None:
    root, _ = _tree(tmp_path)
    _put(root / 'corpus/word/clean/docx/no_pdf.docx')  # no Word PDF: never drawn
    _put(root / 'corpus/word/clean/docx/~$fx00.docx')
    sample = jri.draw_conversion(root, {'clean': 2, 'with_comments_tracking': 3}, 20261003)
    assert [r['state'] for r in sample].count('clean') == 2 and len(sample) == 5
    for r in sample:  # paths from the bench root, the stem is <state>__<docx stem>
        assert r['docx'] == f'corpus/word/{r["state"]}/docx/{r["stem"].split("__")[1]}.docx'
        assert (root / r['word_pdf']).is_file() and (root / r['docx']).is_file()
    assert sample == jri.draw_conversion(root, {'clean': 2, 'with_comments_tracking': 3}, 20261003)
    with pytest.raises(RuntimeError, match='only 4 have a Word PDF'):  # fx00..fx02 and the compare cle0
        jri.draw_conversion(root, {'clean': 5}, 1)


def test_conversion_quotas_scale_with_n() -> None:
    assert jri.DEFAULT_N == 600 == sum(jri.CONVERSION_QUOTAS.values())
    assert jri.conversion_quotas(jri.DEFAULT_N) == jri.CONVERSION_QUOTAS
    small = jri.conversion_quotas(8)
    assert sum(small.values()) == 8 and set(small) == set(jri.CONVERSION_QUOTAS)
    assert sum(jri.conversion_quotas(24).values()) == 24


def test_the_redline_sample_has_one_compare_per_pair_and_the_manifest_names_each(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    steps = _plan(root, regen, n=8)
    detail = _act(steps, 'draw redline sample')
    ev = root / jri.evidence_dir(V)
    sample = jri.read_csv(ev / f'sample_redline_{V}.csv')
    # the pool columns first (measure.py reads the keys), then the sha256 of each file a row names
    assert list(sample[0]) == jri.GEN_SHA_FIELDS and jri.GEN_SHA_FIELDS[:len(jri.GEN_FIELDS)] == jri.GEN_FIELDS
    word = root / 'corpus/word'
    for r in sample:
        assert r['base_sha256'] == jri._sha(word / f'{r["base"]}.docx')
        assert r['next_sha256'] == jri._sha(word / f'{r["next"]}.docx')
        assert r['docx_sha256'] == jri._sha(word / r['docx']) and r['pdf_sha256'] == jri._sha(word / r['pdf'])
    assert any(r['base_sha256'] and r['pdf_sha256'] for r in sample)
    keys = [r['key'] for r in sample]
    # one compare per pair: the pair's first key, never its second Word compare
    assert len(keys) == 8 and {'wct0', 'wct1', 'cle0'} <= set(keys) and 'wct0b' not in keys
    manifest = [r['key'] for r in jri.read_csv(ev / 'gen_pairs_sample.csv')]
    assert sorted(manifest) == sorted(keys)
    assert '8 compares of 8 pairs' in detail
    assert 'twc0' not in keys  # the one fill pair docxodus does not cover is drawn last
    # the same seed draws the same sample again
    _act(steps, 'draw redline sample')
    assert [r['key'] for r in jri.read_csv(ev / f'sample_redline_{V}.csv')] == keys


def test_a_draw_skips_compares_without_an_oracle_and_refuses_to_come_up_short(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    (root / jri.RUN_DIR / 'oracle_pdf' / 'cle0.pdf').unlink()
    _act(_plan(root, regen, n=8), 'draw redline sample')
    keys = [r['key'] for r in jri.read_csv(root / jri.redline_list(V))]
    assert 'cle0' not in keys and len(keys) == 8
    with pytest.raises(RuntimeError, match='only 8 compares have their Word PDF, 10 wanted'):
        _act(_plan(root, regen, n=10), 'draw redline sample')


def test_evidence_names_carry_the_version_so_measure_never_resumes_another_release(tmp_path: Path) -> None:
    assert jri.redline_list(V) == Path(f'results/release_{V}_evidence/sample_redline_{V}.csv')
    assert jri.conversion_list(V) == Path(f'results/release_{V}_evidence/sample_conversion_{V}.csv')
    assert jri.scores_json(LANE, V) == jri.RUN_DIR / f'scores_{LANE}_sample_redline_{V}.json'
    assert jri.scores_json('docxodus', '0.11.4') != jri.scores_json('docxodus', V)
    steps = jri.plan(_rel(tmp_path), conversion=[])
    for name in ('measure jubarte', 'measure docxodus'):
        cmd = _cmd(steps, name)
        assert cmd[cmd.index('--sample-csv') + 1] == str(jri.redline_list(V))
    docxodus = [s for s in steps if s.stage == 'export' and 'docxodus' in s.name and s.argv]
    assert all(V in str(s.log) and V in s.argv[s.argv.index('--log') + 1] for s in docxodus)


def test_adopting_validates_the_lists_and_records_where_they_came_from(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    pool = jri.read_csv(root / jri.RUN_DIR / 'pool_pairs.csv')
    mine = root / 'results/mine.csv'
    picked = [r for r in pool if r['key'] != 'wct0b'][:5]
    jri.write_csv(mine, jri.GEN_FIELDS, picked)
    # a list that names a pair twice is refused: the sample is one compare per pair
    jri.write_csv(root / 'results/twice.csv', jri.GEN_FIELDS, pool[:5])
    with pytest.raises(RuntimeError, match='1 compares repeat a pair already listed'):
        _act(_plan(root, regen, n=5, adopt_redline_csv=Path('results/twice.csv')), 'adopt redline sample')
    fixtures = [f'corpus/word/{state}/docx/fx{s}0.docx' for s, state in enumerate(jri.CONVERSION_QUOTAS)]
    listing = _put(root / 'results/convert.txt', ('\n'.join(fixtures) + '\n').encode())
    steps = _plan(root, regen, n=5, seed=7, adopt_redline_csv=Path('results/mine.csv'),
                  adopt_conversion_list=listing)
    assert [s.name for s in steps if s.stage == 'sample'] == \
        ['bench inputs', 'adopt redline sample', 'adopt conversion sample']
    assert 'adopted from results/mine.csv' in _act(steps, 'adopt redline sample')
    ev = root / jri.evidence_dir(V)
    assert [r['key'] for r in jri.read_csv(ev / f'sample_redline_{V}.csv')] == [r['key'] for r in picked]
    assert len(jri.read_csv(ev / 'gen_pairs_sample.csv')) == 5
    with pytest.raises(RuntimeError, match='4 fixtures, want 5'):
        _act(steps, 'adopt conversion sample')
    four = _plan(root, regen, n=4, seed=7, adopt_conversion_list=listing)
    _act(four, 'adopt conversion sample')
    rows = jri.read_csv(ev / f'sample_conversion_{V}.csv')
    assert list(rows[0]) == ['state', 'stem', 'docx', 'word_pdf', 'docx_sha256', 'word_pdf_sha256']
    assert rows[0] == {'state': 'clean', 'stem': 'clean__fx00', 'docx': 'corpus/word/clean/docx/fx00.docx',
                       'word_pdf': 'corpus/word/clean/pdf/fx00.pdf',
                       'docx_sha256': jri._sha(root / 'corpus/word/clean/docx/fx00.docx'),
                       'word_pdf_sha256': jri._sha(root / 'corpus/word/clean/pdf/fx00.pdf')}
    assert len(rows[0]['docx_sha256']) == 64 and len(rows[0]['word_pdf_sha256']) == 64
    meta = json.loads((ev / 'sample_meta.json').read_text())
    assert meta['redline']['rule'] == 'adopted from results/mine.csv, not drawn'
    assert meta['redline']['seed'] == 7 and meta['redline']['adopted_sha256'] == _sha(mine)
    assert meta['conversion']['rule'] == 'adopted from results/convert.txt, not drawn'
    assert meta['conversion']['seed'] == 7 and meta['conversion']['date']
    # every key must be a pool key, once, and the count must be --n
    with pytest.raises(RuntimeError, match='5 keys, want 6'):
        jri.adopt_redline(mine, pool, 6)
    jri.write_csv(mine, jri.GEN_FIELDS, [*pool[:4], _row('stranger', 'clean')])
    with pytest.raises(RuntimeError, match=r'1 keys are not in pool_pairs\.csv'):
        jri.adopt_redline(mine, pool, 5)
    jri.write_csv(mine, jri.GEN_FIELDS, [*pool[:4], pool[0]])
    with pytest.raises(RuntimeError, match='listed twice'):
        jri.adopt_redline(mine, pool, 5)
    # every fixture must be corpus/word/<state>/docx/<stem>.docx with its Word PDF
    listing.write_text('results/elsewhere/a.docx\n')
    with pytest.raises(RuntimeError, match=r'is not corpus/word/<state>/docx/<stem>\.docx'):
        jri.adopt_conversion(listing, root, 1)
    (root / 'corpus/word/clean/pdf/fx00.pdf').unlink()
    listing.write_text('corpus/word/clean/docx/fx00.docx\n')
    with pytest.raises(RuntimeError, match=r'no corpus/word/clean/pdf/fx00\.pdf'):
        jri.adopt_conversion(listing, root, 1)


def test_an_adopted_compare_without_its_word_pdf_is_refused(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    pool = jri.read_csv(root / jri.RUN_DIR / 'pool_pairs.csv')
    jri.write_csv(root / 'mine.csv', jri.GEN_FIELDS, [r for r in pool if r['key'] != 'wct0b'][:4])
    (root / jri.RUN_DIR / 'oracle_pdf' / 'cle0.pdf').unlink()
    with pytest.raises(RuntimeError, match='1 sampled compares have no Word PDF'):
        _act(_plan(root, regen, n=4, adopt_redline_csv=root / 'mine.csv'), 'adopt redline sample')
    missing = jri.select(_plan(root, regen, adopt_redline_csv=root / 'nope.csv'), only=['sample'])[0]
    with pytest.raises(RuntimeError, match='no such list to adopt'):
        missing.action()


# ------------------------------------------------------------------ generate

def test_generate_runs_the_given_binary_and_a_manifest_per_tool(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    binary = _put(tmp_path / 'build' / 'jubarte-rc')
    _put(tmp_path / 'build' / 'redline')  # a neighbour the generator would have preferred
    steps = _plan(root, regen, binary=binary)
    ev = jri.evidence_dir(V)
    generate = _cmd(steps, 'jubarte redlines')
    assert generate[generate.index('--method') + 1] == 'jubarte-rust'
    assert generate[generate.index('--dist') + 1] == str(ev / 'dist')
    assert generate[generate.index('--tool') + 1] == LANE
    assert generate[generate.index('--manifest') + 1] == str(ev / 'gen_pairs_sample.csv')
    _act(steps, 'generator dist')
    assert [p.name for p in (root / ev / 'dist').iterdir()] == ['jubarte']
    assert (root / ev / 'dist' / 'jubarte').resolve() == binary.resolve()
    docxodus = _cmd(steps, 'docxodus redlines (missing only)')
    assert docxodus[docxodus.index('--method') + 1] == 'docxodus-csharp-inproc'
    assert docxodus[docxodus.index('--dist') + 1] == str(jri.DOCXODUS_DIST)
    assert docxodus[docxodus.index('--tool') + 1] == 'docxodus'
    assert docxodus[docxodus.index('--manifest') + 1] == str(ev / 'gen_pairs_docxodus_missing.csv')
    names = [s.name for s in steps if s.stage == 'generate']
    assert names.index('docxodus PDFs from the hub') < names.index('docxodus manifest') \
        < names.index('docxodus redlines (missing only)')


def test_the_draw_counts_the_hub_listing_as_coverage_and_caches_it(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    fake = FakeHub(['twc0_docxodus.pdf', 'README.md'])
    steps = _plan(root, regen, n=9, hub=fake.hub())
    detail = _act(steps, 'draw redline sample')
    assert '9 pairs with a docxodus Word PDF (local PDFs + Hub listing)' in detail
    cache = root / jri.evidence_dir(V) / 'hub_docxodus_listing.json'
    assert json.loads(cache.read_text())['names'] == ['README.md', 'twc0_docxodus.pdf']
    assert 'cached Hub listing' in _act(steps, 'draw redline sample') and fake.listed == 1
    meta = json.loads((root / jri.evidence_dir(V) / 'sample_meta.json').read_text())['redline']
    assert meta['docxodus_covered_pairs'] == 9 and meta['pairs'] == 9 and meta['seed'] == jri.DEFAULT_SEED


def test_an_unreachable_hub_falls_back_to_local_pdfs_and_says_so(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    fake = FakeHub([], down=True)
    steps = _plan(root, regen, n=9, hub=fake.hub())
    detail = _act(steps, 'draw redline sample')
    assert '8 pairs with a docxodus Word PDF (local PDFs only: Hub unreachable (ConnectionError))' in detail
    assert not (root / jri.evidence_dir(V) / 'hub_docxodus_listing.json').exists()
    assert 'Hub unreachable (ConnectionError): nothing fetched, 1 pairs left to Docxodus' in \
        _act(steps, 'docxodus PDFs from the hub')
    assert fake.fetched == []
    assert 'Hub not consulted' in _act(_plan(root, regen, n=9), 'docxodus PDFs from the hub')


def test_missing_docxodus_pdfs_come_from_the_hub_and_docxodus_redlines_the_rest(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    lane = root / jri.RUN_DIR / 'docxodus' / 'pdf_by_word'
    for key in ('wct0', 'wct1'):
        (lane / f'{key}_docxodus.pdf').unlink()
    ran: list[list[str]] = []

    def run(cmd, **_):
        ran.append(list(cmd))
        return Proc(0, 'wrote 1 redline(s)\n')

    fake = FakeHub(['wct0_docxodus.pdf'])  # the Hub has wct0, neither wct1 nor twc0
    steps = _sample(root, regen, 9, hub=fake.hub(), run=run)
    assert _act(steps, 'docxodus PDFs from the hub') == \
        '1 docxodus Word PDFs fetched (cached Hub listing), 2 not on the Hub'
    assert fake.fetched == ['wct0_docxodus.pdf'] and (lane / 'wct0_docxodus.pdf').is_file()
    assert '2 pairs without a docxodus Word PDF' in _act(steps, 'docxodus manifest')
    ev = root / jri.evidence_dir(V)
    assert sorted(r['key'] for r in jri.read_csv(ev / 'gen_pairs_docxodus_missing.csv')) == ['twc0', 'wct1']
    assert '2 pairs redlined by Docxodus' in _act(steps, 'docxodus redlines (missing only)')
    assert ran == [_cmd(steps, 'docxodus redlines (missing only)')]
    assert (ev / 'docxodus.generate.log').read_text() == 'wrote 1 redline(s)\n'
    # the generator exits 1 on an empty manifest: with nothing missing it is not run at all
    for key in ('wct1', 'twc0'):
        _put(lane / f'{key}_docxodus.pdf')
    assert 'every sampled pair has its docxodus Word PDF locally' in _act(steps, 'docxodus PDFs from the hub')
    _act(steps, 'docxodus manifest')
    assert 'nothing to redline' in _act(steps, 'docxodus redlines (missing only)') and len(ran) == 1
    failing = _sample(root, regen, 9, run=lambda cmd, **_: Proc(1, '', 'boom'))
    (lane / 'twc0_docxodus.pdf').unlink()
    _act(failing, 'docxodus manifest')
    with pytest.raises(RuntimeError, match='exit 1'):
        _act(failing, 'docxodus redlines (missing only)')


def test_a_docxodus_redline_word_refused_twice_is_recorded_and_never_opened_again(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    lane = root / jri.RUN_DIR / 'docxodus'
    (lane / 'pdf_by_word' / 'wct1_docxodus.pdf').unlink()
    steps = _sample(root, regen, 9)
    for key in ('twc0', 'wct1', 'wct0'):  # Docxodus redlined three pairs; Word exported wct0 and wct1 only
        _put(lane / 'docx' / f'{key}_docxodus.docx')
    _put(lane / 'pdf_by_word' / 'wct1_docxodus.pdf')
    said = _act(steps, 'word refusals docxodus')
    assert said.startswith('1 Docxodus redlines Word refused twice') and '1 on record for Docxodus 12.6.5 (C#)' in said
    assert sorted(p.name for p in (lane / 'docx').iterdir()) == ['wct0_docxodus.docx', 'wct1_docxodus.docx']
    refused = lane / 'docx_refused' / 'twc0_docxodus.docx'
    assert jri.read_csv(jri.refused_ledger(root)) == [
        {'key': 'twc0', 'tool_version': 'Docxodus 12.6.5 (C#)', 'docx_sha256': _sha(refused),
         'recorded': jri.read_csv(jri.refused_ledger(root))[0]['recorded']}]
    # the pair is not handed to Docxodus again, and a second pass records nothing new
    assert '0 pairs without a docxodus Word PDF' in _act(steps, 'docxodus manifest')
    assert _act(steps, 'word refusals docxodus').startswith('0 Docxodus redlines')
    # another Docxodus version starts with a clean record
    (root / jri.RUN_DIR / 'versions.json').write_text(json.dumps({'docxodus': 'Docxodus 13.0.0 (C#)'}))
    assert jri.word_refused(root) == set()
    assert '1 pairs without a docxodus Word PDF' in _act(steps, 'docxodus manifest')


# ------------------------------------------------------------------ export, measure, convert, score

def test_word_exports_run_under_the_watchdog_with_timeout_300_and_may_fail(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[])
    exports = [s for s in steps if s.stage == 'export' and s.argv]
    assert len(exports) == 4  # batch + retry, jubarte lane and docxodus lane
    # what Word refused in both docxodus passes is recorded right after them
    assert [s.name for s in steps if s.stage == 'export'][-1] == 'word refusals docxodus'
    for s in exports:
        assert '--timeout' in s.argv and s.argv[s.argv.index('--timeout') + 1] == '300'
        assert '--do-not-close' in s.argv
        # Word's dialogs name the staged file: the label in front says whose it is
        assert s.argv[s.argv.index('--label') + 1] == ('docxodus' if 'docxodus' in s.name else 'jubarte')
        assert s.may_fail
        log = Path(s.argv[s.argv.index('--log') + 1])
        assert log in s.watch  # the watchdog follows the log the export grows
    retries = [s for s in exports if '--no-one-osascript' in s.argv]
    assert len(retries) == 2
    assert {s.watch[1] for s in retries} == {  # the retry pass also watches the folder it delivers to
        jri.RUN_DIR / LANE / 'pdf_by_word', jri.RUN_DIR / 'docxodus' / 'pdf_by_word'}


def test_an_adopted_lane_skips_word_altogether(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[])
    assert next(s for s in steps if s.name == 'word answers').stage == 'export'
    kept = jri.select(steps, skip=['export', 'generate'])
    assert not any('word' in s.name or 'redlines' in s.name for s in kept)
    assert [s.name for s in jri.select(steps, only=['install', 'sample'])] == \
        ['bench inputs', 'release binary', 'draw redline sample', 'draw conversion sample']
    # with the export stage in, Word is asked before anything else runs
    assert jri.select(steps, only=['generate', 'export'])[0].name == 'word answers'


def test_measure_scores_the_sample_one_tool_at_a_time(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[], jobs=6)
    jub = _cmd(steps, 'measure jubarte')
    docx = _cmd(steps, 'measure docxodus')
    for cmd in (jub, docx):
        assert cmd[cmd.index('--sample-csv') + 1].endswith(f'sample_redline_{V}.csv')
        assert '--fresh' in cmd and '--regen-list' in cmd
        assert cmd[cmd.index('--jobs') + 1] == '6'
    assert jub[-1] == LANE
    assert docx[-1] == 'docxodus'
    order = [s.name for s in steps if s.stage in ('measure', 'convert', 'score')]
    # one scoring job at a time: jubarte, docxodus, the convert-and-score, the score-only
    assert order == ['measure jubarte', 'measure docxodus', 'convert jubarte (converts + scores)',
                     'soffice missing list', 'convert soffice (missing only)',
                     'stage soffice renders', 'score soffice (score-only)']


def test_convert_takes_one_files_list_flag_per_fixture(tmp_path: Path) -> None:
    files = ['corpus/word/clean/docx/a.docx', 'corpus/word/clean/docx/b.docx']
    steps = jri.plan(_rel(tmp_path), binary=Path('/bin/j'), conversion=files, jobs=5, convert_workers=2)
    convert = _cmd(steps, 'convert jubarte (converts + scores)')
    assert convert[convert.index('--converter') + 1] == '/bin/j'
    assert convert[convert.index('--origin') + 1] == 'list'
    given = [convert[i + 1] for i, flag in enumerate(convert) if flag == '--files-list']
    assert given == files  # one flag per file, in sample order
    assert convert[convert.index('--work-dir') + 1].endswith('convert_work')
    assert convert[convert.index('--json') + 1].endswith(f'docx_to_pdf_jubarte_{V}_sample.json')
    assert convert[convert.index('--jobs') + 1] == '5'
    assert convert[convert.index('--convert-workers') + 1] == '2'
    missing = _cmd(steps, 'convert soffice (missing only)')
    assert missing[missing.index('--engine') + 1] == 'soffice'
    assert missing[missing.index('--out') + 1] == str(jri.SOFFICE_WORK)
    assert missing[missing.index('--files-list') + 1].endswith('soffice_missing.txt')
    defaults = _cmd(jri.plan(_rel(tmp_path), conversion=files), 'convert jubarte (converts + scores)')
    assert defaults[defaults.index('--jobs') + 1] == '4'
    assert defaults[defaults.index('--convert-workers') + 1] == '3'


def test_soffice_renders_are_staged_under_the_docx_stem_and_scored_from_there(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    lines = [f'corpus/word/{state}/docx/fx{s}{i}.docx' for s, state in enumerate(jri.CONVERSION_QUOTAS) for i in (0, 1)]
    _put(root / 'convert.txt', '\n'.join(lines).encode())
    steps = _sample(root, regen, 8, jobs=5, adopt_conversion_list=Path('convert.txt'))
    ev = jri.evidence_dir(V)
    assert '1 fixtures without a LibreOffice render' in _act(steps, 'soffice missing list')
    assert (root / ev / 'soffice_missing.txt').read_text() == 'corpus/word/clean/docx/fx00.docx\n'
    other = _put(root / ev / 'soffice_sample' / 'someone_elses.pdf')
    stale = _put(root / ev / 'soffice_sample' / 'fx00.pdf')  # staged once, its render is gone: it must score 0
    assert '7 renders staged, 1 fixtures without one' in _act(steps, 'stage soffice renders')
    staged = sorted(p.name for p in (root / ev / 'soffice_sample').iterdir() if p != other)
    sampled = jri.read_csv(root / jri.conversion_list(V))
    assert staged == sorted(f'{Path(r["docx"]).stem}.pdf' for r in sampled if r['stem'] != 'clean__fx00')
    assert other.is_file() and not stale.exists()  # nothing else in the folder is touched
    kept = root / ev / 'soffice_sample' / 'fx01.pdf'
    before = kept.stat().st_mtime_ns
    _put(root / ev / 'soffice_sample' / 'fx10.pdf', b'an older render')
    _act(steps, 'stage soffice renders')  # a rerun rewrites only what differs
    assert kept.stat().st_mtime_ns == before
    assert (root / ev / 'soffice_sample' / 'fx10.pdf').read_bytes() == b'tracking_without_comments__fx10.pdf'
    score = _cmd(_plan(root, regen, n=8, jobs=5), 'score soffice (score-only)')
    assert '--score-only' in score
    assert '--tool' not in score  # --tool takes runnable converters; the report key is then 'candidates'
    assert score[score.index('--tool-version') + 1] == 'LibreOffice 26.8.0.3' == jri.SOFFICE_VERSION
    assert score[score.index('--location-to-score') + 1] == str(ev / 'soffice_sample')
    assert score[score.index('--work-dir') + 1] == str(ev / 'soffice_score_work')
    assert score[score.index('--jobs') + 1] == '5'
    assert score[score.index('--json') + 1].endswith(f'docx_to_pdf_soffice_{V}_sample.json')
    assert [score[i + 1] for i, flag in enumerate(score) if flag == '--files-list'] == [r['docx'] for r in sampled]
    # two sampled fixtures with one docx stem could not be told apart by --score-only
    jri.write_csv(root / jri.conversion_list(V), jri.CONVERSION_FIELDS,
                  [{'state': 'clean', 'stem': 'clean__same', 'docx': 'corpus/word/clean/docx/same.docx'},
                   {'state': 'with_comments_clean', 'stem': 'with_comments_clean__same',
                    'docx': 'corpus/word/with_comments_clean/docx/same.docx'}])
    with pytest.raises(RuntimeError, match='share the docx stem same'):
        _act(steps, 'stage soffice renders')


def test_conversion_scores_are_intent_to_treat_and_ignore_letter_case() -> None:
    report = {'tools': {'soffice': {'per_doc': {'CLEAN__Report_A': 81.5, 'clean__b': 0.0}}}}
    scores = jri.report_scores(report, 'soffice', ['clean__report_a', 'clean__b', 'clean__left_out'])
    assert scores == {'clean__report_a': 81.5, 'clean__b': 0.0, 'clean__left_out': 0.0}
    block = jri.tool_block({'version': 'x'}, scores, dict.fromkeys(scores, 'clean'))
    assert block['n'] == 3 and block['failures'] == 2  # the fixture the report left out is a failure
    with pytest.raises(RuntimeError, match="scores \\['soffice'\\], not jubarte"):
        jri.report_scores(report, 'jubarte', ['clean__b'])


# ------------------------------------------------------------------ write

def _scored(root: Path, steps: list[Step], binary: Path) -> dict:
    """Everything the write stage reads, made after the sample: lane files, scores, reports."""
    ev = root / jri.evidence_dir(V)
    sample = jri.read_csv(root / jri.redline_list(V))
    pairs = [r['key'] for r in jri.read_csv(ev / 'gen_pairs_sample.csv')]
    lane = root / jri.RUN_DIR / LANE
    for key in pairs:
        _put(lane / 'docx' / f'{key}_{LANE}.docx')
        if key != 'twc1':  # Word could not open this redline: no PDF, the compare scores 0
            _put(lane / 'pdf_by_word' / f'{key}_{LANE}.pdf')
    for tool, base in ((LANE, 80.0), ('docxodus', 60.0)):
        rows = {r['key']: {'overall_score': base + i % 5, 'overall_score_pagefair': base + i % 5}
                for i, r in enumerate(sample) if r['key'] != 'twc1'}
        (root / jri.scores_json(tool, V)).write_text(json.dumps({'rows': rows}))
    conv = jri.read_csv(root / jri.conversion_list(V))
    absent = conv[2]['stem']
    for i, r in enumerate(conv):
        if r['stem'] != absent:
            _put(ev / 'convert_work' / 'jubarte' / 'candidate' / f'{r["stem"]}.pdf')
    for tool, base in (('jubarte', 90.0), ('soffice', 70.0)):
        per = {(r['stem'].upper() if i == 0 else r['stem']): base + i % 3
               for i, r in enumerate(conv) if r['stem'] != absent}  # one key in another case, one left out
        (root / jri.conversion_report(tool, V)).write_text(json.dumps(
            {'tools': {tool: {'version': 'jubarte 0.11.0' if tool == 'jubarte' else None, 'per_doc': per}}}))
    return {'sample': sample, 'conv': conv, 'absent': absent, 'binary_sha': _sha(binary)}


def _six(folder: Path) -> dict[str, Path]:
    return {p.name.split(f'_{V}_')[0]: p for p in folder.iterdir() if f'_{V}_' in p.name}


def _checker():
    if not CHECKER.is_file():
        pytest.skip(f'no engine-side checker at {CHECKER}')
    spec = importlib.util.spec_from_file_location('check_release_info', CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('mode', ['draw', 'adopt'])
def test_sample_then_write_passes_the_engine_checker(tmp_path: Path, mode: str) -> None:
    root, regen = _tree(tmp_path, fill=21, fixtures=8)
    binary = _put(tmp_path / 'build' / 'jubarte-rc')
    engine = tmp_path / 'engine'
    adopt = {}
    if mode == 'adopt':
        pool = jri.read_csv(root / jri.RUN_DIR / 'pool_pairs.csv')
        jri.write_csv(root / 'results/mine.csv', jri.GEN_FIELDS, [r for r in pool if r['key'] != 'wct0b'])
        lines = [f'corpus/word/{state}/docx/fx{s}{i}.docx'
                 for s, state in enumerate(jri.CONVERSION_QUOTAS) for i in range(6)]
        _put(root / 'results/convert.txt', ('\n'.join(lines) + '\n').encode())
        adopt = {'adopt_redline_csv': Path('results/mine.csv'), 'adopt_conversion_list': Path('results/convert.txt')}
    steps = _sample(root, regen, 24, binary=binary, engine_dir=engine, run=_answers, **adopt)
    made = _scored(root, steps, binary)  # the lane and the scores exist only after the sample
    stale = _put(engine / 'release_info' / f'sample_redline_{V}_01-01-26_00-00.csv')
    other = _put(engine / 'release_info' / 'sample_redline_0.11.2_01-01-26_00-00.csv')
    detail = _act(steps, 'release_info')
    folder = engine / 'release_info'
    six = _six(folder)
    assert len(six) == 6 and not stale.exists() and other.exists()
    assert f'six files of {V}' in detail and 'reports "jubarte 0.11.0"' in detail
    assert _checker().problems(V, folder, 24) == []

    # every path is relative to the bench root, each with the sha256 of the file on disk now
    for name in ('sample_redline', 'sample_conversion', 'results_redline', 'results_conversion'):
        assert str(tmp_path) not in six[name].read_text() and '/Users/' not in six[name].read_text()
    with six['sample_redline'].open(newline='') as fh:
        rows = {r['key']: r for r in csv.DictReader(fh)}
    assert len(rows) == 24 and set(rows) == {r['key'] for r in made['sample']}
    a = rows['wct0']  # the pair's one compare: its own oracle, the pair's first-key redline
    assert 'wct0b' not in rows
    assert a['jubarte_docx'] == f'{jri.RUN_DIR}/{LANE}/docx/wct0_{LANE}.docx'
    assert a['jubarte_docx_sha256'] == _sha(root / a['jubarte_docx'])  # made after the sample was taken
    assert a['docxodus_pdf'] == f'{jri.RUN_DIR}/docxodus/pdf_by_word/wct0_docxodus.pdf'
    assert a['oracle_pdf'] == f'{jri.RUN_DIR}/oracle_pdf/wct0.pdf'
    assert a['base'] == 'corpus/word/clean/docx/wct0_base.docx'
    fresh = rows['wct1']
    assert fresh['oracle'] == 'fresh' and fresh['oracle_pdf'] == '../compare_regen/out/idwct1__vs__idwct1.pdf'
    assert fresh['oracle_pdf_sha256'] == _sha(tmp_path / 'compare_regen/out/idwct1__vs__idwct1.pdf')
    gone = rows['twc1']  # no Word PDF of the jubarte redline, no docxodus PDF for twc0: empty path, empty sha
    assert gone['jubarte_docx'] and (gone['jubarte_pdf'], gone['jubarte_pdf_sha256']) == ('', '')
    assert (rows['twc0']['docxodus_pdf'], rows['twc0']['docxodus_pdf_sha256']) == ('', '')
    with six['sample_conversion'].open(newline='') as fh:
        conv = {r['stem']: r for r in csv.DictReader(fh)}
    assert len(conv) == 24
    some = next(r for stem, r in conv.items() if stem not in (made['absent'], 'clean__fx00'))
    assert some['soffice_pdf'] == f'{jri.SOFFICE_WORK}/candidate/{some["stem"]}.pdf'
    assert some['jubarte_pdf'] == f'{jri.evidence_dir(V)}/convert_work/jubarte/candidate/{some["stem"]}.pdf'
    assert some['jubarte_pdf_sha256'] == _sha(root / some['jubarte_pdf'])
    assert (conv[made['absent']]['jubarte_pdf'], conv[made['absent']]['jubarte_pdf_sha256']) == ('', '')

    # the candidate's identity, in both results
    redline = json.loads(six['results_redline'].read_text())
    conversion = json.loads(six['results_conversion'].read_text())
    for doc in (redline, conversion):
        jub = doc['tools']['jubarte']
        assert jub['version'] == f'jubarte {V}' and jub['candidate_reports'] == 'jubarte 0.11.0'
        assert jub['binary_sha256'] == made['binary_sha'] and jub['commit'] == 'c0ffee'
        assert doc['sample']['csv'] == six[f'sample_{doc["schema"].split("_")[-1].split("/")[0]}'].name
    meta = json.loads((root / jri.evidence_dir(V) / 'sample_meta.json').read_text())
    assert redline['sample']['drawn'] == meta['redline'] and conversion['sample']['drawn'] == meta['conversion']
    assert ('adopted from' in meta['redline']['rule']) == (mode == 'adopt')
    assert redline['sample']['n'] == 24 and redline['sample']['pairs'] == 24
    assert redline['provenance']['scores'][LANE] == f'{jri.RUN_DIR}/scores_{LANE}_sample_redline_{V}.json'
    assert redline['tools']['jubarte']['failures'] == 1  # twc1 has no scored PDF
    assert redline['comparison']['bootstrap'] == {'reps': 2000, 'seed': 42}
    assert redline['comparison']['ci95'][0] <= redline['comparison']['ci95'][1]

    # intent-to-treat: the fixture the reports left out scores 0; the upper-cased key still counts
    jub_c, sof_c = conversion['tools']['jubarte'], conversion['tools']['soffice']
    assert jub_c['n'] == sof_c['n'] == 24 and jub_c['failures'] == sof_c['failures'] == 1
    assert jub_c['per_document'][made['absent']] == 0
    assert jub_c['per_document'][made['conv'][0]['stem']] == 90
    assert sof_c['version'] == 'LibreOffice 26.8.0.3' == conversion['versions']['libreoffice']
    assert conversion['comparison']['comparator'] == 'soffice' and 'ci95' in conversion['comparison']

    # the website records: the real scorer, each tool's own interval, placeholders marked pending
    site = [json.loads(line) for line in six['website_data'].read_text().splitlines()]
    by_key = {r['key']: r for r in site}
    assert {'engine.version', 'bench.tables', 'bench.states'} <= set(by_key)
    table = by_key['bench.tables']['value'][0]
    assert '<scorer>' not in table['meta'] and f'scorer {conversion["versions"]["scorer"]}' in table['meta']
    for row, tool in zip(table['rows'], (jub_c, sof_c)):
        assert row['note'] == f'[{tool["median_ci95"][0]}, {tool["median_ci95"][1]}]'
    assert jub_c['median_ci95'] != conversion['comparison']['ci95']
    assert jub_c['median_ci95'][0] <= jub_c['median'] <= jub_c['median_ci95'][1]
    pending = {r['key'] for r in site if r.get('pending')}
    assert pending == {'engine.released', 'release.archives', 'release.wheels', 'release.history', 'bench.version'}
    for r in site:
        assert set(r) - {'pending'} == {'id', 'ts', 'key', 'value', 'source'} and r['ts'].endswith('Z')
        assert r.get('pending', False) == (isinstance(r['value'], str) and r['value'].startswith('<'))
    app = [json.loads(line) for line in six['app_data'].read_text().splitlines()]
    assert {'app.version/package.json', 'app.changelog', 'facts/engine.version'} <= {r['key'] for r in app}
    assert all(r['file'] and r['where'] for r in app)
    assert all(r.get('pending', False) == r['value'].startswith('<') for r in app)

    # a second write re-stamps the whole set, still six files of this version
    _act(steps, 'release_info')
    assert len(_six(folder)) == 6


def test_the_write_stage_needs_the_engine_checkout_and_the_sample_meta(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    binary = _put(tmp_path / 'jubarte')
    with pytest.raises(RuntimeError, match='needs --engine-dir'):
        _act(_plan(root, regen, binary=binary, run=_answers), 'release_info')
    with pytest.raises(RuntimeError, match='the sample stage writes it'):
        _act(_plan(root, regen, binary=binary, engine_dir=tmp_path / 'engine', run=_answers), 'release_info')


# ------------------------------------------------------------------ select, plan, execute

def test_only_and_skip_keep_the_order_and_run_the_preflights_first(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[])
    names = [s.name for s in jri.select(steps, only=['sample', 'measure'])]
    assert names[0] == 'bench inputs'  # preflights first
    assert 'measure jubarte' in names and 'draw redline sample' in names
    assert 'release binary' not in names and 'release_info' not in names
    assert all(s.stage != 'export' for s in jri.select(steps, skip=['export', 'score']))
    with pytest.raises(ValueError, match='unknown stage'):
        jri.select(steps, only=['sample', 'word'])
    with pytest.raises(ValueError, match='unknown stage'):
        jri.select(steps, skip=['write'], only=['install', 'six'])


def test_plan_flag_prints_and_runs_nothing(tmp_path: Path) -> None:
    out = CliRunner().invoke(jri.app, [V, '--root', str(tmp_path), '--plan', '--only', 'sample,score',
                                       '--adopt-redline', 'mine.csv', '--jobs', '7'])
    assert out.exit_code == 0, out.output
    lines = out.output.splitlines()
    assert lines[0] == 'sample    (bench inputs)' and lines[1] == 'sample    (adopt redline sample)'
    assert lines[2] == 'sample    (draw conversion sample)'
    assert 'score     uv run bench docx-to-pdf --score-only --tool-version' in out.output
    assert '--jobs 7' in lines[-1]
    assert not (tmp_path / 'results').exists()
    bad = CliRunner().invoke(jri.app, [V, '--plan', '--skip', 'word'])
    assert bad.exit_code != 0


def test_the_plan_reads_the_fixtures_of_the_list_being_adopted_and_folds_them(tmp_path: Path) -> None:
    lines = [f'corpus/word/clean/docx/d{i}.docx' for i in range(5)]
    _put(tmp_path / 'convert.txt', '\n'.join(lines).encode())
    steps = jri.plan(_rel(tmp_path), adopt_conversion_list=Path('convert.txt'))
    convert = next(s for s in steps if s.name == 'convert jubarte (converts + scores)')
    assert [convert.argv[i + 1] for i, flag in enumerate(convert.argv) if flag == '--files-list'] == lines
    line = jri.shown(convert)
    assert '--files-list <5 fixtures, one flag each> --work-dir' in line and 'd3.docx' not in line
    assert line.endswith(f'> {convert.log}')
    short = jri.plan(_rel(tmp_path), conversion=lines[:2])
    assert jri.shown(short[-2]) == short[-2].shown()
    docxodus = next(s for s in steps if s.name == 'docxodus redlines (missing only)')
    assert jri.shown(docxodus).startswith('(docxodus redlines (missing only): node --import tsx')


def test_a_failed_step_stops_the_run_and_a_may_fail_step_does_not(tmp_path: Path) -> None:
    steps = jri.select(jri.plan(_rel(tmp_path), conversion=[]), only=['measure', 'export'])
    steps = [s for s in steps if s.action is None]
    rec = Recorder(codes={'measure jubarte': 1, 'word export jubarte (batch)': 1})
    done = execute(steps, tmp_path, run=rec.run, spawn=rec.spawn, echo=lambda _: None)
    assert rec.ran == ['word export jubarte (batch)',
                       'word export jubarte (one osascript per document)',
                       'word export docxodus (batch)',
                       'word export docxodus (one osascript per document)',
                       'measure jubarte']  # a failed export pass does not stop the run, a failed measure does
    assert not done[-1].ok and 'exit 1' in done[-1].detail
    assert all(o.ok or o.step.may_fail for o in done[:-1])


def test_the_stamp_is_the_owners_format(tmp_path: Path) -> None:
    assert jri.stamp_now(datetime(2026, 10, 3, 16, 51)) == '10-03-26_16-51'
    assert jri.stamp_now(datetime(2026, 1, 2, 3, 4)) == '01-02-26_03-04'


def test_two_scoring_jobs_never_share_a_stage_concurrently() -> None:
    """The plan is a list and execute walks it in order; every scoring job sits
    in its own Step, so no two scorers run at once (the watchdog contract)."""
    steps = jri.plan(_rel(Path('/tmp/x')), conversion=['corpus/word/clean/docx/a.docx'])
    scorers = [s.name for s in steps if s.name.startswith(('measure', 'convert jubarte', 'score '))]
    assert scorers == ['measure jubarte', 'measure docxodus', 'convert jubarte (converts + scores)',
                       'score soffice (score-only)']
    assert len(scorers) == len(set(scorers))


@dataclass
class StuckDog(Dog):
    """A watchdog that outlives its terminate: the first wait times out."""

    killed: bool = False

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> int:
        if timeout is not None and not self.killed:
            raise subprocess.TimeoutExpired('zsh', timeout)
        return -9


def test_a_watchdog_that_will_not_stop_is_killed_and_the_step_keeps_its_result(tmp_path: Path) -> None:
    dogs: list[StuckDog] = []

    def spawn(argv, root: Path) -> StuckDog:
        dogs.append(StuckDog(list(argv)))
        return dogs[-1]

    step = Step('export', 'export', ('true',), watch=('export.log',))
    done = execute([step], tmp_path, run=lambda s, r: 0, spawn=spawn, echo=lambda _: None)
    assert len(done) == 1 and done[0].ok
    assert dogs[0].stopped and dogs[0].killed


def test_stopping_the_watchdog_stops_what_it_started(tmp_path: Path) -> None:
    from neurotic_docx_bench import jubarte_bench_release as jbr

    dog = jbr.default_spawn(['zsh', '-c', 'sleep 30 & wait'], tmp_path)
    deadline = time.monotonic() + 5
    children: list[int] = []
    while not children and time.monotonic() < deadline:
        out = subprocess.run(['pgrep', '-P', str(dog.pid)], capture_output=True, text=True).stdout
        children = [int(pid) for pid in out.split()]
        time.sleep(0.05)
    assert children, 'the shell never started its child'
    dog.terminate()
    dog.wait(timeout=5)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            import os

            os.kill(children[0], 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        pytest.fail(f'the watchdog child {children[0]} outlived terminate')
