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
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import fixed_sets as fs
from neurotic_docx_bench import jubarte_release_info as jri
from neurotic_docx_bench.jubarte_bench_release import Outcome, Release, Step, execute

V = '0.11.3'
LANE = f'jubarte-{V}'
COMMIT = 'c0ffee' + '0' * 34
REPO = Path(__file__).resolve().parents[1]
# the engine's own release gate (scripts/release.sh step 3), from the canonical checkout
CHECKER = Path(__file__).resolve().parents[1] / 'src/neurotic_docx_bench/utils/jubarte/jubarte-redlines/scripts/check_release_info.py'


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
    if cmd[0] == 'git':  # rev-parse --verify always answers the full 40-hex id
        return Proc(0, COMMIT + '\n')
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
    (regen / 'regen_list.csv').write_text('id\nidwct1\n')
    for r in gen:
        if r['key'] != 'twc0':
            _put(run / 'docxodus' / 'pdf_by_word' / f'{r["key"]}_docxodus.pdf')
    for s, state in enumerate(jri.CONVERSION_QUOTAS):
        for i in range(fixtures):
            _put(word / state / 'docx' / f'fx{s}{i}.docx')
            _put(word / state / 'pdf' / f'fx{s}{i}.pdf')
    for pdf in word.glob('*/pdf/*.pdf'):
        if pdf.stem != 'fx00':
            _put(root / jri.SOFFICE_WORK / 'candidate' / f'{pdf.parent.parent.name}__{pdf.stem}.pdf',
                 f'%PDF-1.7 {pdf.stem}'.encode())
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
    # the fixed-set flow (#130) replaces the draw's sample stage with a sets stage;
    # --draw-sample keeps the old one for regenerating archived evidence
    assert jri.STAGES == ('install', 'sample', 'sets', 'generate', 'export', 'measure', 'convert',
                          'score', 'write', 'publish')
    for kw in ({}, {'draw_sample': True}):
        steps = jri.plan(_rel(Path('/tmp/x')), conversion=['clean/docx/a.docx'], **kw)
        assert [s.stage for s in steps] == sorted((s.stage for s in steps), key=jri.STAGES.index)


def test_the_publish_stage_uploads_the_release_own_outputs_and_records_the_revision(
    tmp_path: Path,
) -> None:
    """The fixed-set flow's last step publishes the release's own lane (#143)."""
    from test_hub_outputs import FakeOutputsHub

    root, regen = _tree(tmp_path)
    _write_sets(root)
    ev = root / jri.evidence_dir(V)
    candidate = ev / 'convert_work' / 'jubarte' / 'candidate'
    candidate.mkdir(parents=True, exist_ok=True)
    (candidate / 'clean__fx0.pdf').write_bytes(b'%PDF-1.7 fx0')
    (ev / f'docx_to_pdf_jubarte_{V}_sample.json').write_text(json.dumps({
        'n': 1,
        'stems': ['clean__fx0'],
        'tools': {'jubarte': {'tool': 'jubarte', 'version': f'jubarte {V}', 'n_scored': 1,
                              'per_doc': {'clean__fx0': 90.0}, 'generate_failures': [], 'failures': 0}},
    }))
    lane = root / jri.RUN_DIR / LANE
    (lane / 'docx').mkdir(parents=True, exist_ok=True)
    (lane / 'pdf_by_word').mkdir(parents=True, exist_ok=True)
    (lane / 'docx' / f'cle0_{LANE}.docx').write_bytes(b'redline')
    (lane / 'pdf_by_word' / f'cle0_{LANE}_byword.pdf').write_bytes(b'%PDF-1.7 cle0')

    api = FakeOutputsHub()
    steps = _plan(root, regen, api=api)
    assert [s.name for s in steps if s.stage == 'publish'] == [
        'upload the jubarte lane to the results dataset'
    ]
    detail = _act(steps, 'upload the jubarte lane to the results dataset')
    assert 'uploaded and verified' in detail
    assert f'outputs/convert_860/jubarte_{V}/pdf/clean__fx0.pdf' in api.stored
    assert f'outputs/redlines_0929_full/{LANE}/pdf_by_word/cle0_{LANE}_byword.pdf' in api.stored
    evidence = json.loads((ev / 'release_info' / 'hub_outputs.json').read_text())
    assert evidence['revision'] == api.head
    assert evidence['verified'] is True
    assert evidence['paths'][0] == f'outputs/convert_860/jubarte_{V}'


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
        # the sets flow measures jubarte only; the comparators are read, not run
        assert len(lines) == 1 and lines[0].startswith('measure   uv run python'), out.stdout
        out = subprocess.run([sys.executable, *argv, V, '--root', str(tmp_path), '--plan', '--only', 'measure',
                              '--draw-sample'], cwd=REPO, capture_output=True, text=True)
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
    steps = _plan(root, regen, n=8, draw_sample=True)
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
    _act(_plan(root, regen, n=8, draw_sample=True), 'draw redline sample')
    keys = [r['key'] for r in jri.read_csv(root / jri.redline_list(V))]
    assert 'cle0' not in keys and len(keys) == 8
    with pytest.raises(RuntimeError, match='only 8 compares have their Word PDF, 10 wanted'):
        _act(_plan(root, regen, n=10, draw_sample=True), 'draw redline sample')


def test_evidence_names_carry_the_version_so_measure_never_resumes_another_release(tmp_path: Path) -> None:
    assert jri.redline_list(V) == Path(f'results/release_{V}_evidence/sample_redline_{V}.csv')
    assert jri.conversion_list(V) == Path(f'results/release_{V}_evidence/sample_conversion_{V}.csv')
    assert jri.scores_json(LANE, V) == jri.RUN_DIR / f'scores_{LANE}_sample_redline_{V}.json'
    assert jri.scores_json('docxodus', '0.11.4') != jri.scores_json('docxodus', V)
    for kw in ({}, {'draw_sample': True}):
        steps = jri.plan(_rel(tmp_path), conversion=[], **kw)
        cmd = _cmd(steps, 'measure jubarte')
        assert cmd[cmd.index('--sample-csv') + 1] == str(jri.redline_list(V))
    docxodus = [s for s in jri.plan(_rel(tmp_path), conversion=[], draw_sample=True) if s.stage == 'export'
                and 'docxodus' in s.name and s.argv]
    assert docxodus and all(V in str(s.log) and V in s.argv[s.argv.index('--log') + 1] for s in docxodus)


def test_adopting_validates_the_lists_and_records_where_they_came_from(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    pool = jri.read_csv(root / jri.RUN_DIR / 'pool_pairs.csv')
    mine = root / 'results/mine.csv'
    picked = [r for r in pool if r['key'] != 'wct0b'][:5]
    jri.write_csv(mine, jri.GEN_FIELDS, picked)
    # a list that names a pair twice is refused: the sample is one compare per pair
    jri.write_csv(root / 'results/twice.csv', jri.GEN_FIELDS, pool[:5])
    with pytest.raises(RuntimeError, match='1 compares repeat a pair already listed'):
        _act(_plan(root, regen, n=5, draw_sample=True, adopt_redline_csv=Path('results/twice.csv')),
             'adopt redline sample')
    fixtures = [f'corpus/word/{state}/docx/fx{s}0.docx' for s, state in enumerate(jri.CONVERSION_QUOTAS)]
    listing = _put(root / 'results/convert.txt', ('\n'.join(fixtures) + '\n').encode())
    steps = _plan(root, regen, n=5, seed=7, draw_sample=True, adopt_redline_csv=Path('results/mine.csv'),
                  adopt_conversion_list=listing)
    assert [s.name for s in steps if s.stage == 'sample'] == \
        ['bench inputs', 'adopt redline sample', 'adopt conversion sample']
    assert 'adopted from results/mine.csv' in _act(steps, 'adopt redline sample')
    ev = root / jri.evidence_dir(V)
    assert [r['key'] for r in jri.read_csv(ev / f'sample_redline_{V}.csv')] == [r['key'] for r in picked]
    assert len(jri.read_csv(ev / 'gen_pairs_sample.csv')) == 5
    with pytest.raises(RuntimeError, match='4 fixtures, want 5'):
        _act(steps, 'adopt conversion sample')
    four = _plan(root, regen, n=4, seed=7, draw_sample=True, adopt_conversion_list=listing)
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
        _act(_plan(root, regen, n=4, draw_sample=True, adopt_redline_csv=root / 'mine.csv'),
             'adopt redline sample')
    missing = jri.select(_plan(root, regen, draw_sample=True, adopt_redline_csv=root / 'nope.csv'),
                         only=['sample'])[0]
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
    # a rerun with a new candidate must not keep the previous binary's redlines
    assert '--force' in generate
    _act(steps, 'generator dist')
    assert [p.name for p in (root / ev / 'dist').iterdir()] == ['jubarte']
    assert (root / ev / 'dist' / 'jubarte').resolve() == binary.resolve()
    # the docxodus generate-missing path is the --draw-sample flow's, not the fixed-set flow's
    docxodus = [s for s in steps if 'docxodus' in s.name]
    assert not docxodus
    steps = _plan(root, regen, binary=binary, draw_sample=True)
    docxodus = _cmd(steps, 'docxodus redlines (missing only)')
    assert docxodus[docxodus.index('--method') + 1] == 'docxodus-csharp-inproc'
    assert docxodus[docxodus.index('--dist') + 1] == str(jri.DOCXODUS_DIST)
    assert docxodus[docxodus.index('--tool') + 1] == 'docxodus'
    assert docxodus[docxodus.index('--manifest') + 1] == str(ev / 'gen_pairs_docxodus_missing.csv')
    assert '--force' not in docxodus
    names = [s.name for s in steps if s.stage == 'generate']
    assert names.index('docxodus PDFs from the hub') < names.index('docxodus manifest') \
        < names.index('docxodus redlines (missing only)')


def test_a_rewritten_redline_loses_its_old_word_pdf(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    jub = root / jri.RUN_DIR / LANE
    for stem in ('same', 'changed', 'unexported'):
        _put(jub / 'docx' / f'{stem}.docx', stem.encode())
    for stem in ('same', 'changed'):
        _put(jub / 'pdf_by_word' / f'{stem}.pdf', b'%PDF word')
    steps = _plan(root, regen)
    assert _act(steps, 'redline snapshot') == '3 redlines on record before generating'
    (jub / 'docx' / 'changed.docx').write_bytes(b'new candidate bytes')
    detail = _act(steps, 'stale Word PDFs aside')
    assert detail.startswith('1 Word PDFs of changed redlines moved to pdf_by_word_stale/')
    assert detail.endswith('; 2 redlines await a Word export')  # changed + unexported
    assert sorted(p.name for p in (jub / 'pdf_by_word').iterdir()) == ['same.pdf']
    assert [p.read_bytes() for p in (jub / 'pdf_by_word_stale').rglob('changed.pdf')] == [b'%PDF word']
    assert _act(steps, 'stale Word PDFs aside') == \
        'every exported redline is byte-identical to the one Word exported; 2 redlines await a Word export'
    names = [s.name for s in steps if s.stage == 'generate']
    assert names.index('redline snapshot') < names.index('jubarte redlines') < names.index('stale Word PDFs aside')


def test_a_pair_the_candidate_fails_scores_zero_not_the_old_binary_s_redline(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    jub = root / jri.RUN_DIR / LANE
    for key in ('kept', 'lost'):
        _put(jub / 'docx' / f'{key}_{LANE}.docx', key.encode())
        _put(jub / 'pdf_by_word' / f'{key}_{LANE}.pdf', b'%PDF old binary')
    steps = _plan(root, regen)
    _act(steps, 'redline snapshot')
    # --force rewrote 'kept' byte-identically; 'lost' threw, so its old bytes are still there
    _put(jub / 'generate_failures.json', json.dumps([{'doc': 'lost', 'stage': 'generate', 'error': 'x'}]).encode())
    detail = _act(steps, 'stale Word PDFs aside')
    assert '1 Word PDFs of changed redlines moved' in detail
    assert '1 redlines the candidate failed moved to docx_failed/' in detail and '(they score 0)' in detail
    assert sorted(p.name for p in (jub / 'docx').iterdir()) == [f'kept_{LANE}.docx']
    assert sorted(p.name for p in (jub / 'pdf_by_word').iterdir()) == [f'kept_{LANE}.pdf']
    assert [p.name for p in (jub / 'docx_failed').rglob('*.docx')] == [f'lost_{LANE}.docx']
    # a failures file older than the snapshot is an earlier run's: it names nothing now
    _put(jub / 'docx' / f'lost_{LANE}.docx', b'lost')
    _act(steps, 'redline snapshot')
    os.utime(jub / 'generate_failures.json', ns=(0, 0))
    assert 'candidate failed' not in _act(steps, 'stale Word PDFs aside')


def test_set_aside_copies_are_never_overwritten(tmp_path: Path) -> None:
    docx, pdf, ledger = tmp_path / 'docx', tmp_path / 'pdf_by_word', tmp_path / 'before.json'
    for n, stamp in enumerate((1_000_000_000, 1_000_000_100)):
        _put(docx / 'a.docx', f'v{n}'.encode())
        _put(pdf / 'a.pdf', f'%PDF {n}'.encode())
        ledger.write_text('{}')
        os.utime(ledger, (stamp, stamp))
        jri.set_aside_stale_pdfs(docx, pdf, ledger)
    assert sorted(p.read_bytes() for p in (tmp_path / 'pdf_by_word_stale').rglob('a.pdf')) == [b'%PDF 0', b'%PDF 1']


def test_a_word_pdf_without_recorded_source_bytes_counts_as_stale(tmp_path: Path) -> None:
    docx, pdf = tmp_path / 'docx', tmp_path / 'pdf_by_word'
    _put(docx / 'a.docx', b'a')
    _put(pdf / 'a.pdf', b'%PDF')
    assert jri.set_aside_stale_pdfs(docx, pdf, tmp_path / 'no-ledger.json').startswith('1 Word PDFs')
    assert not (pdf / 'a.pdf').exists()


def test_the_draw_counts_the_hub_listing_as_coverage_and_caches_it(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    fake = FakeHub(['twc0_docxodus.pdf', 'README.md'])
    steps = _plan(root, regen, n=9, draw_sample=True, hub=fake.hub())
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
    steps = _plan(root, regen, n=9, draw_sample=True, hub=fake.hub())
    detail = _act(steps, 'draw redline sample')
    assert '8 pairs with a docxodus Word PDF (local PDFs only: Hub unreachable (ConnectionError))' in detail
    assert not (root / jri.evidence_dir(V) / 'hub_docxodus_listing.json').exists()
    assert 'Hub unreachable (ConnectionError): nothing fetched, 1 pairs left to Docxodus' in \
        _act(steps, 'docxodus PDFs from the hub')
    assert fake.fetched == []
    assert 'Hub not consulted' in _act(_plan(root, regen, n=9, draw_sample=True), 'docxodus PDFs from the hub')


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
    steps = _sample(root, regen, 9, draw_sample=True, hub=fake.hub(), run=run)
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
    failing = _sample(root, regen, 9, draw_sample=True, run=lambda cmd, **_: Proc(1, '', 'boom'))
    (lane / 'twc0_docxodus.pdf').unlink()
    _act(failing, 'docxodus manifest')
    with pytest.raises(RuntimeError, match='exit 1'):
        _act(failing, 'docxodus redlines (missing only)')


def _docxodus_fails(root: Path, stage: str, error: str = 'Document has no w:body element.',
                    extra: tuple[str, ...] = ()) -> Callable[..., Proc]:
    """A generator run that writes nothing: Docxodus fails every pair it is given (and ``extra``)."""
    def run(cmd, **_):
        manifest = Path(cmd[cmd.index('--manifest') + 1])
        docs = [r['key'] for r in jri.read_csv(root / manifest)] + list(extra)
        failed = [{'doc': doc, 'stage': stage, 'error': f'docxodus-csharp-inproc: {error}'} for doc in docs]
        _put(root / cmd[cmd.index('--run-dir') + 1] / 'generate_failures.json', json.dumps(failed).encode())
        return Proc(1, 'wrote 0 redline(s)\n', f'{len(failed)} pair(s) skipped:\n')
    return run


def test_pairs_docxodus_itself_cannot_redline_score_zero_instead_of_stopping(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    lane = root / jri.RUN_DIR / 'docxodus' / 'pdf_by_word'
    for key in ('wct0', 'wct1'):
        (lane / f'{key}_docxodus.pdf').unlink()
    steps = _sample(root, regen, 9, draw_sample=True, run=_docxodus_fails(root, 'generate'))
    _act(steps, 'docxodus manifest')
    assert _act(steps, 'docxodus redlines (missing only)') == \
        '3 pairs Docxodus itself fails to redline (they score 0); none redlined'
    # the failures file that run left behind proves nothing about a run that crashed before writing one
    stale = _sample(root, regen, 9, draw_sample=True, run=lambda cmd, **_: Proc(1, '', 'crash'))
    with pytest.raises(RuntimeError, match='exit 1'):
        _act(stale, 'docxodus redlines (missing only)')
    # a source the generator could not find is the bench's fault, not Docxodus's: it stops the run
    missing = _sample(root, regen, 9, draw_sample=True, run=_docxodus_fails(root, 'missing_source'))
    with pytest.raises(RuntimeError, match='exit 1'):
        _act(missing, 'docxodus redlines (missing only)')
    # so is a worker that crashed or timed out on every pair
    for error in ('timeout waiting for worker reply after 15000 ms bin=x', 'worker exited before reply (code=1)'):
        harness = _sample(root, regen, 9, draw_sample=True, run=_docxodus_fails(root, 'generate', error))
        with pytest.raises(RuntimeError, match='exit 1'):
            _act(harness, 'docxodus redlines (missing only)')
    # a failures file naming more than this manifest is another run's
    other = _sample(root, regen, 9, draw_sample=True, run=_docxodus_fails(root, 'generate', extra=('not-in-the-sample',)))
    with pytest.raises(RuntimeError, match='exit 1'):
        _act(other, 'docxodus redlines (missing only)')
    # the lane's full-run failures record is never the release run's scratch
    cmd = _cmd(steps, 'docxodus redlines (missing only)')
    assert cmd[cmd.index('--run-dir') + 1] == str(jri.evidence_dir(V) / 'docxodus_generate')


def test_a_docxodus_redline_word_refused_twice_is_recorded_and_never_opened_again(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    lane = root / jri.RUN_DIR / 'docxodus'
    (lane / 'pdf_by_word' / 'wct1_docxodus.pdf').unlink()
    steps = _sample(root, regen, 9, draw_sample=True)
    # Docxodus redlined five pairs; Word exported wct0 and wct1 only
    for key in ('twc0', 'twc1', 'twc2', 'wct1', 'wct0'):
        _put(lane / 'docx' / f'{key}_docxodus.docx')
    for key in ('twc1', 'twc2'):
        (lane / 'pdf_by_word' / f'{key}_docxodus.pdf').unlink()
    _put(lane / 'pdf_by_word' / 'wct1_docxodus.pdf')
    # twc0 failed in both passes; twc1 failed, then failed its replay in the retry pass; twc2 has
    # no per-file failure at all (a pass that died at its preflight never opened it): not a refusal
    _put(lane / f'word_pdf.sample_{V}.log',
         b'| ERROR    | __main__:_finish:1745 - [batch] FAIL: twc0_docxodus.docx \xe2\x80\x94 document loaded empty\n')
    _put(lane / f'word_pdf.sample_{V}.retry.log',
         b'| ERROR    | __main__:_convert_serial:1574 - [1/3] FAIL: twc0_docxodus.docx \xe2\x80\x94 AppleEvent timed out\n'
         b'| ERROR    | __main__:_convert_serial:1574 - [2/3] FAIL: twc1_docxodus.docx \xe2\x80\x94 x (-2700)\n'
         b'| INFO     | __main__:_replay:1637 - [replay] still failing, so it is the file: '
         b'twc1_docxodus.docx \xe2\x80\x94 x (-2700)\n')
    said = _act(steps, 'word refusals docxodus')
    assert said.startswith('2 Docxodus redlines Word refused twice') and '2 on record for Docxodus 12.6.5 (C#)' in said
    assert said.endswith('; 1 without a Word PDF and no failure on record stay for the next export')
    assert sorted(p.name for p in (lane / 'docx').iterdir()) == \
        ['twc2_docxodus.docx', 'wct0_docxodus.docx', 'wct1_docxodus.docx']
    (lane / 'docx' / 'twc2_docxodus.docx').unlink()  # the next export got it
    _put(lane / 'pdf_by_word' / 'twc2_docxodus.pdf')
    (lane / 'docx_refused' / 'twc1_docxodus.docx').replace(tmp_path / 'twc1_docxodus.docx')
    refused = lane / 'docx_refused' / 'twc0_docxodus.docx'
    assert [{k: r[k] for k in ('key', 'tool_version', 'docx_sha256')} for r in jri.read_csv(jri.refused_ledger(root))] == [
        {'key': 'twc0', 'tool_version': 'Docxodus 12.6.5 (C#)', 'docx_sha256': _sha(refused)},
        {'key': 'twc1', 'tool_version': 'Docxodus 12.6.5 (C#)', 'docx_sha256': _sha(tmp_path / 'twc1_docxodus.docx')}]
    # the pair is not handed to Docxodus again, and a second pass records nothing new
    assert '0 pairs without a docxodus Word PDF' in _act(steps, 'docxodus manifest')
    assert _act(steps, 'word refusals docxodus').startswith('0 Docxodus redlines')
    # another Docxodus version starts with a clean record
    (root / jri.RUN_DIR / 'versions.json').write_text(json.dumps({'docxodus': 'Docxodus 13.0.0 (C#)'}))
    assert jri.word_refused(root) == set()
    assert '2 pairs without a docxodus Word PDF' in _act(steps, 'docxodus manifest')  # twc0, twc1


# ------------------------------------------------------------------ export, measure, convert, score

def test_word_exports_run_under_the_watchdog_with_timeout_300_and_may_fail(tmp_path: Path) -> None:
    # the fixed-set flow exports jubarte only: batch + retry, no docxodus lane
    steps = jri.plan(_rel(tmp_path), conversion=[])
    exports = [s for s in steps if s.stage == 'export' and s.argv]
    assert [s.name for s in exports] == ['word export jubarte (batch)',
                                         'word export jubarte (one osascript per document)']
    assert [s.name for s in steps if s.stage == 'export'][0] == 'word answers'
    # --draw-sample adds the docxodus lane and its refusal record
    steps = jri.plan(_rel(tmp_path), conversion=[], draw_sample=True)
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
    # a batch pass that refuses to start (exit 2) stops the run; a retry's refusal may follow work (#101)
    assert all(s.refusal_codes == (() if s in retries else (2,)) for s in exports)
    assert {s.watch[1] for s in retries} == {  # the retry pass also watches the folder it delivers to
        jri.RUN_DIR / LANE / 'pdf_by_word', jri.RUN_DIR / 'docxodus' / 'pdf_by_word'}


def test_an_adopted_lane_skips_word_altogether(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[], draw_sample=True)
    assert next(s for s in steps if s.name == 'word answers').stage == 'export'
    kept = jri.select(steps, skip=['export', 'generate'])
    assert not any('word' in s.name or 'redlines' in s.name for s in kept)
    assert [s.name for s in jri.select(steps, only=['install', 'sample'])] == \
        ['bench inputs', 'release binary', 'draw redline sample', 'draw conversion sample']
    # with the export stage in, Word is asked before anything else runs
    assert jri.select(steps, only=['generate', 'export'])[0].name == 'word answers'


def test_a_sets_lane_skips_word_too(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[])
    kept = jri.select(steps, skip=['export', 'generate'])
    assert not any('word' in s.name or 'redlines' in s.name for s in kept)
    assert [s.name for s in jri.select(steps, only=['install', 'sets'])] == \
        ['bench inputs', 'release binary', 'validate the fixed sets', 'adopt the fixed sets']
    assert jri.select(steps, only=['generate', 'export'])[0].name == 'word answers'


def test_measure_scores_the_sample_one_tool_at_a_time(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[], jobs=6)
    jub = _cmd(steps, 'measure jubarte')
    for cmd in (jub,):
        assert cmd[cmd.index('--sample-csv') + 1].endswith(f'sample_redline_{V}.csv')
        assert '--fresh' in cmd and '--regen-list' in cmd
        assert cmd[cmd.index('--jobs') + 1] == '6'
    assert jub[-1] == LANE
    order = [s.name for s in steps if s.stage in ('measure', 'convert', 'score')]
    # one scoring job at a time, and only jubarte is scored: the comparators are read (#130)
    assert order == ['measure jubarte', 'stale renders aside', 'convert jubarte (converts + scores)']
    steps = jri.plan(_rel(tmp_path), conversion=[], jobs=6, draw_sample=True)
    docx = _cmd(steps, 'measure docxodus')
    assert docx[-1] == 'docxodus' and docx[docx.index('--jobs') + 1] == '6'
    order = [s.name for s in steps if s.stage in ('measure', 'convert', 'score')]
    # the draw flow still measures docxodus and renders what soffice lacks
    assert order == ['measure jubarte', 'measure docxodus', 'stale renders aside',
                     'convert jubarte (converts + scores)',
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
    assert not [s for s in steps if s.stage in ('convert', 'score') and 'soffice' in s.name]  # jubarte only
    defaults = _cmd(jri.plan(_rel(tmp_path), conversion=files), 'convert jubarte (converts + scores)')
    assert defaults[defaults.index('--jobs') + 1] == '4'
    assert defaults[defaults.index('--convert-workers') + 1] == '3'
    # the soffice render-missing path is the --draw-sample flow's
    steps = jri.plan(_rel(tmp_path), binary=Path('/bin/j'), conversion=files, draw_sample=True)
    missing = _cmd(steps, 'convert soffice (missing only)')
    assert missing[missing.index('--engine') + 1] == 'soffice'
    assert missing[missing.index('--out') + 1] == str(jri.SOFFICE_WORK)
    assert missing[missing.index('--files-list') + 1].endswith('soffice_missing.txt')


def test_a_new_candidate_never_resumes_the_previous_binary_s_renders(tmp_path: Path) -> None:
    # bench docx-to-pdf resumes: it keeps every PDF and checkpointed score in its work folder
    root, regen = _tree(tmp_path)
    old, new = _put(tmp_path / 'old' / 'jubarte', b'old binary'), _put(tmp_path / 'new' / 'jubarte', b'new binary')
    work = root / jri.evidence_dir(V) / 'convert_work' / 'jubarte'
    names = [s.name for s in _plan(root, regen, binary=new) if s.stage == 'convert']
    assert names.index('stale renders aside') < names.index('convert jubarte (converts + scores)')
    assert _act(_plan(root, regen, binary=old), 'stale renders aside') == 'no earlier renders'
    _put(work / 'candidate' / 'fx00.pdf', b'%PDF old')
    _put(work / 'scores.checkpoint.jsonl', b'{"key": "fx00"}\n')
    assert _act(_plan(root, regen, binary=old), 'stale renders aside') == \
        f'resuming the renders of this binary ({_sha(old)[:12]})'
    assert (work / 'candidate' / 'fx00.pdf').is_file()
    detail = _act(_plan(root, regen, binary=new), 'stale renders aside')
    assert detail.startswith(f'renders of binary {_sha(old)[:12]} moved to convert_work_stale/')
    assert sorted(p.name for p in work.iterdir()) == ['binary.sha256']
    assert (work / 'binary.sha256').read_text() == _sha(new) + '\n'
    kept = work.parent.with_name('convert_work_stale')
    assert [p.read_bytes() for p in kept.rglob('fx00.pdf')] == [b'%PDF old']
    assert len(list(kept.rglob('scores.checkpoint.jsonl'))) == 1
    # renders nobody recorded belong to an unknown binary: they move aside too
    (work / 'binary.sha256').unlink()
    _put(work / 'candidate' / 'fx01.pdf', b'%PDF unknown')
    assert _act(_plan(root, regen, binary=new), 'stale renders aside').startswith(
        'renders of binary unrecorded moved to convert_work_stale/')
    assert len(list(kept.rglob('*.pdf'))) == 2  # the earlier set-aside copy is still there


def test_soffice_renders_are_staged_under_the_docx_stem_and_scored_from_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from neurotic_docx_bench.render import soffice as so

    root, regen = _tree(tmp_path)
    lines = [f'corpus/word/{state}/docx/fx{s}{i}.docx' for s, state in enumerate(jri.CONVERSION_QUOTAS) for i in (0, 1)]
    _put(root / 'convert.txt', '\n'.join(lines).encode())
    # the pinned LibreOffice answers, whatever soffice this machine has (or none)
    monkeypatch.setattr(so, 'find_soffice', lambda *a, **k: Path('soffice'))

    def pinned(cmd, **_):
        return Proc(0, f'{jri.SOFFICE_VERSION} bce0998afefdbc355585ca324285661a2170ba77\n') if cmd[-1] == '--version' \
            else Proc(1)

    steps = _sample(root, regen, 8, draw_sample=True, jobs=5, adopt_conversion_list=Path('convert.txt'), run=pinned)
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
    assert (root / ev / 'soffice_sample' / 'fx10.pdf').read_bytes() == b'%PDF-1.7 fx10'
    score = _cmd(_plan(root, regen, n=8, jobs=5, draw_sample=True), 'score soffice (score-only)')
    assert '--score-only' in score
    assert score[score.index('--tool') + 1] == 'soffice'  # the store label its converters.jsonl line maps by
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


def test_a_broken_soffice_render_is_rendered_again_not_published(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    _sample(root, regen, 9, draw_sample=True)
    cand = root / jri.SOFFICE_WORK / 'candidate'
    sample = jri.read_csv(root / jri.conversion_list(V))
    empty, truncated = [cand / f'{r["stem"]}.pdf' for r in sample if r['stem'] != 'clean__fx00'][:2]
    empty.write_bytes(b'')
    truncated.write_bytes(b'<html>a crash page</html>')
    missing = jri.soffice_missing(root / jri.conversion_list(V), root)
    assert sorted(missing) == sorted(r['docx'] for r in sample
                                     if r['stem'] in ('clean__fx00', empty.stem, truncated.stem))
    assert jri.stage_soffice(root / jri.conversion_list(V), root, tmp_path / 'staged')[1] == 3


def test_renders_of_another_libreoffice_never_join_the_set(tmp_path: Path, monkeypatch) -> None:
    root, regen = _tree(tmp_path)
    monkeypatch.setenv('SOFFICE', '/opt/lo/soffice')
    asked: list[list[str]] = []

    def lo(version: str):
        def run(cmd, **_):
            asked.append(list(cmd))
            return Proc(0, f'{version} bce0998afefdbc355585ca324285661a2170ba77\n') if cmd[-1] == '--version' else Proc(1)
        return run

    with pytest.raises(RuntimeError, match=re.escape('soffice is LibreOffice 25.2.1.1, not LibreOffice 26.8.0.3')):
        _act(_sample(root, regen, 9, draw_sample=True, run=lo('LibreOffice 25.2.1.1')), 'soffice missing list')
    assert asked[-1] == ['/opt/lo/soffice', '--version']
    said = _act(_sample(root, regen, 9, draw_sample=True, run=lo('LibreOffice 26.8.0.3')), 'soffice missing list')
    assert said.endswith('1 fixtures without a LibreOffice render (LibreOffice 26.8.0.3 renders them)')
    _put(root / jri.SOFFICE_WORK / 'candidate' / 'clean__fx00.pdf', b'%PDF-1.7')
    asked.clear()
    said = _act(_sample(root, regen, 9, draw_sample=True, run=lo('LibreOffice 25.2.1.1')), 'soffice missing list')
    assert said.endswith('0 fixtures without a LibreOffice render') and asked == []  # nothing to render


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
        # measure.py ran under --device mps: its own summary names the backend, not the writer's
        (root / jri.scores_json(tool, V)).write_text(json.dumps({'rows': rows,
                                                                 'summary': {'scorer_backend': 'torch-mps'}}))
    conv = jri.read_csv(root / jri.conversion_list(V))
    absent = conv[2]['stem']
    for i, r in enumerate(conv):
        if r['stem'] != absent:
            _put(ev / 'convert_work' / 'jubarte' / 'candidate' / f'{r["stem"]}.pdf')
    for tool, base in (('jubarte', 90.0), ('soffice', 70.0)):
        per = {(r['stem'].upper() if i == 0 else r['stem']): base + i % 3
               for i, r in enumerate(conv) if r['stem'] != absent}  # one key in another case, one left out
        (root / jri.conversion_report(tool, V)).write_text(json.dumps(
            {'scorer_backend': 'torch-cpu',
             'tools': {tool: {'version': 'jubarte 0.11.0' if tool == 'jubarte' else None, 'per_doc': per}}}))
    return {'sample': sample, 'conv': conv, 'absent': absent, 'binary_sha': _sha(binary)}


def test_score_artifacts_of_two_backends_are_never_published_as_one() -> None:
    assert jri.one_backend({'jubarte': 'torch-mps', 'docxodus': 'torch-mps'}) == 'torch-mps'
    assert jri.one_backend({'jubarte': None, 'soffice': None}) == 'unrecorded'
    with pytest.raises(RuntimeError, match='disagree on the scorer backend'):
        jri.one_backend({'jubarte': 'torch-mps', 'docxodus': 'numpy'})


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
    adopt = {'draw_sample': True}
    if mode == 'adopt':
        pool = jri.read_csv(root / jri.RUN_DIR / 'pool_pairs.csv')
        jri.write_csv(root / 'results/mine.csv', jri.GEN_FIELDS, [r for r in pool if r['key'] != 'wct0b'])
        lines = [f'corpus/word/{state}/docx/fx{s}{i}.docx'
                 for s, state in enumerate(jri.CONVERSION_QUOTAS) for i in range(6)]
        _put(root / 'results/convert.txt', ('\n'.join(lines) + '\n').encode())
        adopt = {'draw_sample': True, 'adopt_redline_csv': Path('results/mine.csv'),
                 'adopt_conversion_list': Path('results/convert.txt')}
    steps = _sample(root, regen, 24, binary=binary, engine_dir=engine, run=_answers, **adopt)
    made = _scored(root, steps, binary)  # the lane and the scores exist only after the sample
    stale = _put(engine / 'release_info' / f'sample_redline_{V}_01-01-26_00-00.csv')
    other = _put(engine / 'release_info' / 'sample_redline_0.11.2_01-01-26_00-00.csv')
    detail = _act(steps, 'release_info')
    folder = engine / 'release_info'
    six = _six(folder)
    assert len(six) == 6 and not stale.exists() and other.exists()
    assert f'six files of {V}' in detail and 'reports "jubarte 0.11.0"' in detail
    # the same six files, same names, same bytes, are filed in the bench's own
    # evidence folder: results/release_<v>_evidence/release_info/ (the copy the
    # report reads; the engine's release_info stays the release's own record)
    bench_copy = root / jri.evidence_dir(V) / 'release_info'
    bench_six = _six(bench_copy)
    assert set(bench_six) == set(six)
    for name, p in six.items():
        assert (bench_copy / p.name).read_bytes() == p.read_bytes()
    assert str(bench_copy) in detail
    assert _checker().problems(V, folder, 24) == []
    # each result names the backend its own score artifacts record
    assert json.loads(six['results_redline'].read_text())['versions']['scorer'] == 'torch-mps'
    assert json.loads(six['results_conversion'].read_text())['versions']['scorer'] == 'torch-cpu'

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
        assert jub['binary_sha256'] == made['binary_sha'] and jub['commit'] == COMMIT
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
    assert len(_six(bench_copy)) == 6
    for name, p in _six(folder).items():
        assert (bench_copy / p.name).read_bytes() == p.read_bytes()


def test_the_write_stage_needs_the_engine_checkout_and_the_sample_meta(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    binary = _put(tmp_path / 'jubarte')
    with pytest.raises(RuntimeError, match='needs --engine-dir'):
        _act(_plan(root, regen, binary=binary, run=_answers), 'release_info')
    # without the fixed sets the write names them; with them but no sets stage, the meta
    _write_sets(root)
    with pytest.raises(RuntimeError, match='the sets stage writes it'):
        _act(_plan(root, regen, binary=binary, engine_dir=tmp_path / 'engine', run=_answers), 'release_info')


# ------------------------------------------------------------------ the fixed sets (plan 7.3, #130)

SET_KEYS = ['wct0b', 'wct1', 'cle0', 'twc0', 'twc1']  # wct0b is its pair's second compare
CONV_STEMS = [('clean', 'fx00'), ('clean', 'fx01'), ('tracking_without_comments', 'fx10'),
              ('tracking_without_comments', 'fx11'), ('with_comments_clean', 'fx20'),
              ('with_comments_clean', 'fx21'), ('with_comments_tracking', 'fx30'),
              ('with_comments_tracking', 'fx31')]


def _write_sets(root: Path, redline: list[str] = SET_KEYS, convert: list[tuple[str, str]] = CONV_STEMS,
                *, folder: str = 'results/sets', set_version: str | None = None) -> None:
    """The two fixed-set CSVs + sets.json over the _tree corpus (paths and shas real)."""
    set_version = set_version if set_version is not None else fs.SET_VERSION
    pool = {r['key']: r for r in jri.read_csv(root / jri.RUN_DIR / 'pool_pairs.csv')}
    word = root / 'corpus/word'
    red = []
    for key in redline:
        r = pool[key]
        red.append({'key': key,
                    'base': f'corpus/word/{r["base"]}.docx', 'base_sha256': _sha(word / f'{r["base"]}.docx'),
                    'next': f'corpus/word/{r["next"]}.docx', 'next_sha256': _sha(word / f'{r["next"]}.docx'),
                    'docx': f'corpus/word/{r["docx"]}', 'docx_sha256': _sha(word / r['docx']),
                    'pdf': f'corpus/word/{r["pdf"]}', 'pdf_sha256': _sha(word / r['pdf']),
                    'state': r['state'], 'id': r['id'], 'sets': r['sets'], 'oracle': 'corpus',
                    'oracle_pdf': f'{jri.RUN_DIR}/oracle_pdf/{key}.pdf',
                    'oracle_pdf_sha256': _sha(root / jri.RUN_DIR / 'oracle_pdf' / f'{key}.pdf'),
                    'origin': fs.ORIGIN_SAMPLE, 'source': 'local'})
    conv = []
    for state, name in convert:
        conv.append({'state': state, 'stem': f'{state}__{name}',
                     'docx': f'corpus/word/{state}/docx/{name}.docx',
                     'docx_sha256': _sha(word / state / 'docx' / f'{name}.docx'),
                     'word_pdf': f'corpus/word/{state}/pdf/{name}.pdf',
                     'word_pdf_sha256': _sha(word / state / 'pdf' / f'{name}.pdf'),
                     'source': 'local', 'pages': '2', 'jubarte_score': '90.0'})
    jri.write_csv(root / Path(folder) / 'convert_860.csv', fs.CONVERT_HEADER, conv)
    jri.write_csv(root / Path(folder) / 'redline_600.csv', fs.REDLINE_SET_HEADER, red)
    (root / Path(folder) / 'sets.json').write_text(json.dumps(
        {'set_version': set_version, 'seed': fs.SEED,
         'counts': {'convert_860': jri.state_counts(conv), 'redline_600': jri.state_counts(red)},
         'totals': {'convert_860': len(conv), 'redline_600': len(red)},
         'origins': {fs.ORIGIN_SAMPLE: len(red)}, 'excluded': []}, indent=1) + '\n')


def _put_json(path: Path, doc: dict) -> Path:
    return _put(path, json.dumps(doc).encode())


def _scores_doc(vals: dict[str, float], backend: str = 'torch-mps') -> dict:
    return {'rows': {k: {'overall_score': v, 'overall_score_pagefair': v} for k, v in vals.items()},
            'summary': {'scorer_backend': backend}}


def _lanes(root: Path, *, redline: dict[str, dict] | None = None,
           convert: dict[str, dict] | None = None, run: Path | None = None) -> None:
    """The vendor-refresh results (#129): one measure-scores / docx-to-pdf report JSON
    per (tool, version), over the set's keys/stems."""
    run = run or root / jri.RUN_DIR
    for tool, versions in (redline or {}).items():
        for version, doc in versions.items():
            _put_json(run / f'scores_{tool}-{version}_set-redline_600.json', doc)
    for tool, versions in (convert or {}).items():
        for version, per in versions.items():
            _put_json(root / 'results' / f'docx_to_pdf_{tool}_{version}_set-convert_860.json',
                      {'scorer_backend': 'torch-cpu', 'tools': {tool: {'per_doc': per}}})


def test_the_sets_flags_default_to_the_committed_sets_and_override(tmp_path: Path) -> None:
    assert jri.DEFAULT_CONVERT_SET == Path('results/sets/convert_860.csv')
    assert jri.DEFAULT_REDLINE_SET == Path('results/sets/redline_600.csv')
    root, regen = _tree(tmp_path)
    # the defaults are read relative to the bench root; their absence is refused by name
    with pytest.raises(RuntimeError, match=r'no results/sets/convert_860\.csv'):
        _act(_plan(root, regen), 'validate the fixed sets')
    _write_sets(root, folder='results/mysets')
    steps = _plan(root, regen, convert_set=Path('results/mysets/convert_860.csv'),
                  redline_set=Path('results/mysets/redline_600.csv'))
    assert 'set version' in _act(steps, 'validate the fixed sets')
    # --draw-sample ignores the set flags; the two flows cannot be mixed
    out = CliRunner().invoke(jri.app, [V, '--root', str(root), '--plan', '--draw-sample',
                                       '--convert-set', 'results/mysets/convert_860.csv', '--only', 'sample'])
    assert out.exit_code != 0 and '--draw-sample' in out.output
    out = CliRunner().invoke(jri.app, [V, '--root', str(root), '--plan', '--adopt-redline', 'mine.csv'])
    assert out.exit_code != 0 and '--draw-sample' in out.output


def test_set_validation_refuses_any_drift(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    _write_sets(root)
    steps = _plan(root, regen)
    assert '5 compares' in _act(steps, 'validate the fixed sets') and '8 fixtures' in _act(steps, 'validate the fixed sets')
    # set_version drift: a changed set is a new set version, never an edit
    _write_sets(root, set_version='1999-01-01.0')
    with pytest.raises(RuntimeError, match=r'set_version is 1999-01-01\.0'):
        _act(steps, 'validate the fixed sets')
    _write_sets(root)
    # count drift: a row dropped behind sets.json's back
    rows = jri.read_csv(root / 'results/sets/redline_600.csv')
    jri.write_csv(root / 'results/sets/redline_600.csv', fs.REDLINE_SET_HEADER, rows[:-1])
    with pytest.raises(RuntimeError, match='redline_600.csv: counts by state drifted'):
        _act(steps, 'validate the fixed sets')
    # totals drift: sets.json claims another total than the CSVs hold
    jri.write_csv(root / 'results/sets/redline_600.csv', fs.REDLINE_SET_HEADER, rows)
    sets = json.loads((root / 'results/sets/sets.json').read_text())
    sets['totals']['convert_860'] = 7
    (root / 'results/sets/sets.json').write_text(json.dumps(sets))
    with pytest.raises(RuntimeError, match=r'convert_860 totals 7, convert_860\.csv holds 8 rows'):
        _act(steps, 'validate the fixed sets')
    sets['totals']['convert_860'] = 8
    (root / 'results/sets/sets.json').write_text(json.dumps(sets))
    # input sha drift: the corpus moved under the pinned set
    (root / 'corpus/word/clean/docx/wct0_base.docx').write_bytes(b'drifted')
    with pytest.raises(RuntimeError, match=r'hashes to .* but base_sha256 records'):
        _act(steps, 'validate the fixed sets')
    # an input missing on disk is drift too, named
    (root / 'corpus/word/clean/docx/wct0_base.docx').unlink()
    with pytest.raises(RuntimeError, match=r'corpus/word/clean/docx/wct0_base\.docx .*is missing'):
        _act(steps, 'validate the fixed sets')


def test_the_sets_stage_adopts_the_sets_into_the_release_evidence(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    _write_sets(root)
    steps = _plan(root, regen)
    detail = _act(steps, 'adopt the fixed sets')
    ev = root / jri.evidence_dir(V)
    sample = jri.read_csv(root / jri.redline_list(V))
    assert [r['key'] for r in sample] == SET_KEYS
    # the sample layout keeps the pool spelling measure.py and the generator expect
    assert list(sample[0]) == jri.GEN_SHA_FIELDS
    assert sample[0]['base'] == 'clean/docx/wct0_base' and sample[0]['docx'].endswith('.docx')
    assert sample[0]['base_sha256'] == _sha(root / 'corpus/word/clean/docx/wct0_base.docx')
    # the manifest redlines each pair once, under its FIRST key (measure.py's rule)
    manifest = [r['key'] for r in jri.read_csv(ev / 'gen_pairs_sample.csv')]
    assert 'wct0' in manifest and 'wct0b' not in manifest and len(manifest) == len(SET_KEYS)
    conv = jri.read_csv(root / jri.conversion_list(V))
    assert [r['stem'] for r in conv] == [f'{s}__{n}' for s, n in CONV_STEMS]
    assert list(conv[0]) == jri.CONVERSION_SHA_FIELDS
    meta = json.loads((ev / 'sample_meta.json').read_text())
    for kind in ('redline', 'conversion'):
        assert meta[kind]['set_version'] == fs.SET_VERSION and meta[kind]['date'] \
            and 'not drawn' in meta[kind]['rule']
    assert 'set version' in detail and 'not run' in detail


def test_the_sets_flow_runs_jubarte_only(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    _write_sets(root)
    steps = _plan(root, regen)
    # no other vendor's command anywhere in the plan: the comparator lanes are read, not run
    whole = ' '.join(' '.join(s.argv) for s in steps if s.argv) + ' ' + ' '.join(s.name for s in steps)
    for other in ('docxodus', 'soffice', 'superdoc'):
        assert other not in whole.lower()
    assert [s.name for s in steps if s.stage == 'sets'] == \
        ['bench inputs', 'validate the fixed sets', 'adopt the fixed sets']
    assert [s.name for s in steps if s.stage == 'generate'] == \
        ['generator dist', 'redline snapshot', 'jubarte redlines', 'stale Word PDFs aside']
    assert [s.name for s in steps if s.stage == 'export'] == \
        ['word answers', 'word export jubarte (batch)', 'word export jubarte (one osascript per document)']
    assert [s.name for s in steps if s.stage == 'measure'] == ['measure jubarte']
    assert [s.name for s in steps if s.stage == 'convert'] == \
        ['stale renders aside', 'convert jubarte (converts + scores)']
    assert not [s for s in steps if s.stage == 'score']  # the convert stage scores jubarte itself
    assert [s.name for s in steps if s.stage == 'write'] == ['release_info']


def test_the_newest_vendor_refresh_lane_wins_per_tool(tmp_path: Path) -> None:
    d = tmp_path / 'results'
    for name in ('docx_to_pdf_soffice_26.8.0.3_set-convert_860.json',
                 'docx_to_pdf_soffice_26.8.2.2_set-convert_860.json',
                 'docx_to_pdf_soffice_9.9.9_set-convert_860.json',
                 'docx_to_pdf_docxide_0.18.4_set-convert_860.json',
                 'docx_to_pdf_docxide_0.18.10_set-convert_860.json',
                 'docx_to_pdf_jubarte_0.17.0.json',                       # not a refresh lane
                 'docx_to_pdf_apryse_12.2.1_set-convert_v1.json'):         # another set
        _put(d / name)
    lanes = jri.newest_vendor_lanes(d, prefix='docx_to_pdf_', sep='_', set_name='convert_860')
    assert lanes == {'soffice': ('26.8.2.2', d / 'docx_to_pdf_soffice_26.8.2.2_set-convert_860.json'),
                     'docxide': ('0.18.10', d / 'docx_to_pdf_docxide_0.18.10_set-convert_860.json')}
    r = tmp_path / 'run'
    for name in ('scores_docxodus-12.6.5_set-redline_600.json',
                 'scores_docxodus-15.0.0_set-redline_600.json',
                 'scores_superdoc-2.28.0_set-redline_600.json',
                 'scores_jubarte-0.17.0.json',
                 'scores_broken_set-redline_600.json'):                    # no tool<sep>version
        _put(r / name)
    lanes = jri.newest_vendor_lanes(r, prefix='scores_', sep='-', set_name='redline_600')
    assert set(lanes) == {'docxodus', 'superdoc'}
    assert lanes['docxodus'][:1] == ('15.0.0',)
    assert not jri.newest_vendor_lanes(tmp_path / 'nowhere', prefix='scores_', sep='-',
                                       set_name='redline_600')


def test_a_comparator_that_never_ran_is_not_run_never_zero() -> None:
    rows = {'k1': {'overall_score': 50.0, 'overall_score_pagefair': 50.0},
            'k2': {'overall_score': 0.0, 'overall_score_pagefair': 0.0}}
    # a key the refresh lane never scored stays out of its aggregates: not run, never 0
    assert jri.refresh_scores(rows, ['k1', 'k2', 'k3']) == {'k1': 50.0, 'k2': 0.0}
    report = {'tools': {'docxide': {'per_doc': {'S1': 80.0}}}}
    assert jri.refresh_report_scores(report, 'docxide', ['s1', 's2']) == {'s1': 80.0}
    block = jri.not_run_block(['a', 'b', 'c'])
    assert block['status'] == 'not run' and block['n'] == 0 and block['not_run'] == 3
    assert block['median'] is None and block['mean'] is None and block['median_ci95'] is None
    assert block['by_state'] == {} and block['per_document'] == {}


def _scored_sets(root: Path, steps: list[Step], binary: Path) -> dict:
    """Jubarte's own artifacts after the sets stage: the lane, its measure scores,
    its conversion report — everything else comes from the vendor refresh lanes."""
    ev = root / jri.evidence_dir(V)
    sample = jri.read_csv(root / jri.redline_list(V))
    manifest = [r['key'] for r in jri.read_csv(ev / 'gen_pairs_sample.csv')]
    lane = root / jri.RUN_DIR / LANE
    for key in manifest:
        _put(lane / 'docx' / f'{key}_{LANE}.docx')
        if key != 'twc1':  # Word could not open this redline: no PDF, the compare scores 0
            _put(lane / 'pdf_by_word' / f'{key}_{LANE}.pdf')
    rows = {r['key']: 80.0 + i % 5 for i, r in enumerate(sample) if r['key'] != 'twc1'}
    _put_json(root / jri.scores_json(LANE, V), _scores_doc(rows))
    conv = jri.read_csv(root / jri.conversion_list(V))
    absent = conv[2]['stem']
    for i, r in enumerate(conv):
        if r['stem'] != absent:
            _put(ev / 'convert_work' / 'jubarte' / 'candidate' / f'{r["stem"]}.pdf')
    per = {r['stem']: 90.0 + i % 3 for i, r in enumerate(conv) if r['stem'] != absent}
    _put_json(root / jri.conversion_report('jubarte', V),
              {'scorer_backend': 'torch-cpu', 'tools': {'jubarte': {'version': f'jubarte {V}', 'per_doc': per}}})
    return {'sample': sample, 'conv': conv, 'absent': absent, 'binary_sha': _sha(binary)}


def test_sets_sample_then_write_reads_the_vendor_lanes(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    _write_sets(root)
    binary = _put(tmp_path / 'build' / 'jubarte-rc')
    engine = tmp_path / 'engine'
    steps = _plan(root, regen, binary=binary, engine_dir=engine, run=_answers)
    for name in ('validate the fixed sets', 'adopt the fixed sets'):
        _act(steps, name)
    made = _scored_sets(root, steps, binary)
    # the vendor refresh lanes (#129): docxodus newest of two, superdoc misses one pair,
    # apryse absent; conversions: soffice newest of two, docxide partial, the rest absent
    keys = [r['key'] for r in made['sample']]
    stems = [r['stem'] for r in made['conv']]
    dx = {k: 60.0 + i for i, k in enumerate(keys)}
    sup = {k: 55.0 for k in keys if k != 'cle0'}
    sof = {s: 70.0 + i % 3 for i, s in enumerate(stems)}
    did = {s: 65.0 for s in stems if s != stems[0]}
    _lanes(root, redline={'docxodus': {'12.6.5': _scores_doc({}), '15.0.0': _scores_doc(dx)},
                          'superdoc': {'2.28.0': _scores_doc(sup, backend='numpy')}},
           convert={'soffice': {'26.8.0.3': {}, '26.8.2.2': sof},
                    'docxide': {'0.18.4': did}})
    # the refresh lane carries its own version string and scorer backend (#129's real
    # files do): both are recorded, and a backend unlike this run's never refuses the write
    lane_doc = json.loads((root / 'results/docx_to_pdf_docxide_0.18.4_set-convert_860.json').read_text())
    lane_doc['tools']['docxide']['version'] = 'docxide-pdf 0.18.4'
    lane_doc['scorer_backend'] = 'numpy'
    _put_json(root / 'results/docx_to_pdf_docxide_0.18.4_set-convert_860.json', lane_doc)
    # the comparator files the sample names must be local (Codex on #174): absent,
    # the write refuses and says how to fetch them; present, every row names one
    with pytest.raises(RuntimeError, match=r'docxodus_pdf names 0 file\(s\), the refresh scored 5.*bench hub get'):
        _act(steps, 'release_info')
    for key in {r['key'] for r in jri.read_csv(root / jri.RUN_DIR / 'gen_pairs.csv')}:  # rows name first keys
        _put(root / jri.RUN_DIR / 'docxodus-15.0.0' / 'pdf_by_word' / f'{key}_docxodus-15.0.0_byword.pdf')
    with pytest.raises(RuntimeError, match=r'soffice_pdf names 0 file\(s\), the refresh scored'):
        _act(steps, 'release_info')
    for stem in stems:
        _put(root / 'results' / 'soffice_26.8.2.2_work' / 'candidate' / f'{stem}.pdf')
    detail = _act(steps, 'release_info')
    assert f'six files of {V}' in detail
    six = _six(engine / 'release_info')
    redline = json.loads(six['results_redline'].read_text())
    conversion = json.loads(six['results_conversion'].read_text())

    # set_version recorded in the release_info files and the evidence
    for doc, name in ((redline, 'redline_600'), (conversion, 'convert_860')):
        assert doc['sample']['set_version'] == fs.SET_VERSION and doc['sample']['set'] == name
    meta = json.loads((root / jri.evidence_dir(V) / 'sample_meta.json').read_text())
    assert meta['redline']['set_version'] == meta['conversion']['set_version'] == fs.SET_VERSION

    # jubarte scored ITT; the comparators read from the lanes, newest version per tool
    tools = redline['tools']
    assert set(tools) == {'jubarte', 'docxodus', 'superdoc', 'apryse'}
    assert tools['jubarte']['failures'] == 1 and tools['jubarte']['n'] == 5  # twc1 ITT 0
    assert tools['docxodus']['version'] == 'docxodus 15.0.0' and tools['docxodus']['n'] == 5
    assert 'not_run' not in tools['docxodus']
    assert tools['superdoc']['n'] == 4 and tools['superdoc']['not_run'] == 1  # cle0 not run, never 0
    assert tools['apryse']['status'] == 'not run' and tools['apryse']['not_run'] == 5
    assert tools['apryse']['median'] is None and tools['apryse']['mean'] is None
    assert redline['comparison']['comparator'] == 'docxodus'  # 5 pairs sit under the bootstrap's 20, so no ci95
    assert redline['provenance']['scores']['docxodus'] == \
        f'{jri.RUN_DIR}/scores_docxodus-15.0.0_set-redline_600.json'
    assert redline['versions']['scorer'] == 'torch-mps'

    ctools = conversion['tools']
    assert set(ctools) == {'jubarte', 'soffice', 'docxide', 'docxodus', 'apryse'}
    assert ctools['soffice']['version'] == 'soffice 26.8.2.2' and ctools['soffice']['n'] == 8
    assert ctools['docxide']['version'] == 'docxide-pdf 0.18.4'  # the lane's own string beats the file name
    assert ctools['docxide']['n'] == 7 and ctools['docxide']['not_run'] == 1
    assert ctools['docxide']['scorer'] == 'numpy' and tools['superdoc']['scorer'] == 'numpy'
    assert ctools['docxodus']['status'] == 'not run' and ctools['apryse']['status'] == 'not run'
    assert ctools['jubarte']['failures'] == 1  # the fixture left out scores 0, intent-to-treat
    assert conversion['versions']['libreoffice'] == 'soffice 26.8.2.2'
    assert conversion['provenance']['scores']['soffice'] == \
        'results/docx_to_pdf_soffice_26.8.2.2_set-convert_860.json'

    # the website tables: fixed-set titles, vendor rows, not-run notes
    site = [json.loads(line) for line in six['website_data'].read_text().splitlines()]
    by_key = {r['key']: r for r in site}
    tables = {t['id']: t for t in by_key['bench.tables']['value']}
    assert tables['conversion-sample']['title'] == "DOCX → PDF vs Word's own PDF — the 8-document set"
    assert tables['redlines-sample']['title'] == "Redlines vs Word's compare — the 5-pair set"
    for t in tables.values():
        assert f'set {fs.SET_VERSION}' in t['meta'] and 'sample' not in t['title']
    rows_c = {r['tool']: r for r in tables['conversion-sample']['rows']}
    assert rows_c['apryse']['median'] is None and 'not run' in rows_c['apryse']['note']
    assert rows_c['soffice']['pin'] == 'soffice 26.8.2.2'
    ranks = [r['rank'] for r in tables['redlines-sample']['rows']]
    assert ranks[-1] == '—' and '1' in ranks[0]  # the not-run row ranks last, unnumbered
    heads = by_key['bench.headlines']['value']
    assert 'docxodus 15.0.0' in heads[1]['vs'] and f'set {fs.SET_VERSION}' in heads[1]['sub']
    assert 'not run' in tables['redlines-sample']['desc']  # never 0, said in the wording
    method = {m['t']: m['d'] for m in by_key['bench.method']['value']}
    assert 'Fixed sets' in method and 'vendor refresh' in method['Fixed sets']
    generated = by_key['bench.generated']['value']
    assert generated == meta['redline']['date']  # the day the sets were adopted, not the write


def test_the_write_refuses_when_no_vendor_lane_exists(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    _write_sets(root)
    binary = _put(tmp_path / 'build' / 'jubarte-rc')
    steps = _plan(root, regen, binary=binary, engine_dir=tmp_path / 'engine', run=_answers)
    for name in ('validate the fixed sets', 'adopt the fixed sets'):
        _act(steps, name)
    _scored_sets(root, steps, binary)
    with pytest.raises(RuntimeError, match='vendor refresh'):
        _act(steps, 'release_info')


# ------------------------------------------------------------------ select, plan, execute

def test_only_and_skip_keep_the_order_and_run_the_preflights_first(tmp_path: Path) -> None:
    steps = jri.plan(_rel(tmp_path), conversion=[])
    names = [s.name for s in jri.select(steps, only=['sets', 'measure'])]
    assert names[0] == 'bench inputs'  # preflights first
    assert 'measure jubarte' in names and 'validate the fixed sets' in names
    assert 'release binary' not in names and 'release_info' not in names
    assert all(s.stage != 'export' for s in jri.select(steps, skip=['export', 'score']))
    with pytest.raises(ValueError, match='unknown stage'):
        jri.select(steps, only=['sets', 'word'])
    with pytest.raises(ValueError, match='unknown stage'):
        jri.select(steps, skip=['write'], only=['install', 'six'])
    # the draw flow's sample stage is still selectable under --draw-sample
    names = [s.name for s in jri.select(jri.plan(_rel(tmp_path), conversion=[], draw_sample=True),
                                        only=['sample', 'measure'])]
    assert names[0] == 'bench inputs' and 'draw redline sample' in names


def test_plan_flag_prints_and_runs_nothing(tmp_path: Path) -> None:
    out = CliRunner().invoke(jri.app, [V, '--root', str(tmp_path), '--plan', '--only', 'sets,measure', '--jobs', '7'])
    assert out.exit_code == 0, out.output
    lines = out.output.splitlines()
    assert lines[0] == 'sets      (bench inputs)'
    assert lines[1] == 'sets      (validate the fixed sets)'
    assert lines[2] == 'sets      (adopt the fixed sets)'
    assert lines[-1].startswith('measure   uv run python') and '--jobs 7' in lines[-1]
    assert not (tmp_path / 'results').exists()
    # --draw-sample keeps the old draw (and its soffice score stage) printable
    out = CliRunner().invoke(jri.app, [V, '--root', str(tmp_path), '--plan', '--draw-sample',
                                       '--only', 'sample,score', '--adopt-redline', 'mine.csv', '--jobs', '7'])
    assert out.exit_code == 0, out.output
    lines = out.output.splitlines()
    assert lines[0] == 'sample    (bench inputs)' and lines[1] == 'sample    (adopt redline sample)'
    assert lines[2] == 'sample    (draw conversion sample)'
    assert 'score     uv run bench docx-to-pdf --score-only --tool soffice --tool-version' in out.output
    assert '--jobs 7' in lines[-1]
    bad = CliRunner().invoke(jri.app, [V, '--plan', '--skip', 'word'])
    assert bad.exit_code != 0


def test_a_redline_stage_resumes_without_the_conversion_list(tmp_path: Path, monkeypatch) -> None:
    ran: list[str] = []

    def fake(steps, root, **_):
        ran.extend(s.name for s in steps)
        return [Outcome(s, True, 'ok') for s in steps]

    monkeypatch.setattr(jri, 'execute', fake)
    args = [V, '--root', str(tmp_path), '--binary', str(_put(tmp_path / 'jubarte-rc'))]
    draw = ['--draw-sample']
    for stage, step, extra in (('generate', 'jubarte redlines', draw),
                               ('export', 'word refusals docxodus', draw),
                               ('measure', 'measure jubarte', []),
                               ('sets', 'adopt the fixed sets', [])):
        out = CliRunner().invoke(jri.app, [*args, '--only', stage, *extra])
        assert out.exit_code == 0, out.output
        assert step in ran
    # converting reads the conversion list: without it the run stops and says why
    out = CliRunner().invoke(jri.app, [*args, '--only', 'convert'])
    assert out.exit_code == 1 and 'run the sets stage first' in out.output
    out = CliRunner().invoke(jri.app, [*args, '--only', 'convert', *draw])
    assert out.exit_code == 1 and 'run the sample stage first' in out.output


def test_the_sample_preflight_bootstraps_without_soffice_renders(tmp_path: Path) -> None:
    root, regen = _tree(tmp_path)
    for pdf in (root / jri.SOFFICE_WORK / 'candidate').iterdir():
        pdf.unlink()
    (root / jri.SOFFICE_WORK / 'candidate').rmdir()  # git-ignored: a clean checkout has none
    assert _act(_plan(root, regen), 'bench inputs').endswith('1 ids listed, each with its PDF')
    (regen / 'regen_list.csv').write_text('id\nidwct1\nidwct2\n')
    with pytest.raises(RuntimeError, match=r'idwct2.*scripts/fetch_corpus\.py'):
        _act(_plan(root, regen), 'bench inputs')  # #82: checked here, not after the Word export
    (regen / 'out' / 'idwct1__vs__idwct1.pdf').unlink()
    (regen / 'out').rmdir()
    with pytest.raises(RuntimeError, match='does not exist'):
        _act(_plan(root, regen), 'bench inputs')


def test_compare_regen_is_a_cli_option(tmp_path: Path) -> None:
    out = CliRunner().invoke(jri.app, [V, '--root', str(tmp_path), '--plan', '--only', 'measure',
                                       '--compare-regen', str(tmp_path / 'regen')])
    assert out.exit_code == 0, out.output
    assert f"--fresh {tmp_path / 'regen' / 'out'} --regen-list {tmp_path / 'regen' / 'regen_list.csv'}" in out.output


def test_the_plan_reads_the_fixtures_of_the_list_being_adopted_and_folds_them(tmp_path: Path) -> None:
    lines = [f'corpus/word/clean/docx/d{i}.docx' for i in range(5)]
    _put(tmp_path / 'convert.txt', '\n'.join(lines).encode())
    steps = jri.plan(_rel(tmp_path), draw_sample=True, adopt_conversion_list=Path('convert.txt'))
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
    assert scorers == ['measure jubarte', 'convert jubarte (converts + scores)']
    assert len(scorers) == len(set(scorers))
    steps = jri.plan(_rel(Path('/tmp/x')), conversion=['corpus/word/clean/docx/a.docx'], draw_sample=True)
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


def test_headline_comparator_median_has_two_decimals():
    """The site's check-bench reads the headline's comparator median as the
    page prints ours: two decimals. A raw 4-decimal median fails the site step."""
    def tool(version: str, median: float) -> dict:
        return {'version': version, 'median': median, 'mean': 50.0, 'n': 2, 'failures': 0,
                'exact_100': 0, 'at_least_90': 0, 'median_ci95': [1.0, 2.0],
                'by_state': {'clean': {'n': 2, 'median': median}}}
    redline = {'tools': {'jubarte': tool('jubarte 9.9.9', 83.1975),
                         'docxodus': tool('Docxodus 12.6.5 (C#)', 70.2666)},
               'sample': {'pairs': 2}, 'comparison': {'ci95': [0.461, 1.25]}}
    conversion = {'tools': {'jubarte': tool('jubarte 9.9.9', 81.0971),
                            'soffice': tool('LibreOffice 26.8.0.3', 47.8853)},
                  'versions': {'scorer': 's'}}
    recs = jri.website_records('9.9.9', 'g', redline, conversion, 'r', 'c')
    heads = next(r['value'] for r in recs if r['key'] == 'bench.headlines')
    assert [h['vs'] for h in heads] == ['LibreOffice 26.8.0.3 47.89', 'Docxodus 70.27']
    assert [h['value'] for h in heads] == ['81.10', '83.20']


def test_table_ranks_follow_the_medians_and_tie_when_the_paired_interval_holds_zero():
    def tool(version: str, median: float) -> dict:
        return {'version': version, 'median': median, 'mean': 50.0, 'n': 2, 'failures': 0,
                'exact_100': 0, 'at_least_90': 0, 'median_ci95': [1.0, 2.0],
                'by_state': {'clean': {'n': 2, 'median': median}}}
    # LibreOffice ahead on conversion, a tie on redlines: neither table may put jubarte first by name
    redline = {'tools': {'jubarte': tool('jubarte 9.9.9', 71.0), 'docxodus': tool('Docxodus 12.6.5 (C#)', 72.0)},
               'sample': {'pairs': 2}, 'comparison': {'ci95': [-1.5, 0.5]}}
    conversion = {'tools': {'jubarte': tool('jubarte 9.9.9', 50.0), 'soffice': tool('LibreOffice 26.8.0.3', 60.0)},
                  'versions': {'scorer': 's'}, 'comparison': {'ci95': [-12.0, -8.0]}}
    recs = jri.website_records('9.9.9', 'g', redline, conversion, 'r', 'c')
    tables = {t['id']: t['rows'] for t in next(r['value'] for r in recs if r['key'] == 'bench.tables')}
    assert [(r['rank'], r['tool']) for r in tables['conversion-sample']] == [('1', 'soffice'), ('2', 'jubarte †')]
    assert [(r['rank'], r['tool']) for r in tables['redlines-sample']] == [('1=', 'docxodus'), ('1=', 'jubarte-9.9.9 †')]


def test_write_six_files_the_bench_evidence_copy(tmp_path: Path, monkeypatch) -> None:
    # The write stage files the same six files, same names, same bytes, in the
    # bench's own evidence folder: results/release_<v>_evidence/release_info/
    # (the copy `bench report` reads for scores.json's sample tables).
    engine, bench = tmp_path / 'engine', tmp_path / 'bench'
    args = _six_args('2026-10-24', '2026-10-24')
    names = lambda folder: {p.name: p.read_bytes() for p in folder.iterdir() if '_9.9.9_' in p.name}  # noqa: E731

    detail = jri.write_six(engine, '9.9.9', bench_root=bench,
                           now=datetime(2026, 10, 25, 1, 20), **args)
    folder = engine / 'release_info'
    copy = bench / jri.evidence_dir('9.9.9') / 'release_info'
    six, six_copy = names(folder), names(copy)
    assert len(six) == len(six_copy) == 6
    assert set(six) == set(six_copy)
    for name, blob in six.items():
        assert six_copy[name] == blob
    assert str(copy) in detail
    # a re-write re-stamps both folders; each keeps one stamp of this version
    jri.write_six(engine, '9.9.9', bench_root=bench,
                  now=datetime(2026, 10, 26, 2, 0), **args)
    assert len(names(folder)) == 6 and len(names(copy)) == 6
    for name, blob in names(folder).items():
        assert names(copy)[name] == blob
    # a write that fails halfway (before any file moves) leaves both untouched
    before = dict(names(copy))

    def broken(version: str):
        raise OSError('No space left on device')

    monkeypatch.setattr(jri, 'app_records', broken)
    with pytest.raises(OSError, match='No space left'):
        jri.write_six(engine, '9.9.9', bench_root=bench,
                      now=datetime(2026, 10, 27, 3, 0), **args)
    assert names(copy) == before


def test_a_write_that_fails_halfway_keeps_the_previous_complete_set(tmp_path: Path, monkeypatch) -> None:
    def tool(version: str, median: float) -> dict:
        return {'version': version, 'median': median, 'mean': 50.0, 'n': 2, 'failures': 0,
                'exact_100': 0, 'at_least_90': 0, 'median_ci95': [1.0, 2.0],
                'by_state': {'clean': {'n': 2, 'median': median}}}
    redline = {'tools': {'jubarte': tool('jubarte 9.9.9', 71.0), 'docxodus': tool('Docxodus', 65.0)},
               'sample': {'pairs': 2}, 'comparison': {'ci95': [1.0, 9.0]}}
    conversion = {'tools': {'jubarte': tool('jubarte 9.9.9', 79.0), 'soffice': tool('LibreOffice', 55.0)},
                  'sample': {}, 'versions': {'scorer': 's'}, 'comparison': {'ci95': [1.0, 9.0]}}
    args = dict(redline=redline, conversion=conversion, redline_data=[['a']], conversion_data=[['b']])
    folder = tmp_path / 'release_info'
    jri.write_six(tmp_path, '9.9.9', now=datetime(2026, 10, 1, 9, 0), **args)
    before = {p.name: p.read_bytes() for p in folder.iterdir()}
    assert len(before) == 6

    def broken(version: str):
        raise OSError('No space left on device')

    monkeypatch.setattr(jri, 'app_records', broken)
    for now in (datetime(2026, 10, 2, 9, 0), datetime(2026, 10, 1, 9, 0)):  # a new stamp, then the same one
        with pytest.raises(OSError, match='No space left'):
            jri.write_six(tmp_path, '9.9.9', now=now, **args)
        assert {p.name: p.read_bytes() for p in folder.iterdir()} == before


def _six_args(redline_drawn: str | None, conversion_drawn: str | None) -> dict:
    def tool(version: str, median: float) -> dict:
        return {'version': version, 'median': median, 'mean': 50.0, 'n': 2, 'failures': 0,
                'exact_100': 0, 'at_least_90': 0, 'median_ci95': [1.0, 2.0],
                'by_state': {'clean': {'n': 2, 'median': median}}}

    def sample(date: str | None) -> dict:
        return {'pairs': 2, 'drawn': {'seed': 1, 'date': date}} if date else {'pairs': 2}

    redline = {'tools': {'jubarte': tool('jubarte 9.9.9', 71.0), 'docxodus': tool('Docxodus', 65.0)},
               'sample': sample(redline_drawn), 'comparison': {'ci95': [1.0, 9.0]}}
    conversion = {'tools': {'jubarte': tool('jubarte 9.9.9', 79.0), 'soffice': tool('LibreOffice', 55.0)},
                  'sample': sample(conversion_drawn), 'versions': {'scorer': 's'},
                  'comparison': {'ci95': [1.0, 9.0]}}
    return dict(redline=redline, conversion=conversion, redline_data=[['a']], conversion_data=[['b']])


def _website(folder: Path) -> list[dict]:
    (path,) = folder.glob('website_data_*.jsonl')
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_the_website_date_is_the_day_the_samples_were_drawn(tmp_path: Path) -> None:
    # 0.14.0 (#60): the samples were drawn on 10-24 and the six written after
    # midnight UTC; bench.generated said 10-25 and the site step refused it.
    jri.write_six(tmp_path, '9.9.9', now=datetime(2026, 10, 25, 1, 20), **_six_args('2026-10-24', '2026-10-24'))
    records = _website(tmp_path / 'release_info')
    generated = next(r['value'] for r in records if r['key'] == 'bench.generated')
    assert generated == '2026-10-24'
    # every date the page shows (meta, desc, source); ts is the write time, as facts.py stamps it
    text = json.dumps([{k: v for k, v in r.items() if k != 'ts'} for r in records], ensure_ascii=False)
    assert '2026-10-24' in text
    assert '2026-10-25' not in text


def test_samples_drawn_on_two_days_are_refused(tmp_path: Path) -> None:
    # The site holds bench.generated to both drawn dates: no single date fits.
    with pytest.raises(ValueError, match='redraw'):
        jri.write_six(tmp_path, '9.9.9', now=datetime(2026, 10, 25, 1, 20),
                      **_six_args('2026-10-24', '2026-10-25'))
    assert not (tmp_path / 'release_info').exists() or not list((tmp_path / 'release_info').glob('*_9.9.9_*'))


def test_one_drawn_date_is_the_website_date(tmp_path: Path) -> None:
    # The site holds bench.generated only to the samples that name a drawn
    # date; today's date would fail it whenever the flow crosses midnight.
    jri.write_six(tmp_path, '9.9.9', now=datetime(2026, 10, 25, 1, 20), **_six_args('2026-10-24', None))
    records = _website(tmp_path / 'release_info')
    assert next(r['value'] for r in records if r['key'] == 'bench.generated') == '2026-10-24'


def test_without_drawn_dates_the_website_date_is_the_write_time_s(tmp_path: Path) -> None:
    # Neither sample names a drawn date: the date is the write time's (UTC),
    # and a caller's now pins it, as it pins the stamp.
    jri.write_six(tmp_path, '9.9.9', now=datetime(2026, 1, 2, 12, 0), **_six_args(None, None))
    records = _website(tmp_path / 'release_info')
    assert next(r['value'] for r in records if r['key'] == 'bench.generated') == '2026-01-02'


def test_the_engine_commit_names_the_binary_s_build_not_the_checkout_s_head(tmp_path: Path) -> None:
    # 0.12.0: the write stage stamped the checkout's HEAD, which had moved past
    # the commit the scored candidate was built from. --engine-commit names it.
    seen: list[list[str]] = []

    def run(argv: list[str], **_: object) -> Proc:
        seen.append(argv)
        return Proc(stdout='c551f287' + '0' * 32 + '\n') if 'c551f287^{commit}' in argv[-1] or argv[-1] == 'HEAD^{commit}' \
            else Proc(returncode=128, stderr='fatal: Needed a single revision')

    assert jri.engine_commit(tmp_path, run, 'c551f287') == 'c551f287' + '0' * 32
    assert seen[-1] == ['git', '-C', str(tmp_path), 'rev-parse', '--verify', 'c551f287^{commit}']
    assert jri.engine_commit(tmp_path, run) == 'c551f287' + '0' * 32
    assert seen[-1][-1] == 'HEAD^{commit}'
    with pytest.raises(RuntimeError, match='nope'):
        jri.engine_commit(tmp_path, run, 'nope')
    assert jri.engine_commit(None, run, 'c551f287') is None


def test_report_tool_reads_the_docxide_lane_filed_as_docxide_pdf() -> None:
    """#169: `bench docx-to-pdf` files docxide's scores under `docxide-pdf`."""
    report = {'tools': {'docxide-pdf': {'per_doc': {'clean__A': 80.0}, 'version': 'docxide-pdf 0.18.4'}}}
    assert jri.refresh_report_scores(report, 'docxide', ['clean__a', 'clean__b']) == {'clean__a': 80.0}
    assert jri._report_tool(report, 'docxide')['version'] == 'docxide-pdf 0.18.4'


def test_report_tool_refuses_a_report_with_two_keys_for_one_vendor() -> None:
    """#169: a report naming docxide under both keys is ambiguous and refused."""
    report = {'tools': {'docxide': {'per_doc': {}}, 'docxide-pdf': {'per_doc': {}}}}
    with pytest.raises(RuntimeError, match='docxide'):
        jri._report_tool(report, 'docxide')


def test_report_tool_still_refuses_a_missing_vendor() -> None:
    """#169: the alias map does not make an absent vendor readable."""
    with pytest.raises(RuntimeError, match='not soffice'):
        jri._report_tool({'tools': {'docxide-pdf': {}}}, 'soffice')


def _ranked_tool(version: str, scores: dict[str, float], *, nested: bool) -> dict:
    """A tool block carrying its per-document scores, nested ``{'overall': x}`` as
    the redline results file them or bare floats as the conversion results do."""
    values = sorted(scores.values())
    median = values[len(values) // 2]
    return {'version': version, 'median': median, 'mean': median, 'n': len(scores), 'failures': 0,
            'exact_100': 0, 'at_least_90': 0, 'median_ci95': [1.0, 2.0],
            'by_state': {'clean': {'n': len(scores), 'median': median}},
            'per_document': {k: ({'overall': v} if nested else v) for k, v in scores.items()}}


def test_fixed_set_ranks_tie_only_adjacent_tools_whose_own_paired_interval_holds_zero():
    """#172: the jubarte-vs-docxodus interval held 0, and every redline row was
    ranked ``1=`` — superdoc and apryse, 20 and 35 points behind, included. Each
    adjacent pair ties only on its own paired interval over the documents both
    scored; a pair sharing fewer than MIN_PAIRED_DOCS documents never ties."""
    keys = [f'k{i:03d}' for i in range(60)]
    jub = {k: 80.0 + (i % 7) * 0.1 for i, k in enumerate(keys)}
    doc = {k: v + (0.05 if i % 2 else -0.05) for i, (k, v) in enumerate(jub.items())}  # a coin flip
    sup = {k: 60.0 + (i % 5) for i, k in enumerate(keys[:40])}                     # well behind
    apr = {k: 59.5 + (i % 5) for i, k in enumerate(keys[45:])}                     # shares 0 docs with superdoc
    redline = {'tools': {'jubarte': _ranked_tool('jubarte 9.9.9', jub, nested=True),
                         'docxodus': _ranked_tool('docxodus 15.0.0', doc, nested=True),
                         'superdoc': _ranked_tool('superdoc 2.25.0', sup, nested=True),
                         'apryse': _ranked_tool('apryse 12.2.1', apr, nested=True)},
               'sample': {'pairs': 60},
               'comparison': {'comparator': 'docxodus', 'ci95': [-0.1, 0.1]}}
    conv = {k: 70.0 + (i % 3) for i, k in enumerate(keys)}
    conversion = {'tools': {'jubarte': _ranked_tool('jubarte 9.9.9', conv, nested=False),
                            'soffice': _ranked_tool('LibreOffice 26.8.2.2', {k: v - 10 for k, v in conv.items()}, nested=False),
                            'docxide': _ranked_tool('docxide 0.18.4', {k: v - 10.01 for k, v in conv.items()}, nested=False),
                            'docxodus': _ranked_tool('docxodus 15.0.0', {k: v - 30 for k, v in conv.items()}, nested=False),
                            'apryse': _ranked_tool('apryse 12.2.1', {k: v - 5 for k, v in conv.items()}, nested=False)},
                  'versions': {'scorer': 's'},
                  'comparison': {'comparator': 'soffice', 'ci95': [9.0, 11.0]}}
    recs = jri.website_records('9.9.9', 'g', redline, conversion, 'r', 'c', set_version='2026-11-03.1')
    tables = {t['id']: t['rows'] for t in next(r['value'] for r in recs if r['key'] == 'bench.tables')}
    assert [(r['rank'], r['tool']) for r in tables['redlines-sample']] == [
        ('1=', 'jubarte-9.9.9 †'), ('1=', 'docxodus'), ('3', 'superdoc'), ('4', 'apryse')]
    # soffice and docxide differ by 0.01 on every document: a sure difference, not a tie
    assert [(r['rank'], r['tool']) for r in tables['conversion-sample']] == [
        ('1', 'jubarte †'), ('2', 'apryse'), ('3', 'soffice'), ('4', 'docxide'), ('5', 'docxodus')]
    assert not any(set(r) & {'scores', '_scores', 'key'} for t in tables.values() for r in t)


def _manifest(folder: Path, *lines: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'manifest.jsonl').write_text(''.join(json.dumps(line) + '\n' for line in lines))


def test_redline_rows_follow_word_trimmed_names_and_read_the_docxodus_refresh_lane(tmp_path: Path):
    """#172: the 0.17.0 sample named 5/600 jubarte docx and 0/600 jubarte PDFs.
    Word's driver renames a long docx in place (manifest ``renamed`` line) and
    exports ``<trimmed>_byword.pdf``; the row must follow the manifest. In the
    fixed-set flow the docxodus column comes from the refresh lane's folder."""
    root, lane, key = tmp_path, 'jubarte-9.9.9', 'a' * 70 + '__vs__' + 'b' * 70
    run = root / jri.RUN_DIR
    word = root / 'corpus/word'
    for name in ('base.docx', 'next.docx', 'cmp.docx', 'cmp.pdf'):
        (word / name).parent.mkdir(parents=True, exist_ok=True)
        (word / name).write_bytes(name.encode())
    (run / 'oracle_pdf').mkdir(parents=True)
    (run / 'oracle_pdf' / f'{key}.pdf').write_bytes(b'oracle')
    trimmed = 'a' * 27 + '_1234abcd'
    (run / lane / 'docx').mkdir(parents=True)
    (run / lane / 'docx' / f'{trimmed}.docx').write_bytes(b'jubarte docx')
    _manifest(run / lane / 'pdf_by_word',
              {'original_filename': f'{key}_{lane}.docx', 'converted_filename': f'{trimmed}.docx',
               'status': 'renamed', 'kind': 'rename'},
              {'original_filename': f'{trimmed}.docx', 'converted_filename': f'{trimmed}_byword.pdf',
               'path_out': f'{jri.RUN_DIR}/{lane}/pdf_by_word/{trimmed}_byword.pdf',  # bench-root relative
               'status': 'ok', 'kind': 'pdf'})
    (run / lane / 'pdf_by_word' / f'{trimmed}_byword.pdf').write_bytes(b'jubarte pdf')
    dx = run / 'docxodus-15.0.0' / 'pdf_by_word'
    dtrim = 'a' * 27 + '_9876fedc'
    _manifest(dx, {'original_filename': f'{key}_docxodus-15.0.0.docx', 'converted_filename': f'{dtrim}.docx',
                   'status': 'renamed', 'kind': 'rename'})
    (dx / f'{dtrim}_byword.pdf').write_bytes(b'docxodus pdf')
    sample = [{'key': key, 'base': 'base', 'next': 'next', 'docx': 'cmp.docx', 'pdf': 'cmp.pdf',
               'state': 'clean', 'id': 'x', 'sets': 's'}]
    gen = [{'key': key, 'base': 'base', 'next': 'next'}]
    row = jri.redline_rows(sample, root, lane, gen, tmp_path / 'fresh', with_docxodus=False, docxodus_dir=dx)[0]
    cols = dict(zip(jri.REDLINE_HEADER, row, strict=True))
    assert cols['jubarte_docx'] == f'{jri.RUN_DIR}/{lane}/docx/{trimmed}.docx'
    assert cols['jubarte_pdf'] == f'{jri.RUN_DIR}/{lane}/pdf_by_word/{trimmed}_byword.pdf'
    assert cols['docxodus_pdf'] == f'{jri.RUN_DIR}/docxodus-15.0.0/pdf_by_word/{dtrim}_byword.pdf'
    assert cols['jubarte_pdf_sha256'] == hashlib.sha256(b'jubarte pdf').hexdigest()
    # the drawn flow without a docxodus folder still leaves the column empty
    row = jri.redline_rows(sample, root, lane, gen, tmp_path / 'fresh', with_docxodus=False)[0]
    assert dict(zip(jri.REDLINE_HEADER, row, strict=True))['docxodus_pdf'] == ''


def test_conversion_rows_read_the_soffice_refresh_lane(tmp_path: Path):
    """#172: the fixed-set conversion sample left soffice_pdf empty on all 860 rows;
    the refresh lane's candidate folder fills it."""
    root = tmp_path
    for name in ('d.docx', 'w.pdf'):
        (root / name).write_bytes(name.encode())
    jub, sof = root / 'jub', root / 'results/soffice_26.8.2.2_work/candidate'
    jub.mkdir()
    sof.mkdir(parents=True)
    (jub / 'S1.pdf').write_bytes(b'j')
    (sof / 'S1.pdf').write_bytes(b's')
    sample = [{'state': 'clean', 'stem': 'S1', 'docx': 'd.docx', 'word_pdf': 'w.pdf'}]
    row = jri.conversion_rows(sample, root, jub, with_soffice=False, soffice_dir=sof)[0]
    cols = dict(zip(jri.CONVERSION_HEADER, row, strict=True))
    assert cols['soffice_pdf'] == 'results/soffice_26.8.2.2_work/candidate/S1.pdf'
    assert cols['jubarte_pdf'] == 'jub/S1.pdf'


def test_comparator_files_must_cover_what_the_refresh_scored():
    """Codex on #174: on a clean checkout the refresh lanes' PDFs are not local, and
    the comparator column would go blank again. The write refuses when the sample
    names fewer comparator files than the refresh scored, and says how to fetch them."""
    header = ['key', 'docxodus_pdf', 'docxodus_pdf_sha256']
    rows = [['a', 'x.pdf', 's'], ['b', '', ''], ['c', '', '']]
    jri.check_comparator_files(rows, header, 'docxodus_pdf', scored=1, fetch='F')  # 1 of 1: fine
    with pytest.raises(RuntimeError) as err:
        jri.check_comparator_files(rows, header, 'docxodus_pdf', scored=2,
                                   fetch='uv run bench hub get --path p --dest d')
    assert 'docxodus_pdf names 1 file(s), the refresh scored 2' in str(err.value)
    assert 'uv run bench hub get --path p --dest d' in str(err.value)
