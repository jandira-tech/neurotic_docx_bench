"""Functional accept/reject invariant (PR7): any correct redline, whatever it looks
like, must satisfy accept(candidate) ≡ next and reject(candidate) ≡ base.

The pixel lens cannot tell a real tracked change from paint: a candidate that emits
plain text styled red-with-strikethrough (no w:ins/w:del) scores near-perfect
visually. The functional lens accepts/rejects the candidate with the bench's own
neutral machinery (docx-revisions — NOT the tool's own accept, which masks the
tool's own defects) and compares extracted text against the next/base sources.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from neurotic_docx_bench import functional_lens

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
    "</Relationships>"
)


def _p(content: str) -> str:
    return f"<w:p>{content}</w:p>"


def _run(text: str) -> str:
    return f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'


def _ins(text: str) -> str:
    return f'<w:ins w:id="1" w:author="t" w:date="2026-01-01T00:00:00Z">{_run(text)}</w:ins>'


def _del(text: str) -> str:
    return (
        f'<w:del w:id="2" w:author="t" w:date="2026-01-01T00:00:00Z">'
        f'<w:r><w:delText xml:space="preserve">{text}</w:delText></w:r></w:del>'
    )


def _docx(path: Path, body_paragraphs: list[str]) -> Path:
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>'
        + "".join(body_paragraphs)
        + "<w:sectPr/></w:body></w:document>"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", document)
    return path


def _fixtures(tmp_path: Path) -> dict[str, Path]:
    base = _docx(tmp_path / "base.docx", [_p(_run("Alpha stays.")), _p(_run("Bravo goes."))])
    next_ = _docx(tmp_path / "next.docx", [_p(_run("Alpha stays.")), _p(_run("Charlie arrives."))])
    good = _docx(
        tmp_path / "good.docx",
        [_p(_run("Alpha stays.")), _p(_del("Bravo goes.") + _ins("Charlie arrives."))],
    )
    # The gaming case: final text with NO revision marks — visually identical to a
    # redline when styled, functionally inert.
    flattened = _docx(
        tmp_path / "flat.docx", [_p(_run("Alpha stays.")), _p(_run("Charlie arrives."))],
    )
    truncated = _docx(tmp_path / "trunc.docx", [_p(_run("Alpha stays."))])
    return {"base": base, "next": next_, "good": good, "flat": flattened, "trunc": truncated}


def test_extract_body_text_drops_empty_paragraphs(tmp_path: Path) -> None:
    d = _docx(tmp_path / "x.docx", [_p(_run("One")), _p(""), _p(_run("Two"))])
    assert functional_lens.extract_body_text(d) == ["One", "Two"]


def test_extract_body_text_counts_nested_textbox_paragraph_once(tmp_path: Path) -> None:
    # A text box (w:txbxContent) nests its own w:p INSIDE a run of an outer w:p.
    # Naive body.iter(w:p) yields both outer and inner, double-counting the boxed
    # text (7 corpus source docs contain text boxes). Only top-level paragraphs
    # count; a nested paragraph's text belongs to its outer paragraph.
    inner = "<w:r><w:pict><w:txbxContent>" + _p(_run("Boxed")) + "</w:txbxContent></w:pict></w:r>"
    d = _docx(tmp_path / "tb.docx", [_p(_run("Outer ") + inner), _p(_run("After"))])
    assert functional_lens.extract_body_text(d) == ["Outer Boxed", "After"]


def test_extract_body_text_strict_namespace(tmp_path: Path) -> None:
    # Strict OOXML uses a different w namespace; hardcoding the transitional one
    # silently extracted [] for strict docs (4 corpus files), letting an empty
    # candidate pass both invariants. Extraction must follow the document's own ns.
    strict_ns = "http://purl.oclc.org/ooxml/wordprocessingml/main"
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{strict_ns}"><w:body>'
        '<w:p><w:r><w:t xml:space="preserve">Strict text</w:t></w:r></w:p>'
        "<w:sectPr/></w:body></w:document>"
    )
    path = tmp_path / "strict.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", document)
    assert functional_lens.extract_body_text(path) == ["Strict text"]


def test_extract_body_text_no_body_raises(tmp_path: Path) -> None:
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"/>'
    )
    path = tmp_path / "nobody.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("_rels/.rels", _RELS)
        zf.writestr("word/document.xml", document)
    import pytest

    with pytest.raises(ValueError, match="body"):
        functional_lens.extract_body_text(path)


def test_extract_body_text_skips_mc_fallback(tmp_path: Path) -> None:
    # mc:AlternateContent carries the same content in Choice AND Fallback; Word
    # renders exactly one alternative. Extracting both double-counts (confirmed on
    # corpus alternate_content.docx). Prefer Choice, skip Fallback.
    mc_ns = "http://schemas.openxmlformats.org/markup-compatibility/2006"
    alt = (
        f'<w:r><mc:AlternateContent xmlns:mc="{mc_ns}">'
        f"<mc:Choice>{_run('Choice text')}</mc:Choice>"
        f"<mc:Fallback>{_run('Fallback text')}</mc:Fallback>"
        "</mc:AlternateContent></w:r>"
    )
    d = _docx(tmp_path / "alt.docx", [_p(alt)])
    assert functional_lens.extract_body_text(d) == ["Choice text"]


def test_blind_pair_flagged(tmp_path: Path) -> None:
    # Formatting-only pair: base and next carry IDENTICAL text, so the text lens
    # has zero discriminating power — a painted candidate would pass both
    # invariants. Such docs must be flagged blind and excluded from the counts.
    base = _docx(tmp_path / "b.docx", [_p(_run("Same text."))])
    next_ = _docx(tmp_path / "n.docx", [_p(_run("Same text."))])
    cand = _docx(tmp_path / "c.docx", [_p(_run("Same text."))])
    v = functional_lens.check_functional(cand, base, next_, tmp_path / "wb")
    assert v.blind is True
    assert v.accept_ok is True  # still computed, just carries no signal


def test_not_blind_on_real_change(tmp_path: Path) -> None:
    f = _fixtures(tmp_path)
    v = functional_lens.check_functional(f["good"], f["base"], f["next"], tmp_path / "wnb")
    assert v.blind is False


def test_both_sources_empty_is_error(tmp_path: Path) -> None:
    base = _docx(tmp_path / "eb.docx", [_p("")])
    next_ = _docx(tmp_path / "en.docx", [_p("")])
    cand = _docx(tmp_path / "ec.docx", [_p("")])
    v = functional_lens.check_functional(cand, base, next_, tmp_path / "we")
    assert v.accept_ok is None
    assert v.reject_ok is None
    assert v.error


def test_correct_redline_passes_both_invariants(tmp_path: Path) -> None:
    f = _fixtures(tmp_path)
    v = functional_lens.check_functional(f["good"], f["base"], f["next"], tmp_path / "w1")
    assert v.accept_ok is True
    assert v.reject_ok is True
    assert v.error is None


def test_flattened_candidate_fails_reject(tmp_path: Path) -> None:
    f = _fixtures(tmp_path)
    v = functional_lens.check_functional(f["flat"], f["base"], f["next"], tmp_path / "w2")
    assert v.accept_ok is True  # accept-all of no-revisions == its own text == next
    assert v.reject_ok is False  # reject-all == same text != base → caught
    assert v.error is None


def test_truncated_candidate_fails_both(tmp_path: Path) -> None:
    f = _fixtures(tmp_path)
    v = functional_lens.check_functional(f["trunc"], f["base"], f["next"], tmp_path / "w3")
    assert v.accept_ok is False
    assert v.reject_ok is False


def test_corrupt_candidate_reports_error(tmp_path: Path) -> None:
    f = _fixtures(tmp_path)
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"not a zip")
    v = functional_lens.check_functional(bad, f["base"], f["next"], tmp_path / "w4")
    assert v.accept_ok is None
    assert v.reject_ok is None
    assert v.error


def test_text_equality_levels() -> None:
    # strict: paragraph lists equal; text: whitespace-collapsed join equal — tolerant
    # of the documented accept_changes paragraph-merge limitation.
    assert functional_lens.texts_equal(["A B"], ["A B"]) == (True, True)
    assert functional_lens.texts_equal(["A", "B"], ["A B"]) == (False, True)
    assert functional_lens.texts_equal(["A", "B"], ["A", "C"]) == (False, False)


def test_check_folder_serial_matches_single(tmp_path: Path) -> None:
    f = _fixtures(tmp_path)
    tasks = [
        ("good", f["good"], f["base"], f["next"], tmp_path / "cf" / "good"),
        ("flat", f["flat"], f["base"], f["next"], tmp_path / "cf" / "flat"),
    ]
    verdicts = functional_lens.check_folder(tasks, jobs=1)
    assert verdicts["good"].accept_ok is True
    assert verdicts["good"].reject_ok is True
    assert verdicts["flat"].reject_ok is False


def test_functional_counts_on_results() -> None:
    from neurotic_docx_bench.results_schema import _functional_counts

    per_doc = {
        "a": {"functional_accept_ok": True, "functional_reject_ok": True},
        "b": {"functional_accept_ok": True, "functional_reject_ok": False},
        "crashed": {"functional_accept_ok": None, "functional_reject_ok": None},
        "unchecked": {"overall_score": 90.0},
        "blind": {
            "functional_accept_ok": True,
            "functional_reject_ok": True,
            "functional_blind": True,
        },
    }
    # blind docs carry no signal (base ≡ next at text level) and are excluded
    assert _functional_counts(per_doc) == (2, 2, 1)
    assert _functional_counts({"x": {"overall_score": 1.0}}) == (None, None, None)
    assert _functional_counts(None) == (None, None, None)


def test_resolve_source_docx_from_mapping(tmp_path: Path) -> None:
    csv = tmp_path / "map.csv"
    csv.write_text(
        "pair_stem,base,next\nAlpha_Beta,Alpha,Beta\nmissing_pair,Nope,Alpha\n",
    )
    src = tmp_path / "docx_source"
    src.mkdir()
    (src / "Alpha.docx").write_bytes(b"x")
    (src / "Beta.docx").write_bytes(b"x")
    resolved = functional_lens.resolve_source_docx([csv], [src])
    assert resolved == {"alpha_beta": (src / "Alpha.docx", src / "Beta.docx")}
