"""The shown-page renderer: MuPDF rasters -> 16-colour lossless WebP + a pages PDF.

Plan 7.4 (issue #131): the gh-pages ``_build`` rendering moves onto main. What the
published pages show is the **first** ``min(12, page count)`` pages of a PDF,
rasterised by MuPDF at **180 DPI** (no downscale), quantised to **16 colours**
(median cut) and stored as **lossless WebP (method 4)**, next to a ``pages.pdf``
holding the same pages (``mutool clean -gggz``'s equivalent: garbage collection 4,
deflated). Arthur's decision of 2026-11-03 (option 3) fixed the page cap at 12 and
the storage resolution at 180 DPI; scoring stays in ``raster.py`` at 144 DPI over
every page and is *not* part of this module.

Two backends rasterise the same MuPDF pages:

* ``mupdf`` (the default) — PyMuPDF, already a dependency, no external binary;
* ``mutool`` — the ``mutool draw``/``mutool clean`` of the reference build, for
  parity work; it must exist on PATH or the render says so.

Every render is a pure function of its input: the same PDF gives byte-identical
WebPs and ``pages.pdf`` (the pages PDF carries a deterministic ``/ID`` derived
from the input's sha256, so it never depends on a clock or a random draw).

    uv run python -m neurotic_docx_bench.cli pages render \\
        --set results/sets/convert_860.csv --column word_pdf \\
        --root ~/temp/T/neurotic_docx_bench --out results/pages/convert_860
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image

#: How many pages of a PDF are shown (the first ones).
MAX_PAGES = 12
#: The stored resolution: 180 DPI, no downscale (Arthur, 2026-11-03).
DEFAULT_DPI = 180
#: The palette size of every stored page image.
COLORS = 16
#: The WebP encoder effort (lossless; the reference build's setting).
WEBP_METHOD = 4
#: The shown-page PDF's name inside a render directory.
PAGES_PDF_NAME = "pages.pdf"
#: The render manifest's name inside a render directory.
MANIFEST_NAME = "render.json"
#: The page image's name inside a render directory.
IMAGE_NAME = "page-{page:03d}.webp"

BACKEND_MUPDF = "mupdf"
BACKEND_MUTOOL = "mutool"
BACKENDS = (BACKEND_MUPDF, BACKEND_MUTOOL)

#: The environment variable that names the mutool binary (default: ``mutool``).
MUTOOL_ENV = "BENCH_MUTOOL"


class RenderError(RuntimeError):
    """A render that cannot be done (missing PDF, missing mutool, bad backend)."""


@dataclass(frozen=True)
class PageImage:
    """One stored page image."""

    page: int  # 1-based page number
    name: str  # the file's name inside the render directory
    bytes: int
    sha256: str


@dataclass(frozen=True)
class RenderResult:
    """What one rendered PDF produced."""

    pdf: Path
    out_dir: Path
    page_count: int  # the PDF's true page count
    shown: tuple[int, ...]  # the 1-based page numbers that were stored
    dpi: int
    colors: int
    backend: str
    images: tuple[PageImage, ...]
    pdf_bytes: int
    pdf_sha256: str
    input_sha256: str
    reused: bool = False  # True when the render directory was already up to date

    @property
    def total_bytes(self) -> int:
        """The bytes of every stored file (the page images and the pages PDF)."""
        return sum(image.bytes for image in self.images) + self.pdf_bytes

    @property
    def image_bytes(self) -> int:
        """The bytes of the page images alone."""
        return sum(image.bytes for image in self.images)


@dataclass(frozen=True)
class CaseResult:
    """One row of a lane: what its PDF produced (or why it did not)."""

    case: str
    pdf: Path
    out_dir: Path
    page_count: int = 0
    shown: tuple[int, ...] = ()
    image_bytes: int = 0
    pdf_bytes: int = 0
    reused: bool = False
    error: str | None = None

    @property
    def bytes(self) -> int:
        """Every byte the case stored (the page images and the pages PDF)."""
        return self.image_bytes + self.pdf_bytes


@dataclass(frozen=True)
class LaneReport:
    """The outcome of rendering a lane (a CSV of PDF paths)."""

    csv: Path
    out_root: Path
    rows: int = 0
    rendered: int = 0
    reused: int = 0
    failed: int = 0
    pages: int = 0
    image_bytes: int = 0
    pdf_bytes: int = 0
    cases: tuple[CaseResult, ...] = ()

    @property
    def bytes(self) -> int:
        """Every byte the lane stored (the page images and the pages PDFs)."""
        return self.image_bytes + self.pdf_bytes

    @property
    def errors(self) -> tuple[tuple[str, str], ...]:
        """The failed cases with their messages."""
        return tuple((case.case, case.error or "") for case in self.cases if case.error)


def sha256_file(path: Path) -> str:
    """The sha256 of a file, read in blocks (a 200 MB PDF does not fit in memory)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def page_numbers(directory: Path) -> list[int]:
    """The page numbers of the page images in one asset directory.

    Both spellings count: the published trees hold ``page_001.webp`` and the
    renderer of #131 writes ``page-001.webp``.
    """
    numbers = []
    for path in Path(directory).glob("page*.webp"):
        if (match := re.fullmatch(r"page[-_](\d{3,})\.webp", path.name)) is not None:
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def mutool_binary() -> str:
    """The mutool binary to use, from ``BENCH_MUTOOL`` or the PATH."""
    return os.environ.get(MUTOOL_ENV, "mutool")


def require_mutool() -> str:
    """The mutool binary, or a clear refusal when it is not installed.

    Raises:
        RenderError: when the binary cannot be found.
    """
    binary = mutool_binary()
    found = shutil.which(binary)
    if found is None:
        raise RenderError(
            f"mutool not found: {binary!r} is not on PATH. Install mupdf-tools "
            f"(brew install mupdf-tools) or render with the {BACKEND_MUPDF!r} backend."
        )
    return found


def page_count(pdf: Path) -> int:
    """The PDF's page count.

    Raises:
        RenderError: when the PDF cannot be opened.
    """
    try:
        doc = pymupdf.open(pdf)
    except Exception as exc:
        raise RenderError(f"cannot open PDF: {pdf} ({exc})") from exc
    try:
        return doc.page_count
    finally:
        doc.close()


def shown_pages(page_count: int, max_pages: int = MAX_PAGES) -> tuple[int, ...]:
    """The 1-based page numbers that are shown: the first ``min(max_pages, count)``."""
    return tuple(range(1, min(max_pages, page_count) + 1))


def raster_pages(
    pdf: Path,
    pages: Sequence[int],
    dpi: int = DEFAULT_DPI,
    backend: str = BACKEND_MUPDF,
) -> list[bytes]:
    """The PNG rasters of ``pages`` (1-based), at ``dpi``.

    Args:
        pdf: the PDF to raster.
        pages: the 1-based page numbers to raster.
        dpi: the resolution.
        backend: ``mupdf`` (PyMuPDF) or ``mutool``.

    Returns:
        One PNG per requested page, in order.

    Raises:
        RenderError: when the backend is unknown, mutool is missing or the
            rasterisation failed.
    """
    if backend == BACKEND_MUPDF:
        return _raster_mupdf(pdf, pages, dpi)
    if backend == BACKEND_MUTOOL:
        return _raster_mutool(pdf, pages, dpi)
    raise RenderError(f"unknown backend: {backend!r} (one of {', '.join(BACKENDS)})")


def _raster_mupdf(pdf: Path, pages: Sequence[int], dpi: int) -> list[bytes]:
    try:
        doc = pymupdf.open(pdf)
    except Exception as exc:
        raise RenderError(f"cannot open PDF: {pdf} ({exc})") from exc
    try:
        rasters: list[bytes] = []
        for number in pages:
            page = doc[number - 1]
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            rasters.append(pixmap.tobytes("png"))
        return rasters
    except RenderError:
        raise
    except Exception as exc:
        raise RenderError(f"cannot rasterise {pdf}: {exc}") from exc
    finally:
        doc.close()


def _raster_mutool(pdf: Path, pages: Sequence[int], dpi: int) -> list[bytes]:
    binary = require_mutool()
    with tempfile.TemporaryDirectory(prefix="pages-render-") as tmp:
        out = Path(tmp)
        command = [
            binary, "draw", "-q", "-F", "png", "-r", str(dpi),
            "-o", str(out / "page_%03d.png"), str(pdf),
            ",".join(str(number) for number in pages),
        ]
        finished = subprocess.run(command, capture_output=True, text=True)
        if finished.returncode:
            raise RenderError(
                f"mutool draw failed ({finished.returncode}): {finished.stderr[-500:].strip()}"
            )
        rasters = sorted(out.glob("page_*.png"))
        if len(rasters) != len(pages):
            raise RenderError(
                f"mutool draw produced {len(rasters)} page(s), expected {len(pages)}"
            )
        return [raster.read_bytes() for raster in rasters]


def encode_webp(png: bytes, colors: int = COLORS) -> bytes:
    """A PNG raster as a 16-colour (median cut) lossless WebP.

    Args:
        png: the raster's PNG bytes.
        colors: the palette size.

    Returns:
        The WebP bytes.
    """
    with Image.open(io.BytesIO(png)) as source:
        image = source.convert("RGB")
    image = image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    buffer = io.BytesIO()
    image.save(buffer, "WEBP", lossless=True, method=WEBP_METHOD)
    return buffer.getvalue()


def write_pages_pdf(
    pdf: Path,
    out: Path,
    pages: Sequence[int],
    input_sha256: str,
    backend: str = BACKEND_MUPDF,
) -> None:
    """The shown pages as one PDF (garbage collected and deflated).

    The ``mupdf`` backend writes a deterministic ``/ID`` (derived from the input's
    sha256) so the file is a pure function of its input.

    Raises:
        RenderError: when the PDF cannot be written.
    """
    if backend == BACKEND_MUTOOL:
        binary = require_mutool()
        command = [
            binary, "clean", "-gggz", str(pdf), str(out),
            ",".join(str(number) for number in pages),
        ]
        finished = subprocess.run(command, capture_output=True, text=True)
        if finished.returncode:
            raise RenderError(
                f"mutool clean failed ({finished.returncode}): {finished.stderr[-500:].strip()}"
            )
        return
    if backend != BACKEND_MUPDF:
        raise RenderError(f"unknown backend: {backend!r} (one of {', '.join(BACKENDS)})")
    try:
        doc = pymupdf.open(pdf)
    except Exception as exc:
        raise RenderError(f"cannot open PDF: {pdf} ({exc})") from exc
    try:
        doc.select([number - 1 for number in pages])
        # A deterministic /ID: no clock, no random draw in the output.
        identifier = input_sha256[:32]
        doc.xref_set_key(-1, "ID", f"[<{identifier}><{identifier}>]")
        doc.save(out, garbage=4, deflate=True, no_new_id=True)
    except Exception as exc:
        raise RenderError(f"cannot write {out}: {exc}") from exc
    finally:
        doc.close()


def _params(max_pages: int, dpi: int, colors: int, backend: str) -> dict[str, object]:
    return {"max_pages": max_pages, "dpi": dpi, "colors": colors, "backend": backend}


def _result_from_manifest(
    manifest_path: Path,
    out_dir: Path,
    pdf: Path,
    input_sha256: str,
    params: dict[str, object],
) -> RenderResult | None:
    """The stored result of an up-to-date render directory, or None."""
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if manifest.get("input_sha256") != input_sha256:
        return None
    if manifest.get("params") != params:
        return None
    images: list[PageImage] = []
    for entry in manifest.get("images") or []:
        name = str(entry["name"])
        path = out_dir / name
        if not path.is_file() or path.stat().st_size != entry["bytes"]:
            return None
        if sha256_file(path) != entry["sha256"]:
            return None
        images.append(
            PageImage(
                page=int(entry["page"]),
                name=name,
                bytes=int(entry["bytes"]),
                sha256=str(entry["sha256"]),
            )
        )
    pages_pdf = manifest.get("pages_pdf") or {}
    pdf_path = out_dir / str(pages_pdf.get("name", PAGES_PDF_NAME))
    if not pdf_path.is_file() or pdf_path.stat().st_size != pages_pdf.get("bytes"):
        return None
    if sha256_file(pdf_path) != pages_pdf.get("sha256"):
        return None
    return RenderResult(
        pdf=pdf,
        out_dir=out_dir,
        page_count=int(manifest["page_count"]),
        shown=tuple(int(number) for number in manifest["shown"]),
        dpi=int(params["dpi"]),  # type: ignore[arg-type]
        colors=int(params["colors"]),  # type: ignore[arg-type]
        backend=str(params["backend"]),
        images=tuple(images),
        pdf_bytes=int(pages_pdf["bytes"]),
        pdf_sha256=str(pages_pdf["sha256"]),
        input_sha256=input_sha256,
        reused=True,
    )


def render_pdf(
    pdf: Path,
    out_dir: Path,
    *,
    max_pages: int = MAX_PAGES,
    dpi: int = DEFAULT_DPI,
    colors: int = COLORS,
    backend: str = BACKEND_MUPDF,
    force: bool = False,
) -> RenderResult:
    """Render a PDF's shown pages into ``out_dir``.

    Writes ``page-001.webp``… (one per shown page) and ``pages.pdf`` (the same
    pages), plus ``render.json`` — the manifest that makes a rerun cheap: an
    input whose sha256 and parameters match is skipped.

    Args:
        pdf: the PDF to render.
        out_dir: where the pages go (created when missing).
        max_pages: the page cap (the first ``min(max_pages, page count)`` pages).
        dpi: the stored resolution.
        colors: the palette size of every page image.
        backend: ``mupdf`` or ``mutool``.
        force: re-render even when the directory is already up to date.

    Returns:
        The render's result (with ``reused`` set when nothing was rendered).

    Raises:
        RenderError: when the PDF is missing, the backend is unknown or the
            rendering failed.
    """
    pdf = Path(pdf)
    out_dir = Path(out_dir)
    if not pdf.is_file():
        raise RenderError(f"PDF not found: {pdf}")
    if max_pages < 1:
        raise RenderError(f"max_pages must be at least 1, got {max_pages}")
    if backend not in BACKENDS:
        raise RenderError(f"unknown backend: {backend!r} (one of {', '.join(BACKENDS)})")
    input_sha256 = sha256_file(pdf)
    params = _params(max_pages, dpi, colors, backend)
    manifest_path = out_dir / MANIFEST_NAME
    if not force:
        stored = _result_from_manifest(manifest_path, out_dir, pdf, input_sha256, params)
        if stored is not None:
            return stored
    out_dir.mkdir(parents=True, exist_ok=True)
    count = page_count(pdf)
    shown = shown_pages(count, max_pages)
    if not shown:
        raise RenderError(f"{pdf} has no page to show")
    rasters = raster_pages(pdf, shown, dpi, backend)
    images: list[PageImage] = []
    for number, raster in zip(shown, rasters, strict=True):
        data = encode_webp(raster, colors)
        name = IMAGE_NAME.format(page=number)
        (out_dir / name).write_bytes(data)
        images.append(
            PageImage(
                page=number,
                name=name,
                bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )
        )
    keep = {image.name for image in images}
    for stale in out_dir.glob("page-*.webp"):
        if stale.name not in keep:
            stale.unlink()
    pages_pdf = out_dir / PAGES_PDF_NAME
    write_pages_pdf(pdf, pages_pdf, shown, input_sha256, backend)
    manifest = {
        "input": pdf.name,
        "input_sha256": input_sha256,
        "page_count": count,
        "shown": list(shown),
        "params": params,
        "images": [
            {"page": image.page, "name": image.name, "bytes": image.bytes, "sha256": image.sha256}
            for image in images
        ],
        "pages_pdf": {
            "name": PAGES_PDF_NAME,
            "bytes": pages_pdf.stat().st_size,
            "sha256": sha256_file(pages_pdf),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return RenderResult(
        pdf=pdf,
        out_dir=out_dir,
        page_count=count,
        shown=shown,
        dpi=dpi,
        colors=colors,
        backend=backend,
        images=tuple(images),
        pdf_bytes=manifest["pages_pdf"]["bytes"],  # type: ignore[index]
        pdf_sha256=manifest["pages_pdf"]["sha256"],  # type: ignore[index]
        input_sha256=input_sha256,
        reused=False,
    )


def _case_name(row: dict[str, str], pdf: Path) -> str:
    """The directory name of a lane row: its case id, else its PDF's stem."""
    for column in ("case", "stem", "id", "key"):
        value = (row.get(column) or "").strip()
        if value:
            return value.replace("/", "__").replace(os.sep, "__")
    return pdf.stem


def _resolve(path: str, root: Path) -> Path:
    """A lane row's PDF path: absolute, or relative to the bench root."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _render_task(task: tuple[str, str, str, dict[str, object]]) -> dict[str, object]:
    """Render one lane row in a worker process (picklable: module level)."""
    case, pdf, out_dir, params = task
    try:
        result = render_pdf(Path(pdf), Path(out_dir), **params)  # type: ignore[arg-type]
    except Exception as exc:
        return {"case": case, "pdf": pdf, "out_dir": out_dir, "error": f"{exc}"}
    return {
        "case": case,
        "pdf": pdf,
        "out_dir": out_dir,
        "page_count": result.page_count,
        "shown": list(result.shown),
        "image_bytes": result.image_bytes,
        "pdf_bytes": result.pdf_bytes,
        "reused": result.reused,
        "error": None,
    }


def render_lane(
    list_csv: Path,
    pdf_column: str,
    out_root: Path,
    jobs: int = 1,
    *,
    root: Path = Path("."),
    max_pages: int = MAX_PAGES,
    dpi: int = DEFAULT_DPI,
    colors: int = COLORS,
    backend: str = BACKEND_MUPDF,
    force: bool = False,
) -> LaneReport:
    """Render every PDF a lane's CSV names.

    The rows are read from ``list_csv``; the PDF of a row is the ``pdf_column``
    cell (relative to ``root``, the bench root, when it is not absolute) and its
    pages land in ``out_root/<case>/``. A row whose render directory is already
    up to date (the manifest's input sha256 matches) is skipped, so the lane is
    resumable.

    Args:
        list_csv: the lane's CSV.
        pdf_column: the column holding the PDF path.
        out_root: where the per-case directories go.
        jobs: how many PDFs to render at once (a process pool when above one).
        root: the bench root the column's relative paths hang off.
        max_pages: the page cap.
        dpi: the stored resolution.
        colors: the palette size of every page image.
        backend: ``mupdf`` or ``mutool``.
        force: re-render every row.

    Returns:
        The lane's report (rendered, reused and failed counts; per-case results).

    Raises:
        RenderError: when the CSV cannot be read or has no usable column.
    """
    list_csv = Path(list_csv)
    out_root = Path(out_root)
    root = Path(root)
    if not list_csv.is_file():
        raise RenderError(f"lane CSV not found: {list_csv}")
    try:
        with list_csv.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    except OSError as exc:
        raise RenderError(f"cannot read {list_csv}: {exc}") from exc
    if rows and pdf_column not in rows[0]:
        raise RenderError(
            f"{list_csv} has no {pdf_column!r} column (columns: {', '.join(rows[0])})"
        )
    params = _params(max_pages, dpi, colors, backend)
    options: dict[str, object] = {**params, "force": force}
    tasks: list[tuple[str, str, str, dict[str, object]]] = []
    skipped: list[CaseResult] = []
    for index, row in enumerate(rows, start=1):
        cell = (row.get(pdf_column) or "").strip()
        if not cell:
            skipped.append(
                CaseResult(
                    case=f"row {index}",
                    pdf=Path(),
                    out_dir=out_root,
                    error=f"row {index} has no {pdf_column!r} path",
                )
            )
            continue
        pdf = _resolve(cell, root)
        case = _case_name(row, pdf)
        tasks.append((case, str(pdf), str(out_root / case), options))
    if jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            outcomes = list(pool.map(_render_task, tasks))
    else:
        outcomes = [_render_task(task) for task in tasks]
    cases: list[CaseResult] = []
    for outcome in outcomes:
        error = outcome.get("error")
        cases.append(
            CaseResult(
                case=str(outcome["case"]),
                pdf=Path(str(outcome["pdf"])),
                out_dir=Path(str(outcome["out_dir"])),
                page_count=int(outcome.get("page_count") or 0),
                shown=tuple(int(number) for number in outcome.get("shown") or ()),
                image_bytes=int(outcome.get("image_bytes") or 0),
                pdf_bytes=int(outcome.get("pdf_bytes") or 0),
                reused=bool(outcome.get("reused")),
                error=str(error) if error else None,
            )
        )
    cases.extend(skipped)
    rendered = sum(1 for case in cases if case.error is None and not case.reused)
    reused = sum(1 for case in cases if case.error is None and case.reused)
    failed = sum(1 for case in cases if case.error is not None)
    return LaneReport(
        csv=list_csv,
        out_root=out_root,
        rows=len(rows),
        rendered=rendered,
        reused=reused,
        failed=failed,
        pages=sum(len(case.shown) for case in cases if case.error is None),
        image_bytes=sum(case.image_bytes for case in cases if case.error is None),
        pdf_bytes=sum(case.pdf_bytes for case in cases if case.error is None),
        cases=tuple(cases),
    )
