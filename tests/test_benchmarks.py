"""Tests for benchmark names and outcomes (Task 2)."""

from __future__ import annotations

from neurotic_docx_bench.benchmarks import (
    BenchmarkOutcome,
    benchmark_for_legacy_stage,
    default_benchmarks_for_vendor,
)


def test_legacy_stage_mapping() -> None:
    assert benchmark_for_legacy_stage("redline") == "script_redlines"
    assert benchmark_for_legacy_stage("accepted") == "accepted_changes"
    assert benchmark_for_legacy_stage("roundtrip") == "roundtrip"
    assert benchmark_for_legacy_stage("render-original") == "visual_rendering"
    assert benchmark_for_legacy_stage("render-redline") == "visual_redlines"
    assert benchmark_for_legacy_stage("render-accepted") == "visual_accepted_changes"


def test_vendor_defaults() -> None:
    assert default_benchmarks_for_vendor("docxodus") == [
        "accepted_changes",
        "script_redlines",
        "roundtrip",
        "visual_rendering",
        "visual_redlines",
        "visual_accepted_changes",
    ]
    assert default_benchmarks_for_vendor("jubarte-final-lossless") == [
        "accepted_changes",
        "script_redlines",
        "roundtrip",
    ]


def test_outcome_speed_samples_are_milliseconds() -> None:
    outcome = BenchmarkOutcome(
        benchmark="script_redlines",
        scores={"a": 100.0},
        per_doc=None,
        failures=[],
        speed_samples_ms=[12.5],
    )
    assert outcome.speed_samples_ms == [12.5]


def test_unknown_legacy_stage_raises() -> None:
    try:
        benchmark_for_legacy_stage("bogus")
    except ValueError as exc:
        assert "unknown benchmark stage" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_folio_defaults_cover_five_of_six_benchmarks() -> None:
    # folio covers 5/6 benchmarks across two runs:
    #  - script_redlines + accepted_changes + roundtrip via the `folio` run
    #    (loadEngine('folio') adapter + accept_changes + generate-roundtrips folio route)
    #  - visual_rendering + visual_redlines + visual_accepted_changes via
    #    folio-playwright (@stll/folio-react renderAsync harness)
    folio_benchmarks = default_benchmarks_for_vendor("folio")
    assert "script_redlines" in folio_benchmarks
    assert "accepted_changes" in folio_benchmarks
    assert "roundtrip" in folio_benchmarks
    assert "visual_rendering" in folio_benchmarks
    assert "visual_redlines" in folio_benchmarks
    assert "visual_accepted_changes" in folio_benchmarks


def test_unknown_vendor_gets_script_redlines_only() -> None:
    assert default_benchmarks_for_vendor("unknown-tool") == ["script_redlines"]
