"""The identity check catches a redline that is actually a different document."""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "redline_identity.py"
_spec = importlib.util.spec_from_file_location("redline_identity", _SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
sys.modules["redline_identity"] = _mod
_spec.loader.exec_module(_mod)
matches_pair = _mod.matches_pair

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _docx(path: Path, paragraphs: list[str], *, deleted: str = "", inserted: str = "") -> None:
    bits = [
        f'<?xml version="1.0"?>',
        f'<w:document xmlns:w="{W}"><w:body>',
    ]
    for text in paragraphs:
        bits.append(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>")
    if deleted:
        bits.append(f"<w:p><w:del><w:r><w:delText>{deleted}</w:delText></w:r></w:del></w:p>")
    if inserted:
        bits.append(f"<w:p><w:ins><w:r><w:t>{inserted}</w:t></w:r></w:ins></w:p>")
    bits.append("</w:body></w:document>")
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as package:
        package.writestr("word/document.xml", "".join(bits))


def test_real_redline_matches_its_pair(tmp_path: Path) -> None:
    base = tmp_path / "a.docx"
    revision = tmp_path / "b.docx"
    redline = tmp_path / "a__vs__b.docx"
    _docx(base, ["alpha sentence from the base document only"])
    _docx(revision, ["beta sentence from the revision document only"])
    _docx(
        redline,
        [],
        deleted="alpha sentence from the base document only",
        inserted="beta sentence from the revision document only",
    )
    verdict = matches_pair(redline, base, revision)
    assert verdict.ok
    assert verdict.sim_base > 0.9
    assert verdict.sim_revision > 0.9


def test_small_word_rewrite_still_matches(tmp_path: Path) -> None:
    """Word may add a checkbox or a page mark. That is not a swapped file."""
    base = tmp_path / "a.docx"
    revision = tmp_path / "b.docx"
    redline = tmp_path / "redline.docx"
    _docx(base, ["the committee met on tuesday and approved the minutes of may"])
    _docx(revision, ["the committee met on wednesday and approved the minutes of june"])
    _docx(
        redline,
        [],
        deleted="the committee met on tuesday and approved the minutes of may",
        inserted="the committee met on wednesday and approved the minutes of june ☐",
    )
    assert matches_pair(redline, base, revision).ok


def test_foreign_document_saved_under_this_name_is_rejected(tmp_path: Path) -> None:
    """The failure Word produced: before and after are some other file entirely."""
    base = tmp_path / "a.docx"
    revision = tmp_path / "b.docx"
    foreign = tmp_path / "z.docx"
    redline = tmp_path / "a__vs__b.docx"
    _docx(base, ["Kolmastoista pykälä koskee vain kunnan talousarviota vuodelle 2024"])
    _docx(revision, ["Article fourteen covers the harbour dues payable at Lowestoft"])
    _docx(foreign, ["Achensee Tourismus Presse Info Ballonfahren Tirol Maurach"])
    _docx(redline, ["Achensee Tourismus Presse Info Ballonfahren Tirol Maurach"])
    verdict = matches_pair(redline, base, revision)
    assert not verdict.ok
    assert verdict.sim_base < 0.5
    assert verdict.sim_revision < 0.5


def test_placeholder_bytes_are_not_rejected(tmp_path: Path) -> None:
    """Driver tests plant a PK marker where Word has not actually saved."""
    base = tmp_path / "a.docx"
    revision = tmp_path / "b.docx"
    redline = tmp_path / "redline.docx"
    _docx(base, ["alpha"])
    _docx(revision, ["beta"])
    redline.write_bytes(b"PK")
    assert matches_pair(redline, base, revision).ok
