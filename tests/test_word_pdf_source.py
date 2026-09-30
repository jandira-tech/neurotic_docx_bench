"""corpus/word state folders are the DOCX→PDF source: pairs, not the pinned lists."""

from __future__ import annotations

from pathlib import Path

import pytest

from neurotic_docx_bench.word_corpus import STATES
from neurotic_docx_bench.word_pdf_source import select_corpus_word_pdfs, word_pdf_from_config

REPO_ROOT = Path(__file__).resolve().parents[1]

MISSING = "df097720f7_file_131"
PRESENT = "0f5a806b4c_file_141__vs__dccd972179_file_142_redline_3d22ad3c37"


def _touch(path: Path, body: bytes = b"x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def _corpus(root: Path) -> None:
    """The example pair, plus a Word PDF with no DOCX and a DOCX with no Word PDF."""
    _touch(root / "with_comments_clean" / "docx" / f"{MISSING}.docx")
    _touch(root / "with_comments_tracking" / "docx" / f"{PRESENT}.docx")
    _touch(root / "with_comments_tracking" / "pdf" / f"{PRESENT}.pdf", b"%PDF-1.4 present")
    _touch(root / "clean" / "pdf" / "orphan_only.pdf", b"%PDF-1.4 orphan")
    _touch(root / "clean" / "docx" / "paired.docx")
    _touch(root / "clean" / "pdf" / "paired.pdf", b"%PDF-1.4 paired")
    _touch(root / "clean" / "pdf_prior" / "paired.pdf", b"%PDF-1.4 old")


def test_conversion_keeps_every_pdf_that_has_a_docx_and_warns_on_the_rest(tmp_path: Path) -> None:
    _corpus(tmp_path)
    selected = select_corpus_word_pdfs(origin="all", root=tmp_path, score_only=False)
    stems = {item.original_stem for item in selected.fixtures}
    assert stems == {PRESENT, "paired"}
    text = "\n".join(selected.warnings)
    assert MISSING in text
    assert "orphan_only" in text
    assert selected.candidates == {}


def test_tracking_example_is_kept_and_the_clean_example_is_only_a_warning(tmp_path: Path) -> None:
    _corpus(tmp_path)
    clean = select_corpus_word_pdfs(origin="with_comments_clean", root=tmp_path)
    assert clean.fixtures == []
    assert MISSING in "\n".join(clean.warnings)
    tracking = select_corpus_word_pdfs(origin="with_comments_tracking", root=tmp_path)
    assert [item.original_stem for item in tracking.fixtures] == [PRESENT]
    assert tracking.fixtures[0].oracle.name == f"{PRESENT}.pdf"
    assert tracking.fixtures[0].docx.name == f"{PRESENT}.docx"
    assert tracking.warnings == []


def test_files_list_requires_origin_list_and_corpus_paths(tmp_path: Path) -> None:
    _corpus(tmp_path)
    docx = tmp_path / "with_comments_tracking" / "docx" / f"{PRESENT}.docx"
    with pytest.raises(ValueError, match="list"):
        select_corpus_word_pdfs(origin="clean", root=tmp_path, files_list=[docx])
    with pytest.raises(ValueError, match="files-list"):
        select_corpus_word_pdfs(origin="list", root=tmp_path, files_list=[])
    outside = tmp_path.parent / "not-in-corpus.docx"
    _touch(outside)
    with pytest.raises(ValueError, match="corpus"):
        select_corpus_word_pdfs(origin="list", root=tmp_path, files_list=[outside])


def test_files_list_accepts_a_corpus_docx_with_a_pdf_or_a_corpus_pdf(tmp_path: Path) -> None:
    _corpus(tmp_path)
    kept = tmp_path / "with_comments_tracking" / "docx" / f"{PRESENT}.docx"
    missing = tmp_path / "with_comments_clean" / "docx" / f"{MISSING}.docx"
    pdf = tmp_path / "clean" / "pdf" / "paired.pdf"
    prior = tmp_path / "clean" / "pdf_prior" / "paired.pdf"
    selected = select_corpus_word_pdfs(
        origin="list", root=tmp_path, files_list=[kept, missing, pdf],
    )
    assert {item.original_stem for item in selected.fixtures} == {PRESENT, "paired"}
    assert MISSING in "\n".join(selected.warnings)
    with pytest.raises(ValueError, match="pdf_prior"):
        select_corpus_word_pdfs(origin="list", root=tmp_path, files_list=[prior])


def test_score_only_keeps_pdfs_that_have_a_pdf_to_score(tmp_path: Path) -> None:
    _corpus(tmp_path)
    location = tmp_path / "scored"
    _touch(location / f"{PRESENT}.pdf", b"%PDF-1.4 cand")
    _touch(location / "paired_jubarte.pdf", b"%PDF-1.4 cand2")
    _touch(location / "nobody.pdf", b"%PDF-1.4 extra")
    with pytest.raises(ValueError, match="location-to-score"):
        select_corpus_word_pdfs(origin="all", root=tmp_path, score_only=True)
    selected = select_corpus_word_pdfs(
        origin="all",
        root=tmp_path,
        score_only=True,
        locations=[location],
        tool="jubarte",
    )
    stems = {item.original_stem for item in selected.fixtures}
    assert stems == {PRESENT, "paired"}
    assert selected.candidates[f"with_comments_tracking__{PRESENT}"].name == f"{PRESENT}.pdf"
    assert selected.candidates["clean__paired"].name == "paired_jubarte.pdf"
    text = "\n".join(selected.warnings)
    assert "orphan_only" in text
    assert "nobody" in text
    assert "orphan_only" not in stems


def test_score_only_location_can_be_specific_pdfs(tmp_path: Path) -> None:
    _corpus(tmp_path)
    cand = _touch(tmp_path / "one" / "paired.pdf", b"%PDF-1.4 cand")
    selected = select_corpus_word_pdfs(
        origin="clean", root=tmp_path, score_only=True, locations=[cand],
    )
    assert [item.original_stem for item in selected.fixtures] == ["paired"]
    assert selected.fixtures[0].docx.name == "paired.docx"


def test_bench_yaml_names_corpus_word_as_the_docx_pdf_source() -> None:
    for name in ("bench.yaml", "bench.smoke1.yaml", "bench.compare.yaml", "bench.randomized.yaml"):
        root, states = word_pdf_from_config(REPO_ROOT / name)
        assert root == REPO_ROOT / "corpus" / "word"
        assert states == STATES


def test_score_only_list_of_corpus_pdfs_does_not_need_the_docx(tmp_path: Path) -> None:
    _corpus(tmp_path)
    oracle = tmp_path / "clean" / "pdf" / "orphan_only.pdf"
    cand = _touch(tmp_path / "cands" / "orphan_only.pdf", b"%PDF-1.4 cand")
    selected = select_corpus_word_pdfs(
        origin="list",
        root=tmp_path,
        files_list=[oracle],
        score_only=True,
        locations=[cand.parent],
    )
    assert [item.original_stem for item in selected.fixtures] == ["orphan_only"]
    assert selected.warnings == []
