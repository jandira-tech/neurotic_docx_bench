"""Word document export and PDF rasterization utilities."""

import re
from pathlib import Path

import pymupdf as fitz  # PyMuPDF (the `fitz` alias package is broken in this venv)


def _sanitize_filename(name: str) -> str:
    """Sanitize a filename to be safe for filesystem and AppleScript.

    Args:
        name: Original filename (without extension).

    Returns:
        Sanitized filename with special characters replaced.
    """
    # Replace any non-alphanumeric characters (except . _ -) with underscore
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return sanitized.strip("_") or "document"


DPI_MIN = 72
DPI_MAX = 600
DEFAULT_DPI = 144

# Stable temp folder to minimize repeated Word permission prompts.
BENCHMARK_TEMP_DIR = Path.home() / ".buceta-benchmark" / "word-temp"


def rasterize_pdf(pdf_path: Path, out_dir: Path, dpi: int = DEFAULT_DPI, prefix: str = "page") -> int:
    """Convert PDF pages to PNG images at a specified DPI.

    Args:
        pdf_path: Path to the input PDF file.
        out_dir: Directory where PNG images will be saved.
        dpi: Dots per inch for rasterization (72-600, default 144).
        prefix: Filename prefix for output PNGs (e.g., "page" -> "page_0001.png").

    Returns:
        Number of pages rasterized.

    Raises:
        RuntimeError: If PDF cannot be opened or rasterization fails.
        ValueError: If DPI is out of valid range.
    """
    if not pdf_path.exists():
        raise RuntimeError(f"PDF file not found: {pdf_path}")
    if dpi < DPI_MIN or dpi > DPI_MAX:
        raise ValueError(f"DPI must be between {DPI_MIN} and {DPI_MAX}, got {dpi}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF: {pdf_path}") from exc

    out_dir.mkdir(parents=True, exist_ok=True)
    page_count = len(doc)

    idx = 0
    try:
        for idx in range(len(doc)):
            page = doc[idx]  # type: ignore[index]
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            pix.save(out_dir / f"{prefix}_{idx + 1:04d}.png")
    except Exception as exc:
        raise RuntimeError(f"Failed to rasterize page {idx + 1}: {exc}") from exc
    finally:
        doc.close()

    return page_count


def get_pdf_page_count(pdf_path: Path) -> int:
    """Get the number of pages in a PDF file.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Number of pages in the PDF.
    """
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


def render_pdf_folder(
    folder: Path,
    dpi: int = DEFAULT_DPI,
    prefix: str = "page",
    force: bool = False,
) -> dict[str, int]:
    """Rasterize every ``*.pdf`` in ``folder`` into ``folder/<stem>/<prefix>_NNNN.png``.

    Each source ``folder/<stem>.pdf`` is rendered into a sibling directory
    ``folder/<stem>/`` so downstream tooling can pick up ``page_*.png`` per
    document. Already-rendered documents are skipped unless ``force`` is set.

    Args:
        folder: Directory containing the source ``.pdf`` files.
        dpi: Rasterization DPI (72-600).
        prefix: Output filename prefix.
        force: Re-render even if page images already exist.

    Returns:
        Mapping of PDF stem -> number of pages rendered this run (0 if cached/skipped).
    """
    folder = Path(folder)
    if not folder.is_dir():
        raise RuntimeError(f"Not a directory: {folder}")

    results: dict[str, int] = {}
    for pdf_path in sorted(folder.glob("*.pdf")):
        out_dir = folder / pdf_path.stem
        existing = sorted(out_dir.glob(f"{prefix}_*.png"))
        if existing and not force:
            results[pdf_path.stem] = 0
            continue
        # Clear stale renders so page numbering stays consistent.
        for stale in existing:
            stale.unlink()
        results[pdf_path.stem] = rasterize_pdf(pdf_path, out_dir, dpi=dpi, prefix=prefix)
    return results


def main(argv: list[str] | None = None) -> int:
    """CLI: rasterize all PDFs in one or more folders to per-document page images."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="report_one.export_pdf",
        description="Rasterize every PDF in a folder into <folder>/<stem>/page_*.png images.",
    )
    parser.add_argument("folders", nargs="+", type=Path, help="Folder(s) containing .pdf files to render.")
    parser.add_argument(
        "--dpi", type=int, default=DEFAULT_DPI, help=f"Rasterization DPI ({DPI_MIN}-{DPI_MAX}, default {DEFAULT_DPI}).",
    )
    parser.add_argument("--prefix", default="page", help="Output filename prefix (default 'page').")
    parser.add_argument("--force", action="store_true", help="Re-render even if page images already exist.")
    args = parser.parse_args(argv)

    total_pdfs = 0
    total_pages = 0
    for folder in args.folders:
        if not folder.is_dir():
            print(f"[skip] not a directory: {folder}")
            continue
        results = render_pdf_folder(folder, dpi=args.dpi, prefix=args.prefix, force=args.force)
        rendered = sum(1 for n in results.values() if n > 0)
        cached = sum(1 for n in results.values() if n == 0)
        pages = sum(results.values())
        total_pdfs += len(results)
        total_pages += pages
        print(f"{folder}: {len(results)} pdf(s) -> {rendered} rendered, {cached} cached, {pages} new page(s)")
    print(f"Done: {total_pdfs} pdf(s) processed, {total_pages} page(s) rendered.")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
