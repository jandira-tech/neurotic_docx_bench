"""Unit tests for the word-validate gate's decision logic.

The actual Microsoft Word open (AppleScript) is a manual/interactive gate — it
cannot run unattended (a repair dialog blocks the process). What IS unit-testable
is how we interpret the osascript outcome, which is what these tests pin. The
Word-driving `validate_one` is exercised interactively (see `word-validate` CLI).
"""

from __future__ import annotations

from neurotic_docx_bench.render.word import _interpret_validation


def test_clean_open_returns_ok() -> None:
    # osascript exited 0 and echoed the document name → Word opened it cleanly.
    result = _interpret_validation(returncode=0, stdout="mydoc.docx\n", stderr="", timed_out=False)
    assert result.ok
    assert result.error is None


def test_timeout_is_not_valid_dialog() -> None:
    # A repair/warning dialog blocks the AppleScript `open`, so the subprocess
    # times out — that is precisely a NOT-word-valid document.
    result = _interpret_validation(returncode=None, stdout="", stderr="", timed_out=True)
    assert not result.ok
    assert result.error is not None and "dialog" in result.error


def test_nonzero_exit_is_not_valid() -> None:
    result = _interpret_validation(
        returncode=1, stdout="", stderr="Word got an error", timed_out=False
    )
    assert not result.ok
    assert result.error == "Word got an error"


def test_zero_exit_without_docname_is_not_valid() -> None:
    # Exit 0 but no document name echoed means the open did not actually succeed.
    result = _interpret_validation(returncode=0, stdout="   \n", stderr="", timed_out=False)
    assert not result.ok
