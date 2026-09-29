"""results/redlines_0928/provenance.py: every Word-made file finds the tool redline it came from."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "redlines_0928_provenance",
    Path(__file__).resolve().parent.parent / "results" / "redlines_0928" / "provenance.py",
)
provenance = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(provenance)


@pytest.mark.parametrize("action", ["accepted", "rejected"])
def test_source_for_matches_word_accept_and_reject_outputs(tmp_path: Path, action: str):
    src = tmp_path / "src"
    src.mkdir()
    (src / "1855b51281.docx").write_bytes(b"x")
    (src / "29aa0f0e11.docx").write_bytes(b"x")
    for suffix in (".docx", ".pdf"):
        made = tmp_path / f"1855b51281_{action}_tracking_jubarte-rust{suffix}"
        assert provenance.source_for(made, src, "jubarte-rust") == src / "1855b51281.docx"


def test_source_for_plain_word_pdf_of_a_redline(tmp_path: Path):
    src = tmp_path / "docx"
    src.mkdir()
    (src / "k1_jubarte-rust.docx").write_bytes(b"x")
    assert provenance.source_for(tmp_path / "k1_jubarte-rust.pdf", src, "jubarte-rust") == src / "k1_jubarte-rust.docx"
