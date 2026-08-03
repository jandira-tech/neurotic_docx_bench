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
from neurotic_docx_bench.emit import snapshot as snapshot_emit
from neurotic_docx_bench.gate import gate as run_gate

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
        app, ["run", "--config", str(cfg), "--results-dir", str(results_dir), "--runs-dir", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, result.output
    line = _script_lines()[-1]
    assert line["holdout_mode"] == "excluded"
    assert set(line["scores"]) == set(keys) - {holdout_key}

    # --holdout run: ONLY the holdout keys are scored, mode stamped "only".
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(results_dir), "--runs-dir", str(tmp_path / "runs"), "--holdout"],
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
            "--results-dir", str(tmp_path / "results"),
            "--runs-dir", str(tmp_path / "runs"), "--holdout",
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


# ── finding 1: gate must never mix corpus regimes ────────────────────────────


def test_gate_ignores_baseline_only_keys():
    # 403-era snapshot (contains the now-sealed docs) vs a 383-doc run: the
    # aggregate must compare the INTERSECTION, not punish the corpus change.
    base = {"a": 90.0, "b": 90.0, "sealed": 100.0}
    cur = {"a": 90.0, "b": 90.0}
    r = run_gate(cur, base)
    assert r.status == "pass"
    assert r.n_only_baseline == 1
    assert r.n_only_current == 0
    assert "baseline-only" in r.reason


def test_gate_ignores_current_only_keys():
    base = {"a": 90.0, "b": 90.0}
    cur = {"a": 90.0, "b": 90.0, "new_doc": 10.0}
    r = run_gate(cur, base)
    assert r.status == "pass"
    assert r.n_only_current == 1
    assert "current-only" in r.reason


def test_gate_intersection_regression_still_fails():
    base = {"a": 90.0, "b": 90.0, "sealed": 100.0}
    cur = {"a": 50.0, "b": 90.0}
    r = run_gate(cur, base)
    assert r.status == "fail"
    assert "aggregate regression" in r.reason


def test_gate_disjoint_key_sets_warn_not_fail():
    # No shared docs at all: the aggregate is not comparable — surface it
    # loudly (warn) instead of manufacturing a spurious pass or fail.
    r = run_gate({"a": 10.0}, {"x": 100.0})
    assert r.status == "warn"
    assert "no shared docs" in r.reason


def test_gate_total_wipeout_fails_not_warns():
    # Empty current scores vs a non-empty baseline is a regression (the tool
    # crashed on everything), NOT corpus drift — the disjoint-warn branch must
    # not let it through at exit 0.
    r = run_gate({}, {"a": 90.0, "b": 85.0})
    assert r.status == "fail"
    assert "wipeout" in r.reason


def _degraded_holdout_setup(tmp_path, sample_oracle_pdfs):
    """Synthetic corpus where the HOLDOUT key scores < 100 (oracle A vs
    candidate B) and the visible key mirrors (scores 100)."""
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    pdf_a, pdf_b = sample_oracle_pdfs
    key_hold = pipeline.oracle_pair_key(pdf_a.stem)
    key_vis = pipeline.oracle_pair_key(pdf_b.stem)
    shutil.copy(pdf_a, oracle / f"{key_hold}_redline.pdf")
    shutil.copy(pdf_b, cand / f"{key_hold}_t_redline.pdf")  # mismatched → < 100
    shutil.copy(pdf_b, oracle / f"{key_vis}_redline.pdf")
    shutil.copy(pdf_b, cand / f"{key_vis}_t_redline.pdf")  # mirrored → 100
    hold = tmp_path / "holdout.txt"
    hold.write_text(f"# test holdout\n{key_hold}\n")
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        f"holdout_list: {hold}\n"
        "runs:\n"
        f"  - {{name: t, render: passthrough, modified: {cand}, "
        "unversioned: true, vendor: t, jobs: 1}\n",
    )
    return cfg, key_hold, key_vis


def test_cli_holdout_run_is_never_gated(tmp_path, sample_oracle_pdfs):
    # A full-corpus snapshot exists; the holdout-only line must be reported as
    # a diagnostic and never compared against it (no FAIL exit, no gate line).
    cfg, _key_hold, key_vis = _degraded_holdout_setup(tmp_path, sample_oracle_pdfs)
    results_dir = tmp_path / "results"
    snapshot_emit.write_snapshot_for_benchmark(
        results_dir / "score-snapshots", "t", "script_redlines", {key_vis: 100.0},
    )
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(results_dir), "--holdout"],
    )
    assert result.exit_code == 0, result.output
    assert "never gated" in result.output


# ── finding 2: accept-scores must never promote a holdout-only line ──────────


def test_last_line_for_benchmark_skips_holdout_only_by_default(tmp_path):
    p = tmp_path / "bench.jsonl"
    full = {"vendor": "v", "benchmark": "script_redlines", "scores": {"a": 90.0}}
    hold = {
        "vendor": "v", "benchmark": "script_redlines",
        "scores": {"h": 50.0}, "holdout_mode": "only",
    }
    _write_jsonl(p, [full, hold])
    picked = jsonl.last_line_for_benchmark(p, "v", "script_redlines")
    assert picked is not None and picked["scores"] == {"a": 90.0}
    only = jsonl.last_line_for_benchmark(p, "v", "script_redlines", holdout_only=True)
    assert only is not None and only["scores"] == {"h": 50.0}
    any_line = jsonl.last_line_for_benchmark(p, "v", "script_redlines", holdout_only=None)
    assert any_line is not None and any_line["scores"] == {"h": 50.0}


def test_accept_scores_promotes_full_line_not_holdout(tmp_path):
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    _write_jsonl(results_dir / "bench.jsonl", [
        {"vendor": "v", "benchmark": "script_redlines", "scores": {"a": 90.0}},
        {"vendor": "v", "benchmark": "script_redlines",
         "scores": {"h": 50.0}, "holdout_mode": "only"},
    ])
    result = runner.invoke(app, ["accept-scores", "v", "--results-dir", str(results_dir)])
    assert result.exit_code == 0, result.output
    snap = json.loads(
        (results_dir / "score-snapshots" / "v__script_redlines.json").read_text(),
    )
    assert snap == {"a": 90.0}


# ── finding 3: ITT universe must match the scoring universe ──────────────────


def test_filter_failure_records_excluded_direction():
    failures = [
        {"doc": "sealed_pair", "stage": "generate", "error": "x"},
        {"doc": "visible_pair", "stage": "render", "error": "y"},
    ]
    out = pipeline.filter_failure_records(failures, exclude_keys={"sealed_pair"})
    assert out == [{"doc": "visible_pair", "stage": "render", "error": "y"}]


def test_filter_failure_records_only_direction():
    failures = [
        {"doc": "sealed_pair", "stage": "generate", "error": "x"},
        {"doc": "visible_pair", "stage": "render", "error": "y"},
    ]
    out = pipeline.filter_failure_records(failures, only_keys={"sealed_pair"})
    assert out == [{"doc": "sealed_pair", "stage": "generate", "error": "x"}]


def test_filter_failure_records_both_filters_raise():
    with pytest.raises(ValueError, match="mutually exclusive"):
        pipeline.filter_failure_records([], exclude_keys={"a"}, only_keys={"b"})


def _generate_run_setup(tmp_path, sample_oracle_pdfs, *, cand_key_idx, fail_key_idx):
    """A generate-based passthrough run: the generate command copies ONE
    candidate PDF into $RUN_DIR/docx and records the OTHER key as a generate
    failure — so failures and scores land on opposite sides of the seal."""
    oracle = tmp_path / "oracle"
    oracle.mkdir()
    keys, pdfs = [], {}
    for p in sample_oracle_pdfs:
        key = pipeline.oracle_pair_key(p.stem)
        shutil.copy(p, oracle / f"{key}_redline.pdf")
        keys.append(key)
        pdfs[key] = p
    keys = sorted(keys)
    holdout_key = keys[0]
    hold = tmp_path / "holdout.txt"
    hold.write_text(f"# test holdout\n{holdout_key}\n")

    cand_key = keys[cand_key_idx]
    fail_key = keys[fail_key_idx]
    fail_json = tmp_path / "generate_failures.json"
    fail_json.write_text(json.dumps(
        [{"doc": fail_key, "stage": "generate", "error": "boom"}],
    ))
    gen_cmd = (
        f"cp {pdfs[cand_key]} $RUN_DIR/docx/{cand_key}_t_redline.pdf"
        f" && cp {fail_json} $RUN_DIR/generate_failures.json"
    )
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        f"holdout_list: {hold}\n"
        "runs:\n"
        "  - name: t\n"
        "    render: passthrough\n"
        "    vendor: t\n"
        "    unversioned: true\n"
        "    jobs: 1\n"
        f"    generate: {gen_cmd}\n",
    )
    return cfg, holdout_key, keys


def _last_script_line(results_dir: Path) -> dict:
    lines = [
        json.loads(raw)
        for raw in (results_dir / "bench.jsonl").read_text().splitlines()
        if raw.strip()
    ]
    return [x for x in lines if x.get("benchmark") == "script_redlines"][-1]


def test_cli_itt_excludes_sealed_failures_on_normal_run(tmp_path, sample_oracle_pdfs):
    # Sealed doc fails generation; visible doc scores. The excluded-mode line
    # must not carry the sealed failure — ITT is over the visible universe.
    cfg, _holdout_key, keys = _generate_run_setup(
        tmp_path, sample_oracle_pdfs, cand_key_idx=1, fail_key_idx=0,
    )
    results_dir = tmp_path / "results"
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(results_dir),
         "--runs-dir", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, result.output
    line = _last_script_line(results_dir)
    assert line["holdout_mode"] == "excluded"
    assert set(line["scores"]) == {keys[1]}
    assert line["failures"] == []
    assert line["itt_n_docs"] == 1
    assert line["itt_mean"] == pytest.approx(100.0, abs=1e-3)
    assert line["n_oracle_unmatched"] == 0


def test_cli_holdout_itt_excludes_visible_failures(tmp_path, sample_oracle_pdfs):
    # Visible doc fails generation; sealed doc scores. The holdout-only line
    # must not absorb the visible failure into its ITT stats.
    cfg, holdout_key, _keys = _generate_run_setup(
        tmp_path, sample_oracle_pdfs, cand_key_idx=0, fail_key_idx=1,
    )
    results_dir = tmp_path / "results"
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(results_dir),
         "--runs-dir", str(tmp_path / "runs"), "--holdout"],
    )
    assert result.exit_code == 0, result.output
    line = _last_script_line(results_dir)
    assert line["holdout_mode"] == "only"
    assert set(line["scores"]) == {holdout_key}
    assert line["failures"] == []
    assert line["itt_n_docs"] == 1
    assert line["n_oracle_unmatched"] == 0


# ── finding 4: export ranking — recency wins within the full-corpus bucket ───


def test_export_rank_newest_full_line_wins_over_bigger_stale_line(tmp_path):
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 95.0, "n_docs": 403, "scores": {"a": 95.0},
         "timestamp": "2026-01-01T00:00:00+00:00"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 90.0, "n_docs": 383, "scores": {"a": 90.0},
         "timestamp": "2026-06-01T00:00:00+00:00"},
    ])
    rows = exp.rows_from_jsonl(p)
    assert len(rows) == 1
    assert rows[0]["mean"] == 90.0
    assert rows[0]["n_docs"] == 383


def test_export_rank_full_line_still_beats_newer_smoke(tmp_path):
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 90.0, "n_docs": 383,
         "timestamp": "2026-01-01T00:00:00+00:00"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 99.0, "n_docs": 20,
         "timestamp": "2026-06-01T00:00:00+00:00"},
    ])
    rows = exp.rows_from_jsonl(p)
    assert len(rows) == 1
    assert rows[0]["mean"] == 90.0
    assert rows[0]["n_docs"] == 383


# ── findings 5+6: holdout-gap main selection + uncertainty ───────────────────


def test_export_holdout_gap_main_same_version_excluded_full_only(tmp_path):
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        # pre-holdout 403-doc line for the SAME version — contains the sealed
        # docs, must never be "main"
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 99.0, "n_docs": 403},
        # excluded line for a DIFFERENT version — must not be "main" either
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 80.0, "n_docs": 383, "holdout_mode": "excluded"},
        # the genuine main: same version, excluded, full corpus
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 90.0, "n_docs": 383, "holdout_mode": "excluded"},
        # a smoke excluded line for the same version (n ≤ 100) — not "main"
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 70.0, "n_docs": 5, "holdout_mode": "excluded"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 85.0, "n_docs": 20, "holdout_mode": "only"},
    ])
    text = "\n".join(exp.holdout_gap_section(p))
    assert "-5.00" in text  # 85 − 90, not 85 − 99 / 85 − 80 / 85 − 70
    assert "no comparable main run" not in text


def test_export_holdout_gap_smoke_holdout_line_does_not_displace_full(tmp_path):
    # A later --holdout --limit smoke run (n=3) must not displace the fuller
    # holdout line (n=20) as the vendor's holdout number; recency applies only
    # among equally-full holdout lines.
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 90.0, "n_docs": 383, "holdout_mode": "excluded"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 85.0, "n_docs": 20, "holdout_mode": "only"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 40.0, "n_docs": 3, "holdout_mode": "only"},
    ])
    text = "\n".join(exp.holdout_gap_section(p))
    assert "-5.00" in text  # 85 − 90 from the n=20 line, not 40 − 90
    assert "-50.00" not in text


def test_export_holdout_gap_no_comparable_main(tmp_path):
    p = tmp_path / "bench.jsonl"
    _write_jsonl(p, [
        # only a different-version full line and a same-version smoke line exist
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 90.0, "n_docs": 383, "holdout_mode": "excluded"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 88.0, "n_docs": 2, "holdout_mode": "excluded"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "2",
         "overall_mean": 85.0, "n_docs": 20, "holdout_mode": "only"},
    ])
    text = "\n".join(exp.holdout_gap_section(p))
    assert "no comparable main run" in text


def test_export_holdout_gap_shows_n_and_uncertainty(tmp_path):
    p = tmp_path / "bench.jsonl"
    hold_scores = {f"d{i}": 80.0 + i for i in range(4)}
    _write_jsonl(p, [
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 90.0, "n_docs": 383, "holdout_mode": "excluded"},
        {"vendor": "v", "benchmark": "script_redlines", "tool_version": "1",
         "overall_mean": 81.5, "n_docs": 4, "holdout_mode": "only",
         "scores": hold_scores},
    ])
    text = "\n".join(exp.holdout_gap_section(p))
    assert "n_main" in text
    assert "n_holdout" in text
    assert "383" in text
    assert "±" in text  # gap carries 2·SE from the holdout per-doc scores
    assert "noise" in text  # footnote: |gap| below ~2·SE is noise


# ── finding 7: filter keys that match nothing must be loud ───────────────────


def test_score_folders_full_unknown_exclude_key_raises(tmp_path, sample_oracle_pdfs):
    oracle, cand, keys = _mirrored_pair_dirs(tmp_path, sample_oracle_pdfs)
    with pytest.raises(ValueError, match="nope_key"):
        pipeline.score_folders_full(
            oracle, cand, tmp_path / "work", jobs=1, candidate_tool="t",
            exclude_keys={keys[0], "nope_key"},
        )


def test_score_folders_full_unknown_only_key_raises(tmp_path, sample_oracle_pdfs):
    oracle, cand, keys = _mirrored_pair_dirs(tmp_path, sample_oracle_pdfs)
    with pytest.raises(ValueError, match="nope_key"):
        pipeline.score_folders_full(
            oracle, cand, tmp_path / "work", jobs=1, candidate_tool="t",
            only_keys={keys[0], "nope_key"},
        )


def test_score_folders_full_lenient_keys_for_subset_oracles(tmp_path, sample_oracle_pdfs):
    # Secondary benchmarks (accepted/visual corpora) legitimately cover a
    # subset of the holdout sampling universe — strict_filter_keys=False
    # tolerates keys absent from THIS oracle while still filtering the rest.
    oracle, cand, keys = _mirrored_pair_dirs(tmp_path, sample_oracle_pdfs)
    full = pipeline.score_folders_full(
        oracle, cand, tmp_path / "work", jobs=1, candidate_tool="t",
        exclude_keys={keys[0], "not_in_this_universe"}, strict_filter_keys=False,
    )
    assert set(full) == set(keys) - {keys[0]}


# ── finding 8: the seal covers accepted/visual paths; stamps stay truthful ───


def _mirrored_accepted_dirs(tmp_path, sample_oracle_pdfs):
    """Accepted-changes pairing: oracle ``<key>_word_redline_accepted.pdf`` vs
    candidate ``<key>_redline.pdf`` (both map to the ``<key>`` pair key)."""
    oracle = tmp_path / "acc_oracle"
    cand = tmp_path / "acc_cand"
    oracle.mkdir()
    cand.mkdir()
    keys = []
    for p in sample_oracle_pdfs:
        key = pipeline.oracle_pair_key(p.stem)
        shutil.copy(p, oracle / f"{key}_word_redline_accepted.pdf")
        shutil.copy(p, cand / f"{key}_redline.pdf")
        keys.append(key)
    return oracle, cand, sorted(keys)


def test_score_folders_accepted_exclude_and_only(tmp_path, sample_oracle_pdfs):
    oracle, cand, keys = _mirrored_accepted_dirs(tmp_path, sample_oracle_pdfs)
    excluded = pipeline.score_folders_accepted(
        oracle, cand, tmp_path / "w1", jobs=1, exclude_keys={keys[0]},
    )
    assert set(excluded) == set(keys) - {keys[0]}
    only = pipeline.score_folders_accepted(
        oracle, cand, tmp_path / "w2", jobs=1, only_keys={keys[0]},
    )
    assert set(only) == {keys[0]}


def test_accept_compare_stage_filters_sealed_keys(tmp_path, sample_oracle_pdfs, monkeypatch):
    from neurotic_docx_bench import accept_changes
    from neurotic_docx_bench import cli as cli_mod
    from neurotic_docx_bench.config import RunConfig
    from neurotic_docx_bench.render.base import RenderReport

    oracle, cand, keys = _mirrored_pair_dirs(tmp_path, sample_oracle_pdfs)
    sealed = keys[0]
    monkeypatch.setattr(accept_changes, "process_folder", lambda *a, **k: [])

    class _FakeRenderer:
        def to_pdfs(self, source_dir, work_dir, **kw):
            return RenderReport(pdf_dir=cand, results=[])

    monkeypatch.setattr(cli_mod, "SofficeRenderer", _FakeRenderer)
    rc = RunConfig(name="t", render="soffice", vendor="t", jobs=1)

    run1 = tmp_path / "run1"
    run1.mkdir()
    outcome = cli_mod._accept_compare_stage(
        rc, run1, cand, {}, oracle, 72,
        exclude_keys={sealed}, only_keys=None,
    )
    assert set(outcome.scores) == set(keys) - {sealed}

    run2 = tmp_path / "run2"
    run2.mkdir()
    outcome_only = cli_mod._accept_compare_stage(
        rc, run2, cand, {}, oracle, 72,
        exclude_keys=None, only_keys={sealed},
    )
    assert set(outcome_only.scores) == {sealed}


def _visual_run_cfg(tmp_path, sample_oracle_pdfs, *, visual_benchmark):
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
    keys = sorted(keys)
    hold = tmp_path / "holdout.txt"
    hold.write_text(f"# test holdout\n{keys[0]}\n")
    extra = ""
    if visual_benchmark == "visual_rendering":
        # plain-stem matcher: the vis oracle mirrors the candidate FILENAMES
        vis_dir = tmp_path / "vis_oracle"
        vis_dir.mkdir()
        for f in cand.glob("*.pdf"):
            shutil.copy(f, vis_dir / f.name)
        extra = f"visual_oracles:\n  visual_rendering: {vis_dir}\n"
    cfg = tmp_path / "bench.yaml"
    cfg.write_text(
        f"source_of_truth: {oracle}\n"
        f"holdout_list: {hold}\n"
        f"{extra}"
        "runs:\n"
        "  - name: t\n"
        "    render: passthrough\n"
        f"    modified: {cand}\n"
        "    vendor: t\n"
        "    unversioned: true\n"
        "    jobs: 1\n"
        f"    benchmarks: [script_redlines, {visual_benchmark}]\n",
    )
    return cfg, keys


def _lines_for_benchmark(results_dir: Path, benchmark: str) -> list[dict]:
    lines = [
        json.loads(raw)
        for raw in (results_dir / "bench.jsonl").read_text().splitlines()
        if raw.strip()
    ]
    return [x for x in lines if x.get("benchmark") == benchmark]


def test_cli_visual_redlines_lines_respect_the_seal(tmp_path, sample_oracle_pdfs):
    cfg, keys = _visual_run_cfg(
        tmp_path, sample_oracle_pdfs, visual_benchmark="visual_redlines",
    )
    results_dir = tmp_path / "results"
    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(results_dir),
         "--runs-dir", str(tmp_path / "runs")],
    )
    assert result.exit_code == 0, result.output
    line = _lines_for_benchmark(results_dir, "visual_redlines")[-1]
    assert line["holdout_mode"] == "excluded"
    assert set(line["scores"]) == set(keys) - {keys[0]}

    result = runner.invoke(
        app,
        ["run", "--config", str(cfg), "--results-dir", str(results_dir),
         "--runs-dir", str(tmp_path / "runs"), "--holdout"],
    )
    assert result.exit_code == 0, result.output
    line = _lines_for_benchmark(results_dir, "visual_redlines")[-1]
    assert line["holdout_mode"] == "only"
    assert set(line["scores"]) == {keys[0]}


def test_cli_visual_rendering_unfilterable_stamps_none(tmp_path, sample_oracle_pdfs):
    # visual_rendering is keyed by plain doc stems, not pair keys — the seal
    # cannot filter it, so its stamp must be None (truthful) and the line must
    # survive the headline-table filter even on a --holdout run.
    cfg, keys = _visual_run_cfg(
        tmp_path, sample_oracle_pdfs, visual_benchmark="visual_rendering",
    )
    results_dir = tmp_path / "results"
    for extra_args in ([], ["--holdout"]):
        result = runner.invoke(
            app,
            ["run", "--config", str(cfg), "--results-dir", str(results_dir),
             "--runs-dir", str(tmp_path / "runs"), *extra_args],
        )
        assert result.exit_code == 0, result.output
        line = _lines_for_benchmark(results_dir, "visual_rendering")[-1]
        assert line["holdout_mode"] is None
        assert len(line["scores"]) == len(keys)
    rows = exp.rows_from_jsonl(results_dir / "bench.jsonl")
    assert any(r["benchmark"] == "visual_rendering" for r in rows)
