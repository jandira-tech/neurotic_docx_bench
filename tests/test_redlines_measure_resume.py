"""results/redlines_0929_full/measure.py: what a resumed score row may stand for."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'results/redlines_0929_full/measure.py'


@pytest.fixture(scope='module')
def measure():
    spec = importlib.util.spec_from_file_location('redlines_measure', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pdfs(tmp_path: Path) -> tuple[Path, Path, dict]:
    orc, cand = tmp_path / 'oracle.pdf', tmp_path / 'cand.pdf'
    orc.write_bytes(b'%PDF word')
    cand.write_bytes(b'%PDF candidate')
    shas = {'oracle_sha256': hashlib.sha256(orc.read_bytes()).hexdigest(),
            'candidate_sha256': hashlib.sha256(cand.read_bytes()).hexdigest()}
    return orc, cand, shas


def test_a_row_stands_for_its_two_pdfs_and_its_scorer(measure, tmp_path: Path) -> None:
    orc, cand, shas = _pdfs(tmp_path)
    scorer = measure._scorer_id()
    assert measure._still_current(shas | {'scorer': scorer}, orc, cand, scorer)
    cand.write_bytes(b'%PDF another candidate')
    assert not measure._still_current(shas | {'scorer': scorer}, orc, cand, scorer)


def test_a_row_scored_by_another_backend_or_scorer_source_is_scored_again(measure, tmp_path: Path) -> None:
    orc, cand, shas = _pdfs(tmp_path)
    scorer = measure._scorer_id()
    assert not measure._still_current(shas | {'scorer': 'torch-mps:0123456789abcdef'}, orc, cand, 'numpy:0123456789abcdef')
    assert not measure._still_current(shas, orc, cand, scorer)  # scored before the scorer was recorded


def test_a_row_without_recorded_hashes_is_scored_again(measure, tmp_path: Path) -> None:
    orc, cand, _ = _pdfs(tmp_path)
    scorer = measure._scorer_id()
    assert not measure._still_current({'overall_score': 99.0, 'scorer': scorer}, orc, cand, scorer)


def test_the_scorer_id_names_the_backend_and_the_scoring_sources(measure) -> None:
    from neurotic_docx_bench import content_cache, kernels

    assert measure._scorer_id() == f'{kernels.backend_id()}:{content_cache.scorer_fingerprint()}'
