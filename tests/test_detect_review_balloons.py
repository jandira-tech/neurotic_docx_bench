"""The balloon detector flags a narrowed page with revision boxes on the right.

Thresholds were measured on the pair in
``grok_run/compared_a_100_vs_b_10_pdf/{with,without}_balloons_do_not_use.pdf``.
Those files are not in git. The synthetic pages below freeze the same geometry,
and the real pair is checked when it is on disk.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import fitz
import numpy as np
import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "detect_review_balloons.py"
_ROOT = Path(__file__).resolve().parents[1]
_WITH = _ROOT / "grok_run/compared_a_100_vs_b_10_pdf/with_balloons_do_not_use.pdf"
_WITHOUT = _ROOT / "grok_run/compared_a_100_vs_b_10_pdf/without_balloons_do_not_use.pdf"


def _load():
    spec = importlib.util.spec_from_file_location("detect_review_balloons", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["detect_review_balloons"] = mod
    spec.loader.exec_module(mod)
    return mod


det = _load()


def _page(width: int = 596, height: int = 842) -> np.ndarray:
    return np.full((height, width, 3), 255, dtype=np.uint8)


def _strokes(img: np.ndarray, x0: int, x1: int, y0: int, y1: int) -> None:
    """Text-like horizontal strokes, so a column has ink but is not a solid bar."""
    img[y0:y1:8, x0:x1] = (30, 30, 30)


def _box(img: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> None:
    img[y0 : y0 + 2, x0:x1] = (20, 20, 20)
    img[y1 - 2 : y1, x0:x1] = (20, 20, 20)
    img[y0:y1, x0 : x0 + 2] = (20, 20, 20)
    img[y0:y1, x1 - 2 : x1] = (20, 20, 20)
    _strokes(img, x0 + 8, x1 - 8, y0 + 6, y1 - 6)


def _balloon_page() -> np.ndarray:
    img = _page()
    # Body ends near 62% of the width. The rail of boxes reaches the outer margin.
    _strokes(img, 50, 370, 80, 760)
    img[80:760, 368:370] = (20, 20, 20)
    _box(img, 410, 120, 575, 280)
    _box(img, 410, 340, 575, 520)
    return img


def test_narrowed_page_with_right_hand_boxes_is_balloons() -> None:
    hit = det.page_balloon_layout(_balloon_page())
    assert hit is not None
    assert hit.boxes >= 2
    assert 0.55 <= hit.gutter_fraction <= 0.78


def test_full_width_page_is_not_balloons() -> None:
    img = _page()
    _strokes(img, 40, 540, 80, 760)
    assert det.page_balloon_layout(img) is None


def test_narrow_page_with_an_empty_right_margin_is_not_balloons() -> None:
    img = _page()
    _strokes(img, 50, 340, 80, 760)
    assert det.page_balloon_layout(img) is None


def test_table_whose_rules_cross_the_gutter_is_not_balloons() -> None:
    """A right-hand column of a form is not a review rail.

    The cells are boxes and a column gap can sit where a balloon gutter
    would, but each cell's horizontal rules run back through the body.
    """
    img = _page(width=842, height=596)
    _strokes(img, 40, 500, 80, 520)
    for y in (80, 160, 240, 320, 400, 520):
        img[y : y + 2, 40:800] = (20, 20, 20)
    for x in (40, 300, 520, 800):
        img[80:522, x : x + 2] = (20, 20, 20)
    assert det.page_balloon_layout(img) is None


def test_two_columns_split_at_the_middle_are_not_balloons() -> None:
    img = _page()
    _strokes(img, 40, 270, 80, 760)
    _strokes(img, 330, 560, 80, 760)
    assert det.page_balloon_layout(img) is None


def test_scanner_reads_balloon_pages_from_a_pdf(tmp_path: Path) -> None:
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page(width=596, height=842)
        page.draw_rect(fitz.Rect(40, 80, 560, 760), color=(0, 0, 0), width=0.4)
        # Full-width rules: this page is inline, not a balloon rail.
        for y in range(100, 740, 18):
            page.draw_line(fitz.Point(50, y), fitz.Point(540, y), width=0.6)
    page = doc.new_page(width=596, height=842)
    page.draw_line(fitz.Point(368, 70), fitz.Point(368, 780), width=0.8)
    for y in range(90, 740, 16):
        page.draw_line(fitz.Point(50, y), fitz.Point(360, y), width=0.6)
    page.draw_rect(fitz.Rect(410, 120, 575, 280), color=(0, 0, 0), width=1.2)
    page.draw_rect(fitz.Rect(410, 340, 575, 520), color=(0, 0, 0), width=1.2)
    for y in (150, 180, 210, 370, 400, 430):
        page.draw_line(fitz.Point(424, y), fitz.Point(560, y), width=0.5)
    pdf = tmp_path / "sample.pdf"
    doc.save(pdf)
    doc.close()
    assert det.pdf_balloon_pages(pdf) == [3]


def test_fuzzy_recall_finds_a_word_glued_to_its_neighbor() -> None:
    found = det.fuzzy_recall("february presidents", "the névfebruary presidents day")
    assert found == 1.0


def test_fuzzy_recall_rejects_unrelated_text() -> None:
    source = "luunja vald haldusreformi seadusega elanikku statistikaameti"
    other = "ankara üniversitesi kütüphane dokümantasyon ders izlence formu"
    assert det.fuzzy_recall(source, other) < 0.6


def test_name_match_is_not_an_average_of_the_two_files() -> None:
    base = "alpha bravo charlie delta echo foxtrot"
    revision = "hotel india juliet kilo lima mike november"
    verdict = det.names_match_text(base, base, revision)
    assert verdict.ok is False
    assert verdict.score_base >= 0.6
    assert verdict.score_revision < 0.6


def test_stem_pair_strips_a_stage_prefix() -> None:
    path = Path("00012__aaaaaaaa__vs__bbbbbbbb.pdf")
    assert det.stem_pair(path) == ("aaaaaaaa", "bbbbbbbb")
    assert det.stem_pair(Path("with_balloons_do_not_use.pdf")) is None


@pytest.mark.skipif(not (_WITH.is_file() and _WITHOUT.is_file()), reason="example PDFs are local")
def test_real_example_pair() -> None:
    assert det.pdf_balloon_pages(_WITH) == [1, 2]
    assert det.pdf_balloon_pages(_WITHOUT) == []


# Two versions of one form: the same words, different figures. The redline PDF
# shows both sets of figures (the deletions stay visible); a PDF of the revision
# alone shows only its own. Common words alone give the lone PDF a high recall.
_FORM_BASE = "quarterly return form applicant signature total amount 1250 2310 4471 6032 date 2019"
_FORM_REVISION = "quarterly return form applicant signature total amount 1875 2940 5520 7118 date 2021"


def test_a_lone_pdf_of_the_revision_does_not_match_the_pair() -> None:
    verdict = det.names_match_text(_FORM_REVISION, _FORM_BASE, _FORM_REVISION)
    assert verdict.ok is False
    assert "base" in verdict.reason


def test_a_redline_pdf_of_near_identical_files_matches_the_pair() -> None:
    redline = (
        "quarterly return form applicant signature total amount 12501875 23102940 "
        "44715520 60327118 date 20192021"
    )
    assert det.names_match_text(redline, _FORM_BASE, _FORM_REVISION).ok is True


def test_distinct_recall_ignores_a_word_glued_to_a_figure() -> None:
    # docx text runs a word into the next cell's figure; the PDF keeps a space.
    source = "catchment0 area241 admits1 district7 clinic22"
    found = "catchment 0 area 241 admits 1 district 7 clinic 22"
    assert det.distinct_recall(source, "total", found) == 1.0


_MESSED = Path(__file__).resolve().parents[1] / "scripts" / "messed_fixtures"


@pytest.mark.skipif(not (_MESSED / "pdfs").is_dir(), reason="messed fixtures are local")
def test_command_fails_when_a_pdf_is_not_its_named_pair() -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(
        det.app,
        ["--src", str(_MESSED / "pdfs"), "--a", str(_MESSED / "a"), "--b", str(_MESSED / "b")],
    )
    assert result.exit_code == 1
    assert "yes 0" in result.output
