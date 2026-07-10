"""Benchmark names, legacy stage mapping, outcomes, and vendor defaults (Task 2).

Provides the canonical mapping from legacy schema-v3 stage names to the six
:class:`BenchmarkName` literals, a frozen :class:`BenchmarkOutcome` dataclass
that stages produce, and :func:`default_benchmarks_for_vendor` for config convenience.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BenchmarkName = Literal[
    "accepted_changes",
    "script_redlines",
    "roundtrip",
    "visual_rendering",
    "visual_redlines",
    "visual_accepted_changes",
]

BENCHMARKS: tuple[BenchmarkName, ...] = (
    "accepted_changes",
    "script_redlines",
    "roundtrip",
    "visual_rendering",
    "visual_redlines",
    "visual_accepted_changes",
)

LegacyStage = str

LEGACY_STAGE_TO_BENCHMARK: dict[LegacyStage, BenchmarkName] = {
    "redline": "script_redlines",
    "accepted": "accepted_changes",
    "roundtrip": "roundtrip",
    "render-original": "visual_rendering",
    "render-redline": "visual_redlines",
    "render-accepted": "visual_accepted_changes",
}


@dataclass(frozen=True)
class BenchmarkOutcome:
    benchmark: BenchmarkName
    scores: dict[str, float]
    per_doc: dict[str, dict[str, object]] | None
    failures: list[dict[str, str]] = field(default_factory=list)
    speed_samples_ms: list[float] = field(default_factory=list)
    # Per-doc step durations (seconds). The visual_* benchmarks share one render
    # pass, so they share its ``render_s`` distribution; accept/roundtrip carry
    # their own ``render_s``. ``_emit_and_gate_benchmark`` derives
    # ``speed_samples_ms`` from this when the caller doesn't pass one explicitly.
    timings: dict[str, dict[str, float]] = field(default_factory=dict)


def benchmark_for_legacy_stage(stage: str) -> BenchmarkName:
    try:
        return LEGACY_STAGE_TO_BENCHMARK[stage]
    except KeyError as exc:
        raise ValueError(f"unknown benchmark stage: {stage}") from exc


def default_benchmarks_for_vendor(vendor: str) -> list[BenchmarkName]:
    lowered = vendor.lower()
    if lowered.startswith("jubarte"):
        return ["accepted_changes", "script_redlines", "roundtrip"]
    if lowered in {"docxodus", "superdoc"}:
        return list(BENCHMARKS)
    if lowered == "folio":
        # folio covers 5/6 benchmarks across two runs: the `folio` run drives
        # script_redlines + accepted_changes + roundtrip (headless), and
        # folio-playwright drives the three visual_* (via @stll/folio-react).
        return ["script_redlines", "accepted_changes", "roundtrip",
                "visual_rendering", "visual_redlines", "visual_accepted_changes"]
    return ["script_redlines"]
