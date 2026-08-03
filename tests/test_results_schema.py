"""Tests for typed benchmark results schema (Task 1)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench.benchmarks import BENCHMARKS
from neurotic_docx_bench.config import BenchConfig
from neurotic_docx_bench.results_schema import (
    Results,
    aggregate_speed,
    build_results,
    score_config_metadata,
)


def test_benchmark_names_are_exact() -> None:
    assert BENCHMARKS == (
        "accepted_changes",
        "script_redlines",
        "roundtrip",
        "visual_rendering",
        "visual_redlines",
        "visual_accepted_changes",
    )


def test_score_config_metadata_mirrors_score_py_defaults() -> None:
    meta = score_config_metadata()
    assert meta.max_shift_px == 5.0
    assert meta.align_upsample == 10
    assert meta.weights.ssim_full == 0.25
    assert meta.weights.blob_sim == 0.1


def test_speed_stats_known_vector() -> None:
    stats = aggregate_speed([10.0, 20.0, 30.0, 40.0])
    assert stats.overall_mean_speed == 25.0
    assert stats.overall_median_speed == 25.0
    assert stats.min_speed == 10.0
    assert stats.max_speed == 40.0
    assert stats.q1_speed == 17.5
    assert stats.q3_speed == 32.5


def test_build_results_serializes_paths_and_uuid7() -> None:
    cfg = BenchConfig(source_of_truth=Path("corpus/oracle"))
    rid = uuid.uuid7()
    result = build_results(
        id_run=rid,
        vendor="docxodus",
        benchmark="script_redlines",
        scores={"a": 100.0, "b": 80.0},
        per_doc=None,
        speed_samples_ms=[5.0, 7.0],
        environment_config=cfg,
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
    )
    assert isinstance(result, Results)
    assert result.id_run == rid
    assert result.n_docs == 2
    assert result.overall_mean == 90.0
    line = result.to_json_dict()
    assert line["id_run"] == str(rid)
    assert line["vendor"] == "docxodus"
    assert line["benchmark"] == "script_redlines"
    assert line["environment_config"]["source_of_truth"] == "corpus/oracle"


def test_build_results_serializes_tuple_of_paths() -> None:
    """Regression: extra_oracle_dirs is a tuple of Paths — asdict() keeps
    tuples as tuples, so _jsonable must recurse into them or json.dumps
    dies with "Object of type PosixPath is not JSON serializable" on the
    first emitted line (which is exactly how the 2026-08-03 run failed)."""
    import json

    cfg = BenchConfig(
        source_of_truth=Path("corpus/oracle"),
        extra_oracle_dirs=(Path("corpus/word_based/pdf_redlines_randomized/pdf"),),
    )
    result = build_results(
        id_run=uuid.uuid7(),
        vendor="docxodus",
        benchmark="script_redlines",
        scores={"a": 100.0},
        per_doc=None,
        speed_samples_ms=[5.0],
        environment_config=cfg,
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
    )
    line = result.to_json_dict()
    json.dumps(line)  # must not raise
    assert line["environment_config"]["extra_oracle_dirs"] == [
        "corpus/word_based/pdf_redlines_randomized/pdf"
    ]


def test_build_results_empty_scores_zero_aggregate() -> None:
    cfg = BenchConfig(source_of_truth=Path("oracle"))
    result = build_results(
        id_run=uuid.uuid7(),
        vendor="test",
        benchmark="roundtrip",
        scores={},
        per_doc=None,
        speed_samples_ms=[],
        environment_config=cfg,
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
    )
    assert result.n_docs == 0
    assert result.overall_mean == 0.0


def test_uuid_not_v7_raises() -> None:
    from neurotic_docx_bench.results_schema import ScoreConfigMetadata, ScoreWeightsMetadata

    try:
        Results(
            id_run=uuid.uuid4(),
            vendor="test",
            benchmark="script_redlines",
            n_docs=0,
            overall_mean=0.0,
            overall_median=0.0,
            exact_100=0,
            at_least_90=0,
            below_50=0,
            min=0.0,
            max=0.0,
            std=0.0,
            q1=0.0,
            q3=0.0,
            page_mean=None,
            page_median=None,
            overall_mean_speed=0.0,
            overall_median_speed=0.0,
            min_speed=0.0,
            max_speed=0.0,
            std_speed=0.0,
            q1_speed=0.0,
            q3_speed=0.0,
            score_config=ScoreConfigMetadata(
                max_shift_px=5.0, align_upsample=10, downscale_factor=0.25,
                edge_sigma=1.2, edge_dilate=1, ink_min_size=24, ink_tol_px=2.0,
                drift_sigma=2.0, min_drift_px=1.0, single_issue_cap=30.0,
                single_issue_min_gain=15.0, single_issue_min_ssim_small=0.7,
                single_issue_min_ink_f1=0.65, single_issue_min_edge_iou=0.5,
                single_issue_max_blob_penalty=0.03, color_deltaE_max=20.0,
                blob_min_size=40,
                weights=ScoreWeightsMetadata(ssim_full=0.25, ssim_small=0.15,
                    ink_f1=0.2, edge_iou=0.15, color_sim=0.15, blob_sim=0.1),
            ),
            environment_config=BenchConfig(source_of_truth=Path("oracle")),
        )
    except ValueError as exc:
        assert "UUIDv7" in str(exc)
    else:
        raise AssertionError("expected ValueError for non-v7 UUID")


def test_empty_speed_samples() -> None:
    stats = aggregate_speed([])
    assert stats.overall_mean_speed == 0.0
    assert stats.overall_median_speed == 0.0


def test_build_results_carries_render_timings_to_speed_stats() -> None:
    """A visual_* outcome's ``render_s`` timings flow through to the emitted line's
    speed stats (``overall_mean_speed``) and the embedded ``timings`` dict — the gap
    that previously left visual_* lines at 0.0 speed. ``speed_samples_ms`` is derived
    from ``timings`` by ``_emit_and_gate_benchmark`` via ``speed_samples_from_timings``.
    """
    from neurotic_docx_bench.emit.jsonl import build_results_line
    from neurotic_docx_bench.stages import speed_samples_from_timings

    cfg = BenchConfig(source_of_truth=Path("oracle"))
    timings = {"a_b": {"render_s": 0.012}, "c_d": {"render_s": 0.034}}
    samples = speed_samples_from_timings(timings, "render_s")
    line = build_results_line(
        id_run=uuid.uuid7(),
        vendor="folio",
        benchmark="visual_redlines",
        scores={"a_b": 90.0, "c_d": 80.0},
        per_doc=None,
        speed_samples_ms=samples,
        environment_config=cfg,
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
        timings=timings,
    )
    assert line["timings"] == timings
    # mean of {12, 34} ms == 23.0
    assert line["overall_mean_speed"] == 23.0
    assert line["overall_median_speed"] == 23.0
    assert line["min_speed"] == 12.0 and line["max_speed"] == 34.0
