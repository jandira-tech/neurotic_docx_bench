"""The release gate and the release itself (PyPI + GitHub).

A release is refused unless, on this machine:

1. Microsoft Word answers ``osascript`` with a version;
2. that Word renders a corpus DOCX to PDF (not merely installed: it opens and exports);
3. ``results/bench.jsonl`` holds rows rendered with exactly that Word version
   (``renderer_id == "word-<version>"``) and none rendered with another Word version;
4. ``bench report --check`` reports the published pages current;
5. the git tree is clean;
6. tag ``v<version>`` does not exist yet;
7. ``CHANGELOG.md`` has a ``## [<version>]`` section (it becomes the release notes).

Only then: ``git tag``, ``uv build``, ``uv publish``, ``git push origin <tag>``,
``gh release create``. The version is the one in ``pyproject.toml``.

Every subprocess goes through ``run`` and Word rendering through ``convert`` so the
gate is testable without Word, network or git side effects. In the cloud VM this
gate fails at step 1 by design.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import typer

PACKAGE = "neurotic-docx-bench"
WORD_VERSION_CMD = 'osascript -e version of application "Microsoft Word"'
_WORD_VERSION_ARGV = ["osascript", "-e", 'version of application "Microsoft Word"']
SMOKE_DOCX = Path("corpus/word_based/docx_source/24_id_paraid_overflow.docx")
BUILD_DIR = Path("build/release")
CHECK_NAMES = (
    "word installed",
    "word renders",
    "word rows current",
    "pages current",
    "tree clean",
    "tag free",
    "changelog entry",
)


class ProcLike(Protocol):
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[..., ProcLike]


@dataclass(frozen=True)
class RenderOutcome:
    ok: bool
    pdf: Path | None
    error: str | None


Convert = Callable[..., RenderOutcome]


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


def default_runner() -> Runner:
    def run(
        cmd: list[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, cwd=cwd, check=False
            )
        except FileNotFoundError as exc:
            return subprocess.CompletedProcess(
                cmd, 127, "", f"{cmd[0]}: not found ({exc})"
            )

    return run


def default_convert() -> Convert:
    from neurotic_docx_bench.render import word

    def convert(docx: Path, out_dir: Path, **kw: Any) -> RenderOutcome:
        r = word.convert_one(docx, out_dir, force=True, **kw)
        return RenderOutcome(ok=r.ok, pdf=r.pdf, error=r.error)

    return convert


def _python() -> str:
    return sys.executable


# --- pure pieces -----------------------------------------------------------


def source_version(root: Path) -> str:
    data = tomllib.loads((Path(root) / "pyproject.toml").read_text())
    return str(data["project"]["version"])


def changelog_section(path: Path, version: str) -> str | None:
    """The body of ``## [version]`` (or ``## version``) up to the next ``## `` heading."""
    if not Path(path).exists():
        return None
    text = Path(path).read_text()
    heading = re.compile(rf"^## \[?{re.escape(version)}\]?(?:\s|$)", re.MULTILINE)
    m = heading.search(text)
    if m is None:
        return None
    rest = text[m.end() :]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    body = rest[: nxt.start()] if nxt else rest
    body = body.strip()
    return body or None


def word_version(run: Runner) -> str | None:
    proc = run(list(_WORD_VERSION_ARGV))
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None


def word_rows_check(store: Path, version: str) -> Check:
    """Rows in the store rendered with Word: all must carry this Word version, and at least one must."""
    name = "word rows current"
    store = Path(store)
    if not store.exists():
        return Check(name, False, f"no store at {store}")
    want = f"word-{version}"
    current = 0
    stale: list[str] = []
    for line in store.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        rid = row.get("renderer_id")
        if not isinstance(rid, str) or not rid.startswith("word-"):
            continue
        if rid == want:
            current += 1
        else:
            stale.append(f"{row.get('id_run')} ({rid})")
    if stale:
        return Check(
            name,
            False,
            f"{len(stale)} rows rendered with another Word than {want}: "
            + ", ".join(stale),
        )
    if current == 0:
        return Check(
            name,
            False,
            f"no row in {store} rendered with {want}; re-render the headline groups with this Word first",
        )
    return Check(
        name, True, f"{current} row{'s' if current != 1 else ''} rendered with {want}"
    )


# --- the gate --------------------------------------------------------------


def _word_renders(root: Path, convert: Convert) -> Check:
    docx = Path(root) / SMOKE_DOCX
    if not docx.exists():
        return Check("word renders", False, f"smoke document missing: {docx}")
    with tempfile.TemporaryDirectory(prefix="bench-release-word.") as work:
        outcome = convert(docx, Path(work))
        if (
            not outcome.ok
            or outcome.pdf is None
            or not outcome.pdf.exists()
            or outcome.pdf.stat().st_size == 0
        ):
            return Check(
                "word renders",
                False,
                f"Word failed to export {docx.name}: {outcome.error or 'no PDF'}",
            )
        size = outcome.pdf.stat().st_size
    return Check("word renders", True, f"{docx.name} exported ({size} bytes)")


def preflight(root: Path, *, run: Runner, convert: Convert) -> list[Check]:
    root = Path(root)
    version = source_version(root)
    checks: list[Check] = []

    wv = word_version(run)
    if wv is None:
        checks.append(
            Check(
                "word installed",
                False,
                "Microsoft Word did not answer osascript; releases need Word on this machine",
            )
        )
        checks.append(Check("word renders", False, "skipped: no Word"))
        checks.append(
            Check(
                "word rows current",
                False,
                "skipped: no Word version to compare against",
            )
        )
    else:
        checks.append(Check("word installed", True, f"Microsoft Word {wv}"))
        checks.append(_word_renders(root, convert))
        checks.append(word_rows_check(root / "results" / "bench.jsonl", wv))

    proc = run(
        [_python(), "-m", "neurotic_docx_bench.cli", "report", "--check"], cwd=root
    )
    if proc.returncode == 0:
        checks.append(
            Check(
                "pages current",
                True,
                "RESULTS.md, RESULTS_DETAILED.md and README are current",
            )
        )
    else:
        checks.append(
            Check(
                "pages current",
                False,
                (proc.stdout + proc.stderr).strip() or f"exit {proc.returncode}",
            )
        )

    proc = run(["git", "status", "--porcelain"], cwd=root)
    dirty = (proc.stdout or "").strip()
    if proc.returncode != 0:
        checks.append(
            Check("tree clean", False, (proc.stderr or "git status failed").strip())
        )
    elif dirty:
        checks.append(
            Check(
                "tree clean",
                False,
                "uncommitted changes: " + "; ".join(dirty.splitlines()),
            )
        )
    else:
        checks.append(Check("tree clean", True, "no uncommitted changes"))

    tag = f"v{version}"
    proc = run(["git", "tag", "-l", tag], cwd=root)
    if (proc.stdout or "").strip():
        checks.append(Check("tag free", False, f"tag {tag} already exists"))
    else:
        checks.append(Check("tag free", True, f"tag {tag} is free"))

    notes = changelog_section(root / "CHANGELOG.md", version)
    if notes is None:
        checks.append(
            Check(
                "changelog entry",
                False,
                f"CHANGELOG.md has no '## [{version}]' section",
            )
        )
    else:
        checks.append(
            Check(
                "changelog entry",
                True,
                f"CHANGELOG.md [{version}]: {len(notes.splitlines())} lines",
            )
        )
    return checks


# --- publishing ------------------------------------------------------------


def _step(run: Runner, name: str, cmd: list[str], cwd: Path) -> Check:
    proc = run(cmd, cwd=cwd)
    if proc.returncode == 0:
        return Check(name, True, " ".join(cmd))
    return Check(
        name,
        False,
        f"{' '.join(cmd)}: {(proc.stderr or proc.stdout or f'exit {proc.returncode}').strip()}",
    )


def publish(root: Path, *, run: Runner) -> list[Check]:
    """Tag, build, publish to PyPI, push the tag, create the GitHub release. Stops at the first failure."""
    root = Path(root)
    version = source_version(root)
    tag = f"v{version}"
    title = f"{PACKAGE} {version}"
    out = root / BUILD_DIR
    steps: list[Check] = []

    steps.append(_step(run, "tag", ["git", "tag", "-a", tag, "-m", title], root))
    if not steps[-1].ok:
        return steps
    steps.append(_step(run, "build", ["uv", "build", "--out-dir", str(out)], root))
    if not steps[-1].ok:
        return steps
    stem = PACKAGE.replace("-", "_")
    artifacts = sorted(
        p for p in out.glob(f"{stem}-{version}*") if p.suffix in {".whl", ".gz"}
    )
    if not artifacts:
        steps.append(
            Check("build", False, f"no {stem}-{version}* artifacts under {out}")
        )
        return steps
    steps.append(_step(run, "publish", ["uv", "publish", *map(str, artifacts)], root))
    if not steps[-1].ok:
        return steps
    steps.append(_step(run, "push tag", ["git", "push", "origin", tag], root))
    if not steps[-1].ok:
        return steps
    notes = changelog_section(root / "CHANGELOG.md", version) or title
    notes_file = out / f"notes-{version}.md"
    notes_file.write_text(notes + "\n")
    steps.append(
        _step(
            run,
            "github release",
            [
                "gh",
                "release",
                "create",
                tag,
                *map(str, artifacts),
                "--title",
                title,
                "--notes-file",
                str(notes_file),
            ],
            root,
        )
    )
    return steps


# --- CLI -------------------------------------------------------------------

app = typer.Typer(name="release", add_completion=False, help=__doc__)


@app.callback(invoke_without_command=True)
def main(
    root: Path = typer.Option(Path("."), "--root", help="repository root"),
    check: bool = typer.Option(
        False, "--check", help="run the gate and stop; publish nothing"
    ),
) -> None:
    """Run the release gate; on success tag, build, publish to PyPI and create the GitHub release."""
    run = default_runner()
    convert = default_convert()
    version = source_version(root)
    checks = preflight(root, run=run, convert=convert)
    failed = [c for c in checks if not c.ok]
    for c in checks:
        mark = "ok  " if c.ok else "FAIL"
        typer.echo(f"{mark} {c.name}: {c.detail}")
    if failed:
        typer.echo(
            f"gate failed ({len(failed)} of {len(checks)}); {PACKAGE} {version} not released"
        )
        raise typer.Exit(code=1)
    typer.echo(f"gate passed; {PACKAGE} {version}")
    if check:
        return
    steps = publish(root, run=run)
    for s in steps:
        typer.echo(f"{'ok  ' if s.ok else 'FAIL'} {s.name}: {s.detail}")
    if not all(s.ok for s in steps):
        typer.echo(f"release stopped at '{steps[-1].name}'")
        raise typer.Exit(code=1)
    typer.echo(f"released {PACKAGE} {version}")


if __name__ == "__main__":
    app()
