"""--nudge-after, --nudge-wait and --empty-limit reach the batch (#107)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.usefixtures("no_live_word")

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "word_pdf.py"


def _load():
    spec = importlib.util.spec_from_file_location("word_pdf", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["word_pdf"] = mod
    spec.loader.exec_module(mod)
    return mod


wp = _load()


def _seen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *args: str) -> dict:
    """Run the CLI with ``_main`` stubbed; return what the batch would have used."""
    seen: dict = {}

    def fake_main(*a, **k) -> None:
        p = wp._Progress(tmp_path / "x.log", total=1)
        seen["nudge_after"], seen["nudge_wait"] = p.nudge_after, p.nudge_wait
        seen["script"] = wp.batch_script(close_documents=True, accept=False)

    monkeypatch.setattr(wp, "_main", fake_main)
    (tmp_path / "src").mkdir()
    result = CliRunner().invoke(wp.app, ["--src", str(tmp_path / "src"), *args])
    assert result.exit_code == 0, result.output
    return seen


def test_defaults_are_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen = _seen(monkeypatch, tmp_path)
    assert (seen["nudge_after"], seen["nudge_wait"]) == (10.0, 2.0)
    assert "if emptyStreak ≥ 3 then exit repeat" in seen["script"]


def test_flags_reach_the_progress_and_the_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen = _seen(monkeypatch, tmp_path, "--nudge-after", "5", "--nudge-wait", "1", "--empty-limit", "10")
    assert (seen["nudge_after"], seen["nudge_wait"]) == (5.0, 1.0)
    assert "if emptyStreak ≥ 10 then exit repeat" in seen["script"]
    assert "emptyStreak ≥ 3 " not in seen["script"]


def test_flags_do_not_leak_past_the_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _seen(monkeypatch, tmp_path, "--nudge-after", "5", "--empty-limit", "10")
    assert wp._Progress(tmp_path / "y.log", total=1).nudge_after == 10.0
    assert "emptyStreak ≥ 3 then" in wp.batch_script(close_documents=True, accept=False)


@pytest.mark.parametrize("flag", ["--empty-limit=0", "--nudge-after=0", "--nudge-wait=-1"])
def test_out_of_range_is_refused(tmp_path: Path, flag: str) -> None:
    (tmp_path / "src").mkdir()
    result = CliRunner().invoke(wp.app, ["--src", str(tmp_path / "src"), flag])
    assert result.exit_code != 0
