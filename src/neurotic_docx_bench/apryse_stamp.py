"""Stamp-matched normalization for Apryse's demo watermark (#100).

A demo key makes Apryse paint its logo on every page it converts: a few even-odd filled
paths in RGB(0, 153, 204) at fill opacity 0.102, centred on the page, drawn before the
content (so they sit behind it). Scored against Word's clean PDF, that stamp costs Apryse
pixels Word never painted.

``apply_stamp`` copies those very paths from Apryse's PDF of a document onto Word's PDF of
the same document, page for page and centred, so the oracle carries the stamp too and it
cancels in the score. Word's PDFs paint an opaque white page first, which would hide
anything drawn behind it, so the stamp goes on top with a Multiply blend: over white that
gives Apryse's tint, over black ink it leaves black, which is what "behind the content"
looks like. The raw score stays the record; this one is reported beside it, labelled.
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

STAMP_FILL = (0.0, 0.6, 0.8)
STAMP_OPACITY = 0.102
_TOL = 0.01


def _is_stamp(path: dict) -> bool:
    fill = path.get("fill")
    opacity = path.get("fill_opacity")
    return (
        fill is not None
        and opacity is not None
        and abs(opacity - STAMP_OPACITY) < _TOL
        and all(abs(a - b) < _TOL for a, b in zip(fill, STAMP_FILL, strict=True))
        and path.get("color") is None
    )


def stamp_paths(apryse_pdf: Path) -> list[tuple[pymupdf.Rect, list[dict]]]:
    """Per page of ``apryse_pdf``: (page rect, the stamp's paths). Raises ValueError when no
    page carries the stamp (a licensed render, or not Apryse's output)."""
    out: list[tuple[pymupdf.Rect, list[dict]]] = []
    with pymupdf.open(apryse_pdf) as doc:
        for page in doc:
            out.append((pymupdf.Rect(page.rect), [p for p in page.get_drawings() if _is_stamp(p)]))
    if not any(paths for _, paths in out):
        raise ValueError(f"no Apryse stamp in {apryse_pdf}")
    return out


def _draw(shape: pymupdf.Shape, path: dict, dx: float, dy: float) -> None:
    move = pymupdf.Point(dx, dy)
    for item in path["items"]:
        kind = item[0]
        if kind == "l":
            shape.draw_line(item[1] + move, item[2] + move)
        elif kind == "c":
            shape.draw_bezier(item[1] + move, item[2] + move, item[3] + move, item[4] + move)
        elif kind == "re":
            shape.draw_rect(pymupdf.Rect(item[1]) + (dx, dy, dx, dy))
        elif kind == "qu":
            shape.draw_quad(pymupdf.Quad(item[1]) * pymupdf.Matrix(1, 0, 0, 1, dx, dy))
        else:
            raise ValueError(f"unexpected path item {kind!r} in the Apryse stamp")
    shape.finish(
        color=None,
        fill=path["fill"],
        fill_opacity=path["fill_opacity"],
        even_odd=bool(path.get("even_odd")),
        closePath=bool(path.get("closePath", True)),
    )


def _ext_gstates(doc: pymupdf.Document, page: pymupdf.Page) -> tuple[int, str]:
    """(xref, key path) under which this page's ExtGState dictionary lives."""
    kind, value = doc.xref_get_key(page.xref, "Resources")
    if kind == "xref":
        res_xref = int(value.split()[0])
        kind2, value2 = doc.xref_get_key(res_xref, "ExtGState")
        if kind2 == "xref":
            return int(value2.split()[0]), ""
        return res_xref, "ExtGState/"
    kind2, value2 = doc.xref_get_key(page.xref, "Resources/ExtGState")
    if kind2 == "xref":
        return int(value2.split()[0]), ""
    return page.xref, "Resources/ExtGState/"


def _gstate_names(doc: pymupdf.Document, page: pymupdf.Page) -> set[str]:
    xref, prefix = _ext_gstates(doc, page)
    key = prefix.rstrip("/")
    if key:
        return set(_dict_keys(doc, xref, key))
    return set(doc.xref_get_keys(xref))


def _dict_keys(doc: pymupdf.Document, xref: int, key: str) -> list[str]:
    kind, value = doc.xref_get_key(xref, key)
    if kind != "dict":
        return []
    # value looks like "<</fitz1 <</ca .102>>/GS0 5 0 R>>": take the top-level names.
    names, depth, i = [], 0, 0
    while i < len(value):
        if value.startswith("<<", i):
            depth += 1
            i += 2
            continue
        if value.startswith(">>", i):
            depth -= 1
            i += 2
            continue
        if value[i] == "/" and depth == 1:
            j = i + 1
            while j < len(value) and value[j] not in " /<>[]()\n\r\t":
                j += 1
            names.append(value[i + 1 : j])
            # skip the value that follows the name
            i = j
            while i < len(value) and value[i] in " \n\r\t":
                i += 1
            if value.startswith("<<", i):
                d, i = 1, i + 2
                while i < len(value) and d:
                    if value.startswith("<<", i):
                        d, i = d + 1, i + 2
                    elif value.startswith(">>", i):
                        d, i = d - 1, i + 2
                    else:
                        i += 1
            elif value[i : i + 1] == "/":
                j = i + 1
                while j < len(value) and value[j] not in " /<>[]()\n\r\t":
                    j += 1
                i = j
            else:  # "5 0 R", a number
                while i < len(value) and value[i] not in "/>":
                    i += 1
            continue
        i += 1
    return names


def _multiply(doc: pymupdf.Document, page: pymupdf.Page, names: set[str]) -> None:
    """Add ``/BM /Multiply`` to the ExtGStates ``names`` of ``page``."""
    xref, prefix = _ext_gstates(doc, page)
    for name in names:
        kind, value = doc.xref_get_key(xref, f"{prefix}{name}")
        if kind == "xref":
            doc.xref_set_key(int(value.split()[0]), "BM", "/Multiply")
        else:
            doc.xref_set_key(xref, f"{prefix}{name}/BM", "/Multiply")


def apply_stamp(src_pdf: Path, apryse_pdf: Path, dst_pdf: Path) -> int:
    """Write ``src_pdf`` with Apryse's stamp from ``apryse_pdf`` on every page to
    ``dst_pdf``. Page i takes the stamp of Apryse's page i (its last stamped page when
    Apryse has fewer), shifted so it keeps its place relative to the page centre.
    Returns the number of pages stamped."""
    stamps = stamp_paths(apryse_pdf)
    stamped = 0
    last: tuple[pymupdf.Rect, list[dict]] | None = None
    with pymupdf.open(src_pdf) as doc:
        for i, page in enumerate(doc):
            if i < len(stamps) and stamps[i][1]:
                last = stamps[i]
            if last is None:
                last = next(s for s in stamps if s[1])
            rect, paths = last
            dx = (page.rect.width - rect.width) / 2
            dy = (page.rect.height - rect.height) / 2
            before = _gstate_names(doc, page)
            shape = page.new_shape()
            for path in paths:
                _draw(shape, path, dx, dy)
            shape.commit(overlay=True)
            _multiply(doc, page, _gstate_names(doc, page) - before)
            stamped += 1
        doc.save(dst_pdf, garbage=1, deflate=True)
    return stamped



# --- the redline lane ---------------------------------------------------------------
# Apryse's demo puts the stamp in the redline DOCX as a header picture (a translucent
# blue PNG, peak alpha 16/255, anchored behind the text). Word renders it as an image
# XObject with an alpha mask (plus empty 1-pixel strips) under a rotated matrix. Those
# images, with their matrices, go onto Word's own compare PDF.

_MAX_STAMP_ALPHA = 32
_MIN_STAMP_SIDE = 4
_MUL_GS = "ndbStampMul"


def _stamp_rgba(doc: pymupdf.Document, xref: int) -> pymupdf.Pixmap | None:
    """The image as an RGBA pixmap when it looks like the stamp, else None."""
    info = doc.extract_image(xref)
    # Word also emits 1-pixel seam strips of the picture, drawn under a clip that a copy of
    # the image alone would not carry (it smears them across the page); they are not the stamp.
    if min(info.get("width", 0), info.get("height", 0)) < _MIN_STAMP_SIDE:
        return None
    smask = info.get("smask") or 0
    if not smask:
        return None
    base = pymupdf.Pixmap(doc, xref)
    if base.n != 3 or base.alpha:
        base = pymupdf.Pixmap(pymupdf.csRGB, base)
    mask = pymupdf.Pixmap(doc, smask)
    if mask.width != base.width or mask.height != base.height:
        return None
    alpha = mask.samples
    peak = max(alpha) if alpha else 0
    if peak == 0 or peak > _MAX_STAMP_ALPHA:
        return None
    rgb = base.samples
    inked = [i for i, a in enumerate(alpha) if a]
    blue = sum(1 for i in inked if rgb[3 * i + 2] > 1.5 * rgb[3 * i] + 1 and rgb[3 * i + 2] >= rgb[3 * i + 1])
    if blue * 2 < len(inked):
        return None
    return pymupdf.Pixmap(base, mask)


def word_stamp_images(word_pdf: Path) -> list[tuple[pymupdf.Rect, list[tuple[bytes, pymupdf.Matrix]]]]:
    """Per page of Word's render of an Apryse redline: (page rect, [(RGBA PNG, PDF matrix)])
    for each stamp image. The matrix is the image's PDF ``cm`` in that page's user space.
    Raises ValueError when no page carries the stamp."""
    out: list[tuple[pymupdf.Rect, list[tuple[bytes, pymupdf.Matrix]]]] = []
    with pymupdf.open(word_pdf) as doc:
        for page in doc:
            found: list[tuple[bytes, pymupdf.Matrix]] = []
            for info in page.get_image_info(xrefs=True):
                xref = info.get("xref") or 0
                if not xref:
                    continue
                rgba = _stamp_rgba(doc, xref)
                if rgba is None:
                    continue
                cm = pymupdf.Matrix(1, 0, 0, -1, 0, 1) * pymupdf.Matrix(info["transform"]) * ~page.transformation_matrix
                found.append((rgba.tobytes("png"), cm))
            out.append((pymupdf.Rect(page.rect), found))
    if not any(images for _, images in out):
        raise ValueError(f"no Apryse stamp in {word_pdf}")
    return out


def _add_multiply_gstate(doc: pymupdf.Document, page: pymupdf.Page) -> None:
    xref, prefix = _ext_gstates(doc, page)
    doc.xref_set_key(xref, f"{prefix}{_MUL_GS}", "<</Type/ExtGState/BM/Multiply>>")


def apply_word_stamp(src_pdf: Path, apryse_word_pdf: Path, dst_pdf: Path) -> int:
    """Write ``src_pdf`` with the stamp images of ``apryse_word_pdf`` on every page to
    ``dst_pdf``, each under its own matrix shifted to keep its place relative to the page
    centre, drawn on top with a Multiply blend (the stamp sits behind Word's ink). Page i
    takes the stamp of page i, or of the last stamped page. Returns pages stamped."""
    stamps = word_stamp_images(apryse_word_pdf)
    stamped = 0
    last = None
    with pymupdf.open(src_pdf) as doc:
        for i, page in enumerate(doc):
            if i < len(stamps) and stamps[i][1]:
                last = stamps[i]
            if last is None:
                last = next(s for s in stamps if s[1])
            rect, images = last
            dx = (page.rect.width - rect.width) / 2
            dy = (page.rect.height - rect.height) / 2  # y up in PDF space: centre shift is symmetric
            # Registered first: each insert_image re-parses the page's streams, the ones
            # already rewritten to use this state included.
            _add_multiply_gstate(doc, page)
            for png, cm in images:
                page.insert_image(page.rect, stream=png, overlay=True, keep_proportion=False)
                cx = page.get_contents()[-1]
                name = next(t for t in doc.xref_stream(cx).split() if t.startswith(b"/"))
                m = cm * pymupdf.Matrix(1, 0, 0, 1, dx, dy)
                doc.update_stream(
                    cx,
                    b"q /%s gs %s cm %s Do Q" % (
                        _MUL_GS.encode(), " ".join(f"{v:.6f}" for v in m).encode(), name,
                    ),
                )
            stamped += 1
        doc.save(dst_pdf, garbage=1, deflate=True)
    return stamped
