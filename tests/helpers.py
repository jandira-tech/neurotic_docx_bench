"""Importable test helpers (markers + corpus paths).

Kept separate from conftest.py so test modules can ``from helpers import ...`` — pytest
puts the ``tests/`` dir on sys.path, and importing *from* conftest is discouraged.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / "corpus" / "word_based"
DOCX_SOURCE = CORPUS / "docx_source"
PDF_REDLINES = CORPUS / "pdf_redlines_word"

_HAS_SOFFICE = (
    shutil.which("soffice") is not None
    or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").exists()
)

requires_soffice = pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not installed")
requires_corpus = pytest.mark.skipif(not CORPUS.is_dir(), reason="corpus absent")
