"""The jubarte release run: which commands each stage runs, in which order, and when it stops.

Commands go through an injected runner and the watchdog through an injected spawner, so
nothing here needs Word, the network or git.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import jubarte_bench_release as jbr
from neurotic_docx_bench import release


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

    def wait(self, timeout: float | None = None) -> int:
        return 0


@dataclass
class Recorder:
    """Runs steps by answering exit codes by step name; records the order and the watchdogs."""

    codes: dict[str, int] = field(default_factory=dict)
    ran: list[str] = field(default_factory=list)
    dogs: list[Dog] = field(default_factory=list)

    def run(self, step: jbr.Step, root: Path) -> int:
        # The watchdog runs exactly while its step does.
        assert all(d.stopped for d in self.dogs[:-1])
        if step.watch:
            assert self.dogs and not self.dogs[-1].stopped
        self.ran.append(step.name)
        return self.codes.get(step.name, 0)

    def spawn(self, argv, root: Path) -> Dog:
        self.dogs.append(Dog(list(argv)))
        return self.dogs[-1]


def _rel(tmp_path: Path, version: str = '0.10.2') -> jbr.Release:
    return jbr.Release(version, tmp_path, cache=tmp_path / 'cache')


def _cmd(steps: list[jbr.Step], name: str) -> list[str]:
    return list(next(s for s in steps if s.name == name).argv)


def test_rejects_a_version_that_is_not_a_release(tmp_path: Path) -> None:
    for bad in ('0.10', 'v0.10.2', 'latest', '0.10.2-rc1'):
        with pytest.raises(ValueError, match='not a release version'):
            jbr.Release(bad, tmp_path)


def test_every_stage_scores_the_downloaded_release_binary(tmp_path: Path) -> None:
    rel = _rel(tmp_path)
    steps = jbr.plan(rel)
    assert [s.stage for s in steps] == sorted((s.stage for s in steps), key=jbr.STAGES.index)
    binary = str(rel.binary)
    assert binary.startswith(str(tmp_path / 'cache' / '0.10.2' / 'jubarte-0.10.2-'))
    convert = _cmd(steps, 'docx-to-pdf')
    assert convert[convert.index('--converter') + 1] == binary
    assert convert[convert.index('--origin') + 1] == 'all'
    metrics = _cmd(steps, 'docxide-metrics')
    assert metrics[metrics.index('--converter') + 1] == binary
    # docxide-metrics reads the PDFs docx-to-pdf wrote.
    assert metrics[metrics.index('--work-dir') + 1] == convert[convert.index('--work-dir') + 1]
    generate = _cmd(steps, 'generate')
    assert generate[generate.index('--dist') + 1] == str(rel.binary.parent)
    assert generate[generate.index('--tool') + 1] == 'jubarte-0.10.2'
    assert generate[generate.index('--method') + 1] == 'jubarte-rust'


def test_word_exports_run_under_the_watchdog_and_may_fail(tmp_path: Path) -> None:
    steps = jbr.plan(_rel(tmp_path))
    batch, single = (s for s in steps if s.name.startswith('word export'))
    for s in (batch, single):
        assert '--do-not-close' in s.argv
        assert s.may_fail
        # The watchdog follows the log the export grows, never an unrelated folder.
        log = Path(s.argv[s.argv.index('--log') + 1])
        assert log in s.watch
    assert '--no-one-osascript' not in batch.argv
    assert '--no-one-osascript' in single.argv
    measure = _cmd(steps, 'measure')
    assert measure[-1] == 'jubarte-0.10.2'
    assert '--fresh' in measure and '--regen-list' in measure


def test_only_and_skip_keep_the_order_and_run_the_word_check_first(tmp_path: Path) -> None:
    steps = jbr.plan(_rel(tmp_path))
    names = [s.name for s in jbr.select(steps, only=['convert', 'redlines'])]
    assert names[0] == 'word answers'
    assert names[1] == 'docx-to-pdf'
    assert 'release binary' not in names and 'report' not in names
    skipped = jbr.select(steps, skip=['redlines'])
    assert all(s.stage != 'redlines' for s in skipped)
    assert skipped[0].name == 'release binary'
    with pytest.raises(ValueError, match='unknown stage'):
        jbr.select(steps, only=['convert', 'word'])


def test_no_hub_leaves_out_the_upload(tmp_path: Path) -> None:
    assert 'hub upload' in [s.name for s in jbr.plan(_rel(tmp_path))]
    assert 'hub upload' not in [s.name for s in jbr.plan(_rel(tmp_path), hub=False)]


def test_word_check_fails_without_word(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def no_word(cmd, **_):
        calls.append(cmd)
        return Proc(1, '', 'execution error')

    steps = jbr.select(jbr.plan(_rel(tmp_path), run=no_word), only=['redlines'])
    rec = Recorder()
    done = jbr.execute(steps, tmp_path, run=rec.run, spawn=rec.spawn, echo=lambda _: None)
    assert len(done) == 1 and not done[0].ok
    assert 'Microsoft Word does not answer' in done[0].detail
    assert rec.ran == []
    assert calls and calls[0][0] == 'osascript'


def test_a_failed_export_pass_does_not_stop_the_run_but_a_failed_measure_does(tmp_path: Path) -> None:
    word = {release.WORD_VERSION_CMD: Proc(0, '16.101.1\n')}

    def run(cmd, **_):
        return word.get(' '.join(cmd), Proc())

    steps = jbr.select(jbr.plan(_rel(tmp_path), run=run, hub=False), only=['redlines'])
    rec = Recorder(codes={'word export (batch)': 1, 'measure': 2})
    done = jbr.execute(steps, tmp_path, run=rec.run, spawn=rec.spawn, echo=lambda _: None)
    assert rec.ran == ['generate', 'word export (batch)', 'word export (one osascript per document)', 'measure']
    assert done[-1].step.name == 'measure' and not done[-1].ok and 'exit 2' in done[-1].detail
    # One watchdog per export pass, each stopped when its pass ended.
    assert len(rec.dogs) == 2 and all(d.stopped for d in rec.dogs)
    assert rec.dogs[0].argv[:2] == ['zsh', str(jbr.WATCHDOG)]
    assert rec.dogs[0].argv[2].endswith('jubarte-0.10.2.word_pdf.log')
    # versions.json is not touched when measure failed.
    assert not (tmp_path / jbr.RUN_DIR / 'versions.json').exists()


def test_versions_json_gains_the_lane_and_keeps_the_others(tmp_path: Path) -> None:
    path = tmp_path / 'versions.json'
    path.write_text(json.dumps({'jubarte-rust': 'jubarte 0.10.0 (86b6b5d3)', 'docxodus': 'Docxodus 12.6.5 (C#)'}))
    jbr.add_version(path, 'jubarte-0.10.2', 'jubarte 0.10.2 (release)')
    jbr.add_version(path, 'jubarte-0.10.2', 'jubarte 0.10.2 (release)')
    assert json.loads(path.read_text()) == {
        'jubarte-rust': 'jubarte 0.10.0 (86b6b5d3)',
        'docxodus': 'Docxodus 12.6.5 (C#)',
        'jubarte-0.10.2': 'jubarte 0.10.2 (release)',
    }


def test_publish_commits_only_the_files_that_exist(tmp_path: Path) -> None:
    rel = _rel(tmp_path)
    for p in ('results/converters.jsonl', 'results/docx_to_pdf_jubarte_0.10.2.json', 'RESULTS.md'):
        (tmp_path / p).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / p).write_text('x')
    added: list[list[str]] = []

    def run(cmd, **_):
        added.append(cmd)
        return Proc()

    stage = next(s for s in jbr.plan(rel, run=run) if s.name == 'stage')
    assert stage.action is not None
    assert stage.action().startswith('staged 3')
    assert added == [
        ['git', 'add', '--', 'results/converters.jsonl', 'results/docx_to_pdf_jubarte_0.10.2.json', 'RESULTS.md']
    ]
    names = [s.name for s in jbr.plan(rel) if s.stage == 'publish']
    assert names == ['branch', 'stage', 'commit', 'push', 'pull request']
    branch = _cmd(jbr.plan(rel), 'branch')
    assert branch == ['git', 'switch', '-c', 'bench/jubarte-0.10.2']


def test_plan_flag_prints_and_runs_nothing(tmp_path: Path) -> None:
    out = CliRunner().invoke(jbr.app, ['0.10.2', '--root', str(tmp_path), '--plan', '--only', 'convert,report'])
    assert out.exit_code == 0, out.output
    lines = out.output.splitlines()
    assert lines[0].startswith('convert   uv run bench docx-to-pdf')
    assert lines[-1] == 'report    uv run bench report --check'
    bad = CliRunner().invoke(jbr.app, ['0.10.2', '--plan', '--skip', 'word'])
    assert bad.exit_code != 0
