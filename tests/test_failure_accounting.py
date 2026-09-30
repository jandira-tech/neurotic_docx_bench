"""A document is scored or failed, never both in the published counts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench.aggregate import compute_aggregate_itt, failed_doc_keys
from neurotic_docx_bench.config import BenchConfig
from neurotic_docx_bench.results_schema import build_results


def _results(**over):
    args = {
        "id_run": uuid.uuid7(),
        "vendor": "acme",
        "benchmark": "script_redlines",
        "scores": {"a": 100.0, "b": 90.0, "c": 50.0},
        "per_doc": None,
        "speed_samples_ms": [1.0],
        "environment_config": BenchConfig(source_of_truth=Path("oracle")),
        "timestamp": datetime(2026, 9, 27, tzinfo=UTC),
        "failures": [
            {"doc": "d", "stage": "generate", "error": "boom"},
            {"doc": "c", "stage": "render", "error": "warning only"},
        ],
    }
    args.update(over)
    return build_results(**args)


def test_failed_doc_keys_excludes_scored_docs() -> None:
    assert failed_doc_keys({"c": 50.0}, ["d", "c", "d"]) == {"d"}


def test_itt_uses_failed_doc_keys() -> None:
    agg = compute_aggregate_itt({"c": 50.0}, ["d", "c"])
    assert agg.n_docs == 2 and agg.overall_mean == 25.0


def test_results_carry_both_counts() -> None:
    r = _results()
    assert r.n_failure_events == 2
    assert r.n_failed_docs == 1
    assert r.n_failures == 2  # legacy field keeps its old meaning for old readers
    assert r.n_docs + r.n_failed_docs == r.itt_n_docs == 4


def test_new_provenance_fields_default_to_none_and_serialize() -> None:
    r = _results()
    d = r.to_json_dict()
    for key in ("tool_id", "configuration", "docset_id", "renderer_id", "hardware"):
        assert key in d and d[key] is None
    assert d["n_failed_docs"] == 1 and d["n_failure_events"] == 2


def test_provenance_fields_round_trip() -> None:
    r = _results(
        tool_id="acme",
        configuration="fast",
        docset_id="abc123abc123",
        renderer_id="soffice-26.2.4.2",
        hardware={"cpu": "Apple M3", "cores": 12},
    )
    d = r.to_json_dict()
    assert d["tool_id"] == "acme" and d["configuration"] == "fast"
    assert d["docset_id"] == "abc123abc123" and d["renderer_id"] == "soffice-26.2.4.2"
    assert d["hardware"] == {"cpu": "Apple M3", "cores": 12}
