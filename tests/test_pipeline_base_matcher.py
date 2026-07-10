"""Tests for the base-PDF matcher (visual_rendering) and visual dispatch helper."""

from types import SimpleNamespace

from neurotic_docx_bench.pipeline import match_base_to_candidate
from neurotic_docx_bench.visual_oracles import visual_benchmarks_for_run


def test_match_base_to_candidate_pairs_plain_stems(tmp_path):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "alpha.pdf").write_bytes(b"%PDF-1.4")
    (oracle / "beta.pdf").write_bytes(b"%PDF-1.4")
    (cand / "alpha.pdf").write_bytes(b"%PDF-1.4")
    (cand / "gamma.pdf").write_bytes(b"%PDF-1.4")  # no oracle → dropped
    pairs = match_base_to_candidate(oracle, cand)
    keys = [k for k, _, _ in pairs]
    assert keys == ["alpha"]  # beta has no candidate, gamma has no oracle


def test_match_base_to_candidate_is_case_insensitive(tmp_path):
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "MixedCase.pdf").write_bytes(b"%PDF-1.4")
    (cand / "mixedcase.pdf").write_bytes(b"%PDF-1.4")
    pairs = match_base_to_candidate(oracle, cand)
    assert len(pairs) == 1
    assert pairs[0][0] == "mixedcase"


def test_visual_benchmarks_for_run_returns_declared_in_canonical_order(tmp_path):
    rc = SimpleNamespace(
        benchmarks=["visual_redlines", "visual_rendering", "visual_accepted_changes"],
    )
    oracles = {
        "visual_rendering": tmp_path,
        "visual_redlines": tmp_path,
        "visual_accepted_changes": tmp_path,
    }
    pairs = visual_benchmarks_for_run(rc, oracles)
    names = [name for name, _ in pairs]
    # Canonical order is rendering → redlines → accepted, regardless of declaration order.
    assert names == ["visual_rendering", "visual_redlines", "visual_accepted_changes"]


def test_visual_benchmarks_for_run_skips_undeclared_and_missing_oracles(tmp_path):
    rc = SimpleNamespace(benchmarks=["visual_redlines"])  # only redlines declared
    oracles = {
        "visual_rendering": tmp_path,  # oracle present but not declared → skipped
        "visual_redlines": tmp_path,
        # visual_accepted_changes oracle absent → would be skipped even if declared
    }
    pairs = visual_benchmarks_for_run(rc, oracles)
    names = [name for name, _ in pairs]
    assert names == ["visual_redlines"]


def test_visual_benchmarks_for_run_empty_when_no_visual_declared(tmp_path):
    rc = SimpleNamespace(benchmarks=["script_redlines", "roundtrip"])
    oracles = {"visual_rendering": tmp_path, "visual_redlines": tmp_path}
    pairs = visual_benchmarks_for_run(rc, oracles)
    assert pairs == []
