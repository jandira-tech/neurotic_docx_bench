"""The ``docxide_metrics`` track after the Rust scorer's retirement (0.7.0).

Metric parity against docxide-pdf's frozen numbers lives in ``tests/test_page_metrics.py``.
This file covers the track around it: it must score with ``page_metrics`` in-process
(no cargo, no binary, no mutool), carry exactly the two ported metrics, and keep the
intent-to-treat rule (a failed convert scores 0, never NaN or missing).
"""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz

from neurotic_docx_bench import docxide_metrics as dm
from neurotic_docx_bench import page_metrics as pm


def _make_pdf(path: Path, page_texts: list[str]) -> Path:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(72, 72, 540, 720), text, fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


def test_track_carries_only_the_ported_metrics() -> None:
    assert dm.METRICS == ("jaccard", "text_boundary")
    assert dm.DPI == pm.UPSTREAM_DPI == 150
    assert not hasattr(dm, "ensure_scorer")
    assert not hasattr(dm, "SCORER_BIN")
    assert "ssim" not in dm.METRIC_LABELS


def test_score_candidates_runs_in_process(tmp_path: Path) -> None:
    class Fixture:
        def __init__(self, stem: str, oracle: Path) -> None:
            self.stem, self.oracle = stem, oracle

    text = "Video provides a powerful way to help you prove your point. " * 10
    oracle = _make_pdf(tmp_path / "oracle" / "doc.pdf", [text])
    cand_dir = tmp_path / "cand"
    _make_pdf(cand_dir / "doc.pdf", [text])
    fixtures = [Fixture("doc", oracle), Fixture("missing", oracle)]
    out = tmp_path / "scores.json"
    rows = dm.score_candidates(fixtures, cand_dir, out, workers=2)
    assert out.is_file()
    assert rows["doc"]["converted"] is True
    assert rows["doc"]["jaccard"] == 1.0 and rows["doc"]["text_boundary"] == 1.0
    assert rows["missing"]["converted"] is False
    assert rows["missing"]["error"] == pm.ERROR_CANDIDATE_MISSING
    assert set(rows["doc"]) == {"stem", *pm.PairMetrics(converted=True).as_row()}


def test_itt_zeroes_a_failed_convert() -> None:
    """A document with no candidate PDF scores 0 on both metrics, not NaN or missing."""
    report = dm._tool_report(
        "toy",
        None,
        ["a", "b"],
        {"a": {"stem": "a", "converted": True, "jaccard": 0.5,
               "text_boundary": 0.5, "ref_pages": 1, "pages": 1, "scored_pages": 1,
               "max_break_drift": 0}},
        [{"doc": "b", "stage": "generate", "error": "boom", "cmd": ["toy"]}],
    )
    assert report["per_doc"]["b"] == {"jaccard": 0.0, "text_boundary": 0.0}
    assert report["n_scored"] == 1
    assert report["itt_n"] == 2
    assert report["failures"] == 1
    assert report["metrics"]["jaccard"]["mean"] == 25.0
    assert report["pass_jaccard_20"] == 1
    assert "pass_ssim_75" not in report
    assert report["unscored_docs"] == []


def test_a_converted_document_with_no_scorable_page_is_named_unscored() -> None:
    ok = {"converted": True, "jaccard": 0.5, "text_boundary": 0.5, "ref_pages": 1, "pages": 1}
    landscape = {"converted": True, "jaccard": None, "text_boundary": None, "ref_pages": 1, "pages": 1}
    report = dm._tool_report(
        "toy",
        None,
        ["a", "b", "c"],
        {"a": ok, "b": landscape},
        [{"doc": "c", "stage": "generate", "error": "boom", "cmd": ["toy"]}],
    )
    assert report["unscored_docs"] == ["b"]
    assert report["per_doc"]["b"] == {"jaccard": 0.0, "text_boundary": 0.0}
    assert report["n_scored"] + report["failures"] + len(report["unscored_docs"]) == report["itt_n"]


def test_render_table_has_no_ssim_columns() -> None:
    report = {
        "n": 2,
        "dpi": 150,
        "tools": {
            "toy": {
                "version": "1.0",
                "n_scored": 2,
                "itt_n": 2,
                "failures": 0,
                "metrics": {
                    "jaccard": {"mean": 40.0, "median": 41.0},
                    "text_boundary": {"mean": 90.0, "median": 95.0},
                },
                "pass_jaccard_20": 2,
            },
        },
    }
    md = dm.render_table(report)
    header = next(line for line in md.splitlines() if line.startswith("| Rank |"))
    assert "SSIM" not in header
    assert header.count("|") == 12  # 11 columns
    assert "| 1 | toy | 1.0 | 2 | 2 | 40.00 | 41.00 | 90.00 | 95.00 | 2 | 0 |" in md
    assert "—" not in md
