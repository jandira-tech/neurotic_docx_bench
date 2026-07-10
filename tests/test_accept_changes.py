"""accept/reject tracked changes via docx-revisions."""

from __future__ import annotations

import zipfile

import pytest
from helpers import CORPUS
from typer.testing import CliRunner

from neurotic_docx_bench import accept_changes
from neurotic_docx_bench.cli import app

runner = CliRunner()
REDLINES = CORPUS / "docx_redlines_word"


def _document_xml(docx_path) -> str:
    with zipfile.ZipFile(docx_path) as z:
        return z.read("word/document.xml").decode("utf-8", errors="ignore")


def _a_tracked_redline():
    """A corpus redline DOCX that actually contains tracked changes."""
    if not REDLINES.is_dir():
        pytest.skip("redline corpus absent")
    for docx in sorted(REDLINES.glob("*_redline.docx")):
        xml = _document_xml(docx)
        if "<w:ins" in xml or "<w:del" in xml:
            return docx
    pytest.skip("no redline docx with tracked changes found")


def test_accept_all_removes_tracked_changes(tmp_path):
    src = _a_tracked_redline()
    out = accept_changes.accept_all(src, tmp_path / "accepted.docx")
    assert out.exists()
    xml = _document_xml(out)
    # accepting removes the tracked-change wrappers (insertions kept as plain runs,
    # deletions dropped) → no <w:ins>/<w:del> remain
    assert "<w:ins" not in xml
    assert "<w:del" not in xml


def test_reject_all_removes_tracked_changes(tmp_path):
    src = _a_tracked_redline()
    out = accept_changes.reject_all(src, tmp_path / "rejected.docx")
    assert out.exists()
    xml = _document_xml(out)
    assert "<w:ins" not in xml
    assert "<w:del" not in xml


def test_process_folder(tmp_path):
    src = _a_tracked_redline()
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    import shutil

    shutil.copy(src, in_dir / src.name)
    results = accept_changes.process_folder(in_dir, tmp_path / "out")
    assert len(results) == 1 and results[0].ok
    assert (tmp_path / "out" / src.name).exists()


def test_cli_accept(tmp_path):
    src = _a_tracked_redline()
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    import shutil

    shutil.copy(src, in_dir / src.name)
    result = runner.invoke(app, ["accept", str(in_dir), "--out", str(tmp_path / "acc")])
    assert result.exit_code == 0, result.output
    assert "accepted" in result.output


def test_process_folder_validates_dir_and_skips_temp(tmp_path):
    import pytest as _pt

    with _pt.raises(NotADirectoryError):
        accept_changes.process_folder(tmp_path / "nope", tmp_path / "out")
    # ~$ Word lock files are skipped
    in_dir = tmp_path / "in"
    in_dir.mkdir()
    (in_dir / "~$lock.docx").write_bytes(b"PK")
    results = accept_changes.process_folder(in_dir, tmp_path / "out2")
    assert results == []
