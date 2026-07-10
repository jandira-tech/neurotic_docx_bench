"""Tests for benchmark stage executors (Task 5)."""

from __future__ import annotations

from pathlib import Path

from neurotic_docx_bench.render.base import RenderReport, RenderResult
from neurotic_docx_bench.stages import render_timings_from_report, speed_samples_from_timings


def test_speed_samples_from_generation_seconds_to_ms() -> None:
    timings = {"a": {"generate_s": 0.010}, "b": {"generate_s": 0.025}}
    assert speed_samples_from_timings(timings, "generate_s") == [10.0, 25.0]


def test_speed_samples_ignore_missing_key() -> None:
    timings = {"a": {"render_s": 0.010}, "b": {"score_s": 0.030}}
    assert speed_samples_from_timings(timings, "render_s") == [10.0]


def test_speed_samples_empty_timings() -> None:
    assert speed_samples_from_timings({}, "generate_s") == []


def test_render_timings_from_report_extracts_render_s() -> None:
    """A RenderReport whose results carry ``duration_ns`` produces a per-doc
    ``{key: {"render_s": seconds}}`` map — the input the visual_* benchmark lines
    need to populate their (currently empty) render-speed stats.
    """
    report = RenderReport(
        pdf_dir=Path("/tmp/x"),
        results=[
            RenderResult(source=Path("a_b_jubarte_redline.docx"), pdf=Path("a_b.pdf"),
                         ok=True, duration_ns=12_000_000),
            RenderResult(source=Path("c_d_jubarte_redline.docx"), pdf=Path("c_d.pdf"),
                         ok=True, duration_ns=34_000_000),
        ],
    )
    timings = render_timings_from_report(report, tool="jubarte")
    assert set(timings) == {"a_b", "c_d"}
    assert timings["a_b"]["render_s"] == 0.012
    assert timings["c_d"]["render_s"] == 0.034


def test_render_timings_from_report_skips_missing_duration() -> None:
    """A result without ``duration_ns`` (e.g. a backend that didn't time itself)
    is skipped, not emitted as a None — ``speed_samples_from_timings`` then just
    gets fewer samples, never a crash.
    """
    report = RenderReport(
        pdf_dir=Path("/tmp/x"),
        results=[
            RenderResult(source=Path("a_b_jubarte_redline.docx"), pdf=Path("a_b.pdf"),
                         ok=True, duration_ns=None),
        ],
    )
    assert render_timings_from_report(report, tool="jubarte") == {}


def test_render_timings_from_report_empty() -> None:
    assert render_timings_from_report(RenderReport(pdf_dir=Path("/tmp/x")), tool="x") == {}
