"""neurotic-docx-bench — DOCX tool fidelity benchmark vs a Microsoft Word oracle.

The scoring core (``score``/``diff``/``report``/``html_report``/``raster``/``utils``)
is lifted verbatim from ``superdoc-visual-benchmarks`` (see README provenance); only
absolute→relative imports and a soft logo-path lookup were adjusted so the numbers stay
byte-identical to the in-tree harness.
"""

from neurotic_docx_bench.diff import SUPERDOC_DIFF_COLOR, WORD_DIFF_COLOR, build_diff_overlay, create_diff_from_files
from neurotic_docx_bench.html_report import DocumentReportInput, generate_html_report
from neurotic_docx_bench.raster import DEFAULT_DPI, get_pdf_page_count, rasterize_pdf, render_pdf_folder
from neurotic_docx_bench.report import (
    build_run_label,
    create_run_report_dir,
    generate_comparison_pdf,
    generate_diff_pdf,
    generate_reports,
    get_doc_report_dir,
    get_reports_dir,
)
from neurotic_docx_bench.score import ScoreConfig, ScoreWeights, format_score_text, score_document

__all__ = [
    "DEFAULT_DPI",
    "SUPERDOC_DIFF_COLOR",
    "WORD_DIFF_COLOR",
    "DocumentReportInput",
    "ScoreConfig",
    "ScoreWeights",
    "build_diff_overlay",
    "build_run_label",
    "create_diff_from_files",
    "create_run_report_dir",
    "format_score_text",
    "generate_comparison_pdf",
    "generate_diff_pdf",
    "generate_html_report",
    "generate_reports",
    "get_doc_report_dir",
    "get_pdf_page_count",
    "get_reports_dir",
    "rasterize_pdf",
    "render_pdf_folder",
    "score_document",
]
