"""Shared speed-distribution statistics for every speed benchmark.

The Node ``scripts/speed-bench.ts`` and the Python ``superdoc_speed`` /
``playwright_speed`` modules all reduce a list of per-call millisecond samples to
the same distribution: ``n, mean, median, p90, p95, p99, min, max, std, total,
throughput_per_s``. Centralising it here keeps the percentile definition
(``ceil(p*n)-1`` index, matching the TS implementation) and the 3-dp rounding
identical across runtimes, so a render-speed row is directly comparable to a
generation-speed row.

Usage:
    from neurotic_docx_bench.speed_stats import stats
    s = stats([1.45, 2.36, 4.50])  # → dict with median, p95, throughput_per_s, …
"""

from __future__ import annotations

import math
import statistics
from typing import TypedDict


class SpeedStats(TypedDict):
    n: int
    mean: float
    median: float
    p90: float
    p95: float
    p99: float
    min: float
    max: float
    std: float
    total: float
    throughput_per_s: float


def _round3(x: float) -> float:
    return round(x, 3)


def stats(xs: list[float]) -> SpeedStats:
    """Full distribution of a sample list (ms per call).

    Percentiles use the ``ceil(p*n)-1`` index (same as ``scripts/speed-bench.ts``)
    so the Node and Python rows agree. ``throughput_per_s`` is ``1000*n/total``.
    Values are rounded to 3 dp. An empty list returns all-zero stats (callers
    guard against this, but it keeps the function total).
    """
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return SpeedStats(
            n=0, mean=0.0, median=0.0, p90=0.0, p95=0.0, p99=0.0,
            min=0.0, max=0.0, std=0.0, total=0.0, throughput_per_s=0.0,
        )
    total = sum(s)
    mean = total / n

    def q(p: float) -> float:
        return s[min(n - 1, max(0, math.ceil(p * n) - 1))]

    return SpeedStats(
        n=n,
        mean=_round3(mean),
        median=_round3(q(0.5)),
        p90=_round3(q(0.9)),
        p95=_round3(q(0.95)),
        p99=_round3(q(0.99)),
        min=_round3(s[0]),
        max=_round3(s[-1]),
        std=_round3(statistics.pstdev(s)),
        total=_round3(total),
        throughput_per_s=_round3(1000.0 * n / total),
    )
