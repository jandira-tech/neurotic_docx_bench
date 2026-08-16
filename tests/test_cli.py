"""CLI wiring — version, compare, run (light; heavy end-to-end is exercised manually)."""

from __future__ import annotations

import shutil

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
    assert "soffice" in result.output.lower()
    assert "--converter" in result.output


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
