"""The A/B harness's pure parts: applying and restoring a variant, deriving
crash timings from log records, picking fixtures, rendering the report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from test_word_pdf import _touch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import word_ab as ab

# The harness patches the `word_pdf` it imported; assert against that one, not
# the copy test_word_pdf loads (a different module object under xdist).
wp = ab.wp

pytestmark = pytest.mark.usefixtures("no_live_word")


# ─── variants ────────────────────────────────────────────────────────────────


def test_there_are_at_least_ten_variants_with_distinct_names() -> None:
    assert len(ab.VARIANTS) >= 10
    assert len({v.name for v in ab.VARIANTS}) == len(ab.VARIANTS)
    assert ab.VARIANTS[0].name == "baseline" and ab.VARIANTS[1].name == "current"


def test_applied_edits_the_batch_open_line_and_restores_it() -> None:
    before = wp._EXPORT_BATCH
    session = wp.WordSession()
    with ab.applied(ab.BY_NAME["open_norepair"], session):
        assert "open (POSIX file inP) repair false" in wp._EXPORT_BATCH
        assert ab.OPEN_LINE not in wp._EXPORT_BATCH
        assert "repair false" in wp._EXPORT_BATCH_KEEP_OPEN
    assert wp._EXPORT_BATCH is before
    assert ab.OPEN_LINE in wp._EXPORT_BATCH


def test_applied_changes_the_appleevent_timeout_in_every_script() -> None:
    session = wp.WordSession()
    with ab.applied(ab.BY_NAME["ae60"], session):
        for name in ("_EXPORT_BATCH", "_EXPORT_BATCH_KEEP_OPEN", "_EXPORT_PDF", "_EXPORT_PDF_KEEP_OPEN"):
            assert "with timeout of 60 seconds" in getattr(wp, name), name
            assert "with timeout of 240 seconds" not in getattr(wp, name), name
    assert "with timeout of 240 seconds" in wp._EXPORT_BATCH


def test_applied_sets_session_knobs_and_wraps_progress_defaults(tmp_path: Path) -> None:
    session = wp.WordSession()
    original_progress = wp._Progress
    with ab.applied(ab.BY_NAME["grace5"], session):
        assert session.answer_grace == 5.0
    with ab.applied(ab.BY_NAME["poll1"], session):
        p = wp._Progress(tmp_path / "x.log", 3, " pdf")
        assert isinstance(p, original_progress) and p.poll == 1.0 and p.total == 3 and p.label == " pdf"
    assert wp._Progress is original_progress
    assert wp._Progress(tmp_path / "x.log", 3).poll == 5.0


def test_applied_turns_focus_off_for_no_nudge_and_back() -> None:
    session = wp.WordSession()
    assert wp._focus.get() is True
    with ab.applied(ab.BY_NAME["no_nudge"], session):
        assert wp._focus.get() is False
    assert wp._focus.get() is True


def test_quit_first_variant_replaces_recycle_on_that_session_only(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[object] = []
    monkeypatch.setattr(wp, "osa", lambda s, *a, **k: ran.append(s) or (0, "", ""))
    session = wp.WordSession()
    monkeypatch.setattr(session, "_alive", lambda: True)
    monkeypatch.setattr(session, "_gone_within", lambda *a, **k: True)
    monkeypatch.setattr(session, "clean_after_kill", lambda *f: None)
    monkeypatch.setattr(session, "warm", lambda: True)
    with ab.applied(ab.BY_NAME["quit_first"], session):
        assert session.recycle() is True
    assert wp._QUIT in ran and wp._CLOSE_ALL not in ran, "quit-first never tries the close-all"
    assert wp.WordSession().recycle.__func__ is wp.WordSession.recycle  # type: ignore[attr-defined]


# ─── timings ─────────────────────────────────────────────────────────────────


def _rec(t: float, msg: str) -> ab.Record:
    return ab.Record(t, "INFO", msg)


def test_crashes_from_derives_detect_recover_and_resume() -> None:
    growth = [ab.Growth(10.0, 1), ab.Growth(12.0, 2), ab.Growth(30.0, 3)]
    records = [
        _rec(11.0, "[batch pdf 1] 1/5"),
        _rec(13.5, "[watchdog] error report declined via 'OK'; Word said: 'problem'"),
        _rec(14.0, "[batch pdf] pass 1 ended at item 2: Microsoft Word got an error: Connection is invalid. (Word crashed); 3 item(s) not reached"),
        _rec(14.1, "[word] recovery 1: Word is running; closing every document, running: osascript"),
        _rec(14.6, "[word] recovery 1: Word answers (0.2 s after the close-all); carrying on with the same Word"),
        _rec(40.0, "[batch pdf] pass 2 ended at item 4: Microsoft Word got an error: Connection is invalid. (Word crashed); 0 item(s) not reached"),
        _rec(41.0, "[word] recovery 2: Word's process is gone (it crashed); relaunching it"),
        _rec(47.0, "[word] Word answered after 6 s; alerts off"),
    ]
    first, second = ab.crashes_from(records, growth)
    assert first.item == 2 and first.error.startswith("Microsoft Word got an error: Connection is invalid.")
    assert first.detect_s == pytest.approx(2.0)  # 12.0 -> 14.0
    assert first.merp_to_detect_s == pytest.approx(0.5)
    assert first.recover_s == pytest.approx(0.6)
    assert first.resume_s == pytest.approx(30.0 - 14.6)
    assert second.item == 4 and second.detect_s == pytest.approx(10.0)
    assert second.recover_s == pytest.approx(7.0), "a relaunch counts as recovered when Word answers"
    assert second.resume_s is None, "nothing came after"


def test_run_result_summary_has_medians_and_per_crash_cost() -> None:
    crashes = [
        ab.Crash(at=1, item=1, error="x", detect_s=1.0, recover_s=0.5, resume_s=4.0),
        ab.Crash(at=2, item=2, error="x", detect_s=3.0, recover_s=0.7, resume_s=6.0),
    ]
    r = ab.RunResult("baseline", "broken", "t", 100.0, 20, 0, 20, 0, crashes, nudges=3)
    s = r.summary()
    assert s["crashes"] == 2 and s["detect_med_s"] == 2.0 and s["recover_med_s"] == 0.6
    assert s["per_crash_s"] == pytest.approx(5.6)
    assert s["nudges"] == 3 and s["failed"] == 20


# ─── fixtures ────────────────────────────────────────────────────────────────


def test_pick_fixtures_takes_failed_docs_and_a_seeded_random_sample_of_good_ones() -> None:
    lines = [{"kind": "pdf", "original_filename": f"ok{i}.docx", "status": "ok"} for i in range(100)]
    lines += [{"kind": "pdf", "original_filename": f"bad{i}.docx", "status": "failed"} for i in range(25)]
    lines += [{"kind": "rename", "original_filename": "bad0.docx", "status": "renamed"}]
    lines += [{"kind": "pdf", "original_filename": "ok0.docx", "status": "failed"}]  # later line wins
    broken, good = ab.pick_fixtures(lines, broken_n=20, good_n=50, seed=1)
    assert len(broken) == 20 and all(b.startswith("bad") for b in broken)
    assert len(good) == 50 and all(g.startswith("ok") for g in good) and "ok0.docx" not in good
    assert ab.pick_fixtures(lines, broken_n=20, good_n=50, seed=1) == (broken, good), "deterministic"


def test_stage_set_copies_once(tmp_path: Path) -> None:
    src = tmp_path / "src"
    _touch(src / "a.docx", b"PK a")
    staged = ab.stage_set(["a.docx"], src, tmp_path / "dest")
    assert staged[0].read_bytes() == b"PK a"
    staged[0].write_bytes(b"edited")
    ab.stage_set(["a.docx"], src, tmp_path / "dest")
    assert staged[0].read_bytes() == b"edited", "an existing staged file is left alone"


# ─── report ──────────────────────────────────────────────────────────────────


def test_render_report_names_the_fastest_variant_that_lost_no_extra_documents() -> None:
    summaries = [
        {"variant": "baseline", "set": "broken", "wall_s": 300.0, "ok": 0, "failed": 20, "crashes": 40, "nudges": 0},
        {"variant": "crash1", "set": "broken", "wall_s": 150.0, "ok": 0, "failed": 20, "crashes": 20, "nudges": 0},
        {"variant": "lossy", "set": "broken", "wall_s": 100.0, "ok": 0, "failed": 21, "crashes": 21, "nudges": 0},
    ]
    text = ab.render_report(summaries)
    assert "`broken`: `crash1` in 150.0 s" in text
    assert "| crash1 | broken | 150.0 |" in text
    json.dumps(summaries)  # what results.jsonl holds must stay JSON


def test_merp_auto_variant_writes_the_defaults_for_the_run_and_deletes_them_after(monkeypatch: pytest.MonkeyPatch) -> None:
    ran: list[list[str]] = []

    class Done:
        returncode = 0
        stdout = stderr = ""

    monkeypatch.setattr(ab.subprocess, "run", lambda cmd, **k: ran.append(list(cmd)) or Done())
    with ab.applied(ab.BY_NAME["merp_auto"], wp.WordSession()):
        assert ["defaults", "write", "com.microsoft.errorreporting", "SendReportAutomatically", "-bool", "true"] in ran
        assert ["defaults", "write", "com.microsoft.errorreporting", "QuitAfterGeneratingReport", "-bool", "true"] in ran
        assert not any(c[1] == "delete" for c in ran)
    assert ["defaults", "delete", "com.microsoft.errorreporting", "SendReportAutomatically"] in ran
    assert ["defaults", "delete", "com.microsoft.errorreporting", "QuitAfterGeneratingReport"] in ran


def test_merp_kill_variant_turns_the_crash_signal_on_in_the_watchdogs() -> None:
    v = ab.BY_NAME["merp_kill_crash1"]
    assert wp.Watchdogs(**v.watchdogs).kill_pass_on_crash is True
    assert v.convert == {"crash_limit": 1}
    assert ab.BY_NAME["merp_kill"].convert == {"crash_limit": 2}, "pinned: signal with the old retry"
    assert ab.BY_NAME["poll1"].watchdogs == {"kill_pass_on_crash": False}, "every pinned variant turns the signal off"
    assert wp.Watchdogs().kill_pass_on_crash is True, "the A/B winner is the driver's default"
    base = ab.BY_NAME["baseline"]
    assert base.convert == {"crash_limit": 2} and base.watchdogs == {"kill_pass_on_crash": False}, (
        "baseline stays the pre-A/B driver, pinned, so reruns compare against the same thing"
    )
    cur = ab.BY_NAME["current"]
    assert cur.convert == {} and cur.watchdogs == {} and cur.open_line is None


def test_render_report_drops_named_runs_and_says_why() -> None:
    summaries = [
        {"variant": "baseline", "set": "mixed", "started_at": "t1", "wall_s": 300.0, "ok": 48, "failed": 22, "crashes": 39, "nudges": 0},
        {"variant": "current", "set": "mixed", "started_at": "t2", "wall_s": 9.0, "ok": 0, "failed": 70, "crashes": 0, "nudges": 0},
    ]
    text = ab.render_report(summaries, {"t2": "another driver held Word (PID 19876)"})
    assert "| current |" not in text.split("## Dropped")[0]
    assert "`current` on `mixed` started t2: another driver held Word (PID 19876)" in text
    assert "`mixed`: `baseline` in 300.0 s" in text
