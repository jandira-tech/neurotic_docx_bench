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


def test_accepting_the_same_input_twice_is_byte_identical(tmp_path):
    """`bench accept` runs on every `--generate`, so a non-deterministic writer rewrites
    the whole accepted corpus with identical CONTENT but a fresh zip container.

    That churned 232 files in `git status` after every generate run — phantom diffs that
    hide real ones and invite committing noise. `pdf_accepted_word` is rendered from these
    and IS pinned in oracle_manifest.json, so the same churn is one re-render away from
    tripping the oracle gate the way `pdf_source` already did.
    """
    src = _a_tracked_redline()
    first = accept_changes.accept_all(src, tmp_path / "a.docx")
    second = accept_changes.accept_all(src, tmp_path / "b.docx")
    assert first.read_bytes() == second.read_bytes()


def test_accept_is_deterministic_across_zip_metadata_not_just_content(tmp_path):
    """Guard the mechanism, not only the symptom: every entry must carry the fixed
    timestamp. A writer that merely happened to run inside the same clock second would
    pass the byte-equality test above while still churning on the next run.
    """
    src = _a_tracked_redline()
    out = accept_changes.accept_all(src, tmp_path / "a.docx")
    with zipfile.ZipFile(out) as z:
        stamps = {i.date_time for i in z.infolist()}
    assert stamps == {accept_changes.FIXED_ZIP_DATE_TIME}


def test_accept_preserves_entry_order_and_payloads(tmp_path):
    """Normalising the container must not reorder or re-encode the package: OPC wants
    [Content_Types].xml first, and a payload change here would silently move the accepted
    ground truth the functional lens compares against.
    """
    src = _a_tracked_redline()
    out = accept_changes.accept_all(src, tmp_path / "a.docx")
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        payloads = {n: z.read(n) for n in names}
    assert names[0] == "[Content_Types].xml"

    # Re-running must reproduce the exact same names in the exact same order.
    again = accept_changes.accept_all(src, tmp_path / "b.docx")
    with zipfile.ZipFile(again) as z:
        assert z.namelist() == names
        assert {n: z.read(n) for n in z.namelist()} == payloads


def test_reject_is_deterministic_too(tmp_path):
    src = _a_tracked_redline()
    first = accept_changes.reject_all(src, tmp_path / "a.docx")
    second = accept_changes.reject_all(src, tmp_path / "b.docx")
    assert first.read_bytes() == second.read_bytes()
