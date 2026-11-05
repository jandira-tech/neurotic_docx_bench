"""One scoring pass per candidate: ``pipeline.score_pdf_pair`` carries docxide's page
metrics (ink Jaccard, text boundary, break drift) as columns on the same row as
pagefair-v2 and the page counts, computed from the rasters that pass already made."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from neurotic_docx_bench import pipeline

PAGE_A = "Video provides a powerful way to help you prove your point. " * 12
PAGE_B = "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. " * 12


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


def test_identity_pair_carries_page_metric_columns(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", [PAGE_A, PAGE_B])
    row = pipeline.score_pdf_pair(pdf, pdf, tmp_path / "w")
    assert row["ink_jaccard"] == 1.0
    assert row["text_boundary"] == 1.0
    assert row["max_break_drift"] == 0
    # Same row as the headline and the counts: no second pass, no second dict.
    assert row["page_count_oracle"] == 2 and "overall_score_pagefair" in row


def test_page_metrics_come_from_the_pass_rasters_not_a_second_render(tmp_path: Path, monkeypatch) -> None:
    from neurotic_docx_bench import page_metrics as pm

    pdf = _make_pdf(tmp_path / "a.pdf", [PAGE_A])
    calls: list[int] = []
    real = pm.jaccard_from_rasters

    def spy(oracle_pages, cand_pages):
        calls.append(len(oracle_pages))
        return real(oracle_pages, cand_pages)

    monkeypatch.setattr(pm, "jaccard_from_rasters", spy)
    monkeypatch.setattr(pm, "_rasterize", lambda *a, **k: (_ for _ in ()).throw(AssertionError("second render")))
    row = pipeline.score_pdf_pair(pdf, pdf, tmp_path / "w")
    assert calls == [1]
    assert row["ink_jaccard"] == 1.0


def test_disjoint_pair_scores_low_on_both_metrics(tmp_path: Path) -> None:
    a = _make_pdf(tmp_path / "a.pdf", [PAGE_A, PAGE_A])
    b = _make_pdf(tmp_path / "b.pdf", [PAGE_B, PAGE_B, PAGE_B])
    row = pipeline.score_pdf_pair(a, b, tmp_path / "w")
    assert 0.0 <= row["ink_jaccard"] < 1.0
    assert row["text_boundary"] is not None and row["text_boundary"] < 1.0
    # Break drift is signed (candidate minus oracle) over the breaks both sides have:
    # PAGE_A is 132 words a page, PAGE_B 96, so the first break lands 36 words early.
    assert row["max_break_drift"] == -36
    assert row["page_count_mismatch"] is True


def test_build_results_aggregates_page_metrics() -> None:
    import uuid
    from datetime import UTC, datetime

    import pytest

    from neurotic_docx_bench.config import BenchConfig
    from neurotic_docx_bench.results_schema import build_results

    per_doc = {
        "a": {"ink_jaccard": 0.4, "text_boundary": 1.0, "max_break_drift": 3},
        "b": {"ink_jaccard": 0.2, "text_boundary": None, "max_break_drift": -9},
        "c": {"ink_jaccard": None, "text_boundary": 0.5, "max_break_drift": 0},
    }
    result = build_results(
        id_run=uuid.uuid7(),
        vendor="acme",
        benchmark="script_redlines",
        scores={"a": 90.0, "b": 70.0, "c": 60.0},
        per_doc=per_doc,
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("corpus/oracle")),
        timestamp=datetime(2026, 8, 2, tzinfo=UTC),
    )
    assert result.ink_jaccard_mean == pytest.approx(0.3)
    assert result.ink_jaccard_median == pytest.approx(0.3)
    assert result.text_boundary_mean == pytest.approx(0.75)
    assert result.text_boundary_median == pytest.approx(0.75)
    assert result.to_json_dict()["ink_jaccard_mean"] == pytest.approx(0.3)

    empty = build_results(
        id_run=uuid.uuid7(),
        vendor="acme",
        benchmark="script_redlines",
        scores={"a": 90.0},
        per_doc={"a": {}},
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("corpus/oracle")),
        timestamp=datetime(2026, 8, 2, tzinfo=UTC),
    )
    assert empty.ink_jaccard_mean is None and empty.text_boundary_median is None
