"""Coverage matrix (PR10): feature/revision tagging on tiny synthetic DOCX.

Every fixture docx is built in-test via zipfile (minimal [Content_Types].xml +
word/document.xml) — the real corpus is never touched.
"""

from __future__ import annotations

import csv
import json
import zipfile
from pathlib import Path

from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.coverage_matrix import (
    KNOWN_FEATURES,
    KNOWN_REVISIONS,
    build_coverage,
    latest_scores_by_vendor,
    render_markdown,
    tag_oracle_revisions,
    tag_source_docx,
    unjoined_score_keys,
)

runner = CliRunner()

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_W_STRICT_NS = "http://purl.oclc.org/ooxml/wordprocessingml/main"
_M_STRICT_NS = "http://purl.oclc.org/ooxml/officeDocument/math"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-'
    'officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_TBL = "<w:tbl><w:tr><w:tc><w:p/></w:tc></w:tr></w:tbl>"
_NESTED_TBL = f"<w:tbl><w:tr><w:tc>{_TBL}</w:tc></w:tr></w:tbl>"
_INS = '<w:p><w:ins w:id="1" w:author="a"><w:r><w:t>added</w:t></w:r></w:ins></w:p>'
_DEL = '<w:p><w:del w:id="2" w:author="a"><w:r><w:delText>gone</w:delText></w:r></w:del></w:p>'


def _document_xml(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}" xmlns:mc="{_MC_NS}">'
        f"<w:body>{body}</w:body></w:document>"
    )


def make_docx(
    path: Path,
    body: str = "<w:p><w:r><w:t>plain</w:t></w:r></w:p>",
    footnotes: str | None = None,
) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("word/document.xml", _document_xml(body))
        if footnotes is not None:
            zf.writestr("word/footnotes.xml", footnotes)
    return path


def _strict_document_xml(body: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_STRICT_NS}" xmlns:m="{_M_STRICT_NS}" xmlns:mc="{_MC_NS}">'
        f"<w:body>{body}</w:body></w:document>"
    )


def make_strict_docx(path: Path, body: str) -> Path:
    """Strict OOXML fixture: w:/m: bound to the purl.oclc.org namespace family."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("word/document.xml", _strict_document_xml(body))
    return path


def write_mapping(path: Path, rows: list[dict[str, str]]) -> Path:
    columns = [
        "pair_stem", "base", "next",
        "docx_source_base", "docx_source_next",
        "redline_docx", "redline_docx_word",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=columns)
        writer.writeheader()
        writer.writerows([{c: row.get(c, "") for c in columns} for row in rows])
    return path


def test_table_not_nested(tmp_path: Path) -> None:
    tags = tag_source_docx(make_docx(tmp_path / "t.docx", _TBL))
    assert "table" in tags
    assert "nested_table" not in tags


def test_nested_table(tmp_path: Path) -> None:
    tags = tag_source_docx(make_docx(tmp_path / "t.docx", _NESTED_TBL))
    assert {"table", "nested_table"} <= tags


def test_content_control(tmp_path: Path) -> None:
    body = "<w:sdt><w:sdtContent><w:p/></w:sdtContent></w:sdt>"
    assert "content_control" in tag_source_docx(make_docx(tmp_path / "t.docx", body))


def test_alternate_content(tmp_path: Path) -> None:
    body = '<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"/><mc:Fallback/></mc:AlternateContent></w:r></w:p>'
    assert "alternate_content" in tag_source_docx(make_docx(tmp_path / "t.docx", body))


def test_cjk(tmp_path: Path) -> None:
    tags = tag_source_docx(make_docx(tmp_path / "t.docx", "<w:p><w:r><w:t>漢字テキスト</w:t></w:r></w:p>"))
    assert "cjk" in tags


def test_strict_namespace_features(tmp_path: Path) -> None:
    body = (
        _TBL
        + "<w:sdt><w:sdtContent><w:p/></w:sdtContent></w:sdt>"
        + "<w:p><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></w:p>"
    )
    tags = tag_source_docx(make_strict_docx(tmp_path / "s.docx", body))
    assert {"table", "content_control", "math"} <= tags
    assert "nested_table" not in tags


def test_strict_namespace_nested_table_and_sections(tmp_path: Path) -> None:
    body = _NESTED_TBL + "<w:p><w:pPr><w:sectPr/></w:pPr></w:p><w:sectPr/>"
    tags = tag_source_docx(make_strict_docx(tmp_path / "s.docx", body))
    assert {"table", "nested_table", "multi_section"} <= tags


def test_strict_namespace_revisions(tmp_path: Path) -> None:
    assert tag_oracle_revisions(make_strict_docx(tmp_path / "r.docx", _INS + _DEL)) == {"rev_ins", "rev_del"}


def test_rtl_element_without_val_is_on(tmp_path: Path) -> None:
    body = "<w:p><w:pPr><w:bidi/></w:pPr></w:p>"
    assert "rtl" in tag_source_docx(make_docx(tmp_path / "t.docx", body))


def test_rtl_val_zero_is_ltr(tmp_path: Path) -> None:
    body = '<w:p><w:r><w:rPr><w:rtl w:val="0"/></w:rPr><w:t>hi</w:t></w:r></w:p>'
    assert "rtl" not in tag_source_docx(make_docx(tmp_path / "t.docx", body))


def test_bidi_val_false_is_ltr(tmp_path: Path) -> None:
    body = '<w:p><w:pPr><w:bidi w:val="false"/></w:pPr></w:p>'
    assert "rtl" not in tag_source_docx(make_docx(tmp_path / "t.docx", body))


def test_rtl_val_true_is_on(tmp_path: Path) -> None:
    body = '<w:p><w:pPr><w:bidi w:val="1"/></w:pPr></w:p><w:p><w:r><w:rPr><w:rtl w:val="true"/></w:rPr></w:r></w:p>'
    assert "rtl" in tag_source_docx(make_docx(tmp_path / "t.docx", body))


def _footnotes_xml(notes: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:footnotes xmlns:w="{_W_NS}">{notes}</w:footnotes>'
    )


def test_separator_stub_footnotes_not_tagged(tmp_path: Path) -> None:
    notes = (
        '<w:footnote w:type="separator" w:id="-1"><w:p/></w:footnote>'
        '<w:footnote w:type="continuationSeparator" w:id="0"><w:p/></w:footnote>'
        '<w:footnote w:type="continuationNotice" w:id="1"><w:p/></w:footnote>'
    )
    path = make_docx(tmp_path / "t.docx", footnotes=_footnotes_xml(notes))
    assert "footnote" not in tag_source_docx(path)


def test_authored_footnote_tagged(tmp_path: Path) -> None:
    notes = '<w:footnote w:id="2"><w:p><w:r><w:t>note</w:t></w:r></w:p></w:footnote>'
    path = make_docx(tmp_path / "t.docx", footnotes=_footnotes_xml(notes))
    assert "footnote" in tag_source_docx(path)


def test_ins_del_revisions(tmp_path: Path) -> None:
    assert tag_oracle_revisions(make_docx(tmp_path / "r.docx", _INS + _DEL)) == {"rev_ins", "rev_del"}


def test_move_revisions(tmp_path: Path) -> None:
    body = (
        '<w:p><w:moveFrom w:id="3" w:author="a"><w:r><w:t>x</w:t></w:r></w:moveFrom></w:p>'
        '<w:p><w:moveTo w:id="4" w:author="a"><w:r><w:t>x</w:t></w:r></w:moveTo></w:p>'
    )
    assert tag_oracle_revisions(make_docx(tmp_path / "r.docx", body)) == {"rev_moveFrom", "rev_moveTo"}


def test_tbl_change_umbrella(tmp_path: Path) -> None:
    body = (
        "<w:tbl><w:tblPr><w:tblPrChange w:id=\"5\" w:author=\"a\"><w:tblPr/></w:tblPrChange></w:tblPr>"
        "<w:tr><w:tc><w:p/></w:tc></w:tr></w:tbl>"
    )
    tags = tag_oracle_revisions(make_docx(tmp_path / "r.docx", body))
    assert {"rev_tblChange", "rev_tblPrChange"} <= tags


def _corpus(tmp_path: Path) -> tuple[Path, Path, Path]:
    src = tmp_path / "src"
    red = tmp_path / "red"
    src.mkdir()
    red.mkdir()
    make_docx(src / "a.docx")
    make_docx(src / "b.docx", _TBL)
    return tmp_path, src, red


def test_build_coverage_prefers_word_redline(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    make_docx(red / "p_redline.docx", _INS)
    make_docx(red / "p_word_redline.docx", _DEL)
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "p", "base": "a", "next": "b",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx", "redline_docx_word": "p_word_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    assert coverage["errors"] == {}
    assert coverage["pairs"]["p"]["revisions"] == ["rev_del"]  # word redline won
    assert "table" in coverage["pairs"]["p"]["features"]  # union across both sources


def test_corrupt_word_redline_falls_back_to_valid_redline(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    (red / "p_word_redline.docx").write_bytes(b"this is not a zip archive")
    make_docx(red / "p_redline.docx", _INS)
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "p",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx", "redline_docx_word": "p_word_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    assert coverage["errors"] == {}
    assert coverage["pairs"]["p"]["revisions"] == ["rev_ins"]


def test_all_redline_candidates_broken_error_names_both(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    (red / "p_word_redline.docx").write_bytes(b"junk")
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "p",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx", "redline_docx_word": "p_word_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    assert coverage["pairs"] == {}
    error = coverage["errors"]["p"]
    assert "p_word_redline.docx" in error  # the corrupt preferred candidate
    assert "p_redline.docx" in error  # the absent fallback candidate


def test_zero_coverage_lists_absent_known_tags(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    make_docx(red / "p_redline.docx", _INS)
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "p",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    zero = set(coverage["zero_coverage"])
    assert {"rev_moveFrom", "rev_moveTo", "math", "footnote"} <= zero
    assert "table" not in zero
    assert "rev_ins" not in zero
    assert coverage["tag_counts"]["rev_moveFrom"] == 0
    assert coverage["tag_counts"]["table"] == 1
    # every known tag is accounted for in the counts
    assert set(coverage["tag_counts"]) == KNOWN_FEATURES | KNOWN_REVISIONS


def test_missing_and_malformed_docx_recorded_not_raised(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    make_docx(red / "p_redline.docx", _INS)
    (src / "bad.docx").write_bytes(b"this is not a zip archive")
    mapping = write_mapping(root / "map.csv", [
        {
            "pair_stem": "gone",
            "docx_source_base": "does_not_exist.docx", "docx_source_next": "b.docx",
            "redline_docx": "p_redline.docx",
        },
        {
            "pair_stem": "broken",
            "docx_source_base": "bad.docx", "docx_source_next": "b.docx",
            "redline_docx": "p_redline.docx",
        },
        {
            "pair_stem": "skipped",
            "docx_source_base": "MISSING: never generated", "docx_source_next": "b.docx",
            "redline_docx": "p_redline.docx",
        },
        {
            "pair_stem": "ok",
            "docx_source_base": "a.docx", "docx_source_next": "b.docx",
            "redline_docx": "p_redline.docx",
        },
    ])
    coverage = build_coverage([mapping], [src], [red])
    assert set(coverage["pairs"]) == {"ok"}
    assert set(coverage["errors"]) == {"gone", "broken"}
    # MISSING rows are not errors, but they are accounted for, stem and all
    assert set(coverage["skipped"]) == {"skipped"}
    assert "MISSING" in coverage["skipped"]["skipped"]
    md = render_markdown(coverage, None)
    assert "1 skipped" in md


def test_render_markdown_zero_coverage_section(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    make_docx(red / "p_redline.docx", _INS)
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "p",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    md = render_markdown(coverage, None)
    assert "## Zero coverage" in md
    assert "- `rev_moveFrom`" in md
    assert "| `rev_moveFrom` | revision | **0** |" in md  # zero rows bolded
    assert "| `table` | feature | 1 |" in md


def test_render_markdown_vendor_medians(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    make_docx(red / "p_redline.docx", _INS)
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "p",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    md = render_markdown(coverage, {"acme": {"p": 91.5}, "other": {"unrelated": 10.0}})
    assert "## Median score per tag per vendor" in md
    assert "| `table` | 91.5 (n=1) | — |" in md


def test_render_markdown_joins_mixed_case_stems_to_lowercase_scores(tmp_path: Path) -> None:
    """Mapping stems keep casing; bench score keys are lowercased — join must normalize."""
    root, src, red = _corpus(tmp_path)
    make_docx(red / "File_A_File_B_redline.docx", _INS)
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "File_A_File_B",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "File_A_File_B_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    assert "File_A_File_B" in coverage["pairs"]
    scores = {"acme": {"file_a_file_b": 88.0, "MixedCase": 1.0}}
    md = render_markdown(coverage, scores)
    assert "88.0 (n=1)" in md
    # Caller dict must not be mutated.
    assert "MixedCase" in scores["acme"]
    assert "mixedcase" not in scores["acme"]


def test_latest_scores_by_vendor_filters_non_numeric_and_non_finite(tmp_path: Path) -> None:
    p = tmp_path / "bench.jsonl"
    p.write_text(json.dumps({
        "vendor": "acme",
        "benchmark": "script_redlines",
        "scores": {
            "ok": 90.0,
            "string_num": "91.5",
            "bad": "N/A",
            "inf": "Infinity",
            "nan": "NaN",
        },
    }) + "\n")
    out = latest_scores_by_vendor(p)
    assert out["acme"] == {"ok": 90.0, "string_num": 91.5}


def test_latest_scores_by_vendor_empty_clears_stale(tmp_path: Path) -> None:
    p = tmp_path / "bench.jsonl"
    p.write_text(
        json.dumps({"vendor": "acme", "benchmark": "script_redlines", "scores": {"a": 10.0}})
        + "\n"
        + json.dumps({"vendor": "acme", "benchmark": "script_redlines", "scores": {"a": "nope"}})
        + "\n",
    )
    out = latest_scores_by_vendor(p)
    assert out["acme"] == {}


def test_unjoined_score_keys_ignores_case_differences() -> None:
    coverage = {"pairs": {"File_A_File_B": {}}}
    scores_by_vendor = {
        "acme": {"file_a_file_b": 88.0, "unmatched_pair": 75.0},
    }
    unjoined = unjoined_score_keys(coverage, scores_by_vendor)
    assert "file_a_file_b" not in unjoined["acme"]
    assert "unmatched_pair" in unjoined["acme"]


def test_unjoined_score_keys_counted_per_vendor(tmp_path: Path) -> None:
    root, src, red = _corpus(tmp_path)
    make_docx(red / "p_redline.docx", _INS)
    mapping = write_mapping(root / "map.csv", [{
        "pair_stem": "p",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx",
    }])
    coverage = build_coverage([mapping], [src], [red])
    scores = {
        "acme": {"p": 91.5, "p_word": 10.0, "orphan": 5.0},
        "clean": {"p": 50.0},
    }
    assert unjoined_score_keys(coverage, scores) == {
        "acme": ["orphan", "p_word"],
        "clean": [],
    }
    md = render_markdown(coverage, scores)
    assert "2 of 3 score keys" in md  # acme's footnote makes the n column honest
    assert "`p_word`" in md


def _cli_corpus(tmp_path: Path) -> list[str]:
    root, src, red = _corpus(tmp_path)
    make_docx(red / "p_redline.docx", _INS)
    write_mapping(root / "map.csv", [{
        "pair_stem": "p",
        "docx_source_base": "a.docx", "docx_source_next": "b.docx",
        "redline_docx": "p_redline.docx",
    }])
    return [
        "coverage-matrix",
        "--mapping", str(root / "map.csv"),
        "--source-dir", str(src),
        "--redline-dir", str(red),
        "--out-json", str(root / "coverage.json"),
        "--out-md", str(root / "coverage.md"),
    ]


def test_cli_missing_jsonl_is_friendly_error(tmp_path: Path) -> None:
    args = _cli_corpus(tmp_path) + ["--jsonl", str(tmp_path / "nope.jsonl")]
    result = runner.invoke(app, args)
    assert result.exit_code == 2, result.output
    assert "nope.jsonl" in result.output
    assert not isinstance(result.exception, FileNotFoundError)  # no raw traceback


def test_cli_jsonl_unjoined_scores_in_json(tmp_path: Path) -> None:
    jsonl = tmp_path / "bench.jsonl"
    jsonl.write_text(json.dumps({
        "benchmark": "script_redlines",
        "vendor": "acme",
        "scores": {"p": 91.5, "p_word": 10.0},
    }) + "\n")
    args = _cli_corpus(tmp_path) + ["--jsonl", str(jsonl)]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    data = json.loads((tmp_path / "coverage.json").read_text())
    assert data["unjoined_scores"] == {"acme": ["p_word"]}
