"""bench.jsonl lines normalize to ResultRow with honest failure counts and ITT."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import load_registry


@pytest.fixture
def registry(tmp_path: Path):
    doc = {
        "schema_version": 1,
        "tools": [
            {
                "id": "docxodus",
                "vendor": "docxodus",
                "display": "docxodus",
                "role": "generator",
                "engine": "docxodus",
                "run_names": ["docxodus"],
                "bench_vendors": ["docxodus"],
            },
            {
                "id": "jubarte-ast",
                "vendor": "jubarte",
                "display": "jubarte (ast)",
                "role": "generator",
                "engine": "jubarte-final",
                "affiliated": True,
                "configuration": "ast",
                "run_names": ["jubarte-final-native"],
                "bench_vendors": ["jubarte-ast"],
            },
            {
                "id": "jubarte-lossless",
                "vendor": "jubarte",
                "display": "jubarte (lossless)",
                "role": "generator",
                "engine": "jubarte-final",
                "affiliated": True,
                "run_names": ["jubarte-final-lossless"],
                "bench_vendors": ["jubarte"],
            },
        ],
    }
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def _line(**over) -> dict:
    base = {
        "id_run": "019ff85b-23fd-7450-9744-5669ef0d3c1e",
        "vendor": "docxodus",
        "benchmark": "script_redlines",
        "n_docs": 3,
        "overall_mean": 80.0,
        "overall_median": 90.0,
        "exact_100": 1,
        "scores": {"a": 100.0, "b": 90.0, "c": 50.0},
        "failures": [
            {"doc": "d", "stage": "generate", "error": "x"},
            {"doc": "c", "stage": "render", "error": "non-fatal"},
        ],
        "tool_version": "9.8.0",
        "timestamp": "2026-08-12T23:42:30.000000+00:00",
        "corpus_revision": "5ed816028d99",
        "scorer": "pagefair-v2",
        "environment_config": {"runs": [{"name": "docxodus", "render": "soffice"}]},
    }
    base.update(over)
    return base


def test_failed_docs_exclude_docs_that_also_scored(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None
    assert row.n_scored == 3
    assert row.n_failure_events == 2
    assert row.n_failed_docs == 1  # only "d" is zeroed
    assert row.failed_docs == ("d",)
    assert row.itt_n == 4  # 3 scored + 1 zeroed
    assert row.n_scored + row.n_failed_docs == row.itt_n
    assert row.itt_scores() == {"a": 100.0, "b": 90.0, "c": 50.0, "d": 0.0}
    assert row.key == "019ff85b-23fd-7450-9744-5669ef0d3c1e|script_redlines"


def test_emitted_itt_fields_win_over_recomputation(registry) -> None:
    row = rws.row_from_bench_line(
        _line(itt_n_docs=4, itt_mean=60.0, itt_median=70.0), registry
    )
    assert row is not None
    assert (row.itt_n, row.itt_mean, row.itt_median) == (4, 60.0, 70.0)
    assert row.itt_approx is False


def test_itt_recomputed_from_scores_when_not_emitted(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None
    assert row.itt_n == 4
    assert row.itt_median == 70.0  # median of [100, 90, 50, 0]
    assert row.itt_mean == 60.0
    assert row.itt_approx is False


def test_legacy_line_without_scores_is_approximate(registry) -> None:
    row = rws.row_from_bench_line(_line(scores={}, corpus_revision=None), registry)
    assert row is not None
    assert row.itt_approx is True
    assert row.provenance == "legacy"


def test_stamped_line_with_scores_is_stamped(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None and row.provenance == "stamped"


def test_tool_id_uses_run_name_before_vendor(registry) -> None:
    line = _line(
        vendor="jubarte",
        environment_config={
            "runs": [{"name": "jubarte-final-native", "render": "soffice"}]
        },
    )
    row = rws.row_from_bench_line(line, registry)
    assert row is not None and row.tool_id == "jubarte-ast"
    assert row.affiliated is True


def _ghost(**over) -> dict:
    return _line(
        vendor="ghost",
        environment_config={"runs": [{"name": "ghost", "render": "soffice"}]},
        **over,
    )


def test_unknown_vendor_and_run_name_returns_none(registry) -> None:
    assert rws.row_from_bench_line(_ghost(), registry) is None


def test_known_run_name_wins_over_unknown_vendor(registry) -> None:
    row = rws.row_from_bench_line(_line(vendor="ghost"), registry)
    assert row is not None and row.tool_id == "docxodus"


def test_unknown_benchmark_returns_none(registry) -> None:
    assert rws.row_from_bench_line(_line(benchmark="not_a_bench"), registry) is None


def test_load_bench_rows_reports_unmapped(tmp_path: Path, registry) -> None:
    p = tmp_path / "bench.jsonl"
    p.write_text(json.dumps(_line()) + "\n" + json.dumps(_ghost()) + "\n" + "\n")
    rows, unmapped = rws.load_bench_rows(p, registry)
    assert [r.tool_id for r in rows] == ["docxodus"]
    assert [u["vendor"] for u in unmapped] == ["ghost"]


def test_pin_and_render_and_run_name_are_carried(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None
    assert row.pin.display == "9.8.0"
    assert row.render == "soffice"
    assert row.run_name == "docxodus"
    assert row.timestamp.year == 2026



def test_repeated_failure_events_zero_each_unscored_document_once(registry) -> None:
    row = rws.row_from_bench_line(
        _line(
            n_docs=999,
            scores={"scored": 100, "zero-score": 0},
            failures=[
                {"doc": "missing", "stage": "generate"},
                {"doc": "missing", "stage": "render"},
                {"doc": "scored", "stage": "render"},
                {"doc": "zero-score", "stage": "render"},
                {},
                {"doc": ""},
                "malformed event",
                None,
            ],
        ),
        registry,
    )
    assert row is not None
    assert (row.n_scored, row.n_failed_docs, row.n_failure_events) == (2, 1, 8)
    assert (row.itt_n, row.itt_mean, row.itt_median) == (3, 33.3333, 0)
    assert row.itt_approx is False


@pytest.mark.parametrize(
    "partial_itt",
    [
        {"itt_n_docs": 999, "itt_mean": 999},
        {"itt_median": 999, "itt_mean": 999},
        {"itt_n_docs": 999, "itt_median": None},
    ],
)
def test_incomplete_emitted_itt_is_recomputed(registry, partial_itt) -> None:
    row = rws.row_from_bench_line(_line(**partial_itt), registry)
    assert row is not None
    assert (row.itt_n, row.itt_mean, row.itt_median) == (4, 60, 70)
    assert row.itt_approx is False


@pytest.mark.parametrize("itt_n, expected_failed", [(5, 2), (2, 0)])
def test_emitted_itt_without_scores_infers_nonnegative_failed_count(
    registry, itt_n, expected_failed
) -> None:
    row = rws.row_from_bench_line(
        _line(scores=None, itt_n_docs=itt_n, itt_mean=12.5, itt_median=0), registry
    )
    assert row is not None
    assert row.n_failed_docs == expected_failed
    assert (row.itt_n, row.itt_mean, row.itt_median) == (itt_n, 12.5, 0)
    assert row.itt_approx is False
    assert row.provenance == "legacy"


@pytest.mark.parametrize("emitted", [False, True])
def test_empty_run_has_zero_itt_statistics(registry, emitted) -> None:
    fields = {"itt_n_docs": 0, "itt_mean": 0, "itt_median": 0} if emitted else {}
    row = rws.row_from_bench_line(
        _line(n_docs=0, scores={}, failures=[], **fields), registry
    )
    assert row is not None
    assert (row.n_scored, row.n_failed_docs) == (0, 0)
    assert (row.itt_n, row.itt_mean, row.itt_median) == (0, 0, 0)
    assert row.itt_approx is (not emitted)
    assert row.provenance == "legacy"


@pytest.mark.parametrize("scores", [None, {}, []])
def test_legacy_approximation_uses_median_and_failure_event_count(registry, scores) -> None:
    row = rws.row_from_bench_line(
        _line(scores=scores, n_docs=2, overall_median=90, overall_mean=12), registry
    )
    assert row is not None
    assert (row.n_scored, row.n_failed_docs, row.n_failure_events) == (2, 2, 2)
    assert (row.itt_n, row.itt_mean, row.itt_median) == (4, 45, 45)
    assert row.itt_approx is True


def test_numeric_strings_and_invalid_values_are_normalized(registry) -> None:
    row = rws.row_from_bench_line(
        _line(
            scores={1: "75.5", "bool": True, "missing": None, "bad": "invalid"},
            failures=[],
            overall_mean="18.875",
            overall_median=False,
            exact_100="2",
            n_oracle_unmatched="3",
        ),
        registry,
    )
    assert row is not None
    assert row.scores == {"1": 75.5, "bool": 0, "missing": 0, "bad": 0}
    assert (row.mean, row.median, row.exact_100, row.n_oracle_unmatched) == (18.875, 0, 2, 3)
    assert (row.itt_n, row.itt_mean, row.itt_median) == (4, 18.875, 0)


@pytest.mark.parametrize(
    "stage, benchmark",
    [
        ("redline", "script_redlines"),
        ("accepted", "accepted_changes"),
        ("roundtrip", "roundtrip"),
        ("render-original", "visual_rendering"),
        ("render-redline", "visual_redlines"),
        ("render-accepted", "visual_accepted_changes"),
    ],
)
def test_legacy_stage_and_identity_fields_are_supported(registry, stage, benchmark) -> None:
    row = rws.row_from_bench_line(
        _line(
            benchmark=None, stage=stage, vendor=None, tool="docxodus",
            id_run=None, uuid7="legacy-run", environment_config=None,
            render="passthrough",
        ),
        registry,
    )
    assert row is not None
    assert row.benchmark == benchmark
    assert (row.id_run, row.tool_id, row.run_name, row.render) == (
        "legacy-run", "docxodus", "docxodus", "passthrough"
    )


def test_explicit_benchmark_takes_precedence_over_legacy_stage(registry) -> None:
    row = rws.row_from_bench_line(_line(stage="accepted"), registry)
    assert row is not None and row.benchmark == "script_redlines"
    assert rws.row_from_bench_line(_line(benchmark="unknown", stage="redline"), registry) is None


@pytest.mark.parametrize("stage", [None, "unknown", 123])
def test_missing_or_unknown_legacy_stage_is_unmapped(registry, stage) -> None:
    assert rws.row_from_bench_line(_line(benchmark=None, stage=stage), registry) is None


@pytest.mark.parametrize(
    "env", [None, [], "invalid", {}, {"runs": []}, {"runs": {}}, {"runs": [None]}]
)
def test_invalid_run_metadata_falls_back_to_top_level_fields(registry, env) -> None:
    row = rws.row_from_bench_line(
        _line(environment_config=env, tool="docxodus", render="passthrough"), registry
    )
    assert row is not None
    assert (row.run_name, row.render) == ("docxodus", "passthrough")


@pytest.mark.parametrize(
    "fields, expected",
    [
        ({"timestamp": "2026-08-12T23:42:30"}, datetime(2026, 8, 12, 23, 42, 30, tzinfo=UTC)),
        ({"timestamp": "2026-08-12T23:42:30Z"}, datetime(2026, 8, 12, 23, 42, 30, tzinfo=UTC)),
        ({"timestamp": None, "run_ts": "2026-01-02"}, datetime(2026, 1, 2, tzinfo=UTC)),
        ({"timestamp": None}, datetime(1970, 1, 1, tzinfo=UTC)),
        ({"timestamp": "invalid"}, datetime(1970, 1, 1, tzinfo=UTC)),
    ],
)
def test_timestamps_are_timezone_aware_with_deterministic_fallback(
    registry, fields, expected
) -> None:
    row = rws.row_from_bench_line(_line(**fields), registry)
    assert row is not None and row.timestamp == expected


def test_timestamp_preserves_explicit_offset_and_wins_over_run_ts(registry) -> None:
    row = rws.row_from_bench_line(
        _line(timestamp="2026-01-02T03:00:00+03:00", run_ts="2000-01-01"), registry
    )
    assert row is not None
    assert row.timestamp.utcoffset() == timedelta(hours=3)
    assert row.timestamp.astimezone(UTC) == datetime(2026, 1, 2, tzinfo=UTC)


def test_normalization_preserves_metadata_without_mutating_input(registry) -> None:
    data = _line(
        vendor="jubarte", docset_id="documents-v1", renderer_id="lo-26",
        holdout_mode="test",
        hardware={"cpu": "synthetic", "cores": 4},
        environment_config={"runs": [{"name": "jubarte-final-native", "render": "soffice"}]},
    )
    original = deepcopy(data)
    row = rws.row_from_bench_line(data, registry)
    assert row is not None
    assert (row.source, row.lens) == ("bench", "pixel")
    assert (row.display, row.configuration) == ("jubarte (ast)", "ast")
    assert (row.docset_id, row.renderer_id) == ("documents-v1", "lo-26")
    assert (row.holdout_mode, row.scorer) == ("test", "pagefair-v2")
    assert row.corpus_revision == "5ed816028d99"
    assert row.hardware == {"cpu": "synthetic", "cores": 4}
    assert data == original
    row.scores["a"] = 1
    assert data == original


@pytest.mark.parametrize("hardware", [None, [], "unknown"])
def test_optional_metadata_defaults_and_legacy_provenance(registry, hardware) -> None:
    row = rws.row_from_bench_line(
        _line(
            corpus_revision=None, scorer=None, hardware=hardware,
            environment_config=None,
        ),
        registry,
    )
    assert row is not None
    assert row.provenance == "legacy"
    assert row.scorer == "v1"
    assert (row.hardware, row.run_name, row.render) == (None,) * 3
    assert (row.docset_id, row.renderer_id, row.holdout_mode) == (None,) * 3


def test_result_identity_cannot_be_reassigned(registry) -> None:
    row = rws.row_from_bench_line(_line(), registry)
    assert row is not None
    with pytest.raises(ValidationError, match="frozen_instance"):
        row.tool_id = "other"


def test_loader_skips_corrupt_lines_and_preserves_order_and_unmapped_details(
    tmp_path: Path, registry
) -> None:
    first = _line(id_run="first", scores={"café": 90}, failures=[])
    last = _line(id_run="last")
    unknown = _ghost(id_run="unknown")
    legacy = _line(
        id_run="legacy", benchmark=None, stage="unknown", vendor=None,
        tool="docxodus", environment_config=None,
    )
    path = tmp_path / "bench.jsonl"
    path.write_text(
        "\n  \n" + json.dumps(first, ensure_ascii=False) + "\n{broken json\n"
        + json.dumps(unknown) + "\n" + json.dumps(legacy) + "\n" + json.dumps(last)
        + '\n{"truncated":',
        encoding="utf-8",
    )
    rows, unmapped = rws.load_bench_rows(path, registry)
    assert [row.id_run for row in rows] == ["first", "last"]
    assert rows[0].scores == {"café": 90}
    assert unmapped == [
        {"vendor": "ghost", "run_name": "ghost",
         "benchmark": "script_redlines", "id_run": "unknown"},
        {"vendor": "docxodus", "run_name": "docxodus",
         "benchmark": "unknown", "id_run": "legacy"},
    ]


@pytest.mark.parametrize("contents", ["", "\n \t\n", "invalid json\n"])
def test_loader_with_no_valid_rows_returns_empty_results(
    tmp_path: Path, registry, contents
) -> None:
    path = tmp_path / "empty.jsonl"
    path.write_text(contents)
    assert rws.load_bench_rows(path, registry) == ([], [])


def test_loader_surfaces_missing_file(tmp_path: Path, registry) -> None:
    with pytest.raises(FileNotFoundError):
        rws.load_bench_rows(tmp_path / "missing.jsonl", registry)

# ---- speed rows ---------------------------------------------------------------


def _speed_line(**over) -> dict:
    base = {
        "schema": 1,
        "kind": "speed_redlines",
        "tool": "jubarte-rust-inproc",
        "runtime": "rust",
        "run_ts": "2026-08-15T10:00:00Z",
        "fixture_count": 1000,
        "pair_count": 5000,
        "n": 5000,
        "failures": 0,
        "unit": "ms_per_redline",
        "mean": 25.34,
        "median": 6.2,
        "p95": 110.76,
        "throughput_per_s": 39.5,
        "tool_version": "jubarte-rust@17ea47e9a0d7+git.bf3d07d",
        "hardware": {"cpu": "Apple M3", "cores": 12},
    }
    base.update(over)
    return base


def _registry_with(tmp_path: Path, *entries: dict):
    doc = yaml.safe_load((tmp_path / "reg.yaml").read_text())
    doc["tools"].extend(entries)
    (tmp_path / "reg2.yaml").write_text(yaml.safe_dump(doc))
    return load_registry(tmp_path / "reg2.yaml")


_JUBARTE_RUST = {
    "id": "jubarte-rust",
    "vendor": "jubarte",
    "display": "jubarte-rust",
    "role": "generator",
    "engine": "jubarte-redlines",
    "affiliated": True,
    "speed_tools": ["jubarte-rust"],
}
_CSHARP = {
    "id": "docxodus-csharp",
    "vendor": "docxodus",
    "display": "docxodus (C#)",
    "role": "generator",
    "engine": "docxodus",
    "speed_tools": ["docxodus-csharp"],
}


def test_speed_row_maps_tool_and_inproc(tmp_path: Path, registry) -> None:
    reg2 = _registry_with(tmp_path, _JUBARTE_RUST)
    row = rws.speed_row_from_line(_speed_line(), reg2)
    assert row is not None
    assert row.tool_id == "jubarte-rust" and row.inproc is True and row.kind == "large"
    assert row.pin.display == "jubarte-rust@17ea47e9a0d7+git.bf3d07d"
    assert row.median_ms == 6.2 and row.fixture_count == 1000 and row.n == 5000
    assert row.hardware == {"cpu": "Apple M3", "cores": 12}
    assert row.affiliated is True


def test_speed_row_without_version_is_unpinned(tmp_path: Path, registry) -> None:
    reg2 = _registry_with(tmp_path, _CSHARP)
    row = rws.speed_row_from_line(
        _speed_line(
            tool="docxodus-csharp", tool_version=None, hardware=None, kind="speed"
        ),
        reg2,
    )
    assert row is not None and row.pin.pinned is False and row.kind == "micro"
    assert row.hardware is None and row.inproc is False


def test_speed_row_rejects_other_units_errors_and_unknown_tools(
    tmp_path: Path, registry
) -> None:
    reg2 = _registry_with(tmp_path, _JUBARTE_RUST)
    assert rws.speed_row_from_line(_speed_line(unit="ms_per_render"), reg2) is None
    assert rws.speed_row_from_line(_speed_line(error="boom", median=None), reg2) is None
    assert rws.speed_row_from_line(_speed_line(tool="nobody"), reg2) is None
    assert rws.speed_row_from_line(_speed_line(n=0), reg2) is None


def test_load_speed_rows_reads_jsonl_and_summaries(tmp_path: Path, registry) -> None:
    reg2 = _registry_with(tmp_path, _JUBARTE_RUST)
    (tmp_path / "speed.jsonl").write_text(
        json.dumps(_speed_line())
        + "\n"
        + json.dumps(_speed_line(tool="ghost-tool"))
        + "\n"
    )
    summary_dir = tmp_path / "redline_speed_bench" / "run1"
    summary_dir.mkdir(parents=True)
    (summary_dir / "summary.json").write_text(
        json.dumps(
            {
                "runTs": "2026-08-16T10:00:00Z",
                "fixtures": 200,
                "pairs": 500,
                "rows": [
                    dict(
                        _speed_line(
                            kind="redline_speed_bench",
                            fixture_count=None,
                            pair_count=None,
                            run_ts=None,
                        )
                    )
                ],
            }
        )
    )
    rows, unmapped = rws.load_speed_rows(
        tmp_path / "speed.jsonl", tmp_path / "redline_speed_bench", reg2
    )
    assert [u["tool"] for u in unmapped] == ["ghost-tool"]
    assert sorted((r.fixture_count, r.pair_count) for r in rows) == [
        (200, 500),
        (1000, 5000),
    ]
    assert {r.timestamp.day for r in rows} == {15, 16}


def test_bench_version_is_carried_and_absent_on_old_lines(registry) -> None:
    stamped = rws.row_from_bench_line(_line(bench_version="0.7.0"), registry)
    old = rws.row_from_bench_line(_line(), registry)
    assert stamped is not None and old is not None
    assert stamped.bench_version == "0.7.0"
    assert old.bench_version is None
