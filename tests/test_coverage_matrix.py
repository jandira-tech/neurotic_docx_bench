"""Coverage matrix (PR10): feature/revision tagging on tiny synthetic DOCX.

Every fixture docx is built in-test via zipfile (minimal [Content_Types].xml +
word/document.xml) — the real corpus is never touched.
"""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from neurotic_docx_bench.coverage_matrix import (
    KNOWN_FEATURES,
    KNOWN_REVISIONS,
    build_coverage,
    render_markdown,
    tag_oracle_revisions,
    tag_source_docx,
)

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"

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


def make_docx(path: Path, body: str = "<w:p><w:r><w:t>plain</w:t></w:r></w:p>") -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", _CONTENT_TYPES)
        zf.writestr("word/document.xml", _document_xml(body))
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
    assert "skipped" not in coverage["errors"]  # MISSING rows are skipped silently


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
