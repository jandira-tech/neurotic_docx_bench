"""Visual-benchmark oracle resolution.

Maps a run's declared ``visual_*`` benchmarks to their oracle PDF folders.
The actual scoring dispatch lives in :mod:`neurotic_docx_bench.cli`; this module
isolates the (benchmark_name → oracle_folder) policy so it can be unit-tested
without driving a full bench run (which needs LibreOffice + a real DOCX corpus).
"""

from __future__ import annotations

from pathlib import Path

from neurotic_docx_bench.benchmarks import BenchmarkName

# Canonical order: rendering → redlines → accepted. Stable regardless of how a
# run declares its benchmarks list, so JSONL lines are emitted deterministically.
_VISUAL_BENCHMARKS: tuple[BenchmarkName, ...] = (
    "visual_rendering",
    "visual_redlines",
    "visual_accepted_changes",
)


def visual_benchmarks_for_run(
    rc,
    visual_oracles: dict[str, Path],
) -> list[tuple[BenchmarkName, Path]]:
    """Yield ``(benchmark_name, oracle_dir)`` for every visual_* benchmark declared
    on ``rc.benchmarks`` whose oracle is present in ``visual_oracles``.

    Order is the canonical BENCHMARKS order (rendering, redlines, accepted),
    independent of declaration order. A declared benchmark with no resolvable
    oracle is omitted (the caller prints a skip notice).
    """
    declared = set(getattr(rc, "benchmarks", []) or [])
    pairs: list[tuple[BenchmarkName, Path]] = []
    for name in _VISUAL_BENCHMARKS:
        if name not in declared:
            continue
        oracle = visual_oracles.get(name)
        if oracle is None:
            continue
        pairs.append((name, oracle))
    return pairs
