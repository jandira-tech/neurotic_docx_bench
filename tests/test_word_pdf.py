"""Spec for the reusable half of the Word driver pair (``scripts/word_pdf.py``).

Everything exercised here is pure or filesystem-only: no Microsoft Word, no
macOS, no ``osascript``. The Word-facing calls are reached through ``osa``,
which is patched, so the AppleScript strings themselves are covered as data
(argument order, argv shape) rather than by execution.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "word_pdf.py"


def _load():
    spec = importlib.util.spec_from_file_location("word_pdf", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["word_pdf"] = mod
    spec.loader.exec_module(mod)
    return mod


wp = _load()


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


def test_osa_timeout_kills_and_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    killed: list[list[str]] = []

    def fake_run(cmd, **kw):
        if cmd[0] == "osascript":
            raise wp.subprocess.TimeoutExpired(cmd, 1)
        killed.append(cmd)

        class _Done:
            returncode = 0
            stdout = ""
            stderr = ""

        return _Done()

    monkeypatch.setattr(wp.subprocess, "run", fake_run)
    rc, out, err = wp.osa("SCRIPT", timeout=1)

    assert rc is None and out == ""
    assert "timed out" in err
    # SIGKILL, by exact process name: a blocked osascript ignores SIGTERM.
    assert killed == [["pkill", "-9", "-x", "osascript"]]


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
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)

    results = wp.convert_folder(src, tmp_path / "out", session=session)
    assert len(results) == 1 and results[0].skipped and results[0].ok
    assert calls == []

    results = wp.convert_folder(src, tmp_path / "out", force=True, session=session)
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
    session = wp.WordSession()
    monkeypatch.setattr(session, "warm", lambda: True)
    recycled: list[tuple] = []
    monkeypatch.setattr(session, "recycle", lambda *f: recycled.append(f) or True)

    results = wp.convert_folder(src, tmp_path / "out", session=session)
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

    assert "--allow-open-docs" in wp.preflight(session, allow_open_docs=False)
    assert wp.preflight(session, allow_open_docs=True) == ""


def test_preflight_reports_unresponsive_word(monkeypatch: pytest.MonkeyPatch) -> None:
    session = wp.WordSession()
    monkeypatch.setattr(wp.WordSession, "available", staticmethod(lambda: True))
    monkeypatch.setattr(session, "warm", lambda: False)
    assert "responsive" in wp.preflight(session, allow_open_docs=True)


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
            return (0, "Don’t Send\tSend\t", "") if args[0] == wp.MERP_PROC else (0, "", "")
        if script is wp._PRESS:
            pressed_on.append(args[0])
            return 0, "Don’t Send", ""
        return 0, "", ""

    monkeypatch.setattr(wp, "osa", fake_osa)
    dogs = wp.Watchdogs(poll=0.01)
    dogs.start()
    deadline = wp.time.monotonic() + 3
    while not pressed_on and wp.time.monotonic() < deadline:
        wp.time.sleep(0.02)
    dogs.stop()

    assert wp.MERP_PROC in pressed_on


def test_watchdog_stop_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (0, "", ""))
    dogs = wp.Watchdogs(poll=0.01)
    with dogs:
        pass
    dogs.stop()


# ─── WordSession ─────────────────────────────────────────────────────────────


def test_recycle_escalates_gracefully_then_cleans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """quit → pkill -x → pkill -9 -x, never pkill -f, then wipe the debris."""
    recovery = tmp_path / "AutoRecovery"
    _touch(recovery / "stale.olk")
    folder = tmp_path / "work"
    _touch(folder / "~$deal.docx")
    _touch(folder / "deal.docx")

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

    assert session.recycle(folder) is True
    assert ["pkill", "-x", wp.WORD_PROC] in cmds
    assert ["pkill", "-9", "-x", wp.WORD_PROC] in cmds
    assert not any("-f" in c for c in cmds)
    assert list(recovery.iterdir()) == []
    assert not (folder / "~$deal.docx").exists()
    assert (folder / "deal.docx").exists()


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
    monkeypatch.setattr(wp, "preflight", lambda s, *, allow_open_docs: "Word is busy")
    result = CliRunner().invoke(wp.app, ["--src", str(tmp_path / "src"), "--no-check-preset"])
    assert result.exit_code == 2


def test_cli_runs_the_batch_and_returns_the_report_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    src = tmp_path / "src"
    _touch(src / "a.docx")
    monkeypatch.setattr(wp, "preflight", lambda s, *, allow_open_docs: "")
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


def test_warm_gives_up_at_its_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter([0.0, 0.0, 5.0, 999.0])
    monkeypatch.setattr(wp, "osa", lambda *a, **k: (1, "", "no"))
    monkeypatch.setattr(wp.subprocess, "run", lambda cmd, **k: None)
    monkeypatch.setattr(wp.time, "sleep", lambda _s: None)
    monkeypatch.setattr(wp.time, "monotonic", lambda: next(clock))

    assert wp.WordSession(warm_timeout=10).warm() is False


def test_quit_if_ours_only_quits_a_word_we_launched(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(wp, "osa", lambda script, *a, **k: calls.append(script) or (0, "", ""))

    wp.WordSession(launched_by_us=False).quit_if_ours()
    assert calls == []

    wp.WordSession(launched_by_us=True).quit_if_ours()
    assert wp._CLOSE_ALL in calls


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
