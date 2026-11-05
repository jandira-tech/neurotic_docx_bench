"""emit.jsonl — schema v4: one self-contained ``Results`` line per ``(vendor, benchmark)``.

Each line is a typed :class:`~neurotic_docx_bench.results_schema.Results` with
stable key order (``id_run``, ``vendor``, ``benchmark`` first).  Legacy v3
``build_line`` (``tool``/``stage``) is deprecated but still tested for
backward-compatible readers.
"""

from __future__ import annotations

import json
import re

from neurotic_docx_bench.emit import jsonl


def _line(scores, tool="jubarte", stage="redline", render="soffice", run_id="r1",
          uuid7_str=None):
    return jsonl.build_line(
        tool=tool,
        stage=stage,
        tool_version="1.6.2",
        render=render,
        baseline_ref="corpus/word_based/pdf_redlines_word@abc",
        scores=scores,
        config_hash="cfg",
        run_id=run_id,
        run_ts="2026-07-05T14:32:11Z",
        git_sha="deadbeef",
        uuid7_str=uuid7_str,
    )


def test_build_line_shape():
    line = _line({"doc1": 76.69, "doc2": 100.0})
    assert line["schema"] == jsonl.SCHEMA
    assert line["schema"] == 4
    assert line["tool"] == "jubarte"
    assert line["stage"] == "redline"
    assert line["n_docs"] == 2
    assert line["scores"] == {"doc1": 76.69, "doc2": 100.0}
    aggregate = line["aggregate"]
    assert aggregate["overall_mean"] == round((76.69 + 100.0) / 2, 4)
    assert aggregate["n_docs"] == 2
    assert line["failures"] == [] and line["n_failures"] == 0


def test_build_line_tool_is_first_key():
    """Per-run consumers (e.g. ``head -1 bench.jsonl | jq .tool``) need a stable
    leading key. ``stage`` is the second key.
    """
    line = _line({"doc1": 1.0})
    keys = list(line.keys())
    assert keys[0] == "tool"
    assert keys[1] == "stage"


def test_build_line_records_failures():
    fails = [
        {"doc": "a_b", "stage": "generate", "error": "engine boom"},
        {"doc": "c_d", "stage": "render", "error": "soffice exit 1"},
    ]
    line = jsonl.build_line(
        tool="superdoc",
        stage="accepted",
        tool_version="1.19.2",
        render="soffice",
        baseline_ref="ref",
        scores={"x_y": 90.0},
        failures=fails,
        config_hash="cfg",
        run_id="r",
        run_ts="t",
        git_sha="s",
    )
    assert line["n_failures"] == 2
    assert line["failures"] == fails
    assert line["tool_version"] == "1.19.2"
    assert line["stage"] == "accepted"


def test_build_line_includes_uuid7_and_datetime():
    line = _line({"a": 1.0})
    assert re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$",
        line["uuid7"],
    )
    assert "T" in line["datetime"]
    assert line["datetime"] != line["run_ts"]
    assert line["datetime"].endswith("+00:00") or line["datetime"].endswith("Z")


def test_build_line_accepts_explicit_uuid7_and_datetime():
    line = _line(
        {"a": 1.0},
        uuid7_str="019f39b6-241c-72ca-b67b-6ba864415506",
    )
    assert line["uuid7"] == "019f39b6-241c-72ca-b67b-6ba864415506"


def test_build_line_no_embedded_alternate_stages():
    """Schema v3: no roundtrip_scores/accepted_scores/aggregate_* keys on a line.
    Each stage is its own self-contained line.
    """
    line = _line({"a": 1.0})
    for removed in ("roundtrip_scores", "accepted_scores",
                    "aggregate_roundtrip", "aggregate_accepted"):
        assert removed not in line


def test_build_line_serialises_round_trip():
    line = _line({"a": 1.0}, stage="roundtrip")
    payload = json.loads(json.dumps(line, sort_keys=False))
    assert next(iter(payload.keys())) == "tool"
    assert payload["stage"] == "roundtrip"


def test_append_line_always_appends(tmp_path):
    path = tmp_path / "bench.jsonl"
    assert jsonl.append_line(path, _line({"d": 80.0})) is True
    # identical content still appends (never truncates/rewrites) → 2 lines
    assert jsonl.append_line(path, _line({"d": 80.0}, run_id="r2")) is True
    assert len(jsonl.read_lines(path)) == 2


def test_append_only_on_change(tmp_path):
    path = tmp_path / "bench.jsonl"
    assert jsonl.append_if_changed(path, _line({"d": 80.0})) is True
    # identical scores + aggregate + stage → skipped
    assert jsonl.append_if_changed(path, _line({"d": 80.0}, run_id="r2")) is False
    # changed scores → appended
    assert jsonl.append_if_changed(path, _line({"d": 81.0}, run_id="r3")) is True
    assert len(jsonl.read_lines(path)) == 2


def test_last_line_scoped_by_render(tmp_path):
    path = tmp_path / "bench.jsonl"
    jsonl.append_if_changed(path, _line({"d": 80.0}, render="soffice"))
    jsonl.append_if_changed(path, _line({"d": 70.0}, render="playwright"))
    line_soffice = jsonl.last_line_for_tool(path, "jubarte", render="soffice")
    line_playwright = jsonl.last_line_for_tool(path, "jubarte", render="playwright")
    assert line_soffice is not None
    assert line_playwright is not None
    assert line_soffice["scores"] == {"d": 80.0}
    assert line_playwright["scores"] == {"d": 70.0}
    # same tool, different render → treated independently for change detection
    assert jsonl.append_if_changed(path, _line({"d": 80.0}, render="playwright")) is True


def test_last_line_scoped_by_stage(tmp_path):
    """Schema v3: ``last_line_for_tool`` returns the latest line for a given
    ``(tool, stage)``, treating stages independently.
    """
    path = tmp_path / "bench.jsonl"
    jsonl.append_if_changed(path, _line({"d": 80.0}, stage="redline"))
    jsonl.append_if_changed(path, _line({"d": 99.0}, stage="accepted"))
    red = jsonl.last_line_for_tool(path, "jubarte", stage="redline")
    acc = jsonl.last_line_for_tool(path, "jubarte", stage="accepted")
    assert red is not None and acc is not None
    assert red["scores"] == {"d": 80.0}
    assert acc["scores"] == {"d": 99.0}
    # Same tool+scores but different stage → treated as different (change detected)
    assert jsonl.append_if_changed(
        path, _line({"d": 80.0}, stage="accepted", run_id="r2"),
    ) is True


def test_change_detector_per_stage(tmp_path):
    """Two runs with identical scores but different stages are independent — appending
    a new stage does not collide with the redline baseline.
    """
    path = tmp_path / "bench.jsonl"
    jsonl.append_if_changed(path, _line({"d": 80.0}, stage="redline"))
    # Same scores, different stage → must append (not skipped as a dup of redline)
    assert jsonl.append_if_changed(
        path, _line({"d": 80.0}, stage="roundtrip", run_id="r2"),
    ) is True
    assert len(jsonl.read_lines(path)) == 2
    # Identical scores + stage → skipped
    assert jsonl.append_if_changed(
        path, _line({"d": 80.0}, stage="roundtrip", run_id="r3"),
    ) is False


def test_has_already_ran_stage_aware(tmp_path):
    """``has_already_ran`` matches on ``(tool, stage, tool_version, config_hash)``."""
    path = tmp_path / "bench.jsonl"
    jsonl.append_line(path, _line({"d": 80.0}, stage="redline"))
    # Same identity → hit
    hit = jsonl.has_already_ran(
        path, tool="jubarte", tool_version="1.6.2", config_hash="cfg", stage="redline",
    )
    assert hit is not None
    # Different stage → miss
    miss = jsonl.has_already_ran(
        path, tool="jubarte", tool_version="1.6.2", config_hash="cfg", stage="accepted",
    )
    assert miss is None


def test_read_lines_treats_legacy_v2_as_redline(tmp_path):
    """A v2 line without a ``stage`` key is read back with stage defaulting to redline."""
    path = tmp_path / "bench.jsonl"
    legacy = {
        "tool": "oldtool", "tool_version": "0.1.0", "config_hash": "h",
        "schema": 2, "scores": {"d": 50.0}, "aggregate": {"n_docs": 1},
    }
    path.write_text(json.dumps(legacy) + "\n")
    lines = jsonl.read_lines(path)
    assert len(lines) == 1
    # last_line_for_tool treats it as redline
    got = jsonl.last_line_for_tool(path, "oldtool", stage="redline")
    assert got is not None
    assert got["scores"] == {"d": 50.0}


def test_build_results_line_uses_standard_schema():
    """Schema v4: build_results_line emits a Results dict keyed by vendor/benchmark,
    carrying aggregate + speed + score_config + environment_config, with no legacy
    tool/stage keys.
    """
    import uuid
    from datetime import UTC, datetime
    from pathlib import Path

    from neurotic_docx_bench.config import BenchConfig

    line = jsonl.build_results_line(
        id_run=uuid.UUID("019f39b6-241c-72ca-b67b-6ba864415506"),
        vendor="docxodus",
        benchmark="script_redlines",
        scores={"doc1": 100.0, "doc2": 80.0},
        per_doc=None,
        speed_samples_ms=[10.0, 20.0],
        environment_config=BenchConfig(source_of_truth=Path("oracle")),
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
        tool_version="6.4.0",
        config_hash="abc123",
    )
    # Leading keys are the Results identity triple.
    assert list(line)[:3] == ["id_run", "vendor", "benchmark"]
    assert line["vendor"] == "docxodus"
    assert line["benchmark"] == "script_redlines"
    assert line["n_docs"] == 2
    assert line["overall_mean"] == 90.0
    assert line["tool_version"] == "6.4.0"
    assert line["config_hash"] == "abc123"
    # Per-doc scores are embedded for the gate/snapshots.
    assert line["scores"] == {"doc1": 100.0, "doc2": 80.0}
    # Speed + score config + environment config are present.
    assert line["overall_mean_speed"] == 15.0
    assert "score_config" in line and "environment_config" in line
    # No legacy schema-v3 keys.
    assert "tool" not in line
    assert "stage" not in line
    assert "aggregate" not in line  # aggregate fields are top-level on Results


def test_has_already_ran_benchmark_matches_identity(tmp_path):
    """Schema v4 skip-already-ran keys on (vendor, benchmark, tool_version, config_hash)."""
    import uuid
    from datetime import UTC, datetime
    from pathlib import Path

    from neurotic_docx_bench.config import BenchConfig

    path = tmp_path / "bench.jsonl"
    line = jsonl.build_results_line(
        id_run=uuid.uuid7(),
        vendor="docxodus",
        benchmark="script_redlines",
        scores={"d": 90.0},
        per_doc=None,
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("oracle")),
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
        tool_version="6.4.0",
        config_hash="abc",
    )
    jsonl.append_line(path, line)
    hit = jsonl.has_already_ran_benchmark(
        path, vendor="docxodus", benchmark="script_redlines",
        tool_version="6.4.0", config_hash="abc",
    )
    assert hit is not None
    miss = jsonl.has_already_ran_benchmark(
        path, vendor="docxodus", benchmark="accepted_changes",
        tool_version="6.4.0", config_hash="abc",
    )
    assert miss is None


def test_append_if_changed_handles_results_line(tmp_path):
    """append_if_changed matches Results lines on (vendor, benchmark)."""
    import uuid
    from datetime import UTC, datetime
    from pathlib import Path

    from neurotic_docx_bench.config import BenchConfig

    path = tmp_path / "bench.jsonl"

    def _line(scores):
        return jsonl.build_results_line(
            id_run=uuid.uuid7(),
            vendor="docxodus",
            benchmark="script_redlines",
            scores=scores,
            per_doc=None,
            speed_samples_ms=[],
            environment_config=BenchConfig(source_of_truth=Path("oracle")),
            timestamp=datetime(2026, 7, 7, tzinfo=UTC),
        )

    assert jsonl.append_if_changed(path, _line({"d": 80.0})) is True
    # identical scores → skipped
    assert jsonl.append_if_changed(path, _line({"d": 80.0})) is False
    # changed scores → appended
    assert jsonl.append_if_changed(path, _line({"d": 81.0})) is True
    assert len(jsonl.read_lines(path)) == 2
