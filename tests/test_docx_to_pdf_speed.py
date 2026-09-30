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


@pytest.mark.parametrize(
    ('tool', 'binary', 'stdout', 'stderr', 'expected', 'command'),
    [
        (
            'jubarte',
            '/tools/jubarte-abc123',
            'jubarte 1.2\nextra\n',
            '',
            'jubarte 1.2@abc123',
            ['/tools/jubarte-abc123', '--version'],
        ),
        (
            'jubarte',
            '/tools-with-dashes/jubarte',
            'jubarte 1.2\n',
            '',
            'jubarte 1.2',
            ['/tools-with-dashes/jubarte', '--version'],
        ),
        (
            'jubarte-compress',
            '/tools/jubarte',
            'jubarte 1.2\n',
            '',
            'jubarte 1.2 --compress',
            ['/tools/jubarte', '--version'],
        ),
        ('soffice', 'unused', '', 'LibreOffice 26.2\nextra', 'LibreOffice 26.2', ['soffice', '--version']),
        (
            'docxide',
            'unused',
            'other v1:\n    other\ndocxide-pdf v0.17.1:\n    docxide-pdf\n',
            '',
            'docxide-pdf v0.17.1',
            ['cargo', 'install', '--list'],
        ),
        ('docxide', 'unused', 'other v1:\n', '', 'docxide-pdf', ['cargo', 'install', '--list']),
    ],
)
def test_version_probe_parses_output_and_preserves_provenance(
    monkeypatch, tool, binary, stdout, stderr, expected, command
):
    import subprocess
    from unittest.mock import Mock

    probe = Mock(return_value=subprocess.CompletedProcess(command, 0, stdout, stderr))
    monkeypatch.setattr(speed.subprocess, 'run', probe)
    assert speed.version_of(tool, binary) == expected
    probe.assert_called_once_with(command, capture_output=True, text=True, timeout=speed.PROBE_TIMEOUT)


@pytest.mark.parametrize(
    ('limit', 'expected'), [(0, ['a.docx', 'z.docx']), (1, ['a.docx']), (9, ['a.docx', 'z.docx'])]
)
def test_corpus_limit_applies_after_sorting_and_excluding_lock_files(tmp_path: Path, limit, expected):
    corpus = tmp_path / 'docs=source'
    corpus.mkdir()
    for name in ('z.docx', '~$a.docx', 'a.docx', 'notes.txt'):
        (corpus / name).write_bytes(b'fixture')
    nested = corpus / 'nested'
    nested.mkdir()
    (nested / 'nested.docx').write_bytes(b'fixture')
    [(name, docs)] = speed.load_corpora([f'pool={corpus}'], limit)
    assert name == 'pool'
    assert [p.name for p in docs] == expected


def test_corpus_limit_keeps_the_list_file_order(tmp_path: Path):
    for n in ('b.docx', 'a.docx'):
        (tmp_path / n).write_bytes(b'x')
    listing = tmp_path / 'docs.txt'
    listing.write_text(f'{tmp_path / "b.docx"}\n{tmp_path / "a.docx"}\n')
    assert speed.load_corpora([f'mix=@{listing}'], 1) == [('mix', [tmp_path / 'b.docx'])]


@pytest.mark.parametrize('xs', [[0.0], [2.0, 1.0], list(range(21, 0, -1))])
def test_summary_percentile_boundaries_and_input_order(xs):
    before = xs.copy()
    (row,) = speed.summary_rows(['t'], [], {('t', 'all'): xs}, {}, {'t': 'v'}, 'ts', warm=False)
    expected_p95 = {1: 0.0, 2: 2.0, 21: 20.0}[len(xs)]
    assert row['p95'] == expected_p95
    assert row['n'] == len(xs)
    assert row['failed'] == 0
    assert xs == before


def test_summary_rows_are_sorted_rounded_and_keep_corpus_counts_separate():
    rows = speed.summary_rows(
        ['z', 'a'],
        ['second', 'first'],
        {('a', 'first'): [1.1111, 2.2222], ('a', 'all'): [1.1111, 2.2222, 6.6666]},
        {('a', 'first'): 2, ('a', 'all'): 3},
        {'a': 'a-v1', 'z': 'z-v1'},
        'run-id',
        warm=True,
    )
    assert [(r['tool'], r['corpus']) for r in rows] == [(t, c) for t in ('a', 'z') for c in ('all', 'first', 'second')]
    by = {(r['tool'], r['corpus']): r for r in rows}
    assert by['a', 'first']['mean'] == pytest.approx(1.667)
    assert by['a', 'first']['median'] == pytest.approx(1.667)
    assert by['a', 'first']['total_s'] == pytest.approx(0.003)
    assert by['a', 'first']['failed'] == 2
    assert by['a', 'all']['n'] == 3
    assert by['a', 'all']['failed'] == 3
    assert by['z', 'second']['n'] == 0
    assert all(by['z', 'second'][key] is None for key in ('total_s', 'mean', 'median', 'p95'))
    assert all(r['unit'] == 'ms_per_docx' and r['mode'] == 'warm' and r['run_ts'] == 'run-id' for r in rows)
    assert by['z', 'second']['version'] == 'z-v1'


@pytest.fixture
def worker_process(monkeypatch):
    """Fake only the process and readiness boundary; exercise the worker protocol."""
    from unittest.mock import Mock

    proc = Mock()
    proc.poll.return_value = None
    proc.stdout.readline.return_value = 'ok 12.5\n'
    popen = Mock(return_value=proc)
    selector = Mock()
    selector.select.return_value = [object()]
    monkeypatch.setattr(speed.subprocess, 'Popen', popen)
    monkeypatch.setattr(speed.selectors, 'DefaultSelector', Mock(return_value=selector))
    return proc, popen, selector


@pytest.mark.parametrize(
    ('reply', 'pdf', 'ok'),
    [
        ('ok 12.5\n', b'%PDF', True),
        ('ok 12.5\n', b'', False),
        ('ok 12.5\n', None, False),
        ('err 12.5 conversion failed\n', b'%PDF', False),
    ],
)
def test_worker_requires_success_reply_and_nonempty_pdf(tmp_path: Path, worker_process, reply, pdf, ok):
    import subprocess

    proc, popen, selector = worker_process
    proc.stdout.readline.return_value = reply
    src, dst = tmp_path / 'source with spaces.docx', tmp_path / 'out.pdf'
    if pdf is not None:
        dst.write_bytes(pdf)
    worker = speed.Worker('docxide', timeout=7)
    assert worker.convert(src, dst) == (12.5, ok)
    popen.assert_called_once_with(
        [str(speed.WARM_BIN / 'd2p-warm-docxide'), 'docxide'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    proc.stdin.write.assert_called_once_with(f'{src}\t{dst}\n')
    proc.stdin.flush.assert_called_once_with()
    selector.register.assert_called_once_with(proc.stdout, speed.selectors.EVENT_READ)
    selector.select.assert_called_once_with(7)
    selector.close.assert_called_once_with()
    proc.kill.assert_not_called()


@pytest.mark.parametrize('timeout', [True, False], ids=['timeout', 'eof'])
def test_worker_restarts_after_timeout_or_eof(tmp_path: Path, monkeypatch, worker_process, timeout):
    from unittest.mock import Mock

    proc, popen, selector = worker_process
    selector.select.return_value = [] if timeout else [object()]
    proc.stdout.readline.return_value = ''
    monkeypatch.setattr(speed.time, 'perf_counter', Mock(side_effect=[10, 10.25, 11]))
    worker = speed.Worker('rdocx', timeout=2)
    dst = tmp_path / 'out.pdf'
    assert worker.convert(tmp_path / 'a.docx', dst) == (250.0, False)
    proc.kill.assert_called_once_with()
    proc.wait.assert_called_once_with()
    assert worker.proc is None
    if timeout:
        proc.stdout.readline.assert_not_called()
    selector.select.return_value = [object()]
    proc.stdout.readline.return_value = 'ok 3.25\n'
    dst.write_bytes(b'%PDF')
    assert worker.convert(tmp_path / 'b.docx', dst) == (3.25, True)
    assert popen.call_count == 2


def test_worker_reuses_live_process_and_replaces_exited_process(tmp_path: Path, worker_process):
    proc, popen, _ = worker_process
    worker = speed.Worker('rdocx', timeout=2)
    dst = tmp_path / 'out.pdf'
    dst.write_bytes(b'%PDF')
    worker.convert(tmp_path / 'a.docx', dst)
    worker.convert(tmp_path / 'b.docx', dst)
    assert popen.call_count == 1
    proc.poll.return_value = 1
    worker.convert(tmp_path / 'c.docx', dst)
    assert popen.call_count == 2
    worker.close()
    proc.stdin.close.assert_called_once_with()
    proc.wait.assert_called_once_with()


def test_closing_unstarted_worker_does_not_spawn(worker_process):
    _, popen, _ = worker_process
    speed.Worker('rdocx', timeout=2).close()
    popen.assert_not_called()


@pytest.fixture
def benchmark_cli(tmp_path: Path, monkeypatch):
    """Small synthetic corpora; every external converter must be replaced by a test."""
    import sys
    from unittest.mock import Mock

    first, second = tmp_path / 'first', tmp_path / 'second'
    first.mkdir()
    second.mkdir()
    for path in (first / 'a.docx', first / 'b.docx', second / 'c.docx'):
        path.write_bytes(b'synthetic docx')
    out, work = tmp_path / 'results', tmp_path / 'work'
    work.mkdir()
    argv = [
        'docx_to_pdf_speed.py',
        '--jubarte',
        str(tmp_path / 'jubarte'),
        '--corpus',
        f'first={first}',
        '--corpus',
        f'second={second}',
        '--tools',
        'docxide,rdocx',
        '--timeout',
        '4',
        '--out',
        str(out),
    ]
    monkeypatch.setattr(sys, 'argv', argv)
    monkeypatch.setattr(speed, 'version_of', Mock(side_effect=lambda tool, _: f'{tool}-v1'))
    monkeypatch.setattr(speed.tempfile, 'mkdtemp', lambda **_: str(work))
    monkeypatch.setattr(speed, 'run_capped', Mock(side_effect=AssertionError('unexpected real converter')))
    monkeypatch.setattr(speed.subprocess, 'run', Mock(side_effect=AssertionError('unexpected real probe')))
    monkeypatch.setattr(speed.subprocess, 'Popen', Mock(side_effect=AssertionError('unexpected real worker')))
    return argv, out, work


def _jsonl(path: Path) -> list[dict]:
    import json

    return [json.loads(line) for line in path.read_text().splitlines()]


def test_cold_run_rotates_tools_excludes_warmup_and_appends_summaries(benchmark_cli, monkeypatch):
    _, out, work = benchmark_cli
    calls = []

    def convert(cmd, timeout):
        assert timeout == 4
        if cmd[0] == 'docxide-pdf':
            src, dst = Path(cmd[1]), Path(cmd[2])
            tool = 'docxide'
        else:
            assert cmd[:4] == ['rdocx', 'convert', '--to', 'pdf']
            assert cmd[4] == '-o'
            dst, src = Path(cmd[5]), Path(cmd[6])
            tool = 'rdocx'
        assert not dst.exists(), 'a previous PDF must not count as a new conversion'
        calls.append((tool, src.name))
        dst.write_bytes(b'%PDF')
        return 0, False

    monkeypatch.setattr(speed, 'run_capped', convert)
    out.mkdir()
    (out / 'speed.jsonl').write_text('{"prior": true}\n')
    speed.main()
    expected = [
        ('docxide', 'a.docx'),
        ('rdocx', 'a.docx'),
        ('rdocx', 'b.docx'),
        ('docxide', 'b.docx'),
        ('docxide', 'c.docx'),
        ('rdocx', 'c.docx'),
    ]
    assert calls == [('docxide', 'a.docx'), ('rdocx', 'a.docx'), *expected]
    [files] = out.glob('*/files.jsonl')
    rows = _jsonl(files)
    assert [(r['tool'], r['doc']) for r in rows] == expected
    assert all(r['ok'] and 'timeout' not in r for r in rows)
    summaries = _jsonl(out / 'speed.jsonl')
    assert summaries.pop(0) == {'prior': True}
    assert len(summaries) == 6
    assert {(r['tool'], r['corpus']): r['n'] for r in summaries} == {
        (t, c): n for t in ('docxide', 'rdocx') for c, n in [('first', 2), ('second', 1), ('all', 3)]
    }
    assert all(r['failed'] == 0 and r['mode'] == 'cold' for r in summaries)
    assert not work.exists()


@pytest.mark.parametrize('failure', ['timeout', 'nonzero', 'missing', 'empty'])
def test_failed_cold_conversions_never_contribute_timings(benchmark_cli, monkeypatch, failure):
    _, out, _ = benchmark_cli

    def convert(cmd, timeout):
        if failure == 'timeout':
            return -9, True
        dst = Path(cmd[2] if cmd[0] == 'docxide-pdf' else cmd[5])
        if failure in ('nonzero', 'empty'):
            dst.write_bytes(b'%PDF' if failure == 'nonzero' else b'')
        return (1 if failure == 'nonzero' else 0), False

    monkeypatch.setattr(speed, 'run_capped', convert)
    speed.main()
    [files] = out.glob('*/files.jsonl')
    per_call = _jsonl(files)
    assert len(per_call) == 6
    assert all(not row['ok'] for row in per_call)
    assert all(row.get('timeout', False) is (failure == 'timeout') for row in per_call)
    rows = _jsonl(out / 'speed.jsonl')
    assert len(rows) == 6
    for row in rows:
        assert row['n'] == 0
        assert row['failed'] == {'first': 2, 'second': 1, 'all': 3}[row['corpus']]
        assert all(row[key] is None for key in ('total_s', 'mean', 'median', 'p95'))


def test_warm_run_uses_worker_timings_skips_soffice_and_closes_workers(benchmark_cli, monkeypatch):
    from unittest.mock import Mock

    argv, out, work = benchmark_cli
    argv[argv.index('--tools') + 1] = 'docxide,soffice,rdocx'
    argv.append('--warm')
    workers = {tool: Mock() for tool in ('docxide', 'rdocx')}
    workers['docxide'].convert.return_value = (7.25, True)
    workers['rdocx'].convert.return_value = (900.0, False)
    factory = Mock(side_effect=lambda tool, timeout: workers[tool])
    monkeypatch.setattr(speed, 'Worker', factory)
    speed.main()
    assert [call.args for call in factory.call_args_list] == [('docxide', 4), ('rdocx', 4)]
    for worker in workers.values():
        assert worker.convert.call_count == 4  # one warmup plus three samples
        worker.close.assert_called_once_with()
    rows = _jsonl(out / 'speed.jsonl')
    assert len(rows) == 6
    assert all(row['mode'] == 'warm' for row in rows)
    pooled = {row['tool']: row for row in rows if row['corpus'] == 'all'}
    assert pooled['docxide']['mean'] == pytest.approx(7.25)
    assert pooled['docxide']['n'] == 3
    assert pooled['rdocx']['n'] == 0
    assert pooled['rdocx']['failed'] == 3
    assert pooled['rdocx']['mean'] is None
    assert not work.exists()


def test_stale_jubarte_worker_is_rejected_before_probing_or_writing(benchmark_cli, tmp_path: Path, monkeypatch):
    import os

    argv, out, _ = benchmark_cli
    argv[argv.index('--tools') + 1] = 'jubarte'
    argv.append('--warm')
    binary = Path(argv[argv.index('--jubarte') + 1])
    binary.write_bytes(b'CLI')
    worker = tmp_path / 'd2p-warm-jubarte'
    worker.write_bytes(b'worker')
    os.utime(worker, (100, 100))
    os.utime(binary, (200, 200))
    monkeypatch.setattr(speed, 'WARM_BIN', tmp_path)
    with pytest.raises(SystemExit, match=r'predates .*rebuild'):
        speed.main()
    speed.version_of.assert_not_called()
    speed.subprocess.Popen.assert_not_called()
    assert not out.exists()


def test_empty_corpus_fails_before_probes_workers_or_output(benchmark_cli, tmp_path: Path):
    argv, out, _ = benchmark_cli
    argv.extend(['--corpus', f'absent={tmp_path / "absent"}', '--warm'])
    with pytest.raises(SystemExit, match='empty corpus'):
        speed.main()
    speed.version_of.assert_not_called()
    speed.subprocess.Popen.assert_not_called()
    assert not out.exists()


@pytest.mark.parametrize('tool', ['jubarte', 'jubarte-compress', 'office2pdf', 'soffice'])
def test_cold_converter_arguments_and_output_locations(benchmark_cli, monkeypatch, tool):
    argv, out, work = benchmark_cli
    argv[argv.index('--tools') + 1] = tool
    binary = argv[argv.index('--jubarte') + 1]
    sources = []

    def convert(cmd, timeout):
        dst = work / f'{tool}.pdf'
        assert not dst.exists()
        if tool.startswith('jubarte'):
            src = Path(cmd[2])
            jub = [binary, 'convert', str(src), '-o', str(dst), '--force', '--revisions', 'word']
            assert cmd == (jub if tool == 'jubarte' else [*jub, '--compress'])
        elif tool == 'office2pdf':
            src = Path(cmd[3])
            assert cmd == ['office2pdf', '-o', str(dst), str(src)]
        else:
            src = Path(cmd[-1])
            assert cmd == [
                'soffice',
                f'-env:UserInstallation=file://{work / "lo_profile"}',
                '--headless',
                '--convert-to',
                'pdf',
                '--outdir',
                str(work / 'lo'),
                str(src),
            ]
            (work / 'lo').mkdir(exist_ok=True)
            dst = work / 'lo' / f'{src.stem}.pdf'
            assert not dst.exists(), 'LibreOffice output must be moved after each conversion'
        sources.append(src.name)
        dst.write_bytes(b'%PDF')
        return 0, False

    monkeypatch.setattr(speed, 'run_capped', convert)
    speed.main()
    assert sources == ['a.docx', 'a.docx', 'b.docx', 'c.docx']
    rows = _jsonl(out / 'speed.jsonl')
    assert len(rows) == 3
    assert all(row['tool'] == tool and row['failed'] == 0 for row in rows)
    assert next(row for row in rows if row['corpus'] == 'all')['n'] == 3
