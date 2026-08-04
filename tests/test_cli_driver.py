"""PR4 driver — runs/ folders, --clean-runs, failure isolation, generate, version stamping."""

from __future__ import annotations

import shutil

from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.emit import jsonl as jsonl_emit
from neurotic_docx_bench.pipeline import redline_key

runner = CliRunner()


def _passthrough_dirs(tmp_path, pdf, tool="prebaked"):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    key = redline_key(pdf.stem)
    shutil.copy(pdf, oracle / pdf.name)
    shutil.copy(pdf, cand / f"{key}_{tool}_redline.pdf")
    return oracle, cand


def test_runs_folder_kept_by_default(tmp_path, sample_oracle_pdfs):
    oracle, cand = _passthrough_dirs(tmp_path, sample_oracle_pdfs[0])
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    runs_dir = tmp_path / "runs"
    r = runner.invoke(
        app,
        ["run", "-c", str(cfg), "--results-dir", str(tmp_path / "results"),
         "--runs-dir", str(runs_dir)],
    )
    assert r.exit_code == 0, r.output
    kept = list(runs_dir.glob("prebaked_*"))
    assert len(kept) == 1, "run work folder should be kept locally"


def test_clean_runs_deletes(tmp_path, sample_oracle_pdfs):
    oracle, cand = _passthrough_dirs(tmp_path, sample_oracle_pdfs[0])
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    runs_dir = tmp_path / "runs"
    r = runner.invoke(
        app,
        ["run", "-c", str(cfg), "--results-dir", str(tmp_path / "results"),
         "--runs-dir", str(runs_dir), "--clean-runs"],
    )
    assert r.exit_code == 0, r.output
    assert list(runs_dir.glob("prebaked_*")) == [], "--clean-runs must delete work folders"


def test_failure_isolation(tmp_path, sample_oracle_pdfs):
    oracle, cand = _passthrough_dirs(tmp_path, sample_oracle_pdfs[0], tool="good")
    cfg = tmp_path / "bench.yaml"
    # first run points at a non-existent source (fails), second is valid
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: broken, render: passthrough, modified: {tmp_path}/nope, unversioned: true, jobs: 1}}\n"
        f"  - {{name: good, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    r = runner.invoke(
        app,
        ["run", "-c", str(cfg), "--results-dir", str(tmp_path / "results"),
         "--runs-dir", str(tmp_path / "runs")],
    )
    assert r.exit_code == 1, r.output          # a failure ⇒ nonzero
    assert "broken" in r.output and "FAILED" in r.output
    assert "good" in r.output and "100.00" in r.output  # second run still executed


def test_tool_version_stamped_in_jsonl(tmp_path, sample_oracle_pdfs):
    oracle, cand = _passthrough_dirs(tmp_path, sample_oracle_pdfs[0])
    build = tmp_path / "toolbuild"
    build.mkdir()
    (build / "package.json").write_text('{"version": "2.3.4"}')
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, "
        f"dist: {build}, jobs: 1}}\n",
    )
    results = tmp_path / "results"
    r = runner.invoke(
        app,
        ["run", "-c", str(cfg), "--results-dir", str(results),
         "--runs-dir", str(tmp_path / "runs"), "--no-update"],
    )
    assert r.exit_code == 0, r.output
    line = jsonl_emit.last_line_for_benchmark(results / "bench.jsonl", "prebaked", "script_redlines")
    assert line is not None
    # tests that the dist's version is STAMPED into the row; the pin is
    # "<version>@<content-hash>" since 2026-08-04 (a bare version cannot distinguish
    # two builds — see test_local_version_from_package_json for why that changed).
    assert line["tool_version"].startswith("2.3.4@")
    assert line["vendor"] == "prebaked"
    assert line["benchmark"] == "script_redlines"


def _two_run_cfg(tmp_path, sample_oracle_pdfs):
    oracle, cand = _passthrough_dirs(tmp_path, sample_oracle_pdfs[0], tool="one")
    key = redline_key(sample_oracle_pdfs[0].stem)
    shutil.copy(sample_oracle_pdfs[0], cand / f"{key}_two_redline.pdf")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - {{name: one, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n"
        f"  - {{name: two, render: passthrough, modified: {cand}, unversioned: true, jobs: 1}}\n",
    )
    return cfg


_RUN_ALL_STAGE_FLAGS = ["--no-generate", "--no-accept-compare", "--no-roundtrip"]


def test_run_all_requires_names_or_really_all(tmp_path, sample_oracle_pdfs):
    cfg = _two_run_cfg(tmp_path, sample_oracle_pdfs)
    r = runner.invoke(app, ["run-all", "-c", str(cfg), *_RUN_ALL_STAGE_FLAGS])
    assert r.exit_code != 0
    assert "--really-all" in r.output


def test_run_all_rejects_names_with_really_all(tmp_path, sample_oracle_pdfs):
    cfg = _two_run_cfg(tmp_path, sample_oracle_pdfs)
    r = runner.invoke(
        app, ["run-all", "one", "--really-all", "-c", str(cfg), *_RUN_ALL_STAGE_FLAGS],
    )
    assert r.exit_code != 0
    assert "--really-all" in r.output


def test_run_all_really_all_runs_every_config_run(tmp_path, sample_oracle_pdfs):
    cfg = _two_run_cfg(tmp_path, sample_oracle_pdfs)
    r = runner.invoke(
        app,
        ["run-all", "--really-all", "-c", str(cfg), *_RUN_ALL_STAGE_FLAGS,
         "--results-dir", str(tmp_path / "results"), "--runs-dir", str(tmp_path / "runs"),
         "--no-emit", "--no-gate"],
    )
    assert r.exit_code == 0, r.output
    assert "one" in r.output and "two" in r.output
    assert len(list((tmp_path / "runs").glob("one_*"))) == 1
    assert len(list((tmp_path / "runs").glob("two_*"))) == 1


def test_run_all_scopes_generate_scripts_to_named_tools(tmp_path, sample_oracle_pdfs):
    """Named runs export $BENCH_TOOLS to generate_scripts; --really-all leaves it unset."""
    cfg = _two_run_cfg(tmp_path, sample_oracle_pdfs)
    marker = tmp_path / "bench_tools.txt"
    cfg.write_text(
        cfg.read_text()
        + f'generate_scripts:\n  - {{name: probe, command: "echo ${{BENCH_TOOLS:-UNSET}} > {marker}"}}\n',
    )
    base = ["run-all", "-c", str(cfg), "--no-accept-compare", "--no-roundtrip",
            "--results-dir", str(tmp_path / "results"), "--runs-dir", str(tmp_path / "runs"),
            "--no-emit", "--no-gate"]
    r = runner.invoke(app, [*base[:1], "two", *base[1:]])
    assert r.exit_code == 0, r.output
    assert marker.read_text().strip() == "two"
    r = runner.invoke(app, [*base, "--really-all"])
    assert r.exit_code == 0, r.output
    assert marker.read_text().strip() == "UNSET"


def test_generate_then_render(tmp_path):
    """A `generate` command that writes DOCX into $RUN_DIR/docx, then soffice renders it."""
    # oracle: render the same redline docx set is heavy; instead point oracle at the real
    # redline PDFs and generate by copying the matching redline DOCX.
    import pytest
    from helpers import CORPUS

    # Find a redline DOCX whose matching oracle redline PDF exists (skip the _word_redline
    # variant, which has no direct pdf oracle).
    one = oracle_pdf = None
    for d in sorted((CORPUS / "docx_redlines_word").glob("*_redline.docx")):
        if d.stem.endswith("_word_redline"):
            continue
        cand_pdf = CORPUS / "pdf_redlines_word" / f"{d.stem}.pdf"
        if cand_pdf.exists():
            one, oracle_pdf = d, cand_pdf
            break
    if one is None or oracle_pdf is None:
        pytest.skip("no redline docx with a matching oracle pdf")
    oracle = tmp_path / "oracle"
    oracle.mkdir()
    shutil.copy(oracle_pdf, oracle / oracle_pdf.name)

    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\nruns:\n"
        f"  - name: gentool\n"
        f"    render: soffice\n"
        f"    unversioned: true\n"
        f'    generate: "cp {one} $RUN_DIR/docx/"\n'
        f"    jobs: 1\n",
    )
    r = runner.invoke(
        app,
        ["run", "-c", str(cfg), "--results-dir", str(tmp_path / "results"),
         "--runs-dir", str(tmp_path / "runs"), "--no-emit", "--no-gate"],
    )
    assert r.exit_code == 0, r.output
    assert "generate:" in r.output
    assert "100.00" in r.output  # identity render of the oracle's own redline docx
