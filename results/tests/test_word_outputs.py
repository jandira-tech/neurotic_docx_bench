"""Finding what Word's drivers wrote: manifest first, then the name conventions."""

from __future__ import annotations

import json
from pathlib import Path

from neurotic_docx_bench import word_outputs
from neurotic_docx_bench.word_outputs import current_name, find_output, read_manifest


def _manifest(folder: Path, *lines: dict) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "manifest.jsonl").open("a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")


def test_read_manifest_is_empty_without_a_file_and_skips_a_torn_line(tmp_path: Path) -> None:
    assert read_manifest(tmp_path) == []
    _manifest(tmp_path, {"a": 1})
    (tmp_path / "manifest.jsonl").open("a").write('{"b": \n')
    assert read_manifest(tmp_path) == [{"a": 1}]


def test_current_name_follows_renames() -> None:
    lines = [
        {"status": "renamed", "original_filename": "long.docx", "converted_filename": "short.docx"},
        {"status": "ok", "original_filename": "short.docx", "converted_filename": "short_byword.pdf"},
    ]
    assert current_name(lines, "long.docx") == "short.docx"
    assert current_name(lines, "short.docx") == "short.docx"
    assert current_name(lines, "other.docx") == "other.docx"


def test_find_output_prefers_the_newest_manifest_line_that_still_exists(tmp_path: Path) -> None:
    old = tmp_path / "a_byword.pdf"
    old.write_bytes(b"%PDF old")
    gone = tmp_path / "elsewhere.pdf"
    _manifest(
        tmp_path,
        {"status": "ok", "kind": "pdf", "original_filename": "a.docx", "path_out": str(old)},
        {"status": "ok", "kind": "pdf", "original_filename": "a.docx", "path_out": str(gone)},
        {"status": "failed", "kind": "pdf", "original_filename": "a.docx", "path_out": ""},
        {"status": "ok", "kind": "accept_all", "original_filename": "a.docx", "path_out": str(tmp_path / "x.pdf")},
    )
    assert find_output(tmp_path, "a.docx", kind="pdf", ext=".pdf") == old


def test_find_output_resolves_a_trimmed_name_through_the_rename_line(tmp_path: Path) -> None:
    long_name = "deal_" + "x" * 100 + ".docx"
    out = tmp_path / "deal_xxxx_1234abcd_byword.pdf"
    out.write_bytes(b"%PDF")
    _manifest(
        tmp_path,
        {"status": "renamed", "original_filename": long_name, "converted_filename": "deal_xxxx_1234abcd.docx"},
        {"status": "ok", "kind": "pdf", "original_filename": "deal_xxxx_1234abcd.docx", "path_out": str(out)},
    )
    assert find_output(tmp_path, long_name, kind="pdf", ext=".pdf") == out
    # and by name alone once the manifest line is gone
    (tmp_path / "manifest.jsonl").unlink()
    _manifest(tmp_path, {"status": "renamed", "original_filename": long_name, "converted_filename": "deal_xxxx_1234abcd.docx"})
    assert find_output(tmp_path, long_name, kind="pdf", ext=".pdf") == out


def test_find_output_falls_back_to_new_then_old_spelling(tmp_path: Path) -> None:
    assert find_output(tmp_path, "a.docx", kind="pdf", ext=".pdf") is None
    (tmp_path / "a.pdf").write_bytes(b"%PDF old spelling")
    assert find_output(tmp_path, "a.docx", kind="pdf", ext=".pdf") == tmp_path / "a.pdf"
    (tmp_path / "a_byword.pdf").write_bytes(b"%PDF")
    assert find_output(tmp_path, "a.docx", kind="pdf", ext=".pdf") == tmp_path / "a_byword.pdf"
    (tmp_path / "a_accepted_tracking_byword.docx").write_bytes(b"PK")
    assert (
        find_output(tmp_path, "a.docx", kind="accept_all", ext=".docx", suffix="_accepted_tracking")
        == tmp_path / "a_accepted_tracking_byword.docx"
    )
    assert word_outputs.BY_WORD == "_byword"
