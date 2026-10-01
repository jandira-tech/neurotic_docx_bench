"""Shared fixtures for the bench test suite (markers/paths live in helpers.py)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from helpers import MANIFEST, word_based_pairs

# The scorer defaults to mps; the parity tests are locked to the numpy path.
os.environ.setdefault("BENCH_DEVICE", "numpy")


@pytest.fixture(scope="session")
def sample_docx() -> list[Path]:
    """The base documents of the first two word_based Word compares (corpus/word)."""
    if not MANIFEST.is_file():
        pytest.skip("corpus/word absent")
    docs = [p.base for p in word_based_pairs()[:2]]
    if not all(d.is_file() for d in docs):
        pytest.skip("no source docx")
    return docs


@pytest.fixture(scope="session")
def sample_oracle_pdfs() -> list[Path]:
    """Two real redline oracle PDFs: LibreOffice's renders of two Word compares
    (corpus/libreoffice), named by their corpus key.
    """
    if not MANIFEST.is_file():
        pytest.skip("corpus/word absent")
    pdfs = [p.libreoffice_pdf for p in word_based_pairs() if p.libreoffice_pdf is not None][:2]
    if len(pdfs) < 2 or not all(p.is_file() for p in pdfs):
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


@pytest.fixture(autouse=True)
def _auto_renders_with_soffice(monkeypatch: pytest.MonkeyPatch) -> None:
    """``render: auto`` resolves to LibreOffice in tests, on a Mac with Word as in CI.

    A test about the resolution itself clears ``BENCH_RENDERER`` and stubs
    ``word.word_available``.
    """
    monkeypatch.setenv("BENCH_RENDERER", "soffice")


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
