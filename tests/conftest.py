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
