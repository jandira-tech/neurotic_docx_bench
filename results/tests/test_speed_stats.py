"""Shared speed-distribution stats (extracted so every speed benchmark — Node-style
``speed-bench.ts``, ``superdoc_speed``, and the new ``playwright_speed`` — computes
the same percentile/throughput shape from a sample list).
"""

from __future__ import annotations

from neurotic_docx_bench.speed_stats import stats as speed_stats


def test_stats_percentiles_and_throughput() -> None:
    s = speed_stats([10.0, 20.0, 30.0, 40.0, 50.0])
    assert s["n"] == 5
    assert s["min"] == 10.0 and s["max"] == 50.0
    assert s["median"] == 30.0
    assert s["mean"] == 30.0
    assert s["p90"] == 50.0 and s["p99"] == 50.0
    assert s["total"] == 150.0
    # 5 samples over 150ms → 5/0.150s ≈ 33.33/s
    assert abs(s["throughput_per_s"] - (1000 * 5 / 150)) < 0.01


def test_stats_single_sample() -> None:
    s = speed_stats([7.5])
    assert s["n"] == 1
    assert s["median"] == 7.5 and s["mean"] == 7.5
    assert s["min"] == 7.5 and s["max"] == 7.5
    assert s["std"] == 0.0


def test_stats_rounds_to_millisecond_thousandths() -> None:
    # 1/3 ms should round to 0.333 (3 dp), not propagate float noise.
    s = speed_stats([1.0 / 3.0])
    assert s["mean"] == 0.333
