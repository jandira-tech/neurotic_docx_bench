"""soffice renderer — parity with .old/docx-to-pdf.sh behaviour."""

from __future__ import annotations

import pymupdf as fitz
from helpers import requires_soffice

from neurotic_docx_bench.render import soffice
from neurotic_docx_bench.render.base import RenderReport


@requires_soffice
def test_find_soffice_returns_executable():
    path = soffice.find_soffice()
    assert path.exists(), f"{path} should exist"


@requires_soffice
def test_convert_one_produces_valid_pdf(tmp_path, sample_docx):
    out = tmp_path / "out"
    out.mkdir()
    result = soffice.convert_one(soffice.find_soffice(), sample_docx[0], out)
    assert result.ok, result.error
    assert result.pdf is not None and result.pdf.exists()
    assert result.pdf.suffix == ".pdf"
    with fitz.open(result.pdf) as doc:
        assert doc.page_count >= 1


@requires_soffice
def test_convert_one_skips_when_exists(tmp_path, sample_docx):
    out = tmp_path / "out"
    out.mkdir()
    sof = soffice.find_soffice()
    first = soffice.convert_one(sof, sample_docx[0], out)
    assert first.ok and not first.skipped
    again = soffice.convert_one(sof, sample_docx[0], out, force=False)
    assert again.ok and again.skipped, "second conversion should skip the existing PDF"


@requires_soffice
def test_renderer_to_pdfs_folder(tmp_path, docx_dir):
    work = tmp_path / "work"
    report = soffice.SofficeRenderer().to_pdfs(docx_dir, work, jobs=2)
    assert isinstance(report, RenderReport)
    assert report.pdf_dir == work / "pdf"
    assert report.ok_count == 2, [(r.source.name, r.error) for r in report.results]
    assert len(report.pdfs) == 2
    for pdf in report.pdfs:
        assert pdf.exists() and pdf.suffix == ".pdf"
