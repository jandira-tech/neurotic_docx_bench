"""Spec for ``scripts/word_pdf_focus.py``: word_pdf with a watchdog that brings Word forward to
press "No" on a Yes/No prompt and keeps it there for the OK that follows.

After "No" on the repair prompt Word raises "Word experienced an error trying to open the
file" (OK), but only once Word is the active app; in the background the alert does not exist
and the open AppleEvent hangs until its timeout (2026-09-30). No Word, no osascript here:
``word_pdf.osa`` is patched.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.usefixtures("no_live_word")

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load():
    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    spec = importlib.util.spec_from_file_location("word_pdf_focus", _SCRIPTS / "word_pdf_focus.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["word_pdf_focus"] = mod
    spec.loader.exec_module(mod)
    return mod


wpf = _load()
wp = wpf.word_pdf


def _run(dogs, until, seconds: float = 3.0) -> None:
    dogs.start()
    deadline = wp.time.monotonic() + seconds
    while not until() and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()


def _word_shows(first: str):
    """Word's button dump: ``first`` once, then no windows at all."""
    shown = iter([first])
    return lambda: next(shown, "")


def test_no_and_its_ok_are_pressed_in_one_activation(monkeypatch: pytest.MonkeyPatch) -> None:
    dump = _word_shows("Yes\tNo\tCancel\t")
    forwarded: list[tuple[str, ...]] = []
    used: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        used.append(script)
        if script is wp._DUMP_BUTTONS:
            return (0, dump(), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wpf._FORWARD_AND_PRESS:
            forwarded.append(args)
            return 0, "No,OK", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wpf.FocusWatchdogs(poll=0.01)
    _run(dogs, lambda: dogs.forwarded > 0)

    assert dogs.forwarded == 1 and dogs.declined == 1
    assert forwarded[0][0] == wp.WORD_PROC and forwarded[0][2:] == ("No", "OK|Ok")
    assert dogs._owed_until == 0.0  # the OK was taken in the same activation
    # the No was not pressed in the background first
    assert wp._PRESS not in used and wp._DECLINE_REPAIR not in used


def test_ok_still_owed_after_the_no_is_fetched_by_a_later_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dump = _word_shows("Yes\tNo\t")
    forwarded: list[tuple[str, ...]] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_BUTTONS:
            return (0, dump(), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wpf._FORWARD_AND_PRESS:
            forwarded.append(args[2:])
            return 0, ("No" if len(forwarded) == 1 else "OK"), ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wpf.FocusWatchdogs(poll=0.01)
    _run(dogs, lambda: len(forwarded) >= 2)

    assert forwarded[:2] == [("No", "OK|Ok"), ("OK|Ok",)]
    assert dogs.forwarded == 2


def test_never_takes_focus_when_word_owes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An OK Word already shows is pressed in the background; no reason to take focus."""
    dump = _word_shows("OK\t")
    used: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        used.append(script)
        if script is wp._DUMP_BUTTONS:
            return (0, dump(), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._PRESS and args[0] == wp.WORD_PROC:
            return 0, "OK", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wpf.FocusWatchdogs(poll=0.01)
    _run(dogs, lambda: False, seconds=0.5)

    assert dogs.dismissed == 1
    assert wpf._FORWARD_AND_PRESS not in used


def test_gives_up_on_the_owed_ok_after_its_window(monkeypatch: pytest.MonkeyPatch) -> None:
    dump = _word_shows("Yes\tNo\t")
    tries: list[tuple[str, ...]] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_BUTTONS:
            return (0, dump(), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wpf._FORWARD_AND_PRESS:
            tries.append(args[2:])
            return 0, ("No" if len(tries) == 1 else ""), ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wpf.FocusWatchdogs(poll=0.01, owe_window=0.2)
    _run(dogs, lambda: False, seconds=0.8)

    assert len(tries) >= 2 and dogs._owed_until == 0.0


def test_forward_script_hands_focus_back_and_hides_word() -> None:
    """Word is hidden again after every check, unless Word was the app in front before it."""
    s = wpf._FORWARD_AND_PRESS
    assert "set frontmost of (first process whose name is priorApp) to true" in s
    assert "if priorApp is not procName then" in s
    assert "set visible of process procName to false" in s
    assert "wasVisible" not in s


def test_defaults_check_at_5_s_then_every_10_s() -> None:
    p = wpf.FocusProgress(Path("unused.log"), total=1)
    assert (p.nudge_after, p.nudge_every) == (5.0, 10.0)


def test_a_slow_stall_report_never_delays_a_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """word_pdf's stall report runs osascript probes that each time out while Word is busy
    (30 s in the 2026-09-30 trial); it must not hold up the next check."""
    log, forwarded = _progress(tmp_path, monkeypatch)
    release = wp.threading.Event()

    def slow_report(_p):
        release.wait(5)
        return ""

    with wpf.FocusProgress(log, total=1, poll=0.01, stall_after=0.01, nudge_after=0.1,
                           nudge_every=60, diagnose=slow_report):
        wp.time.sleep(0.4)
        seen = list(forwarded)
        release.set()
    assert seen == [("No|OK|Ok", "OK|Ok")]


def test_forward_script_compiles(tmp_path: Path) -> None:
    """Compiles only, runs nothing (``st`` is an AppleScript keyword and slipped past the fakes)."""
    import shutil
    import subprocess

    if not shutil.which("osacompile"):
        pytest.skip("osacompile is macOS only")
    src = tmp_path / "forward.applescript"
    src.write_text(wpf._FORWARD_AND_PRESS)
    r = subprocess.run(["osacompile", "-o", str(tmp_path / "f.scpt"), str(src)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_forward_script_ends_at_an_ok() -> None:
    """An OK is the last press: after it nothing else is waited for with Word in front."""
    assert 'if pressed is "OK" or pressed is "Ok" then exit repeat' in wpf._FORWARD_AND_PRESS


def test_install_swaps_the_watchdog_and_progress_word_pdf_uses() -> None:
    originals = wp.Watchdogs, wp._Progress
    try:
        wpf.install()
        assert wp.Watchdogs is wpf.FocusWatchdogs and wp._Progress is wpf.FocusProgress
    finally:
        wp.Watchdogs, wp._Progress = originals


# ─── an opened item that is not saved soon: bring Word forward and check ─────


def _progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reply: str = ""):
    log = tmp_path / "batch-pdf-1.log"
    log.write_text("")
    forwarded: list[tuple[str, ...]] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wpf._FORWARD_AND_PRESS:
            forwarded.append(args[2:])
            return 0, reply, ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    return log, forwarded


def test_item_not_saved_soon_brings_word_forward_for_no_then_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log, forwarded = _progress(tmp_path, monkeypatch, reply="No,OK")
    with wpf.FocusProgress(log, total=2, poll=0.01, nudge_after=0.05, nudge_every=60, diagnose=lambda p: ""):
        wp.time.sleep(0.4)
    assert forwarded == [("No|OK|Ok", "OK|Ok")]  # once per item until nudge_every passes


def test_item_saved_quickly_never_takes_focus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log, forwarded = _progress(tmp_path, monkeypatch)
    with wpf.FocusProgress(log, total=5, poll=0.01, nudge_after=0.3, diagnose=lambda p: ""):
        for i in range(5):
            wp.time.sleep(0.05)
            with log.open("a") as f:
                f.write(f"[ok]\t{i + 1}\n")
    assert forwarded == []


def test_a_retry_line_starts_the_next_items_clock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """word_pdf's own counter ignores [retry]; the nudge clock must not, or the next item is
    nudged early."""
    log, forwarded = _progress(tmp_path, monkeypatch)
    with wpf.FocusProgress(log, total=5, poll=0.01, nudge_after=0.3, diagnose=lambda p: ""):
        for i in range(5):
            wp.time.sleep(0.1)
            with log.open("a") as f:
                f.write(f"[retry]\t{i + 1}\tdocument loaded empty\n")
    assert forwarded == []


def test_a_stuck_item_is_checked_again_every_nudge_every(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log, forwarded = _progress(tmp_path, monkeypatch)
    with wpf.FocusProgress(log, total=1, poll=0.01, nudge_after=0.05, nudge_every=0.15, diagnose=lambda p: ""):
        wp.time.sleep(0.5)
    assert 2 <= len(forwarded) <= 4
