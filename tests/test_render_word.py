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
