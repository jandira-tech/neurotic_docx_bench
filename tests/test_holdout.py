"""Sealed 20-pair holdout (PR12) — loader, scoring filters, config wiring, CLI
mode stamp, and the RESULTS.md "Holdout gap" section."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest
from helpers import CORPUS, PDF_REDLINES, REPO_ROOT, requires_corpus
from typer.testing import CliRunner

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.cli import app
from neurotic_docx_bench.config import environment_config_for_run, load_config
from neurotic_docx_bench.emit import jsonl

HOLDOUT_TXT = CORPUS / "holdout.txt"
RANDOMIZED_PDF = CORPUS / "pdf_redlines_randomized" / "pdf"

# Same importlib pattern as test_export_results_md.py (the script name has dashes),
# under a distinct module name so the two test modules never clobber each other.
_MOD_PATH = REPO_ROOT / "scripts" / "export-results-md.py"
_spec = importlib.util.spec_from_file_location("export_results_md_holdout", _MOD_PATH)
assert _spec and _spec.loader
exp = importlib.util.module_from_spec(_spec)
sys.modules["export_results_md_holdout"] = exp
_spec.loader.exec_module(exp)

runner = CliRunner()


# ── load_holdout ─────────────────────────────────────────────────────────────


def test_load_holdout_skips_comments_and_blanks(tmp_path):
    p = tmp_path / "holdout.txt"
    p.write_text("# provenance header\n\na_b\n  c_d  \n# trailing comment\n\n")
    assert pipeline.load_holdout(p) == {"a_b", "c_d"}


def test_load_holdout_duplicate_raises(tmp_path):
    p = tmp_path / "holdout.txt"
    p.write_text("a_b\nc_d\na_b\n")
    with pytest.raises(ValueError, match="duplicate"):
        pipeline.load_holdout(p)


# ── score_folders_full filters ───────────────────────────────────────────────


def _mirrored_pair_dirs(tmp_path, sample_oracle_pdfs):
    """Oracle + candidate dirs where the candidate is the oracle renamed with a
    tool suffix (every doc scores ~100) — the established synthetic-corpus setup."""
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    keys = []
    for p in sample_oracle_pdfs:
        key = pipeline.oracle_pair_key(p.stem)
        shutil.copy(p, oracle / f"{key}_redline.pdf")
        shutil.copy(p, cand / f"{key}_t_redline.pdf")
        keys.append(key)
    return oracle, cand, sorted(keys)


def test_score_folders_full_exclude_keys_drops_exactly(tmp_path, sample_oracle_pdfs):
    oracle, cand, keys = _mirrored_pair_dirs(tmp_path, sample_oracle_pdfs)
    full = pipeline.score_folders_full(
        oracle, cand, tmp_path / "work", jobs=1, candidate_tool="t",
        exclude_keys={keys[0]},
    )
    assert set(full) == set(keys) - {keys[0]}
    for result in full.values():
        assert result["overall_score"] == pytest.approx(100.0, abs=1e-6)


def test_score_folders_full_only_keys_keeps_exactly(tmp_path, sample_oracle_pdfs):
    oracle, cand, keys = _mirrored_pair_dirs(tmp_path, sample_oracle_pdfs)
    full = pipeline.score_folders_full(
        oracle, cand, tmp_path / "work", jobs=1, candidate_tool="t",
        only_keys={keys[0]},
    )
    assert set(full) == {keys[0]}


def test_score_folders_full_both_filters_raise(tmp_path):
    o = tmp_path / "o"
    c = tmp_path / "c"
    o.mkdir()
    c.mkdir()
    with pytest.raises(ValueError, match="exclude_keys and only_keys"):
        pipeline.score_folders_full(
            o, c, tmp_path / "w", jobs=1, exclude_keys={"a"}, only_keys={"b"},
        )


# ── holdout.txt (the committed sealed set) ───────────────────────────────────


def test_holdout_txt_integrity():
    text = HOLDOUT_TXT.read_text()
    keys = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    assert len(keys) == 20
    assert keys == sorted(keys)
    assert len(set(keys)) == 20
    # provenance header (seed / universe / date) must be present
    assert text.lstrip().startswith("#")
    assert "0xD0C5" in text


@pytest.mark.skipif(
    not (PDF_REDLINES.is_dir() and RANDOMIZED_PDF.is_dir()),
    reason="oracle corpus absent",
)
def test_holdout_keys_exist_in_oracle_index():
    index = pipeline._index_redlines_union([PDF_REDLINES, RANDOMIZED_PDF], None)
    keys = pipeline.load_holdout(HOLDOUT_TXT)
    missing = keys - set(index)
    assert not missing, f"holdout keys not in the oracle index union: {sorted(missing)}"


# ── config wiring ────────────────────────────────────────────────────────────


def test_config_holdout_list_parsed(tmp_path):
    (tmp_path / "holdout.txt").write_text("a_b\n")
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "holdout_list: holdout.txt\n"
        "runs:\n"
        "  - {name: t, render: passthrough, unversioned: true, vendor: t}\n",
    )
    cfg = load_config(cfg_path)
    assert cfg.holdout_list == tmp_path / "holdout.txt"
    # the single-run environment_config keeps the field (self-contained lines)
    assert environment_config_for_run(cfg, "t").holdout_list == cfg.holdout_list


def test_config_holdout_list_default_none(tmp_path):
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "runs:\n"
        "  - {name: t, render: passthrough, unversioned: true, vendor: t}\n",
    )
    assert load_config(cfg_path).holdout_list is None


def test_config_holdout_list_missing_file_raises(tmp_path):
    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "holdout_list: nope.txt\n"
        "runs:\n"
        "  - {name: t, render: passthrough, unversioned: true, vendor: t}\n",
    )
    with pytest.raises(ValueError, match="holdout_list"):
        load_config(cfg_path)


@requires_corpus
def test_real_bench_yaml_wires_holdout():
    cfg = load_config(REPO_ROOT / "bench.yaml")
    assert cfg.holdout_list == HOLDOUT_TXT
    assert len(pipeline.load_holdout(cfg.holdout_list)) == 20


# ── skip-already-ran identity ────────────────────────────────────────────────


def test_skip_identity_distinguishes_holdout_lines(tmp_path):
    p = tmp_path / "bench.jsonl"
    ident = {
        "vendor": "v",
        "benchmark": "script_redlines",
        "tool_version": "1.0",
        "config_hash": "abc",
    }
    kwargs = dict(
        vendor="v", benchmark="script_redlines", tool_version="1.0", config_hash="abc",
    )
    # A pre-holdout line (no holdout_mode field) satisfies a normal run…
    p.write_text(json.dumps(ident) + "\n")
    assert jsonl.has_already_ran_benchmark(p, **kwargs, holdout_only=False) is not None
    # …but never a --holdout run.
    assert jsonl.has_already_ran_benchmark(p, **kwargs, holdout_only=True) is None
    # A holdout-only line earlier in the file must not shadow the full line (and
    # vice versa): each mode finds its own prior.
    p.write_text(
        json.dumps({**ident, "holdout_mode": "only"}) + "\n" + json.dumps(ident) + "\n",
    )
    prior_holdout = jsonl.has_already_ran_benchmark(p, **kwargs, holdout_only=True)
    assert prior_holdout is not None and prior_holdout["holdout_mode"] == "only"
    prior_full = jsonl.has_already_ran_benchmark(p, **kwargs, holdout_only=False)
    assert prior_full is not None and "holdout_mode" not in prior_full


# ── CLI: exclude by default, --holdout flips to only ─────────────────────────


def test_cli_run_holdout_modes(tmp_path, sample_oracle_pdfs):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    keys = []
    for p in sample_oracle_pdfs:
        key = pipeline.oracle_pair_key(p.stem)
        shutil.copy(p, oracle / f"{key}_redline.pdf")
        shutil.copy(p, cand / f"{key}_prebaked_redline.pdf")  # tool == run name
        keys.append(key)
    keys = sorted(keys)
    holdout_key = keys[0]
    hold = tmp_path / "holdout.txt"
    hold.write_text(f"# test holdout\n{holdout_key}\n")

    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        f"holdout_list: {hold}\n"
        "runs:\n"
        f"  - {{name: prebaked, render: passthrough, modified: {cand}, "
        "unversioned: true, vendor: prebaked, jobs: 1}\n",
    )
    results_dir = tmp_path / "results"

    def _script_lines():
        raw = (results_dir / "bench.jsonl").read_text().splitlines()
        return [
            line
            for line in map(json.loads, raw)
            if line.get("benchmark") == "script_redlines"
        ]

    # Normal run: holdout keys are excluded from scoring, mode stamped "excluded".
    result = runner.invoke(
        app, ["run", "--config", str(cfg), "--results-dir", str(results_dir)],
    )
    assert result.exit_code == 0, result.output
    line = _script_lines()[-1]
    assert line["holdout_mode"] == "excluded"
    assert set(line["scores"]) == set(keys) - {holdout_key}

    # --holdout run: ONLY the holdout keys are scored, mode stamped "only".
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(results_dir), "--holdout"],
    )
    assert result.exit_code == 0, result.output
    line = _script_lines()[-1]
    assert line["holdout_mode"] == "only"
    assert set(line["scores"]) == {holdout_key}


def test_cli_holdout_flag_without_config_key_fails(tmp_path):
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {tmp_path}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {tmp_path}, "
        "unversioned: true, vendor: t}\n",
    )
    result = runner.invoke(
        app,
        [
            "run", "--config", str(cfg),
            "--results-dir", str(tmp_path / "results"), "--holdout",
        ],
    )
    assert result.exit_code != 0


# ── export: "## Holdout gap" section ─────────────────────────────────────────


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")


def test_export_holdout_gap_with_data(tmp_path):
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        # older lines first (append-only log): both sides must pick the LATEST
        {"vendor": "jubarte", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 95.0, "n_docs": 383},
        {"vendor": "jubarte", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 70.0, "n_docs": 20, "holdout_mode": "only"},
        {"vendor": "jubarte", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 90.0, "n_docs": 383, "holdout_mode": "excluded"},
        {"vendor": "jubarte", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 85.5, "n_docs": 20, "holdout_mode": "only"},
    ])
    text = "\n".join(exp.holdout_gap_section(p))
    assert "## Holdout gap" in text
    assert "jubarte" in text
    assert "85.5" in text  # latest holdout mean
    assert "-4.50" in text  # gap = 85.5 − 90.0 (latest main, not the stale 95)
    assert "no holdout runs recorded" not in text


def test_export_holdout_gap_no_data(tmp_path):
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        {"vendor": "jubarte", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 90.0, "n_docs": 383},
    ])
    text = "\n".join(exp.holdout_gap_section(p))
    assert "## Holdout gap" in text
    assert "no holdout runs recorded" in text


def test_export_main_tables_drop_holdout_only_lines(tmp_path):
    # A holdout-only line must never enter the headline ranking tables.
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        {"vendor": "x", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 99.0, "n_docs": 20, "holdout_mode": "only"},
    ])
    assert exp.rows_from_jsonl(p) == []
