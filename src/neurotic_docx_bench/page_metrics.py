"""docxide-pdf's page metrics (ink Jaccard, text boundary), in Python.

A port of the metric code in `sverrejb/docxide-pdf <https://github.com/sverrejb/docxide-pdf>`_
(``tests/common/mod.rs``, ``tests/common/text_boundary.rs``, Apache-2.0), which used to be
vendored here as a Rust crate driving ``mutool``. The port drives the same MuPDF entry
points through PyMuPDF instead (``get_text("text")`` is ``mutool draw -F text``,
``get_text("xml")`` is ``mutool draw -F stext``, ``get_pixmap`` is ``mutool draw -F png``),
and ``tests/test_page_metrics.py`` requires the numbers upstream's own ``page-metrics``
binary produced on five committed corpus pairs.

* **Jaccard** - ink-pixel intersection over union, a pixel being ink when its luma
  ``299 R + 587 G + 114 B`` is under ``200_000``. Placement is everything.
* **Text boundary** - share of lines that begin and end on the same words as the
  oracle, ignoring where the ink landed. Pages whose line counts differ by more than
  15 % are skipped; ``max_break_drift`` is the largest (signed) page-break drift in
  words.

Upstream's SSIM is not ported: the pass this feeds already carries SSIM through the
pagefair-v2 score.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymupdf as fitz
from PIL import Image

#: docxide-pdf rasterizes at 150 DPI; the parity numbers hold only at that DPI.
UPSTREAM_DPI = 150
#: Luma threshold from upstream: ``r*299 + g*587 + b*114 < 200_000`` is ink.
INK_LUMA_MAX = 200_000
#: Page dimension slack (pixels) before two rasters are refused as incomparable.
SIZE_TOLERANCE_PX = 2
#: Lines whose y-tops fall within this many points are one visual line.
LINE_CLUSTER_PT = 8.0
#: A page is skipped when its line counts differ by more than this share.
LINE_COUNT_SKIP = 0.15

ERROR_CANDIDATE_MISSING = "candidate PDF missing (convert failure)"
ERROR_ORACLE_MISSING = "oracle PDF missing"


class PageSizeMismatch(ValueError):
    """Two rasters differ by more than :data:`SIZE_TOLERANCE_PX` in either dimension."""


# ------------------------------------------------------------------- ink ----


def ink_mask(rgb: np.ndarray) -> np.ndarray:
    """Boolean ink mask of an ``(H, W, 3)`` uint8 raster under upstream's luma rule."""
    px = rgb.astype(np.int64)
    luma = px[..., 0] * 299 + px[..., 1] * 587 + px[..., 2] * 114
    return luma < INK_LUMA_MAX


def page_jaccard(a: np.ndarray, b: np.ndarray) -> float:
    """Ink Jaccard of two rasters, cropped to their shared size.

    Dimensions may differ by up to :data:`SIZE_TOLERANCE_PX`; beyond that the pages
    are not the same layout and :class:`PageSizeMismatch` is raised. Two rasters
    with no ink at all score 1.0.
    """
    ha, wa = a.shape[:2]
    hb, wb = b.shape[:2]
    if abs(wa - wb) > SIZE_TOLERANCE_PX or abs(ha - hb) > SIZE_TOLERANCE_PX:
        raise PageSizeMismatch(f"page dimensions differ: {wa}x{ha} vs {wb}x{hb}")
    h, w = min(ha, hb), min(wa, wb)
    ink_a = ink_mask(a[:h, :w])
    ink_b = ink_mask(b[:h, :w])
    union = int(np.logical_or(ink_a, ink_b).sum())
    if union == 0:
        return 1.0
    inter = int(np.logical_and(ink_a, ink_b).sum())
    return inter / union


def _load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as img:
        return np.asarray(img.convert("RGB"), dtype=np.uint8)


def jaccard_from_rasters(oracle_pages: Sequence[Path], cand_pages: Sequence[Path]) -> float | None:
    """Mean page Jaccard over ``min(len)`` already-rasterized PNG pages.

    This is the one-pass entry point: the pipeline rasterizes once for pagefair-v2 and
    hands the same PNGs here. ``None`` when there is no page pair to score or a pair
    is not the same size (see :class:`PageSizeMismatch`).
    """
    n = min(len(oracle_pages), len(cand_pages))
    if n == 0:
        return None
    total = 0.0
    for idx in range(n):
        try:
            total += page_jaccard(_load_rgb(oracle_pages[idx]), _load_rgb(cand_pages[idx]))
        except PageSizeMismatch:
            return None
    return total / n


def _rasterize(doc: fitz.Document, dpi: int) -> list[np.ndarray]:
    pages: list[np.ndarray] = []
    for page in doc:
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        pages.append(arr[..., :3].copy())
    return pages


# ------------------------------------------------------------------ text ----


def normalize_leaders(s: str) -> str:
    """Replace tab-leader dot runs (3+) with a space so only the words are compared."""
    out: list[str] = []
    dots = 0
    for c in s:
        if c == ".":
            dots += 1
            continue
        if dots >= 3:
            out.append(" ")
        else:
            out.append("." * dots)
        dots = 0
        out.append(c)
    if 0 < dots < 3:
        out.append("." * dots)
    return "".join(out)


def first_word(s: str) -> str:
    words = normalize_leaders(s).split()
    return words[0] if words else ""


def last_word(s: str) -> str:
    words = normalize_leaders(s).split()
    return words[-1] if words else ""


def page_words(page: fitz.Page) -> list[str]:
    """Whitespace-split words of ``mutool draw -F text`` for one page."""
    return page.get_text("text").split()


def _parse_stext_lines(xml: str) -> list[tuple[float, float, str]]:
    """``(x_left, y_top, text)`` for every non-empty ``<line>`` of a stext page, parsed the
    way upstream parses ``mutool draw -F stext`` (no XML unescaping: both sides get the
    same treatment, so escapes compare equal)."""
    found: list[tuple[float, float, str]] = []
    for raw in xml.splitlines():
        trimmed = raw.strip()
        if not trimmed.startswith("<line "):
            continue
        rest = trimmed[len("<line "):]
        x_left, y_top = 0.0, 0.0
        if rest.startswith('bbox="'):
            parts = rest[len('bbox="'):].split()
            try:
                x_left, y_top = float(parts[0]), float(parts[1])
            except (IndexError, ValueError):
                x_left, y_top = 0.0, 0.0
        start = rest.find('text="')
        if start < 0:
            continue
        after = rest[start + len('text="'):]
        end = after.find('"')
        if end < 0:
            continue
        text = after[:end].strip()
        if text:
            found.append((x_left, y_top, text))
    return found


def cluster_lines(found: Sequence[tuple[float, float, str]]) -> list[str]:
    """Sort by y, cluster within :data:`LINE_CLUSTER_PT`, sort each cluster by x and join,
    so super/subscript fragments recombine left to right."""
    ordered = sorted(found, key=lambda item: item[1])
    clusters: list[list[tuple[float, float, str]]] = []
    for item in ordered:
        if clusters and abs(item[1] - clusters[-1][0][1]) < LINE_CLUSTER_PT:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return [" ".join(t for _, _, t in sorted(cluster, key=lambda item: item[0])) for cluster in clusters]


def page_lines(page: fitz.Page) -> list[str]:
    """Visual lines of one page, as upstream reads them from ``mutool draw -F stext``."""
    return cluster_lines(_parse_stext_lines(page.get_text("xml")))


def break_positions(pages: Sequence[Sequence[str]]) -> list[int]:
    """Cumulative word count at the end of each page."""
    out: list[int] = []
    cumulative = 0
    for page in pages:
        cumulative += len(page)
        out.append(cumulative)
    return out


@dataclass(frozen=True)
class TextBoundary:
    ref_pages: int
    gen_pages: int
    max_break_drift: int
    total_words: int
    total_lines: int
    matching_lines: int

    def line_match_pct(self) -> float | None:
        """Share of compared lines that start and end on the same words; ``None`` when no
        line was comparable (upstream reports null, not 0)."""
        if self.total_lines <= 0:
            return None
        return self.matching_lines / self.total_lines


def boundary_from_extracts(
    ref_words: Sequence[Sequence[str]],
    gen_words: Sequence[Sequence[str]],
    ref_lines: Sequence[Sequence[str]],
    gen_lines: Sequence[Sequence[str]],
) -> TextBoundary:
    """The text-boundary comparison on already-extracted per-page words and lines."""
    common_pages = min(len(ref_words), len(gen_words))
    ref_breaks = break_positions(ref_words)
    gen_breaks = break_positions(gen_words)
    total_words = ref_breaks[-1] if ref_breaks else 0
    break_count = min(max(len(ref_breaks) - 1, 0), max(len(gen_breaks) - 1, 0))
    max_drift = 0
    for i in range(break_count):
        drift = gen_breaks[i] - ref_breaks[i]
        if abs(drift) > abs(max_drift):
            max_drift = drift

    total_lines = 0
    matching = 0
    for p in range(common_pages):
        r_lines = ref_lines[p]
        g_lines = gen_lines[p]
        max_count = max(len(r_lines), len(g_lines))
        min_count = min(len(r_lines), len(g_lines))
        if max_count > 0 and (max_count - min_count) / max_count > LINE_COUNT_SKIP:
            continue
        for line_idx in range(min_count):
            total_lines += 1
            if first_word(r_lines[line_idx]) == first_word(g_lines[line_idx]) and last_word(
                r_lines[line_idx],
            ) == last_word(g_lines[line_idx]):
                matching += 1

    return TextBoundary(
        ref_pages=len(ref_words),
        gen_pages=len(gen_words),
        max_break_drift=max_drift,
        total_words=total_words,
        total_lines=total_lines,
        matching_lines=matching,
    )


def text_boundary(ref_doc: fitz.Document, gen_doc: fitz.Document) -> TextBoundary:
    """Text-boundary comparison of two open documents."""
    ref_words = [page_words(p) for p in ref_doc]
    gen_words = [page_words(p) for p in gen_doc]
    common = min(len(ref_words), len(gen_words))
    ref_lines = [page_lines(ref_doc[i]) for i in range(common)]
    gen_lines = [page_lines(gen_doc[i]) for i in range(common)]
    return boundary_from_extracts(ref_words, gen_words, ref_lines, gen_lines)


def text_boundary_for_pdfs(oracle_pdf: Path, candidate_pdf: Path) -> TextBoundary:
    """Text-boundary comparison straight from the PDFs (text extraction, no raster)."""
    with fitz.open(oracle_pdf) as ref_doc, fitz.open(candidate_pdf) as gen_doc:
        return text_boundary(ref_doc, gen_doc)


# ------------------------------------------------------------------ pair ----


@dataclass(frozen=True)
class PairMetrics:
    """One oracle/candidate pair, in the shape upstream's ``page-metrics`` emits."""

    converted: bool
    jaccard: float | None = None
    text_boundary: float | None = None
    ref_pages: int = 0
    pages: int = 0
    scored_pages: int = 0
    max_break_drift: int = 0
    error: str | None = None

    def as_row(self) -> dict[str, object]:
        return {
            "converted": self.converted,
            "jaccard": self.jaccard,
            "text_boundary": self.text_boundary,
            "ref_pages": self.ref_pages,
            "pages": self.pages,
            "scored_pages": self.scored_pages,
            "max_break_drift": self.max_break_drift,
            "error": self.error,
        }


def score_pair(oracle_pdf: Path, candidate_pdf: Path, *, dpi: int = UPSTREAM_DPI) -> PairMetrics:
    """Rasterize both PDFs at ``dpi`` and compute Jaccard (page mean over the shared
    page count) and the text boundary. A missing file is reported, not raised."""
    if not Path(candidate_pdf).is_file():
        return PairMetrics(converted=False, error=ERROR_CANDIDATE_MISSING)
    if not Path(oracle_pdf).is_file():
        return PairMetrics(converted=False, error=ERROR_ORACLE_MISSING)
    with fitz.open(oracle_pdf) as ref_doc, fitz.open(candidate_pdf) as gen_doc:
        ref_pages = len(ref_doc)
        gen_pages = len(gen_doc)
        scored = min(ref_pages, gen_pages)
        ref_raster = _rasterize(ref_doc, dpi)
        gen_raster = _rasterize(gen_doc, dpi)
        tb = text_boundary(ref_doc, gen_doc)
    try:
        jaccards = [page_jaccard(ref_raster[i], gen_raster[i]) for i in range(scored)]
    except PageSizeMismatch as exc:
        return PairMetrics(
            converted=True, ref_pages=ref_pages, pages=gen_pages, scored_pages=scored,
            max_break_drift=tb.max_break_drift, error=str(exc),
        )
    return PairMetrics(
        converted=True,
        jaccard=(sum(jaccards) / scored) if scored else None,
        text_boundary=tb.line_match_pct(),
        ref_pages=ref_pages,
        pages=gen_pages,
        scored_pages=scored,
        max_break_drift=tb.max_break_drift,
    )
