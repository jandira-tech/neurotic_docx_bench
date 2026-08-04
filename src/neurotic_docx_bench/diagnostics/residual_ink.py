"""S0.2 — residual-ink cause classifier (execution contract C5).

The near-miss-closure stages of all three jubarte plans (L4/R4/A4) say the same
thing: "diff the candidate render against the oracle render and classify the single
largest residual ink region … group by cause, fix by group". The perfect-count
target rests on that grouping, and until now the classifier was presupposed and
never built. This is it.

The pipeline, per page: ink masks (score.py's, not a second one) → *unmatched* ink
(ink on one side with no counterpart within score.py's 2px tolerance) → group the
unmatched pixels into regions → take the largest → read its geometry → apply an
ordered rule set → emit a label with a confidence and every number the rule used.

WHAT THIS CANNOT TELL YOU — read before quoting any label
---------------------------------------------------------
1. **It attributes pixels to a SHAPE, not to OOXML.** ``MARGINAL_GLYPH`` means "a
   small residual sits against the left margin". That is a *hypothesis* about a
   pilcrow, a list marker or a numbering field. It is not proof of one, and nothing
   here parses a ``.docx``. The whole audit this repo is engaged in exists because
   our own infrastructure has repeatedly been mistaken for vendor behaviour; do not
   restart that habit here by reading these labels as OOXML findings.
2. **DIFFUSE and VERTICAL_SHIFT are the confusable pair.** A global font or metric
   difference displaces everything below the first line, which is geometrically
   what an inserted empty paragraph does. The only discriminator available is
   whether the residual starts at the top of the page's ink (``starts_at_ink_top``),
   and it only lowers a confidence — it never changes the label. If a corpus comes
   back overwhelmingly VERTICAL_SHIFT, suspect a font before believing in 400
   inserted paragraphs.
3. **One region per page, one page per document.** A page with two independent
   defects reports only the larger; ``classify_document`` reports only the page with
   the largest residual. The frequency table is therefore a table of *dominant*
   causes, not of all causes.
4. **It inherits every artefact of the render path.** DPI, font substitution and the
   LibreOffice-vs-Word oracle gap all land in the residual and get labelled as if
   they were candidate defects. This classifier cannot distinguish "the tool did
   something wrong" from "our renderer did something different".
5. **There is a floor and things hide under it.** Residual components smaller than
   ``ScoreConfig.ink_min_size`` (24px) are discarded, the same floor score.py uses
   for ink. A hairline table rule, a one-pixel underline extent or a punctuation
   difference can sit below it and be reported as ``NONE``.
6. **Grouping is a tunable, and the taxonomy moves with it.** ``merge_dilate_px``
   decides whether adjacent glyph residuals are one region or fifty, which decides
   DIFFUSE against everything else. Change it and the frequency table changes; two
   tables built with different configs are not comparable.

Argument order is ``(candidate, oracle)`` throughout — deliberately the OPPOSITE of
``score.score_document(word_pages, jubarte_pages)``. The residual itself is
symmetric, but ``candidate_frac`` is not: swap them and "we dropped this ink" reads
as "we invented this ink".
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import numpy as np
from scipy import ndimage
from skimage import color, measure, morphology

# score.py is parity-locked and owns the ink model, the alignment step and the match
# tolerance. Import them; a second rasteriser or a second notion of "ink" would make
# this diagnostic disagree with the scorer it is supposed to explain.
from neurotic_docx_bench.score import (
    ScoreConfig,
    _align_images,
    _ink_mask,
    _load_image,
    _resize_to_match,
)


class Cause(StrEnum):
    """Geometric cause classes. The names describe a SHAPE and hint at a cause; see
    the module docstring for what that hint is and is not worth."""

    NONE = "none"
    MARGINAL_GLYPH = "marginal_glyph"
    INLINE_SPAN = "inline_span"
    VERTICAL_SHIFT = "vertical_shift"
    BLOCK = "block"
    DIFFUSE = "diffuse"


@dataclass(frozen=True)
class ResidualConfig:
    """Thresholds for the rule set. All fractions are of the page, so a config is
    DPI-independent; ``merge_dilate_px`` is not, and is the one knob to revisit if the
    render DPI changes away from 144."""

    score: ScoreConfig = field(default_factory=ScoreConfig)
    align: bool = True
    # Grouping. ~8px of iterated cross-dilation ≈ a diamond of radius 8, the same
    # idiom score_v2 uses on its change mask: it joins the glyph residuals of one
    # text line, and the lines of one displaced column, into a single region.
    merge_dilate_px: int = 8
    # One text line at 144dpi ≈ 2.2% of the page height; a residual up to 1.6 of
    # those still counts as confined to one line (descenders, a taller run).
    line_band_frac: float = 0.022
    line_band_multiple: float = 1.6
    # "At the left margin" and "narrow", as fractions of the page width.
    margin_band_frac: float = 0.18
    marginal_max_width_frac: float = 0.10
    # Solid enough to be an object rather than displaced text.
    block_min_fill: float = 0.55
    # Tall enough that whatever happened affected the rest of the column.
    vertical_min_height_frac: float = 0.45
    # No region dominates + many regions ⇒ the page, not a region, is the defect.
    diffuse_max_dominance: float = 0.25
    diffuse_min_components: int = 8


DEFAULT_CONFIG = ResidualConfig()

# No geometric attribution is allowed to look certain: these are hypotheses about a
# cause, and a rule that fires exactly on its threshold is barely a hypothesis.
_CONF_MIN = 0.55
_CONF_MAX = 0.95
_CONF_FALLBACK_MAX = 0.75
# When a competing hypothesis fits the same pixels, no amount of shape agreement can
# lift the label above this: a ceiling, not a discount, so a taller region cannot earn
# its way back past a label that is genuinely ambiguous.
_CONF_AMBIGUOUS = 0.65


@dataclass(frozen=True)
class Region:
    """The largest residual region on a page, plus the page-level census that decides
    whether "largest" means anything. All pixel counts are of the UNDILATED residual;
    dilation is used for grouping only, so a page of scattered glyph residual does not
    acquire a solid-looking fill ratio on its way through the grouping step."""

    bbox: tuple[int, int, int, int]  # (top, left, bottom, right); bottom/right exclusive
    area: int  # residual pixels in this region
    candidate_area: int  # of those, the ones that are candidate-only ink
    residual_area: int  # residual pixels on the whole page
    component_count: int  # grouped residual regions on the whole page
    ink_bbox: tuple[int, int, int, int]  # bbox of candidate-ink ∪ oracle-ink

    @property
    def height(self) -> int:
        return self.bbox[2] - self.bbox[0]

    @property
    def width(self) -> int:
        return self.bbox[3] - self.bbox[1]

    @property
    def fill_ratio(self) -> float:
        """Residual pixels over bounding-box area. Solid objects approach 1.0; text —
        displaced or otherwise — sits well under it, because glyphs are mostly paper."""
        box = self.height * self.width
        return float(self.area / box) if box else 0.0

    @property
    def dominance(self) -> float:
        """Share of the page's residual this one region holds."""
        return float(self.area / self.residual_area) if self.residual_area else 0.0


@dataclass(frozen=True)
class Geometry:
    """Every measurement that entered the decision, in the units the rules used. A
    label without this is not auditable, so it is emitted whenever a region exists."""

    bbox: tuple[int, int, int, int]
    area_px: int
    height_px: int
    width_px: int
    height_frac: float
    width_frac: float
    left_edge_frac: float
    fill_ratio: float
    dominance: float
    component_count: int
    candidate_frac: float  # 1.0 = candidate-only ink (extra), 0.0 = oracle-only (missing)
    starts_at_ink_top: bool
    line_band_px: float


@dataclass(frozen=True)
class CauseLabel:
    """A cause class, how much the geometry supports it, and the evidence."""

    cause: Cause
    confidence: float
    geometry: Geometry | None
    rule: str  # which branch fired, for grouping and for arguing with
    note: str  # the reading in words, including the competing hypothesis


@dataclass(frozen=True)
class DocumentCause:
    """A document's dominant cause: the label of its worst page."""

    label: CauseLabel
    page: int | None  # 1-based; None when no page had a residual region
    page_count: int


def _as_rgb(page: np.ndarray) -> np.ndarray:
    """Accept either a grayscale or an RGB page. Alignment warps RGB, and rgb2gray of
    a stacked gray channel is the identity (the luma weights sum to 1), so widening is
    lossless and keeps one code path."""
    arr = np.asarray(page, dtype=np.float32)
    if arr.ndim == 2:
        return np.repeat(arr[..., None], 3, axis=2)
    if arr.ndim == 3 and arr.shape[2] >= 3:
        return arr[..., :3]
    raise ValueError(f"expected a 2-D gray or 3-D RGB page, got shape {arr.shape}")


def _unmatched(a: np.ndarray, b: np.ndarray, tol_px: float) -> np.ndarray:
    """Ink in ``a`` with no ``b`` ink within ``tol_px``.

    The complement of the match rule in ``score._f1_with_tolerance`` (which computes
    the same distance transform and keeps ``dt <= tol``). Sharing the rule is what
    keeps the residual this module reports consistent with the score it explains:
    anti-aliasing halos and sub-pixel edge wobble are matched, not residual.
    """
    if not a.any():
        return np.zeros_like(a, dtype=bool)
    if not b.any():
        return a.copy()
    return a & (ndimage.distance_transform_edt(~b) > tol_px)


def _mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int]:
    rows = np.flatnonzero(mask.any(axis=1))
    cols = np.flatnonzero(mask.any(axis=0))
    return (int(rows[0]), int(cols[0]), int(rows[-1]) + 1, int(cols[-1]) + 1)


def largest_residual_region(
    candidate_page: np.ndarray,
    oracle_page: np.ndarray,
    *,
    config: ResidualConfig = DEFAULT_CONFIG,
) -> Region | None:
    """The single largest residual-ink region between two rasterised pages.

    ``None`` when no residual component survives score.py's ink floor — which means
    "nothing this classifier can see", not "the pages are identical" (limit 5).

    Tie-break: strictly larger area wins; on an exact tie, the region whose bounding
    box starts higher, then further left. Ties are broken deterministically so a
    frequency table over a corpus is reproducible from the pages alone — not because
    the upper region is the likelier cause. On a tie the choice is arbitrary.
    """
    oracle_rgb = _as_rgb(oracle_page)
    cand_rgb = _resize_to_match(oracle_rgb, _as_rgb(candidate_page))
    oracle_gray = color.rgb2gray(oracle_rgb)
    if config.align:
        # Same alignment the scorer applies, for the same reason: a whole-page
        # translation under max_shift_px is a render artefact, not a defect.
        cand_rgb = _align_images(oracle_gray, color.rgb2gray(cand_rgb), cand_rgb, config.score)
    cand_gray = color.rgb2gray(cand_rgb)

    ink_cand = _ink_mask(cand_gray, config.score.ink_min_size)
    ink_oracle = _ink_mask(oracle_gray, config.score.ink_min_size)
    if not (ink_cand.any() or ink_oracle.any()):
        return None

    tol = config.score.ink_tol_px
    cand_only = _unmatched(ink_cand, ink_oracle, tol)
    oracle_only = _unmatched(ink_oracle, ink_cand, tol)
    residual = morphology.remove_small_objects(cand_only | oracle_only, max_size=config.score.ink_min_size)
    if not residual.any():
        return None

    # Dilate to GROUP; measure on the original pixels. Grouping decides what counts as
    # one region (a text line, a displaced column); it must not decide how solid that
    # region looks, or every sparse page would read as a block.
    grouped = (
        ndimage.binary_dilation(residual, iterations=config.merge_dilate_px)
        if config.merge_dilate_px > 0
        else residual
    )
    labels = measure.label(grouped, connectivity=2)
    region_labels = np.where(residual, labels, 0)
    count = int(labels.max())
    areas = ndimage.sum_labels(residual, region_labels, index=np.arange(1, count + 1))
    boxes = ndimage.find_objects(region_labels)

    best_key: tuple[int, int, int] | None = None  # (-area, top, left) — see the tie-break
    best_idx = -1
    for idx, box in enumerate(boxes):
        if box is None:  # a group whose residual vanished — cannot happen, cheap to guard
            continue
        key = (-int(areas[idx]), int(box[0].start), int(box[1].start))
        if best_key is None or key < best_key:
            best_key, best_idx = key, idx
    if best_key is None:
        return None

    _, top, left = best_key
    box = boxes[best_idx]
    region_mask = region_labels == best_idx + 1
    return Region(
        bbox=(top, left, int(box[0].stop), int(box[1].stop)),
        area=int(region_mask.sum()),
        candidate_area=int((region_mask & cand_only).sum()),
        residual_area=int(residual.sum()),
        component_count=sum(1 for b in boxes if b is not None),
        ink_bbox=_mask_bbox(ink_cand | ink_oracle),
    )


def _ramp(value: float, lo: float, hi: float) -> float:
    """0 at ``lo``, 1 at ``hi``, clamped between. ``lo > hi`` gives a falling ramp."""
    if lo == hi:
        return 1.0 if value >= hi else 0.0
    return float(min(1.0, max(0.0, (value - lo) / (hi - lo))))


def _confidence(strength: float, *, ceiling: float = _CONF_MAX) -> float:
    return float(_CONF_MIN + (ceiling - _CONF_MIN) * min(1.0, max(0.0, strength)))


def _side(geom: Geometry) -> str:
    if geom.candidate_frac >= 0.9:
        return "ink the candidate paints and the oracle does not"
    if geom.candidate_frac <= 0.1:
        return "ink the oracle has and the candidate is missing"
    return "ink on both sides — displaced rather than added or dropped"


def _geometry(region: Region, page_shape: tuple[int, int], config: ResidualConfig) -> Geometry:
    page_h, page_w = int(page_shape[0]), int(page_shape[1])
    line_band = page_h * config.line_band_frac * config.line_band_multiple
    return Geometry(
        bbox=region.bbox,
        area_px=region.area,
        height_px=region.height,
        width_px=region.width,
        height_frac=region.height / page_h if page_h else 0.0,
        width_frac=region.width / page_w if page_w else 0.0,
        left_edge_frac=region.bbox[1] / page_w if page_w else 0.0,
        fill_ratio=region.fill_ratio,
        dominance=region.dominance,
        component_count=region.component_count,
        candidate_frac=float(region.candidate_area / region.area) if region.area else 0.0,
        # Within one line band of the first ink on the page: a displacement that starts
        # at the top of the ink is indistinguishable from every glyph changing size.
        starts_at_ink_top=(region.bbox[0] - region.ink_bbox[0]) <= line_band,
        line_band_px=line_band,
    )


def classify(
    region: Region | None,
    *,
    page_shape: tuple[int, int],
    config: ResidualConfig = DEFAULT_CONFIG,
) -> CauseLabel:
    """Attribute a residual region to a cause class.

    The rules, in the order they are tried — first match wins, and the order is load
    bearing:

    1. **no region** → ``NONE``. Nothing above the ink floor.
    2. **no region dominates** (share ≤ ``diffuse_max_dominance`` across ≥
       ``diffuse_min_components`` regions) → ``DIFFUSE``. When the residual is spread
       over the page, the largest region's shape is an accident of thresholding and
       must not be read as evidence — hence this test runs before any shape test.
    3. **tall and solid** (≥ ``vertical_min_height_frac`` of the page, fill ≥
       ``block_min_fill``) → ``BLOCK``. Column height alone is not displacement; a
       solid full-height object is an object.
    4. **tall and sparse** → ``VERTICAL_SHIFT``. Content below some point moved:
       spacing, an inserted empty paragraph, a list that wrapped a line earlier. The
       confidence is cut when the residual starts at the top of the page's ink,
       because a global font or metric change fits those pixels equally well.
    5. **one line tall, left-anchored and narrow** → ``MARGINAL_GLYPH``. The pilcrow /
       list-marker / numbering hypothesis. Note this is LEFT only: in an RTL document
       the marker sits on the right and this rule will not fire.
    6. **one line tall** → ``INLINE_SPAN``. A run-level formatting or wording
       difference on a single line.
    7. **anything else** → ``BLOCK``, split by fill into ``solid-block`` (an image, a
       shaded cell) and ``multi-line-block`` (several lines' worth — a paragraph
       difference). ``multi-line-block`` is the fallback bucket and is capped at a
       lower confidence than any rule that actually matched a shape.
    """
    if region is None:
        return CauseLabel(
            cause=Cause.NONE,
            confidence=1.0,
            geometry=None,
            rule="no-residual",
            note=(
                f"no residual component of ≥{config.score.ink_min_size}px after {config.score.ink_tol_px}px "
                "match tolerance; differences below that floor are invisible here"
            ),
        )

    geom = _geometry(region, page_shape, config)
    side = _side(geom)

    if geom.dominance <= config.diffuse_max_dominance and geom.component_count >= config.diffuse_min_components:
        strength = min(
            _ramp(geom.dominance, config.diffuse_max_dominance, 0.0),
            _ramp(float(geom.component_count), float(config.diffuse_min_components), 40.0),
        )
        return CauseLabel(
            cause=Cause.DIFFUSE,
            confidence=_confidence(strength),
            geometry=geom,
            rule="no-dominant-region",
            note=(
                f"{geom.component_count} residual regions, the largest holding only "
                f"{geom.dominance:.0%} of the residual: the page differs, not a place on it. "
                "Usually a font substitution or a global metric difference; the largest "
                "region's shape is not evidence here"
            ),
        )

    if geom.height_frac >= config.vertical_min_height_frac:
        if geom.fill_ratio >= config.block_min_fill:
            return CauseLabel(
                cause=Cause.BLOCK,
                confidence=_confidence(_ramp(geom.fill_ratio, config.block_min_fill, 1.0)),
                geometry=geom,
                rule="tall-solid",
                note=(
                    f"{geom.height_frac:.0%} of the page height at {geom.fill_ratio:.0%} fill — solid, so "
                    f"an object (image, shaded cell, rule) rather than displaced text; {side}"
                ),
            )
        strength = _ramp(geom.height_frac, config.vertical_min_height_frac, 0.9)
        ceiling = _CONF_AMBIGUOUS if geom.starts_at_ink_top else _CONF_MAX
        return CauseLabel(
            cause=Cause.VERTICAL_SHIFT,
            confidence=_confidence(strength, ceiling=ceiling),
            geometry=geom,
            rule="column-height-sparse",
            note=(
                f"sparse residual ({geom.fill_ratio:.0%} fill) over {geom.height_frac:.0%} of the page "
                f"height: content below row {geom.bbox[0]} is displaced — spacing, an inserted empty "
                "paragraph, or an earlier line wrap"
                + (
                    ". It starts at the top of the page's ink, so a GLOBAL font or metric change fits "
                    "these pixels just as well — treat the label as a guess"
                    if geom.starts_at_ink_top
                    else f"; content above row {geom.bbox[0]} matches"
                )
            ),
        )

    if geom.height_px <= geom.line_band_px:
        if geom.left_edge_frac <= config.margin_band_frac and geom.width_frac <= config.marginal_max_width_frac:
            strength = min(
                _ramp(geom.left_edge_frac, config.margin_band_frac, 0.0),
                _ramp(geom.width_frac, config.marginal_max_width_frac, 0.0),
            )
            return CauseLabel(
                cause=Cause.MARGINAL_GLYPH,
                confidence=_confidence(strength),
                geometry=geom,
                rule="left-margin-glyph",
                note=(
                    f"{geom.height_px}×{geom.width_px}px against the left margin "
                    f"({geom.left_edge_frac:.0%} in): consistent with a pilcrow, list marker or "
                    f"numbering field — a hypothesis about a mark, not a reading of the markup; {side}"
                ),
            )
        return CauseLabel(
            cause=Cause.INLINE_SPAN,
            confidence=_confidence(_ramp(geom.height_px / geom.line_band_px, 1.0, 0.4)),
            geometry=geom,
            rule="single-line",
            note=(
                f"confined to one line band ({geom.height_px}px of {geom.line_band_px:.0f}px) and "
                f"{geom.width_frac:.0%} of the page wide: a run-level formatting or wording "
                f"difference; {side}"
            ),
        )

    if geom.fill_ratio >= config.block_min_fill:
        return CauseLabel(
            cause=Cause.BLOCK,
            confidence=_confidence(_ramp(geom.fill_ratio, config.block_min_fill, 1.0)),
            geometry=geom,
            rule="solid-block",
            note=(
                f"solid {geom.height_px}×{geom.width_px}px region at {geom.fill_ratio:.0%} fill: an "
                f"image, a shaded cell or a filled shape; {side}"
            ),
        )

    return CauseLabel(
        cause=Cause.BLOCK,
        confidence=_confidence(
            _ramp(geom.height_px / geom.line_band_px, 1.0, 6.0), ceiling=_CONF_FALLBACK_MAX,
        ),
        geometry=geom,
        rule="multi-line-block",
        note=(
            f"{geom.height_px // max(1, int(geom.line_band_px))}+ lines' worth of sparse residual "
            f"({geom.fill_ratio:.0%} fill): a paragraph-level difference. This is the fallback "
            f"bucket — it matched no shape, so the confidence is capped; {side}"
        ),
    )


def classify_page(
    candidate_page: np.ndarray,
    oracle_page: np.ndarray,
    *,
    config: ResidualConfig = DEFAULT_CONFIG,
) -> CauseLabel:
    """``largest_residual_region`` then ``classify``, for one page."""
    region = largest_residual_region(candidate_page, oracle_page, config=config)
    shape = np.asarray(oracle_page).shape
    return classify(region, page_shape=(int(shape[0]), int(shape[1])), config=config)


def classify_document(
    candidate_pages: Sequence[Path],
    oracle_pages: Sequence[Path],
    *,
    config: ResidualConfig = DEFAULT_CONFIG,
) -> DocumentCause:
    """The dominant cause for a document: the label of the page carrying the largest
    residual region.

    Pages are paired by index up to the shorter list, exactly as ``score_document``
    pairs them. A document whose candidate is short by a page therefore reports on
    what both renders have — the missing page is the pipeline's finding, not this
    module's (limit 3).
    """
    n_pages = min(len(candidate_pages), len(oracle_pages))
    if n_pages == 0:
        raise ValueError("no page pairs to classify")

    best_region: Region | None = None
    best_shape = (0, 0)
    best_page = 0
    for idx in range(n_pages):
        oracle_rgb = _load_image(oracle_pages[idx])
        cand_rgb = _resize_to_match(oracle_rgb, _load_image(candidate_pages[idx]))
        region = largest_residual_region(cand_rgb, oracle_rgb, config=config)
        if region is not None and (best_region is None or region.area > best_region.area):
            best_region = region
            best_shape = (int(oracle_rgb.shape[0]), int(oracle_rgb.shape[1]))
            best_page = idx + 1

    if best_region is None:
        oracle_rgb = _load_image(oracle_pages[0])
        best_shape = (int(oracle_rgb.shape[0]), int(oracle_rgb.shape[1]))

    return DocumentCause(
        label=classify(best_region, page_shape=best_shape, config=config),
        page=best_page or None,
        page_count=n_pages,
    )


def cause_frequency(labels: Iterable[CauseLabel | DocumentCause | Cause]) -> Counter[Cause]:
    """Frequency table over a document set, so near-misses are fixed by group.

    Accepts labels, per-document results or bare causes. Anything else raises — a
    silently-miscounted census is worse than no census.
    """
    counts: Counter[Cause] = Counter()
    for item in labels:
        match item:
            case Cause():
                counts[item] += 1
            case CauseLabel():
                counts[item.cause] += 1
            case DocumentCause():
                counts[item.label.cause] += 1
            case _:
                raise TypeError(f"not a Cause, CauseLabel or DocumentCause: {item!r}")
    return counts
