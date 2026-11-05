"""Importable test helpers (markers + corpus paths).

Kept separate from conftest.py so test modules can ``from helpers import ...`` — pytest
puts the ``tests/`` dir on sys.path, and importing *from* conftest is discouraged.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from neurotic_docx_bench import corpus_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS = REPO_ROOT / corpus_paths.WORD
LIBREOFFICE = REPO_ROOT / corpus_paths.LIBREOFFICE
# a generator's --manifest / --source-dir, as the bench driver passes them for the word_based pool
MANIFEST = CORPUS / "pools" / "word_based_pairs.csv"
SOURCE = CORPUS


def word_based_pairs() -> list[corpus_paths.Pair]:
    """The word_based Word compares, every path resolved under this checkout's corpus."""
    return corpus_paths.pairs("word_based", word=CORPUS, libreoffice=LIBREOFFICE)


_HAS_SOFFICE = (
    shutil.which("soffice") is not None
    or Path("/Applications/LibreOffice.app/Contents/MacOS/soffice").exists()
)

requires_soffice = pytest.mark.skipif(not _HAS_SOFFICE, reason="soffice not installed")
requires_corpus = pytest.mark.skipif(not MANIFEST.is_file(), reason="corpus absent")
