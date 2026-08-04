"""WV-1 word-validate decision logic (PR9: relative timeouts + modal detection).

The old gate inferred "repair dialog" from an AppleScript timeout — but Word takes
longer than any fixed window just to OPEN a large document, so big docs failed
regardless of validity (TODO §1). The new contract: an actual modal (System Events
probe) means INVALID; a clean open means VALID; budget exhaustion with NO modal
observed means UNJUDGEABLE — its own recorded outcome, never a failure. The budget
is calibrated per invocation from a known-Word-valid reference open (``k×``).

The Word-driving parts stay interactive-only; these tests pin the pure
interpreters and the polling flow with a fake process.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from neurotic_docx_bench.render import word
from neurotic_docx_bench.render.word import (
    ValidationResult,
    _budget,
    _interpret_modal_probe,
    _interpret_open_exit,
    validate_one,
)

# ── pure interpreters ────────────────────────────────────────────────────────


def test_budget_math() -> None:
    assert _budget(60.0, None, 4.0) == 60.0  # no reference → plain timeout
    assert _budget(60.0, 30.0, 4.0) == 120.0  # slow machine → stretched budget
    assert _budget(60.0, 5.0, 4.0) == 60.0  # fast reference → floor at timeout


def test_interpret_modal_probe() -> None:
    assert _interpret_modal_probe("no-process", 0) is False
    assert _interpret_modal_probe("0 0", 0) is False
    assert _interpret_modal_probe("1 0", 0) is True  # a sheet is up
    assert _interpret_modal_probe("0 2", 0) is True  # dialog windows
    assert _interpret_modal_probe("", 1) is None  # probe failed → unknown
    assert _interpret_modal_probe("garbage", 0) is None


def test_interpret_open_exit() -> None:
    ok = _interpret_open_exit(returncode=0, stdout="mydoc.docx\n", stderr="", duration_s=1.0)
    assert ok.outcome == "valid"
    assert ok.ok
    assert ok.error is None

    # Exit 0 but no document name echoed means the open did not actually succeed.
    no_name = _interpret_open_exit(returncode=0, stdout="   \n", stderr="", duration_s=1.0)
    assert no_name.outcome == "invalid"
    assert not no_name.ok

    err = _interpret_open_exit(returncode=1, stdout="", stderr="Word got an error", duration_s=1.0)
    assert err.outcome == "invalid"
    assert err.error == "Word got an error"


def test_validation_result_ok_property() -> None:
    assert ValidationResult("valid").ok
    assert not ValidationResult("invalid", error="x").ok
    assert not ValidationResult("unjudgeable", error="slow").ok


# ── polling flow (fake process; no Word involved) ────────────────────────────


class _FakeProc:
    """Stands in for the osascript Popen: exits after ``exits_after`` waits."""

    def __init__(self, exits_after: int | None, returncode: int = 0, out: str = "doc\n", err: str = ""):
        self._exits_after = exits_after
        self._waits = 0
        self._out, self._err = out, err
        self.returncode: int | None = None
        self._final_rc = returncode
        self.killed = False

    def wait(self, timeout: float | None = None) -> int:
        self._waits += 1
        if self._exits_after is not None and self._waits >= self._exits_after:
            self.returncode = self._final_rc
            return self._final_rc
        raise subprocess.TimeoutExpired(cmd="osascript", timeout=timeout or 0)

    def poll(self) -> int | None:
        return self.returncode

    def communicate(self) -> tuple[str, str]:
        return self._out, self._err

    def kill(self) -> None:
        self.killed = True


def _patch_flow(monkeypatch, proc: _FakeProc, modal: bool | None):
    closes: list[str] = []
    monkeypatch.setattr(word.subprocess, "Popen", lambda *a, **k: proc)
    monkeypatch.setattr(word, "probe_modal", lambda **k: modal)
    monkeypatch.setattr(word, "_close_active_document", lambda **k: closes.append("close"))
    return closes


def test_clean_open_is_valid(monkeypatch, tmp_path: Path) -> None:
    proc = _FakeProc(exits_after=1, returncode=0, out="doc.docx\n")
    _patch_flow(monkeypatch, proc, modal=False)
    r = validate_one(tmp_path / "d.docx", timeout=5.0, poll_interval=0.01)
    assert r.outcome == "valid"
    assert r.ok


def test_nonzero_exit_is_invalid(monkeypatch, tmp_path: Path) -> None:
    proc = _FakeProc(exits_after=1, returncode=1, out="", err="Word got an error")
    _patch_flow(monkeypatch, proc, modal=False)
    r = validate_one(tmp_path / "d.docx", timeout=5.0, poll_interval=0.01)
    assert r.outcome == "invalid"
    assert r.error == "Word got an error"


def test_modal_is_invalid_with_targeted_close(monkeypatch, tmp_path: Path) -> None:
    proc = _FakeProc(exits_after=None)  # never exits — blocked on the dialog
    closes = _patch_flow(monkeypatch, proc, modal=True)
    r = validate_one(tmp_path / "d.docx", timeout=5.0, poll_interval=0.01)
    assert r.outcome == "invalid"
    assert r.error is not None and "modal" in r.error
    assert closes  # the opened document was closed, not left stacking windows
    assert proc.killed


def test_budget_exhausted_without_modal_is_unjudgeable(monkeypatch, tmp_path: Path) -> None:
    proc = _FakeProc(exits_after=None)  # slow open, no dialog
    closes = _patch_flow(monkeypatch, proc, modal=False)
    r = validate_one(tmp_path / "d.docx", timeout=0.05, poll_interval=0.01)
    assert r.outcome == "unjudgeable"
    assert not r.ok
    assert r.error is not None and "budget" in r.error
    assert closes
    assert proc.killed


def test_reference_stretches_budget(monkeypatch, tmp_path: Path) -> None:
    # With a measured 30s reference open and k=4, a doc that would blow a 0.05s
    # fixed timeout is NOT unjudgeable-flagged before the stretched budget.
    proc = _FakeProc(exits_after=3, returncode=0, out="doc.docx\n")
    _patch_flow(monkeypatch, proc, modal=False)
    r = validate_one(
        tmp_path / "d.docx", timeout=0.001, poll_interval=0.001, k=4.0,
        reference_duration_s=30.0,
    )
    assert r.outcome == "valid"


# ── CLI: outcomes printed + --json producer ──────────────────────────────────


def test_cli_word_validate_json(monkeypatch, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from neurotic_docx_bench.cli import app

    (tmp_path / "a.docx").write_bytes(b"x")
    (tmp_path / "b.docx").write_bytes(b"x")
    (tmp_path / "c.docx").write_bytes(b"x")
    outcomes = {
        "a": ValidationResult("valid", None, 1.0),
        "b": ValidationResult("invalid", "repair dialog (modal detected)", 2.0),
        "c": ValidationResult("unjudgeable", "slow open", 60.0),
    }
    monkeypatch.setattr(word, "word_available", lambda: True)
    monkeypatch.setattr(word, "validate_one", lambda docx, **k: outcomes[docx.stem])
    json_path = tmp_path / "wv1.json"
    result = CliRunner().invoke(
        app, ["word-validate", str(tmp_path), "--json", str(json_path)],
    )
    assert result.exit_code == 1  # invalid present fails; unjudgeable does not
    assert "VALID" in result.stdout
    assert "INVALID" in result.stdout
    assert "UNJUDGEABLE" in result.stdout

    import json

    data = json.loads(json_path.read_text())
    assert data["results"]["a"]["outcome"] == "valid"
    assert data["results"]["b"]["outcome"] == "invalid"
    assert data["results"]["c"]["outcome"] == "unjudgeable"
    assert data["results"]["c"]["duration_s"] == 60.0


def test_cli_unjudgeable_alone_does_not_fail(monkeypatch, tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from neurotic_docx_bench.cli import app

    (tmp_path / "big.docx").write_bytes(b"x")
    monkeypatch.setattr(word, "word_available", lambda: True)
    monkeypatch.setattr(
        word, "validate_one", lambda docx, **k: ValidationResult("unjudgeable", "slow", 60.0),
    )
    result = CliRunner().invoke(app, ["word-validate", str(tmp_path)])
    assert result.exit_code == 0
