"""Parity guard: the lifted scoring core must produce numbers byte-identical to the
original ``.old/compare`` harness it was lifted from.

The scoring modules were copied verbatim (only absolute→relative imports and a soft
logo-path lookup changed — none of which touch ``score.py``). This test loads the
ORIGINAL ``.old/compare/score.py`` as a standalone module and asserts that, on the same
rasterized page inputs, ``neurotic_docx_bench.score.score_document`` returns an identical
result dict, once the two deviations recorded in AGENTS.md are applied to the reference.
It is the anchor that keeps every later bench score comparable.

Skips cleanly when ``.old/compare`` is absent (e.g. in CI, where only the package ships).
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from neurotic_docx_bench import raster
from neurotic_docx_bench import score as new_score

REPO_ROOT = Path(__file__).resolve().parents[1]
# Committed frozen copy of the original scoring core, so parity is verified EVEN in CI /
# fresh clones (the source `.old/compare/` is git-ignored and absent there).
OLD_SCORE_PATH = REPO_ROOT / "tests" / "reference" / "old_compare_score.py"


def _oracle_pdfs() -> list[Path]:
    """LibreOffice's renders of the word_based Word redlines, as filed in corpus/libreoffice."""
    from helpers import MANIFEST, word_based_pairs

    if not MANIFEST.is_file():
        return []
    return sorted(p.libreoffice_pdf for p in word_based_pairs() if p.libreoffice_pdf and p.libreoffice_pdf.is_file())


def _load_old_score():
    """Import the frozen reference score.py as a standalone module (it has no internal
    imports, so it loads without the rest of the .old package).
    """
    spec = importlib.util.spec_from_file_location("_old_compare_score", OLD_SCORE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclasses can resolve `from __future__ import annotations`
    # string annotations via sys.modules[cls.__module__] (Python 3.14 requirement).
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assert_equal(a, b, path: str = "") -> None:
    """Recursively assert two score dicts are numerically identical."""
    if isinstance(a, dict):
        assert isinstance(b, dict), f"type mismatch at {path}: {type(a)} vs {type(b)}"
        assert a.keys() == b.keys(), f"key mismatch at {path}: {a.keys()} vs {b.keys()}"
        for k in a:
            _assert_equal(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b), f"length mismatch at {path}: {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_equal(x, y, f"{path}[{i}]")
    elif isinstance(a, float):
        assert isinstance(b, (int, float)), f"type mismatch at {path}"
        if math.isnan(a):
            assert math.isnan(b), f"nan mismatch at {path}: {a} vs {b}"
        else:
            assert math.isclose(a, b, rel_tol=0.0, abs_tol=1e-9), (
                f"value mismatch at {path}: {a!r} vs {b!r}"
            )
    else:
        assert a == b, f"value mismatch at {path}: {a!r} vs {b!r}"


@pytest.fixture(scope="module")
def two_pdf_page_sets(tmp_path_factory) -> tuple[list[Path], list[Path]]:
    """Rasterize the first page of two different oracle PDFs so the full metric pipeline
    (alignment / ink / edge / colour / blob) actually runs, not the identical-image path.
    """
    pdfs = _oracle_pdfs()
    if len(pdfs) < 2:
        pytest.skip("need at least two oracle PDFs for a parity comparison")

    out = tmp_path_factory.mktemp("parity_pages")
    word_dir = out / "word"
    cand_dir = out / "cand"
    word_dir.mkdir()
    cand_dir.mkdir()
    raster.rasterize_pdf(pdfs[0], word_dir, dpi=raster.DEFAULT_DPI)
    raster.rasterize_pdf(pdfs[1], cand_dir, dpi=raster.DEFAULT_DPI)
    word_pages = sorted(word_dir.glob("page_*.png"))[:1]
    cand_pages = sorted(cand_dir.glob("page_*.png"))[:1]
    assert word_pages and cand_pages, "rasterization produced no pages"
    return word_pages, cand_pages


# The two recorded deviations from the lifted core (0de6361bf, 2026-10-03, bb35ae41ba):
# the ink threshold comes from the REFERENCE page for both sides, capped at 0.9 (below
# Word's 0.949 markup pane), and the alignment never lowers a score (the unshifted
# candidate is scored too, the better of the two stands). Nothing else may drift.
INK_THRESHOLD_CAP = 0.9


def _with_recorded_deviations(old):
    """The frozen reference with exactly the two recorded deviations applied, spelled
    out here independently of score.py so the test cannot inherit a later drift."""
    page: dict = {}
    score_page, align_images, compute_metrics = old._score_page, old._align_images, old._compute_metrics

    def ink_mask(gray, min_size):
        ink = gray < page["thr"]
        return old.morphology.remove_small_objects(ink, max_size=min_size)

    def align(ref_gray, mov_gray, mov_rgb, config):
        aligned = align_images(ref_gray, mov_gray, mov_rgb, config)
        word_rgb = page["word_rgb"]
        unshifted = compute_metrics(word_rgb, mov_rgb, config)
        return mov_rgb if unshifted["score"] > compute_metrics(word_rgb, aligned, config)["score"] else aligned

    def scored_page(word_rgb, sd_rgb, config):
        gray = old.color.rgb2gray(word_rgb)
        try:
            thr = old.filters.threshold_otsu(gray)
        except ValueError:
            thr = INK_THRESHOLD_CAP
        page.update(thr=float(min(thr, INK_THRESHOLD_CAP)), word_rgb=word_rgb)
        return score_page(word_rgb, sd_rgb, config)

    old._ink_mask, old._align_images, old._score_page = ink_mask, align, scored_page
    return old


def test_score_document_matches_old_compare(two_pdf_page_sets):
    word_pages, cand_pages = two_pdf_page_sets
    old = _with_recorded_deviations(_load_old_score())

    old_result = old.score_document(word_pages, cand_pages)
    new_result = new_score.score_document(word_pages, cand_pages)

    _assert_equal(new_result, old_result)


def test_score_document_shape_and_range(two_pdf_page_sets):
    """The packaged scorer returns the documented dict shape with an in-range score."""
    word_pages, cand_pages = two_pdf_page_sets
    result = new_score.score_document(word_pages, cand_pages)

    for key in ("overall_score", "page_count", "pages", "config"):
        assert key in result, f"missing key {key!r} in score_document result"
    overall_score = result["overall_score"]
    assert isinstance(overall_score, float)
    assert 0.0 <= overall_score <= 100.0
    page_count = result["page_count"]
    pages = result["pages"]
    assert isinstance(page_count, int)
    assert isinstance(pages, list)
    assert page_count == len(pages) == 1
    page = pages[0]
    for metric in ("ssim_full", "ssim_small", "ink_f1", "edge_iou", "color_sim"):
        assert metric in page, f"missing per-page metric {metric!r}"


def test_identical_pages_score_100(tmp_path):
    """Scoring a page against itself yields a perfect score (sanity of the pipeline)."""
    pdfs = _oracle_pdfs()
    if not pdfs:
        pytest.skip("no oracle PDFs")
    d = tmp_path / "p"
    d.mkdir()
    raster.rasterize_pdf(pdfs[0], d, dpi=raster.DEFAULT_DPI)
    pages = sorted(d.glob("page_*.png"))[:1]
    result = new_score.score_document(pages, pages)
    assert result["overall_score"] == pytest.approx(100.0, abs=1e-6)


def _synthetic_pages(tmp_path: Path, case: str) -> tuple[list[Path], list[Path]]:
    """Pages built to reach each deviation: a page that is mostly Word's 0.949 pane
    (Otsu lands at 0.949, so only the 0.9 cap keeps the pane out of the ink) and a page
    whose lower fifth sits 1px right (phase correlation shifts the exact rest)."""
    from PIL import Image

    if case == "pane":
        ref = np.ones((400, 300, 3), np.float32)
        ref[40:360, 120:280] = 0.949
        cand = np.ones_like(ref)
        cand[40:360, 150:280] = 0.949
    else:
        rng = np.random.default_rng(3)
        ref = np.ones((300, 240, 3), np.float32)
        for _ in range(60):
            y, x = rng.integers(5, 290), rng.integers(5, 200)
            ref[y : y + 4, x : x + rng.integers(6, 30)] = 0
        cand = ref.copy()
        cand[240:] = np.roll(ref, 1, axis=1)[240:]
    out = []
    for name, page in (("word", ref), ("cand", cand)):
        path = tmp_path / f"{case}_{name}.png"
        Image.fromarray((page * 255).round().astype(np.uint8)).save(path)
        out.append([path])
    return out[0], out[1]


@pytest.mark.parametrize("case", ["pane", "partial_shift"])
def test_each_recorded_deviation_is_reached_and_matched(tmp_path, case):
    """Each synthetic page moves the frozen core's score, and the packaged scorer equals
    the reference with exactly the recorded deviations applied."""
    word_pages, cand_pages = _synthetic_pages(tmp_path, case)
    plain = _load_old_score().score_document(word_pages, cand_pages)
    deviated = _with_recorded_deviations(_load_old_score()).score_document(word_pages, cand_pages)

    assert plain["overall_score"] != pytest.approx(deviated["overall_score"], abs=1e-6)
    _assert_equal(new_score.score_document(word_pages, cand_pages), deviated)
