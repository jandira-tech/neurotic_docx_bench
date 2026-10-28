"""docxide-pdf's page metrics, ported to Python (``page_metrics``).

Two layers, as the retired Rust parity test had:

1. **Parity** - score five committed corpus PDF pairs (Word's redline render vs the
   LibreOffice render of the same document) and require the numbers frozen in
   ``tests/reference/docxide_page_metrics.json``. Upstream's own ``page-metrics``
   binary recorded them over mutool 1.28.4; the file's ``_engine`` block names the
   MuPDF build they were re-frozen on, and the parity test refuses to run on any
   other build (MuPDF's line segmentation moves between releases, and a silent
   drift is exactly what a frozen reference exists to catch). To re-freeze after a
   deliberate PyMuPDF upgrade: render the five pairs with ``pm._rasterize`` at
   ``UPSTREAM_DPI`` into temporary RGB ``page_001.png`` etc. directories; run the
   pinned upstream ``page-metrics <ref.pdf> <other.pdf> <ref_dir> <other_dir>`` on
   each pair, diff moved values, then update the numbers and ``_engine`` together.
   Never freeze from the Python port; delete temporary PNGs after each pair.
2. **Units** - the pure pieces (leader normalisation, break positions, the ink rule,
   page Jaccard, the line-count skip rule) on hand-built inputs, no PDF needed.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pymupdf as fitz
import pytest

from neurotic_docx_bench import page_metrics as pm

REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE = REPO_ROOT / "tests" / "reference" / "docxide_page_metrics.json"
# Word's PDF of each frozen pair, now under its corpus name (corpus/word/notices/RENAMED.csv).
WORD_PDFS = {
    "file_100_file_101_redline": "8b45820aa8_file_100__vs__0d6cc8a99c_file_101_redline_f953aac51a",
    "file_101_file_102_redline": "0d6cc8a99c_file_101__vs__c39d1916e3_file_102_redline_77269bd39c",
    "file_102_file_103_redline": "c39d1916e3_file_102__vs__f05b2b13ee_file_103_redline_9760c7c6b0",
    "file_103_file_104_redline": "f05b2b13ee_file_103__vs__d435c8d66c_file_104_redline_ed3701fb29",
    "file_104_file_105_redline": "d435c8d66c_file_104__vs__0f0620ff98_file_105_redline_0c90ac520a",
}
WORD_PDF_DIR = REPO_ROOT / "corpus" / "word" / "tracking_without_comments" / "pdf"
# The LibreOffice 26.2.4.2 renders the numbers were frozen on (not Word files, so not in corpus/).
SOFFICE_PDFS = REPO_ROOT / "tests" / "reference" / "docxide_page_metrics_soffice"

METRIC_KEYS = ("jaccard", "ssim", "text_boundary", "ref_pages", "pages", "scored_pages", "max_break_drift")


def _reference() -> dict:
    return json.loads(REFERENCE.read_text(encoding="utf-8"))


def _expected() -> dict[str, dict]:
    return {k: v for k, v in _reference().items() if not k.startswith("_")}


def _pairs() -> list[tuple[str, Path, Path]]:
    return [(stem, WORD_PDF_DIR / f"{WORD_PDFS[stem]}.pdf", SOFFICE_PDFS / f"{stem}.pdf") for stem in sorted(_expected())]


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


# ---------------------------------------------------------------- parity ----


def test_reference_names_the_engine_it_was_frozen_on() -> None:
    engine = _reference()["_engine"]
    assert engine["mupdf"] == fitz.version[1], (
        f"reference frozen on MuPDF {engine['mupdf']}, this PyMuPDF bundles {fitz.version[1]}: "
        "re-freeze deliberately (see module docstring), do not loosen the tolerance"
    )
    assert engine["upstream_commit"] == "a72d91bca065be5c96b659e5daadc3cf3ffc9fb2"
    assert all(isinstance(row["ssim"], float) for row in _expected().values())


@pytest.mark.skipif(
    not all((WORD_PDF_DIR / f"{n}.pdf").is_file() for n in WORD_PDFS.values()),
    reason="needs corpus/word's PDFs: uv run bench fixtures download",
)
def test_port_matches_frozen_upstream_numbers() -> None:
    assert _reference()["_engine"]["mupdf"] == fitz.version[1], "engine mismatch, see the engine test"
    expected = _expected()
    for stem, oracle, candidate in _pairs():
        assert oracle.is_file() and candidate.is_file(), f"corpus PDF missing: {oracle} / {candidate}"
        got = pm.score_pair(oracle, candidate, dpi=pm.UPSTREAM_DPI).as_row()
        assert got["converted"] is True, stem
        assert got.get("error") is None, f"{stem}: {got.get('error')}"
        want = expected[stem]
        for key in METRIC_KEYS:
            if isinstance(want.get(key), float):
                assert got.get(key) == pytest.approx(want[key], abs=1e-6 if key == "ssim" else 1e-12, rel=0), f"{stem}.{key}"
            else:
                assert got.get(key) == want.get(key), f"{stem}.{key}: {got.get(key)} != {want.get(key)}"


def test_upstream_dpi_is_150() -> None:
    assert pm.UPSTREAM_DPI == 150


# ----------------------------------------------------------------- units ----


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("Title.......3", "Title 3"),
        ("a..b", "a..b"),
        ("a...b", "a b"),
        ("ab..", "ab.."),
        ("ab...", "ab"),
        ("...x", " x"),
        ("", ""),
    ],
)
def test_normalize_leaders(raw: str, want: str) -> None:
    assert pm.normalize_leaders(raw) == want


def test_first_and_last_word_ignore_leaders() -> None:
    assert pm.first_word("  Chapter one.......12 ") == "Chapter"
    assert pm.last_word("Chapter one.......12") == "12"
    assert pm.first_word("") == ""
    assert pm.last_word("   ") == ""


def test_break_positions_are_cumulative_word_counts() -> None:
    assert pm.break_positions([["a", "b"], ["c"], []]) == [2, 3, 3]
    assert pm.break_positions([]) == []


def test_ink_rule_is_luma_under_200() -> None:
    px = np.array([[[0, 0, 0], [255, 255, 255], [200, 200, 200], [199, 199, 199]]], dtype=np.uint8)
    assert pm.ink_mask(px).tolist() == [[True, False, False, True]]


def test_page_jaccard_identity_blank_and_disjoint() -> None:
    a = np.full((4, 4, 3), 255, dtype=np.uint8)
    b = a.copy()
    a[0, 0] = 0
    b[0, 0] = 0
    assert pm.page_jaccard(a, b) == 1.0
    blank = np.full((4, 4, 3), 255, dtype=np.uint8)
    assert pm.page_jaccard(blank, blank.copy()) == 1.0
    c = np.full((4, 4, 3), 255, dtype=np.uint8)
    c[3, 3] = 0
    assert pm.page_jaccard(a, c) == 0.0
    d = a.copy()
    d[0, 1] = 0
    assert pm.page_jaccard(a, d) == 0.5


def test_page_jaccard_tolerates_two_pixels_and_refuses_three() -> None:
    a = np.full((10, 10, 3), 255, dtype=np.uint8)
    a[0, 0] = 0
    b = np.full((12, 10, 3), 255, dtype=np.uint8)
    b[0, 0] = 0
    assert pm.page_jaccard(a, b) == 1.0
    c = np.full((13, 10, 3), 255, dtype=np.uint8)
    with pytest.raises(pm.PageSizeMismatch):
        pm.page_jaccard(a, c)


def test_boundary_skips_pages_whose_line_counts_differ_by_more_than_15_percent() -> None:
    ref_words = [["w"] * 10, ["w"] * 5]
    gen_words = [["w"] * 12, ["w"] * 3]
    ref_lines = [["alpha beta", "gamma delta", "eps zeta"], ["one two"] * 10]
    gen_lines = [["alpha x beta", "gamma delta", "eps y"], ["one two"] * 8]
    tb = pm.boundary_from_extracts(ref_words, gen_words, ref_lines, gen_lines)
    # page 1: 3 vs 3 lines -> scored; lines 1 and 2 match on first+last word, line 3 does not
    # page 2: 10 vs 8 lines -> 20 % apart -> skipped
    assert tb.total_lines == 3
    assert tb.matching_lines == 2
    assert tb.line_match_pct() == pytest.approx(2 / 3)
    assert tb.ref_pages == 2 and tb.gen_pages == 2
    assert tb.total_words == 15
    # breaks: ref [10, 15], gen [12, 15]; only the first break counts (len-1)
    assert tb.max_break_drift == 2


def test_boundary_drift_keeps_the_sign_of_the_largest_absolute_drift() -> None:
    ref_words = [["w"] * 10, ["w"] * 10, ["w"] * 10]
    gen_words = [["w"] * 7, ["w"] * 14, ["w"] * 9]
    tb = pm.boundary_from_extracts(ref_words, gen_words, [[], [], []], [[], [], []])
    # ref breaks [10, 20, 30], gen [7, 21, 30]; drifts -3, +1 -> -3
    assert tb.max_break_drift == -3
    assert tb.line_match_pct() is None


def test_score_pair_reports_missing_inputs_as_errors(tmp_path: Path) -> None:
    oracle = _make_pdf(tmp_path / "o.pdf", ["hello world"])
    row = pm.score_pair(oracle, tmp_path / "missing.pdf").as_row()
    assert row["converted"] is False
    assert row["error"] == "candidate PDF missing (convert failure)"
    assert row.get("jaccard") is None
    row = pm.score_pair(tmp_path / "nope.pdf", oracle).as_row()
    assert row["converted"] is False
    assert row["error"] == "oracle PDF missing"


def test_score_pair_identity_on_a_generated_pdf(tmp_path: Path) -> None:
    text = "The quick brown fox jumps over the lazy dog. " * 12
    pdf = _make_pdf(tmp_path / "same.pdf", [text, text])
    row = pm.score_pair(pdf, pdf).as_row()
    assert row["converted"] is True
    assert row["jaccard"] == 1.0
    assert row["ssim"] == 1.0
    assert row["text_boundary"] == 1.0
    assert row["max_break_drift"] == 0
    assert row["ref_pages"] == row["pages"] == row["scored_pages"] == 2


def test_score_pair_scores_min_page_count(tmp_path: Path) -> None:
    text = "Pack my box with five dozen liquor jugs. " * 12
    two = _make_pdf(tmp_path / "two.pdf", [text, text])
    one = _make_pdf(tmp_path / "one.pdf", [text])
    row = pm.score_pair(two, one).as_row()
    assert row["ref_pages"] == 2 and row["pages"] == 1 and row["scored_pages"] == 1
    assert row["jaccard"] == 1.0
    assert row["ssim"] == 1.0


def test_jaccard_from_rasters_uses_existing_pngs(tmp_path: Path) -> None:
    """The one-pass pipeline hands over PNGs it already rasterized; no second raster."""
    a = np.full((6, 6, 3), 255, dtype=np.uint8)
    a[1, 1] = 0
    b = a.copy()
    b[1, 2] = 0
    from PIL import Image

    pa, pb = tmp_path / "a.png", tmp_path / "b.png"
    Image.fromarray(a).save(pa)
    Image.fromarray(b).save(pb)
    assert pm.jaccard_from_rasters([pa, pa], [pa, pb]) == pytest.approx((1.0 + 0.5) / 2)
    assert pm.jaccard_from_rasters([], [pa]) is None


@pytest.mark.parametrize("shape", [(8, 8), (7, 16), (16, 7)])
def test_ssim_white_or_no_full_window_scores_one(shape) -> None:
    a = np.full((*shape, 3), 255, dtype=np.uint8)
    b = np.zeros_like(a)
    assert pm.page_ssim(a, b) == 1.0


def test_ssim_uses_image_crate_dynamic_luma_and_population_variance() -> None:
    red = np.full((8, 8, 3), [255, 0, 0], dtype=np.uint8)
    green = np.full((8, 8, 3), [0, 255, 0], dtype=np.uint8)
    # image 0.25.9 DynamicImage::to_luma8 rounds sRGB luminance.
    assert pm.page_ssim(red, green) == pytest.approx(
        (2 * 54 * 182 + 6.5025) / (54**2 + 182**2 + 6.5025), abs=1e-12,
    )
    color = np.full((8, 8, 3), [100, 150, 200], dtype=np.uint8)
    gray = np.full_like(color, 143)  # integer Pixel::to_luma would give 142
    assert pm.page_ssim(color, gray) == 1.0
    a = np.zeros((8, 8, 3), dtype=np.uint8)
    a[::2] = 100
    b = np.zeros_like(a)
    b[::2] = 200
    expected = ((2 * 50 * 100 + 6.5025) * (2 * 5000 + 58.5225)
                / ((50**2 + 100**2 + 6.5025) * (2500 + 10000 + 58.5225)))
    assert pm.page_ssim(a, b) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("shift", [-8, 8])
def test_ssim_searches_eight_pixels_vertically(shift) -> None:
    a = np.full((32, 16, 3), 255, dtype=np.uint8)
    a[12:15, 1:7] = 0
    b = np.roll(a, shift, axis=0)
    assert pm.page_ssim(a, b) == 1.0
    assert pm.page_jaccard(a, b) == 0.0
    assert pm.page_ssim(a, np.roll(a, 9, axis=1)) < 1.0


def test_ssim_skips_only_reference_white_windows_and_partial_edges() -> None:
    a = np.full((10, 18, 3), 200, dtype=np.uint8)
    b = np.zeros_like(a)
    assert pm.page_ssim(a, b) == 1.0  # 200 is not reference ink
    a[0:8, 0:8] = 199
    b[:8, :8] = 199
    a[8:, :] = 0
    a[:, 16:] = 0
    assert pm.page_ssim(a, b) == 1.0  # full second window and edges ignored
    assert pm.page_ssim(b, a) < 1.0  # intentionally asymmetric


@pytest.mark.parametrize("shape", [(10, 10), (8, 10), (10, 8)])
def test_ssim_tolerates_two_pixels(shape) -> None:
    a = np.zeros((8, 8, 3), dtype=np.uint8)
    b = np.zeros((*shape, 3), dtype=np.uint8)
    assert pm.page_ssim(a, b) == 1.0


@pytest.mark.parametrize("shape", [(11, 8), (8, 11)])
def test_ssim_refuses_three_pixels(shape) -> None:
    with pytest.raises(pm.PageSizeMismatch):
        pm.page_ssim(np.zeros((8, 8, 3), dtype=np.uint8), np.zeros((*shape, 3), dtype=np.uint8))


def test_ssim_from_rasters_is_shared_page_mean(tmp_path: Path) -> None:
    from PIL import Image

    a = np.zeros((8, 8, 3), dtype=np.uint8)
    b = np.full_like(a, 100)
    pa, pb, bad = (tmp_path / name for name in ("a.png", "b.png", "bad.png"))
    Image.fromarray(a).save(pa)
    Image.fromarray(b).save(pb)
    Image.fromarray(np.zeros((11, 8, 3), dtype=np.uint8)).save(bad)
    assert pm.ssim_from_rasters([pa, pa], [pa, pb, bad]) == pytest.approx(
        (1 + 6.5025 / (10000 + 6.5025)) / 2, abs=1e-12,
    )
    assert pm.ssim_from_rasters([], [pa]) is None
    assert pm.ssim_from_rasters([pa], [bad]) is None
