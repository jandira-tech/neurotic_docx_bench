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


def _manifest(folder: Path, lines: list[dict]) -> None:
    import json
    with open(folder / 'manifest.jsonl', 'w') as fh:
        for line in lines:
            fh.write(json.dumps(line) + '\n')


def test_a_candidate_is_found_under_the_name_word_pdf_gave_it(measure, tmp_path: Path) -> None:
    """word_pdf.py trims a long docx name and writes `<stem>_byword.pdf`; its manifest links them."""
    long_docx = 'k' * 120 + '_jubarte-0.13.0.docx'
    (tmp_path / 'kkk_1a7c593e_byword.pdf').write_bytes(b'%PDF trimmed')
    (tmp_path / 'short_jubarte-0.13.0_byword.pdf').write_bytes(b'%PDF short')
    _manifest(tmp_path, [
        {'kind': 'rename', 'status': 'renamed', 'original_filename': long_docx,
         'converted_filename': 'kkk_1a7c593e.docx'},
        {'kind': 'pdf', 'status': 'ok', 'original_filename': 'kkk_1a7c593e.docx',
         'converted_filename': 'kkk_1a7c593e_byword.pdf', 'path_out': str(tmp_path / 'kkk_1a7c593e_byword.pdf')},
        {'kind': 'pdf', 'status': 'skipped', 'original_filename': 'short_jubarte-0.13.0.docx',
         'converted_filename': 'short_jubarte-0.13.0_byword.pdf',
         'path_out': str(tmp_path / 'short_jubarte-0.13.0_byword.pdf')},
        {'kind': 'pdf', 'status': 'failed', 'original_filename': 'gone_jubarte-0.13.0.docx',
         'converted_filename': ''},
    ])
    assert measure.candidate_pdf(tmp_path, 'k' * 120, 'jubarte-0.13.0') == tmp_path / 'kkk_1a7c593e_byword.pdf'
    assert measure.candidate_pdf(tmp_path, 'short', 'jubarte-0.13.0') == tmp_path / 'short_jubarte-0.13.0_byword.pdf'
    assert not measure.candidate_pdf(tmp_path, 'gone', 'jubarte-0.13.0').is_file()


def test_a_candidate_under_the_plain_name_still_wins(measure, tmp_path: Path) -> None:
    """PDFs fetched from the hub keep `<key>_<tool>.pdf` and have no manifest."""
    (tmp_path / 'abc_docxodus.pdf').write_bytes(b'%PDF hub')
    assert measure.candidate_pdf(tmp_path, 'abc', 'docxodus') == tmp_path / 'abc_docxodus.pdf'
