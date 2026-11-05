"""scripts/pdf_sample_report.py: tool selection, failure scores, empty shared sets."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'pdf_sample_report.py'
spec = importlib.util.spec_from_file_location('pdf_sample_report', SCRIPT)
psr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(psr)


def _report(path: Path, tools: dict) -> Path:
    path.write_text(json.dumps({'tools': tools}), encoding='utf-8')
    return path


def test_a_failed_document_scores_zero_even_when_a_score_was_kept(tmp_path):
    report = _report(
        tmp_path / 'r.json',
        {'jubarte': {'per_doc': {'a': 80.0, 'b': 70.0}, 'generate_failures': [{'doc': 'b'}, {'doc': 'c'}]}},
    )
    scores, fails = psr.load(str(report))
    assert scores == {'a': 80.0, 'b': 0.0, 'c': 0.0}
    assert fails == {'b', 'c'}


def test_a_multi_tool_report_needs_the_tool_named(tmp_path):
    report = _report(
        tmp_path / 'r.json', {'jubarte': {'per_doc': {'a': 80.0}}, 'soffice': {'per_doc': {'a': 50.0}}}
    )
    with pytest.raises(SystemExit, match='pick one'):
        psr.load(str(report))
    with pytest.raises(SystemExit, match='no tool'):
        psr.load(f'{report}#docxide')
    assert psr.load(f'{report}#soffice')[0] == {'a': 50.0}


def test_reports_sharing_no_document_print_instead_of_crashing(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(psr, 'docs', dict)
    a = _report(tmp_path / 'a.json', {'t': {'per_doc': {'x': 1.0}}})
    b = _report(tmp_path / 'b.json', {'t': {'per_doc': {'y': 2.0}}})
    psr.main([f'A={a}', f'B={b}'])
    assert 'nothing to report' in capsys.readouterr().out
