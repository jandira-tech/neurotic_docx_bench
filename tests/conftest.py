"""Shared fixtures for the bench test suite (markers/paths live in helpers.py)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from helpers import DOCX_SOURCE, PDF_REDLINES


@pytest.fixture(scope="session")
def sample_docx() -> list[Path]:
    if not DOCX_SOURCE.is_dir():
        pytest.skip("docx_source corpus absent")
    docs = sorted(DOCX_SOURCE.glob("*.docx"))[:2]
    if not docs:
        pytest.skip("no source docx")
    return docs


@pytest.fixture(scope="session")
def sample_oracle_pdfs() -> list[Path]:
    """Two real *redline* oracle PDFs (``…_redline.pdf``), excluding the base PDFs that
    also live in the redline dir.
    """
    if not PDF_REDLINES.is_dir():
        pytest.skip("pdf_redlines_word corpus absent")
    pdfs = [p for p in sorted(PDF_REDLINES.glob("*.pdf")) if p.stem.endswith("_redline")][:2]
    if len(pdfs) < 2:
        pytest.skip("need two redline oracle pdfs")
    return pdfs


@pytest.fixture
def docx_dir(tmp_path, sample_docx) -> Path:
    """A small temp folder holding a couple of real corpus DOCX to render."""
    d = tmp_path / "docx_in"
    d.mkdir()
    for src in sample_docx:
        shutil.copy(src, d / src.name)
    return d


# Programs that reach the live Microsoft Word on the machine running the tests.
_LIVE_WORD_PROGRAMS = frozenset({"osascript", "open", "pkill", "pgrep"})


@pytest.fixture
def no_live_word(monkeypatch: pytest.MonkeyPatch):
    """Fail any test that reaches the real Word instead of a stub.

    `word_pdf.osa()` shells out to `osascript`. A test that forgets to stub one
    path (failure recovery is the one that slipped) sends close-all and a
    document count to whatever Word is running, and then passes or fails on how
    many documents that Word happens to hold. A test that patches
    `subprocess.run` itself still wins: its patch is applied after this one.
    """
    import functools
    import subprocess

    real_run = subprocess.run
    reached: list[list[str]] = []

    @functools.wraps(real_run)
    def fenced_run(cmd, *args, **kwargs):
        argv = [str(part) for part in cmd] if isinstance(cmd, (list, tuple)) else [str(cmd)]
        if argv and Path(argv[0]).name in _LIVE_WORD_PROGRAMS:
            reached.append(argv[:2])
            # Fail at the call, not at teardown: a leak inside a polling loop
            # (`warm`, `recycle`) would otherwise spin until its deadline. The
            # exception is BaseException, so no `except Exception` swallows it.
            pytest.fail(f"test reached the live Word through {argv[:2]}")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fenced_run)
    yield
    if reached:
        pytest.fail(f"test reached the live Word through {len(reached)} call(s): {reached[:3]}")
