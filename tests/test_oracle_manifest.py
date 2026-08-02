"""Oracle checksum manifest gate (PR4): the bench refuses to score against a drifted
oracle. An accidental regeneration with the wrong LibreOffice build was previously
invisible until scores looked weird."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench import oracle_manifest
from neurotic_docx_bench.cli import app

runner = CliRunner()


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    (root / "pdf_oracle").mkdir(parents=True)
    (root / "pdf_oracle" / "a_b_redline.pdf").write_bytes(b"%PDF-1.4 oracle-a\n")
    (root / "pdf_oracle" / "c_d_redline.pdf").write_bytes(b"%PDF-1.4 oracle-c\n")
    (root / "centralized_mapping.csv").write_text("pair_stem,base,next\na_b,a,b\n")
    return root


def test_build_manifest_is_sorted_and_relative(tmp_path):
    root = _corpus(tmp_path)
    manifest = oracle_manifest.build_manifest(root, [root / "pdf_oracle"])
    assert list(manifest) == sorted(manifest)
    assert "pdf_oracle/a_b_redline.pdf" in manifest
    assert "centralized_mapping.csv" in manifest  # mapping CSVs always covered
    assert all(len(v) == 64 for v in manifest.values())


def test_verify_detects_changed_missing_extra(tmp_path):
    root = _corpus(tmp_path)
    dirs = [root / "pdf_oracle"]
    manifest_path = root / "oracle_manifest.json"
    oracle_manifest.write_manifest(manifest_path, oracle_manifest.build_manifest(root, dirs))

    drift = oracle_manifest.verify_manifest(manifest_path, root, dirs)
    assert drift.clean

    (root / "pdf_oracle" / "a_b_redline.pdf").write_bytes(b"%PDF-1.4 TAMPERED\n")
    (root / "pdf_oracle" / "c_d_redline.pdf").unlink()
    (root / "pdf_oracle" / "e_f_redline.pdf").write_bytes(b"%PDF-1.4 new\n")
    drift = oracle_manifest.verify_manifest(manifest_path, root, dirs)
    assert not drift.clean
    assert drift.changed == ["pdf_oracle/a_b_redline.pdf"]
    assert drift.missing == ["pdf_oracle/c_d_redline.pdf"]
    assert drift.extra == ["pdf_oracle/e_f_redline.pdf"]


def test_cli_oracle_manifest_write_and_verify(tmp_path):
    root = _corpus(tmp_path)
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {root / 'pdf_oracle'}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {root / 'pdf_oracle'}, unversioned: true}}\n",
    )
    w = runner.invoke(app, ["oracle-manifest", "--config", str(cfg), "--write"])
    assert w.exit_code == 0, w.output
    manifest_path = root / "oracle_manifest.json"
    assert manifest_path.is_file()
    assert json.loads(manifest_path.read_text())

    v = runner.invoke(app, ["oracle-manifest", "--config", str(cfg)])
    assert v.exit_code == 0, v.output

    (root / "pdf_oracle" / "a_b_redline.pdf").write_bytes(b"%PDF-1.4 TAMPERED\n")
    v2 = runner.invoke(app, ["oracle-manifest", "--config", str(cfg)])
    assert v2.exit_code == 2
    assert "a_b_redline.pdf" in v2.output


def test_run_refuses_drifted_oracle(tmp_path):
    root = _corpus(tmp_path)
    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "a_b_t_redline.pdf").write_bytes(b"%PDF-1.4 oracle-a\n")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {root / 'pdf_oracle'}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    oracle_manifest.write_manifest(
        root / "oracle_manifest.json",
        oracle_manifest.build_manifest(root, [root / "pdf_oracle"]),
    )
    (root / "pdf_oracle" / "a_b_redline.pdf").write_bytes(b"%PDF-1.4 TAMPERED\n")
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(tmp_path / "results")],
    )
    assert result.exit_code == 2
    assert "oracle" in result.output.lower()


def test_run_warns_but_proceeds_without_manifest(tmp_path):
    """No committed manifest (synthetic corpora, randomized config) → warn, not fail."""
    root = _corpus(tmp_path)
    cand = tmp_path / "cand"
    cand.mkdir()
    # Candidate PDF must be a real PDF for scoring; reuse identity on the oracle file.
    import shutil

    shutil.copy(root / "pdf_oracle" / "a_b_redline.pdf", cand / "a_b_t_redline.pdf")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {root / 'pdf_oracle'}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(tmp_path / "results"), "--no-emit"],
    )
    assert "no oracle manifest" in result.output.lower()
    assert result.exit_code != 2


def test_no_oracle_check_flag_skips_gate(tmp_path):
    root = _corpus(tmp_path)
    cand = tmp_path / "cand"
    cand.mkdir()
    import shutil

    shutil.copy(root / "pdf_oracle" / "a_b_redline.pdf", cand / "a_b_t_redline.pdf")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {root / 'pdf_oracle'}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    oracle_manifest.write_manifest(
        root / "oracle_manifest.json",
        oracle_manifest.build_manifest(root, [root / "pdf_oracle"]),
    )
    (root / "pdf_oracle" / "a_b_redline.pdf").write_bytes(b"%PDF-1.4 TAMPERED\n")
    result = runner.invoke(
        app,
        [
            "run", "--config", str(cfg), "--results-dir", str(tmp_path / "results"),
            "--no-oracle-check", "--no-emit",
        ],
    )
    assert result.exit_code != 2
