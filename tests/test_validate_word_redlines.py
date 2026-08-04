"""Validation of Word-produced redlines (plan Chapter 2.3, teaching doc §5)."""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_word_redlines.py"


def _load():
    spec = importlib.util.spec_from_file_location("validate_word_redlines", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["validate_word_redlines"] = mod
    spec.loader.exec_module(mod)
    return mod


vwr = _load()

_DOC = (
    '<?xml version="1.0"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    "<w:body>{}</w:body></w:document>"
)


def _docx(path: Path, body: str) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", _DOC.format(body))
    return path


def test_redline_with_tracked_changes_is_ok(tmp_path: Path):
    p = _docx(tmp_path / "a.docx", '<w:ins w:id="1"><w:r><w:t>hi</w:t></w:r></w:ins>')
    result = vwr.validate_one(p)
    assert result.status == "ok"
    assert result.insertions == 1
    assert len(result.sha256) == 64


def test_redline_with_only_deletions_is_ok(tmp_path: Path):
    p = _docx(tmp_path / "a.docx", '<w:del w:id="2"><w:r><w:delText>x</w:delText></w:r></w:del>')
    result = vwr.validate_one(p)
    assert result.status == "ok"
    assert result.deletions == 1


def test_redline_without_tracked_changes_is_empty_not_ok(tmp_path: Path):
    """A change-free 'redline' is a compare that silently did nothing. It opens
    fine and looks valid, so nothing downstream would catch it — but as ground
    truth it is worthless, and it would score every tool against a blank."""
    p = _docx(tmp_path / "a.docx", "<w:p><w:r><w:t>unchanged</w:t></w:r></w:p>")
    result = vwr.validate_one(p)
    assert result.status == "empty_redline"


def test_format_only_revision_is_ok_not_empty(tmp_path: Path):
    """The corpus is compared with `detect format changes` ON. A pair that
    differs only in formatting produces *PrChange revisions and NO w:ins/w:del —
    exactly the ground truth the flag was enabled for. Counting only ins/del
    would throw those pairs away as empty."""
    body = (
        "<w:p><w:pPr><w:rPr>"
        '<w:rPrChange w:id="7" w:author="a"><w:rPr><w:b/></w:rPr></w:rPrChange>'
        "</w:rPr></w:pPr><w:r><w:t>same words, new font</w:t></w:r></w:p>"
    )
    result = vwr.validate_one(_docx(tmp_path / "a.docx", body))
    assert result.status == "ok"
    assert result.insertions == 0
    assert result.deletions == 0
    assert result.format_changes == 1


def test_every_format_change_element_kind_counts(tmp_path: Path):
    """Word emits a different *PrChange per object kind; missing one silently
    under-counts revisions for whole categories of document (tables especially)."""
    kinds = ("rPrChange", "pPrChange", "tblPrChange", "trPrChange", "tcPrChange", "sectPrChange", "tblGridChange")
    body = "".join(f'<w:{k} w:id="{i}"/>' for i, k in enumerate(kinds))
    result = vwr.validate_one(_docx(tmp_path / "a.docx", body))
    assert result.format_changes == len(kinds)
    assert result.status == "ok"


def test_missing_file_is_reported_not_raised(tmp_path: Path):
    result = vwr.validate_one(tmp_path / "nope.docx")
    assert result.status == "missing"


def test_corrupt_zip_is_reported(tmp_path: Path):
    p = tmp_path / "bad.docx"
    p.write_bytes(b"this is not a zip archive")
    result = vwr.validate_one(p)
    assert result.status == "corrupt_zip"


def test_docx_without_document_xml_is_reported(tmp_path: Path):
    p = tmp_path / "nodoc.docx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
    result = vwr.validate_one(p)
    assert result.status == "no_document_xml"


def test_sha256_matches_file_content(tmp_path: Path):
    import hashlib

    p = _docx(tmp_path / "a.docx", '<w:ins w:id="1"><w:r><w:t>hi</w:t></w:r></w:ins>')
    assert vwr.validate_one(p).sha256 == hashlib.sha256(p.read_bytes()).hexdigest()


def test_counts_ignore_unrelated_elements_that_share_a_prefix(tmp_path: Path):
    """`w:insideH` starts with `w:ins` — a substring count would treat table
    border definitions as tracked insertions and pass an empty redline."""
    body = "<w:tblBorders><w:insideH w:val=\"single\"/><w:insideV w:val=\"single\"/></w:tblBorders>"
    result = vwr.validate_one(_docx(tmp_path / "a.docx", body))
    assert result.insertions == 0
    assert result.status == "empty_redline"
