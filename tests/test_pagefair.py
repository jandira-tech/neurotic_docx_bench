"""Page-count fairness (PR1): a tool that drops or adds pages must pay for it.

``score.score_document`` is parity-locked and scores only ``min(oracle, candidate)``
pages, so the penalty lives in the ``pipeline.score_pdf_pair`` wrapper: every unmatched
page (either side) enters the doc aggregate with score 0 and an ink-derived weight,
producing the ``*_pagefair`` fields. When page counts match, pagefair equals the
parity-locked values exactly.
"""

from __future__ import annotations

import math
from pathlib import Path

import pymupdf as fitz
import pytest

from neurotic_docx_bench import pipeline

PAGE_TEXT_A = "The quick brown fox jumps over the lazy dog. " * 12
PAGE_TEXT_B = "Pack my box with five dozen liquor jugs, promptly. " * 12


def _make_pdf(path: Path, page_texts: list[str]) -> Path:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        rect = fitz.Rect(72, 72, page.rect.width - 72, page.rect.height - 72)
        page.insert_textbox(rect, text, fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


@pytest.fixture
def pdfs(tmp_path: Path) -> dict[str, Path]:
    return {
        "two_page": _make_pdf(tmp_path / "two_page.pdf", [PAGE_TEXT_A, PAGE_TEXT_B]),
        "one_page": _make_pdf(tmp_path / "one_page.pdf", [PAGE_TEXT_A]),
    }


def test_pagefair_fields_present_and_identity_when_counts_match(pdfs, tmp_path):
    result = pipeline.score_pdf_pair(pdfs["one_page"], pdfs["one_page"], tmp_path / "w1")
    assert "overall_score_pagefair" in result
    assert "average_score_pagefair" in result
    assert "min_score_pagefair" in result
    assert result["page_count_mismatch"] is False
    assert math.isclose(result["overall_score_pagefair"], result["overall_score"], abs_tol=1e-9)
    assert math.isclose(result["average_score_pagefair"], result["average_score"], abs_tol=1e-9)
    assert math.isclose(result["min_score_pagefair"], result["min_score"], abs_tol=1e-9)


def test_pagefair_penalizes_candidate_missing_a_page(pdfs, tmp_path):
    """Oracle has 2 pages, candidate reproduces only page 1 → identical on the matched
    page (v1 sees 100) but pagefair must fall, with the min term scaled to the matched
    ink share (~half here)."""
    result = pipeline.score_pdf_pair(pdfs["two_page"], pdfs["one_page"], tmp_path / "w2")
    assert result["page_count_mismatch"] is True
    assert result["overall_score_pagefair"] < result["overall_score"]
    assert 30.0 < result["min_score_pagefair"] < 70.0
    assert result["average_score_pagefair"] < result["average_score"]
    # The matched page is pixel-identical, so v1 is perfect and pagefair must not be.
    assert result["overall_score"] == pytest.approx(100.0, abs=1e-6)
    assert result["overall_score_pagefair"] < 70.0


def test_pagefair_penalizes_candidate_with_extra_page(pdfs, tmp_path):
    """Candidate adds a page the oracle does not have → same penalty direction."""
    result = pipeline.score_pdf_pair(pdfs["one_page"], pdfs["two_page"], tmp_path / "w3")
    assert result["page_count_mismatch"] is True
    assert result["overall_score_pagefair"] < result["overall_score"]
    assert result["min_score_pagefair"] < result["min_score"]


def test_pagefair_weight_uses_unmatched_page_ink(pdfs, tmp_path):
    """The unmatched page's weight comes from its own ink, so dropping an ink-heavy page
    must cost more than the naive per-page average would suggest: with two roughly
    equal-ink pages, losing one should land the average near 50, not near 100."""
    result = pipeline.score_pdf_pair(pdfs["two_page"], pdfs["one_page"], tmp_path / "w4")
    assert 25.0 < result["average_score_pagefair"] < 75.0


def test_pagefair_is_ink_weighted_not_count_weighted(tmp_path):
    """The discriminating case: a naive per-page count weighting would score both of
    these ~50; ink weighting must separate them decisively."""
    dense = PAGE_TEXT_A + " " + PAGE_TEXT_B + " " + PAGE_TEXT_A
    sparse = "fin."
    oracle_ds = _make_pdf(tmp_path / "o_ds.pdf", [dense, sparse])
    oracle_sd = _make_pdf(tmp_path / "o_sd.pdf", [sparse, dense])
    cand_dense = _make_pdf(tmp_path / "c_d.pdf", [dense])
    cand_sparse = _make_pdf(tmp_path / "c_s.pdf", [sparse])

    # Missing the near-blank trailing page: cheap.
    kept_dense = pipeline.score_pdf_pair(oracle_ds, cand_dense, tmp_path / "wa")
    # Missing the dense page: catastrophic.
    kept_sparse = pipeline.score_pdf_pair(oracle_sd, cand_sparse, tmp_path / "wb")

    assert kept_dense["average_score_pagefair"] > 85.0
    assert kept_sparse["average_score_pagefair"] < 30.0
    # Min term is ink-proportional: near-blank loss keeps a high min, dense loss guts it.
    assert kept_dense["min_score_pagefair"] > 85.0
    assert kept_sparse["min_score_pagefair"] < 30.0
    assert kept_dense["overall_score_pagefair"] > 80.0
    assert kept_sparse["overall_score_pagefair"] < 30.0


def test_scorer_selection_is_benchmark_aware():
    assert pipeline.scorer_for_benchmark("script_redlines") == pipeline.SCORER_PAGEFAIR
    assert pipeline.scorer_for_benchmark("accepted_changes") == pipeline.SCORER_PAGEFAIR
    assert pipeline.scorer_for_benchmark("roundtrip") == pipeline.SCORER_PAGEFAIR
    assert pipeline.scorer_for_benchmark("visual_rendering") == pipeline.SCORER_RAW
    assert pipeline.scorer_for_benchmark("visual_redlines") == pipeline.SCORER_RAW
    assert pipeline.raw_overall_from_result(
        {"overall_score": 90.0, "overall_score_pagefair": 40.0}
    ) == 90.0


def test_overall_from_result_prefers_pagefair():
    assert pipeline.overall_from_result(
        {"overall_score": 90.0, "overall_score_pagefair": 40.0}
    ) == 40.0
    assert pipeline.overall_from_result({"overall_score": 90.0}) == 90.0


def test_score_folders_reports_pagefair(pdfs, tmp_path):
    oracle_dir = tmp_path / "oracle"
    cand_dir = tmp_path / "cand"
    oracle_dir.mkdir()
    cand_dir.mkdir()
    _make_pdf(oracle_dir / "a_b_redline.pdf", [PAGE_TEXT_A, PAGE_TEXT_B])
    _make_pdf(cand_dir / "a_b_tool_redline.pdf", [PAGE_TEXT_A])
    scores = pipeline.score_folders(
        oracle_dir, cand_dir, tmp_path / "w5", jobs=1, candidate_tool="tool"
    )
    full = pipeline.score_folders_full(
        oracle_dir, cand_dir, tmp_path / "w6", jobs=1, candidate_tool="tool"
    )
    assert scores["a_b"] == full["a_b"]["overall_score_pagefair"]
    assert scores["a_b"] < 100.0
