"""Spec for how ``scripts/word_pdf.py`` recognises and answers Word's alerts.

The repair prompt ("Word found unreadable content …", Yes/No) and the alert Word raises after
"No" ("Word experienced an error trying to open the file", OK) are read and answered in as few
``osascript`` round trips as possible, and everything Word says is logged. No Word, no macOS:
``word_pdf.osa`` is patched; the AppleScript sources are covered as data.

Why (2026-10-14): across every batch log in `results/`, the text-matched repair handler never
fired (0 × "repair prompt declined", 259 × "dismissed via 'No'" from the generic fallback, after
three osascripts and ~6 s), and the OK after the No was never pressed while Word sat in the
background, so each broken fixture cost a 240 s AppleEvent timeout and one of three passes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

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


@pytest.fixture(autouse=True)
def _private_word_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test takes the one-driver lock on its own file, never the real one."""
    monkeypatch.setattr(wp, "WORD_LOCK_PATH", tmp_path / "word_driver.lock")

RS, US = "\x1e", "\x1f"
REPAIR_TEXT = (
    "Word found unreadable content in 00003__docxodus__deal.docx. Do you want to recover the "
    "contents of this document? If you trust the source of this document, click Yes."
)
ERROR_TEXT = "Word experienced an error trying to open the file."


def _dump(*dialogs: tuple[str, str]) -> str:
    """What `_DUMP_DIALOGS` returns: per dialog, tab-joined buttons, US, text, RS."""
    return "".join(f"{buttons}{US}{text}{RS}" for buttons, text in dialogs)


def _run(dogs, until, seconds: float = 3.0) -> None:
    dogs.start()
    deadline = wp.time.monotonic() + seconds
    while not until() and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()


# ─── parsing what Word shows ─────────────────────────────────────────────────


def test_parse_dialogs_reads_buttons_and_text_per_window() -> None:
    dialogs = wp.parse_dialogs(_dump(("Yes\tNo\t", REPAIR_TEXT), ("OK\t", "")))
    assert [d.buttons for d in dialogs] == [("Yes", "No"), ("OK",)]
    assert dialogs[0].text == REPAIR_TEXT
    assert dialogs[1].text == ""


def test_parse_dialogs_tolerates_a_bare_button_list() -> None:
    """A dump with no text separator (an older script, a stub) is one dialog of buttons."""
    (dialog,) = wp.parse_dialogs("OK\tMore Information\tmissing value\t")
    assert dialog.buttons == ("OK", "More Information", "missing value")
    assert dialog.text == ""


def test_parse_dialogs_of_nothing_is_empty() -> None:
    assert wp.parse_dialogs("") == []
    assert wp.parse_dialogs(RS) == []


def test_parse_dialogs_drops_the_alerts_title_line() -> None:
    """Word's first static text is the alert's title, the process name (seen live 2026-10-14)."""
    (dialog,) = wp.parse_dialogs(_dump(("Yes\tNo\t", f"Microsoft Word | {REPAIR_TEXT} | ")))
    assert dialog.text == REPAIR_TEXT


@pytest.mark.parametrize(
    ("buttons", "text", "expected"),
    [
        (("Yes", "No"), REPAIR_TEXT, True),
        (("Yes", "No"), "", True),  # the text was not readable; Yes/No is still the prompt
        (("No", "Yes", "Cancel"), "", True),
        (("OK",), REPAIR_TEXT, True),  # the words decide even when the buttons differ
        (("OK",), ERROR_TEXT, False),
        (("OK",), "", False),
        (("Select…", "Cancel"), "", False),
        (("Save", "Don't Save", "Cancel"), "", False),
    ],
)
def test_is_repair_prompt(buttons: tuple[str, ...], text: str, expected: bool) -> None:
    assert wp.is_repair_prompt(wp.Dialog(buttons, text)) is expected


# ─── the repair prompt: one read, one answer ─────────────────────────────────


def test_repair_prompt_is_answered_no_then_ok_in_one_osascript(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One dump recognises it; one script brings Word forward, presses No, waits for the OK."""
    shown = iter([_dump(("Yes\tNo\t", REPAIR_TEXT))])
    used: list[tuple[str, tuple[str, ...]]] = []
    warned: list[str] = []
    monkeypatch.setattr(wp.logger, "warning", lambda m: warned.append(str(m)))

    def fake_osa(script, *args, timeout=60.0):
        used.append((script, args))
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._ANSWER:
            return 0, f"No{US}{REPAIR_TEXT}{RS}OK{US}{ERROR_TEXT}{RS}", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01, wait=2.5)
    _run(dogs, lambda: dogs.declined >= 1)

    assert dogs.declined == 1 and dogs.forwarded == 1
    answers = [a for s, a in used if s is wp._ANSWER]
    assert answers == [(wp.WORD_PROC, "2.5", "No", "OK|Ok")]
    scripts = [s for s, _ in used]
    assert wp._PRESS_ACTIVATED not in scripts and wp._PRESS not in scripts
    # Both of Word's sentences are on the record, with the staged file name Word used.
    assert any("No" in m and "OK" in m and "00003__docxodus__deal.docx" in m for m in warned)
    assert any(ERROR_TEXT in m for m in warned)
    assert [e.pressed for e in dogs.events] == [("No", "OK")]
    assert dogs.events[0].text == REPAIR_TEXT


def test_repair_prompt_without_focus_is_declined_in_the_background(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--no-focus` keeps today's behaviour: No is pressed where Word is, nothing is activated."""
    shown = iter([_dump(("Yes\tNo\t", REPAIR_TEXT))])
    used: list[tuple[str, tuple[str, ...]]] = []

    def fake_osa(script, *args, timeout=60.0):
        used.append((script, args))
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._PRESS:
            return 0, "No", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01, focus=False)
    _run(dogs, lambda: dogs.declined >= 1)

    assert dogs.declined == 1 and dogs.forwarded == 0
    presses = [a for s, a in used if s is wp._PRESS]
    assert presses == [(wp.WORD_PROC, "No")]
    assert wp._ANSWER not in [s for s, _ in used]


def test_yes_no_without_readable_text_is_still_declined_and_the_gap_is_logged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shown = iter([_dump(("Yes\tNo\t", ""))])
    warned: list[str] = []
    monkeypatch.setattr(wp.logger, "warning", lambda m: warned.append(str(m)))

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._ANSWER:
            return 0, f"No{US}{RS}", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    _run(dogs, lambda: dogs.declined >= 1)

    assert dogs.declined == 1
    assert any("no readable text" in m for m in warned)


# ─── the OK that follows the No ──────────────────────────────────────────────


def test_an_ok_not_seen_with_the_no_is_fetched_by_a_later_poll(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Word owes an OK after a No. An empty poll inside the window brings Word forward for it."""
    shown = iter([_dump(("Yes\tNo\t", REPAIR_TEXT))])
    answers: list[tuple[str, ...]] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._ANSWER:
            answers.append(args[2:])
            if args[2:] == ("No", "OK|Ok"):
                return 0, f"No{US}{REPAIR_TEXT}{RS}", ""  # the OK did not come in time
            return 0, f"OK{US}{ERROR_TEXT}{RS}", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01, owe_window=5.0, owe_every=0.0)
    _run(dogs, lambda: len(answers) >= 2)

    assert answers[:2] == [("No", "OK|Ok"), ("OK|Ok",)]
    assert dogs.declined == 1 and dogs.forwarded == 2
    assert dogs.owed_until == 0.0  # settled
    assert [e.pressed for e in dogs.events] == [("No",), ("OK",)]


def test_the_owed_ok_is_given_up_after_its_window(monkeypatch: pytest.MonkeyPatch) -> None:
    shown = iter([_dump(("Yes\tNo\t", REPAIR_TEXT))])
    answers: list[tuple[str, ...]] = []
    warned: list[str] = []
    monkeypatch.setattr(wp.logger, "warning", lambda m: warned.append(str(m)))

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._ANSWER:
            answers.append(args[2:])
            return (0, f"No{US}{REPAIR_TEXT}{RS}", "") if "No" in args else (0, "", "")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01, owe_window=0.05, owe_every=0.0)
    _run(dogs, lambda: any("stopped bringing Word forward" in m for m in warned), 2.0)

    assert dogs.owed_until == 0.0
    assert answers[0] == ("No", "OK|Ok")
    assert all(a == ("OK|Ok",) for a in answers[1:])
    assert any("stopped bringing Word forward" in m for m in warned)


def test_never_takes_focus_when_word_owes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    used: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        used.append(script)
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    dogs.start()
    wp.time.sleep(0.2)
    dogs.stop()

    assert wp._DUMP_DIALOGS in used
    assert wp._ANSWER not in used


def test_a_generic_ok_settles_the_owed_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the OK does show up in the background, the plain dismiss pays the debt."""
    shown = iter([_dump(("Yes\tNo\t", REPAIR_TEXT)), _dump(("OK\t", ERROR_TEXT))])
    used: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        used.append(script)
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._ANSWER:
            return 0, f"No{US}{REPAIR_TEXT}{RS}", ""
        if script is wp._PRESS:
            return 0, "OK", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01, owe_window=5.0)
    _run(dogs, lambda: dogs.dismissed >= 1)

    assert dogs.declined == 1 and dogs.dismissed == 1
    assert dogs.owed_until == 0.0
    assert used.count(wp._ANSWER) == 1


# ─── everything Word says is logged ──────────────────────────────────────────


def test_each_distinct_dialog_text_is_logged_once(monkeypatch: pytest.MonkeyPatch) -> None:
    dumps = iter([_dump(("OK\t", ERROR_TEXT)), _dump(("OK\t", ERROR_TEXT)), _dump(("OK\t", "Other"))])
    infos: list[str] = []
    monkeypatch.setattr(wp.logger, "info", lambda m: infos.append(str(m)))

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(dumps, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._PRESS:
            return 0, "OK", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    _run(dogs, lambda: dogs.dismissed >= 3)

    said = [m for m in infos if "says:" in m]
    assert len(said) == 2
    assert ERROR_TEXT in said[0] and "Other" in said[1]
    assert sum("shows button 'OK'" in m for m in infos) == 1


def test_a_nameless_button_is_logged_as_exactly_that(monkeypatch: pytest.MonkeyPatch) -> None:
    """System Events returns `missing value` for a button with no title, and an
    empty string for an empty one. The log says which it saw, rather than
    "shows button 'missing value'" (2026-10-14 13:58) or dropping it."""
    infos: list[str] = []
    monkeypatch.setattr(wp.logger, "info", lambda m: infos.append(str(m)))
    dogs = wp.Watchdogs(poll=0.01)
    dogs._note_dialogs(
        wp.WORD_PROC,
        [wp.Dialog(buttons=("OK", "missing value", ""), text="")],
    )
    assert any(m.endswith("shows button 'OK'") for m in infos)
    assert any("shows a button with no name (AppleScript 'missing value')" in m for m in infos), infos
    assert any("shows a button with an empty name" in m for m in infos), infos
    assert not any("button 'missing value'" in m or "button ''" in m for m in infos)


def test_an_ordinary_dismissal_logs_the_text_it_dismissed(monkeypatch: pytest.MonkeyPatch) -> None:
    shown = iter([_dump(("OK\t", ERROR_TEXT))])
    warned: list[str] = []
    monkeypatch.setattr(wp.logger, "warning", lambda m: warned.append(str(m)))

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._PRESS:
            return 0, "OK", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    _run(dogs, lambda: dogs.dismissed >= 1)

    assert any("dismissed via 'OK'" in m and ERROR_TEXT in m for m in warned)
    assert dogs.events[-1].pressed == ("OK",) and dogs.events[-1].text == ERROR_TEXT


def test_stop_logs_a_tally(monkeypatch: pytest.MonkeyPatch) -> None:
    infos: list[str] = []
    monkeypatch.setattr(wp.logger, "info", lambda m: infos.append(str(m)))
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    with wp.Watchdogs(poll=0.01):
        pass
    assert any("tally" in m and "declined=0" in m for m in infos)


def test_one_poll_is_one_osascript_when_word_is_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    """The old loop dumped twice per dialog (once to look, once to log labels)."""
    used: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        if args and args[0] == wp.WORD_PROC:
            used.append(script)
        if script is wp._DUMP_DIALOGS:
            return (0, _dump(("OK\t", ERROR_TEXT)), "") if args[0] == wp.WORD_PROC else (0, "", "")
        return (0, "OK", "") if script is wp._PRESS else (0, "", "")

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    _run(dogs, lambda: dogs.dismissed >= 2)
    first_two = used[: used.index(wp._PRESS) + 1]
    assert first_two == [wp._DUMP_DIALOGS, wp._PRESS]
    assert wp._DUMP_BUTTONS not in used


# ─── the AppleScript, as data ────────────────────────────────────────────────


def test_answer_script_never_presses_yes_and_hands_focus_back() -> None:
    s = wp._ANSWER
    assert '"Yes"' not in s
    assert "set frontmost to true" in s
    assert "set frontmost of (first process whose name is priorApp) to true" in s
    assert "if priorApp is not procName then" in s
    assert "set visible of process procName to false" in s
    assert 'if pressed is "OK" or pressed is "Ok" then exit repeat' in s
    # The wait is bounded by the clock, not by a count of slow System Events calls
    # (the focus trial's 10 s check took 28 s).
    assert "current date" in s
    assert "items 3 thru -1 of argv" in s  # steps come in through argv, never interpolated


def test_dump_script_reads_text_beside_the_buttons() -> None:
    s = wp._DUMP_DIALOGS
    assert "static texts of" in s
    assert "character id 31" in s and "character id 30" in s
    assert "sheets of w" in s
    assert "item 1 of argv" in s


def test_repair_markers_are_unchanged() -> None:
    assert wp.REPAIR_MARKERS == (
        "Word found unreadable content",
        "Do you want to recover the contents of this document",
    )


# ─── recover_after_failure uses the same answer ──────────────────────────────


def test_recover_after_failure_answers_no_then_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: ran.append((s, a)) or (0, "", ""))
    session = wp.WordSession()
    monkeypatch.setattr(session, "open_document_count", lambda: 0)
    assert wp.recover_after_failure(session) is True
    assert ran[0][0] is wp._ANSWER and ran[0][1][2:] == ("No", "OK|Ok")


def test_recover_after_failure_without_focus_presses_no_in_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ran: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: ran.append((s, a)) or (0, "", ""))
    session = wp.WordSession()
    monkeypatch.setattr(session, "open_document_count", lambda: 0)
    token = wp._focus.set(False)
    try:
        assert wp.recover_after_failure(session) is True
    finally:
        wp._focus.reset(token)
    assert ran[0] == (wp._PRESS, (wp.WORD_PROC, "No"))
    assert wp._ANSWER not in [s for s, _ in ran]


# ─── an opened item that is not saved soon ───────────────────────────────────


def _progress(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    log = tmp_path / "batch.log"
    log.write_text("")
    monkeypatch.setattr(wp.logger, "info", lambda m: None)
    monkeypatch.setattr(wp.logger, "warning", lambda m: None)
    nudged: list[tuple[str, ...]] = []
    monkeypatch.setattr(wp, "answer_alert", lambda *steps, **kw: nudged.append(steps) or [])
    return log, nudged


def test_item_not_saved_soon_brings_word_forward_for_no_then_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log, nudged = _progress(tmp_path, monkeypatch)
    with wp._Progress(log, total=1, poll=0.01, nudge_after=0.05, nudge_every=60, diagnose=lambda p: ""):
        deadline = wp.time.monotonic() + 3
        while not nudged and wp.time.monotonic() < deadline:
            wp.time.sleep(0.02)
    assert nudged == [("No|OK|Ok", "OK|Ok")]


def test_item_saved_quickly_never_takes_focus(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log, nudged = _progress(tmp_path, monkeypatch)
    with wp._Progress(log, total=2, poll=0.01, nudge_after=0.2, nudge_every=60, diagnose=lambda p: ""):
        wp.time.sleep(0.1)
        log.write_text("[ok]\t0\n")
        wp.time.sleep(0.15)
    assert nudged == []


def test_a_retry_line_starts_the_next_items_clock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log, nudged = _progress(tmp_path, monkeypatch)
    with wp._Progress(log, total=2, poll=0.01, nudge_after=0.2, nudge_every=60, diagnose=lambda p: ""):
        wp.time.sleep(0.1)
        log.write_text("[retry]\t0\tloaded empty\n")
        wp.time.sleep(0.15)
    assert nudged == []


def test_a_stuck_item_is_checked_again_every_nudge_every(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log, nudged = _progress(tmp_path, monkeypatch)
    with wp._Progress(log, total=1, poll=0.01, nudge_after=0.05, nudge_every=0.05, diagnose=lambda p: "") as p:
        deadline = wp.time.monotonic() + 3
        while len(nudged) < 3 and wp.time.monotonic() < deadline:
            wp.time.sleep(0.02)
    assert len(nudged) >= 3 and p.nudges >= 3


def test_no_focus_means_no_nudge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log, nudged = _progress(tmp_path, monkeypatch)
    token = wp._focus.set(False)
    try:
        with wp._Progress(log, total=1, poll=0.01, nudge_after=0.02, nudge_every=0.02, diagnose=lambda p: ""):
            wp.time.sleep(0.2)
    finally:
        wp._focus.reset(token)
    assert nudged == []


def test_a_slow_stall_report_never_delays_a_nudge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log, nudged = _progress(tmp_path, monkeypatch)
    release = wp.threading.Event()

    def slow_report(_p):
        release.wait(5)
        return ""

    with wp._Progress(log, total=1, poll=0.01, stall_after=0.01, nudge_after=0.1, nudge_every=60, diagnose=slow_report):
        wp.time.sleep(0.4)
        seen = list(nudged)
        release.set()
    assert seen == [("No|OK|Ok", "OK|Ok")]


def test_progress_nudge_defaults_are_conservative() -> None:
    p = wp._Progress(Path("unused.log"), total=1)
    assert p.nudge_after >= 10.0 and p.nudge_every >= p.nudge_after
    assert p.nudge_wait <= 3.0


# ─── focus is serialised ─────────────────────────────────────────────────────


def test_only_one_focus_taking_script_runs_at_a_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """A nudge and a watchdog answer must not both drive Word's focus at once."""
    inside = wp.threading.Semaphore(0)
    overlap: list[int] = []
    active = [0]
    lock = wp.threading.Lock()

    def fake_osa(script, *args, timeout=60.0):
        with lock:
            active[0] += 1
            overlap.append(active[0])
        wp.time.sleep(0.05)
        with lock:
            active[0] -= 1
        inside.release()
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    threads = [wp.threading.Thread(target=wp.answer_alert, args=("OK|Ok",), kwargs={"wait": 0.1}) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(3)
    assert max(overlap) == 1


def test_a_nudge_skips_when_focus_is_already_taken(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda *a, **k: calls.append("osa") or (0, "", ""))
    with wp._FOCUS_LOCK:
        assert wp.answer_alert("OK|Ok", wait=0.1, skip_if_busy=True) == []
    assert calls == []


# ─── CLI ─────────────────────────────────────────────────────────────────────


def test_cli_no_focus_turns_focus_off_for_the_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    seen: dict[str, bool] = {}

    def fake_convert(*a, **k):
        seen["focus"] = wp._focus.get()
        return []

    monkeypatch.setattr(wp, "preflight", lambda *a, **k: "")
    monkeypatch.setattr(wp, "convert_folder", fake_convert)
    monkeypatch.setattr(wp.WordSession, "quit_if_ours", lambda self: None)
    monkeypatch.setattr(wp.Watchdogs, "start", lambda self: None)
    monkeypatch.setattr(wp.Watchdogs, "stop", lambda self: None)
    src = tmp_path / "src"
    src.mkdir()
    assert CliRunner().invoke(wp.app, ["--src", str(src), "--no-check-preset", "--no-focus"]).exit_code == 0
    assert seen == {"focus": False}
    assert CliRunner().invoke(wp.app, ["--src", str(src), "--no-check-preset"]).exit_code == 0
    assert seen == {"focus": True}
    assert wp._focus.get() is True  # the CLI's choice does not leak past the run


def test_an_ordinary_alert_does_not_activate_word_to_look_for_a_grant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The dump names the buttons; Word is activated only when one of them is a grant."""
    shown = iter([_dump(("OK\t", ERROR_TEXT)), _dump(("Select…\tCancel\t", ""))])
    used: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        if args and args[0] == wp.WORD_PROC:
            used.append(script)
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._PRESS:
            return 0, "OK", ""
        if script is wp._PRESS_ACTIVATED:
            return 0, "Select…", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    _run(dogs, lambda: dogs.granted >= 1)

    assert dogs.dismissed == 1 and dogs.granted == 1
    assert used.index(wp._PRESS) < used.index(wp._PRESS_ACTIVATED)
    assert used[: used.index(wp._PRESS) + 1] == [wp._DUMP_DIALOGS, wp._PRESS]


def test_redline_cli_shares_the_focus_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("word_redline", scripts / "word_redline.py")
    assert spec and spec.loader
    wr = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "word_redline", wr)
    monkeypatch.setitem(sys.modules, "word_pdf", wp)
    spec.loader.exec_module(wr)

    seen: list[bool] = []
    monkeypatch.setattr(wr, "redline_preflight", lambda *a, **k: "")
    monkeypatch.setattr(wr, "redline_folders", lambda *a, **k: seen.append(wp._focus.get()) or [])
    monkeypatch.setattr(wp.WordSession, "quit_if_ours", lambda self: None)
    monkeypatch.setattr(wp.Watchdogs, "start", lambda self: None)
    monkeypatch.setattr(wp.Watchdogs, "stop", lambda self: None)
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    args = ["--a", str(a), "--b", str(b), "--out", str(tmp_path / "out"), "--no-check-preset"]
    assert CliRunner().invoke(wr.app, [*args, "--no-focus"]).exit_code == 0
    assert CliRunner().invoke(wr.app, args).exit_code == 0
    assert seen == [False, True]
    assert wp._focus.get() is True


def test_the_owed_ok_is_looked_for_at_most_once_per_owe_every(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each look is a focus flip; the batch progress check covers the gaps between them."""
    shown = iter([_dump(("Yes\tNo\t", REPAIR_TEXT))])
    looks: list[float] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._ANSWER:
            if "No" in args:
                return 0, f"No{US}{REPAIR_TEXT}{RS}", ""
            looks.append(wp.time.monotonic())
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.005, owe_window=5.0, owe_every=0.1)
    _run(dogs, lambda: len(looks) >= 3)

    assert len(looks) >= 3
    assert all(b - a >= 0.09 for a, b in zip(looks, looks[1:], strict=False))


# ─── a declined file is the file's fault, not Word's: no retry, no recycle ───


def test_declined_file_is_read_from_words_own_words() -> None:
    assert wp.declined_file(REPAIR_TEXT) == "00003__docxodus__deal.docx"
    assert wp.declined_file("Word found unreadable content in a b c.docx. Do you want") == "a b c.docx"
    assert wp.declined_file(ERROR_TEXT) == ""
    assert wp.declined_file("") == ""


def test_watchdog_marks_the_declined_file_in_the_batch_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = tmp_path / "batch-pdf-1.log"
    log.write_text("[ok]\t0\n")
    shown = iter([_dump(("Yes\tNo\t", REPAIR_TEXT))])

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(shown, ""), "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._ANSWER:
            return 0, f"No{US}{REPAIR_TEXT}{RS}OK{US}{ERROR_TEXT}{RS}", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    monkeypatch.setattr(wp, "_BATCH_LOG", log)
    dogs = wp.Watchdogs(poll=0.01)
    _run(dogs, lambda: dogs.declined >= 1)
    assert log.read_text() == "[ok]\t0\n[declined]\t00003__docxodus__deal.docx\n"


def test_no_batch_log_means_no_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "_BATCH_LOG", None)
    wp.mark_declined("x.docx")  # nothing to write to, nothing raised


def test_nudge_marks_a_declined_file_too(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = tmp_path / "batch-pdf-1.log"
    log.write_text("")
    monkeypatch.setattr(wp, "_BATCH_LOG", log)
    monkeypatch.setattr(wp.logger, "info", lambda m: None)
    monkeypatch.setattr(wp.logger, "warning", lambda m: None)
    monkeypatch.setattr(wp, "answer_alert", lambda *steps, **kw: [("No", REPAIR_TEXT), ("OK", ERROR_TEXT)])
    with wp._Progress(log, total=1, poll=0.01, nudge_after=0.02, nudge_every=60, diagnose=lambda p: ""):
        deadline = wp.time.monotonic() + 3
        while "[declined]" not in log.read_text() and wp.time.monotonic() < deadline:
            wp.time.sleep(0.02)
    assert "[declined]\t00003__docxodus__deal.docx\n" in log.read_text()


def test_batch_scripts_fail_a_declined_file_instead_of_retrying_it() -> None:
    for src in (wp._EXPORT_BATCH, wp._EXPORT_BATCH_KEEP_OPEN):
        assert "on wasDeclined(logPath, p)" in src
        assert 'logText contains ("[declined]" & tab & my baseName(p))' in src
        assert "if my wasDeclined(logPath, inP) then" in src
        assert '"repair prompt declined; Word could not read it"' in src
        # the streak rule stays for the undeclined case
        assert "emptyStreak ≥ 3" in src
        assert src.index("if my wasDeclined(logPath, inP) then") < src.index("set emptyStreak to emptyStreak + 1")


def test_parse_batch_log_reads_declined_markers() -> None:
    log = wp.parse_batch_log("[declined]\t00001__a.docx\n[retry]\t1\tdocument loaded empty\n[done]\t0\t0\n")
    assert log.declined == {"00001__a.docx"}
    assert log.retried == {"1": "document loaded empty"}


def test_run_batch_with_resume_does_not_retry_or_recycle_a_declined_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The marker can land after the script already logged [retry]; Python closes the gap."""
    manifests: list[list[str]] = []

    def fake(script, *args, timeout=60.0):
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        manifests.append([r[0] for r in rows])
        lines = []
        for r in rows:
            if r[0] == "1":
                lines.append("[declined]\t" + Path(r[1]).name)
                lines.append("[retry]\t1\tdocument loaded empty (Word could not read it)")
            else:
                lines.append(f"[ok]\t{r[0]}")
        lines.append("[done]\t0\t0")
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake)
    session = wp.WordSession()
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)
    rows = [(str(i), f"/in/0000{i}__doc{i}.docx", f"/out/{i}.pdf") for i in range(3)]
    got = wp.run_batch_with_resume("SCRIPT", rows, tmp_path, per_item_timeout=10, session=session)

    assert manifests == [["0", "1", "2"]]  # one pass, nothing retried
    assert recycled == []
    assert got["0"] == (True, "") and got["2"] == (True, "")
    assert got["1"][0] is False and "repair prompt declined" in got["1"][1]


def test_crash_limit_reaches_the_batch_and_the_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from typer.testing import CliRunner

    seen: list[int] = []

    def fake_resume(script, rows, work_dir, *, per_item_timeout, session, recycle_paths=(), max_passes=3, crash_limit=2, label=""):
        seen.append(crash_limit)
        return {r[0]: (False, "x") for r in rows}

    monkeypatch.setattr(wp, "run_batch_with_resume", fake_resume)
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.docx").write_bytes(b"x")
    session = wp.WordSession()
    session.preflighted = session.started_clean = True
    wp.convert_folder(src, tmp_path / "out", session=session, crash_limit=1)
    assert seen == [1]

    def fake_preflight(sess, **kw):
        sess.preflighted = sess.started_clean = True
        return ""

    monkeypatch.setattr(wp, "preflight", fake_preflight)
    monkeypatch.setattr(wp.WordSession, "quit_if_ours", lambda self: None)
    monkeypatch.setattr(wp.Watchdogs, "start", lambda self: None)
    monkeypatch.setattr(wp.Watchdogs, "stop", lambda self: None)
    r = CliRunner().invoke(wp.app, ["--src", str(src), "--out", str(tmp_path / "out2"), "--no-check-preset", "--crash-limit", "1"])
    assert r.exit_code == 1, r.output  # the fake fails the file; the flag reached the batch
    assert seen == [1, 1]
    assert CliRunner().invoke(wp.app, ["--src", str(src), "--out", str(tmp_path / "out3"), "--no-check-preset", "--crash-limit", "0"]).exit_code == 2


def test_compare_batch_script_fails_a_declined_base_instead_of_retrying_it(monkeypatch: pytest.MonkeyPatch) -> None:
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("word_redline", scripts / "word_redline.py")
    assert spec and spec.loader
    wr = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "word_redline", wr)
    monkeypatch.setitem(sys.modules, "word_pdf", wp)
    spec.loader.exec_module(wr)
    for src in (wr._COMPARE_BATCH, wr._COMPARE_BATCH_KEEP_OPEN):
        assert "if my wasDeclined(logPath, baseP) then" in src
        assert '"repair prompt declined; Word could not read the base"' in src
        assert "emptyStreak ≥ 3" in src
    import inspect
    assert inspect.signature(wr.redline_folders).parameters["crash_limit"].default == 2
    assert "--crash-limit" in str(inspect.signature(wr.main).parameters["crash_limit"].annotation)


# ─── the document saved is the one `open` produced, never `document 1` ───────


def test_export_scripts_find_the_opened_document_by_exclusion() -> None:
    """Seen live 2026-10-14: a leftover document survived close-all, a broken file's open
    produced nothing, and `document 1` was the leftover, saved under the broken file's name."""
    for src in (wp._EXPORT_PDF, wp._EXPORT_PDF_KEEP_OPEN, wp._EXPORT_BATCH, wp._EXPORT_BATCH_KEEP_OPEN):
        assert "set theDoc to document 1" not in src
        assert "set seenBeforeOpen to {}" in src
        assert "if seenBeforeOpen does not contain nm then" in src
        assert 'error "open produced " & newCount & " new documents, none named " & wantName & "; refusing to guess"' in src
        assert src.index("set seenBeforeOpen to {}") < src.index("open") < src.index("if theDoc is missing value then")
        # the new document NAMED after the file; a ghost named "Document1" is new too and is not it
        assert "if (nm as string) is wantName then set theDoc to document i" in src
        # the mismatch branch closes only a document carrying the file's name, in both variants
        assert "if (name of document i as string) is wantName then close document i saving no" in src
        assert "close every document saving no" not in src[src.index("if theDoc is missing value then"):src.index("count of paragraphs")]


def test_export_batch_reports_a_declined_file_that_opened_nothing_as_declined() -> None:
    src = wp._EXPORT_BATCH
    assert 'errMsg contains "new documents"' in src
    # one branch since 2026-10-14 evening: empty load, no new document and
    # "doesn't understand" all ask wasDeclined before deciding file vs Word
    assert src.count("my wasDeclined(logPath, inP)") == 1


def test_a_declined_file_that_opened_nothing_is_reported_as_declined(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The script can log the [fail] before the watchdog's [declined] line lands."""

    def fake(script, *args, timeout=60.0):
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines = ["[fail]\t0\topen produced 0 new documents; refusing to guess",
                 "[declined]\t" + Path(rows[0][1]).name, "[ok]\t1", "[done]\t1\t1"]
        log.write_text("\n".join(lines) + "\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake)
    session = wp.WordSession()
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    rows = [("0", "/in/00000__bad.docx", "/out/0.pdf"), ("1", "/in/00001__good.docx", "/out/1.pdf")]
    got = wp.run_batch_with_resume("SCRIPT", rows, tmp_path, per_item_timeout=10, session=session)
    assert got["0"][0] is False and got["0"][1].startswith("repair prompt declined")
    assert "0 new documents" in got["0"][1]
    assert got["1"] == (True, "")


def test_accept_all_rebinds_by_the_saved_name_not_document_1() -> None:
    src = wp.batch_script(close_documents=True, accept=True)
    assert "set theDoc to document 1" not in src
    assert "set theDoc to document (my baseName(docxP))" in src


# ─── recycle kills Word only when it refuses to quit ──────────────────────────


def _recycle_harness(monkeypatch: pytest.MonkeyPatch, alive_sequence: list[bool]):
    """pgrep answers from `alive_sequence` (last value repeats); every other command is recorded."""
    cmds: list[list[str]] = []
    osas: list[str] = []
    answers = iter(alive_sequence)
    last = [alive_sequence[-1]]

    def fake_run(cmd, **kw):
        cmds.append(list(cmd))

        class _Done:
            returncode = 0

        if cmd[0] == "pgrep":
            last[0] = next(answers, last[0])
            _Done.returncode = 0 if last[0] else 1
        return _Done()

    monkeypatch.setattr(wp.subprocess, "run", fake_run)
    monkeypatch.setattr(wp, "osa", lambda script, *a, **k: osas.append(script) or (0, "", ""))
    monkeypatch.setattr(wp.time, "sleep", lambda _s: None)
    session = wp.WordSession(launched_by_us=True)
    warmed: list[bool] = []
    monkeypatch.setattr(session, "warm", lambda: warmed.append(True) or True)
    monkeypatch.setattr(session, "clean_after_kill", lambda *f: None)
    return session, cmds, osas, warmed


def test_recycle_never_kills_a_word_that_quits_when_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    # alive at the check, alive for two polls after the quit, then gone
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True, True, True, False])
    session.answer_grace = 0.0
    assert session.recycle() is True
    assert any("quit saving no" in s for s in osas)
    assert not any(c[0] == "pkill" for c in cmds), cmds
    assert warmed == [True]


def test_recycle_relaunches_a_crashed_word_without_quitting_or_killing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    """`quit` sent to a Word that is not running would launch it just to kill it again."""
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [False])
    assert session.recycle() is True
    assert osas == []
    assert not any(c[0] == "pkill" for c in cmds)
    assert warmed == [True]
    assert session.restarts == 1


def test_recycle_escalates_only_when_word_refuses_to_quit(monkeypatch: pytest.MonkeyPatch) -> None:
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True])
    session.quit_grace = 0.0
    session.answer_grace = 0.0
    assert session.recycle() is True
    assert any("quit saving no" in s for s in osas)
    kills = [c for c in cmds if c[0] == "pkill"]
    assert kills[0] == ["pkill", "-x", wp.WORD_PROC]
    assert kills[-1] == ["pkill", "-9", "-x", wp.WORD_PROC]
    assert warmed == [True]


def test_quit_grace_default_gives_word_time_to_close_its_documents() -> None:
    assert wp.WordSession().quit_grace >= 15.0


# ─── siblings of a failed pair go to the back ────────────────────────────────


def test_parse_batch_log_reads_defer_lines() -> None:
    log = wp.parse_batch_log("[fail]\t1\tboom\n[defer]\t2\n[defer]\t3\n[ok]\t4\n[done]\t1\t1\n")
    assert log.deferred == {"2", "3"}
    assert log.results["4"] == (True, "")
    assert log.done


def test_deferred_siblings_run_next_pass_without_a_word_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The script defers the siblings itself; the pass reached [done]; Word is fine."""
    manifests: list[list[str]] = []
    calls = {"n": 0}

    def fake(script, *args, timeout=60.0):
        calls["n"] += 1
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t")[0] for ln in manifest.read_text().splitlines() if ln]
        manifests.append(rows)
        if calls["n"] == 1:
            log.write_text("[fail]\t1\tcompare blew up\n[defer]\t2\n[defer]\t3\n[ok]\t4\n[done]\t1\t1\n")
        else:
            log.write_text("".join(f"[ok]\t{r}\n" for r in rows) + "[done]\t2\t0\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake)
    session = wp.WordSession()
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)
    rows = [(str(i), f"/in/a{i}", f"/in/b{i}", f"/out/{i}") for i in range(1, 5)]
    groups = {"1": frozenset({"A", "B"}), "2": frozenset({"A", "C"}), "3": frozenset({"B", "D"}), "4": frozenset({"E", "F"})}
    got = wp.run_batch_with_resume("SCRIPT", rows, tmp_path, per_item_timeout=10, session=session, groups=groups, max_passes=1)

    assert manifests == [["1", "2", "3", "4"], ["2", "3"]]
    assert recycled == []  # nothing wrong with Word: the pass finished
    assert got["1"][0] is False and got["2"] == (True, "") and got["3"] == (True, "") and got["4"] == (True, "")


def test_siblings_of_a_crashed_pair_go_behind_everything_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifests: list[list[str]] = []
    calls = {"n": 0}

    def fake(script, *args, timeout=60.0):
        calls["n"] += 1
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t")[0] for ln in manifest.read_text().splitlines() if ln]
        manifests.append(rows)
        if calls["n"] == 1:
            log.write_text("[retry]\t1\tMicrosoft Word got an error: Connection is invalid.\n[done]\t0\t0\n")
        else:
            log.write_text("".join(f"[ok]\t{r}\n" for r in rows) + "[done]\t9\t0\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake)
    session = wp.WordSession()
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    rows = [(str(i), f"/in/a{i}", f"/in/b{i}", f"/out/{i}") for i in range(1, 6)]
    groups = {"1": frozenset({"A", "B"}), "2": frozenset({"A", "X"}), "3": frozenset({"Y", "Z"}), "4": frozenset({"B", "W"}), "5": frozenset({"V", "U"})}
    wp.run_batch_with_resume("SCRIPT", rows, tmp_path, per_item_timeout=10, session=session, groups=groups, crash_limit=2)

    assert manifests[0] == ["1", "2", "3", "4", "5"]
    assert manifests[1][:2] == ["3", "5"]  # the unrelated pairs first
    assert set(manifests[1][2:]) == {"1", "2", "4"}  # the crasher and both its siblings last


def test_compare_batch_defers_pairs_that_share_a_failed_file(monkeypatch: pytest.MonkeyPatch) -> None:
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("word_redline", scripts / "word_redline.py")
    assert spec and spec.loader
    wr = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "word_redline", wr)
    monkeypatch.setitem(sys.modules, "word_pdf", wp)
    spec.loader.exec_module(wr)
    for src in (wr._COMPARE_BATCH, wr._COMPARE_BATCH_KEEP_OPEN):
        assert "if (count of f) is 6 then" in src
        assert "set keyA to item 5 of f" in src and "set keyB to item 6 of f" in src
        assert "if (badKeys contains keyA) or (badKeys contains keyB) then" in src
        assert 'my logLine(logPath, "[defer]" & tab & itemId)' in src
        assert "set end of badKeys to keyA" in src and "set end of badKeys to keyB" in src
        # the bad keys are recorded before the error is classified, so a crash exit still has them
        assert src.index("set end of badKeys to keyA") < src.index('if errMsg contains "timed out" then')
    assert wr.pair_key(Path("/x/a b.docx")) == str(Path("/x/a b.docx").resolve())
    assert "\t" not in wr.pair_key(Path("/x/a\tb.docx"))


def test_redline_batched_manifest_carries_both_files_as_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("word_redline", scripts / "word_redline.py")
    assert spec and spec.loader
    wr = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "word_redline", wr)
    monkeypatch.setitem(sys.modules, "word_pdf", wp)
    spec.loader.exec_module(wr)

    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir(), b.mkdir()
    for name in ("x.docx", "y.docx"):
        (a / name).write_bytes(b"PK"), (b / name).write_bytes(b"PK")
    seen: dict[str, object] = {}

    def fake_resume(script, rows, work_dir, *, per_item_timeout, session, recycle_paths=(), max_passes=3, crash_limit=2, label="", groups=None):
        if label.strip() == "compare":
            seen["rows"] = rows
            seen["groups"] = groups
        return {r[0]: (False, "x") for r in rows}

    monkeypatch.setattr(wr, "run_batch_with_resume", fake_resume)
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    session = wp.WordSession()
    session.preflighted = session.started_clean = True
    monkeypatch.setattr(session, "warm", lambda: True)
    wr.redline_folders(a, b, tmp_path / "out", emit=wr.Emit.DOCX, docx_dir=tmp_path / "docx", session=session)

    rows = seen["rows"]
    assert all(len(r) == 6 for r in rows)
    assert rows[0][4] == wr.pair_key(a / "x.docx") and rows[0][5] == wr.pair_key(b / "x.docx")
    assert seen["groups"] == {r[0]: frozenset({r[4], r[5]}) for r in rows}


# ─── the default closes documents, so a Word that held some is still ours to restart ──


def test_recycle_restarts_word_under_the_default_close_policy_even_if_it_held_documents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seen 2026-10-14: 2 documents open at preflight, Word crashed at item 792 of 1329, and the
    refusal left a self-relaunched, poisoned Word in place for 19 passes."""
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [False])
    session.started_clean = False
    session.closes_documents = True
    assert session.recycle() is True
    assert warmed == [True]


def test_recycle_still_refuses_under_do_not_close_with_documents_open(monkeypatch: pytest.MonkeyPatch) -> None:
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True])
    session.started_clean = False
    session.closes_documents = False
    assert session.recycle() is False
    assert warmed == [] and osas == [] and not any(c[0] == "pkill" for c in cmds)


def test_preflight_records_the_close_policy_on_the_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(wp, "word_pid", lambda: "stub")  # pgrep would count as reaching Word
    for policy in (True, False):
        session = wp.WordSession()
        monkeypatch.setattr(session, "warm", lambda: True)
        monkeypatch.setattr(session, "open_document_count", lambda: 0)
        monkeypatch.setattr(wp, "osa", lambda s, *a, **k: (0, "missing value", ""))  # the preflight close-all health check
        wp.preflight(session, allow_open_docs=False, close_documents=policy)
        assert session.closes_documents is policy


# ─── one Word, one driver: a cross-process lock ──────────────────────────────


def test_word_lock_is_exclusive_and_names_its_holder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "WORD_LOCK_PATH", tmp_path / "word_driver.lock")
    with wp.WordLock(label="first") as first:
        assert first.held
        text = (tmp_path / "word_driver.lock").read_text()
        assert str(wp.os.getpid()) in text and "first" in text
        second = wp.WordLock(label="second", wait=0.3, poll=0.05)
        with pytest.raises(wp.WordBusy) as exc:
            second.__enter__()
        assert "first" in str(exc.value) and str(wp.os.getpid()) in str(exc.value)
    # released: the next taker gets it at once
    with wp.WordLock(label="third", wait=0.3) as third:
        assert third.held


def test_word_lock_waits_for_the_holder_and_logs_while_it_waits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "WORD_LOCK_PATH", tmp_path / "word_driver.lock")
    warned: list[str] = []
    monkeypatch.setattr(wp.logger, "warning", lambda m: warned.append(str(m)))
    holder = wp.WordLock(label="holder")
    holder.__enter__()
    release_at = wp.time.monotonic() + 0.4

    def release_later():
        while wp.time.monotonic() < release_at:
            wp.time.sleep(0.02)
        holder.__exit__(None, None, None)

    t = wp.threading.Thread(target=release_later)
    t.start()
    started = wp.time.monotonic()
    with wp.WordLock(label="waiter", wait=5.0, poll=0.05, say_every=0.1) as waiter:
        assert waiter.held
        assert wp.time.monotonic() - started >= 0.3
    t.join()
    assert any("holder" in m and "waiting" in m for m in warned)


def test_convert_folder_refuses_when_word_is_busy_and_says_who(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "WORD_LOCK_PATH", tmp_path / "word_driver.lock")
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.docx").write_bytes(b"x")
    session = wp.WordSession()
    session.preflighted = session.started_clean = True
    with wp.WordLock(label="another batch"):
        results = wp.convert_folder(src, tmp_path / "out", session=session, lock_wait=0.2)
    assert len(results) == 1 and results[0].ok is False
    assert "another batch" in results[0].error and "Word is in use" in results[0].error


def test_cli_lock_wait_is_a_duration_and_zero_means_refuse_at_once() -> None:
    import inspect
    assert inspect.signature(wp.convert_folder).parameters["lock_wait"].default >= 600.0
    assert "--lock-wait" in str(inspect.signature(wp.main).parameters["lock_wait"].annotation)


def test_redline_folders_refuses_when_word_is_busy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("word_redline", scripts / "word_redline.py")
    assert spec and spec.loader
    wr = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "word_redline", wr)
    monkeypatch.setitem(sys.modules, "word_pdf", wp)
    spec.loader.exec_module(wr)
    monkeypatch.setattr(wp, "WORD_LOCK_PATH", tmp_path / "word_driver.lock")
    a, b = tmp_path / "A", tmp_path / "B"
    a.mkdir(), b.mkdir()
    (a / "x.docx").write_bytes(b"PK"), (b / "x.docx").write_bytes(b"PK")
    session = wp.WordSession()
    session.preflighted = session.started_clean = True
    with wp.WordLock(label="word_pdf.py corpus"):
        results = wr.redline_folders(a, b, tmp_path / "out", session=session, lock_wait=0.2)
    assert len(results) == 1 and not results[0].ok
    assert "word_pdf.py corpus" in results[0].error


def test_recycle_of_any_running_word_that_stops_answering_quits_it_and_says_for_how_long(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True, True, True, False])
    session.launched_by_us = False  # ownership makes no difference
    session.answer_grace = 0.0
    monkeypatch.setattr(session, "responsive", lambda: False)
    assert session.recycle() is True
    assert osas[0] == wp._CLOSE_ALL and any("quit saving no" in s for s in osas)
    assert warmed == [True]
    joined = "\n".join(said)
    assert "because Word was unresponsive for 0 s after the close-all" in joined
    assert joined.index("close every document saving no") < joined.index("quit saving no")


def test_recycle_of_a_found_word_that_answers_is_just_the_close_all(monkeypatch: pytest.MonkeyPatch) -> None:
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True])
    session.launched_by_us = False
    monkeypatch.setattr(session, "responsive", lambda: True)
    assert session.recycle() is True
    assert osas == [wp._CLOSE_ALL]
    assert not any(c[0] in ("pkill", "open") for c in cmds)
    assert warmed == []


# ─── the log says what is run, not a label for it ────────────────────────────


def _warnings(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    out: list[str] = []
    monkeypatch.setattr(wp.logger, "warning", lambda m: out.append(str(m)))
    monkeypatch.setattr(wp.logger, "info", lambda m: out.append(str(m)))
    monkeypatch.setattr(wp.logger, "error", lambda m: out.append(str(m)))
    return out


def test_recycle_logs_the_close_all_command_for_a_found_word(monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True])
    session.launched_by_us = False
    monkeypatch.setattr(session, "responsive", lambda: True)
    session.recycle()
    assert any("running: osascript -e 'tell application \"Microsoft Word\" to close every document saving no'" in m for m in said), said


def test_recycle_logs_quit_then_each_signal_with_its_command(monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True])
    session.quit_grace = 0.0
    session.answer_grace = 0.0
    session.recycle()
    joined = "\n".join(said)
    assert "running: osascript -e 'tell application \"Microsoft Word\" to quit saving no'" in joined
    assert "running: pkill -x 'Microsoft Word'" in joined
    assert "running: pkill -9 -x 'Microsoft Word'" in joined
    assert joined.index("quit saving no") < joined.index("pkill -x") < joined.index("pkill -9")


def test_recycle_logs_the_relaunch_of_a_crashed_word(monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [False])
    session.recycle()
    assert any("process is gone" in m and "relaunch" in m for m in said), said


def test_warm_logs_the_launch_command_and_how_long_word_took(monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    answers = iter([(1, "", ""), (0, "0", "")])
    monkeypatch.setattr(wp, "osa", lambda script, *a, **k: (0, "", "") if script is wp._SET_ALERTS else next(answers))
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: None)
    monkeypatch.setattr(wp.time, "sleep", lambda _s: None)
    monkeypatch.setattr(wp.WordSession, "_alive", staticmethod(lambda: False))
    assert wp.WordSession().warm() is True
    joined = "\n".join(said)
    assert "running: open -g -a '/Applications/Microsoft Word.app'" in joined
    assert "Word answered after" in joined


def test_pass_end_names_the_item_and_the_error_that_ended_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    calls = {"n": 0}

    def fake(script, *args, timeout=60.0):
        calls["n"] += 1
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t")[0] for ln in manifest.read_text().splitlines() if ln]
        if calls["n"] == 1:
            log.write_text("[ok]\t0\n[retry]\t1\tMicrosoft Word got an error: Connection is invalid.\n[done]\t1\t0\n")
        else:
            log.write_text("".join(f"[ok]\t{r}\n" for r in rows) + "[done]\t9\t0\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake)
    session = wp.WordSession()
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    rows = [(str(i), f"/in/{i}.docx", f"/out/{i}.pdf") for i in range(4)]
    wp.run_batch_with_resume("SCRIPT", rows, tmp_path, per_item_timeout=10, session=session, crash_limit=2)
    line = next(m for m in said if "pass 1 ended" in m)
    assert "item 1" in line and "Connection is invalid" in line
    assert "2 item(s) not reached, 1 to retry" in line
    assert "Word crashed" in line


# ─── close first, quit only when the close-all fails; every command reports back ──


def test_recovery_of_our_word_closes_documents_first_and_never_quits_when_that_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True])
    monkeypatch.setattr(session, "responsive", lambda: True)
    assert session.recycle() is True
    assert osas == [wp._CLOSE_ALL]
    assert not any(c[0] == "pkill" for c in cmds)
    assert warmed == []
    joined = "\n".join(said)
    assert joined.index("running: osascript -e 'tell application \"Microsoft Word\" to close every document saving no'") < joined.index("returned rc=0")


def test_recovery_of_our_word_quits_only_after_the_close_all_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True, True, True, False])
    session.answer_grace = 0.0
    monkeypatch.setattr(session, "responsive", lambda: False)
    assert session.recycle() is True
    assert osas[0] == wp._CLOSE_ALL and any("quit saving no" in s for s in osas)
    assert warmed == [True]
    joined = "\n".join(said)
    assert "unresponsive for 0 s after the close-all" in joined
    assert joined.index("close every document saving no") < joined.index("quit saving no")


def test_recovery_of_our_word_quits_when_the_close_all_itself_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True, False])
    monkeypatch.setattr(wp, "osa", lambda script, *a, **k: osas.append(script) or ((1, "", "Microsoft Word got an error: Connection is invalid.") if script is wp._CLOSE_ALL else (0, "", "")))
    monkeypatch.setattr(session, "responsive", lambda: True)
    assert session.recycle() is True
    assert any("quit saving no" in s for s in osas)
    joined = "\n".join(said)
    assert "returned rc=1" in joined and "Connection is invalid" in joined
    assert "because the close-all returned an error" in joined


def test_every_recovery_command_reports_its_result_on_the_next_line(monkeypatch: pytest.MonkeyPatch) -> None:
    said = _warnings(monkeypatch)
    session, cmds, osas, warmed = _recycle_harness(monkeypatch, [True])
    session.quit_grace = 0.0
    session.answer_grace = 0.0
    monkeypatch.setattr(session, "responsive", lambda: False)
    session.recycle()
    # after each "running:" line the very next [word] line is its result
    lines = [m for m in said if m.startswith("[word]")]
    for i, m in enumerate(lines):
        if "running:" in m:
            assert "returned" in lines[i + 1] or "Word's process" in lines[i + 1] or "gone" in lines[i + 1], (m, lines[i + 1])


# ─── the error reporter as the crash signal ─────────────────────────────────

MERP_TEXT = "There was a problem with Microsoft Word and we apologize for the inconvenience."


def _batch(tmp_path: Path, done: int) -> Path:
    """A batch manifest of three items and a log with `done` of them finished."""
    manifest = tmp_path / "batch-pdf-2.tsv"
    wp.write_manifest([("7", "/in/a.docx", "/out/a.pdf"), ("8", "/in/b.docx", "/out/b.pdf"), ("9", "/in/c.docx", "/out/c.pdf")], manifest)
    log = manifest.with_suffix(".log")
    log.write_text("".join(f"[ok]\t{rid}\n" for rid in ("7", "8")[:done]), encoding="utf-8")
    return log


def test_crash_signal_marks_the_current_item_and_ends_the_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-10-14 A/B: the reporter appears a median 5 s before the batch
    osascript reports `Connection is invalid`. With the signal on, the item
    Word was on is marked [retry] (a crash, for the crash limit) and the pass's
    osascript, found by its manifest path, is ended at once."""
    log = _batch(tmp_path, done=1)
    monkeypatch.setattr(wp, "_BATCH_LOG", log)
    ran: list[list[str]] = []
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: ran.append(list(cmd)) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(wp, "process_age_seconds", lambda name: 0.0)  # the reporter just appeared
    dogs = wp.Watchdogs(poll=0.01, kill_pass_on_crash=True)

    dogs._crash_signal(MERP_TEXT)

    lines = log.read_text(encoding="utf-8").splitlines()
    assert lines[-1].startswith("[retry]\t8\t"), lines
    assert "Connection is invalid" in lines[-1], "so parse_batch_log counts it as a crash"
    kills = [c for c in ran if c[0] == "pkill"]
    assert kills and kills[-1][:2] == ["pkill", "-f"] and kills[-1][2].endswith("batch-pdf-2\\.tsv"), ran
    assert "osascript" not in kills[-1][2], "never a blanket pkill of osascript"
    parsed = wp.parse_batch_log(log.read_text())
    assert "8" in parsed.crashed and "8" in parsed.retried

    dogs._crash_signal(MERP_TEXT)  # the reporter is still up on the next poll
    assert log.read_text(encoding="utf-8").splitlines().count(lines[-1]) == 1, "marked once per item"
    assert len([c for c in ran if c[0] == "pkill"]) == 1


def test_crash_signal_is_on_by_default_and_idle_without_a_running_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """On by default since the 2026-10-14 A/B (merp_kill: 251 s vs 382 s on 20
    crashers, nothing lost); `--no-crash-signal` turns it off. With no batch
    running (a crash during recovery, say) there is nothing to mark or end."""
    log = _batch(tmp_path, done=1)
    before = log.read_text()
    ran: list[list[str]] = []
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: ran.append(list(cmd)) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    assert wp.Watchdogs(poll=0.01).kill_pass_on_crash is True
    monkeypatch.setattr(wp, "_BATCH_LOG", log)
    wp.Watchdogs(poll=0.01, kill_pass_on_crash=False)._crash_signal(MERP_TEXT)
    monkeypatch.setattr(wp, "_BATCH_LOG", None)
    wp.Watchdogs(poll=0.01)._crash_signal(MERP_TEXT)
    assert log.read_text() == before and ran == []


def test_merp_poller_sends_the_crash_signal_before_pressing_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    dumps = iter([_dump(("OK\t", MERP_TEXT))])

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_DIALOGS:
            return (0, next(dumps, ""), "") if args[0] == wp.MERP_PROC else (0, "", "")
        if script is wp._PRESS:
            order.append("press")
            return 0, "OK", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01, kill_pass_on_crash=True)
    monkeypatch.setattr(dogs, "_crash_signal", lambda text: order.append(f"signal:{text[:9]}"))
    _run(dogs, lambda: dogs.dismissed >= 1)
    assert order[:2] == ["signal:There was", "press"]


def test_crash_signal_does_nothing_when_the_script_already_logged_the_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mixed-set A/B 2026-10-14: the batch script's own handler had written
    `[retry] <crasher>` before the reporter was seen, so "the first item without
    a line" was the NEXT, good, document, which was then marked as a crasher and
    (crash limit 1) lost. A crash-marked [retry] as the last line means the
    script saw the crash itself: nothing to mark, nothing to end."""
    log = _batch(tmp_path, done=1)
    with log.open("a") as fh:
        fh.write("[retry]\t8\tMicrosoft Word got an error: Connection is invalid.\n")
    before = log.read_text()
    ran: list[list[str]] = []
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: ran.append(list(cmd)) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(wp, "_BATCH_LOG", log)
    monkeypatch.setattr(wp, "process_age_seconds", lambda name: 1.0)
    wp.Watchdogs(poll=0.01)._crash_signal(MERP_TEXT)
    assert log.read_text() == before and ran == []


def test_crash_signal_ignores_a_reporter_older_than_the_running_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The reporter for the previous crash can surface after the next pass has
    started. A reporter process older than this pass's manifest is that one:
    Word did not crash on the current item."""
    log = _batch(tmp_path, done=1)
    before = log.read_text()
    ran: list[list[str]] = []
    infos: list[str] = []
    monkeypatch.setattr(wp.logger, "info", lambda m: infos.append(str(m)))
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: ran.append(list(cmd)) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(wp, "_BATCH_LOG", log)
    monkeypatch.setattr(wp, "process_age_seconds", lambda name: 3600.0)  # older than any pass here
    wp.Watchdogs(poll=0.01)._crash_signal(MERP_TEXT)
    assert log.read_text() == before and ran == []
    assert any("reporter is older than this pass" in m for m in infos), infos


def test_crash_signal_writes_the_mark_only_after_it_ended_a_live_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """pkill first, mark second: when nothing was there to end (rc 1), the pass
    had already finished on its own and its log is complete; adding a line then
    would name the wrong item."""
    log = _batch(tmp_path, done=1)
    before = log.read_text()
    monkeypatch.setattr(wp, "_BATCH_LOG", log)
    monkeypatch.setattr(wp, "process_age_seconds", lambda name: 0.0)  # a reporter that just appeared
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: SimpleNamespace(returncode=1, stdout="", stderr=""))
    wp.Watchdogs(poll=0.01)._crash_signal(MERP_TEXT)
    assert log.read_text() == before, "no process ended, so nothing is marked"
    order: list[str] = []

    def fake_run(cmd, **k):
        order.append("pkill:" + ("marked" if "[retry]" in log.read_text() else "unmarked"))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(wp.subprocess, "run", fake_run)
    wp.Watchdogs(poll=0.01)._crash_signal(MERP_TEXT)
    assert order == ["pkill:unmarked"], "the kill runs before the mark is written"
    assert log.read_text().splitlines()[-1].startswith("[retry]\t8\t")


def test_process_age_seconds_parses_ps_etime(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs = iter(["12345\n", "   01:02:03\n"])
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: SimpleNamespace(returncode=0, stdout=next(outputs), stderr=""))
    assert wp.process_age_seconds("Microsoft Error Reporting") == pytest.approx(3723.0)
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: SimpleNamespace(returncode=1, stdout="", stderr=""))
    assert wp.process_age_seconds("Microsoft Error Reporting") is None
    assert wp._parse_etime("2-01:02:03") == pytest.approx(2 * 86400 + 3723)
    assert wp._parse_etime("05:09") == pytest.approx(309.0)


# ─── a Word that answers but returns nothing is poison, not 70 failures ─────


def test_batch_scripts_treat_empty_opens_and_does_not_understand_as_poison(monkeypatch: pytest.MonkeyPatch) -> None:
    """2026-10-14 22:22: a self-relaunched Word answered `count of documents`
    but every `open` produced 0 new documents and every `close` errored
    "doesn't understand"; the batch recorded 70 final failures in 5 s. Those
    errors are Word's, not the files': they go through the empty-streak rule
    ([retry], three in a row end the pass and Word is recycled)."""
    scripts = _SCRIPT.parent
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location("word_redline", scripts / "word_redline.py")
    assert spec and spec.loader
    wr = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "word_redline", wr)
    monkeypatch.setitem(sys.modules, "word_pdf", wp)
    spec.loader.exec_module(wr)
    for src in (wp._EXPORT_BATCH, wr._COMPARE_BATCH):
        poison = src.index('else if errMsg contains "loaded empty" or errMsg contains "new documents" or errMsg contains "understand" then')
        decline = src.index("if my wasDeclined(logPath,", poison)
        assert decline > poison, "a declined repair prompt is still the file's fault"
        assert "emptyStreak ≥ 3" in src[poison:]
        assert 'else if errMsg contains "new documents" and my wasDeclined' not in src, "merged into the poison branch"


def test_preflight_health_checks_the_close_all_and_recycles_a_word_that_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Word that answers the document count but errors on `close every
    document` is the degraded one; preflight recycles it before the batch
    rather than letting the batch find out item by item."""
    calls: list[str] = []
    closes = iter([(1, "", "execution error: Microsoft Word got an error: every document doesn’t understand the “close” message. (-1708)"), (0, "missing value", "")])

    def fake_osa(script, *args, timeout=60.0):
        calls.append(script)
        if script is wp._CLOSE_ALL:
            return next(closes)
        if script is wp._COUNT_DOCS:
            return 0, "0", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(wp, "word_pid", lambda: "stub")  # pgrep would count as reaching Word
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    recycled: list[bool] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(True) or True)

    assert wp.preflight(session, allow_open_docs=False, close_documents=True) == ""
    assert recycled == [True], "the first close-all errored, so Word was recycled once"
    assert calls.count(wp._CLOSE_ALL) == 2, "and checked again afterwards"


def test_preflight_refuses_when_word_still_errors_after_the_recycle(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_osa(script, *args, timeout=60.0):
        if script is wp._CLOSE_ALL:
            return 1, "", "execution error: every document doesn’t understand the “close” message. (-1708)"
        if script is wp._COUNT_DOCS:
            return 0, "0", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(wp, "word_pid", lambda: "stub")  # pgrep would count as reaching Word
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "recycle", lambda *f: True)
    problem = wp.preflight(session, allow_open_docs=False, close_documents=True)
    assert "doesn’t understand" in problem and "recycle" in problem


def test_preflight_under_do_not_close_does_not_close_anything(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: calls.append(s) or ((0, "0", "") if s is wp._COUNT_DOCS else (0, "", "")))
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(wp, "word_pid", lambda: "stub")  # pgrep would count as reaching Word
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    wp.preflight(session, allow_open_docs=True, close_documents=False)
    assert wp._CLOSE_ALL not in calls


# ─── a pass that ends on empty loads restarts Word, after one look for a modal ──


def test_recycle_restart_skips_the_close_all_and_says_why(monkeypatch: pytest.MonkeyPatch) -> None:
    """`recycle(restart=True)` is for a Word that answers but returns nothing
    (three empty loads in a row, 2026-10-14 22:22 and 22:45): a close-all on
    an empty Word succeeds and changes nothing, so the same degraded instance
    was reused 39 times. Restart goes straight to quit, then relaunch."""
    ran: list[object] = []
    said: list[str] = []
    monkeypatch.setattr(wp.logger, "warning", lambda m, *a, **k: said.append(str(m)))
    monkeypatch.setattr(wp.logger, "info", lambda m, *a, **k: said.append(str(m)))
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: ran.append(s) or (0, "", ""))
    session = wp.WordSession()
    monkeypatch.setattr(session, "_alive", lambda: True)
    monkeypatch.setattr(session, "_gone_within", lambda *a, **k: True)
    monkeypatch.setattr(session, "clean_after_kill", lambda *f: None)
    monkeypatch.setattr(session, "warm", lambda: True)

    assert session.recycle(restart=True, because="Word returned nothing for 3 documents in a row") is True
    assert wp._CLOSE_ALL not in ran and wp._QUIT in ran
    assert any("because Word returned nothing for 3 documents in a row" in m and "asking Word to quit" in m for m in said), said


def test_resume_restarts_word_after_a_poison_pass_and_looks_for_a_hidden_modal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Three [retry] lines without a crash mark end a pass: Word was answering
    and returning nothing. Before the restart, Word is brought forward once
    (`decline_repair_prompt`), because a modal that System Events cannot see
    from the background is the usual reason (2026-10-14 23:00: another
    driver's repair prompt). Then `recycle(restart=True)`, not a close-all."""
    rows = [("0", "/in/a.docx", "/out/a.pdf"), ("1", "/in/b.docx", "/out/b.pdf"), ("2", "/in/c.docx", "/out/c.pdf"), ("3", "/in/d.docx", "/out/d.pdf")]
    passes = iter([
        "[retry]\t0\topen produced 0 new documents\n[retry]\t1\topen produced 0 new documents\n[retry]\t2\topen produced 0 new documents\n",
        "[ok]\t3\n[ok]\t0\n[ok]\t1\n[ok]\t2\n[done]\t4\t0\n",
    ])

    def fake_osa(script, *args, timeout=60.0):
        Path(args[1]).write_text(next(passes), encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = wp.WordSession()
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(session, "recycle", lambda *f, **kw: calls.append(kw) or True)
    looked: list[bool] = []
    monkeypatch.setattr(wp, "decline_repair_prompt", lambda: looked.append(True) or [])

    final = wp.run_batch_with_resume("SCRIPT", rows, tmp_path, per_item_timeout=10, session=session, crash_limit=2)

    assert all(ok for ok, _ in final.values()), final
    assert looked == [True], "one look at Word's front before the restart"
    assert calls and calls[0].get("restart") is True and "nothing" in str(calls[0].get("because"))


def test_resume_keeps_close_all_first_after_a_crash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [("0", "/in/a.docx", "/out/a.pdf"), ("1", "/in/b.docx", "/out/b.pdf")]
    passes = iter(["[retry]\t0\tMicrosoft Word got an error: Connection is invalid.\n", "[ok]\t1\n[ok]\t0\n[done]\t2\t0\n"])

    def fake_osa(script, *args, timeout=60.0):
        Path(args[1]).write_text(next(passes), encoding="utf-8")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = wp.WordSession()
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(session, "recycle", lambda *f, **kw: calls.append(kw) or True)
    monkeypatch.setattr(wp, "decline_repair_prompt", lambda: pytest.fail("no focus flip for a plain crash"))
    wp.run_batch_with_resume("SCRIPT", rows, tmp_path, per_item_timeout=10, session=session, crash_limit=2)
    assert calls and not calls[0].get("restart")


def test_preflight_logs_words_pid(monkeypatch: pytest.MonkeyPatch) -> None:
    """A pid that changes between runs or recoveries means something else
    restarted Word (2026-10-14 22:28 and 22:59: another session's driver)."""
    infos: list[str] = []
    monkeypatch.setattr(wp.logger, "info", lambda m, *a, **k: infos.append(str(m)))
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: ((0, "0", "") if s is wp._COUNT_DOCS else (0, "missing value", "")))
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(wp, "word_pid", lambda: "4242")
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    assert wp.preflight(session, allow_open_docs=False, close_documents=True) == ""
    assert any("word_pid=4242" in m for m in infos), infos
