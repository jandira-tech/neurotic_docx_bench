"""S0.2 — residual-ink cause classifier (execution contract C5).

Every fixture here is a SYNTHETIC page built from numpy, never a rendered document:
the classifier is a geometry rule set and its unit tests must not depend on
LibreOffice, fonts, or DPI. The pages are drawn text-LIKE rather than solid — real
glyphs fill ~40% of their line box, and the solid-vs-sparse discriminator the
classifier leans on is meaningless against solid bars.

Layout convention: a short shared paragraph at rows 100-208 gives both pages real
ink (so Otsu has something to threshold), and every synthetic defect is drawn below
row 240 so it lands on paper — ink drawn on top of identical ink is not a residual.

Page convention matches ``score._load_image``: float in [0, 1], 1.0 = paper, 0.0 = ink.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from neurotic_docx_bench.diagnostics import residual_ink as ri
from neurotic_docx_bench.diagnostics.residual_ink import Cause

PAGE_H, PAGE_W = 800, 600
SHAPE = (PAGE_H, PAGE_W)
INK = 0.0
PAPER = 1.0

# Alignment off wherever the test's point is the geometry: ``score._align_images`` may
# warp by a sub-pixel amount and blur the ink masks. One test covers it switched on.
NO_ALIGN = ri.ResidualConfig(align=False)


def blank() -> np.ndarray:
    return np.full(SHAPE, PAPER, dtype=np.float32)


def text_line(page: np.ndarray, top: int, col0: int = 60, col1: int = 540, height: int = 18) -> None:
    """One line of glyph-ish dashes (6 on, 8 off) — ~43% ink inside its line box."""
    for col in range(col0, col1, 14):
        page[top : top + height, col : min(col + 6, col1)] = INK


def paragraph(page: np.ndarray, top: int, bottom: int, pitch: int = 30, **kw) -> None:
    """Lines on a 30px pitch: 18px of glyph, 12px of leading — a 144dpi-ish body."""
    for row in range(top, bottom, pitch):
        text_line(page, row, **kw)


def context_page() -> np.ndarray:
    """Shared ink both pages carry, well clear of where the defects get drawn."""
    page = blank()
    paragraph(page, 100, 220)
    return page


def write_png(path: Path, page: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((np.clip(page, 0.0, 1.0) * 255).astype(np.uint8), mode="L").save(path)
    return path


def label_for(
    candidate: np.ndarray, oracle: np.ndarray, config: ri.ResidualConfig = NO_ALIGN,
) -> ri.CauseLabel:
    return ri.classify_page(candidate, oracle, config=config)


# --------------------------------------------------------------------------- NONE


def test_identical_pages_have_no_residual_region():
    page = context_page()
    assert ri.largest_residual_region(page, page.copy(), config=NO_ALIGN) is None

    label = label_for(page, page.copy())
    assert label.cause is Cause.NONE
    assert label.confidence == 1.0
    assert label.geometry is None


def test_blank_pages_are_none():
    """Otsu has no threshold to find on a constant page; score.py's fallback keeps the
    ink mask empty rather than declaring the whole page ink."""
    assert label_for(blank(), blank()).cause is Cause.NONE


def test_subthreshold_speck_is_invisible_to_the_classifier():
    """A 9px mark never becomes ink at all: score.py's ``ink_min_size`` (24px) drops it
    from the ink mask before any residual is computed. A real blind spot, pinned
    deliberately — a hairline rule or a short underline extent can hide under it."""
    candidate = context_page()
    oracle = candidate.copy()
    oracle[400:403, 300:303] = INK
    assert label_for(candidate, oracle).cause is Cause.NONE


def test_a_small_unmatched_piece_of_a_large_object_is_dropped_by_the_floor():
    """The second floor, which bites where the first does not: the oracle's notch is
    part of a large ink object, so it survives the ink mask, but only 12px of it are
    unmatched and the residual floor discards that. This is how a punctuation-sized
    difference inside a real line of text disappears — the honest reading of NONE is
    "nothing above the floor", never "identical"."""
    candidate = blank()
    candidate[100:118, 60:540] = INK
    oracle = candidate.copy()
    oracle[95:100, 200:204] = INK  # a 5x4 notch welded to the top of the bar

    assert label_for(candidate, oracle).cause is Cause.NONE


def test_a_one_pixel_edge_difference_is_matched_not_residual():
    """Residual means ink with no counterpart within score.py's 2px tolerance — the
    same rule ``_f1_with_tolerance`` scores by. Anti-aliasing and sub-pixel edge wobble
    are matched, so this diagnostic and the score it explains agree on what counts as a
    difference. A raw XOR would report 480px of "defect" here."""
    candidate = blank()
    candidate[100:118, 60:540] = INK
    oracle = blank()
    oracle[100:119, 60:540] = INK  # one row taller

    assert label_for(candidate, oracle).cause is Cause.NONE


# ------------------------------------------------------------------- MARGINAL_GLYPH


def test_small_left_margin_blob_is_marginal_glyph():
    candidate = context_page()
    oracle = candidate.copy()
    oracle[300:316, 20:40] = INK  # under one line band, hard against the left margin

    label = label_for(candidate, oracle)
    assert label.cause is Cause.MARGINAL_GLYPH
    assert label.rule == "left-margin-glyph"
    assert label.geometry is not None
    assert label.geometry.left_edge_frac < 0.1
    # The candidate is MISSING the mark, not painting an extra one.
    assert label.geometry.candidate_frac == pytest.approx(0.0)


def test_the_same_blob_away_from_the_margin_is_not_marginal():
    """The label is positional, not semantic — move the identical blob into the text
    column and the same pixels become an inline difference."""
    candidate = context_page()
    oracle = candidate.copy()
    oracle[300:316, 300:320] = INK
    assert label_for(candidate, oracle).cause is Cause.INLINE_SPAN


# ----------------------------------------------------------------------- INLINE_SPAN


def test_single_line_residual_is_inline_span():
    candidate = context_page()
    oracle = candidate.copy()
    text_line(oracle, 400, col0=200, col1=380)  # one line's worth, mid-column

    label = label_for(candidate, oracle)
    assert label.cause is Cause.INLINE_SPAN
    assert label.geometry is not None
    assert label.geometry.height_px <= label.geometry.line_band_px


def test_extra_ink_on_the_candidate_side_is_reported():
    """The residual is symmetric; which side carries the extra ink is not, and it is
    the difference between "we dropped it" and "we invented it"."""
    oracle = context_page()
    candidate = oracle.copy()
    text_line(candidate, 400, col0=200, col1=380)

    label = label_for(candidate, oracle)
    assert label.cause is Cause.INLINE_SPAN
    assert label.geometry is not None
    assert label.geometry.candidate_frac == pytest.approx(1.0)


# -------------------------------------------------------------------- VERTICAL_SHIFT


def shifted_pair(shift_from: int, shift_px: int = 15) -> tuple[np.ndarray, np.ndarray]:
    """Candidate = a plain column; oracle = the same column with everything from
    ``shift_from`` down displaced by ``shift_px`` — an inserted empty paragraph, or a
    spacing difference, or a list that wrapped one line earlier. The classifier cannot
    tell those apart and does not claim to."""
    candidate = blank()
    paragraph(candidate, 100, 740)
    oracle = blank()
    for row in range(100, 740, 30):
        text_line(oracle, row + (shift_px if row >= shift_from else 0))
    return candidate, oracle


def test_displaced_column_is_vertical_shift():
    candidate, oracle = shifted_pair(shift_from=250)
    label = label_for(candidate, oracle)
    assert label.cause is Cause.VERTICAL_SHIFT
    assert label.rule == "column-height-sparse"
    assert label.geometry is not None
    assert label.geometry.height_frac >= NO_ALIGN.vertical_min_height_frac
    assert label.geometry.fill_ratio < NO_ALIGN.block_min_fill
    assert not label.geometry.starts_at_ink_top


def test_shift_starting_at_the_top_of_the_ink_is_less_confident():
    """If the residual starts where the page's ink starts, "everything moved down" and
    "every glyph is a different size" are equally consistent with the pixels. The label
    still says VERTICAL_SHIFT; the confidence says we are guessing."""
    from_top = label_for(*shifted_pair(shift_from=100))
    from_middle = label_for(*shifted_pair(shift_from=250))
    assert from_top.cause is from_middle.cause is Cause.VERTICAL_SHIFT
    assert from_top.geometry is not None and from_top.geometry.starts_at_ink_top
    # A material gap, not a rounding one: the ambiguous case is CAPPED, so the taller
    # residual cannot earn its confidence back through the height ramp.
    assert from_top.confidence < from_middle.confidence - 0.05
    assert "global" in from_top.note.lower()


# --------------------------------------------------------------------------- BLOCK


def solid_block_pair() -> tuple[np.ndarray, np.ndarray]:
    candidate = context_page()
    oracle = candidate.copy()
    oracle[250:450, 150:450] = INK  # an image, or a shaded table cell
    return candidate, oracle


def test_solid_rectangle_is_block():
    label = label_for(*solid_block_pair())
    assert label.cause is Cause.BLOCK
    assert label.rule == "solid-block"
    assert label.geometry is not None
    assert label.geometry.fill_ratio > 0.9


def test_tall_solid_region_is_block_not_vertical_shift():
    """Ordering test: column height alone does not make it a displacement. A solid
    full-height object is a block, and solidity is checked first inside the tall branch."""
    candidate = context_page()
    oracle = candidate.copy()
    oracle[240:740, 200:400] = INK

    label = label_for(candidate, oracle)
    assert label.cause is Cause.BLOCK
    assert label.rule == "tall-solid"


def test_multi_line_sparse_residual_is_block_with_lower_confidence():
    """Neither one line nor a whole column: the fallback bucket. It is deliberately the
    least confident label in the taxonomy."""
    candidate = context_page()
    oracle = candidate.copy()
    paragraph(oracle, 300, 390)

    label = label_for(candidate, oracle)
    assert label.cause is Cause.BLOCK
    assert label.rule == "multi-line-block"
    assert label.confidence < label_for(*solid_block_pair()).confidence


# ------------------------------------------------------------------------- DIFFUSE


def scattered_pair() -> tuple[np.ndarray, np.ndarray]:
    """Every mark on the page moves a little, in no consistent direction — what a font
    substitution or a global metric change looks like from the pixels."""
    rng = np.random.default_rng(7)
    candidate = blank()
    oracle = blank()
    for row in range(60, 780, 60):
        for col in range(50, 560, 100):
            candidate[row : row + 6, col : col + 6] = INK
            dr, dc = (int(v) for v in rng.choice([-10, 10], size=2))
            oracle[row + dr : row + dr + 6, col + dc : col + dc + 6] = INK
    return candidate, oracle


def test_scattered_differences_are_diffuse():
    label = label_for(*scattered_pair())
    assert label.cause is Cause.DIFFUSE
    assert label.geometry is not None
    assert label.geometry.dominance <= NO_ALIGN.diffuse_max_dominance
    assert label.geometry.component_count >= NO_ALIGN.diffuse_min_components


def test_diffuse_is_decided_before_the_shape_of_the_largest_region():
    """The dominance test runs FIRST: when no region dominates, the largest region's
    shape is not evidence about the page. Same scattered pixels, one dominant region
    added, and the verdict flips to that region's shape."""
    candidate, oracle = scattered_pair()
    oracle[250:450, 150:450] = INK
    assert label_for(candidate, oracle).cause is Cause.BLOCK


# ------------------------------------------------------------------------ tie-break


def two_blobs(top_a: int, height_a: int, top_b: int, height_b: int) -> tuple[np.ndarray, np.ndarray]:
    candidate = blank()
    oracle = candidate.copy()
    oracle[top_a : top_a + height_a, 100:120] = INK
    oracle[top_b : top_b + height_b, 100:120] = INK
    return candidate, oracle


def test_equal_area_regions_break_the_tie_topmost_first():
    """Documented tie-break: strictly larger area wins; on an exact tie the region whose
    bounding box starts higher wins, then leftmost. Deterministic so a frequency table
    over a corpus is reproducible — NOT because the upper region is likelier to be the
    cause. On a tie this classifier is choosing arbitrarily and the confidence says so."""
    region = ri.largest_residual_region(*two_blobs(100, 20, 500, 20), config=NO_ALIGN)
    assert region is not None
    assert region.bbox[0] == 100

    label = ri.classify(region, page_shape=SHAPE, config=NO_ALIGN)
    assert label.geometry is not None
    assert label.geometry.dominance == pytest.approx(0.5)


def test_strictly_larger_region_wins_over_the_higher_one():
    region = ri.largest_residual_region(*two_blobs(100, 20, 500, 21), config=NO_ALIGN)
    assert region is not None
    assert region.bbox[0] == 500


# ------------------------------------------------------------------------- evidence


def test_every_label_carries_auditable_evidence():
    candidate = context_page()
    oracle = candidate.copy()
    oracle[300:316, 20:40] = INK

    label = label_for(candidate, oracle)
    geom = label.geometry
    assert geom is not None
    # Every number that entered the decision is on the record.
    assert geom.bbox == (300, 20, 316, 40)
    assert geom.area_px == 320
    assert geom.height_px == 16
    assert geom.width_px == 20
    assert geom.component_count == 1
    assert geom.dominance == pytest.approx(1.0)
    assert geom.fill_ratio == pytest.approx(1.0)
    assert 0.0 < label.confidence <= 1.0
    assert label.rule and label.note


def test_no_geometric_label_ever_claims_certainty():
    """Only NONE — a fact about a pixel count — may carry confidence 1.0. Every
    attribution is a hypothesis about a cause and is capped below it."""
    cases = [
        two_blobs(100, 20, 500, 20),
        shifted_pair(shift_from=250),
        scattered_pair(),
        solid_block_pair(),
    ]
    for candidate, oracle in cases:
        label = label_for(candidate, oracle)
        assert label.cause is not Cause.NONE
        assert label.confidence < 1.0


# ---------------------------------------------------------------------- aggregation


def test_cause_frequency_over_a_document_set():
    labels = [
        ri.CauseLabel(Cause.MARGINAL_GLYPH, 0.8, None, rule="r", note="n"),
        ri.CauseLabel(Cause.MARGINAL_GLYPH, 0.6, None, rule="r", note="n"),
        ri.CauseLabel(Cause.VERTICAL_SHIFT, 0.9, None, rule="r", note="n"),
    ]
    freq = ri.cause_frequency(labels)
    assert freq[Cause.MARGINAL_GLYPH] == 2
    assert freq[Cause.VERTICAL_SHIFT] == 1
    assert freq[Cause.BLOCK] == 0
    # Bare causes and per-document results count too, so grouping near-misses by cause
    # is one call regardless of what the caller happens to be holding.
    doc = ri.DocumentCause(label=labels[0], page=1, page_count=3)
    assert ri.cause_frequency([Cause.BLOCK, Cause.BLOCK, doc]) == {
        Cause.BLOCK: 2,
        Cause.MARGINAL_GLYPH: 1,
    }
    assert ri.cause_frequency([]) == {}


def test_cause_frequency_rejects_foreign_values():
    """The cause is a StrEnum, so a bare string would have silently counted under a key
    that compares equal to it. A miscounted census is worse than no census."""
    foreign: list[Any] = ["marginal_glyph"]
    with pytest.raises(TypeError):
        ri.cause_frequency(foreign)


# -------------------------------------------------------------------- page + document


def test_alignment_absorbs_a_whole_page_translation():
    """A uniform sub-threshold translation is a render artefact, not a defect: score.py
    aligns it away and so must this, or the classifier's largest cause class would be
    "the page moved by four pixels"."""
    candidate = blank()
    for row in (100, 200, 300):
        candidate[row : row + 18, 60:540] = INK
    oracle = np.roll(candidate, 4, axis=0)

    assert label_for(candidate, oracle, config=NO_ALIGN).cause is not Cause.NONE
    assert label_for(candidate, oracle, config=ri.ResidualConfig(align=True)).cause is Cause.NONE


def test_classify_document_labels_the_worst_page(tmp_path):
    quiet = context_page()
    big_oracle = quiet.copy()
    big_oracle[250:450, 150:450] = INK
    small_oracle = quiet.copy()
    small_oracle[300:316, 20:40] = INK

    cand = [write_png(tmp_path / "c1.png", quiet), write_png(tmp_path / "c2.png", quiet)]
    oracle = [
        write_png(tmp_path / "o1.png", small_oracle),
        write_png(tmp_path / "o2.png", big_oracle),
    ]

    doc = ri.classify_document(cand, oracle, config=NO_ALIGN)
    assert doc.label.cause is Cause.BLOCK
    assert doc.page == 2  # 1-based; the page with the largest residual wins
    assert doc.page_count == 2


def test_classify_document_on_a_clean_document(tmp_path):
    page = context_page()
    doc = ri.classify_document(
        [write_png(tmp_path / "c1.png", page)],
        [write_png(tmp_path / "o1.png", page)],
        config=NO_ALIGN,
    )
    assert doc.label.cause is Cause.NONE
    assert doc.page is None


def test_classify_document_requires_pages():
    with pytest.raises(ValueError):
        ri.classify_document([], [], config=NO_ALIGN)


def test_rgb_and_grayscale_inputs_agree():
    """Callers hand us whatever the render step produced; both must land on the same
    label rather than silently taking a different code path."""
    candidate = context_page()
    oracle = candidate.copy()
    oracle[300:316, 20:40] = INK
    rgb_candidate = np.repeat(candidate[..., None], 3, axis=2)
    rgb_oracle = np.repeat(oracle[..., None], 3, axis=2)

    assert label_for(candidate, oracle).cause is Cause.MARGINAL_GLYPH
    assert label_for(rgb_candidate, rgb_oracle).cause is Cause.MARGINAL_GLYPH
