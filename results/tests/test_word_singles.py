"""live-bench/harvest/word_singles.py reads scripts/word_pdf.py's manifest, not the superseded driver's stdout (#67)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "live-bench" / "harvest" / "word_singles.py"


def _load():
    spec = importlib.util.spec_from_file_location("word_singles", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # importing must not run a batch
    return mod


def _manifest(path: Path, *lines: dict) -> Path:
    path.write_text("".join(json.dumps(line) + "\n" for line in lines))
    return path


def test_it_drives_word_pdf_not_the_superseded_focus_driver() -> None:
    text = SCRIPT.read_text()
    assert "scripts/word_pdf.py" in text
    assert "word_pdf_focus" not in text


def test_an_exported_file_opens_ok(tmp_path: Path) -> None:
    m = _manifest(tmp_path / "manifest.jsonl", {"original_filename": "a.docx", "status": "ok", "kind": "pdf",
                                                 "converted_filename": "a_byword.pdf", "error": ""})
    assert _load().verdict(m, "a.docx") == ("opens_ok", "")


def test_a_declined_repair_prompt_is_broken(tmp_path: Path) -> None:
    err = "repair prompt declined; Word could not read it (0 paragraphs)"
    m = _manifest(tmp_path / "manifest.jsonl", {"original_filename": "b.docx", "status": "failed", "kind": "pdf",
                                                 "converted_filename": "", "error": err})
    assert _load().verdict(m, "b.docx") == ("broken", err)


def test_an_old_loaded_empty_message_is_broken_too(tmp_path: Path) -> None:
    m = _manifest(tmp_path / "manifest.jsonl", {"original_filename": "b.docx", "status": "failed", "kind": "pdf",
                                                 "converted_filename": "", "error": "document loaded empty"})
    assert _load().verdict(m, "b.docx")[0] == "broken"


def test_another_failure_is_failed_other(tmp_path: Path) -> None:
    m = _manifest(tmp_path / "manifest.jsonl", {"original_filename": "c.docx", "status": "failed", "kind": "pdf",
                                                 "converted_filename": "", "error": "Word crashed"})
    assert _load().verdict(m, "c.docx") == ("failed_other", "Word crashed")


def test_a_trimmed_name_is_followed_through_its_rename_line(tmp_path: Path) -> None:
    long = "x" * 90 + ".docx"
    m = _manifest(tmp_path / "manifest.jsonl",
                  {"original_filename": long, "status": "renamed", "kind": "rename", "converted_filename": "x_1234abcd.docx",
                   "error": ""},
                  {"original_filename": "x_1234abcd.docx", "status": "ok", "kind": "pdf",
                   "converted_filename": "x_1234abcd_byword.pdf", "error": ""})
    assert _load().verdict(m, long) == ("opens_ok", "")


def test_no_line_for_the_file_is_no_result(tmp_path: Path) -> None:
    m = _manifest(tmp_path / "manifest.jsonl", {"original_filename": "z.docx", "status": "ok", "kind": "pdf",
                                                 "converted_filename": "z_byword.pdf", "error": ""})
    assert _load().verdict(m, "a.docx") == ("no_result", "no manifest line for a.docx")
    assert _load().verdict(tmp_path / "missing.jsonl", "a.docx")[0] == "no_result"


def test_the_last_line_for_a_file_wins(tmp_path: Path) -> None:
    m = _manifest(tmp_path / "manifest.jsonl",
                  {"original_filename": "a.docx", "status": "failed", "kind": "pdf", "converted_filename": "",
                   "error": "Word crashed"},
                  {"original_filename": "a.docx", "status": "ok", "kind": "pdf", "converted_filename": "a_byword.pdf",
                   "error": ""})
    assert _load().verdict(m, "a.docx") == ("opens_ok", "")
