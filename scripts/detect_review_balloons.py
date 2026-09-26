#!/usr/bin/env python3
"""Find PDFs where Word shrank the page and drew review balloons on the right.

Inline tracked changes stay inside the text and the page stays full width.
Balloon layout does both of the following, and a page has to show both:

- the body stops at a low-ink gutter between 55% and 78% of the page width
- the right-hand rail reaches the outer margin and holds at least one boxed
  balloon (a rectangle outline with a mostly empty interior)

The numbers come from the local pair
``with_balloons_do_not_use.pdf`` / ``without_balloons_do_not_use.pdf``
rendered at 72 dpi. A table column is not a rail: its horizontal rules run
back into the body, and a balloon's border stops at the balloon.

Usage:
    uv run python scripts/detect_review_balloons.py --src ./pdfs
    uv run python scripts/detect_review_balloons.py --src ./pdfs \\
        --a ./folder_a --b ./folder_b --out report.tsv

With ``--a`` and ``--b``, each PDF named ``<base>__vs__<revision>`` is also
checked: do the words of those two source documents occur in the PDF text?
That check is fuzzy. Word glues neighbouring words and rewrites punctuation,
so a word counts when it shows up inside the PDF's text, not only as its own
token. The two files are scored separately and are not averaged.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import fitz
import numpy as np
import typer
from scipy import ndimage

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from redline_identity import body_text

app = typer.Typer(add_completion=False, help=__doc__)

# Paper is not only pure white: Word's PDF antialiasing leaves light gray.
_PAPER = 242
# Gutter search window, as a fraction of page width. Measured split on the
# balloon example is 0.653. The window covers a rail of about 2.5–3.5 inches
# on letter and A4.
_GUTTER_LO = 0.55
_GUTTER_HI = 0.78
_GAP_MAX = 0.025
_LEFT_MIN = 0.010
_RIGHT_MIN = 0.015
_OUTER_MIN = 0.008
# A balloon box, as fractions of the page. The example boxes were ~0.32 wide
# with perimeter ink 0.56–0.63 and interior ink 0.04–0.15.
_BOX_MIN_WIDTH = 0.12
_BOX_MIN_HEIGHT = 0.025
_BOX_MAX_HEIGHT = 0.70
_PERI_MIN = 0.45
_INTERIOR_MAX = 0.35
# A named source matches the PDF when this fraction of its words (length >= 4)
# occur in the PDF text. Measured on this batch: a real pair stays at or above
# 0.76 and a swapped file stays at or below 0.36.
_NAME_MIN = 0.60
_TOKEN_MIN_LEN = 4
# Common words cannot tell a redline from a PDF of one file alone: two versions
# of a form share nearly every word, and Word's PDF of the revision alone scored
# 0.76 against the base (messed_fixtures P3). So each side must also show its
# distinctive words, the ones the other file lacks (a redline keeps deletions
# visible). 2026-09-25, 385 English redline PDFs: real pairs >= 0.53; a lone PDF
# of the revision 0.00; a PDF missing the revision's inserted table 0.13. The
# check needs a few distinctive words to mean anything.
_DISTINCT_MIN = 0.40
_DISTINCT_MIN_WORDS = 5
# docx text runs a word into the next cell's figure ("catchment0"); the PDF
# keeps them apart. Splitting letters from digits makes both sides agree.
_LETTER_DIGIT = re.compile(r"(?<=[^\W\d])(?=\d)|(?<=\d)(?=[^\W\d])")
# A table cell's top or bottom rule keeps going left through the body.
# A balloon's own border stops at the rail. Measured reach on the balloon
# example is 0; on a landscape form it is about half the page.
_BODY_REACH_MAX = 0.12


@dataclass(frozen=True, slots=True)
class BalloonLayout:
    """One page whose body was narrowed and whose right rail holds balloons."""

    gutter_fraction: float
    boxes: int


def _ink(rgb: np.ndarray) -> np.ndarray:
    return np.any(rgb[:, :, :3] < _PAPER, axis=2)


def _gutter(ink: np.ndarray) -> int | None:
    """X of the emptiest gutter that splits a body from an outer right rail."""
    height, width = ink.shape
    density = ink.mean(axis=0)
    smooth = np.convolve(density, np.ones(5) / 5, mode="same")
    best: tuple[float, int] | None = None
    left_origin = int(width * 0.08)
    for x in range(int(width * _GUTTER_LO), int(width * _GUTTER_HI)):
        gap = float(smooth[max(0, x - 2) : x + 3].mean())
        if gap > _GAP_MAX:
            continue
        left = smooth[left_origin : max(left_origin + 1, x - 3)]
        right = smooth[min(width - 1, x + 4) : int(width * 0.98)]
        outer = smooth[int(width * 0.90) : int(width * 0.985)]
        if left.size == 0 or right.size == 0 or outer.size == 0:
            continue
        if float(left.mean()) < _LEFT_MIN:
            continue
        if float(right.mean()) < _RIGHT_MIN or float(outer.mean()) < _OUTER_MIN:
            continue
        if best is None or gap < best[0]:
            best = (gap, x)
    return None if best is None else best[1]


def _border_runs_into_body(ink: np.ndarray, y: int, gutter_x: int) -> bool:
    """True when the horizontal rule at ``y`` continues left across the gutter.

    Table rules do this. A balloon border ends at the balloon.
    """
    width = ink.shape[1]
    row = ink[y]
    reach = 0
    x = gutter_x
    while x >= 0:
        if row[max(0, x - 1) : x + 1].any():
            reach += 1
            x -= 1
            continue
        if x >= 4 and row[x - 4 : x].any():
            reach += 1
            x -= 1
            continue
        break
    return reach > width * _BODY_REACH_MAX


def _balloon_boxes(ink: np.ndarray, gutter_x: int) -> int:
    """Outlined rectangles in the rail to the right of ``gutter_x``.

    A rectangle whose top or bottom rule runs back into the body is a table
    cell in a column, not a review balloon.
    """
    height, width = ink.shape
    rail = ink[:, min(width - 1, gutter_x + 6) : int(width * 0.99)]
    if rail.size == 0 or min(rail.shape) < 8:
        return 0
    labels, count = ndimage.label(rail)
    boxes = 0
    for label in range(1, count + 1):
        ys, xs = np.nonzero(labels == label)
        if ys.size < 40:
            continue
        y0, y1 = int(ys.min()), int(ys.max())
        x0, x1 = int(xs.min()), int(xs.max())
        box_h, box_w = y1 - y0 + 1, x1 - x0 + 1
        if box_w < width * _BOX_MIN_WIDTH:
            continue
        if box_h < height * _BOX_MIN_HEIGHT or box_h > height * _BOX_MAX_HEIGHT:
            continue
        component = labels[y0 : y1 + 1, x0 : x1 + 1] == label
        if component.shape[0] < 8 or component.shape[1] < 8:
            continue
        perimeter = np.zeros(component.shape, dtype=bool)
        perimeter[:2, :] = True
        perimeter[-2:, :] = True
        perimeter[:, :2] = True
        perimeter[:, -2:] = True
        interior = np.zeros(component.shape, dtype=bool)
        interior[3:-3, 3:-3] = True
        if not interior.any():
            continue
        if float(component[perimeter].mean()) < _PERI_MIN:
            continue
        if float(component[interior].mean()) > _INTERIOR_MAX:
            continue
        if _border_runs_into_body(ink, y0, gutter_x) or _border_runs_into_body(ink, y1, gutter_x):
            continue
        boxes += 1
    return boxes


def page_balloon_layout(rgb: np.ndarray) -> BalloonLayout | None:
    """Return the balloon geometry of one RGB page, or None.

    ``rgb`` is a ``(height, width, 3+)`` array at about 72 dpi. The page
    matches only when the body is reduced and the right rail contains a
    balloon box. Either half on its own is not enough.
    """
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError("page array must be H×W×3 RGB")
    height, width = rgb.shape[:2]
    if height < 80 or width < 80:
        return None
    ink = _ink(rgb)
    gutter_x = _gutter(ink)
    if gutter_x is None:
        return None
    boxes = _balloon_boxes(ink, gutter_x)
    if boxes < 1:
        return None
    return BalloonLayout(gutter_fraction=gutter_x / width, boxes=boxes)


def _fuzzy_norm(text: str) -> str:
    text = text.casefold().replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def fuzzy_recall(source: str, found: str) -> float:
    """Fraction of ``source``'s words that occur somewhere in ``found``.

    Word's PDF text glues a deletion to the next word and rewrites
    punctuation, so a word counts when it appears inside the PDF text, not
    only as a token of its own. Order does not matter: a redline interleaves
    the two files.
    """
    words = [token for token in _fuzzy_norm(source).split() if len(token) >= _TOKEN_MIN_LEN]
    haystack = _fuzzy_norm(found)
    if not words:
        if not haystack and not _fuzzy_norm(source):
            return 1.0
        whole = _fuzzy_norm(source)
        return 1.0 if whole and whole in haystack else 0.0
    return sum(1 for token in words if token in haystack) / len(words)


def _split_words(text: str) -> str:
    return _LETTER_DIGIT.sub(" ", _fuzzy_norm(text))


def distinct_recall(source: str, other: str, found: str) -> float | None:
    """Fraction of the words only ``source`` has (not ``other``) that occur in ``found``.

    ``None`` when ``source`` has too few such words to judge.
    """
    other_words = set(_split_words(other).split())
    words = {
        token
        for token in _split_words(source).split()
        if len(token) >= _TOKEN_MIN_LEN and token not in other_words
    }
    if len(words) < _DISTINCT_MIN_WORDS:
        return None
    haystack = _split_words(found)
    return sum(1 for token in words if token in haystack) / len(words)


@dataclass(frozen=True, slots=True)
class NameMatch:
    """Whether one PDF contains the two files its name claims."""

    ok: bool
    score_base: float
    score_revision: float
    reason: str


def names_match_text(
    pdf_text: str,
    base_text: str,
    revision_text: str,
    *,
    minimum: float = _NAME_MIN,
) -> NameMatch:
    """True only when both sources fuzzy-match the PDF. The scores are not averaged.

    Each side must also show its distinctive words (``distinct_recall``); a
    side's reported score is the lower of the two recalls.
    """
    missing: list[str] = []
    scores: list[float] = []
    for side, source, other in (
        ("base", base_text, revision_text),
        ("revision", revision_text, base_text),
    ):
        score = fuzzy_recall(source, pdf_text)
        distinct = distinct_recall(source, other, pdf_text)
        if score < minimum:
            missing.append(f"{side} {score:.0%}")
        elif distinct is not None and distinct < _DISTINCT_MIN:
            missing.append(f"{side}'s own words {distinct:.0%}")
        scores.append(score if distinct is None else min(score, distinct))
    score_base, score_revision = scores
    if not missing:
        return NameMatch(True, score_base, score_revision, "")
    return NameMatch(
        False,
        score_base,
        score_revision,
        "pdf is missing " + " and ".join(missing) + " of that file; the two sides are not averaged",
    )


def stem_pair(path: Path) -> tuple[str, str] | None:
    """``<base>__vs__<revision>`` from a PDF name. A staged ``00012__`` prefix is stripped."""
    stem = path.stem
    if "__vs__" not in stem:
        return None
    base, revision = stem.split("__vs__", 1)
    if re.fullmatch(r"\d{5}__.+", base):
        base = base.split("__", 1)[1]
    if not base or not revision:
        return None
    return base, revision


def read_pdf(path: Path, *, zoom: float = 1.0) -> tuple[list[int], str]:
    """Balloon pages (1-based) and the PDF's extracted text, from one open."""
    hits: list[int] = []
    parts: list[str] = []
    with fitz.open(path) as doc:
        for index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if page_balloon_layout(rgb) is not None:
                hits.append(index)
            parts.append(page.get_text())
    return hits, "\n".join(parts)


def pdf_balloon_pages(path: Path, *, zoom: float = 1.0) -> list[int]:
    """1-based page numbers of ``path`` that show a right-hand balloon rail."""
    pages, _ = read_pdf(path, zoom=zoom)
    return pages


def iter_pdfs(folder: Path) -> list[Path]:
    """Real PDFs directly in ``folder``, Word lock files excluded."""
    return sorted(
        p
        for p in folder.glob("*.pdf")
        if p.is_file() and not p.name.startswith(("~$", ".~"))
    )


def _source_text(folder: Path, stem: str, cache: dict[Path, str]) -> str | None:
    path = folder / f"{stem}.docx"
    if path in cache:
        return cache[path]
    if not path.is_file():
        return None
    text = body_text(path, "plain")
    cache[path] = text
    return text


@app.command()
def main(
    src: Annotated[Path, typer.Option("--src", help="Folder of PDFs to scan.")],
    out: Annotated[
        Path | None,
        typer.Option("--out", help="TSV of every file. Default: stdout only."),
    ] = None,
    folder_a: Annotated[
        Path | None,
        typer.Option("--a", help="Folder of base documents named by the PDF."),
    ] = None,
    folder_b: Annotated[
        Path | None,
        typer.Option("--b", help="Folder of revision documents named by the PDF."),
    ] = None,
) -> None:
    """Scan for balloon rails, and for whether each PDF contains its named sources."""
    if not src.is_dir():
        typer.echo(f"not a folder: {src}", err=True)
        raise typer.Exit(2)
    if (folder_a is None) != (folder_b is None):
        typer.echo("pass both --a and --b, or neither", err=True)
        raise typer.Exit(2)
    check_names = folder_a is not None and folder_b is not None
    pdfs = iter_pdfs(src)
    cache: dict[Path, str] = {}
    rows: list[str] = []
    balloon_files = 0
    unreadable = 0
    name_yes = 0
    name_no = 0
    name_skipped = 0
    for pdf in pdfs:
        try:
            pages, pdf_text = read_pdf(pdf)
        except Exception as exc:
            unreadable += 1
            rows.append(f"{pdf.name}\tUNREADABLE\t\t{exc}")
            continue
        balloon_cell = ",".join(str(n) for n in pages) if pages else "-"
        if pages:
            balloon_files += 1
        name_cell = ""
        if check_names:
            pair = stem_pair(pdf)
            if pair is None:
                name_cell = "n/a"
                name_skipped += 1
            else:
                base_stem, revision_stem = pair
                assert folder_a is not None and folder_b is not None
                try:
                    base_text = _source_text(folder_a, base_stem, cache)
                    revision_text = _source_text(folder_b, revision_stem, cache)
                except Exception as exc:
                    name_cell = f"no\t\tunreadable source: {exc}"
                    name_no += 1
                    rows.append(f"{pdf.name}\t{balloon_cell}\t{name_cell}")
                    continue
                if base_text is None or revision_text is None:
                    missing = "base" if base_text is None else "revision"
                    name_cell = f"no\t\tmissing {missing} file"
                    name_no += 1
                else:
                    verdict = names_match_text(pdf_text, base_text, revision_text)
                    answer = "yes" if verdict.ok else "no"
                    name_cell = (
                        f"{answer}\t{verdict.score_base:.3f}\t{verdict.score_revision:.3f}"
                    )
                    if verdict.ok:
                        name_yes += 1
                    else:
                        name_no += 1
        rows.append(f"{pdf.name}\t{balloon_cell}\t{name_cell}".rstrip("\t"))
    header = "file\tballoons\tnames match original content?\tscore_base\tscore_revision"
    interesting = []
    for row in rows:
        fields = row.split("\t")
        balloons = fields[1] if len(fields) > 1 else ""
        answer = fields[2] if len(fields) > 2 else ""
        if balloons not in ("-", "") or answer == "no" or balloons == "UNREADABLE":
            interesting.append(row)
    text = "\n".join([header, *rows])
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    if interesting:
        typer.echo(header)
        typer.echo("\n".join(interesting))
    summary = f"balloons: {balloon_files} / {len(pdfs)}"
    if unreadable:
        summary += f"  unreadable: {unreadable}"
    if check_names:
        summary += (
            f"  names match original content? yes {name_yes}  no {name_no}"
            + (f"  n/a {name_skipped}" if name_skipped else "")
        )
    typer.echo(summary, err=True)
    # A PDF that is not its named pair, or cannot be read, fails the run so a
    # pipeline can gate on it. Balloon pages alone are a report, not a failure.
    raise typer.Exit(1 if name_no or unreadable else 0)


if __name__ == "__main__":
    app()
