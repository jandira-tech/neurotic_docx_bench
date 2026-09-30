"""CLI wiring — version, compare, run (light; heavy end-to-end is exercised manually)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.pipeline import redline_key

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()  # some version string


def test_docx_to_pdf_help_lists_the_visual_track():
    result = runner.invoke(app, ["docx-to-pdf", "--help"])
    assert result.exit_code == 0, result.output
    assert "--tool" in result.output
    assert "--converter" in result.output
    assert "rdocx" in result.output
    assert "--origin" in result.output
    assert "--files-list" in result.output
    assert "--score-only" in result.output
    assert "--location-to-score" in result.output


def test_files_list_without_origin_list_is_an_error(tmp_path):
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        "word_pdf:\n  root: corpus/word\n  states: [clean]\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["docx-to-pdf", "--origin", "clean", "--files-list", "somewhere.docx", "--config", str(cfg)],
    )
    assert result.exit_code != 0
    assert "list" in result.output


def test_origin_without_a_word_pdf_warns_and_does_not_convert(tmp_path):
    root = tmp_path / "corpus" / "word"
    docx = root / "with_comments_clean" / "docx" / "df097720f7_file_131.docx"
    docx.parent.mkdir(parents=True)
    docx.write_bytes(b"docx")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        "word_pdf:\n"
        "  root: corpus/word\n"
        "  states:\n"
        "    - clean\n"
        "    - tracking_without_comments\n"
        "    - with_comments_clean\n"
        "    - with_comments_tracking\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "docxide-metrics",
            "--origin",
            "with_comments_clean",
            "--config",
            str(cfg),
            "--json",
            str(tmp_path / "out.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    # rich wraps the long path at the terminal width; compare unwrapped.
    assert "df097720f7_file_131" in result.output.replace("\n", "")
    assert "warning:" in result.output
    saved = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert saved["n"] == 0
    assert saved["tools"] == {}


def test_compare_passthrough_self(tmp_path, sample_oracle_pdfs):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    p = sample_oracle_pdfs[0]
    key = redline_key(p.stem)
    shutil.copy(p, oracle / p.name)  # <key>_redline.pdf
    shutil.copy(p, cand / f"{key}_jubarte_redline.pdf")

    result = runner.invoke(
        app, ["compare", str(cand), str(oracle), "--tool", "jubarte", "--jobs", "1"],
    )
    assert result.exit_code == 0, result.output
    assert "100.00" in result.output


def test_run_passthrough(tmp_path, sample_oracle_pdfs):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    p = sample_oracle_pdfs[0]
    key = redline_key(p.stem)
    shutil.copy(p, oracle / p.name)
    shutil.copy(p, cand / f"{key}_prebaked_redline.pdf")  # tool == run name

    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        "runs:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    # --results-dir MUST be passed: without it the run appends a junk "prebaked" line
    # to the real results/bench.jsonl on every test run (found 2026-08-02; RESULTS.md
    # had been carrying one since July).
    result = runner.invoke(
        app, ["run", "--config", str(cfg), "--results-dir", str(tmp_path / "results"), "--runs-dir", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, result.output
    assert "prebaked" in result.output
    assert "100.00" in result.output


def test_score_only_stamps_the_tool_version_into_the_report(tmp_path):
    from neurotic_docx_bench.cli import _stamp_tool_version

    out = tmp_path / "out.json"
    report = {"n": 1, "tools": {"jubarte": {"tool": "jubarte", "version": None}}}
    out.write_text(json.dumps(report), encoding="utf-8")
    _stamp_tool_version(report, out, "jubarte 0.9.3")
    assert report["tools"]["jubarte"]["version"] == "jubarte 0.9.3"
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["tools"]["jubarte"]["version"] == "jubarte 0.9.3"


def test_score_only_keeps_a_known_version_and_skips_an_empty_label(tmp_path):
    from neurotic_docx_bench.cli import _stamp_tool_version

    out = tmp_path / "out.json"
    report = {"tools": {"a": {"version": "a 1.0"}, "b": {"version": None}}}
    out.write_text("untouched", encoding="utf-8")
    _stamp_tool_version(report, out, None)
    assert out.read_text(encoding="utf-8") == "untouched"
    _stamp_tool_version(report, out, "b 2.0")
    assert report["tools"]["a"]["version"] == "a 1.0"
    assert report["tools"]["b"]["version"] == "b 2.0"


def test_score_only_help_lists_tool_version():
    for command in ("docx-to-pdf", "docxide-metrics"):
        result = runner.invoke(app, [command, "--help"])
        assert result.exit_code == 0
        assert "--tool-version" in result.output


def test_ledger_report_path_is_repo_relative(tmp_path, monkeypatch):
    from neurotic_docx_bench.cli import _ledger_report_path

    monkeypatch.chdir(tmp_path)
    inside = tmp_path / "results" / "r.json"
    assert _ledger_report_path(inside) == "results/r.json"
    assert _ledger_report_path(Path("results/r.json")) == "results/r.json"
    outside = tmp_path.parent / "elsewhere.json"
    assert _ledger_report_path(outside) == str(outside)
