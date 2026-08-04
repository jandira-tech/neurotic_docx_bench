"""Cluster lens partition (S0.1 — Stage L1).

The ≈50 cluster is the single largest lever in the lossless plan, and Stage L1
exists to find out what it *is* before any engine work starts. The load-bearing
assertion in this file is the gate: if the markup is correct and the SCORER
disagrees on more than ~15% of the cluster, L2 would be optimising the engine
against our own bug. Everything else here protects that number from being
computed on the wrong denominator.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from neurotic_docx_bench.diagnostics import cluster_lens
from neurotic_docx_bench.functional_lens import FunctionalVerdict

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_JSONL = REPO_ROOT / "results" / "bench.jsonl"

# The recorded jubarte-lossless script_redlines run the plan's arithmetic was
# derived from (plans/jubarte-lossless-to-target.md, "Supporting shape").
LOSSLESS_RUN = "019fcc6f-4eb8-72f7-957e-799895a04342"
LOSSLESS_CLUSTER_N = 166


def _verdict(accept: bool | None, reject: bool | None, *, blind: bool = False,
             error: str | None = None) -> FunctionalVerdict:
    """A lens outcome without running the lens — strict flags mirror the headline
    ones, since the partition reads only the tolerant ``*_ok`` pair."""
    return FunctionalVerdict(accept, reject, accept, reject, error=error, blind=blind)


BOTH = _verdict(True, True)
REJECT_ONLY = _verdict(False, True)
ACCEPT_ONLY = _verdict(True, False)
NEITHER = _verdict(False, False)


# ── cluster selection ────────────────────────────────────────────────────────


def test_select_cluster_half_open_interval() -> None:
    # The off-by-one that decides whether the plan's 166 is the same 166:
    # exactly 40.0 is IN, exactly 60.0 is OUT.
    scores = {"lo": 40.0, "mid": 51.5, "hi": 60.0, "under": 39.999, "over": 60.001}
    assert cluster_lens.select_cluster(scores) == ("lo", "mid")


def test_select_cluster_custom_band() -> None:
    scores = {"a": 89.9, "b": 90.0, "c": 99.9, "d": 100.0}
    assert cluster_lens.select_cluster(scores, low=90.0, high=100.0) == ("b", "c")


def test_select_cluster_sorted_by_name_not_insertion_order() -> None:
    # Deterministic across runs: two documents with the SAME score must not
    # depend on dict order for their position.
    scores = {"z_doc": 50.0, "a_doc": 50.0, "m_doc": 50.0}
    assert cluster_lens.select_cluster(scores) == ("a_doc", "m_doc", "z_doc")


def test_select_cluster_ignores_non_numeric_and_nan() -> None:
    # NaN compares False against every bound, so it drops out on its own; the
    # test pins that rather than leaving it to luck.
    scores = {"ok": 50.0, "text": "50.0", "none": None, "nan": float("nan")}
    assert cluster_lens.select_cluster(scores) == ("ok",)  # type: ignore[arg-type]


def test_select_cluster_empty() -> None:
    assert cluster_lens.select_cluster({}) == ()
    assert cluster_lens.select_cluster({"a": 10.0}) == ()


def test_select_cluster_rejects_inverted_band() -> None:
    with pytest.raises(ValueError):
        cluster_lens.select_cluster({"a": 50.0}, low=60.0, high=40.0)


def test_real_lossless_run_has_166_cluster_documents() -> None:
    """The plan's whole L2 sizing rests on this count. If it moves, the plan's
    arithmetic moves with it — that is a finding, not a test to adjust."""
    if not BENCH_JSONL.is_file():
        pytest.skip(f"{BENCH_JSONL} not present in this checkout")
    scores = None
    with BENCH_JSONL.open(encoding="utf-8") as handle:
        for raw in handle:
            # Cheap pre-filter: the file is ~27 MB and only one line can match.
            if LOSSLESS_RUN not in raw:
                continue
            line = json.loads(raw)
            if line.get("id_run") == LOSSLESS_RUN:
                scores = line.get("scores")
                break
    assert scores, f"run {LOSSLESS_RUN} carries no per-document scores in {BENCH_JSONL}"
    assert len(cluster_lens.select_cluster(scores)) == LOSSLESS_CLUSTER_N


# ── partition ────────────────────────────────────────────────────────────────


def test_partition_all_four_buckets() -> None:
    part = cluster_lens.partition({
        "both": BOTH, "rej": REJECT_ONLY, "acc": ACCEPT_ONLY, "none": NEITHER,
    })
    assert part.buckets == {
        "both": cluster_lens.Bucket.BOTH_HOLD,
        "rej": cluster_lens.Bucket.REJECT_ONLY,
        "acc": cluster_lens.Bucket.ACCEPT_ONLY,
        "none": cluster_lens.Bucket.NEITHER,
    }
    assert part.unjudged == {}
    assert part.n_judged == 4


def test_partition_counts_cover_every_bucket() -> None:
    part = cluster_lens.partition({"a": BOTH, "b": BOTH, "c": NEITHER})
    assert part.counts == {
        cluster_lens.Bucket.BOTH_HOLD: 2,
        cluster_lens.Bucket.REJECT_ONLY: 0,
        cluster_lens.Bucket.ACCEPT_ONLY: 0,
        cluster_lens.Bucket.NEITHER: 1,
    }
    # Every bucket is a key even at zero, so a summary table has fixed columns.
    assert set(part.counts) == set(cluster_lens.Bucket)


def test_partition_members_are_sorted_per_bucket() -> None:
    part = cluster_lens.partition({"z": BOTH, "a": BOTH, "m": NEITHER})
    assert part.members(cluster_lens.Bucket.BOTH_HOLD) == ("a", "z")
    assert part.members(cluster_lens.Bucket.NEITHER) == ("m",)
    assert part.members(cluster_lens.Bucket.ACCEPT_ONLY) == ()


def test_partition_blind_doc_is_unjudged_not_both_hold() -> None:
    """A blind pair (base text == next text) satisfies both invariants for a
    candidate that does nothing at all. Counting it as BOTH_HOLD would inflate
    the exact fraction the gate reads — the false STOP this module exists to
    avoid."""
    part = cluster_lens.partition({"blind": _verdict(True, True, blind=True)})
    assert part.buckets == {}
    assert part.unjudged == {"blind": "blind"}
    assert part.n_judged == 0


def test_partition_errored_and_partial_verdicts_are_unjudged() -> None:
    # FunctionalVerdict contract: None means the check could not run, never a fail.
    part = cluster_lens.partition({
        "boom": _verdict(None, None, error="ValueError: no w:body"),
        "half": _verdict(None, True),
        "ok": NEITHER,
    })
    assert part.buckets == {"ok": cluster_lens.Bucket.NEITHER}
    assert set(part.unjudged) == {"boom", "half"}
    assert part.unjudged["boom"].startswith("error: ValueError")
    assert part.unjudged["half"] == "partial"


def test_partition_every_document_accounted_for() -> None:
    results = {"a": BOTH, "b": NEITHER, "c": _verdict(None, None, error="x"),
               "d": _verdict(True, True, blind=True)}
    part = cluster_lens.partition(results)
    assert set(part.buckets) | set(part.unjudged) == set(results)
    assert not set(part.buckets) & set(part.unjudged)  # exactly one home each


def test_partition_empty() -> None:
    part = cluster_lens.partition({})
    assert part.buckets == {} and part.unjudged == {} and part.n_judged == 0


# ── the L1 gate ──────────────────────────────────────────────────────────────


def _partition_of(n_both_hold: int, n_total: int) -> cluster_lens.ClusterPartition:
    results: dict[str, FunctionalVerdict] = {
        f"doc_{i:03d}": (BOTH if i < n_both_hold else NEITHER) for i in range(n_total)
    }
    return cluster_lens.partition(results)


def test_gate_below_threshold_proceeds() -> None:
    outcome = cluster_lens.gate(_partition_of(7, 50))  # 14%
    assert outcome.verdict is cluster_lens.GateVerdict.PROCEED
    assert outcome.both_hold_fraction == pytest.approx(0.14)


def test_gate_at_exactly_15_percent_proceeds() -> None:
    """The plan says bucket 1 must *exceed* ~15% to stop, so the boundary itself
    passes. Strict ``>``; equality is not a stop."""
    outcome = cluster_lens.gate(_partition_of(3, 20))  # exactly 15%
    assert outcome.both_hold_fraction == 0.15
    assert outcome.verdict is cluster_lens.GateVerdict.PROCEED


def test_gate_above_threshold_stops() -> None:
    outcome = cluster_lens.gate(_partition_of(8, 50))  # 16%
    assert outcome.verdict is cluster_lens.GateVerdict.STOP_FIX_SCORER
    assert outcome.both_hold_fraction == pytest.approx(0.16)
    assert outcome.n_both_hold == 8
    assert outcome.n_judged == 50


def test_gate_reason_is_human_readable_and_carries_the_numbers() -> None:
    reason = cluster_lens.gate(_partition_of(8, 50)).reason
    assert "16" in reason and "8" in reason and "50" in reason
    assert "scorer" in reason.lower()


def test_gate_custom_threshold() -> None:
    part = _partition_of(8, 50)  # 16%
    assert cluster_lens.gate(part, threshold=0.20).verdict is cluster_lens.GateVerdict.PROCEED
    assert cluster_lens.gate(part, threshold=0.10).verdict is cluster_lens.GateVerdict.STOP_FIX_SCORER


def test_gate_denominator_excludes_unjudged() -> None:
    # 2 BOTH_HOLD of 10 judged is 20% and must stop, even though 2 of 12 docs
    # (16.7%) would also stop — the point is that the blind docs never enter.
    results: dict[str, FunctionalVerdict] = {f"d{i}": NEITHER for i in range(8)}
    results |= {"b0": BOTH, "b1": BOTH}
    results |= {f"blind{i}": _verdict(True, True, blind=True) for i in range(2)}
    outcome = cluster_lens.gate(cluster_lens.partition(results))
    assert outcome.n_judged == 10
    assert outcome.both_hold_fraction == pytest.approx(0.20)


def test_gate_on_empty_cluster_proceeds_but_says_so() -> None:
    outcome = cluster_lens.gate(cluster_lens.partition({}))
    assert outcome.verdict is cluster_lens.GateVerdict.PROCEED
    assert outcome.both_hold_fraction == 0.0
    assert outcome.n_judged == 0
    assert "no judgeable" in outcome.reason.lower()


# ── cross-tabulation ─────────────────────────────────────────────────────────


def test_cross_tabulate_attributes_buckets_to_feature_tokens() -> None:
    part = cluster_lens.partition({
        "ooxml_rstyle_linked": BOTH,
        "ooxml_math_delimiter": NEITHER,
        "rtl_header_footer": NEITHER,
    })
    table = cluster_lens.cross_tabulate(part)
    assert table["ooxml"] == Counter({
        cluster_lens.Bucket.BOTH_HOLD: 1, cluster_lens.Bucket.NEITHER: 1,
    })
    assert table["rtl"] == Counter({cluster_lens.Bucket.NEITHER: 1})
    assert table["rstyle"] == Counter({cluster_lens.Bucket.BOTH_HOLD: 1})


def test_cross_tabulate_splits_on_hyphen_as_well_as_underscore() -> None:
    part = cluster_lens.partition({"rtl-header_footer": NEITHER})
    assert set(cluster_lens.cross_tabulate(part)) == {"rtl", "header", "footer"}


def test_cross_tabulate_counts_a_repeated_token_once_per_document() -> None:
    # Pair names concatenate both sides, so a family token routinely appears
    # twice in one name. Counting it twice would double-count the document.
    part = cluster_lens.partition({"math_limit_tests_math_matrix_tests": NEITHER})
    assert cluster_lens.cross_tabulate(part)["math"] == Counter(
        {cluster_lens.Bucket.NEITHER: 1},
    )


def test_cross_tabulate_drops_stop_words_and_content_hashes() -> None:
    part = cluster_lens.partition({"behavior__math_tests_36ab389c_super_editor__diff": BOTH})
    tokens = set(cluster_lens.cross_tabulate(part))
    assert "math" in tokens
    for noise in ("behavior", "super", "editor", "tests", "36ab389c", ""):
        assert noise not in tokens


def test_cross_tabulate_drops_pure_digit_tokens() -> None:
    part = cluster_lens.partition({"sd_2447_toc_tab_alignment": BOTH})
    tokens = set(cluster_lens.cross_tabulate(part))
    assert tokens == {"toc", "tab", "alignment"}


def test_cross_tabulate_excludes_unjudged_documents() -> None:
    part = cluster_lens.partition({
        "rtl_one": NEITHER, "rtl_two": _verdict(True, True, blind=True),
    })
    assert cluster_lens.cross_tabulate(part)["rtl"].total() == 1


def test_cross_tabulate_accepts_an_injected_tokenizer() -> None:
    part = cluster_lens.partition({"anything_at_all": BOTH})
    table = cluster_lens.cross_tabulate(part, tokenizer=lambda name: [name[:3]])
    assert table == {"any": Counter({cluster_lens.Bucket.BOTH_HOLD: 1})}


def test_cross_tabulate_empty_partition() -> None:
    assert cluster_lens.cross_tabulate(cluster_lens.partition({})) == {}


def test_stop_words_is_a_module_constant() -> None:
    assert isinstance(cluster_lens.STOP_WORDS, frozenset)
    assert "behavior" in cluster_lens.STOP_WORDS


# ── recorded-results adapter ─────────────────────────────────────────────────


def test_verdicts_from_per_doc_round_trips_the_lens_fields() -> None:
    per_doc = {
        "a": {"functional_accept_ok": True, "functional_reject_ok": True},
        "b": {"functional_accept_ok": True, "functional_reject_ok": False},
        "c": {"functional_accept_ok": True, "functional_reject_ok": True,
              "functional_blind": True},
        "d": {"overall_score": 50.0},  # lens never ran on this doc
    }
    verdicts = cluster_lens.verdicts_from_per_doc(per_doc)
    part = cluster_lens.partition(verdicts)
    assert part.buckets == {
        "a": cluster_lens.Bucket.BOTH_HOLD, "b": cluster_lens.Bucket.ACCEPT_ONLY,
    }
    assert set(part.unjudged) == {"c", "d"}


def test_verdicts_from_per_doc_restricted_to_a_cluster() -> None:
    per_doc = {
        "in": {"functional_accept_ok": True, "functional_reject_ok": True},
        "out": {"functional_accept_ok": False, "functional_reject_ok": False},
    }
    verdicts = cluster_lens.verdicts_from_per_doc(per_doc, keys=("in",))
    assert set(verdicts) == {"in"}
