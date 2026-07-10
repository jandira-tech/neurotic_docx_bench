"""CLI emission + gating (PLAN §7/§8) — append-on-change, accept-scores, regression fail."""

from __future__ import annotations

import shutil

from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.emit import jsonl as jsonl_emit
from neurotic_docx_bench.pipeline import redline_key

runner = CliRunner()


def _yaml(oracle, candidate, name="prebaked"):
    return (
        f"source_of_truth: {oracle}\n"
        "runs:\n"
        f"  - {{name: {name}, render: passthrough, modified: {candidate}, unversioned: true, jobs: 1}}\n"
    )


def test_run_appends_every_time_by_default(tmp_path, sample_oracle_pdfs):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    p = sample_oracle_pdfs[0]
    key = redline_key(p.stem)
    shutil.copy(p, oracle / p.name)  # <key>_redline.pdf
    shutil.copy(p, cand / f"{key}_prebaked_redline.pdf")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(_yaml(oracle, cand))
    results = tmp_path / "results"

    # Default: every run appends a line (append-only trend log, never rewritten).
    r1 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results)])
    assert r1.exit_code == 0, r1.output
    assert "appended" in r1.output
    assert len(jsonl_emit.read_lines(results / "bench.jsonl")) == 1

    r2 = runner.invoke(app, ["run", "-c", str(cfg), "--results-dir", str(results)])
    assert r2.exit_code == 0
    assert "appended" in r2.output
    assert len(jsonl_emit.read_lines(results / "bench.jsonl")) == 2  # accumulated, not rewritten

    # --only-on-change opts into the delta log: an identical run is skipped.
    r3 = runner.invoke(
        app, ["run", "-c", str(cfg), "--results-dir", str(results), "--only-on-change"],
    )
    assert r3.exit_code == 0
    assert "no change, skipped" in r3.output
    assert len(jsonl_emit.read_lines(results / "bench.jsonl")) == 2  # unchanged → not appended


def test_accept_then_regression_fails(tmp_path, sample_oracle_pdfs):
    a, b = sample_oracle_pdfs[0], sample_oracle_pdfs[1]
    oracle = tmp_path / "oracle"
    good = tmp_path / "good"
    bad = tmp_path / "bad"
    for d in (oracle, good, bad):
        d.mkdir()
    key = "doc"
    shutil.copy(a, oracle / f"{key}_redline.pdf")
    shutil.copy(a, good / f"{key}_prebaked_redline.pdf")  # identical → 100
    shutil.copy(b, bad / f"{key}_prebaked_redline.pdf")   # different → < 100
    results = tmp_path / "results"

    # 1) run with the perfect candidate, accept it as the baseline (100)
    cfg_good = tmp_path / "good.yaml"
    cfg_good.write_text(_yaml(oracle, good))
    assert runner.invoke(
        app, ["run", "-c", str(cfg_good), "--results-dir", str(results)],
    ).exit_code == 0
    acc = runner.invoke(app, ["accept-scores", "prebaked", "--results-dir", str(results)])
    assert acc.exit_code == 0, acc.output
    assert (results / "score-snapshots" / "prebaked__script_redlines.json").exists()

    # 2) run with the worse candidate → aggregate regression → red exit
    cfg_bad = tmp_path / "bad.yaml"
    cfg_bad.write_text(_yaml(oracle, bad))
    reg = runner.invoke(app, ["run", "-c", str(cfg_bad), "--results-dir", str(results)])
    assert reg.exit_code == 1, reg.output
    assert "FAIL" in reg.output
