"""The release gate: Word on this machine, headline rows rendered with it, current
pages, clean tree, changelog entry; only then tag, build, publish, GitHub release.

Every subprocess goes through an injected runner, so the gate is exercised on a
machine without Word, without network and without git side effects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from typer.testing import CliRunner

from neurotic_docx_bench import release

runner = CliRunner()


@dataclass
class Proc:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


@dataclass
class FakeRunner:
    """Answers commands by prefix; records every call in order."""

    answers: dict[str, Proc] = field(default_factory=dict)
    calls: list[list[str]] = field(default_factory=list)

    def __call__(self, cmd: list[str], *, cwd: Path | None = None) -> Proc:
        self.calls.append(list(cmd))
        joined = " ".join(cmd)
        for prefix, proc in self.answers.items():
            if joined.startswith(prefix):
                return proc
        return Proc()

    def commands(self) -> list[str]:
        return [" ".join(c) for c in self.calls]


WORD_OK = {release.WORD_VERSION_CMD: Proc(0, "16.101.1\n")}


def _store(root: Path, rows: list[dict]) -> Path:
    (root / "results").mkdir(exist_ok=True)
    p = root / "results" / "bench.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "neurotic-docx-bench"\nversion = "0.7.0"\n'
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n- nothing\n\n## [0.7.0] - 2026-09-27\n\n### Added\n- hub datasets\n- release gate\n\n## [0.6.0] - 2026-09-27\n\n- packaging only\n"
    )
    _store(
        tmp_path,
        [
            {
                "id_run": "a",
                "renderer_id": "word-16.101.1",
                "benchmark": "script_redlines",
            },
            {
                "id_run": "b",
                "renderer_id": "soffice-26.2.4.2",
                "benchmark": "script_redlines",
            },
        ],
    )
    (tmp_path / "corpus" / "word_based" / "docx_source").mkdir(parents=True)
    (
        tmp_path
        / "corpus"
        / "word_based"
        / "docx_source"
        / "24_id_paraid_overflow.docx"
    ).write_bytes(b"PK")
    return tmp_path


# --- pure pieces -----------------------------------------------------------


def test_source_version_reads_pyproject(repo: Path) -> None:
    assert release.source_version(repo) == "0.7.0"


def test_changelog_section_for_the_version(repo: Path) -> None:
    notes = release.changelog_section(repo / "CHANGELOG.md", "0.7.0")
    assert notes is not None
    assert "hub datasets" in notes and "release gate" in notes
    assert "packaging only" not in notes and "nothing" not in notes
    assert release.changelog_section(repo / "CHANGELOG.md", "0.8.0") is None


def test_word_version_comes_from_osascript_and_is_none_when_word_is_absent() -> None:
    assert release.word_version(FakeRunner(WORD_OK)) == "16.101.1"
    assert (
        release.word_version(
            FakeRunner({release.WORD_VERSION_CMD: Proc(1, "", "not found")})
        )
        is None
    )
    assert (
        release.word_version(FakeRunner({release.WORD_VERSION_CMD: Proc(0, "\n")}))
        is None
    )


def test_word_rows_check_requires_current_word_rows_and_no_stale_ones(
    repo: Path,
) -> None:
    ok = release.word_rows_check(repo / "results" / "bench.jsonl", "16.101.1")
    assert ok.ok and "1 row" in ok.detail
    stale = release.word_rows_check(repo / "results" / "bench.jsonl", "16.102.0")
    assert not stale.ok
    assert "word-16.101.1" in stale.detail and "a" in stale.detail
    _store(repo, [{"id_run": "b", "renderer_id": "soffice-26.2.4.2"}])
    none = release.word_rows_check(repo / "results" / "bench.jsonl", "16.101.1")
    assert not none.ok and "no row" in none.detail


# --- the gate --------------------------------------------------------------


def _convert_ok(docx: Path, out_dir: Path, **_: object):
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"{docx.stem}.pdf"
    pdf.write_bytes(b"%PDF-1.7 rendered")
    return release.RenderOutcome(ok=True, pdf=pdf, error=None)


def _convert_fail(docx: Path, out_dir: Path, **_: object):
    return release.RenderOutcome(ok=False, pdf=None, error="Word timed out (dialog?)")


def test_preflight_passes_on_a_machine_with_word_and_current_pages(repo: Path) -> None:
    run = FakeRunner(WORD_OK)
    checks = release.preflight(repo, run=run, convert=_convert_ok)
    assert all(c.ok for c in checks), [c for c in checks if not c.ok]
    names = [c.name for c in checks]
    assert names == [
        "word installed",
        "word renders",
        "word rows current",
        "pages current",
        "tree clean",
        "tag free",
        "changelog entry",
    ]
    cmds = run.commands()
    assert any(c.endswith("report --check") for c in cmds)
    assert "git status --porcelain" in cmds
    assert "git tag -l v0.7.0" in cmds


def test_preflight_fails_without_word_and_still_runs_the_cheap_checks(
    repo: Path,
) -> None:
    run = FakeRunner({release.WORD_VERSION_CMD: Proc(1, "", "execution error")})
    checks = release.preflight(repo, run=run, convert=_convert_ok)
    by = {c.name: c for c in checks}
    assert not by["word installed"].ok
    assert not by["word renders"].ok and "skipped" in by["word renders"].detail
    assert not by["word rows current"].ok
    assert (
        by["pages current"].ok
        and by["tree clean"].ok
        and by["tag free"].ok
        and by["changelog entry"].ok
    )


def test_preflight_fails_when_word_cannot_render(repo: Path) -> None:
    checks = release.preflight(repo, run=FakeRunner(WORD_OK), convert=_convert_fail)
    by = {c.name: c for c in checks}
    assert by["word installed"].ok
    assert not by["word renders"].ok and "dialog" in by["word renders"].detail


def test_preflight_fails_on_stale_pages_dirty_tree_existing_tag_missing_changelog(
    repo: Path,
) -> None:
    answers = dict(WORD_OK)
    answers["git status --porcelain"] = Proc(0, " M RESULTS.md\n")
    answers["git tag -l v0.7.0"] = Proc(0, "v0.7.0\n")
    run = FakeRunner(answers)
    run.answers[f"{release._python()} -m neurotic_docx_bench.cli report --check"] = (
        Proc(1, "stale: RESULTS.md\n")
    )
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n")
    checks = release.preflight(repo, run=run, convert=_convert_ok)
    by = {c.name: c for c in checks}
    assert not by["pages current"].ok and "RESULTS.md" in by["pages current"].detail
    assert not by["tree clean"].ok and "RESULTS.md" in by["tree clean"].detail
    assert not by["tag free"].ok
    assert not by["changelog entry"].ok


# --- publishing ------------------------------------------------------------


def test_publish_tags_builds_publishes_and_creates_the_github_release(
    repo: Path,
) -> None:
    run = FakeRunner(WORD_OK)
    out = repo / "build" / "release"

    def build_side_effect(cmd: list[str], *, cwd: Path | None = None) -> Proc:
        run.calls.append(list(cmd))
        if cmd[:2] == ["uv", "build"]:
            out.mkdir(parents=True, exist_ok=True)
            (out / "neurotic_docx_bench-0.7.0-py3-none-any.whl").write_bytes(b"PK")
            (out / "neurotic_docx_bench-0.7.0.tar.gz").write_bytes(b"\x1f\x8b")
        return Proc()

    steps = release.publish(repo, run=build_side_effect)
    assert all(s.ok for s in steps), steps
    cmds = [" ".join(c) for c in run.calls]
    assert cmds[0] == "git tag -a v0.7.0 -m neurotic-docx-bench 0.7.0"
    assert cmds[1] == f"uv build --out-dir {out}"
    assert cmds[2].startswith(f"uv publish {out}/neurotic_docx_bench-0.7.0")
    assert cmds[3] == "git push origin v0.7.0"
    assert cmds[4].startswith("gh release create v0.7.0 ")
    assert "--title neurotic-docx-bench 0.7.0" in cmds[4]
    assert "--notes-file" in cmds[4]
    notes = Path(cmds[4].split("--notes-file ")[1].split(" ")[0]).read_text()
    assert "hub datasets" in notes
    assert str(out / "neurotic_docx_bench-0.7.0-py3-none-any.whl") in cmds[4]


def test_publish_stops_at_the_first_failing_step(repo: Path) -> None:
    run = FakeRunner({**WORD_OK, "uv build": Proc(1, "", "build exploded")})
    steps = release.publish(repo, run=run)
    assert [s.name for s in steps] == ["tag", "build"]
    assert steps[0].ok and not steps[1].ok and "build exploded" in steps[1].detail
    assert not any(c[:2] == ["uv", "publish"] for c in run.calls)


# --- CLI -------------------------------------------------------------------


def test_cli_refuses_to_publish_when_the_gate_fails(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = FakeRunner({release.WORD_VERSION_CMD: Proc(1, "", "no word")})
    monkeypatch.setattr(release, "default_runner", lambda: run)
    monkeypatch.setattr(release, "default_convert", lambda: _convert_ok)
    result = runner.invoke(release.app, ["--root", str(repo)])
    assert result.exit_code == 1, result.output
    assert "word installed" in result.output and "FAIL" in result.output
    assert not any(
        c[:1] == ["uv"] or c[:2] == ["git", "tag"] and "-a" in c for c in run.calls
    )


def test_cli_check_only_never_publishes(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = FakeRunner(WORD_OK)
    monkeypatch.setattr(release, "default_runner", lambda: run)
    monkeypatch.setattr(release, "default_convert", lambda: _convert_ok)
    result = runner.invoke(release.app, ["--root", str(repo), "--check"])
    assert result.exit_code == 0, result.output
    assert "gate passed" in result.output
    assert not any(c[:1] == ["uv"] for c in run.calls)


def test_cli_publishes_when_the_gate_passes(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = FakeRunner(WORD_OK)
    out = repo / "build" / "release"

    def side_effect(cmd: list[str], *, cwd: Path | None = None) -> Proc:
        if cmd[:2] == ["uv", "build"]:
            out.mkdir(parents=True, exist_ok=True)
            (out / "neurotic_docx_bench-0.7.0-py3-none-any.whl").write_bytes(b"PK")
            (out / "neurotic_docx_bench-0.7.0.tar.gz").write_bytes(b"\x1f\x8b")
        return run(cmd, cwd=cwd)

    monkeypatch.setattr(release, "default_runner", lambda: side_effect)
    monkeypatch.setattr(release, "default_convert", lambda: _convert_ok)
    result = runner.invoke(release.app, ["--root", str(repo)])
    assert result.exit_code == 0, result.output
    assert "released neurotic-docx-bench 0.7.0" in result.output
    assert any(c[:2] == ["uv", "publish"] for c in run.calls)
    assert any(c[:3] == ["gh", "release", "create"] for c in run.calls)


def test_release_script_is_a_thin_uv_script_over_the_module() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "release.py"
    text = script.read_text()
    assert text.startswith("#!/usr/bin/env -S uv run --script\n")
    assert "# /// script" in text
    assert 'neurotic-docx-bench = { path = "..", editable = true }' in text
    assert "from neurotic_docx_bench.release import app" in text


def test_default_runner_turns_a_missing_binary_into_a_failed_process(
    tmp_path: Path,
) -> None:
    run = release.default_runner()
    proc = run(["definitely-not-a-binary-on-this-machine", "--version"], cwd=tmp_path)
    assert proc.returncode != 0
    assert "definitely-not-a-binary-on-this-machine" in proc.stderr
    ok = run([release._python(), "-c", "print('hi')"], cwd=tmp_path)
    assert ok.returncode == 0 and ok.stdout.strip() == "hi"


def test_gate_fails_cleanly_on_a_machine_without_osascript(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(release, "default_convert", lambda: _convert_ok)
    monkeypatch.setattr(
        release, "_WORD_VERSION_ARGV", ["definitely-not-osascript", "-e", "x"]
    )
    result = runner.invoke(release.app, ["--root", str(repo), "--check"])
    assert result.exit_code == 1, result.output
    assert result.output.startswith("FAIL word installed")
    assert "not released" in result.output.splitlines()[-1]
