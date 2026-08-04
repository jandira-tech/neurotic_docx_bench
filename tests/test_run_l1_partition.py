"""Stage L1 partition runner (scripts/run_l1_partition.py).

The runner is mostly orchestration — select a cluster, regenerate its candidates,
run the functional lens, partition — and the orchestration is exercised for real
by the committed result. What is tested here is the logic that could be wrong
*silently*: reading scores out of a recorded detail file, restricting a manifest
to the cluster, keying regenerated candidates back to pair stems, ranking
cross-tabulated tokens, and the regeneration control that checks fresh verdicts
against the ones the original run recorded.
"""

from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import pytest

from neurotic_docx_bench.diagnostics.cluster_lens import Bucket
from neurotic_docx_bench.functional_lens import FunctionalVerdict

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_l1_partition.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_l1_partition", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_l1_partition"] = mod
    spec.loader.exec_module(mod)
    return mod


l1 = _load()


# --- scores_from_detail ------------------------------------------------------


def test_scores_are_read_from_the_named_field_only():
    """The detail file carries eight score fields that disagree by up to 4 points.

    Only ``overall_score_pagefair`` reproduces the published run figures, so the
    field is named explicitly and never guessed — a cluster selected on
    ``average_score`` is a different set of documents.
    """
    per_doc = {
        "a": {"overall_score_pagefair": 51.0, "average_score": 88.0},
        "b": {"overall_score_pagefair": 99.0, "average_score": 12.0},
    }
    assert l1.scores_from_detail(per_doc) == {"a": 51.0, "b": 99.0}
    assert l1.scores_from_detail(per_doc, field="average_score") == {"a": 88.0, "b": 12.0}


def test_a_field_that_names_nothing_raises_instead_of_selecting_an_empty_cluster():
    """A renamed or misspelled score field would otherwise yield zero scores, an
    empty cluster, and a gate that PROCEEDs on no evidence at all."""
    with pytest.raises(ValueError, match="no numeric"):
        l1.scores_from_detail({"a": {"overall_score_pagefair": 51.0}}, field="typo_score")


def test_records_missing_the_field_are_skipped_not_defaulted():
    """``score_v2`` is present on 195 of 763 records. Defaulting a missing score
    to 0.0 would drag absent documents into the [40,60) neighbourhood by
    fabrication; they are simply not scored on that field."""
    per_doc = {"a": {"overall_score_pagefair": 51.0}, "b": {}, "c": {"overall_score_pagefair": None}}
    assert l1.scores_from_detail(per_doc) == {"a": 51.0}


# --- filter_manifest ---------------------------------------------------------


def _write_manifest(path: Path, stems: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["pair_stem", "base", "next", "origin"])
        w.writeheader()
        for s in stems:
            w.writerow({"pair_stem": s, "base": f"{s}_b", "next": f"{s}_n", "origin": "x"})


def test_filter_manifest_keeps_only_cluster_rows_and_preserves_the_schema(tmp_path):
    """The generator reads the manifest with its own CSV parser and needs every
    column it expects; a filtered manifest that drops columns fails at parse
    time, not at generate time."""
    src, out = tmp_path / "in.csv", tmp_path / "out.csv"
    _write_manifest(src, ["keep_one", "drop_me", "keep_two"])
    selected = l1.filter_manifest(src, {"keep_one", "keep_two"}, out)
    assert selected == ("keep_one", "keep_two")
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert [r["pair_stem"] for r in rows] == ["keep_one", "keep_two"]
    assert list(rows[0]) == ["pair_stem", "base", "next", "origin"]


def test_filter_manifest_matches_case_insensitively():
    """per_doc keys are lower-cased by ``redline_key``; manifest pair_stems are
    not guaranteed to be. Matching case-sensitively would silently drop the
    mixed-case pairs from the regeneration set and shrink the denominator."""
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        src, out = Path(td) / "in.csv", Path(td) / "out.csv"
        _write_manifest(src, ["MixedCase_Pair"])
        assert l1.filter_manifest(src, {"mixedcase_pair"}, out) == ("mixedcase_pair",)
        assert [r["pair_stem"] for r in csv.DictReader(out.open())] == ["MixedCase_Pair"]


def test_filter_manifest_writes_nothing_when_no_row_matches(tmp_path):
    """A pool contributing no cluster documents must not be handed to the
    generator: an empty manifest generates zero redlines and exits 1, which
    would read as a regeneration failure rather than an empty selection."""
    src, out = tmp_path / "in.csv", tmp_path / "out.csv"
    _write_manifest(src, ["not_wanted"])
    assert l1.filter_manifest(src, {"other"}, out) == ()
    assert not out.exists()


# --- index_candidates --------------------------------------------------------


def test_candidates_are_keyed_by_pair_stem_with_the_tool_suffix_stripped(tmp_path):
    """Regenerated files are ``<pair>_<tool>_redline.docx``; the lens and the
    recorded per_doc are both keyed by ``<pair>``."""
    (tmp_path / "a_b_jubarte-final-lossless_redline.docx").write_bytes(b"x")
    (tmp_path / "c_d_jubarte-final-lossless_redline.docx").write_bytes(b"x")
    index = l1.index_candidates(tmp_path, "jubarte-final-lossless")
    assert sorted(index) == ["a_b", "c_d"]


def test_present_candidates_are_counted_by_existence_not_by_creation(tmp_path):
    """The generator skips a pair whose output file already exists (no --force),
    so a re-run creates nothing and a "files created" count reports 0 written
    for a pool that is in fact fully covered. The report must say how many of
    the requested candidates *exist*, which is what the lens then consumes.
    """
    (tmp_path / "a_b_tool_redline.docx").write_bytes(b"x")
    (tmp_path / "unrelated_pair_tool_redline.docx").write_bytes(b"x")
    assert l1.count_present(tmp_path, "tool", ["a_b", "c_d"]) == 1


def test_word_lock_files_are_not_mistaken_for_candidates(tmp_path):
    """Word leaves ``~$name.docx`` owner-lock files next to open documents. The
    bench's own candidate indexing skips them and so does this."""
    (tmp_path / "a_b_jubarte-final-lossless_redline.docx").write_bytes(b"x")
    (tmp_path / "~$a_b_jubarte-final-lossless_redline.docx").write_bytes(b"x")
    assert sorted(l1.index_candidates(tmp_path, "jubarte-final-lossless")) == ["a_b"]


# --- top_tokens --------------------------------------------------------------


def test_top_tokens_ranks_by_population_and_reports_concentration():
    """A token's bucket count answers "how much of this bucket is this family",
    and its concentration answers "is this family characteristic of the bucket
    or just large". Reporting only the first would surface every ubiquitous
    token; reporting only the second would surface every n=1 token at 100%."""
    from collections import Counter

    table = {
        "math": Counter({Bucket.BOTH_HOLD: 9, Bucket.NEITHER: 1}),
        "rtl": Counter({Bucket.BOTH_HOLD: 4, Bucket.NEITHER: 4}),
    }
    stats = l1.top_tokens(table, Bucket.BOTH_HOLD, min_docs=1)
    assert [s.token for s in stats] == ["math", "rtl"]
    assert stats[0].n_in_bucket == 9
    assert stats[0].n_token_judged == 10
    assert stats[0].concentration == pytest.approx(0.9)
    assert stats[1].concentration == pytest.approx(0.5)


def test_top_tokens_drops_tokens_below_the_minimum_population():
    """A token carried by one document explains nothing and would crowd out the
    families that do — the same reason the cross-tab drops content hashes."""
    from collections import Counter

    table = {"big": Counter({Bucket.NEITHER: 5}), "singleton": Counter({Bucket.NEITHER: 1})}
    assert [s.token for s in l1.top_tokens(table, Bucket.NEITHER, min_docs=3)] == ["big"]


def test_top_tokens_is_empty_for_an_unpopulated_bucket():
    from collections import Counter

    table = {"math": Counter({Bucket.BOTH_HOLD: 9})}
    assert l1.top_tokens(table, Bucket.NEITHER, min_docs=1) == ()


# --- compare_to_recorded (the regeneration control) --------------------------


def test_regeneration_control_counts_agreement_against_recorded_verdicts():
    """The run directory is gone, so "did I regenerate the same candidates?"
    cannot be answered by comparing bytes. It can be answered on the 46 cluster
    documents whose verdicts the original run recorded: if the fresh lens
    reproduces every one of them, the regenerated candidates behave identically
    on the only axis this stage reads."""
    fresh = {
        "a": FunctionalVerdict(True, True, True, True),
        "b": FunctionalVerdict(True, False, True, False),
    }
    per_doc = {
        "a": {"functional_accept_ok": True, "functional_reject_ok": True, "functional_blind": False},
        "b": {"functional_accept_ok": True, "functional_reject_ok": False, "functional_blind": False},
    }
    control = l1.compare_to_recorded(fresh, per_doc)
    assert control.n_compared == 2
    assert control.n_agree == 2
    assert control.disagreements == ()


def test_regeneration_control_reports_the_documents_that_disagree():
    """A disagreement is the finding, not a warning to average away — it means
    the regenerated candidate is not the scored candidate and the partition
    describes a different artefact than the published run."""
    fresh = {"a": FunctionalVerdict(False, True, False, True)}
    per_doc = {
        "a": {"functional_accept_ok": True, "functional_reject_ok": True, "functional_blind": False}
    }
    control = l1.compare_to_recorded(fresh, per_doc)
    assert control.n_compared == 1
    assert control.n_agree == 0
    assert len(control.disagreements) == 1
    assert control.disagreements[0]["doc"] == "a"
    assert control.disagreements[0]["recorded"]["accept_ok"] is True
    assert control.disagreements[0]["fresh"]["accept_ok"] is False


def test_documents_with_no_recorded_verdict_are_not_counted_as_agreement():
    """120 of the 166 cluster documents were never lensed by the original run —
    the lens only saw the word_based pool. Counting them as agreement would
    report a 100% control on a check that ran on 27% of the cluster."""
    fresh = {"a": FunctionalVerdict(True, True, True, True), "b": FunctionalVerdict(True, True, True, True)}
    per_doc = {
        "a": {"functional_accept_ok": True, "functional_reject_ok": True, "functional_blind": False},
        "b": {},
    }
    control = l1.compare_to_recorded(fresh, per_doc)
    assert control.n_compared == 1
    assert control.n_agree == 1
    assert control.n_no_recorded_verdict == 1


def test_blind_disagreement_counts_as_a_disagreement():
    """``blind`` decides whether a document is judged at all, so a fresh verdict
    that flips it moves the document in or out of the gate's denominator."""
    fresh = {"a": FunctionalVerdict(True, True, True, True, blind=True)}
    per_doc = {
        "a": {"functional_accept_ok": True, "functional_reject_ok": True, "functional_blind": False}
    }
    control = l1.compare_to_recorded(fresh, per_doc)
    assert control.n_agree == 0
    assert control.disagreements[0]["fresh"]["blind"] is True
