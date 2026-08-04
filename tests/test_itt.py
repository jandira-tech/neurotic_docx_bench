"""Intent-to-treat aggregation (PR2): failures count as 0, not as absences.

The completed-only aggregate rewards a tool for crashing on hard documents (the doc
falls out of the denominator). The ITT view scores every explicitly-failed doc as 0 so
means/medians are comparable across tools with different failure sets.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest

from neurotic_docx_bench.aggregate import compute_aggregate, compute_aggregate_itt
from neurotic_docx_bench.config import BenchConfig
from neurotic_docx_bench.results_schema import build_results


def test_itt_zeroes_failed_docs() -> None:
    agg = compute_aggregate_itt({"a": 100.0, "b": 50.0}, ["c"])
    assert agg.n_docs == 3
    assert agg.overall_mean == pytest.approx(50.0)
    assert agg.overall_median == pytest.approx(50.0)
    assert agg.below_50 == 1


def test_itt_dedupes_failure_docs() -> None:
    # One doc failing at two stages is still one document.
    agg = compute_aggregate_itt({"a": 100.0}, ["c", "c"])
    assert agg.n_docs == 2
    assert agg.overall_mean == pytest.approx(50.0)


def test_itt_scored_doc_keeps_its_score_despite_failure_entry() -> None:
    # A doc that scored but also has a failure record (e.g. a non-fatal stage error)
    # keeps its score — no zeroing, no double count.
    agg = compute_aggregate_itt({"a": 80.0}, ["a"])
    assert agg.n_docs == 1
    assert agg.overall_mean == pytest.approx(80.0)


def test_itt_total_wipeout_is_all_zeros() -> None:
    agg = compute_aggregate_itt({}, ["a", "b"])
    assert agg.n_docs == 2
    assert agg.overall_mean == 0.0
    assert agg.overall_median == 0.0


def test_itt_without_failures_equals_completed_aggregate() -> None:
    scores = {"a": 91.5, "b": 47.25, "c": 100.0}
    assert compute_aggregate_itt(scores, []) == compute_aggregate(scores)


def _build(scores: dict[str, float], failures: list[dict[str, str]], **kwargs):
    return build_results(
        id_run=uuid.uuid7(),
        vendor="docxodus",
        benchmark="script_redlines",
        scores=scores,
        per_doc=None,
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("corpus/oracle")),
        timestamp=datetime(2026, 8, 2, tzinfo=UTC),
        failures=failures,
        **kwargs,
    )


def test_build_results_emits_itt_fields() -> None:
    result = _build(
        {"a": 100.0, "b": 50.0},
        [
            {"doc": "c", "stage": "generate", "error": "boom"},
            {"doc": "c", "stage": "render", "error": "boom again"},
            {"doc": "d", "stage": "generate", "error": "boom"},
        ],
    )
    assert result.n_failures == 3
    assert result.itt_n_docs == 4  # a, b scored; c, d zeroed (c deduped)
    assert result.itt_mean == pytest.approx(37.5)
    assert result.itt_median == pytest.approx(25.0)
    line = result.to_json_dict()
    assert line["n_failures"] == 3
    assert line["itt_n_docs"] == 4
    assert line["itt_mean"] == pytest.approx(37.5)
    assert line["itt_median"] == pytest.approx(25.0)


def test_build_results_itt_equals_completed_when_clean() -> None:
    result = _build({"a": 90.0, "b": 70.0}, [])
    assert result.n_failures == 0
    assert result.itt_n_docs == result.n_docs == 2
    assert result.itt_mean == result.overall_mean
    assert result.itt_median == result.overall_median


def test_build_results_carries_oracle_unmatched_diagnostic() -> None:
    result = _build({"a": 90.0}, [], n_oracle_unmatched=7)
    assert result.n_oracle_unmatched == 7
    assert result.to_json_dict()["n_oracle_unmatched"] == 7
    # Default is None (not computable for this benchmark/run shape).
    assert _build({"a": 90.0}, []).n_oracle_unmatched is None


def test_failure_entry_without_doc_key_counts_once() -> None:
    # Defensive: malformed failure entries (no doc key) must not crash and must not
    # inflate the zero count per entry.
    agg = compute_aggregate_itt({"a": 100.0}, [""])
    assert agg.n_docs == 2
    assert agg.overall_mean == pytest.approx(50.0)
