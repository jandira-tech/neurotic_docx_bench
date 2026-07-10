"""Tests for the accepted-changes matcher (visual_accepted_changes).

The pairing rule: candidate PDFs come from rendering docx_accepted_word DOCX
(named ``<base>_<next>_redline.docx``), so their stem is ``<base>_<next>_redline``.
Oracle PDFs in pdf_accepted_word are named ``<base>_<next>[_word]_redline_accepted.pdf``.
The matcher strips ``_accepted`` (and a trailing ``_word`` infix on the oracle
side) to land on the shared ``<base>_<next>`` key.
"""

from pathlib import Path

import pytest

from neurotic_docx_bench.pipeline import (
    accepted_key,
    match_accepted_to_candidate,
)


def test_accepted_key_strips_accepted_suffix() -> None:
    assert accepted_key("alpha_beta_word_redline_accepted") == "alpha_beta"
    assert accepted_key("alpha_beta_redline_accepted") == "alpha_beta"


def test_accepted_key_passes_through_plain_redline() -> None:
    # A candidate stem (from docx_accepted_word DOCX) is <base>_<next>_redline.
    assert accepted_key("alpha_beta_redline") == "alpha_beta"


def test_match_accepted_to_candidate_pairs_redline_to_accepted(tmp_path: Path) -> None:
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    # Oracle PDF carries _word_redline_accepted; candidate (rendered accepted
    # DOCX) carries _redline. Both must normalize to alpha_beta.
    (oracle / "alpha_beta_word_redline_accepted.pdf").write_bytes(b"%PDF-1.4")
    (cand / "alpha_beta_redline.pdf").write_bytes(b"%PDF-1.4")
    pairs = match_accepted_to_candidate(oracle, cand)
    keys = [k for k, _, _ in pairs]
    assert keys == ["alpha_beta"]


def test_match_accepted_to_candidate_drops_unpaired(tmp_path: Path) -> None:
    oracle = tmp_path / "oracle"
    cand = tmp_path / "cand"
    oracle.mkdir()
    cand.mkdir()
    (oracle / "alpha_beta_word_redline_accepted.pdf").write_bytes(b"%PDF-1.4")
    (oracle / "gamma_delta_redline_accepted.pdf").write_bytes(b"%PDF-1.4")
    (cand / "alpha_beta_redline.pdf").write_bytes(b"%PDF-1.4")
    (cand / "epsilon_zeta_redline.pdf").write_bytes(b"%PDF-1.4")  # no oracle
    pairs = match_accepted_to_candidate(oracle, cand)
    keys = [k for k, _, _ in pairs]
    assert keys == ["alpha_beta"]  # gamma_delta has no candidate, epsilon_zeta no oracle


def test_match_accepted_raises_on_collision(tmp_path: Path) -> None:
    oracle = tmp_path / "oracle"
    oracle.mkdir()
    # Two oracle PDFs that normalize to the same key — should be a hard error.
    (oracle / "alpha_beta_word_redline_accepted.pdf").write_bytes(b"%PDF-1.4")
    (oracle / "alpha_beta_redline_accepted.pdf").write_bytes(b"%PDF-1.4")
    cand = tmp_path / "cand"
    cand.mkdir()
    (cand / "alpha_beta_redline.pdf").write_bytes(b"%PDF-1.4")
    with pytest.raises(ValueError, match="accepted key collision"):
        match_accepted_to_candidate(oracle, cand)
