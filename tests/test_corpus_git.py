"""What git keeps under ``corpus/`` (#70): the tables, not the files derived from them."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True)


def test_derived_parquet_configs_are_ignored_and_untracked() -> None:
    # scripts/hf_fixtures/hf_fixtures.py build writes them from the tracked CSVs; their copy of
    # record is the HF fixtures dataset (data/*.parquet). Tracked, they were plain blobs that
    # corpus/.gitattributes wants as LFS pointers.
    if not (ROOT / '.git').exists():
        pytest.skip('not a git checkout')
    assert _git('check-ignore', '-q', '--no-index', 'corpus/data/documents.parquet').returncode == 0
    assert _git('ls-files', '--', 'corpus/data/*.parquet').stdout == ''
