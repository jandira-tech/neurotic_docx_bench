"""Benchmark stage executors extracted from CLI (Task 5).

Holds ``speed_samples_from_timings`` (used by ``cli._emit_and_gate_benchmark``)
and ``render_timings_from_report`` (builds the per-doc ``render_s`` timing map
from a :class:`~neurotic_docx_bench.render.base.RenderReport`, used by the
visual_* benchmarks' render-speed stats). The ``_accept_compare_stage`` /
``_roundtrip_stage`` / ``_collect_timings`` helpers live in ``cli.py`` itself;
this module is the timing-side extraction.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from neurotic_docx_bench import pipeline

if TYPE_CHECKING:
    from neurotic_docx_bench.render.base import RenderReport


def speed_samples_from_timings(
    timings: dict[str, dict[str, float]], key: str,
) -> list[float]:
    """Extract speed samples (ms) from per-doc timing dicts."""
    return [
        round(float(entry[key]) * 1000.0, 4)
        for entry in timings.values()
        if key in entry
    ]


def render_timings_from_report(
    report: RenderReport, tool: str | None = None,
) -> dict[str, dict[str, float]]:
    """Build a per-doc ``{key: {"render_s": seconds}}`` map from a render report.

    Each :class:`~neurotic_docx_bench.render.base.RenderResult` carries a
    ``duration_ns`` walltime (soffice and playwright both set it); results
    without one are skipped. The key is the canonical ``<base>_<next>``
    redline key (via :func:`pipeline.redline_key`) so render-speed lines up
    with the score/``per_doc`` rows. Used by the visual_* benchmarks, whose
    render pass is shared across all three — they legitimately share one
    render-speed distribution.
    """
    timings: dict[str, dict[str, float]] = {}
    for r in report.results:
        if r.duration_ns is None:
            continue
        key = pipeline.redline_key(r.source.stem, tool)
        timings.setdefault(key, {})["render_s"] = r.duration_ns / 1e9
    return timings
