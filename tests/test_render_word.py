"""Word renderer — guards + AppleScript construction (never drives live Word in tests)."""

from __future__ import annotations

import platform
import subprocess
from pathlib import Path

import pytest

from neurotic_docx_bench.render import word
from neurotic_docx_bench.render.word import WordRenderer


def test_applescript_exports_pdf() -> None:
    # the script must open the input and save-as PDF, then close without saving
    assert "file format format PDF" in word._APPLESCRIPT
    assert "active document" in word._APPLESCRIPT
    assert "close theDoc saving no" in word._APPLESCRIPT


def test_word_available_is_platform_gated() -> None:
    avail = word.word_available()
    assert isinstance(avail, bool)
    if platform.system() != "Darwin":
        assert avail is False


def test_renderer_raises_when_word_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(word, "word_available", lambda: False)
    with pytest.raises(RuntimeError, match="Word renderer requires macOS"):
        WordRenderer().to_pdfs(tmp_path, tmp_path / "work")


def test_convert_one_reports_failure_without_word(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # simulate osascript failing (no Word / permission denied) → ok=False, no crash
    class _Proc:
        returncode: int = 1
        stderr: str = "execution error: Microsoft Word got an error"
        stdout: str = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Proc())
    docx = tmp_path / "x.docx"
    docx.write_bytes(b"PK\x03\x04")  # not a real docx; we never reach Word here
    result = word.convert_one(docx, tmp_path / "out")
    assert result.ok is False
    assert result.pdf is None
    assert "Word" in (result.error or "")


def test_renderer_drives_word_pdf_once_for_the_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    # one word_pdf.py batch (one osascript) for the whole folder, never a process per document
    src = tmp_path / "src"
    src.mkdir()
    for name in ("a", "b", "~$lock"):
        (src / f"{name}.docx").write_bytes(b"PK\x03\x04")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        out = Path(argv[argv.index("--out") + 1])
        out.mkdir(parents=True, exist_ok=True)
        (out / "a.pdf").write_bytes(b"%PDF")
        return subprocess.CompletedProcess(argv, 1, "  FAIL b.docx: Word could not open it\n", "")

    monkeypatch.setattr(word, "word_available", lambda: True)
    monkeypatch.setattr(word.subprocess, "run", fake_run)
    report = WordRenderer().to_pdfs(src, tmp_path / "work")
    assert len(calls) == 1
    argv = calls[0]
    assert argv[1].endswith("scripts/word_pdf.py") and Path(argv[1]).is_file()
    assert argv[argv.index("--src") + 1] == str(src)
    assert argv[argv.index("--out") + 1] == str(tmp_path / "work" / "pdf")
    assert "--force" not in argv
    by_name = {r.source.name: r for r in report.results}
    assert set(by_name) == {"a.docx", "b.docx"}
    assert by_name["a.docx"].ok and by_name["a.docx"].pdf == tmp_path / "work" / "pdf" / "a.pdf"
    assert not by_name["b.docx"].ok and by_name["b.docx"].error == "Word could not open it"


def test_default_backend_prefers_word(monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench import render

    monkeypatch.delenv("BENCH_RENDERER")
    monkeypatch.setattr(word, "word_available", lambda: True)
    assert render.default_backend() == "word"
    assert render.resolve_backend("auto") == "word"
    assert render.resolve_backend("soffice") == "soffice"
    monkeypatch.setattr(word, "word_available", lambda: False)
    assert render.default_backend() == "soffice"
    assert render.resolve_backend("auto") == "soffice"


def test_cli_auto_backend_builds_the_resolved_renderer(monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench import cli
    from neurotic_docx_bench.render.soffice import SofficeRenderer

    monkeypatch.delenv("BENCH_RENDERER")
    monkeypatch.setattr(word, "word_available", lambda: True)
    assert isinstance(cli._renderer("auto"), WordRenderer)
    monkeypatch.setattr(word, "word_available", lambda: False)
    assert isinstance(cli._renderer("auto"), SofficeRenderer)


def test_bench_renderer_env_pins_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    from neurotic_docx_bench import render

    monkeypatch.setattr(word, "word_available", lambda: True)
    monkeypatch.setenv("BENCH_RENDERER", "soffice")
    assert render.resolve_backend("auto") == "soffice"
    assert render.resolve_backend("word") == "word"
