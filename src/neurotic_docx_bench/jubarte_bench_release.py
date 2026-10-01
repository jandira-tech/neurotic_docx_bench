"""Score a jubarte release on the bench and open the pull request that publishes it.

    scripts/release_jubarte.py 0.10.2 --plan                 # print every command, run nothing
    scripts/release_jubarte.py 0.10.2                        # every stage, in order
    scripts/release_jubarte.py 0.10.2 --only convert,metrics,report
    scripts/release_jubarte.py 0.10.2 --skip redlines        # no Word today

Stages, in order (``--only`` / ``--skip`` pick among them, the order never changes):

1. ``install``: the release's own binary for this machine, the GitHub asset checked against
   the release's ``SHA256SUMS.txt`` (``jubarte_release.github_download``). Never a local build:
   the bench scores what users download.
2. ``convert``: ``bench docx-to-pdf`` on all of ``corpus/word`` with that binary (the bench
   passes ``--revisions word --compress`` itself); appends to ``results/converters.jsonl``.
3. ``metrics``: ``bench docxide-metrics`` over the same PDFs (same work folder).
4. ``redlines`` (Microsoft Word, hours): a new lane ``jubarte-<version>`` in
   ``results/redlines_0929_full``. The release redlines ``gen_pairs.csv``; Word exports each
   redline to PDF (``scripts/word_pdf.py --do-not-close`` in batch mode, then one osascript per
   document for what the batch dropped) with ``word_watchdog.sh`` following the export log;
   ``measure.py`` scores the PDFs against the run's oracles (the fresh compares in
   ``compare_regen``); the lane joins ``versions.json``; ``to_scores_jsonl.py`` rewrites
   ``scores.jsonl``; ``hub_upload.py`` uploads the lane's files. A redline Word cannot open
   has no PDF and scores 0; that is a result, so the export passes may fail.
5. ``report``: ``bench report``, then ``bench report --check``.
6. ``publish``: branch ``bench/jubarte-<version>``, commit the stores, scores and pages, push,
   open the pull request. Nothing is merged.

Every subprocess goes through ``run`` and the watchdog through ``spawn`` so the plan and the
executor are tested without Word, network or git.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import typer

from neurotic_docx_bench import jubarte_release, release

STAGES = ('install', 'convert', 'metrics', 'redlines', 'report', 'publish')
RUN_DIR = Path('results/redlines_0929_full')
COMPARE_REGEN = Path.home() / 'temp/T/compare_regen'
WATCHDOG = Path.home() / 'T/jubarte-loop/word_watchdog.sh'
_VERSION = re.compile(r'^\d+\.\d+\.\d+$')


@dataclass(frozen=True)
class Step:
    """One command (``argv``) or one Python action (``action``, returns a detail line)."""

    stage: str
    name: str
    argv: tuple[str, ...] = ()
    action: Callable[[], str] | None = None
    log: Path | None = None
    # Paths word_watchdog.sh follows while this step runs (the ones the step grows).
    watch: tuple[Path, ...] = ()
    # A failed step stops the release unless it may fail (a Word export pass may).
    may_fail: bool = False
    # Runs before every other selected step: a check that would otherwise fail hours in.
    preflight: bool = False

    def shown(self) -> str:
        if self.action is not None:
            return f'({self.name})'
        line = ' '.join(self.argv)
        return f'{line} > {self.log}' if self.log else line


@dataclass(frozen=True)
class Outcome:
    step: Step
    ok: bool
    detail: str


class Proc(Protocol):
    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


Run = Callable[[Step, Path], int]
Spawn = Callable[[Sequence[str], Path], Proc]


@dataclass(frozen=True)
class Release:
    """Where one release's files go, from the bench root."""

    version: str
    root: Path
    cache: Path = field(default_factory=jubarte_release.default_cache)

    def __post_init__(self) -> None:
        if not _VERSION.match(self.version):
            raise ValueError(f'not a release version: {self.version!r} (want x.y.z)')

    @property
    def lane(self) -> str:
        return f'jubarte-{self.version}'

    @property
    def binary(self) -> Path:
        """Where ``github_download`` puts this machine's binary."""
        folder = jubarte_release.asset_name(self.version).removesuffix('.tar.gz').removesuffix('.zip')
        return self.cache / self.version / folder / jubarte_release.BIN

    @property
    def work(self) -> Path:
        return Path(f'results/jubarte_{self.version}_docx_to_pdf_work')

    @property
    def convert_json(self) -> Path:
        return Path(f'results/docx_to_pdf_jubarte_{self.version}.json')

    @property
    def metrics_json(self) -> Path:
        return Path(f'results/docxide_metrics_jubarte_{self.version}.json')

    @property
    def branch(self) -> str:
        return f'bench/jubarte-{self.version}'

    def committed(self) -> list[Path]:
        """The files the publish commit carries (relative to the root), those that exist."""
        r = RUN_DIR
        paths = [
            Path('results/converters.jsonl'),
            self.convert_json,
            self.metrics_json,
            r / 'scores.jsonl',
            r / 'versions.json',
            r / f'scores_{self.lane}.json',
            Path('RESULTS.md'),
            Path('RESULTS_DETAILED.md'),
            Path('README.md'),
        ]
        return [p for p in paths if (self.root / p).is_file()]


def add_version(path: Path, lane: str, label: str) -> str:
    """Put ``lane`` in ``versions.json`` (kept in its order, appended when new)."""
    versions = json.loads(path.read_text()) if path.is_file() else {}
    versions[lane] = label
    path.write_text(json.dumps(versions, indent=2) + '\n')
    return f'{path}: {lane} = {label}'


def plan(rel: Release, *, run: Callable[..., release.ProcLike] | None = None, hub: bool = True) -> list[Step]:
    """Every step of every stage, in order. ``run`` answers the Word check (``release.word_version``)."""
    r, lane, v = RUN_DIR, rel.lane, rel.version
    bench = ('uv', 'run', 'bench')
    word_pdf = (
        'uv',
        'run',
        '--script',
        'scripts/word_pdf.py',
        '--src',
        str(r / lane / 'docx'),
        '--out',
        str(r / lane / 'pdf_by_word'),
        '--do-not-close',
    )
    batch_log, retry_log = r / f'{lane}.word_pdf.log', r / f'{lane}.word_pdf.retry.log'

    def install() -> str:
        exe = jubarte_release.github_download(v, rel.cache, jubarte_release.http_get)
        if exe is None:
            raise RuntimeError(f'release v{v} has no {jubarte_release.asset_name(v)} (or no SHA256SUMS.txt)')
        got = jubarte_release.binary_version(exe)
        if got != v:
            raise RuntimeError(f'{exe} says it is {got}, not {v}')
        return f'{exe} ({got}, sha256 checked)'

    def word() -> str:
        found = release.word_version(run or release.default_runner())
        if not found:
            raise RuntimeError('Microsoft Word does not answer osascript; the redline stage needs it')
        return f'Microsoft Word {found}'

    steps = [
        Step('install', 'release binary', action=install),
        Step(
            'convert',
            'docx-to-pdf',
            (
                *bench,
                'docx-to-pdf',
                '--converter',
                str(rel.binary),
                '--origin',
                'all',
                '--work-dir',
                str(rel.work),
                '--json',
                str(rel.convert_json),
            ),
            log=Path(f'results/jubarte_{v}_docx_to_pdf.log'),
        ),
        Step(
            'metrics',
            'docxide-metrics',
            (
                *bench,
                'docxide-metrics',
                '--tool',
                'jubarte',
                '--converter',
                str(rel.binary),
                '--origin',
                'all',
                '--work-dir',
                str(rel.work),
                '--json',
                str(rel.metrics_json),
            ),
            log=Path(f'results/docxide_metrics_jubarte_{v}.log'),
        ),
        Step('redlines', 'word answers', action=word, preflight=True),
        Step(
            'redlines',
            'generate',
            (
                'node',
                '--import',
                'tsx',
                'scripts/generate-native-redlines.ts',
                '--method',
                'jubarte-rust',
                '--dist',
                str(rel.binary.parent),
                '--tool',
                lane,
                '--manifest',
                str(r / 'gen_pairs.csv'),
                '--source-dir',
                'corpus/word',
                '--out',
                str(r / lane / 'docx'),
                '--run-dir',
                str(r / lane),
            ),
            log=r / f'{lane}.generate.log',
        ),
        Step(
            'redlines',
            'word export (batch)',
            (*word_pdf, '--log', str(batch_log)),
            log=r / f'{lane}.word_pdf.out',
            watch=(batch_log,),
            may_fail=True,
        ),
        Step(
            'redlines',
            'word export (one osascript per document)',
            (*word_pdf, '--no-one-osascript', '--log', str(retry_log)),
            log=r / f'{lane}.word_pdf.retry.out',
            watch=(retry_log, r / lane / 'pdf_by_word'),
            may_fail=True,
        ),
        Step(
            'redlines',
            'measure',
            (
                'uv',
                'run',
                'python',
                str(r / 'measure.py'),
                '--fresh',
                str(COMPARE_REGEN / 'out'),
                '--regen-list',
                str(COMPARE_REGEN / 'regen_list.csv'),
                '--device',
                'mps',
                lane,
            ),
            log=r / f'measure_{lane}.log',
        ),
        Step(
            'redlines',
            'versions.json',
            action=lambda: add_version(rel.root / r / 'versions.json', lane, f'jubarte {v} (release)'),
        ),
        Step('redlines', 'scores.jsonl', ('uv', 'run', 'python', str(r / 'to_scores_jsonl.py'))),
    ]
    if hub:
        steps.append(
            Step(
                'redlines',
                'hub upload',
                ('uv', 'run', 'python', str(r / 'hub_upload.py')),
                log=r / f'hub_upload_{lane}.log',
            )
        )
    steps += [
        Step('report', 'report', (*bench, 'report')),
        Step('report', 'report current', (*bench, 'report', '--check')),
        Step('publish', 'branch', ('git', 'switch', '-c', rel.branch)),
        Step('publish', 'stage', action=lambda: _git_add(rel, run)),
        Step('publish', 'commit', ('git', 'commit', '-m', f'Results: jubarte {v} on the bench')),
        Step('publish', 'push', ('git', 'push', '-u', 'origin', rel.branch)),
        Step(
            'publish',
            'pull request',
            ('gh', 'pr', 'create', '--title', f'Results: jubarte {v}', '--body', _pr_body(rel)),
        ),
    ]
    return steps


def _git_add(rel: Release, run: Callable[..., release.ProcLike] | None) -> str:
    files = [str(p) for p in rel.committed()]
    if not files:
        raise RuntimeError('nothing to commit: no store, score or page file exists')
    proc = (run or release.default_runner())(['git', 'add', '--', *files], cwd=rel.root)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f'git add exit {proc.returncode}')
    return f'staged {len(files)}: {", ".join(files)}'


def _pr_body(rel: Release) -> str:
    return (
        f'jubarte {rel.version}, the GitHub release binary (sha256 checked), scored by '
        '`scripts/release_jubarte.py`:\n\n'
        f'- DOCX to PDF on all of corpus/word: `{rel.convert_json}`, `{rel.metrics_json}`\n'
        f'- redlines vs Word: lane `{rel.lane}` in `{RUN_DIR}` (`scores_{rel.lane}.json`)\n'
        '- RESULTS.md and RESULTS_DETAILED.md from `bench report`\n\n'
        'jubarte.pro copies these figures by hand: update `site/data/bench.ts`, then run '
        f'`scripts/release.sh bench {rel.version} --redline-tool {rel.lane}` in jubarte-site.'
    )


def select(steps: Sequence[Step], only: Sequence[str] = (), skip: Sequence[str] = ()) -> list[Step]:
    unknown = sorted((set(only) | set(skip)) - set(STAGES))
    if unknown:
        raise ValueError(f'unknown stage(s) {unknown}; stages are {", ".join(STAGES)}')
    chosen = [s for s in steps if (not only or s.stage in only) and s.stage not in skip]
    return [s for s in chosen if s.preflight] + [s for s in chosen if not s.preflight]


def default_run(step: Step, root: Path) -> int:
    if step.log is None:
        return subprocess.run(step.argv, cwd=root, check=False).returncode
    log = root / step.log
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open('a') as fh:
        return subprocess.run(step.argv, cwd=root, stdout=fh, stderr=subprocess.STDOUT, check=False).returncode


class ProcessGroup:
    """A process started as the leader of its own group; stopping it stops what it started.

    word_watchdog.sh waits in a ``sleep`` child: a signal to the shell alone leaves that
    child behind.
    """

    def __init__(self, popen: subprocess.Popen[bytes]) -> None:
        self.popen = popen
        self.pid = popen.pid

    def _signal(self, sig: int) -> None:
        try:
            os.killpg(self.pid, sig)
        except ProcessLookupError:  # the whole group already exited
            pass

    def terminate(self) -> None:
        self._signal(signal.SIGTERM)

    def kill(self) -> None:
        self._signal(signal.SIGKILL)

    def wait(self, timeout: float | None = None) -> int:
        return self.popen.wait(timeout)


def default_spawn(argv: Sequence[str], root: Path) -> ProcessGroup:
    return ProcessGroup(
        subprocess.Popen(
            list(argv), cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
    )


def stop(dog: Proc) -> None:
    """Stop a watchdog without letting a slow exit replace its step's result."""
    dog.terminate()
    try:
        dog.wait(timeout=10)
    except subprocess.TimeoutExpired:
        dog.kill()
        dog.wait()


def execute(
    steps: Sequence[Step],
    root: Path,
    *,
    run: Run = default_run,
    spawn: Spawn = default_spawn,
    echo: Callable[[str], None] = print,
) -> list[Outcome]:
    """Run ``steps`` in order; stop at the first failure of a step that may not fail."""
    done: list[Outcome] = []
    for step in steps:
        echo(f'== {step.stage}: {step.name}')
        if step.action is not None:
            try:
                out = Outcome(step, True, step.action())
            except Exception as exc:  # an action's failure is reported, never raised past the run
                out = Outcome(step, False, str(exc))
        else:
            dog = spawn(['zsh', str(WATCHDOG), *(str(root / p) for p in step.watch)], root) if step.watch else None
            try:
                code = run(step, root)
            finally:
                if dog is not None:
                    stop(dog)
            out = Outcome(step, code == 0, step.shown() if code == 0 else f'{step.shown()}: exit {code}')
        done.append(out)
        echo(f'   {"ok" if out.ok else "may fail" if step.may_fail else "FAIL"}: {out.detail}')
        if not out.ok and not step.may_fail:
            break
    return done


app = typer.Typer(name='release-jubarte', add_completion=False, help=__doc__)


def _stages(value: str) -> list[str]:
    return [s.strip() for s in value.split(',') if s.strip()]


@app.command()
def main(
    version: str = typer.Argument(..., help='the jubarte release, x.y.z'),
    root: Path = typer.Option(Path('.'), '--root', help='bench repository root'),
    only: str = typer.Option('', '--only', help=f'comma list of stages to run ({", ".join(STAGES)})'),
    skip: str = typer.Option('', '--skip', help='comma list of stages to leave out'),
    hub: bool = typer.Option(True, '--hub/--no-hub', help='upload the redline lane to the results dataset'),
    show_plan: bool = typer.Option(False, '--plan', help='print the steps and run nothing'),
) -> None:
    try:
        rel = Release(version, root.resolve())
        steps = select(plan(rel, hub=hub), _stages(only), _stages(skip))
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    if show_plan:
        for s in steps:
            typer.echo(f'{s.stage:9} {s.shown()}' + ('   [watchdog]' if s.watch else ''))
        return
    done = execute(steps, rel.root, echo=typer.echo)
    if len(done) < len(steps) or not all(o.ok or o.step.may_fail for o in done):
        typer.echo(f'stopped at {done[-1].step.stage}: {done[-1].step.name}')
        raise typer.Exit(code=1)
    typer.echo(f'jubarte {version}: {", ".join(dict.fromkeys(s.stage for s in steps))} done')
