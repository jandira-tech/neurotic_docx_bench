"""docx_to_pdf_speed: the jubarte --compress variant and file-list corpora."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    'docx_to_pdf_speed', Path(__file__).resolve().parent.parent / 'scripts' / 'docx_to_pdf_speed.py'
)
speed = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(speed)


def test_jubarte_compress_is_the_jubarte_call_plus_compress():
    src, dst, lo = Path('a.docx'), Path('a.pdf'), Path('lo')
    plain = speed.tool_cmd('jubarte', src, dst, jubarte='bin/jubarte', profile=lo, lo_dir=lo)
    packed = speed.tool_cmd('jubarte-compress', src, dst, jubarte='bin/jubarte', profile=lo, lo_dir=lo)
    assert plain == ['bin/jubarte', 'convert', 'a.docx', '-o', 'a.pdf', '--force', '--revisions', 'word']
    assert packed == [*plain, '--compress']


def test_corpus_from_a_list_file_keeps_its_order_and_skips_blanks(tmp_path: Path):
    for n in ('b.docx', 'a.docx'):
        (tmp_path / n).write_bytes(b'x')
    listing = tmp_path / 'docs.txt'
    listing.write_text(f'{tmp_path / "b.docx"}\n\n{tmp_path / "a.docx"}\n')
    name, docs = speed.load_corpus(f'mix=@{listing}')
    assert name == 'mix'
    assert docs == [tmp_path / 'b.docx', tmp_path / 'a.docx']


def test_corpus_from_a_list_file_refuses_a_missing_path(tmp_path: Path):
    listing = tmp_path / 'docs.txt'
    listing.write_text(f'{tmp_path / "gone.docx"}\n')
    with pytest.raises(SystemExit):
        speed.load_corpus(f'mix=@{listing}')


def test_corpus_from_a_directory_is_sorted_without_lock_files(tmp_path: Path):
    for n in ('b.docx', 'a.docx', '~$a.docx', 'c.txt'):
        (tmp_path / n).write_bytes(b'x')
    assert speed.load_corpus(f'd={tmp_path}') == ('d', [tmp_path / 'a.docx', tmp_path / 'b.docx'])


def _count(cmdline: str) -> int:
    import subprocess

    out = subprocess.run(['ps', '-Ao', 'command'], capture_output=True, text=True).stdout
    return sum(line.strip() == cmdline for line in out.splitlines())


def test_run_capped_kills_the_whole_process_group_on_timeout():
    before = _count('sleep 3602')
    rc, timed_out = speed.run_capped(['sh', '-c', 'sleep 3602 & sleep 3602'], timeout=0.5)
    assert timed_out and rc != 0
    import time

    time.sleep(0.3)
    assert _count('sleep 3602') == before


def test_run_capped_returns_the_exit_code():
    assert speed.run_capped(['sh', '-c', 'exit 3'], timeout=5) == (3, False)


def test_a_hung_version_probe_does_not_stop_the_run(monkeypatch):
    import subprocess

    def hang(cmd, **kw):
        assert kw.get('timeout'), 'every probe needs a timeout'
        raise subprocess.TimeoutExpired(cmd, kw['timeout'])

    monkeypatch.setattr(speed.subprocess, 'run', hang)
    assert speed.version_of('rdocx', 'jubarte') == 'rdocx (version probe timed out)'
    assert speed.version_of('docxide', 'jubarte') == 'docxide (version probe timed out)'


def test_a_silent_version_probe_names_the_tool(monkeypatch):
    import subprocess

    monkeypatch.setattr(speed.subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, '', ''))
    assert speed.version_of('office2pdf', 'jubarte') == 'office2pdf'


def test_an_empty_corpus_stops_before_any_conversion(tmp_path: Path):
    full, empty = tmp_path / 'full', tmp_path / 'empty'
    full.mkdir()
    empty.mkdir()
    (full / 'a.docx').write_bytes(b'x')
    (empty / '~$lock.docx').write_bytes(b'x')
    with pytest.raises(SystemExit, match='empty'):
        speed.load_corpora([f'full={full}', f'empty={empty}'], 0)
    assert [(n, [p.name for p in docs]) for n, docs in speed.load_corpora([f'full={full}'], 0)] == [
        ('full', ['a.docx'])
    ]


def test_a_tool_without_one_success_still_gets_a_row():
    samples = {('jubarte', 'c'): [3.0, 1.0, 2.0], ('jubarte', 'all'): [3.0, 1.0, 2.0]}
    failed = {('rdocx', 'c'): 3, ('rdocx', 'all'): 3}
    rows = speed.summary_rows(
        ['jubarte', 'rdocx'], ['c'], samples, failed, {'jubarte': 'j', 'rdocx': 'r'}, 'ts', warm=False
    )
    by = {(r['tool'], r['corpus']): r for r in rows}
    assert set(by) == {('jubarte', 'c'), ('jubarte', 'all'), ('rdocx', 'c'), ('rdocx', 'all')}
    assert (by['rdocx', 'c']['n'], by['rdocx', 'c']['failed']) == (0, 3)
    assert all(by['rdocx', 'c'][k] is None for k in ('total_s', 'mean', 'median', 'p95'))
    assert by['jubarte', 'c']['median'] == pytest.approx(2.0)
    assert by['jubarte', 'c']['total_s'] == pytest.approx(0.006)


def test_p95_is_the_nearest_rank_sample():
    xs = [float(i) for i in range(1, 21)]
    (row,) = speed.summary_rows(['t'], [], {('t', 'all'): xs}, {}, {'t': 'v'}, 'ts', warm=True)
    # ceil(0.95 * 20) - 1 = 18 -> the 19th sample, not the maximum.
    assert row['p95'] == pytest.approx(19.0)
    assert row['mode'] == 'warm'
