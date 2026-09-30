"""``neurotic_docx_bench.profile``: per-stage timing summaries (plan item 9b)."""

from __future__ import annotations

from pathlib import Path

import pytest

from neurotic_docx_bench import profile


def test_summarize_reports_every_stage_with_samples_in_pipeline_order() -> None:
    timings = {
        "a_b": {"score_s": 4.0, "raster_s": 1.0, "render_s": 2.0},
        "c_d": {"score_s": 2.0, "raster_s": 3.0},
        "e_f": {"generate_s": 0.5},
    }
    stats = profile.summarize(timings)
    assert list(stats) == ["generate_s", "render_s", "raster_s", "score_s"]
    assert stats["score_s"]["n"] == 2
    assert stats["score_s"]["total_s"] == 6.0
    assert stats["score_s"]["mean_s"] == 3.0
    assert stats["score_s"]["median_s"] == 3.0
    assert stats["score_s"]["max_s"] == 4.0
    assert stats["render_s"]["n"] == 1
    assert stats["render_s"]["p95_s"] == 2.0
    # Share is the stage's total over the sum of every stage total.
    grand = 0.5 + 2.0 + 4.0 + 6.0
    assert stats["score_s"]["share"] == pytest.approx(6.0 / grand)
    assert sum(s["share"] for s in stats.values()) == pytest.approx(1.0)


def test_summarize_skips_stages_without_samples_and_handles_empty_input() -> None:
    assert profile.summarize({}) == {}
    stats = profile.summarize({"a_b": {"raster_s": 1.0}})
    assert list(stats) == ["raster_s"]
    assert stats["raster_s"]["share"] == 1.0


def test_p95_is_the_nearest_rank_percentile() -> None:
    values = [float(i) for i in range(1, 101)]
    assert profile.percentile(values, 95) == 95.0
    assert profile.percentile([7.0], 95) == 7.0
    assert profile.percentile([3.0, 1.0, 2.0], 50) == 2.0


def test_sample_files_is_deterministic_sorted_and_bounded(tmp_path: Path) -> None:
    files = [tmp_path / f"{i:03d}.docx" for i in range(20)]
    for f in files:
        f.write_bytes(b"")
    first = profile.sample_files(files, 5, seed=0)
    assert first == profile.sample_files(list(reversed(files)), 5, seed=0)
    assert first == sorted(first)
    assert len(first) == 5
    assert first != profile.sample_files(files, 5, seed=1)
    # Asking for more than there is returns everything, in order.
    assert profile.sample_files(files, 50, seed=0) == sorted(files)


def test_build_report_carries_provenance_and_summaries() -> None:
    runs = {
        "jubarte": {
            "renderer_id": "soffice-24.2",
            "wall_s": 12.5,
            "benchmarks": {
                "script_redlines": {"a_b": {"raster_s": 1.0, "score_s": 3.0}},
                "visual_redlines": {},
            },
        },
    }
    report = profile.build_report(runs, sample=10, seed=0, dpi=144)
    assert report["cached"] is False
    assert report["sample"] == 10 and report["seed"] == 0 and report["dpi"] == 144
    assert report["scorer_fingerprint"] and report["raster_engine"]
    run = report["runs"]["jubarte"]
    assert run["renderer_id"] == "soffice-24.2"
    assert run["wall_s"] == 12.5
    assert run["benchmarks"]["script_redlines"]["score_s"]["total_s"] == 3.0
    # A benchmark with no timed documents is still listed, empty.
    assert run["benchmarks"]["visual_redlines"] == {}


def test_table_rows_are_one_per_benchmark_stage() -> None:
    report = profile.build_report(
        {"t": {"renderer_id": "x", "wall_s": 1.0, "benchmarks": {
            "script_redlines": {"k": {"raster_s": 1.0, "score_s": 2.0}},
        }}},
        sample=1, seed=0, dpi=144,
    )
    rows = profile.table_rows(report)
    assert [(r["run"], r["benchmark"], r["stage"]) for r in rows] == [
        ("t", "script_redlines", "raster_s"),
        ("t", "script_redlines", "score_s"),
    ]
    assert rows[1]["share"] == pytest.approx(2.0 / 3.0)


def test_render_tables_one_per_run_with_stage_rows() -> None:
    from rich.console import Console

    report = profile.build_report(
        {
            "t": {"renderer_id": "x", "wall_s": 1.0, "benchmarks": {
                "script_redlines": {"k": {"raster_s": 1.0, "score_s": 2.0}},
                "visual_redlines": {},
            }},
            "u": {"renderer_id": None, "wall_s": None, "benchmarks": {}},
        },
        sample=1, seed=0, dpi=144,
    )
    tables = profile.render_tables(report)
    assert len(tables) == 2
    assert tables[0].row_count == 2 and tables[1].row_count == 0
    console = Console(width=80, record=True)
    for table in tables:
        console.print(table)
    text = console.export_text()
    assert "t: wall 1.00 s, renderer x" in text
    assert "u: wall n/a, renderer None" in text
    assert "66.7%" in text and "\u2026" not in text, "nothing is truncated at 80 columns"
