"""Scorer keys on the Word corpus stems.

A Word comparison is ``<idA>_<a>__vs__<idB>_<b>_redline_<idC>`` and a tool's candidate for it is
that stem plus ``_<tool>``; a Word render of a document is ``<idA>_<a>`` and a tool's render of
the same docx is ``<idA>_<a>_<tool>``. The key of a candidate is the Word stem itself. Legacy
``<base>_<next>_redline`` / ``<base>_<next>_<tool>_redline`` names keep keying to ``<base>_<next>``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from neurotic_docx_bench import pipeline

WORD = "0123456789_a__vs__abcdef0123_b_redline_fedcba9876"


def test_is_redline_and_redline_key_on_corpus_stems() -> None:
    assert pipeline.is_redline(WORD)
    assert pipeline.redline_key(WORD) == WORD
    assert pipeline.is_redline(f"{WORD}_jubarte", tool="jubarte")
    assert not pipeline.is_redline(f"{WORD}_jubarte")
    assert pipeline.redline_key(f"{WORD}_jubarte", tool="jubarte") == WORD
    assert pipeline.redline_key(f"{WORD.upper()}_JUBARTE", tool="jubarte") == WORD
    assert not pipeline.is_redline("0123456789_a")
    assert not pipeline.is_redline("0123456789_a_jubarte", tool="jubarte")
    assert pipeline.redline_key("0123456789_a_jubarte", tool="jubarte") == "0123456789_a_jubarte"
    # the id after _redline_ is ten hex digits; anything else is a legacy name
    assert pipeline.redline_key("x__vs__y_redline_zz", tool="jubarte") == "x__vs__y_redline_zz"
    assert pipeline.redline_key("a_b_jubarte_redline", tool="jubarte") == "a_b"
    assert pipeline.redline_key("a_b_redline") == "a_b"


def test_render_key_strips_the_tool_suffix() -> None:
    assert pipeline.render_key("0123456789_a_jubarte", "jubarte") == "0123456789_a"
    assert pipeline.render_key("0123456789_A_JUBARTE", "jubarte") == "0123456789_a"
    assert pipeline.render_key("0123456789_a", "jubarte") == "0123456789_a"
    assert pipeline.render_key("0123456789_a", None) == "0123456789_a"


def _pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.4\n")


def test_match_by_stem_pairs_corpus_candidates_with_word_comparisons(tmp_path: Path) -> None:
    oracle, cand = tmp_path / "o", tmp_path / "c"
    _pdf(oracle / f"{WORD}.pdf")
    _pdf(oracle / "0123456789_a.pdf")  # a document render is not a comparison
    _pdf(cand / f"{WORD}_jubarte.pdf")
    _pdf(cand / "0123456789_a_jubarte.pdf")
    _pdf(cand / "0123456789_a__vs__abcdef0123_b_redline_0000000000_jubarte.pdf")  # another comparison of the pair
    pairs = pipeline.match_by_stem(oracle, cand, candidate_tool="jubarte")
    assert [k for k, _, _ in pairs] == [WORD]
    o_only, c_only = pipeline.coverage(oracle, cand, candidate_tool="jubarte")
    assert o_only == set() and c_only == {"0123456789_a__vs__abcdef0123_b_redline_0000000000"}


def test_match_base_to_candidate_strips_the_tool(tmp_path: Path) -> None:
    oracle, cand = tmp_path / "o", tmp_path / "c"
    _pdf(oracle / "0123456789_a.pdf")
    _pdf(oracle / "abcdef0123_b.pdf")
    _pdf(cand / "0123456789_a_jubarte.pdf")
    _pdf(cand / "abcdef0123_b.pdf")  # a candidate without the suffix still keys by its stem
    pairs = pipeline.match_base_to_candidate(oracle, cand, candidate_tool="jubarte")
    assert [k for k, _, _ in pairs] == ["0123456789_a", "abcdef0123_b"]
    assert [k for k, _, _ in pipeline.match_base_to_candidate(oracle, cand)] == ["abcdef0123_b"]
    _pdf(cand / "0123456789_a.pdf")
    with pytest.raises(ValueError, match="collision"):
        pipeline.match_base_to_candidate(oracle, cand, candidate_tool="jubarte")
