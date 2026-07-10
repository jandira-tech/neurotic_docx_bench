"""Phase B — skip-already-ran: runs with matching (tool, tool_version, config_hash) in
results/bench.jsonl are skipped by default; ``--rerun`` (or ``BENCH_RERUN=1``) overrides.
"""

from __future__ import annotations

import shutil

from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.pipeline import redline_key

runner = CliRunner()


def _setup(tmp_path, pdf):
    """Build oracle + candidate dirs and a passthrough bench.yaml with a real version pin."""
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    key = redline_key(pdf.stem)
    shutil.copy(pdf, oracle / pdf.name)
    shutil.copy(pdf, cand / f"{key}_prebaked_redline.pdf")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, "
        f"package: docxodus@6.4.0, jobs: 1}}\n",
    )
    return cfg


def test_skip_already_ran(tmp_path, sample_oracle_pdfs, monkeypatch):
    """A second run with the same (tool, tool_version, config_hash) is skipped."""
    monkeypatch.delenv("BENCH_RERUN", raising=False)
    cfg = _setup(tmp_path, sample_oracle_pdfs[0])
    results = tmp_path / "results"

    r1 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results), "--no-update"])
    assert r1.exit_code == 0, r1.output
    assert "appended" in r1.output
    jsonl = results / "bench.jsonl"
    lines = jsonl.read_text().strip().splitlines()
    assert len(lines) == 1

    r2 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results), "--no-update"])
    assert r2.exit_code == 0, r2.output
    assert "skip (already ran" in r2.output
    # no new line was appended
    assert len(jsonl.read_text().strip().splitlines()) == 1


def test_rerun_flag_forces_reexecution(tmp_path, sample_oracle_pdfs, monkeypatch):
    """--rerun forces the run even when the identity matches."""
    monkeypatch.delenv("BENCH_RERUN", raising=False)
    cfg = _setup(tmp_path, sample_oracle_pdfs[0])
    results = tmp_path / "results"

    r1 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results), "--no-update"])
    assert r1.exit_code == 0
    jsonl = results / "bench.jsonl"
    assert len(jsonl.read_text().strip().splitlines()) == 1

    r2 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results), "--rerun", "--no-update"])
    assert r2.exit_code == 0, r2.output
    assert "skip (already ran" not in r2.output
    assert "appended" in r2.output
    assert len(jsonl.read_text().strip().splitlines()) == 2


def test_bench_rerun_env_overrides(tmp_path, sample_oracle_pdfs, monkeypatch):
    """BENCH_RERUN=1 forces re-execution even without --rerun."""
    cfg = _setup(tmp_path, sample_oracle_pdfs[0])
    results = tmp_path / "results"

    r1 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results), "--no-update"])
    assert r1.exit_code == 0
    jsonl = results / "bench.jsonl"
    assert len(jsonl.read_text().strip().splitlines()) == 1

    monkeypatch.setenv("BENCH_RERUN", "1")
    r2 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results), "--no-update"])
    assert r2.exit_code == 0, r2.output
    assert "skip (already ran" not in r2.output
    assert len(jsonl.read_text().strip().splitlines()) == 2


def test_different_tool_version_not_skipped(tmp_path, sample_oracle_pdfs, monkeypatch):
    """Changing the version pin produces a different identity → not skipped."""
    monkeypatch.delenv("BENCH_RERUN", raising=False)
    pdf = sample_oracle_pdfs[0]
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    key = redline_key(pdf.stem)
    shutil.copy(pdf, oracle / pdf.name)
    shutil.copy(pdf, cand / f"{key}_prebaked_redline.pdf")

    cfg_v1 = tmp_path / "v1.yaml"
    cfg_v1.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, "
        f"package: docxodus@6.4.0, jobs: 1}}\n",
    )
    cfg_v2 = tmp_path / "v2.yaml"
    cfg_v2.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, "
        f"package: docxodus@6.5.0, jobs: 1}}\n",
    )
    results = tmp_path / "results"

    r1 = runner.invoke(app, ["run", "-c", str(cfg_v1), "--results-dir", str(results), "--no-update"])
    assert r1.exit_code == 0
    jsonl = results / "bench.jsonl"
    assert len(jsonl.read_text().strip().splitlines()) == 1

    # Same tool name, different version → NOT skipped
    r2 = runner.invoke(app, ["run", "-c", str(cfg_v2), "--results-dir", str(results), "--no-update"])
    assert r2.exit_code == 0, r2.output
    assert "skip (already ran" not in r2.output
    assert len(jsonl.read_text().strip().splitlines()) == 2
