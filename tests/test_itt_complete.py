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


def test_a_dropped_document_whose_path_has_spaces_is_completed() -> None:
    """#86 item 3: the warning names a path; a space in it must not hide the document."""
    report = json.loads(REPORT.read_text())
    report["warnings"] = [w.replace("corpus/word/", "my corpus/word/") for w in report["warnings"]]
    _, added = docx_to_pdf.itt_complete_listed(report)
    assert len(added) == 2


def test_a_limited_run_is_not_completed() -> None:
    """#86 item 4: warnings predate --limit, so they can name documents the run never took."""
    report = json.loads(REPORT.read_text()) | {"limit": 10}
    with pytest.raises(ValueError, match="limit"):
        docx_to_pdf.itt_complete_listed(report)


def test_run_records_its_limit_in_the_report(tmp_path: Path, monkeypatch) -> None:
    """#86 item 4: the report says when --limit cut the population, so completion can refuse it."""
    items = []
    for name in ("a", "b"):
        (tmp_path / f"{name}.pdf").write_bytes(b"%PDF-1.4 " + name.encode())
        items.append(docx_to_pdf.Fixture(stem=name, kind="clean", original_stem=name,
                                         docx=tmp_path / f"{name}.docx", oracle=tmp_path / f"{name}.pdf"))
    monkeypatch.setattr(docx_to_pdf, "score_folder_pair", lambda *a, **k: {})
    report = docx_to_pdf.run_eval(tmp_path / "out.json", tools=("soffice",), work_dir=tmp_path / "w", limit=1,
                                  fixtures=items, check_pins=False, score_only=True, candidates={},
                                  track="corpus/word:list")
    assert report["limit"] == 1 and report["n"] == 1
    unlimited = docx_to_pdf.run_eval(tmp_path / "out2.json", tools=("soffice",), work_dir=tmp_path / "w2",
                                     fixtures=items, check_pins=False, score_only=True, candidates={},
                                     track="corpus/word:list")
    assert unlimited.get("limit") is None


def test_itt_completion_preserves_scored_page_metrics() -> None:
    report = json.loads(REPORT.read_text())
    [tool] = report["tools"].values()
    stem = next(iter(tool["per_doc"]))
    metrics = {stem: {"jaccard": 0.4, "ssim": 0.8, "text_boundary": None}}
    tool["page_metrics"] = metrics
    tool["page_metrics_mean"] = metrics[stem]
    done, added = docx_to_pdf.itt_complete_listed(report)
    [completed] = done["tools"].values()
    assert added
    assert completed["page_metrics"] == metrics
    assert completed["page_metrics_mean"] == metrics[stem]
