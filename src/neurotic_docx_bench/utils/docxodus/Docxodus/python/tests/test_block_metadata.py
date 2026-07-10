"""Coverage for the block-metadata read surface on DocxSession.

Mirrors the BM00x .NET tests in spirit but exercises the Python wrapper end-to-end
through the stdio host. Uses the shared ``test_files_dir`` fixture from
``conftest.py`` to locate the byte-identical TestFiles corpus.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

from docx_scalpel import DocxSession, open_session
from docx_scalpel.types import BlockMetadata, NumberFormat


@pytest.fixture
def list_session(test_files_dir: Path) -> Iterator[DocxSession]:
    fixture = test_files_dir / "DB012-Lists-With-Different-Numberings.docx"
    if not fixture.exists():
        pytest.skip(f"fixture missing: {fixture}")
    session = open_session(fixture.read_bytes())
    try:
        yield session
    finally:
        session.close()


def _first_anchor_of_kind(session: DocxSession, kind: str):
    projection = session.project()
    for anchor in projection.anchor_index.values():
        if anchor.kind == kind:
            return anchor
    return None


def test_get_block_metadata_plain_paragraph(list_session: DocxSession) -> None:
    para = _first_anchor_of_kind(list_session, "p")
    if para is None:
        pytest.skip("fixture has no plain paragraph anchors")
    meta = list_session.get_block_metadata(para.id)
    assert isinstance(meta, BlockMetadata)
    assert meta.kind == "p"
    assert meta.scope == "body"


def test_get_block_metadata_unknown_anchor_returns_none(list_session: DocxSession) -> None:
    assert list_session.get_block_metadata("p:body:does-not-exist") is None


def test_get_block_metadatas_bulk_dedups(list_session: DocxSession) -> None:
    para = _first_anchor_of_kind(list_session, "p")
    if para is None:
        pytest.skip("fixture has no plain paragraph anchors")
    result = list_session.get_block_metadatas([para.id, para.id, "p:body:missing"])
    assert len(result) == 2
    assert result[para.id] is not None
    assert result["p:body:missing"] is None


def test_get_list_membership_li_anchor(list_session: DocxSession) -> None:
    li = _first_anchor_of_kind(list_session, "li")
    if li is None:
        pytest.skip("fixture has no list-item anchors")
    membership = list_session.get_list_membership(li.id)
    assert membership is not None
    assert membership.num_id > 0
    assert membership.level >= 0
    assert isinstance(membership.format, NumberFormat)


def test_get_section_info_body_anchor(list_session: DocxSession) -> None:
    para = _first_anchor_of_kind(list_session, "p")
    if para is None:
        para = _first_anchor_of_kind(list_session, "li")
    if para is None:
        pytest.skip("fixture has no body anchors")
    info = list_session.get_section_info(para.id)
    assert info is not None
    assert info.page_width_twips > 0
    assert info.columns >= 1
