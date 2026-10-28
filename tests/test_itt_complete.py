"""#69: a listed score-only report that dropped crashed conversions is completed under ITT."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurotic_docx_bench import docx_to_pdf
from neurotic_docx_bench.ledger import converters as conv

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "results/release_0.13.0_evidence/docx_to_pdf_soffice_0.13.0_sample.json"


def test_the_0_13_0_soffice_sample_scores_its_two_crashes_zero() -> None:
    """Codex on PR #74 (r4373296788): itt_n 600, 2 failures, mean 54.6071, median 47.8822."""
    report = json.loads(REPORT.read_text())
    done, added = docx_to_pdf.itt_complete_listed(report)
    assert len(added) == 2 and all(s.startswith("tracking_without_comments__8e534b49f0_") for s in added)
    tool = done["tools"]["candidates"]
    assert (tool["itt_n"], tool["n_scored"], tool["failures"]) == (600, 598, 2)
    assert (tool["mean"], tool["median"]) == (54.6071, 47.8822)
    assert all(tool["per_doc"][s] == 0.0 for s in added)
    assert {f["doc"] for f in tool["generate_failures"]} == set(added)
    assert done["n"] == 600 and len(done["stems"]) == 600 and set(added) <= set(done["stems"])
    assert done["generated_at"] == report["generated_at"]  # the measurement's date, not today's
    assert done["itt_completed"]["added"] == sorted(added)
    assert report["tools"]["candidates"]["itt_n"] == 598  # the input is not modified
    [line] = conv.lines_from_report(done, hardware=None, report_path="x.json")
    assert (line["itt_n"], line["failures"], sorted(line["failed_docs"])) == (600, 2, sorted(added))


def test_a_complete_report_is_left_as_it_is() -> None:
    report = json.loads(REPORT.read_text())
    done, _ = docx_to_pdf.itt_complete_listed(report)
    again, added = docx_to_pdf.itt_complete_listed(done)
    assert added == [] and again == done


def test_only_a_listed_track_is_completed() -> None:
    report = json.loads(REPORT.read_text()) | {"track": "corpus/word:all"}
    with pytest.raises(ValueError, match="listed"):
        docx_to_pdf.itt_complete_listed(report)


def test_the_cli_writes_the_completed_report_and_appends_its_line(tmp_path: Path, monkeypatch) -> None:
    from typer.testing import CliRunner

    from neurotic_docx_bench.cli import app

    rep = tmp_path / "docx_to_pdf_soffice_0.13.0_sample.json"
    rep.write_text(REPORT.read_text())
    store = tmp_path / "converters.jsonl"
    store.write_text(json.dumps({"report_path": str(rep), "hardware": {"cpu": "M3"}}) + "\n")
    monkeypatch.chdir(tmp_path)
    got = CliRunner().invoke(app, ["itt-complete-reports", str(rep), "--store", str(store)])
    assert got.exit_code == 0, got.output
    out = tmp_path / "docx_to_pdf_soffice_0.13.0_sample_itt.json"
    assert json.loads(out.read_text())["tools"]["candidates"]["itt_n"] == 600
    lines = [json.loads(x) for x in store.read_text().splitlines()]
    assert len(lines) == 2 and lines[0] == {"report_path": str(rep), "hardware": {"cpu": "M3"}}
    assert (lines[1]["itt_n"], lines[1]["hardware"], lines[1]["report_path"]) == (600, {"cpu": "M3"}, out.name)
