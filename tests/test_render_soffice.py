"""soffice renderer — parity with .old/docx-to-pdf.sh behaviour."""

from __future__ import annotations

import shlex
import sys
import time

import pymupdf as fitz
import pytest
from helpers import requires_soffice

from neurotic_docx_bench.render import soffice
from neurotic_docx_bench.render.base import RenderReport


def _converter(tmp_path, body):
    script = tmp_path / "soffice.py"
    script.write_text(body)
    binary = tmp_path / "soffice"
    binary.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(script))} "$@"\n')
    binary.chmod(0o755)
    return binary


@pytest.mark.parametrize("first", ["timeout", "nonzero", "crash"])
def test_failed_attempt_never_reuses_partial_pdf(tmp_path, first):
    attempts = tmp_path / "attempts"
    binary = _converter(
        tmp_path,
        "import os, signal, sys, time\n"
        "from pathlib import Path\n"
        f"attempts = Path({str(attempts)!r})\n"
        "n = int(attempts.read_text()) + 1 if attempts.exists() else 1\n"
        "attempts.write_text(str(n))\n"
        "out = Path(sys.argv[sys.argv.index('--outdir') + 1]) / 'a.pdf'\n"
        "if n == 1:\n"
        "    out.write_bytes(b'%PDF-1.7 partial')\n"
        f"    if {first!r} == 'timeout': time.sleep(30)\n"
        f"    if {first!r} == 'crash': os.kill(os.getpid(), signal.SIGKILL)\n"
        "    sys.exit(3)\n"
        f"if {first!r} == 'crash': out.write_bytes(b'%PDF-1.7 complete')\n"
    )
    result = soffice.convert_one(binary, tmp_path / "a.docx", tmp_path / "pdf", timeout=0.5)
    pdf = tmp_path / "pdf" / "a.pdf"
    assert result.ok is (first == "crash")
    assert attempts.read_text() == ("1" if first == "timeout" else "2")
    if first == "crash":
        assert pdf.read_bytes() == b"%PDF-1.7 complete"
    else:
        assert not pdf.exists()


def test_fake_converter_handles_spaces_in_its_interpreter_and_script_paths(tmp_path, monkeypatch):
    folder = tmp_path / "fake converter with spaces"
    folder.mkdir()
    interpreter = folder / "python"
    interpreter.symlink_to(sys.executable)
    monkeypatch.setattr(sys, "executable", str(interpreter))
    binary = _converter(
        folder,
        "import sys\n"
        "from pathlib import Path\n"
        "out = Path(sys.argv[sys.argv.index('--outdir') + 1]) / 'a.pdf'\n"
        "out.write_bytes(b'%PDF-1.7 complete')\n",
    )
    error = None
    try:
        result = soffice.convert_one(binary, tmp_path / "a.docx", tmp_path / "pdf")
    except OSError as exc:
        error = exc
    assert error is None, f"fake converter must support interpreter paths with spaces: {error}"
    assert result.ok, result.error
    assert result.pdf.read_bytes() == b"%PDF-1.7 complete"


def test_timeout_kills_descendants_before_they_can_write_a_late_pdf(tmp_path):
    pdf = tmp_path / "pdf" / "a.pdf"
    attempts = tmp_path / "attempts"
    binary = tmp_path / "soffice"
    binary.write_text(
        "#!/bin/sh\n"
        f"(sleep 1; printf '%%PDF-1.7 late' > {shlex.quote(str(pdf))}) >/dev/null 2>&1 &\n"
        f"printf 'started\\n' >> {shlex.quote(str(attempts))}\n"
        "sleep 30\n"
    )
    binary.chmod(0o755)
    result = soffice.convert_one(binary, tmp_path / "a.docx", pdf.parent, timeout=0.3, retries=3)
    assert not result.ok and result.error == "soffice timed out"
    assert result.pdf is None
    assert attempts.read_text() == "started\n"
    time.sleep(1.2)
    assert not pdf.exists(), "timed-out descendants must not write a late PDF"


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
