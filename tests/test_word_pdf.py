"""Spec for the reusable half of the Word driver pair (``scripts/word_pdf.py``).

Everything exercised here is pure or filesystem-only: no Microsoft Word, no
macOS, no ``osascript``. The Word-facing calls are reached through ``osa``,
which is patched, so the AppleScript strings themselves are covered as data
(argument order, argv shape) rather than by execution.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Every test here stubs Word. The fence turns a missed stub into a failure
# instead of a close-all sent to the Word that is actually running.
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


def _verified_session(**kw) -> wp.WordSession:
    """A session in the state `preflight()` leaves behind on a clean Word.

    `convert_folder()` refuses a supplied session that cannot show it was
    preflighted, because `started_clean` defaults to True and proves nothing.
    """
    session = wp.WordSession(**kw)
    session.preflighted = True
    session.started_clean = True
    return session


def _touch(p: Path, body: bytes = b"x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(body)
    return p


# ─── is_word_temp ────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("~$contract.docx", True),
        (".~lock.contract.docx", True),
        ("contract.docx", False),
        ("a~$b.docx", False),  # the marker is a prefix, not a substring
        ("~.docx", False),
    ],
)
def test_is_word_temp(name: str, expected: bool) -> None:
    assert wp.is_word_temp(name) is expected


# ─── iter_docx ───────────────────────────────────────────────────────────────


def test_iter_docx_sorted_and_filtered(tmp_path: Path) -> None:
    _touch(tmp_path / "b.docx")
    _touch(tmp_path / "a.docx")
    _touch(tmp_path / "~$a.docx")  # Word owner file
    _touch(tmp_path / "notes.txt")
    _touch(tmp_path / "sub" / "deep.docx")  # not direct child
    (tmp_path / "folder.docx").mkdir()  # a directory that ends in .docx

    assert [p.name for p in wp.iter_docx(tmp_path)] == ["a.docx", "b.docx"]


def test_iter_docx_empty_folder(tmp_path: Path) -> None:
    assert wp.iter_docx(tmp_path) == []


# ─── pdf_path_for ────────────────────────────────────────────────────────────


def test_pdf_path_for_beside_source(tmp_path: Path) -> None:
    docx = tmp_path / "in" / "deal.docx"
    assert wp.pdf_path_for(docx, None) == tmp_path / "in" / "deal.pdf"


def test_pdf_path_for_into_out_dir(tmp_path: Path) -> None:
    docx = tmp_path / "in" / "deal.docx"
    assert wp.pdf_path_for(docx, tmp_path / "out") == tmp_path / "out" / "deal.pdf"


# ─── classify_failure ────────────────────────────────────────────────────────


def test_classify_failure_produced_is_not_a_failure() -> None:
    assert wp.classify_failure(1, "noise", produced=True) == ""


def test_classify_failure_timeout() -> None:
    msg = wp.classify_failure(None, "", produced=False)
    assert "timed out" in msg


def test_classify_failure_uses_first_stderr_line_bounded() -> None:
    err = "first line of trouble\nsecond line\n"
    assert wp.classify_failure(1, err, produced=False) == "first line of trouble"
    assert len(wp.classify_failure(1, "z" * 500, produced=False)) == 200


def test_classify_failure_falls_back_to_exit_code() -> None:
    assert "exit 3" in wp.classify_failure(3, "   ", produced=False)


# ─── osa ─────────────────────────────────────────────────────────────────────


def test_osa_passes_script_and_args_as_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class _Done:
        returncode = 0
        stdout = " ok \n"
        stderr = ""

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        seen["kw"] = kw
        return _Done()

    monkeypatch.setattr(wp.subprocess, "run", fake_run)
    rc, out, err = wp.osa("SCRIPT", "a b", "c'd", timeout=5)

    assert (rc, out, err) == (0, "ok", "")
    # -e SCRIPT then bare arguments: nothing is interpolated into the source.
    assert seen["cmd"] == ["osascript", "-e", "SCRIPT", "a b", "c'd"]
    assert seen["kw"]["timeout"] == 5


def test_osa_timeout_never_reaches_for_pkill(monkeypatch: pytest.MonkeyPatch) -> None:
    """`subprocess.run` SIGKILLs its own child; pkill would hit everyone else's.

    A global `pkill osascript` would match this module's own watchdog threads —
    every poll is an osascript — and any automation the user is running.
    """
    other: list[list[str]] = []

    def fake_run(cmd, **kw):
        if cmd[0] == "osascript":
            raise wp.subprocess.TimeoutExpired(cmd, 1)
        other.append(cmd)

        class _Done:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Done()

    monkeypatch.setattr(wp.subprocess, "run", fake_run)
    rc, out, err = wp.osa("SCRIPT", timeout=1)

    assert rc is None and out == ""
    assert "timed out" in err
    assert other == []  # nothing beyond the one osascript call


def test_osa_timeout_asks_subprocess_to_kill_not_terminate() -> None:
    """The SIGKILL claim is about `subprocess.run`, so pin it to the stdlib."""
    import inspect

    src = inspect.getsource(wp.subprocess.run)
    body = src[src.index("except TimeoutExpired") :]
    assert "process.kill()" in body
    assert "terminate()" not in body


def test_osa_survives_missing_osascript(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, **kw):
        raise FileNotFoundError("osascript")

    monkeypatch.setattr(wp.subprocess, "run", fake_run)
    rc, out, err = wp.osa("SCRIPT")
    assert rc is None and out == "" and "osascript" in err


# ─── Stage ───────────────────────────────────────────────────────────────────


def test_stage_creates_in_out_inside_container_and_cleans_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = _touch(tmp_path / "src" / "deal.docx", b"body")

    with wp.Stage(prefix="spec") as stage:
        root = stage.root
        assert root is not None
        assert root.parent == tmp_path / "container"
        assert stage.inbox.is_dir() and stage.outbox.is_dir()

        placed = stage.place(src)
        assert placed == stage.inbox / "deal.docx"
        assert placed.read_bytes() == b"body"

    assert not root.exists()


def test_stage_place_as_avoids_same_name_collision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Name-paired redlines stage two files that share a filename."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    a = _touch(tmp_path / "a" / "deal.docx", b"A")
    b = _touch(tmp_path / "b" / "deal.docx", b"B")

    with wp.Stage(prefix="spec") as stage:
        pa = stage.place_as(a, "base__deal.docx")
        pb = stage.place_as(b, "rev__deal.docx")
        assert pa != pb
        assert pa.read_bytes() == b"A"
        assert pb.read_bytes() == b"B"


def test_stage_is_unique_per_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    with wp.Stage() as one, wp.Stage() as two:
        assert one.root != two.root


# ─── export_pdf ──────────────────────────────────────────────────────────────


def test_export_pdf_ok_when_osascript_succeeds_and_file_appears(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "deal.pdf"

    def fake_osa(script, *args, timeout=60.0):
        assert args == (str(tmp_path / "deal.docx"), str(out))
        _touch(out, b"%PDF-1.7")
        return 0, "ok", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    assert wp.export_pdf(tmp_path / "deal.docx", out) == (True, "")


def test_export_pdf_reports_missing_output_even_on_exit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "ok", ""))
    ok, err = wp.export_pdf(tmp_path / "deal.docx", tmp_path / "deal.pdf")
    assert ok is False
    assert "no output file" in err


def test_export_pdf_rejects_zero_byte_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = _touch(tmp_path / "deal.pdf", b"")

    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "ok", ""))
    ok, err = wp.export_pdf(tmp_path / "deal.docx", out)
    assert ok is False and err


# ─── convert_folder ──────────────────────────────────────────────────────────


def test_convert_folder_skips_existing_unless_forced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "a.docx")
    _touch(tmp_path / "out" / "a.pdf", b"%PDF")

    calls: list[tuple] = []

    def fake_export(sin, sout, *, timeout=180.0):
        calls.append((sin, sout))
        _touch(sout, b"%PDF")
        return True, ""

    monkeypatch.setattr(wp, "export_pdf", fake_export)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=False)
    assert len(results) == 1 and results[0].skipped and results[0].ok
    assert calls == []

    results = wp.convert_folder(src, tmp_path / "out", force=True, session=session, one_osascript=False)
    assert len(calls) == 1
    assert results[0].ok and not results[0].skipped


def test_convert_folder_recycles_word_after_a_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One bad document leaves Word returning empty documents silently."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "bad.docx")
    _touch(src / "good.docx")

    monkeypatch.setattr(
        wp,
        "export_pdf",
        lambda sin, sout, timeout=180.0: (
            (False, "boom") if "bad" in sin.name else (True, _touch(sout, b"%PDF") and "")
        ),
    )
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    # Word answers the cleanup but keeps a document open: the escalation case.
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    monkeypatch.setattr(session, "open_document_count", lambda: 1)
    recycled: list[tuple] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=False)
    assert [r.ok for r in results] == [False, True]
    assert len(recycled) == 1


def test_convert_folder_with_no_documents_returns_empty(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    assert wp.convert_folder(tmp_path / "src", None) == []


# ─── report ──────────────────────────────────────────────────────────────────


def test_report_exit_code_and_counts(tmp_path: Path) -> None:
    good = wp.Result(source=tmp_path / "a.docx", output=tmp_path / "a.pdf", ok=True, seconds=1.0)
    skip = wp.Result(source=tmp_path / "b.docx", ok=True, skipped=True)
    bad = wp.Result(source=tmp_path / "c.docx", error="boom")

    assert wp.report([good, skip]) == 0
    assert wp.report([good, skip, bad]) == 1
    assert wp.report([]) == 0


# ─── preflight ───────────────────────────────────────────────────────────────


def test_preflight_refuses_when_word_has_documents_open(monkeypatch: pytest.MonkeyPatch) -> None:
    session = wp.WordSession()
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "open_document_count", lambda: 3)

    # Default closes the documents and leaves Word running.
    assert wp.preflight(session, allow_open_docs=False) == ""
    assert "--allow-open-docs" in wp.preflight(
        session, allow_open_docs=False, close_documents=False
    )
    assert wp.preflight(session, allow_open_docs=True, close_documents=False) == ""


def test_preflight_reports_unresponsive_word(monkeypatch: pytest.MonkeyPatch) -> None:
    session = wp.WordSession()
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(session, "warm", lambda: False)
    assert "responsive" in wp.preflight(session, allow_open_docs=True)


def test_preflight_refuses_one_osascript_while_documents_are_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--allow-open-docs` cannot waive this one, the way it can for the serial path.

    The serial export binds the document it opened and closes only that one, so
    leaving a human's documents open costs them Word restarts and nothing else.
    The batch script cannot offer the same deal: it suppresses Word's alerts for
    the whole run, and it has no way to act between documents. So the flag is
    accepted on the command line and declined here, with the reason.
    """
    session = wp.WordSession()
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "open_document_count", lambda: 2)

    # Default closes documents, so an open file is not a refusal.
    assert wp.preflight(session, allow_open_docs=True, one_osascript=True) == ""
    problem = wp.preflight(
        session, allow_open_docs=True, one_osascript=True, close_documents=False
    )
    assert "--do-not-close" in problem
    # The serial path is still the operator's call to make.
    assert wp.preflight(session, allow_open_docs=True, one_osascript=False) == ""
    # And a clean machine may use either.
    monkeypatch.setattr(session, "open_document_count", lambda: 0)
    assert wp.preflight(session, allow_open_docs=False, one_osascript=True) == ""


def test_preflight_refuses_when_the_document_count_is_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`open_document_count()` returns -1 when the query itself fails.

    Both guards below it test `count > 0`, so an unknown count slipped past
    them and the run proceeded without ever establishing the no-open-documents
    premise. That matters more now that the monolithic batch is the default:
    it binds `document 1` after each open and closes it without saving, so a
    pre-existing document the failed query hid could be the one it takes.
    """
    session = wp.WordSession()
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "open_document_count", lambda: -1)

    # Refused in every combination, including the most permissive one.
    for allow, one in ((True, True), (True, False), (False, True), (False, False)):
        problem = wp.preflight(session, allow_open_docs=allow, one_osascript=one)
        assert "could not determine" in problem, (allow, one, problem)


def test_export_batch_closes_every_document_and_does_not_quit_word() -> None:
    """A leftover open document is what got saved as the next file.

    The default closes every document between files and does not quit Word.
    `--do-not-close` is the script that only closes the document it opened.
    """
    assert "close every document saving no" in wp._EXPORT_BATCH
    assert "quit" not in wp._EXPORT_BATCH
    assert "close every document" not in wp._EXPORT_BATCH_KEEP_OPEN
    assert "close theDoc saving no" in wp._EXPORT_BATCH_KEEP_OPEN


def test_cli_tells_preflight_which_mode_it_is_about_to_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gate is worthless if `main` never passes the flag through."""
    from typer.testing import CliRunner

    seen: dict[str, bool] = {}

    def fake_preflight(_session, *, allow_open_docs, one_osascript, close_documents=True):
        seen["allow_open_docs"] = allow_open_docs
        seen["one_osascript"] = one_osascript
        seen["close_documents"] = close_documents
        return "refused"

    src = tmp_path / "src"
    src.mkdir()
    monkeypatch.setattr(wp, "preflight", fake_preflight)
    result = CliRunner().invoke(
        wp.app,
        ["--src", str(src), "--no-check-preset", "--one-osascript", "--allow-open-docs"],
    )
    assert result.exit_code == 2
    assert seen == {"allow_open_docs": True, "one_osascript": True, "close_documents": True}


# ─── watchdogs ───────────────────────────────────────────────────────────────


def test_watchdog_presses_grant_with_activation_not_cancel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancelling a Grant sheet denies access and re-prompts on every later file."""
    scripts: list[tuple[str, tuple[str, ...]]] = []

    def fake_osa(script, *args, timeout=60.0):
        scripts.append((script, args))
        if script is wp._DUMP_BUTTONS:
            return (0, "Select…\tCancel\t", "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._PRESS_ACTIVATED:
            return 0, "Select…", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    dogs.start()
    deadline = wp.time.monotonic() + 3
    while dogs.granted == 0 and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()

    assert dogs.granted >= 1
    used = [s for s, _ in scripts]
    assert wp._PRESS_ACTIVATED in used
    # The plain (non-activating) press is only reached when no grant matched.
    assert wp._PRESS not in used


def test_watchdog_declines_error_reporting_as_its_own_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MERP is a separate process; a handler aimed at Word can never see it."""
    pressed_on: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_BUTTONS:
            return (0, "Don\u2019t Send\tSend\t", "") if args[0] == wp.MERP_PROC else (0, "", "")
        if script is wp._PRESS:
            pressed_on.append(args[0])
            return 0, "Don\u2019t Send", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    dogs.start()
    deadline = wp.time.monotonic() + 3
    while not pressed_on and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()

    assert wp.MERP_PROC in pressed_on


def test_watchdog_closes_error_report_ok_and_not_more_information(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """This machine's report window is OK / More Information, not Don't Send.

    OK dismisses it. More Information only opens the details pane, so it must
    not be pressed. The button dump also reports an unnamed control as
    'missing value'; that is not a button to hit.
    """
    pressed: list[str] = []
    present = {"OK", "More Information"}

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_BUTTONS:
            shown = "OK\tMore Information\tmissing value\t" if args[0] == wp.MERP_PROC else ""
            return 0, shown, ""
        if script is wp._PRESS and args and args[0] == wp.MERP_PROC:
            for name in args[1:]:
                if name in present:
                    pressed.append(name)
                    return 0, name, ""
            return 0, "", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    dogs.start()
    deadline = wp.time.monotonic() + 3
    while not pressed and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()

    assert pressed and set(pressed) == {"OK"}
    assert "More Information" not in wp.MERP_DECLINE
    assert "missing value" not in wp.MERP_DECLINE


def test_watchdog_stop_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    dogs = wp.Watchdogs(poll=0.01)
    with dogs:
        pass
    dogs.stop()


# ─── WordSession ─────────────────────────────────────────────────────────────


def test_recycle_escalates_gracefully_then_cleans_only_our_debris(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """quit → pkill -x → pkill -9 -x, never pkill -f, then OUR debris only.

    The AutoRecovery directory is the user's, not this run's: it holds the
    recovery copy of every document Word has open, a human's unsaved work
    included. Clearing all of it to remove our own residue would destroy theirs.
    """
    recovery = tmp_path / "AutoRecovery"
    folder = tmp_path / "work"
    # Predates the session: a human's unsaved document, and someone else's lock.
    stale_recovery = _touch(recovery / "someones-unsaved-work.olk")
    stale_lock = _touch(folder / "~$their-doc.docx")
    long_ago = 1_000_000.0
    os.utime(stale_recovery, (long_ago, long_ago))
    os.utime(stale_lock, (long_ago, long_ago))

    monkeypatch.setattr(wp, "AUTORECOVERY", recovery)
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    monkeypatch.setattr(wp.time, "sleep", lambda _s: None)

    cmds: list[list[str]] = []

    def fake_run(cmd, **kw):
        cmds.append(cmd)

        class _Done:
            returncode = 0  # pgrep says "alive" so both escalations run

        return _Done()

    monkeypatch.setattr(wp.subprocess, "run", fake_run)
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)

    # Created after the session started: ours.
    _touch(recovery / "ours.olk")
    _touch(folder / "~$deal.docx")
    _touch(folder / "deal.docx")

    assert session.recycle(folder) is True
    assert ["pkill", "-x", wp.WORD_PROC] in cmds
    assert ["pkill", "-9", "-x", wp.WORD_PROC] in cmds
    assert not any("-f" in c for c in cmds)

    assert stale_recovery.exists(), "a human's recovery copy must survive"
    assert stale_lock.exists(), "a lock file we did not create must survive"
    assert not (recovery / "ours.olk").exists()
    assert not (folder / "~$deal.docx").exists()
    assert (folder / "deal.docx").exists()  # never a real document


def test_entries_since_skips_older_and_unreadable(tmp_path: Path) -> None:
    fresh = _touch(tmp_path / "fresh.olk")
    old = _touch(tmp_path / "old.olk")
    os.utime(old, (1_000_000.0, 1_000_000.0))

    got = wp._entries_since(tmp_path, cutoff=fresh.stat().st_mtime)
    assert got == [fresh]

    assert wp._entries_since(tmp_path / "absent", cutoff=0) == []
    assert wp._entries_since(None, cutoff=0) == []  # type: ignore[arg-type]


def test_entries_since_honours_the_pattern(tmp_path: Path) -> None:
    lock = _touch(tmp_path / "~$deal.docx")
    _touch(tmp_path / "deal.docx")
    assert wp._entries_since(tmp_path, cutoff=0, pattern="~$*") == [lock]


# ─── CLI smoke ───────────────────────────────────────────────────────────────


def test_cli_help_exits_cleanly() -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(wp.app, ["--help"])
    assert result.exit_code == 0
    assert "--src" in result.output and "--check-preset" in result.output


def test_cli_rejects_a_source_that_is_not_a_folder(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    result = CliRunner().invoke(wp.app, ["--src", str(tmp_path / "nope")])
    assert result.exit_code == 2


def test_cli_stops_when_preflight_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    (tmp_path / "src").mkdir()
    monkeypatch.setattr(
        wp,
        "preflight",
        lambda s, *, allow_open_docs, one_osascript=False, close_documents=True: "Word is busy",
    )
    result = CliRunner().invoke(wp.app, ["--src", str(tmp_path / "src"), "--no-check-preset"])
    assert result.exit_code == 2


def test_cli_runs_the_batch_and_returns_the_report_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    src = tmp_path / "src"
    _touch(src / "a.docx")
    monkeypatch.setattr(
        wp,
        "preflight",
        lambda s, *, allow_open_docs, one_osascript=False, close_documents=True: "",
    )
    monkeypatch.setattr(wp.Watchdogs, "start", lambda self: None)
    monkeypatch.setattr(wp.Watchdogs, "stop", lambda self: None)
    monkeypatch.setattr(wp.WordSession, "quit_if_ours", lambda self: None)
    monkeypatch.setattr(
        wp,
        "convert_folder",
        lambda *a, **k: [wp.Result(source=src / "a.docx", error="boom")],
    )

    result = CliRunner().invoke(wp.app, ["--src", str(src), "--out", str(tmp_path / "out")])
    assert result.exit_code == 1


# ─── WordSession lifecycle ───────────────────────────────────────────────────


def test_available_requires_word_and_osascript(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp.shutil, "which", lambda _n: "/usr/bin/osascript")
    monkeypatch.setattr(wp, "WORD_APP", Path("/definitely/not/here.app"))
    assert wp.WordSession.available() is False


def test_responsive_only_when_word_answers_with_a_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = wp.WordSession()
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "2", ""))
    assert session.responsive() is True
    assert session.open_document_count() == 2

    monkeypatch.setattr(wp, "osa", lambda *a, **k: (1, "", "-1708"))
    assert session.responsive() is False
    assert session.open_document_count() == -1


def test_warm_launches_in_background_and_silences_alerts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`open -g`: the batch never takes the screen from whoever is at the machine."""
    answers = iter([(1, "", ""), (1, "", ""), (0, "0", "")])
    scripts: list[str] = []
    launched: list[list[str]] = []

    def fake_osa(script, *args, timeout=60.0):
        scripts.append(script)
        if script is wp._SET_ALERTS:
            return 0, "", ""
        return next(answers)

    monkeypatch.setattr(wp, "osa", fake_osa)
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: launched.append(cmd))
    monkeypatch.setattr(wp.time, "sleep", lambda _s: None)

    session = wp.WordSession()
    assert session.warm() is True
    assert session.launched_by_us is True
    assert launched and launched[0][:3] == ["open", "-g", "-a"]
    assert wp._SET_ALERTS in scripts


def test_warm_leaves_an_already_running_word_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pre-warming must never restart a Word that is already up.

    Two sticky settings this tool cannot set for you live in that running
    instance: the PDF "Optimize for" choice and the markup display. Relaunching
    Word to "warm" it risks losing the selection the operator was told to make
    by hand, and every PDF after that point would render at the wrong setting
    without anything failing. So a responsive Word is returned as found: no
    `open`, and no claim of ownership, which is what keeps `quit_if_ours()`
    from closing someone else's session at the end of the batch.
    """
    launched: list[list[str]] = []
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "0", ""))  # responsive
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: launched.append(cmd))

    session = wp.WordSession()
    assert session.warm() is True
    assert launched == [], "warm() relaunched a Word that was already running"
    assert session.launched_by_us is False

    # And therefore the batch does not quit it on the way out.
    calls: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda script, *a, **k: calls.append(script) or (0, "", ""))
    session.quit_if_ours()
    assert calls == []


def test_recycle_warns_before_restarting_a_word_it_did_not_launch(
    monkeypatch: pytest.MonkeyPatch, caplog
) -> None:
    """A clean start is not the same as a Word we own.

    `recycle` already refuses when documents were open. A Word left open with
    *no* documents still starts clean, so recovery may restart it — and that
    restart carries the same risk to the operator's sticky PDF and markup
    settings. Recovery is still worth having, so this warns rather than
    refusing, but it must not be silent.
    """
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: None)
    monkeypatch.setattr(wp.time, "sleep", lambda _s: None)
    monkeypatch.setattr(wp.WordSession, "_alive", staticmethod(lambda: False))
    monkeypatch.setattr(wp.WordSession, "clean_after_kill", lambda self, *f: None)
    monkeypatch.setattr(wp.WordSession, "warm", lambda self: True)

    messages: list[str] = []
    sink = wp.logger.add(lambda m: messages.append(str(m)), level="WARNING")
    try:
        session = wp.WordSession(launched_by_us=False)
        assert session.recycle() is True
    finally:
        wp.logger.remove(sink)

    joined = " ".join(messages)
    assert "did not launch" in joined
    assert "Optimize for" in joined


def test_warm_gives_up_at_its_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter([0.0, 0.0, 5.0, 999.0])
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (1, "", "no"))
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: None)
    monkeypatch.setattr(wp.time, "sleep", lambda _s: None)
    monkeypatch.setattr(wp.time, "monotonic", lambda: next(clock))

    assert wp.WordSession(warm_timeout=10).warm() is False


def test_quit_if_ours_only_quits_a_word_we_launched(monkeypatch: pytest.MonkeyPatch) -> None:
    """A Word this run did not launch is never quit, whatever is open in it.

    This used to also assert that exit ran `close every document saving no`
    first. It no longer does, and should not: see
    `test_quit_if_ours_leaves_word_alone_when_a_document_is_open`.
    """
    calls: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda script, *a, **k: calls.append(script) or (0, "", ""))
    monkeypatch.setattr(wp.WordSession, "open_document_count", lambda self: 0)

    wp.WordSession(launched_by_us=False).quit_if_ours()
    assert calls == []

    wp.WordSession(launched_by_us=True).quit_if_ours()
    assert any("quit saving no" in c for c in calls), calls
    assert wp._CLOSE_ALL not in calls


def test_watchdog_dismisses_an_ordinary_alert_without_activating(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancel is safe here only because a grant would already have matched."""
    pressed: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_BUTTONS:
            return (0, "OK\t", "") if args[0] == wp.WORD_PROC else (0, "", "")
        if script is wp._PRESS_ACTIVATED:
            return 0, "", ""  # no grant button present
        if script is wp._PRESS:
            pressed.append(args[1])
            return 0, "OK", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    dogs.start()
    deadline = wp.time.monotonic() + 3
    while dogs.dismissed == 0 and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()

    assert dogs.dismissed >= 1
    assert dogs.granted == 0


# ─── malformed documents ─────────────────────────────────────────────────────


def test_recover_after_failure_declines_closes_and_keeps_going(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A malformed document costs one failed open, not a ~30s Word restart."""
    ran: list[str] = []

    monkeypatch.setattr(wp, "osa", lambda script, *a, **k: ran.append(script) or (0, "", ""))
    session = wp.WordSession()
    monkeypatch.setattr(session, "open_document_count", lambda: 0)
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    assert wp.recover_after_failure(session) is True
    assert wp._DECLINE_REPAIR in ran  # answer the repair prompt "No"
    assert wp._CLOSE_ALL in ran  # close the file if one is open
    assert recycled == []  # and do NOT restart Word


def test_recover_after_failure_escalates_when_word_stays_dirty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    session = wp.WordSession()
    monkeypatch.setattr(session, "open_document_count", lambda: 2)
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    assert wp.recover_after_failure(session, Path("/tmp/x")) is True
    assert len(recycled) == 1


def test_serial_failure_recovers_without_restarting_word(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "bad.docx")
    _touch(src / "good.docx")

    monkeypatch.setattr(
        wp,
        "export_pdf",
        lambda sin, sout, timeout=180.0: (
            (False, "unreadable") if "bad" in sin.name else (True, _touch(sout, b"%PDF") and "")
        ),
    )
    recovered: list[object] = []
    recycled: list[object] = []
    monkeypatch.setattr(
        wp, "recover_after_failure", lambda s, *f, **kw: recovered.append(f) or True
    )
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=False)

    assert [r.ok for r in results] == [False, True]
    assert len(recovered) == 1
    assert recycled == []  # one bad file is not a reason to restart Word


def test_serial_recycles_once_the_failures_stop_looking_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Word degraded by a poison document answers fine and returns empty docs."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    for name in ("a.docx", "b.docx", "c.docx", "d.docx"):
        _touch(src / name)

    monkeypatch.setattr(wp, "export_pdf", lambda sin, sout, timeout=180.0: (False, "empty"))
    monkeypatch.setattr(wp, "recover_after_failure", lambda s, *f, **kw: True)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=False, poison_streak=3)
    assert len(recycled) == 1  # fires at the third, resets, and 4 is not 6


def test_watchdog_answers_the_repair_prompt_no_before_anything_generic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """"Yes" would make Word rewrite the file and we would measure the repair."""
    order: list[str] = []

    def fake_osa(script, *args, timeout=60.0):
        if script is wp._DUMP_BUTTONS:
            return (0, "Yes\tNo\t", "") if args[0] == wp.WORD_PROC else (0, "", "")
        order.append(script)
        if script is wp._DECLINE_REPAIR:
            return 0, "No", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    dogs.start()
    deadline = wp.time.monotonic() + 3
    while dogs.declined == 0 and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()

    assert dogs.declined >= 1
    assert order[0] is wp._DECLINE_REPAIR
    # A match short-circuits: neither generic handler runs on a repair prompt.
    assert wp._PRESS_ACTIVATED not in order and wp._PRESS not in order


def test_decline_repair_matches_on_window_text_not_a_button_name() -> None:
    src = wp._DECLINE_REPAIR
    assert "wText contains" in src
    assert 'pressNamed(w, "No")' in src
    assert "key code 53" in src  # Escape, when the button is unreachable
    assert '"Yes"' not in src  # never repair the document under test
    for marker in wp.REPAIR_MARKERS:
        assert marker  # markers are supplied via argv, never interpolated
    assert "item 1 of argv" not in src or "items 1 thru -1 of argv" in src


# ─── one-osascript batch mode ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("index", "name", "expected"),
    [
        (0, "deal.docx", "00000__deal.docx"),
        (7, "a\tb.docx", "00007__a_b.docx"),
        (12, "line\nbreak.docx", "00012__line_break.docx"),
        (3, "cr\rhere.docx", "00003__cr_here.docx"),
    ],
)
def test_safe_stage_name(index: int, name: str, expected: str) -> None:
    """A tab in a filename would split one TSV row into two, silently."""
    assert wp.safe_stage_name(index, name) == expected


def test_safe_stage_name_is_unique_across_same_named_sources() -> None:
    assert wp.safe_stage_name(0, "deal.docx") != wp.safe_stage_name(1, "deal.docx")


def test_write_manifest_round_trips_as_tsv(tmp_path: Path) -> None:
    rows = [("0", "/in/a.docx", "/out/a.pdf"), ("1", "/in/b.docx", "/out/b.pdf")]
    path = wp.write_manifest(rows, tmp_path / "deep" / "manifest.tsv")
    assert [tuple(ln.split("\t")) for ln in path.read_text().splitlines()] == rows


@pytest.mark.parametrize(
    ("text", "expected_results", "expected_done"),
    [
        ("[ok]\t0\n[done]\t1\t0\n", {"0": (True, "")}, True),
        ("[ok]\t0\t17\n[done]\t1\t0\n", {"0": (True, "17")}, True),
        ("[fail]\t0\tboom\n[done]\t0\t1\n", {"0": (False, "boom")}, True),
        ("[fail]\t0\n", {"0": (False, "unspecified error")}, False),
        ("[ok]\t0\nrandom noise\n", {"0": (True, "")}, False),
        ("", {}, False),
    ],
)
def test_parse_batch_log(text: str, expected_results: dict, expected_done: bool) -> None:
    log = wp.parse_batch_log(text)
    assert log.results == expected_results
    assert log.done is ("[done]" in text)


def test_parse_batch_log_keeps_a_multi_field_error_whole() -> None:
    log = wp.parse_batch_log("[fail]\t3\tWord said: -1728\tand more\n")
    assert log.results["3"] == (False, "Word said: -1728\tand more")


def test_parse_batch_log_ignores_retry_so_poison_is_not_final() -> None:
    """[retry] is how a batch says 'Word was poisoned, try this again'.

    [fail] is final. A timeout's empty followers must not be [fail], or one
    wedged Word permanently condemns the rest of the folder.
    """
    log = wp.parse_batch_log("[retry]\t0\tAppleEvent timed out\n[ok]\t1\n[done]\t1\t0\n")
    assert "0" not in log.results
    assert log.results["1"] == (True, "")
    assert log.done is True


def test_parse_batch_log_omits_items_the_run_never_reached() -> None:
    """No line at all is not a failure — it is the only case worth retrying."""
    log = wp.parse_batch_log("[ok]\t0\n[ok]\t1\n")
    assert "2" not in log.results
    assert log.done is False


def test_batch_timeout_is_headroom_plus_the_work() -> None:
    assert wp.batch_timeout(180, 10) == 180 * 10 + 120
    assert wp.batch_timeout(180, 0) == 120  # an empty batch gets the headroom
    assert wp.batch_timeout(1, 1, floor=500) == 501
    assert wp.batch_timeout(-5, 10) == 120  # a nonsense budget never shortens it


def _fake_batch_osa(*, fails: tuple[str, ...] = (), stop_after: int | None = None, detail: str = ""):
    """Stand in for the monolithic AppleScript: read manifest, write log + outputs.

    `stop_after` simulates a wedge — the run stops mid-manifest and never reaches
    its own `[done]` line, which is what resume has to detect.
    """

    def fake(script, *args, timeout=60.0):
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        lines: list[str] = []
        ok = bad = 0
        for i, row in enumerate(rows):
            if stop_after is not None and i >= stop_after:
                break
            out = Path(row[-1])
            if row[0] in fails:
                bad += 1
                lines.append(f"[fail]\t{row[0]}\tWord could not read it")
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(b"OUT")
                ok += 1
                lines.append(f"[ok]\t{row[0]}" + (f"\t{detail}" if detail else ""))
        if stop_after is None:
            lines.append(f"[done]\t{ok}\t{bad}")
        log.write_text("\n".join(lines) + "\n")
        return (None if stop_after is not None else 0), "", ""

    return fake


def test_run_batch_passes_only_two_argv_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A thousand absolute paths on argv would risk ARG_MAX; this passes two."""
    seen: dict[str, object] = {}

    def fake(script, *args, timeout=60.0):
        seen["args"] = args
        Path(args[1]).write_text("[ok]\t0\n[done]\t1\t0\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake)
    run = wp.run_batch("SCRIPT", [("0", "/in/a", "/out/a")], tmp_path, timeout=30)

    assert len(seen["args"]) == 2
    assert seen["args"][0] == str(tmp_path / "manifest.tsv")
    assert run.log.results == {"0": (True, "")}
    assert run.wedged is False


def test_run_batch_reports_a_run_that_never_reached_done(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "osa", _fake_batch_osa(stop_after=1))
    rows = [("0", "/in/a", str(tmp_path / "a.pdf")), ("1", "/in/b", str(tmp_path / "b.pdf"))]
    run = wp.run_batch("SCRIPT", rows, tmp_path, timeout=30)

    assert run.wedged is True
    assert "0" in run.log.results and "1" not in run.log.results


def test_run_batch_with_resume_retries_only_what_was_never_reached(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifests: list[list[str]] = []
    calls = {"n": 0}

    def fake(script, *args, timeout=60.0):
        calls["n"] += 1
        manifest, log = Path(args[0]), Path(args[1])
        rows = [ln.split("\t") for ln in manifest.read_text().splitlines() if ln]
        manifests.append([r[0] for r in rows])
        if calls["n"] == 1:  # wedges after the first two, and one of them failed
            log.write_text("[ok]\t0\n[fail]\t1\tbad file\n")
            return None, "", ""
        log.write_text("".join(f"[ok]\t{r[0]}\n" for r in rows) + "[done]\t9\t0\n")
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake)
    session = wp.WordSession()
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    rows = [(str(i), f"/in/{i}", f"/out/{i}") for i in range(4)]
    got = wp.run_batch_with_resume(
        "SCRIPT", rows, tmp_path, per_item_timeout=10, session=session, max_passes=3
    )

    assert manifests[0] == ["0", "1", "2", "3"]
    assert manifests[1] == ["2", "3"]  # only the unreached; the failure is final
    assert got["0"] == (True, "")
    assert got["1"] == (False, "bad file")
    assert got["2"][0] and got["3"][0]
    assert len(recycled) == 1  # Word is recycled between passes, not within one


def test_run_batch_with_resume_gives_up_and_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "osa", _fake_batch_osa(stop_after=0))
    session = wp.WordSession()
    monkeypatch.setattr(session, "recycle", lambda *f: True)

    got = wp.run_batch_with_resume(
        "SCRIPT",
        [("0", "/in/0", str(tmp_path / "0.pdf"))],
        tmp_path,
        per_item_timeout=1,
        session=session,
        max_passes=2,
    )
    assert got["0"][0] is False
    assert "never reached in 2" in got["0"][1]


def test_convert_folder_one_osascript_converts_the_whole_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    for name in ("a.docx", "b.docx", "~$a.docx"):
        _touch(src / name)
    monkeypatch.setattr(wp, "osa", _fake_batch_osa())
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=True)

    assert [r.source.name for r in results] == ["a.docx", "b.docx"]  # lock file excluded
    assert all(r.ok for r in results)
    assert (tmp_path / "out" / "a.pdf").exists() and (tmp_path / "out" / "b.pdf").exists()
    assert all(r.timing_exact is False for r in results)


def test_convert_folder_one_osascript_records_a_bad_document_and_finishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The batch script closes the file and moves on; it does not stop."""
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "a.docx")
    _touch(src / "bad.docx")
    _touch(src / "c.docx")
    monkeypatch.setattr(wp, "osa", _fake_batch_osa(fails=("1",)))  # index 1 == bad.docx
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=True)

    assert [(r.source.name, r.ok) for r in results] == [
        ("a.docx", True),
        ("bad.docx", False),
        ("c.docx", True),
    ]
    assert "could not read" in results[1].error
    assert recycled == []  # nothing was left unreached, so nothing to resume


def test_convert_folder_one_osascript_skips_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "a.docx")
    _touch(src / "b.docx")
    _touch(tmp_path / "out" / "a.pdf", b"%PDF")
    staged_rows: list[list[str]] = []

    inner = _fake_batch_osa()

    def fake(script, *args, timeout=60.0):
        staged_rows.append(Path(args[0]).read_text().splitlines())
        return inner(script, *args, timeout=timeout)

    monkeypatch.setattr(wp, "osa", fake)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=True)
    assert results[0].skipped and results[1].ok
    assert len(staged_rows[0]) == 1  # only b.docx made it into the manifest


def test_convert_folder_one_osascript_resumes_after_a_wedge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    for name in ("a.docx", "b.docx", "c.docx"):
        _touch(src / name)

    calls = {"n": 0}
    complete = _fake_batch_osa()
    wedge = _fake_batch_osa(stop_after=1)

    def fake(script, *args, timeout=60.0):
        calls["n"] += 1
        return (wedge if calls["n"] == 1 else complete)(script, *args, timeout=timeout)

    monkeypatch.setattr(wp, "osa", fake)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    recycled: list[object] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=True)

    assert all(r.ok for r in results)
    assert calls["n"] == 2
    assert len(recycled) == 1


def test_one_osascript_is_the_default_everywhere() -> None:
    """The monolithic run is the normal one; per-document is the opt-out.

    One osascript per document pays a process spawn and an Apple-event
    connection per file for the ability to act between documents. The batch
    already resumes from its own log when it wedges, so that ability is worth
    less than it costs on a folder-sized job.
    """
    import inspect

    assert inspect.signature(wp.convert_folder).parameters["one_osascript"].default is True
    assert inspect.signature(wp.main).parameters["one_osascript"].default is True


def test_export_batch_script_closes_and_continues_on_a_bad_document() -> None:
    src = wp._EXPORT_BATCH
    assert "set displayAlerts to false" in src
    assert "on error errMsg" in src
    # Default closes every open document between files and does not quit Word.
    # A leftover was saved under the next filename after Word's connection died.
    assert "close every document saving no" in src
    assert "quit" not in src
    assert "set theDoc to missing value" in src
    assert '"[fail]" & tab & itemId' in src
    assert '"[done]"' in src
    # A timed-out Apple event leaves Word returning empty documents for every
    # later open (§5.20). The timed-out file is a final [fail] and the batch
    # stops, so the tail is retried after a recycle without lining that file up
    # first again. A streak of empty loads is the same poison when the timeout
    # was in a previous process: [retry] is not a [fail], so those are retried.
    assert "set emptyStreak to 0" in src
    assert '"[retry]" & tab & itemId' in src
    assert 'errMsg contains "loaded empty"' in src
    assert 'if errMsg contains "timed out" then' in src
    assert "exit repeat" in src
    assert "emptyStreak ≥ 3" in src
    # Health before the save, and nothing interpolated: paths arrive by manifest.
    assert src.index("count of paragraphs") < src.index("save as theDoc")
    assert "item 1 of argv" in src and "item 2 of argv" in src


def test_report_does_not_call_a_batch_average_a_median(tmp_path: Path) -> None:
    batched = wp.Result(
        source=tmp_path / "a.docx", output=tmp_path / "a.pdf", ok=True,
        seconds=2.5, timing_exact=False,
    )
    wp.report([batched])  # exercised for the label branch; exit code checked below
    assert wp.report([batched]) == 0


def test_progress_reports_the_batch_log_as_it_grows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A monolithic run is one blocking osascript; its log is the only signal."""
    log = tmp_path / "batch.log"
    log.write_text("")
    seen: list[str] = []
    monkeypatch.setattr(wp.logger, "info", lambda msg: seen.append(str(msg)))

    with wp._Progress(log, total=3, label=" pdf", poll=0.01):
        log.write_text("[ok]\t0\n")
        deadline = wp.time.monotonic() + 3
        while not seen and wp.time.monotonic() < deadline:
            wp.time.sleep(0.02)
        log.write_text("[ok]\t0\n[fail]\t1\tboom\nnoise\n")
        deadline = wp.time.monotonic() + 3
        while not any("2/3" in m for m in seen) and wp.time.monotonic() < deadline:
            wp.time.sleep(0.02)

    assert any("1/3" in m for m in seen)
    assert any("2/3" in m for m in seen)  # noise lines are not progress
    assert all("[batch pdf]" in m for m in seen)


def test_progress_survives_a_log_that_is_not_there_yet(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp.logger, "info", lambda msg: None)
    with wp._Progress(tmp_path / "absent.log", total=1, poll=0.01):
        wp.time.sleep(0.05)


def test_clean_after_kill_skips_autorecovery_when_a_human_doc_was_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run started with documents open must not touch AutoRecovery at all.

    The mtime cutoff is only sound because `preflight` refuses to start while
    Word holds documents: with none open, every AutoRecovery entry written
    during the run is ours. Under `--allow-open-docs` that premise is gone, and
    the cutoff stops protecting anyone: Word's AutoRecover interval defaults to
    10 minutes, so a human's document open during a longer run gets its recovery
    copy rewritten *after* the run started and would be deleted as ours.

    So the cutoff is not the control here; the precondition is. When the run did
    not start clean, AutoRecovery is left entirely alone. Lock files in our own
    staging folders are still ours to remove.
    """
    recovery = tmp_path / "AutoRecovery"
    folder = tmp_path / "work"
    monkeypatch.setattr(wp, "AUTORECOVERY", recovery)
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))

    session = wp.WordSession(started_clean=False)

    # Word autosaved a human's open document mid-run: newer than session.started.
    human_copy = _touch(recovery / "AutoRecovery save of Their Thesis.olk")
    ours = _touch(folder / "~$deal.docx")

    session.clean_after_kill(folder)

    assert human_copy.exists(), "a human's mid-run autosave must survive"
    assert not ours.exists(), "our own lock file is still ours to remove"


def test_preflight_records_whether_word_started_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`preflight` is where the no-open-documents premise is established."""
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))

    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "open_document_count", lambda: 0)
    assert wp.preflight(session, allow_open_docs=False) == ""
    assert session.started_clean is True

    open_session = wp.WordSession()
    monkeypatch.setattr(open_session, "warm", lambda: True)
    monkeypatch.setattr(open_session, "open_document_count", lambda: 2)
    assert wp.preflight(open_session, allow_open_docs=True) == ""
    assert open_session.started_clean is False

    # Word not answering: we cannot prove it started clean, so we must not assume it.
    unknown = wp.WordSession()
    monkeypatch.setattr(unknown, "warm", lambda: True)
    monkeypatch.setattr(unknown, "open_document_count", lambda: -1)
    wp.preflight(unknown, allow_open_docs=True)
    assert unknown.started_clean is False


def test_cleanup_never_sweeps_lock_files_in_the_user_s_own_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only folders this run created are swept for `~$` files.

    Word never opens anything from `--src`: every document is copied into the
    container inbox first (`Stage.place`) and Word opens the copy. So a `~$`
    file in the source folder was put there by someone else's Word, and the
    mtime cutoff does not save it if that human opened their document while our
    run was going. `iter_docx()` already excludes `~$*` from the work list, so
    sweeping the source folder buys nothing and can only break a stranger's
    lock.
    """
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "bad.docx")
    human_lock = _touch(src / "~$their-open-doc.docx")

    monkeypatch.setattr(wp, "export_pdf", lambda sin, sout, timeout=180.0: (False, "boom"))
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    swept: list[tuple[Path, ...]] = []
    monkeypatch.setattr(session, "recycle", lambda *f: swept.append(f) or True)
    monkeypatch.setattr(session, "clean_after_kill", lambda *f: swept.append(f))
    # `export_pdf` is the serial path's; the batch path would run real osascript.
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    monkeypatch.setattr(session, "open_document_count", lambda: 1)

    wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=False)

    assert swept, "the failure path must have run a cleanup"
    for folders in swept:
        assert src not in folders, f"the user's source folder was handed to cleanup: {folders}"
    assert human_lock.exists(), "someone else's lock file must survive"


def test_export_pdf_closes_every_document_and_the_flag_does_not() -> None:
    """Default closes every document. `--do-not-close` closes only ours.

    Neither script quits Word.
    """
    assert "close every document saving no" in wp._EXPORT_PDF
    assert "quit" not in wp._EXPORT_PDF
    assert "close every document" not in wp._EXPORT_PDF_KEEP_OPEN


def test_recover_after_failure_closes_only_ours_when_word_was_not_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Not started clean means a human's documents are open. Close ours by name."""
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_osa(script, *args, timeout=60.0):
        calls.append((script, args))
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    session = wp.WordSession(started_clean=False)
    monkeypatch.setattr(session, "open_document_count", lambda: 1)

    assert wp.recover_after_failure(session, only="00001__deal.docx") is True

    scripts = [s for s, _ in calls]
    assert wp._CLOSE_ALL not in scripts, "must not close a human's documents"
    assert wp._CLOSE_NAMED in scripts
    named = next(a for s, a in calls if s is wp._CLOSE_NAMED)
    assert named == ("00001__deal.docx",)


def test_recover_after_failure_closes_everything_when_word_started_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Close-all is still the escalation when the narrow close does not settle it.

    Started clean no longer makes the blanket close the *first* move when the
    failing item has a name -- a document opened after preflight would be
    caught by it -- but it must stay reachable, because a Word that will not
    come back to zero is the degraded-instance signal the recycle depends on.
    """
    calls: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: calls.append(s) or (0, "", ""))
    session = wp.WordSession(started_clean=True)
    counts = iter([1, 0])  # named close leaves one open; close-all settles it
    monkeypatch.setattr(session, "open_document_count", lambda: next(counts))

    assert wp.recover_after_failure(session, only="00001__deal.docx") is True
    assert calls.index(wp._CLOSE_NAMED) < calls.index(wp._CLOSE_ALL), calls


def test_recycle_refuses_to_quit_word_over_a_human_s_documents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`recycle` quits Word `saving no`. That is not ours to do when we did not
    start clean: the operator asked us to coexist with their documents, not to
    discard them. Refuse and report instead."""
    ran: list[list[str]] = []
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **kw: ran.append(cmd))
    session = wp.WordSession(started_clean=False)

    assert session.recycle(tmp_path) is False
    assert not ran, "no pkill, no quit, nothing destructive"


def test_serial_replays_the_failure_streak_after_recycling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recycle means the earlier failures are no longer trustworthy.

    The streak exists because a Word degraded by one bad document answers
    normally and returns empty documents for everything after it. The
    paragraph-count check turns those into failures rather than false passes,
    which is the important half — but they are failures of *Word*, not of the
    files, and they were final. So up to `poison_streak - 1` healthy documents
    could be reported as permanently failed.

    After a recycle, the streak is replayed against the fresh Word. Whatever
    fails a second time is the file's own fault and stays failed.
    """
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    for name in ("poison.docx", "healthy-a.docx", "healthy-b.docx"):
        _touch(src / name)

    calls: list[str] = []

    def fake_export(sin, sout, timeout=180.0):
        calls.append(sin.name)
        # poison.docx is genuinely bad and fails every time. The other two only
        # fail while Word is degraded, i.e. on their first attempt.
        if "poison" in sin.name:
            return False, "document loaded empty (Word could not read it)"
        if calls.count(sin.name) == 1:
            return False, "document loaded empty (Word could not read it)"
        _touch(sout, b"%PDF")
        return True, ""

    monkeypatch.setattr(wp, "export_pdf", fake_export)
    monkeypatch.setattr(wp, "recover_after_failure", lambda s, *f, **kw: True)
    session = _verified_session()
    monkeypatch.setattr(session, "warm", lambda: True)
    monkeypatch.setattr(session, "recycle", lambda *f: True)

    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=False)
    by_name = {r.source.name: r for r in results}

    assert by_name["healthy-a.docx"].ok, "a healthy file must not stay failed after a recycle"
    assert by_name["healthy-b.docx"].ok
    assert not by_name["poison.docx"].ok, "the genuinely bad file stays failed"
    assert calls.count("poison.docx") == 2, "replayed once, then left alone"


# ─── timeouts that are not times ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "raised",
    [ValueError("cannot convert float NaN to integer"),
     OverflowError("cannot convert float infinity to integer")],
)
def test_osa_never_raises_on_a_non_finite_timeout(raised, monkeypatch) -> None:
    """`osa`'s docstring says "Never raises"; two values made it a liar.

    `subprocess.run` converts the timeout to an integer before spawning, so
    `nan` raises ValueError and `inf` raises OverflowError -- neither caught.
    The exception is raised here rather than passing the real value, because on
    a box with no `osascript` the OSError fires first and the timeout is never
    converted, so the live values prove nothing.

    (A negative or zero timeout does *not* raise: `subprocess.run` accepts it
    and reports TimeoutExpired at once, so every call "times out" instead. That
    one is the CLI's to reject, below.)
    """

    def boom(*args, **kwargs):
        raise raised

    monkeypatch.setattr(wp.subprocess, "run", boom)
    rc, out, err = wp.osa("return 1", timeout=float("nan"))
    assert rc is None and out == ""
    assert "invalid timeout" in err.lower()


def test_cli_rejects_a_timeout_that_is_not_a_positive_duration(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    src, out = tmp_path / "src", tmp_path / "out"
    src.mkdir()
    for bad in ("0", "-1", "nan", "inf"):
        res = CliRunner().invoke(
            wp.app, ["--src", str(src), "--out", str(out), "--timeout", bad]
        )
        assert res.exit_code == 2, f"--timeout {bad} was accepted: {res.output}"
        assert "--timeout" in res.output


def test_module_docstring_does_not_promise_an_autorecovery_wipe() -> None:
    """`clean_after_kill` never wipes it; the header said it did.

    The method deletes only entries modified at or after this session started,
    and skips AutoRecovery entirely when preflight did not establish a clean
    Word. A header promising a wipe invites a future edit back to the
    destructive form.
    """
    head = (wp.__doc__ or "")
    assert "AutoRecovery is wiped" not in head
    assert "scoped" in head or "only" in head


# ─── ownership is not settled once at startup ────────────────────────────────


def test_quit_if_ours_leaves_word_alone_when_a_document_is_open(monkeypatch) -> None:
    """`launched_by_us` identifies the process, not the documents in it.

    Exit used to run `close every document saving no` and then quit, on the
    strength of having launched Word. A person who opened something in that
    instance mid-run lost it. The run's own documents are already closed by the
    time this fires, so anything still open is either a cleanup that did not
    finish or someone else's -- and neither is ours to discard.
    """
    calls: list[str] = []

    def fake_osa(script: str, *args: str, **kw):
        calls.append(script)
        return 0, "", ""

    session = wp.WordSession(launched_by_us=True)
    monkeypatch.setattr(wp, "osa", fake_osa)
    monkeypatch.setattr(wp.WordSession, "open_document_count", lambda self: 1)

    session.quit_if_ours()
    assert not any("close every document" in c for c in calls), calls
    assert not any("quit saving no" in c for c in calls), calls


def test_quit_if_ours_quits_when_word_holds_nothing(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        wp, "osa", lambda script, *a, **k: (calls.append(script), (0, "", ""))[1]
    )
    monkeypatch.setattr(wp.WordSession, "open_document_count", lambda self: 0)

    wp.WordSession(launched_by_us=True).quit_if_ours()
    assert any("quit saving no" in c for c in calls), calls


def test_recovery_prefers_closing_our_document_by_name(monkeypatch) -> None:
    """A foreign document can arrive after preflight and before cleanup.

    `started_clean` records one observation, taken before the first file. The
    close-all it gates runs after every failure for the rest of the run, so a
    document opened in between was closed unsaved. When the failing item has a
    name, closing that is both narrower and sufficient.
    """
    calls: list[tuple[str, tuple[str, ...]]] = []

    def fake_osa(script: str, *args: str, **kw):
        calls.append((script, args))
        return 0, "", ""

    session = wp.WordSession()
    session.started_clean = True
    monkeypatch.setattr(wp, "osa", fake_osa)
    # Word reports a document still open after the named close: the run's own
    # base document in a redline pair, or a foreign one. Either way the
    # escalation still has to be reachable.
    monkeypatch.setattr(wp.WordSession, "open_document_count", lambda self: 0)

    wp.recover_after_failure(session, only="staged__deal.docx")
    scripts = [s for s, _ in calls]
    assert any("close" in s and "name" in s for s in scripts), scripts
    assert not any("close every document" in s for s in scripts), scripts


# ─── the API is held to the CLI's preflight ──────────────────────────────────


def test_convert_folder_preflights_the_session_it_creates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`session=None` is the convenience path, not a way around the check.

    `WordSession.started_clean` defaults to True, so a bare session claims a
    clean Word nobody asked. Recovery then trusts that claim before a
    close-all or a recycle (`quit saving no`).
    """
    src = tmp_path / "src"
    _touch(src / "a.docx")
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    asked: list[dict[str, bool]] = []

    def fake_preflight(session, *, allow_open_docs, one_osascript=False, close_documents=True):
        asked.append(
            {"allow": allow_open_docs, "one": one_osascript, "close": close_documents}
        )
        return "Word did not become responsive"

    monkeypatch.setattr(wp, "preflight", fake_preflight)
    ran: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda *a, **k: ran.append("osa") or (0, "", ""))

    results = wp.convert_folder(src, tmp_path / "out", one_osascript=True, close_documents=False)
    assert asked == [{"allow": False, "one": True, "close": False}]
    assert ran == []
    assert results and all("responsive" in (r.error or "") for r in results)


def test_convert_folder_refuses_a_session_nobody_preflighted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src"
    _touch(src / "a.docx")
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    ran: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda *a, **k: ran.append("osa") or (0, "", ""))
    monkeypatch.setattr(wp, "export_pdf", lambda *a, **k: ran.append("export") or (True, ""))

    results = wp.convert_folder(src, tmp_path / "out", session=wp.WordSession())
    assert ran == []
    assert results and all("preflight" in (r.error or "") for r in results)



# ─── delivery ────────────────────────────────────────────────────────────────


def test_publish_keeps_the_previous_result_when_the_copy_dies_partway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A copy that fails after writing some bytes must not truncate the old file."""
    staged = _touch(tmp_path / "stage" / "a.pdf", b"%PDF-new-and-longer")
    final = _touch(tmp_path / "out" / "a.pdf", b"%PDF-previous")

    def dying_copy(src, dst, *a, **k):
        Path(dst).write_bytes(b"%PD")  # a partial write, then the disk goes away
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(wp.shutil, "copy2", dying_copy)
    problem = wp.publish(staged, final)

    assert "No space left" in problem
    assert final.read_bytes() == b"%PDF-previous"
    assert staged.exists(), "the staged artifact survives for a re-delivery"
    assert sorted(p.name for p in final.parent.iterdir()) == ["a.pdf"], "no temp left behind"


def test_publish_replaces_the_result_whole(tmp_path: Path) -> None:
    staged = _touch(tmp_path / "stage" / "a.pdf", b"%PDF-new")
    final = _touch(tmp_path / "out" / "sub" / "a.pdf", b"%PDF-old")
    assert wp.publish(staged, final) == ""
    assert final.read_bytes() == b"%PDF-new"
    assert sorted(p.name for p in final.parent.iterdir()) == ["a.pdf"]


def test_a_failed_delivery_is_that_document_s_error_not_the_run_s(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(wp, "CONTAINER_TMP", tmp_path / "container")
    src = tmp_path / "src"
    _touch(src / "a.docx")
    _touch(src / "b.docx")
    monkeypatch.setattr(
        wp, "export_pdf", lambda sin, sout, timeout=180.0: (True, _touch(sout, b"%PDF") and "")
    )
    monkeypatch.setattr(
        wp, "publish", lambda staged, final: "disk full" if final.stem == "a" else ""
    )
    session = _verified_session()
    results = wp.convert_folder(src, tmp_path / "out", session=session, one_osascript=False)
    assert [(r.source.name, r.ok) for r in results] == [("a.docx", False), ("b.docx", True)]
    assert "disk full" in results[0].error
