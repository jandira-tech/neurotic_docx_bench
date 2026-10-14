"""Output naming (`_byword`), the 80-char input trim, `manifest.jsonl`, and what
`_run_logged` says about a command's output."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from test_word_pdf import _fake_batch_osa, _touch, _verified_session, wp

pytestmark = pytest.mark.usefixtures("no_live_word")

sys.modules.setdefault("word_pdf", wp)


@pytest.fixture(autouse=True)
def _private_word_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "WORD_LOCK_PATH", tmp_path / "word_driver.lock")


def _lines(path: Path) -> list[dict]:
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln]


# ─── _byword ─────────────────────────────────────────────────────────────────


def test_every_word_output_says_word_wrote_it(tmp_path: Path) -> None:
    docx = tmp_path / "in" / "deal.docx"
    assert wp.by_tool("deal") == "deal_byword"
    assert wp.by_tool("deal", "soffice") == "deal_bysoffice"
    assert wp.pdf_path_for(docx, None) == tmp_path / "in" / "deal_byword.pdf"
    assert wp.pdf_path_for(docx, tmp_path / "out") == tmp_path / "out" / "deal_byword.pdf"
    out_docx, out_pdf = wp.accepted_paths_for(docx, tmp_path / "out", "_accepted_tracking")
    assert out_docx == tmp_path / "out" / "deal_accepted_tracking_byword.docx"
    assert out_pdf == tmp_path / "out" / "deal_accepted_tracking_byword.pdf"


def test_existing_output_accepts_the_spelling_before_byword(tmp_path: Path) -> None:
    new = tmp_path / "out" / "deal_byword.pdf"
    old = tmp_path / "out" / "deal.pdf"
    assert wp.legacy_output(new) == old
    assert wp.legacy_output(old) is None, "already the old spelling: nothing older to look for"
    assert wp.existing_output(new) is None
    _touch(old, b"")
    assert wp.existing_output(new) is None, "an empty file is not an output"
    _touch(old, b"%PDF")
    assert wp.existing_output(new) == old
    _touch(new, b"%PDF")
    assert wp.existing_output(new) == new, "the new spelling wins when both exist"


def test_convert_folder_skips_a_pdf_that_exists_under_the_old_name_and_records_that_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """1194 PDFs were on disk as `<stem>.pdf` when the suffix arrived; a run
    must not redo them, and the manifest must say which file it found."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "old.docx")
    _touch(src / "new.docx")
    out = tmp_path / "out"
    _touch(out / "old.pdf", b"%PDF old")
    monkeypatch.setattr(wp, "osa", _fake_batch_osa())
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)

    results = {r.source.name: r for r in wp.convert_folder(src, out, session=session, one_osascript=True)}

    assert results["old.docx"].skipped and results["old.docx"].output == out / "old.pdf"
    assert not (out / "old_byword.pdf").exists(), "not re-rendered"
    assert results["new.docx"].ok and not results["new.docx"].skipped
    assert results["new.docx"].output == out / "new_byword.pdf"
    rows = {r["original_filename"]: r for r in _lines(out / "manifest.jsonl")}
    assert rows["old.docx"]["status"] == "skipped"
    assert rows["old.docx"]["converted_filename"] == "old.pdf"
    assert rows["old.docx"]["path_out"] == str(out / "old.pdf")
    assert rows["new.docx"]["status"] == "ok" and rows["new.docx"]["converted_filename"] == "new_byword.pdf"


def test_serial_path_also_skips_the_old_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "old.docx")
    out = tmp_path / "out"
    _touch(out / "old.pdf", b"%PDF old")
    monkeypatch.setattr(wp, "osa", lambda *a, **k: pytest.fail("Word must not be asked for anything"))
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)

    (r,) = wp.convert_folder(src, out, session=session, one_osascript=False)
    assert r.skipped and r.output == out / "old.pdf"


# ─── 80-char trim ────────────────────────────────────────────────────────────


def test_trim_name_leaves_short_names_alone() -> None:
    assert wp.trim_name("deal.docx") == "deal.docx"
    assert wp.trim_name("x" * 75 + ".docx") == "x" * 75 + ".docx"  # exactly 80


def test_trim_name_cuts_to_the_limit_keeps_the_extension_and_stays_unique() -> None:
    long_a = "a" * 100 + ".docx"
    long_b = "a" * 100 + "b.docx"
    got_a, got_b = wp.trim_name(long_a), wp.trim_name(long_b)
    assert len(got_a) == 80 and len(got_b) == 80
    assert got_a.endswith(".docx") and got_b.endswith(".docx")
    assert got_a != got_b, "two different long names must not collapse into one"
    assert got_a == wp.trim_name(long_a), "deterministic: the same original always trims the same way"
    assert got_a.startswith("a" * 60)


def test_trim_long_names_renames_the_docx_on_disk_and_records_it(tmp_path: Path) -> None:
    src = tmp_path / "src"
    long_name = "contract_" + "x" * 90 + ".docx"
    long_doc = _touch(src / long_name, b"PK long")
    short_doc = _touch(src / "short.docx", b"PK short")
    manifest = tmp_path / "out" / "manifest.jsonl"

    docs = wp.trim_long_names([long_doc, short_doc], manifest)

    assert docs[1] == short_doc
    assert docs[0].parent == src and len(docs[0].name) == 80 and docs[0].name.endswith(".docx")
    assert not long_doc.exists(), "the docx itself is renamed, not copied"
    assert docs[0].read_bytes() == b"PK long"
    assert docs[0].name == wp.trim_name(long_name)
    (row,) = _lines(manifest)
    assert row["status"] == "renamed"
    assert row["original_filename"] == long_name
    assert row["path_origin"] == str(long_doc)
    assert row["converted_filename"] == docs[0].name
    assert row["path_out"] == str(docs[0])


def test_trim_long_names_does_not_overwrite_an_existing_file(tmp_path: Path) -> None:
    src = tmp_path / "src"
    long_name = "contract_" + "y" * 90 + ".docx"
    long_doc = _touch(src / long_name, b"PK long")
    _touch(src / wp.trim_name(long_name), b"PK other")

    docs = wp.trim_long_names([long_doc], None)

    assert docs == [long_doc], "left untouched rather than clobbering the file already there"
    assert long_doc.read_bytes() == b"PK long"


# ─── manifest.jsonl ──────────────────────────────────────────────────────────


def test_append_manifest_appends_one_json_object_per_line(tmp_path: Path) -> None:
    path = tmp_path / "out" / "manifest.jsonl"
    wp.append_manifest(path, [{"a": 1}])
    wp.append_manifest(path, [{"b": "ü"}, {"c": None}])
    assert _lines(path) == [{"a": 1}, {"b": "ü"}, {"c": None}]
    assert "ü" in path.read_text(encoding="utf-8"), "not ascii-escaped"


def test_manifest_lines_cover_ok_failed_skipped_and_every_file_word_wrote(tmp_path: Path) -> None:
    a = tmp_path / "src" / "a.docx"
    b = tmp_path / "src" / "b.docx"
    c = tmp_path / "src" / "c.docx"
    results = [
        wp.Result(source=a, output=tmp_path / "out" / "a_byword.pdf", ok=True, seconds=1.5),
        wp.Result(source=b, error="Word could not read it", seconds=2.0),
        wp.Result(source=c, output=tmp_path / "out" / "c_byword.pdf", ok=True, skipped=True),
        wp.Result(
            source=a,
            output=tmp_path / "out" / "a_accepted_tracking_byword.pdf",
            also=(tmp_path / "out" / "a_accepted_tracking_byword.docx",),
            ok=True,
        ),
    ]
    lines = wp.manifest_lines(results, kind="pdf")
    by = [(ln["original_filename"], ln["status"], ln["converted_filename"], ln["path_out"]) for ln in lines]
    assert by == [
        ("a.docx", "ok", "a_byword.pdf", str(tmp_path / "out" / "a_byword.pdf")),
        ("b.docx", "failed", "", ""),
        ("c.docx", "skipped", "c_byword.pdf", str(tmp_path / "out" / "c_byword.pdf")),
        ("a.docx", "ok", "a_accepted_tracking_byword.pdf", str(tmp_path / "out" / "a_accepted_tracking_byword.pdf")),
        ("a.docx", "ok", "a_accepted_tracking_byword.docx", str(tmp_path / "out" / "a_accepted_tracking_byword.docx")),
    ]
    assert lines[0]["path_origin"] == str(a)
    assert lines[0]["tool"] == "word" and lines[0]["kind"] == "pdf"
    assert lines[0]["seconds"] == pytest.approx(1.5) and lines[0]["run_at"]
    assert lines[1]["error"] == "Word could not read it"


def test_convert_folder_trims_long_names_first_and_appends_the_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    long_name = "deal_" + "z" * 100 + ".docx"
    _touch(src / long_name)
    _touch(src / "b.docx")
    monkeypatch.setattr(wp, "osa", _fake_batch_osa())
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    out = tmp_path / "out"

    results = wp.convert_folder(src, out, session=session, one_osascript=True)

    trimmed = wp.trim_name(long_name)
    assert [r.source.name for r in results] == sorted([trimmed, "b.docx"])
    assert all(r.ok for r in results)
    assert (src / trimmed).exists() and not (src / long_name).exists()
    assert (out / f"{Path(trimmed).stem}_byword.pdf").exists() and (out / "b_byword.pdf").exists()
    rows = _lines(out / "manifest.jsonl")
    assert [r["status"] for r in rows] == ["renamed", "ok", "ok"]
    assert rows[0]["original_filename"] == long_name and rows[0]["converted_filename"] == trimmed
    assert rows[1]["converted_filename"] == "b_byword.pdf" or rows[2]["converted_filename"] == "b_byword.pdf"

    # a second run skips both and appends again rather than rewriting
    results = wp.convert_folder(src, out, session=session, one_osascript=True)
    assert all(r.skipped for r in results)
    rows = _lines(out / "manifest.jsonl")
    assert [r["status"] for r in rows] == ["renamed", "ok", "ok", "skipped", "skipped"]


def test_manifest_lands_beside_the_sources_when_there_is_no_out_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "a.docx")
    monkeypatch.setattr(wp, "osa", _fake_batch_osa())
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)

    wp.convert_folder(src, None, session=session, one_osascript=True)

    assert (src / "a_byword.pdf").exists()
    (row,) = _lines(src / "manifest.jsonl")
    assert row["path_out"] == str(src / "a_byword.pdf")


# ─── console sink ────────────────────────────────────────────────────────────


def test_console_sink_prints_log_lines_verbatim() -> None:
    """Rich's default markup turned `[word] recovery 1:` into `recovery 1:`,
    `[ok]\\t0` into `0` and `:recycle:` into ♻ on screen (2026-10-14 logs);
    the file log was right and the screen was not."""
    import io

    from rich.console import Console

    buf = io.StringIO()
    sink = wp.make_console_sink(Console(file=buf, force_terminal=False, width=200))
    sink("[word] recovery 1: __main__:recycle:1263 [ok]\t0 [batch] 4/135 [focus] x\n")
    out = buf.getvalue()
    assert "[word] recovery 1:" in out
    assert ":recycle:" in out and "♻" not in out
    assert "[ok]" in out and " 0 [batch]" in out  # rich expands the tab; the tag survives
    assert "[batch] 4/135" in out and "[focus] x" in out


def test_console_sink_keeps_colour(tmp_path: Path) -> None:
    """Verbatim must not mean monochrome: loguru's level colour (the sink is
    added with colorize=True) and rich's highlighting of numbers and paths
    both survive, while the tags still print as text."""
    import io

    from loguru import logger as fresh
    from rich.console import Console

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True, color_system="truecolor", width=200)
    handler = fresh.add(
        wp.make_console_sink(console), colorize=True, format="<level>{level} {message}</level>", level="INFO"
    )
    try:
        fresh.warning("[word] recovery 1: 3 document(s) at /tmp/x.docx")
    finally:
        fresh.remove(handler)
    out = buf.getvalue()
    assert "\x1b[" in out, "no ANSI colour at all"
    stripped = re.sub(r"\x1b\[[0-9;]*m", "", out)
    assert "WARNING [word] recovery 1: 3 document(s) at /tmp/x.docx" in stripped
    assert out.count("\x1b[") >= 3, "expected level colour plus highlighted number and path"


# ─── _run_logged wording ─────────────────────────────────────────────────────


def _caught(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    lines: list[str] = []
    monkeypatch.setattr(wp.logger, "info", lambda m, *a, **k: lines.append(str(m)))
    monkeypatch.setattr(wp.logger, "warning", lambda m, *a, **k: lines.append(str(m)))
    return lines


def test_run_logged_says_when_the_command_returned_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = _caught(monkeypatch)
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    ok, detail = wp.WordSession()._run_logged("[t]", "tell app")
    assert ok and detail == ""
    assert lines[-1].startswith("[t] returned rc=0 in ") and lines[-1].endswith(", no output")


def test_run_logged_explains_applescripts_missing_value(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = _caught(monkeypatch)
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "missing value\n", ""))
    ok, detail = wp.WordSession()._run_logged("[t]", "tell app")
    assert ok and detail == ""
    assert "no value came back (AppleScript 'missing value')" in lines[-1]


def test_run_logged_quotes_what_it_got(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = _caught(monkeypatch)
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "document 1 of application\nmore", ""))
    ok, detail = wp.WordSession()._run_logged("[t]", "tell app")
    assert ok and detail == "document 1 of application"
    assert lines[-1].endswith(", got: document 1 of application")


def test_run_logged_quotes_the_error_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = _caught(monkeypatch)
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (1, "", "execution error: Connection is invalid. (-609)"))
    ok, detail = wp.WordSession()._run_logged("[t]", "tell app")
    assert not ok and detail == "execution error: Connection is invalid. (-609)"
    assert lines[-1].startswith("[t] returned rc=1 in ") and lines[-1].endswith(", error: execution error: Connection is invalid. (-609)")


def test_run_logged_passes_script_arguments_through(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: seen.append((s, a)) or (0, "", ""))
    ok, _ = wp.WordSession()._run_logged("[t]", wp._CLOSE_NAMED, "00001__deal.docx", timeout=20)
    assert ok and seen == [(wp._CLOSE_NAMED, ("00001__deal.docx",))]


def test_shown_folds_a_multiline_script_and_quotes_its_arguments() -> None:
    line = wp.shown(wp._CLOSE_NAMED, "my deal.docx")
    assert "\n" not in line
    assert line.startswith("osascript -e ") and line.endswith(" 'my deal.docx'")
    assert "close document i saving no" in line


def test_run_logged_names_a_silent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    lines = _caught(monkeypatch)
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (None, "", ""))
    ok, detail = wp.WordSession()._run_logged("[t]", "tell app")
    assert not ok and detail == ""
    assert lines[-1].endswith(", no error text")
