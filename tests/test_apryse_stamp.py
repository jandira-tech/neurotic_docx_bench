"""Stamp-matched normalization for Apryse's demo watermark (#100).

The oracle gets the very paths Apryse's demo stamp painted on its own PDF, so the stamp
is on both sides of the comparison and cancels in the score.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pymupdf
import pytest

from neurotic_docx_bench import apryse_stamp

STAMP_FILL = (0.0, 0.6, 0.8)
A4 = pymupdf.paper_rect("a4")
LETTER = pymupdf.paper_rect("letter")


def _apryse_like(path: Path, rect: pymupdf.Rect = A4, pages: int = 1) -> pymupdf.Rect:
    """A PDF like Apryse's demo output: the stamp drawn first, behind a black text block."""
    doc = pymupdf.open()
    c = rect.width / 2, rect.height / 2
    stamp = pymupdf.Rect(c[0] - 60, c[1] - 30, c[0] + 60, c[1] + 30)
    for _ in range(pages):
        page = doc.new_page(width=rect.width, height=rect.height)
        shape = page.new_shape()
        shape.draw_rect(stamp)
        shape.finish(color=None, fill=STAMP_FILL, fill_opacity=0.102, even_odd=True)
        shape.commit()
        page.draw_rect(pymupdf.Rect(50, 50, 120, 70), color=None, fill=(0, 0, 0))
    doc.save(path)
    return stamp


def _oracle(path: Path, rect: pymupdf.Rect = A4, pages: int = 1) -> None:
    """A Word-like page: an opaque white page fill, a black bar through the centre."""
    doc = pymupdf.open()
    for _ in range(pages):
        page = doc.new_page(width=rect.width, height=rect.height)
        page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
        cy = rect.height / 2
        page.draw_rect(pymupdf.Rect(0, cy - 5, rect.width, cy + 5), color=None, fill=(0, 0, 0))
    doc.save(path)


def _px(pdf: Path, x: float, y: float, page: int = 0) -> tuple[int, int, int]:
    pix = pymupdf.open(pdf)[page].get_pixmap(dpi=72)
    return tuple(pix.pixel(int(x), int(y))[:3])


def test_finds_the_stamp_paths(tmp_path: Path) -> None:
    src = tmp_path / "a.pdf"
    _apryse_like(src)
    stamps = apryse_stamp.stamp_paths(src)
    assert len(stamps) == 1
    rect, paths = stamps[0]
    assert rect == A4
    assert paths and all(p["fill"] == pytest.approx(STAMP_FILL, abs=1e-3) for p in paths)


def test_no_stamp_is_an_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain.pdf"
    _oracle(plain)
    with pytest.raises(ValueError, match="no Apryse stamp"):
        apryse_stamp.stamp_paths(plain)


def test_white_takes_the_tint_black_stays_black(tmp_path: Path) -> None:
    src, oracle, out = tmp_path / "a.pdf", tmp_path / "o.pdf", tmp_path / "s.pdf"
    stamp = _apryse_like(src)
    _oracle(oracle)
    assert apryse_stamp.apply_stamp(oracle, src, out) == 1
    cx, cy = A4.width / 2, A4.height / 2
    # Over white: 0.102 of the stamp colour over white, as Apryse paints it.
    expected = tuple(round(255 * (1 - 0.102) + 255 * c * 0.102) for c in STAMP_FILL)
    got = _px(out, cx, stamp.y0 + 5)
    assert np.allclose(got, expected, atol=2), (got, expected)
    # Over black (the bar through the centre): Multiply leaves it black, as when the
    # stamp sits behind opaque ink.
    assert _px(out, cx, cy) == (0, 0, 0)
    # Outside the stamp nothing changes.
    assert _px(out, 10, 10) == (255, 255, 255)


def test_stamp_is_centred_on_another_page_size(tmp_path: Path) -> None:
    src, oracle, out = tmp_path / "a.pdf", tmp_path / "o.pdf", tmp_path / "s.pdf"
    _apryse_like(src, A4)
    _oracle(oracle, LETTER)
    apryse_stamp.apply_stamp(oracle, src, out)
    cx, cy = LETTER.width / 2, LETTER.height / 2
    assert _px(out, cx, cy - 20) != (255, 255, 255)  # inside the centred stamp
    assert _px(out, cx, cy - 45) == (255, 255, 255)  # just above it


def test_every_oracle_page_is_stamped(tmp_path: Path) -> None:
    """An oracle with more pages than Apryse's PDF takes the last stamp on its extra pages."""
    src, oracle, out = tmp_path / "a.pdf", tmp_path / "o.pdf", tmp_path / "s.pdf"
    _apryse_like(src, pages=1)
    _oracle(oracle, pages=3)
    assert apryse_stamp.apply_stamp(oracle, src, out) == 3
    for page in range(3):
        assert _px(out, A4.width / 2, A4.height / 2 - 20, page) != (255, 255, 255)


def test_the_source_pdf_is_untouched(tmp_path: Path) -> None:
    src, oracle, out = tmp_path / "a.pdf", tmp_path / "o.pdf", tmp_path / "s.pdf"
    _apryse_like(src)
    _oracle(oracle)
    before = oracle.read_bytes()
    apryse_stamp.apply_stamp(oracle, src, out)
    assert oracle.read_bytes() == before


# --- the redline lane: Word renders the stamp picture Apryse put in the DOCX header ---

STAMP_RGB = (63, 191, 239)
# A rotated placement written by hand (PDF user space), like Word's for the header picture.
WORD_CM = (186.8234, 290.9603, -53.69, 34.47, 239.39, 233.76)


def _stamp_png(alpha: int = 16, w: int = 120, h: int = 24, rgb: tuple[int, int, int] = STAMP_RGB) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGBA", (w, h), (*rgb, alpha)).save(buf, "PNG")
    return buf.getvalue()


def _with_image(page: pymupdf.Page, png: bytes, cm: tuple[float, ...] | None) -> None:
    """Insert ``png``; with ``cm``, rewrite its placement to that PDF matrix by hand."""
    page.insert_image(page.rect, stream=png, overlay=True, keep_proportion=False)
    if cm is None:
        return
    doc = page.parent
    cx = page.get_contents()[-1]
    name = next(t for t in doc.xref_stream(cx).split() if t.startswith(b"/"))
    doc.update_stream(cx, b"q %s cm %s Do Q" % (" ".join(f"{v:.6f}" for v in cm).encode(), name))


def _word_rendered_apryse(path: Path, *, extra_logo: bool = False) -> None:
    doc = pymupdf.open()
    page = doc.new_page(width=LETTER.width, height=LETTER.height)
    page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
    _with_image(page, _stamp_png(), WORD_CM)
    # Word's 1-pixel seam strips (drawn under a clip Word keeps and the copy would not):
    # one empty, one with a little ink. Neither is the stamp.
    _with_image(page, _stamp_png(alpha=0, h=1), (1, 0, 0, 1, 0, 0))
    _with_image(page, _stamp_png(alpha=16, w=119, h=1), (186.8, 290.9, -110.0, 70.6, 75.7, 267.8))
    if extra_logo:  # a document's own opaque picture is not the stamp
        page.insert_image(pymupdf.Rect(20, 20, 80, 50), stream=_stamp_png(alpha=255, rgb=(30, 60, 200)))
    doc.save(path)


def test_word_stamp_finds_only_the_translucent_blue_picture(tmp_path: Path) -> None:
    src = tmp_path / "w.pdf"
    _word_rendered_apryse(src, extra_logo=True)
    pages = apryse_stamp.word_stamp_images(src)
    assert len(pages) == 1
    rect, images = pages[0]
    assert rect == LETTER
    assert len(images) == 1


def test_word_stamp_absent_is_an_error(tmp_path: Path) -> None:
    plain = tmp_path / "plain.pdf"
    _oracle(plain, LETTER)
    with pytest.raises(ValueError, match="no Apryse stamp"):
        apryse_stamp.word_stamp_images(plain)


def test_word_stamp_lands_where_word_put_it(tmp_path: Path) -> None:
    src, oracle, out = tmp_path / "w.pdf", tmp_path / "o.pdf", tmp_path / "s.pdf"
    _word_rendered_apryse(src)
    _oracle(oracle, LETTER)
    assert apryse_stamp.apply_word_stamp(oracle, src, out) == 1
    want = next(i for i in pymupdf.open(src)[0].get_image_info() if i["width"] == 120 and i["height"] == 24)
    got = [i for i in pymupdf.open(out)[0].get_image_info() if i["width"] == 120]
    assert len(got) == 1
    assert got[0]["transform"] == pytest.approx(want["transform"], abs=1e-3)
    # The tint over white matches the source's own pixel there; black ink stays black.
    bbox = pymupdf.Rect(want["bbox"])
    # A point inside the stamp image (its unit square through its transform), clear of
    # the seam strip and of the black bar.
    centre = pymupdf.Point(0.5, 0.2) * pymupdf.Matrix(want["transform"])
    assert abs(centre.y - LETTER.height / 2) > 8
    assert _px(src, centre.x, centre.y) != (255, 255, 255)
    assert np.allclose(_px(out, centre.x, centre.y), _px(src, centre.x, centre.y), atol=2)
    assert _px(out, 10, 10) == (255, 255, 255)
    black = next(
        (x, LETTER.height / 2)
        for x in range(int(bbox.x0), int(bbox.x1))
        if _px(src, x, LETTER.height / 2) != (255, 255, 255)
    )
    assert _px(out, *black) == (0, 0, 0)


def test_word_stamp_on_every_page(tmp_path: Path) -> None:
    src, oracle, out = tmp_path / "w.pdf", tmp_path / "o.pdf", tmp_path / "s.pdf"
    _word_rendered_apryse(src)
    _oracle(oracle, LETTER, pages=3)
    assert apryse_stamp.apply_word_stamp(oracle, src, out) == 3
    for page in range(3):
        assert len([i for i in pymupdf.open(out)[page].get_image_info() if i["width"] == 120]) == 1
