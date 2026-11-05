"""aggregate.compute_aggregate distribution stats."""

from __future__ import annotations

from neurotic_docx_bench.aggregate import compute_aggregate


def test_known_vector():
    scores = {"a": 100.0, "b": 100.0, "c": 100.0, "d": 90.0, "e": 40.0}
    agg = compute_aggregate(scores)
    assert agg.n_docs == 5
    assert agg.exact_100 == 3
    assert agg.at_least_90 == 4
    assert agg.below_50 == 1
    assert agg.min == 40.0
    assert agg.max == 100.0
    assert agg.overall_mean == 86.0
    assert agg.overall_median == 100.0
    # inclusive quartiles of [40,90,100,100,100]
    assert agg.q1 == 90.0
    assert agg.q3 == 100.0


def test_empty_is_zero():
    agg = compute_aggregate({})
    assert agg.n_docs == 0
    assert agg.overall_mean == 0.0 and agg.max == 0.0
    assert "page_mean" not in agg.to_dict()  # None fields dropped


def test_page_stats_from_per_doc():
    scores = {"a": 95.0, "b": 85.0}
    per_doc = {
        "a": {"overall_score": 95.0, "pages": [{"score": 100.0}, {"score": 90.0}]},
        "b": {"overall_score": 85.0, "pages": [{"score": 80.0}]},
    }
    agg = compute_aggregate(scores, per_doc=per_doc)
    assert agg.page_mean == 90.0  # mean of 100, 90, 80
    assert agg.page_median == 90.0
    assert "page_mean" in agg.to_dict()


def test_single_doc():
    agg = compute_aggregate({"only": 73.5})
    assert agg.n_docs == 1
    assert agg.overall_mean == agg.overall_median == 73.5
    assert agg.q1 == agg.q3 == 73.5
    assert agg.std == 0.0
