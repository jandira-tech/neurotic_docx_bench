"""scripts/speed-bench.ts: a requested jubarte method that cannot start fails the run."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_HEADER = (
    'pair_stem,base,next,origin,docx_source_base,docx_source_next,redline_docx,'
    'redline_docx_word,accepted_docx,pdf_redline,pdf_accepted,missing\n'
)

pytestmark = pytest.mark.skipif(
    shutil.which('node') is None or not (ROOT / 'node_modules' / 'tsx').is_dir(),
    reason='needs node and the bench node_modules (tsx)',
)


def test_an_incomplete_jubarte_dist_fails_instead_of_writing_no_row(tmp_path):
    empty_dist = tmp_path / 'dist'
    empty_dist.mkdir()  # exists, but holds no redline binary
    manifest = tmp_path / 'manifest.csv'
    manifest.write_text(MANIFEST_HEADER)
    out = tmp_path / 'speed.jsonl'
    run = subprocess.run(
        ['node', '--import', 'tsx', 'scripts/speed-bench.ts', '--methods', 'jubarte-rust', '--pairs', '1',
         '--manifest', str(manifest), '--out', str(out)],
        cwd=ROOT,
        env={**os.environ, 'JUBARTE_RUST_DIST': str(empty_dist)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 1, run.stdout + run.stderr
    assert 'jubarte-rust: init failed' in run.stderr
    assert not out.exists() or out.read_text() == ''
