"""Spec for the mini-bench selection (``scripts/mini_bench.py``): the worst n documents of
one converter run plus n/4 spread over the rest of its distribution, reproducible by name."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "mini_bench.py"


def _load():
    spec = importlib.util.spec_from_file_location("mini_bench", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mini_bench"] = mod
    spec.loader.exec_module(mod)
    return mod


mb = _load()


def _scores(k: int) -> dict[str, float]:
    return {f"clean__d{i:04d}": float(i) for i in range(k)}


def test_worst_n_are_the_lowest_scores():
    picked = mb.select_docs(_scores(100), n=20)
    worst = [p for p in picked if p.bucket == "worst"]
    assert [p.key for p in worst] == [f"clean__d{i:04d}" for i in range(20)]
    assert [p.rank for p in worst] == list(range(1, 21))


def test_spread_is_a_quarter_of_n_over_the_rest():
    picked = mb.select_docs(_scores(100), n=20)
    spread = [p for p in picked if p.bucket == "spread"]
    assert len(spread) == 5
    # The rest is d0020..d0099 (80 docs): the midpoints of five strata of 16.
    assert [p.key for p in spread] == [f"clean__d{20 + j:04d}" for j in (8, 24, 40, 56, 72)]
    assert all(p.key not in {w.key for w in picked if w.bucket == "worst"} for p in spread)


def test_failed_documents_count_as_zero_and_ties_break_by_key():
    scores = {"clean__b": 10.0, "clean__a": 10.0, "clean__c": 50.0}
    picked = mb.select_docs(scores, n=3, failed=["clean__z"])
    assert [p.key for p in picked] == ["clean__z", "clean__a", "clean__b"]
    assert picked[0].score == 0.0


def test_small_run_takes_everything_once():
    picked = mb.select_docs(_scores(6), n=4)
    keys = [p.key for p in picked]
    assert len(keys) == len(set(keys)) == 5  # 4 worst + 1 spread of the remaining 2


def test_max_pages_drops_longer_documents_before_ranking():
    scores = {"clean__long": 1.0, "clean__short": 2.0, "clean__three": 3.0}
    pages = {"clean__long": 4, "clean__short": 1, "clean__three": 3}
    kept = mb.filter_pages(scores, pages.__getitem__, max_pages=3)
    assert kept == {"clean__short": 2.0, "clean__three": 3.0}
    assert mb.filter_pages(scores, pages.__getitem__, max_pages=None) == scores


def test_itt_reads_per_doc_and_counts_a_missing_document_as_zero():
    pixel = {"per_doc": {"clean__a": 80.0}}
    docxide = {"per_doc": {"clean__a": {"jaccard": 40.0, "text_boundary": 100.0}}}
    assert mb._itt(pixel, ["clean__a", "clean__b"], None) == [80.0, 0.0]
    assert mb._itt(docxide, ["clean__a", "clean__b"], "jaccard") == [40.0, 0.0]


def test_key_splits_into_state_and_stem():
    assert mb.split_key("with_comments_clean__abc_def") == ("with_comments_clean", "abc_def")
