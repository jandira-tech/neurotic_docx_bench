"""Resumable conversion records retain earlier timing and failure entries."""

from __future__ import annotations

import json
import sys
from itertools import count
from pathlib import Path
from types import SimpleNamespace

import pytest

from neurotic_docx_bench import docx_to_pdf as d2p
from scripts import convert_candidates as candidates


@pytest.fixture
def conversion_run(tmp_path: Path, monkeypatch):
    items = [d2p.Fixture(stem=name, kind="clean", original_stem=name,
                         docx=tmp_path / f"{name}.docx", oracle=tmp_path / f"{name}.pdf")
             for name in ("good", "bad")]
    selection = SimpleNamespace(fixtures=items)
    monkeypatch.setattr(candidates.cli, "_corpus_word_selection", lambda **kw: selection)
    monkeypatch.setattr(d2p, "resolve_tool_binary", lambda tool: tmp_path / "converter")
    monkeypatch.setattr(sys, "argv", ["convert_candidates.py", "--engine", "docxide",
                                     "--out", str(tmp_path / "work"), "--jobs", "1"])
    clock = count(step=0.25)
    monkeypatch.setattr(candidates.time, "perf_counter", lambda: next(clock))
    return selection, tmp_path / "work"


def test_resume_preserves_seconds_and_failures_with_nothing_to_convert(conversion_run, monkeypatch):
    selection, out = conversion_run
    calls = []

    def convert(tool, binary, item, dest):
        calls.append(item.stem)
        if item.stem == "bad":
            return {"error": "crashed"}
        dest.write_bytes(b"%PDF-1.7 test output")
        return None

    monkeypatch.setattr(d2p, "try_convert_fixture", convert)
    candidates.main()
    path = out / "convert_seconds.json"
    first = json.loads(path.read_text())
    assert first["seconds"] == {"bad": 0.25, "good": 0.25}
    assert first["failures"] == {"bad": "crashed"}
    selection.fixtures = selection.fixtures[:1]
    candidates.main()
    assert calls == ["good", "bad"]
    assert json.loads(path.read_text()) == first


@pytest.mark.parametrize("error", [None, "new failure"])
def test_reconversion_replaces_its_records_and_keeps_other_documents(conversion_run, monkeypatch, error):
    selection, out = conversion_run
    selection.fixtures = selection.fixtures[:1]
    out.mkdir()
    path = out / "convert_seconds.json"
    path.write_text(json.dumps({"seconds": {"good": 9.0, "other": 8.0},
                               "failures": {"good": "old failure", "other": "earlier failure"}}))

    def convert(tool, binary, item, dest):
        if error:
            return {"error": error}
        dest.write_bytes(b"%PDF-1.7 test output")
        return None

    monkeypatch.setattr(d2p, "try_convert_fixture", convert)
    candidates.main()
    record = json.loads(path.read_text())
    assert record["seconds"] == {"good": 0.25, "other": 8.0}
    expected = {"other": "earlier failure"}
    if error:
        expected["good"] = error
    assert record["failures"] == expected
