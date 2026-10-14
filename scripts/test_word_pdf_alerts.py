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
    dogs = wp.Watchdogs(poll=0.01, owe_window=5.0)
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
    dogs = wp.Watchdogs(poll=0.01, owe_window=0.05)
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
