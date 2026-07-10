"""Scoring pipeline — redline-key matching (collision-safe, base-excluding) + scoring."""

from __future__ import annotations

import shutil

import pytest

from neurotic_docx_bench import pipeline


def test_redline_key_and_is_redline():
    assert pipeline.is_redline("a_b_redline")
    assert not pipeline.is_redline("a_b")  # base pdf is not a redline
    assert pipeline.redline_key("a_b_redline") == "a_b"
    assert pipeline.redline_key("a_b_jubarte_redline", tool="jubarte") == "a_b"
    # oracle and a tool candidate for the same pair collapse to the same key
    assert pipeline.redline_key("a_b_redline") == pipeline.redline_key(
        "a_b_jubarte_redline", tool="jubarte",
    )


def test_match_excludes_base_and_pairs_by_tool(tmp_path):
    oracle = tmp_path / "o"
    cand = tmp_path / "c"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "doc1_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (oracle / "doc1.pdf").write_bytes(b"%PDF-1.4\n")  # base — must be excluded
    (oracle / "doc2_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "doc1_jubarte_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "orphan_jubarte_redline.pdf").write_bytes(b"%PDF-1.4\n")

    pairs = pipeline.match_by_stem(oracle, cand, candidate_tool="jubarte")
    assert [k for k, _, _ in pairs] == ["doc1"]


def test_match_raises_on_collision(tmp_path):
    cand = tmp_path / "c"
    oracle = tmp_path / "o"
    cand.mkdir()
    oracle.mkdir()
    (oracle / "a_b_redline.pdf").write_bytes(b"%PDF-1.4\n")
    # with tool="x": both 'a_b_x_redline' and 'a_b_redline' collapse to key 'a_b'
    (cand / "a_b_x_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "a_b_redline.pdf").write_bytes(b"%PDF-1.4\n")
    with pytest.raises(ValueError, match="collision"):
        pipeline.match_by_stem(oracle, cand, candidate_tool="x")


def test_coverage_reports_gaps(tmp_path):
    oracle = tmp_path / "o"
    cand = tmp_path / "c"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "only_oracle_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (oracle / "both_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "both_t_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "only_cand_t_redline.pdf").write_bytes(b"%PDF-1.4\n")
    o_only, c_only = pipeline.coverage(oracle, cand, candidate_tool="t")
    assert o_only == {"only_oracle"}
    assert c_only == {"only_cand"}


def test_score_pdf_pair_identical_is_100_with_page_meta(tmp_path, sample_oracle_pdfs):
    result = pipeline.score_pdf_pair(
        sample_oracle_pdfs[0], sample_oracle_pdfs[0], tmp_path / "w", dpi=144, key="k",
    )
    assert result["overall_score"] == pytest.approx(100.0, abs=1e-6)
    assert result["page_count_oracle"] == result["page_count_candidate"]
    assert result["page_count_mismatch"] is False


def test_score_folders_passthrough_oracle_vs_self(tmp_path, sample_oracle_pdfs):
    # candidate == oracle content, renamed with a tool suffix → every doc scores ~100
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    for p in sample_oracle_pdfs:
        key = pipeline.redline_key(p.stem)
        shutil.copy(p, oracle / f"{key}_redline.pdf")
        shutil.copy(p, cand / f"{key}_jubarte_redline.pdf")

    scores = pipeline.score_folders(
        oracle, cand, tmp_path / "work", jobs=1, candidate_tool="jubarte",
    )
    assert len(scores) == len(sample_oracle_pdfs)
    for key, score in scores.items():
        assert score == pytest.approx(100.0, abs=1e-6), f"{key} -> {score}"
