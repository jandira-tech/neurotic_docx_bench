"""``bench run --gate-set``: render and score only the gate subset of each benchmark's
document set, and stamp the line with the gate set's own docset id."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench import cli
from neurotic_docx_bench.cli import app
from neurotic_docx_bench.config import load_config
from neurotic_docx_bench.ledger import docset as docset_mod

runner = CliRunner()


def test_limited_source_keeps_only_the_keyed_files(tmp_path: Path) -> None:
    src = tmp_path / "cand"
    src.mkdir()
    for stem in ("a_b_t_redline", "c_d_t_redline", "e_f_t_redline", "plain"):
        (src / f"{stem}.pdf").write_bytes(b"%PDF")
    out, is_temp = cli._limited_source(
        src, "*.pdf", None, keys={"c_d", "plain"}, tool="t"
    )
    assert is_temp
    assert sorted(p.name for p in out.iterdir()) == ["c_d_t_redline.pdf", "plain.pdf"]
    shutil.rmtree(out)
    # keys plus a limit: the limit applies after the key filter
    out, _ = cli._limited_source(src, "*.pdf", 1, keys={"c_d", "plain"}, tool="t")
    assert [p.name for p in out.iterdir()] == ["c_d_t_redline.pdf"]
    shutil.rmtree(out)
    same, is_temp = cli._limited_source(src, "*.pdf", None)
    assert same == src and not is_temp


def _setup(tmp_path: Path, sample_oracle_pdfs) -> tuple[Path, list[str]]:
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    pdf_a, pdf_b = sample_oracle_pdfs
    keys = []
    for i, pdf in enumerate((pdf_a, pdf_b, pdf_a, pdf_b)):
        key = f"doc{i}_next{i}"
        keys.append(key)
        shutil.copy(pdf, oracle / f"{key}_redline.pdf")
        shutil.copy(pdf, cand / f"{key}_t_redline.pdf")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {cand}, "
        "unversioned: true, vendor: t, jobs: 1}\n",
    )
    return cfg, keys


def test_docset_for_gate_set_is_the_gate_subset(
    tmp_path, sample_oracle_pdfs, monkeypatch
):
    monkeypatch.setattr(docset_mod, "GATE_N", 2)
    cfg_path, _keys = _setup(tmp_path, sample_oracle_pdfs)
    cfg = load_config(cfg_path)
    full = cli._docset_for(cfg, "script_redlines", None)
    gate = cli._docset_for(cfg, "script_redlines", None, gate_set=True)
    assert full is not None and gate is not None
    assert full.n == 4 and gate.n == 2
    assert gate.gate_of == full.id and set(gate.keys) < set(full.keys)
    assert cli._docset_for(cfg, "accepted_changes", None, gate_set=True) is None


def test_run_gate_set_scores_only_the_gate_subset(
    tmp_path, sample_oracle_pdfs, monkeypatch
):
    monkeypatch.setattr(docset_mod, "GATE_N", 2)
    cfg_path, _keys = _setup(tmp_path, sample_oracle_pdfs)
    results_dir = tmp_path / "results"
    copied: list[list[str]] = []
    real = cli._limited_source

    def spy(source, pattern, limit, **kw):
        out, is_temp = real(source, pattern, limit, **kw)
        copied.append(sorted(p.name for p in Path(out).iterdir()))
        return out, is_temp

    monkeypatch.setattr(cli, "_limited_source", spy)
    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(cfg_path),
            "--results-dir",
            str(results_dir),
            "--no-gate",
            "--gate-set",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "gate set: 2 of 4 documents" in result.output
    lines = [
        json.loads(x)
        for x in (results_dir / "bench.jsonl").read_text().splitlines()
        if x.strip()
    ]
    (line,) = [x for x in lines if x["benchmark"] == "script_redlines"]
    cfg = load_config(cfg_path)
    gate = cli._docset_for(cfg, "script_redlines", None, gate_set=True)
    assert gate is not None
    assert line["docset_id"] == gate.id
    assert sorted(line["scores"]) == sorted(gate.keys)
    # only the gate documents were handed to the renderer
    assert copied and copied[0] == sorted(f"{k}_t_redline.pdf" for k in gate.keys)


def test_gate_keys_for_run_include_the_visual_benchmarks(
    tmp_path, sample_oracle_pdfs, monkeypatch
):
    """A run that declares a visual benchmark gates on that benchmark's subset too."""
    monkeypatch.setattr(docset_mod, "GATE_N", 2)
    oracle = tmp_path / "oracle"
    visual = tmp_path / "visual"
    oracle.mkdir()
    visual.mkdir()
    pdf_a, pdf_b = sample_oracle_pdfs
    for i, pdf in enumerate((pdf_a, pdf_b, pdf_a, pdf_b)):
        shutil.copy(pdf, oracle / f"doc{i}_next{i}_redline.pdf")
        shutil.copy(pdf, visual / f"vis{i}_next{i}_redline.pdf")
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        f"source_of_truth: {oracle}\n"
        f"visual_oracles:\n  visual_redlines: {visual}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {oracle}, unversioned: true, "
        "vendor: t, jobs: 1, benchmarks: [script_redlines, visual_redlines]}\n",
    )
    cfg = load_config(cfg_path)
    rc = cfg.runs[0]
    keys = cli._gate_keys_for_run(cfg, rc, None)
    script_gate = cli._docset_for(cfg, "script_redlines", None, gate_set=True)
    visual_gate = cli._docset_for(cfg, "visual_redlines", None, gate_set=True)
    assert script_gate is not None and visual_gate is not None
    assert len(visual_gate.keys) == 2
    assert keys == set(script_gate.keys) | set(visual_gate.keys)
