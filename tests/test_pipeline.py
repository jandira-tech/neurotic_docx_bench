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
        # oracle_pair_key: a `_word_redline` fixture and its candidate must land
        # on the same normalized pair key.
        key = pipeline.oracle_pair_key(p.stem)
        shutil.copy(p, oracle / f"{key}_redline.pdf")
        shutil.copy(p, cand / f"{key}_jubarte_redline.pdf")

    scores = pipeline.score_folders(
        oracle, cand, tmp_path / "work", jobs=1, candidate_tool="jubarte",
    )
    assert len(scores) == len(sample_oracle_pdfs)
    for key, score in scores.items():
        assert score == pytest.approx(100.0, abs=1e-6), f"{key} -> {score}"


def test_oracle_word_variant_normalizes(tmp_path):
    # The Word-captured oracle names 68 files `<pair>_word_redline.pdf`; without
    # normalization those key to `<pair>_word` and never match any candidate
    # (43 pairs were silently unreachable).
    oracle = tmp_path / "o"
    cand = tmp_path / "c"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "a_b_word_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "a_b_t_redline.pdf").write_bytes(b"%PDF-1.4\n")
    pairs = pipeline.match_by_stem(oracle, cand, candidate_tool="t")
    assert [k for k, _, _ in pairs] == ["a_b"]


def test_oracle_dual_variant_prefers_word_capture(tmp_path):
    # 25 pairs carry BOTH variants; the `_word_redline` file is the
    # provenance-matching Word capture and wins deterministically (mirrors
    # _index_accepted's ranking) — never a collision error.
    oracle = tmp_path / "o"
    cand = tmp_path / "c"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "a_b_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (oracle / "a_b_word_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "a_b_t_redline.pdf").write_bytes(b"%PDF-1.4\n")
    pairs = pipeline.match_by_stem(oracle, cand, candidate_tool="t")
    assert len(pairs) == 1
    assert pairs[0][1].name == "a_b_word_redline.pdf"


def test_oracle_same_variant_collision_still_raises():
    # Same-variant collisions only arise from case-differing stems, which a
    # case-insensitive filesystem (macOS) collapses into one file — so drive
    # _index_redlines through a directory stub instead of the real FS.
    from pathlib import Path

    class _FakeDir:
        def __init__(self, paths):
            self._paths = paths

        def glob(self, pattern):
            return self._paths

    fake = _FakeDir([Path("/x/A_B_word_redline.pdf"), Path("/x/a_b_word_redline.pdf")])
    with pytest.raises(ValueError, match="collision"):
        pipeline._index_redlines(fake, None)


def test_candidate_side_not_normalized(tmp_path):
    # Only the ORACLE index interprets `_word` as a variant marker; a candidate
    # keyed `<pair>_<tool>_redline` never carries it and must stay verbatim.
    oracle = tmp_path / "o"
    cand = tmp_path / "c"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "x_y_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "x_y_word_t_redline.pdf").write_bytes(b"%PDF-1.4\n")  # pair "x_y_word"
    pairs = pipeline.match_by_stem(oracle, cand, candidate_tool="t")
    assert pairs == []


def test_multi_dir_oracle_union(tmp_path):
    d1 = tmp_path / "named"
    d2 = tmp_path / "randomized"
    cand = tmp_path / "c"
    for d in (d1, d2, cand):
        d.mkdir()
    (d1 / "a_b_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (d2 / "file_1_file_2_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "a_b_t_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (cand / "file_1_file_2_t_redline.pdf").write_bytes(b"%PDF-1.4\n")
    pairs = pipeline.match_by_stem([d1, d2], cand, candidate_tool="t")
    assert [k for k, _, _ in pairs] == ["a_b", "file_1_file_2"]


def test_multi_dir_cross_collision_raises(tmp_path):
    d1 = tmp_path / "named"
    d2 = tmp_path / "randomized"
    cand = tmp_path / "c"
    for d in (d1, d2, cand):
        d.mkdir()
    (d1 / "a_b_redline.pdf").write_bytes(b"%PDF-1.4\n")
    (d2 / "a_b_redline.pdf").write_bytes(b"%PDF-1.4\n")
    with pytest.raises(ValueError, match="collision"):
        pipeline.match_by_stem([d1, d2], cand, candidate_tool="t")
