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
        '<?xml version="1.0"?>',
        f'<w:document xmlns:w="{W}"><w:body>',
    ]
    bits.extend(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
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


def test_a_redline_that_is_not_a_package_fails(tmp_path: Path) -> None:
    """Word's `save as` always writes a package, so anything else is not the pair.

    This used to pass as "not checked", which let a truncated or foreign save
    through both the driver gate and `check_redline_identity.py`.
    """
    base = tmp_path / "a.docx"
    revision = tmp_path / "b.docx"
    _docx(base, ["alpha sentence from the base document only"])
    _docx(revision, ["beta sentence from the revision document only"])
    redline = tmp_path / "a__vs__b.docx"
    redline.write_bytes(b"PK")

    verdict = matches_pair(redline, base, revision)
    assert not verdict.ok
    assert "not a docx package" in verdict.reason
    assert "a__vs__b.docx" in verdict.reason


def test_an_unreadable_source_fails_rather_than_passing(tmp_path: Path) -> None:
    base = tmp_path / "a.docx"
    base.write_bytes(b"not a zip")
    revision = tmp_path / "b.docx"
    _docx(revision, ["beta sentence from the revision document only"])
    redline = tmp_path / "a__vs__b.docx"
    _docx(redline, [], inserted="beta sentence from the revision document only")

    verdict = matches_pair(redline, base, revision)
    assert not verdict.ok
    assert "a.docx" in verdict.reason


def test_a_missing_file_fails_rather_than_raising(tmp_path: Path) -> None:
    base = tmp_path / "a.docx"
    _docx(base, ["alpha"])
    verdict = matches_pair(tmp_path / "gone.docx", base, base)
    assert not verdict.ok
    assert "gone.docx" in verdict.reason


def test_cli_names_why_a_redline_failed_and_exits_1(tmp_path: Path) -> None:
    """Two 0.00 scores alone do not say whether the file was foreign or broken."""
    import subprocess

    a, b, red = tmp_path / "a", tmp_path / "b", tmp_path / "redlines"
    _docx(a / "x.docx", ["alpha sentence from the base document only"])
    _docx(b / "y.docx", ["beta sentence from the revision document only"])
    red.mkdir()
    (red / "x__vs__y.docx").write_bytes(b"PK")

    script = _SCRIPT.with_name("check_redline_identity.py")
    proc = subprocess.run(
        [sys.executable, str(script), "--a", str(a), "--b", str(b), "--redlines", str(red)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1, proc.stderr
    assert "not a docx package: x__vs__y.docx" in proc.stdout
