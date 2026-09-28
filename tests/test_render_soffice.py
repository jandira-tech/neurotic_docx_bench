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


def test_failure_detail_names_the_crash_not_the_fontconfig_noise():
    from neurotic_docx_bench.render.soffice import failure_detail

    stderr = (
        "Fontconfig warning: no <cachedir> elements found. Check configuration.\n"
        "Fontconfig warning: adding <cachedir>/usr/local/var/cache/fontconfig</cachedir>\n"
        "Unspecified Application Error\n\n\n"
        "Fatal exception: Signal 6\n"
        "Stack:\n"
        "#0 0   libuno_sal.dylib.3 0x00000001044e231c _ZN3sal13backtrace_getEj\n"
    )
    assert failure_detail(134, stderr, "") == (
        "soffice exit 134: Unspecified Application Error | Fatal exception: Signal 6"
    )


def test_failure_detail_falls_back_to_the_exit_status():
    from neurotic_docx_bench.render.soffice import failure_detail

    assert failure_detail(1, "Fontconfig warning: x\n", "") == "soffice exit 1"
    assert failure_detail(-9, "", "") == "soffice killed by signal 9"
    assert failure_detail(0, "", "") == "soffice exit 0 but wrote no PDF"
