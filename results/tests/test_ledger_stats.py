"""Percentile bootstrap on per-document scores; paired on shared documents."""

from __future__ import annotations

from neurotic_docx_bench.ledger import stats as st


def test_median_ci_contains_the_median_and_is_deterministic() -> None:
    values = [float(v) for v in range(101)]
    ci = st.bootstrap_median_ci(values, reps=500, seed=1)
    assert ci is not None
    lo, hi = ci
    assert lo <= 50.0 <= hi
    assert st.bootstrap_median_ci(values, reps=500, seed=1) == (lo, hi)


def test_median_ci_degenerates_for_tiny_samples() -> None:
    assert st.bootstrap_median_ci([1.0, 2.0], reps=100) == (1.0, 2.0)
    assert st.bootstrap_median_ci([], reps=100) is None


def test_paired_diff_on_shared_docs_only() -> None:
    a = {f"d{i}": 60.0 + i for i in range(40)}
    b = {f"d{i}": 50.0 + i for i in range(40)}
    b["only_b"] = 1.0
    d = st.paired_median_diff(a, b, reps=500, seed=7)
    assert d is not None
    assert d.n == 40 and d.median_delta == 10.0
    assert d.ci_low > 0 and d.ci_high >= d.ci_low
    assert (d.wins, d.losses, d.ties) == (40, 0, 0)


def test_paired_diff_identical_tools_straddles_zero() -> None:
    a = {f"d{i}": float(i % 7) for i in range(60)}
    d = st.paired_median_diff(a, dict(a), reps=500, seed=3)
    assert d is not None and d.ci_low <= 0.0 <= d.ci_high and d.ties == 60


def test_paired_diff_requires_min_shared_docs() -> None:
    a = {f"d{i}": 1.0 for i in range(10)}
    assert st.paired_median_diff(a, a, reps=100) is None


def test_tie_when_interval_includes_zero() -> None:
    a = {f"d{i}": float(i % 7) for i in range(60)}
    b = {k: v + 0.01 * (i % 2) for i, (k, v) in enumerate(a.items())}
    assert st.tie_by_paired_bootstrap(a, b, reps=300, seed=2) is True
    far = {k: v + 30.0 for k, v in a.items()}
    assert st.tie_by_paired_bootstrap(a, far, reps=300, seed=2) is False
    assert st.tie_by_paired_bootstrap({"x": 1.0}, {"x": 1.0}) is False
