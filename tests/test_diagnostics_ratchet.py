"""Regression ratchet + census checkpoint (execution contract C1/C2, stage S0.3).

C1's four ratchets exist because every lift table in the jubarte plans is GROSS
arithmetic: a stage that knocks one document from 100 to 99 raises the perfect-count
requirement by one, silently. C2's census exists because those tables are computed
against a baseline that earlier stages mutate. Both are pure functions over recorded
scores, so both are testable without rendering anything.

The real-data test at the bottom is the one that matters: it pins the census against
run ``019fcc5d`` (jubarte-rust), the run every stage table in the three plans was
sized from. If it stops reproducing, either the run moved or the bands did.
"""

from __future__ import annotations

import json

import pytest
from helpers import REPO_ROOT

from neurotic_docx_bench.aggregate import compute_aggregate
from neurotic_docx_bench.diagnostics import ratchet

BENCH_JSONL = REPO_ROOT / "results" / "bench.jsonl"
JUBARTE_RUST_RUN = "019fcc5d-34e6-7029-95d9-463d5513fe7c"


def _report(baseline: dict[str, float], candidate: dict[str, float], **kw) -> ratchet.RatchetReport:
    kw.setdefault("baseline_failures", ())
    kw.setdefault("candidate_failures", ())
    return ratchet.evaluate_ratchets(baseline, candidate, **kw)


# ── R-perfect: no 100 may fall ───────────────────────────────────────────────


def test_r_perfect_trips_and_names_the_document() -> None:
    r = _report({"a": 100.0, "b": 80.0}, {"a": 99.0, "b": 95.0}).r_perfect
    assert r.passed is False
    assert r.offenders == ("a",)


def test_r_perfect_passes_when_every_100_holds() -> None:
    r = _report({"a": 100.0, "b": 80.0}, {"a": 100.0, "b": 70.0}).r_perfect
    assert r.passed is True
    assert r.offenders == ()


def test_r_perfect_ignores_documents_that_were_not_perfect() -> None:
    # b collapses but was never at 100 — R-tail's business, not R-perfect's.
    assert _report({"a": 100.0, "b": 99.9}, {"a": 100.0, "b": 10.0}).r_perfect.passed is True


# ── R-92: the >92 count may not decrease ─────────────────────────────────────


def test_r_92_trips_when_the_count_drops() -> None:
    r = _report({"a": 95.0, "b": 93.0}, {"a": 95.0, "b": 91.0}).r_92
    assert r.passed is False
    assert r.offenders == ("b",)


def test_r_92_passes_when_a_faller_is_offset_by_a_riser() -> None:
    # The ratchet is on the COUNT, but the faller is still enumerated: C1's
    # deliberate exception is priced in enumeration, so the data must be there.
    r = _report({"a": 93.0, "b": 90.0}, {"a": 91.0, "b": 95.0}).r_92
    assert r.passed is True
    assert r.offenders == ("a",)


def test_r_92_boundary_is_strict() -> None:
    # Exactly 92 is not "above 92" — the band is open.
    assert _report({"a": 92.0}, {"a": 92.0}).r_92.passed is True
    assert _report({"a": 92.01}, {"a": 92.0}).r_92.passed is False


# ── R-tail: no drop over 10 points ───────────────────────────────────────────


def test_r_tail_trips_past_ten_points() -> None:
    r = _report({"a": 70.0, "b": 70.0}, {"a": 59.9, "b": 60.0}).r_tail
    assert r.passed is False
    assert r.offenders == ("a",)  # b dropped exactly 10 — allowed


def test_r_tail_passes_on_many_small_losses() -> None:
    baseline = {f"d{i}": 70.0 for i in range(20)}
    candidate = {f"d{i}": 61.0 for i in range(20)}
    assert _report(baseline, candidate).r_tail.passed is True


def test_r_tail_tolerates_float_noise_at_the_boundary() -> None:
    # 92.3 - 82.3 is 10.000000000000014 in binary floating point.
    assert _report({"a": 92.3}, {"a": 82.3}).r_tail.passed is True


# ── R-fail: the failure count may not increase ───────────────────────────────


def test_r_fail_trips_and_names_the_new_failures() -> None:
    r = _report({"a": 50.0}, {"a": 50.0}, baseline_failures=["x"], candidate_failures=["x", "y"]).r_fail
    assert r.passed is False
    assert r.offenders == ("y",)


def test_r_fail_passes_when_failures_are_traded_one_for_one() -> None:
    # The contract gates the COUNT; a swap is still enumerated for the report.
    r = _report({"a": 50.0}, {"a": 50.0}, baseline_failures=["x"], candidate_failures=["y"]).r_fail
    assert r.passed is True
    assert r.offenders == ("y",)


def test_r_fail_passes_when_failures_are_repaired() -> None:
    r = _report({"a": 50.0}, {"a": 50.0}, baseline_failures=["x", "y"], candidate_failures=["y"]).r_fail
    assert r.passed is True
    assert r.offenders == ()


def test_a_regression_into_failure_trips_r_perfect_via_itt_zero_fill() -> None:
    # The intended calling convention: ITT scores, failures zero-filled. A perfect
    # document that becomes a crash must not escape the comparison by leaving the
    # score map — it enters at 0.0 and trips R-perfect and R-tail.
    report = _report(
        {"a": 100.0, "b": 80.0},
        {"a": 0.0, "b": 80.0},
        candidate_failures=["a"],
    )
    assert report.r_perfect.offenders == ("a",)
    assert report.r_tail.offenders == ("a",)
    assert report.r_fail.passed is False
    assert report.passed is False


# ── whole-report verdict + corpus drift ──────────────────────────────────────


def test_clean_stage_passes_every_ratchet() -> None:
    report = _report({"a": 100.0, "b": 50.0, "c": 93.0}, {"a": 100.0, "b": 62.0, "c": 94.0})
    assert report.passed is True
    assert report.tripped == ()
    assert [r.name for r in report.ratchets] == ["R-perfect", "R-92", "R-fail", "R-tail"]


def test_documents_on_one_side_only_are_enumerated_and_void_the_comparison() -> None:
    report = _report({"a": 100.0, "gone": 100.0}, {"a": 100.0, "new": 100.0})
    assert report.only_in_baseline == ("gone",)
    assert report.only_in_candidate == ("new",)
    assert report.n_compared == 1
    assert report.corpus_stable is False
    # Every ratchet holds on the intersection, but the verdict is still not a pass:
    # a changed corpus voids the comparison the way C2 voids a stale sizing table.
    assert all(r.passed for r in report.ratchets)
    assert report.passed is False


# ── C2 census ────────────────────────────────────────────────────────────────


def test_census_on_hand_built_scores() -> None:
    scores = {
        "c1": 40.0, "c2": 55.5, "c3": 59.999,   # the [40,60) cluster
        "edge_lo": 39.9, "edge_hi": 60.0,        # just outside it
        "n1": 90.0, "n2": 92.0, "n3": 92.5, "n4": 99.9,  # near-miss pool
        "p1": 100.0, "p2": 99.9999995,           # perfect (within the aggregate tolerance)
        "dead": 12.0,
    }
    c = ratchet.census(scores, n_itt=13)
    assert c.cluster == ("c1", "c2", "c3")
    assert c.n_cluster == 3
    assert c.perfect == 2
    assert c.near_miss == ("n1", "n2", "n3", "n4")
    assert c.n_near_miss == 4
    assert c.near_miss_at_or_below_92 == 2          # 90.0 and 92.0
    assert c.above_92 == 4                          # 92.5, 99.9, and the two perfects
    assert c.majority_position == 7                 # 13 // 2 + 1
    assert c.shortfall_to_majority == 3


def test_census_shortfall_floors_at_zero() -> None:
    c = ratchet.census({f"d{i}": 99.0 for i in range(9)}, n_itt=9)
    assert c.above_92 == 9
    assert c.shortfall_to_majority == 0


def test_census_perfect_matches_the_recorded_exact_100_rule() -> None:
    # exact_100 in every bench.jsonl line comes from aggregate.compute_aggregate;
    # the ratchet MUST agree with it or a stage can pass C1 while the published
    # perfect count falls.
    for value in (100.0, 99.9999995, 99.999999, 99.995, 99.99, 92.0):
        scores = {"d": value}
        assert ratchet.census(scores).perfect == compute_aggregate(scores).exact_100, value


def test_census_default_denominator_is_the_itt_corpus() -> None:
    assert ratchet.census({}).n_itt == 763
    assert ratchet.census({}).majority_position == 382


# ── C2 census delta + the 10% void rule ──────────────────────────────────────


def _cluster_scores(names: list[str]) -> dict[str, float]:
    return {n: 50.0 for n in names}


def test_census_delta_reports_every_figure() -> None:
    before = ratchet.census({"a": 50.0, "b": 91.0, "c": 100.0}, n_itt=3)
    after = ratchet.census({"a": 95.0, "b": 91.0, "c": 100.0}, n_itt=3)
    d = ratchet.census_delta(before, after)
    assert d.d_cluster == -1
    assert d.d_above_92 == 1
    assert d.d_shortfall == -1
    assert d.d_near_miss == 1  # a left the cluster and landed in [90,100)
    assert d.d_near_miss_at_or_below_92 == 0
    assert d.d_perfect == 0
    assert d.left_cluster == ("a",)
    assert d.entered_cluster == ()


def test_pool_shift_under_ten_percent_keeps_the_sizing_table_alive() -> None:
    names = [f"d{i}" for i in range(100)]
    before = ratchet.census(_cluster_scores(names))
    after = ratchet.census(_cluster_scores(names[:91]))
    d = ratchet.census_delta(before, after)
    assert d.pool_shift_fraction == pytest.approx(-0.09)
    assert d.sizing_void is False


def test_pool_shift_over_ten_percent_voids_the_sizing_table() -> None:
    names = [f"d{i}" for i in range(100)]
    before = ratchet.census(_cluster_scores(names))
    after = ratchet.census(_cluster_scores(names[:89]))
    d = ratchet.census_delta(before, after)
    assert d.pool_shift_fraction == pytest.approx(-0.11)
    assert d.sizing_void is True


def test_a_wholly_swapped_cluster_of_the_same_size_also_voids() -> None:
    # Same size, different documents: the sizing table was built on the members,
    # not on the count, so "unchanged size" must not read as "unchanged pool".
    before = ratchet.census(_cluster_scores([f"a{i}" for i in range(50)]))
    after = ratchet.census(_cluster_scores([f"b{i}" for i in range(50)]))
    d = ratchet.census_delta(before, after)
    assert d.pool_shift_fraction == pytest.approx(0.0)
    assert d.pool_churn_fraction == pytest.approx(2.0)
    assert d.sizing_void is True


def test_empty_before_cluster_is_not_a_division_by_zero() -> None:
    empty = ratchet.census({})
    assert ratchet.census_delta(empty, empty).sizing_void is False
    grew = ratchet.census_delta(empty, ratchet.census({"a": 50.0}))
    assert grew.pool_shift_fraction == float("inf")
    assert grew.sizing_void is True


# ── the recorded run the three plans were sized from ─────────────────────────


@pytest.mark.skipif(not BENCH_JSONL.is_file(), reason="results/bench.jsonl absent")
def test_real_jubarte_rust_census_matches_the_execution_contract() -> None:
    run = ratchet.load_run(BENCH_JSONL, JUBARTE_RUST_RUN)
    assert run is not None, f"run {JUBARTE_RUST_RUN} not in {BENCH_JSONL}"
    assert run.vendor == "jubarte-rust"
    c = ratchet.census(run.itt_scores, n_itt=run.itt_n_docs)
    # Figures quoted in plans/jubarte-execution-contract.md and the three stage
    # tables that bind to it. These are not free parameters.
    assert c.n_cluster == 197              # the ≈50 cluster, [40,60)
    assert c.above_92 == 282
    assert c.shortfall_to_majority == 100  # 382 - 282
    assert c.n_near_miss == 149            # [90,100)
    assert c.near_miss_at_or_below_92 == 25
    assert c.perfect == 158


@pytest.mark.skipif(not BENCH_JSONL.is_file(), reason="results/bench.jsonl absent")
def test_real_run_agrees_with_its_own_recorded_aggregates() -> None:
    run = ratchet.load_run(BENCH_JSONL, JUBARTE_RUST_RUN)
    assert run is not None
    c = ratchet.census(run.itt_scores, n_itt=run.itt_n_docs)
    line = next(
        json.loads(raw)
        for raw in BENCH_JSONL.read_text().splitlines()
        if raw.strip() and json.loads(raw).get("id_run") == JUBARTE_RUST_RUN
    )
    assert c.perfect == line["exact_100"]
    assert c.perfect + c.n_near_miss == line["at_least_90"]
    assert run.itt_n_docs == line["itt_n_docs"]


@pytest.mark.skipif(not BENCH_JSONL.is_file(), reason="results/bench.jsonl absent")
def test_a_run_compared_with_itself_trips_nothing() -> None:
    run = ratchet.load_run(BENCH_JSONL, JUBARTE_RUST_RUN)
    assert run is not None
    report = ratchet.evaluate_ratchets(
        run.itt_scores,
        run.itt_scores,
        baseline_failures=run.failure_docs,
        candidate_failures=run.failure_docs,
    )
    assert report.passed is True
    assert report.n_compared == 763


def test_load_run_returns_none_for_an_unknown_id(tmp_path) -> None:
    p = tmp_path / "bench.jsonl"
    p.write_text(json.dumps({"id_run": "x", "vendor": "v", "scores": {}}) + "\n")
    assert ratchet.load_run(p, "not-here") is None
    assert ratchet.load_run(tmp_path / "absent.jsonl", "x") is None


def test_load_run_zero_fills_failures_into_itt_scores(tmp_path) -> None:
    p = tmp_path / "bench.jsonl"
    p.write_text(
        json.dumps(
            {
                "id_run": "x",
                "vendor": "v",
                "tool_version": "v@1",
                "scores": {"a": 91.0},
                "itt_n_docs": 2,
                "failures": [{"doc": "b", "stage": "render", "error": "boom"}],
            },
        )
        + "\n",
    )
    run = ratchet.load_run(p, "x")
    assert run is not None
    assert run.failure_docs == ("b",)
    assert run.itt_scores == {"a": 91.0, "b": 0.0}
    assert run.scores == {"a": 91.0}
