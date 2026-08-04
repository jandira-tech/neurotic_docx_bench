"""Renderer protocol + shared result types.

A renderer turns a *source* folder into a folder of PDFs (one per document), which the
scoring pipeline then rasterizes and compares against the Word oracle. The two PR2
backends are ``soffice`` (DOCX→PDF via LibreOffice) and ``passthrough`` (the source is
already a folder of PDFs — nothing to render). Later PRs add ``playwright`` and ``word``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RenderResult:
    """Outcome of converting a single source document to PDF."""

    source: Path
    pdf: Path | None
    ok: bool
    skipped: bool = False
    error: str | None = None
    duration_ns: int | None = None


@dataclass(frozen=True)
class RenderReport:
    """Result of rendering a whole folder.

    ``pdf_dir`` is the directory that now contains the produced (or pre-existing) PDFs.
    """

    pdf_dir: Path
    results: list[RenderResult] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.ok)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if not r.ok)

    @property
    def pdfs(self) -> list[Path]:
        return sorted(r.pdf for r in self.results if r.ok and r.pdf is not None)


@runtime_checkable
class Renderer(Protocol):
    """Turn a source folder into a folder of PDFs."""

    name: str

    def to_pdfs(
        self,
        source_dir: Path,
        work_dir: Path,
        *,
        force: bool = False,
        jobs: int = 12,
    ) -> RenderReport:
        """Render every source document under ``source_dir`` to a PDF.

        ``work_dir`` is a per-run scratch dir the backend may write into. Returns a
        :class:`RenderReport` whose ``pdf_dir`` holds the resulting PDFs.
        """
        ...
