"""PDF report generation for visual comparisons."""

import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pymupdf as fitz  # PyMuPDF (the `fitz` alias package is broken in this venv)
from PIL import Image

from neurotic_docx_bench.diff import build_diff_overlay
from neurotic_docx_bench.score import score_document

# Reports folder in current working directory
REPORTS_DIR = Path.cwd() / "reports"


def get_reports_dir() -> Path:
    """Get the reports directory, creating it if needed.

    Returns:
        Path to the reports directory.
    """
    REPORTS_DIR.mkdir(exist_ok=True)
    return REPORTS_DIR


def get_comparisons_dir() -> Path:
    """Get the comparisons directory, creating it if needed.

    Returns:
        Path to reports/comparisons/
    """
    comparisons_dir = get_reports_dir() / "comparisons"
    comparisons_dir.mkdir(exist_ok=True)
    return comparisons_dir


def _sanitize_report_label(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return sanitized or "report"


def build_run_label(version_label: str, timestamp: datetime | None = None) -> str:
    """Build a timestamped label for a comparison run."""
    safe_version = _sanitize_report_label(version_label)
    when = timestamp or datetime.now()
    stamp = when.strftime("%Y%m%d-%H%M%S")
    return f"report-{safe_version}-{stamp}"


def create_run_report_dir(version_label: str, timestamp: datetime | None = None) -> tuple[Path, str]:
    """Create and return a run-level report directory and its label."""
    run_label = build_run_label(version_label, timestamp)
    run_dir = get_comparisons_dir() / run_label
    if run_dir.exists():
        suffix = datetime.now().strftime("%f")
        run_label = f"{run_label}-{suffix}"
        run_dir = get_comparisons_dir() / run_label
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir, run_label


def get_doc_report_dir(run_dir: Path, docx_name: str) -> Path:
    """Get the report directory for a document within a run."""
    return run_dir / docx_name


def create_side_by_side(
    left_img: Image.Image, right_img: Image.Image, gap: int = 20, background: tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """Create a side-by-side image from two images.

    Args:
        left_img: Left image.
        right_img: Right image.
        gap: Gap between images in pixels.
        background: Background color (RGB).

    Returns:
        Combined side-by-side image.
    """
    # Resize right to match left height if needed
    if left_img.height != right_img.height:
        ratio = left_img.height / right_img.height
        new_width = int(right_img.width * ratio)
        right_img = right_img.resize((new_width, left_img.height), Image.Resampling.LANCZOS)

    # Create combined image
    total_width = left_img.width + gap + right_img.width
    combined = Image.new("RGB", (total_width, left_img.height), background)

    # Paste images
    combined.paste(left_img, (0, 0))
    combined.paste(right_img, (left_img.width + gap, 0))

    return combined


def images_to_pdf(images: list[Image.Image], output_path: Path) -> None:
    """Convert a list of PIL images to a PDF.

    Args:
        images: List of PIL images.
        output_path: Path to save the PDF.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = fitz.open()

    for img in images:
        # Convert PIL image to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Create page with image dimensions
        # Convert pixels to points (72 points per inch, assume 144 DPI)
        width_pt = img.width * 72 / 144
        height_pt = img.height * 72 / 144

        page = doc.new_page(width=width_pt, height=height_pt)

        # Insert image
        rect = fitz.Rect(0, 0, width_pt, height_pt)
        page.insert_image(rect, stream=img_bytes.read())

    doc.save(str(output_path))
    doc.close()


def generate_comparison_pdf(
    word_pages: list[Path], jubarte_pages: list[Path], output_path: Path, gap: int = 20,
) -> None:
    """Generate a comparison PDF with Word and SuperDoc side by side.

    Args:
        word_pages: List of Word page image paths (sorted).
        jubarte_pages: List of SuperDoc page image paths (sorted).
        output_path: Path to save the PDF.
        gap: Gap between images in pixels.
    """
    combined_images = []

    # Match pages by index
    num_pages = min(len(word_pages), len(jubarte_pages))

    for i in range(num_pages):
        word_img = Image.open(word_pages[i])
        superdoc_img = Image.open(jubarte_pages[i])

        combined = create_side_by_side(word_img, superdoc_img, gap=gap)
        combined_images.append(combined)

    images_to_pdf(combined_images, output_path)


def generate_diff_pdf(word_pages: list[Path], jubarte_pages: list[Path], output_path: Path, gap: int = 20) -> None:
    """Generate a diff PDF with Word and diff overlay side by side.

    Args:
        word_pages: List of Word page image paths (sorted).
        jubarte_pages: List of SuperDoc page image paths (sorted).
        output_path: Path to save the PDF.
        gap: Gap between images in pixels.
    """
    combined_images = []

    # Match pages by index
    num_pages = min(len(word_pages), len(jubarte_pages))

    for i in range(num_pages):
        word_img = Image.open(word_pages[i])
        superdoc_img = Image.open(jubarte_pages[i])

        # Generate diff overlay
        diff_img = build_diff_overlay(word_img, superdoc_img)

        combined = create_side_by_side(word_img, diff_img, gap=gap)
        combined_images.append(combined)

    images_to_pdf(combined_images, output_path)


def generate_reports(docx_name: str, word_dir: Path, jubarte_dir: Path, version_label: str, report_dir: Path) -> dict:
    """Generate comparison and diff PDF reports for a document.

    Args:
        docx_name: Name of the document (stem).
        word_dir: Directory containing Word page images.
        jubarte_dir: Directory containing SuperDoc page images.
        version_label: SuperDoc version label for filename.
        report_dir: Output directory for the document's reports.

    Returns:
        Dict with paths to generated reports.
    """
    # Get sorted page lists
    word_pages = sorted(word_dir.glob("page_*.png"))
    jubarte_pages = sorted(jubarte_dir.glob("page_*.png"))

    if not word_pages:
        raise RuntimeError(f"No Word pages found in {word_dir}")
    if not jubarte_pages:
        raise RuntimeError(f"No SuperDoc pages found in {jubarte_dir}")

    # Create report directory
    report_dir.mkdir(parents=True, exist_ok=True)

    # Generate comparison PDF
    comparison_path = report_dir / f"comparison-{version_label}.pdf"
    generate_comparison_pdf(word_pages, jubarte_pages, comparison_path)

    # Generate diff PDF
    diff_path = report_dir / f"diff-{version_label}.pdf"
    generate_diff_pdf(word_pages, jubarte_pages, diff_path)

    # Generate scoring files
    try:
        score_data = score_document(word_pages, jubarte_pages)
    except Exception as exc:
        raise RuntimeError(f"Failed to score document: {exc}") from exc

    score_json_path = report_dir / f"score-{version_label}.json"
    score_json_path.write_text(json.dumps(score_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report_by_version_path = _update_report_by_version(report_dir, docx_name)

    return {
        "report_dir": report_dir,
        "comparison_pdf": comparison_path,
        "diff_pdf": diff_path,
        "score_json": score_json_path,
        "report_by_version": report_by_version_path,
        "word_pages": len(word_pages),
        "jubarte_pages": len(jubarte_pages),
    }


def _update_report_by_version(report_dir: Path, docx_name: str) -> Path:
    score_files = sorted(report_dir.glob("score-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)

    entries = []
    for score_path in score_files:
        version = score_path.stem.removeprefix("score-")
        mtime = score_path.stat().st_mtime
        generated_at = datetime.fromtimestamp(mtime, tz=UTC).isoformat()
        try:
            data = json.loads(score_path.read_text(encoding="utf-8"))
            entry = {
                "version": version,
                "score_file": score_path.name,
                "generated_at": generated_at,
                "mtime_epoch": mtime,
                "score": data,
            }
        except Exception as exc:
            entry = {
                "version": version,
                "score_file": score_path.name,
                "generated_at": generated_at,
                "mtime_epoch": mtime,
                "error": str(exc),
            }
        entries.append(entry)

    report_data = {"document": docx_name, "updated_at": datetime.now(tz=UTC).isoformat(), "scores": entries}

    report_path = report_dir / "report-by-version.json"
    report_path.write_text(json.dumps(report_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report_path
