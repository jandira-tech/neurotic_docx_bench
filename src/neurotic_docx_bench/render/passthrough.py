"""Passthrough renderer — the source folder already contains PDFs; nothing to render.

Requirements:
- ``to_pdfs`` treats ``source_dir`` as a folder of finished PDFs. It does NOT copy or
  move them; ``RenderReport.pdf_dir`` points straight at ``source_dir``.
- Every ``*.docx``-free ``*.pdf`` (top-level, sorted) becomes an ``ok`` RenderResult
  with ``skipped=True`` (there was nothing to do).
- ``force`` and ``jobs`` are accepted for protocol conformance and ignored.
- Raise ``FileNotFoundError`` if ``source_dir`` doesn't exist; an empty (0-PDF) folder is
  allowed and yields an empty report.
"""

from __future__ import annotations

from pathlib import Path

from neurotic_docx_bench.render.base import RenderReport, RenderResult


class PassthroughRenderer:
    name = "passthrough"

    def to_pdfs(
        self,
        source_dir: Path,
        work_dir: Path,
        *,
        force: bool = False,
        jobs: int = 12,
        timeout: float = 1200.0,
    ) -> RenderReport:
        if not source_dir.is_dir():
            raise FileNotFoundError(f"passthrough source is not a directory: {source_dir}")
        results = [
            RenderResult(source=pdf, pdf=pdf, ok=True, skipped=True)
            for pdf in sorted(source_dir.glob("*.pdf"))
        ]
        return RenderReport(pdf_dir=source_dir, results=results)
