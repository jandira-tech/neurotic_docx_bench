"""Failure-cluster mining (plan Chapter 4.5 step 2)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mine_failure_clusters.py"


def _load():
    spec = importlib.util.spec_from_file_location("mine_failure_clusters", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mine_failure_clusters"] = mod
    spec.loader.exec_module(mod)
    return mod


mfc = _load()


def test_recoverable_points_are_measured_against_the_whole_corpus():
    """A tag on 1 of 100 documents cannot recover more than its own shortfall/100.

    Normalising by the tagged count instead would make a single catastrophic
    document outrank a cluster of 30 mediocre ones, which is backwards: the
    headline mean is what the campaign moves.
    """
    scores = {f"d{i}": 100.0 for i in range(99)}
    scores["d99"] = 0.0
    tags = {"d99": {"rare"}}
    clusters, _ = mfc.mine(scores, tags, threshold=70.0, target=90.0)
    assert len(clusters) == 1
    assert clusters[0].tag == "rare"
    assert clusters[0].recoverable == 90.0 / 100


def test_a_broad_shallow_cluster_outranks_one_deep_document():
    scores = {f"a{i}": 60.0 for i in range(30)}  # 30 docs, 30 points each
    scores["deep"] = 0.0  # 1 doc, 90 points
    tags = {**{f"a{i}": {"broad"} for i in range(30)}, "deep": {"narrow"}}
    clusters, _ = mfc.mine(scores, tags, threshold=70.0, target=90.0)
    assert [c.tag for c in clusters] == ["broad", "narrow"]
    assert clusters[0].recoverable > clusters[1].recoverable


def test_documents_above_target_contribute_nothing_even_when_below_threshold():
    """With threshold=95 and target=90, a doc at 92 is 'failing' but already past
    the target — counting a negative shortfall would inflate the ranking."""
    scores = {"x": 92.0, "y": 100.0}
    clusters, _ = mfc.mine(scores, {"x": {"t"}}, threshold=95.0, target=90.0)
    assert clusters[0].recoverable == 0.0


def test_passing_documents_never_enter_the_ranking():
    scores = {"good": 95.0, "bad": 10.0}
    tags = {"good": {"shared"}, "bad": {"shared"}}
    clusters, _ = mfc.mine(scores, tags, threshold=70.0, target=90.0)
    assert clusters[0].n_tagged == 2
    assert clusters[0].n_failing == 1
    assert clusters[0].median_failing == 10.0


def test_failing_documents_with_no_tags_are_reported_not_dropped():
    """Silently omitting untagged failures makes the ranking look complete when a
    whole slice of the corpus has no coverage entry — exactly the case when a new
    subcorpus lands before its tags are generated."""
    scores = {"tagged": 10.0, "untagged": 5.0}
    clusters, untagged = mfc.mine(scores, {"tagged": {"t"}}, threshold=70.0, target=90.0)
    assert untagged == ["untagged"]
    assert [c.tag for c in clusters] == ["t"]


def test_tag_keys_are_matched_case_insensitively(tmp_path: Path):
    """Scorer keys are lower-cased by pipeline.redline_key; a coverage file that
    preserves case must still join, or the miner reports an empty ranking."""
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps({"pairs": {"SD_732_Hello": {"features": ["tables"], "revisions": ["rev_ins"]}}}))
    tags = mfc.load_tags([path])
    assert tags == {"sd_732_hello": {"tables", "rev_ins"}}


def test_load_tags_merges_multiple_corpora(tmp_path: Path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"pairs": {"k": {"features": ["f1"], "revisions": []}}}))
    b.write_text(json.dumps({"pairs": {"k": {"features": [], "revisions": ["r1"]}, "k2": {"features": ["f2"]}}}))
    tags = mfc.load_tags([a, b])
    assert tags["k"] == {"f1", "r1"}
    assert tags["k2"] == {"f2"}


def test_missing_coverage_file_is_skipped_not_fatal(tmp_path: Path):
    assert mfc.load_tags([tmp_path / "nope.json"]) == {}


def test_latest_scores_prefers_the_last_matching_line_and_skips_holdout_only(tmp_path: Path):
    """`holdout_mode == "only"` lines are the sealed n=20 view; mining them ranks the
    holdout instead of the corpus."""
    jsonl = tmp_path / "bench.jsonl"
    jsonl.write_text(
        json.dumps({"vendor": "v", "benchmark": "script_redlines", "scores": {"a": 1.0}})
        + "\n"
        + json.dumps({"vendor": "v", "benchmark": "script_redlines", "scores": {"a": 2.0}})
        + "\n"
        + json.dumps({"vendor": "v", "benchmark": "script_redlines", "holdout_mode": "only", "scores": {"a": 99.0}})
        + "\n",
    )
    assert mfc.latest_scores(jsonl, "v") == {"a": 2.0}


def test_holdout_excluded_is_the_headline_run_and_must_be_mined(tmp_path: Path):
    """Every normal run since PR12 carries holdout_mode="excluded". Treating any
    truthy holdout_mode as "skip" silently mined a stale pre-holdout line instead —
    the miner reported 164 documents on an 763-document corpus and looked fine."""
    jsonl = tmp_path / "bench.jsonl"
    jsonl.write_text(
        json.dumps({"vendor": "v", "benchmark": "script_redlines", "scores": {"old": 1.0}})
        + "\n"
        + json.dumps(
            {"vendor": "v", "benchmark": "script_redlines", "holdout_mode": "excluded", "scores": {"new": 2.0}},
        )
        + "\n",
    )
    assert mfc.latest_scores(jsonl, "v") == {"new": 2.0}


def test_empty_score_set_does_not_divide_by_zero():
    assert mfc.mine({}, {}, threshold=70.0, target=90.0) == ([], [])
