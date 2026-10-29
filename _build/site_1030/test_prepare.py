"""Manifest/failure decisions are pure; no real network, files or clocks."""
from pathlib import Path
import pytest
from prepare_helpers import manifest_hashes_text, word_output_confirmed, word_log_evidence, word_failure_reason


def test_sha_manifest_parses_text_and_binary_markers():
    assert manifest_hashes_text('a' * 64 + '  input with spaces.pdf\n\n' + 'b' * 64 + ' *other.pdf\n') == {
        'input with spaces.pdf': 'a' * 64, 'other.pdf': 'b' * 64}
    assert manifest_hashes_text('') == {}


@pytest.mark.parametrize('text', ['short', 'a' * 64 + '??name', 'g' * 64 + '  name',
                                  ('a' * 64 + '  same\n') * 2])
def test_sha_manifest_rejects_ambiguous_or_invalid_lines(text):
    with pytest.raises(ValueError):
        manifest_hashes_text(text)


def test_only_same_document_successful_manifest_output_confirms_resolution():
    pdf = Path('/fake/export.pdf')
    good = {'kind': 'accept_all', 'original_filename': 'trimmed.docx', 'status': 'ok', 'path_out': str(pdf)}
    assert word_output_confirmed(pdf, [good], 'original.docx', 'trimmed.docx', 'accept_all')
    assert word_output_confirmed(pdf, [{**good, 'status': 'skipped'}], 'original.docx', 'trimmed.docx', 'accept_all')
    assert not word_output_confirmed(None, [good], 'original.docx', 'trimmed.docx', 'accept_all')
    for field, value in [('kind', 'pdf'), ('original_filename', 'other.docx'),
                         ('status', 'failed'), ('path_out', '/other/export.pdf')]:
        assert not word_output_confirmed(pdf, [{**good, field: value}], 'original.docx', 'trimmed.docx', 'accept_all')
    assert not word_output_confirmed(pdf, [], 'original.docx', 'trimmed.docx', 'accept_all')


def test_word_failure_keeps_exact_reason_and_matching_per_document_log():
    text = 'INFO file.docx\nFAIL other.docx — unrelated\n[batch] FAIL: file.docx — precise driver reason\n'
    evidence = word_log_evidence(text, 'file.docx', '/fake/driver.log')
    assert evidence == [{'path': '/fake/driver.log', 'line': '[batch] FAIL: file.docx — precise driver reason'}]
    line = {'original_filename': 'trim.docx', 'kind': 'pdf', 'status': 'failed', 'error': 'exact manifest error'}
    assert word_failure_reason([line], 'file.docx', 'trim.docx', 'pdf', evidence) == 'exact manifest error'
    assert word_failure_reason([], 'file.docx', 'trim.docx', 'pdf', evidence) == 'precise driver reason'
    assert word_failure_reason([{**line, 'error': ''}], 'file.docx', 'trim.docx', 'pdf', evidence) == 'precise driver reason'
    assert word_failure_reason([{**line, 'kind': 'wrong'}], 'file.docx', 'trim.docx', 'pdf', evidence) == 'precise driver reason'
    assert word_failure_reason([{**line, 'status': 'ok'}], 'file.docx', 'trim.docx', 'pdf', evidence) == 'precise driver reason'
    assert word_failure_reason([{**line, 'original_filename': 'other'}], 'file.docx', 'trim.docx', 'pdf', evidence) == 'precise driver reason'


def test_word_failure_requires_both_reason_and_log_evidence():
    line = {'original_filename': 'file.docx', 'kind': 'pdf', 'status': 'failed', 'error': 'manifest error'}
    with pytest.raises(ValueError, match='failure reason'):
        word_failure_reason([], 'file.docx', 'file.docx', 'pdf', [{'line': 'FAIL without separator'}])
    with pytest.raises(ValueError, match='log evidence'):
        word_failure_reason([line], 'file.docx', 'file.docx', 'pdf', [])
