#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["loguru", "rich", "typer"]
# ///
"""A/B the Word PDF driver's crash handling on a fixed set of fixtures.

AGENTS.md rule (2026-10-14): the next time a batch turns up a bunch of
documents that crash Word, stop, take 20 of them, and time at least ten driver
variants replaying the same 20 on how quickly each one detects the crash,
closes what is open and gets Word back to work. Pick the best, then add 50
random good fixtures and check it is not slower on the happy path.

The variants change nothing in `scripts/word_pdf.py`: each one is a set of
overrides applied to that module for the duration of one run (a knob on the
session, the progress watcher or the watchdogs; an edit to the AppleScript's
`open` line; a different recovery policy) and restored afterwards, so every
run drives the one driver that the batches use.

What is measured per run, from the driver's own log lines and the batch log's
growth (polled every 0.1 s):

- `wall_s`: the whole `convert_folder` call.
- per crash: `detect_s` (last batch-log growth → the driver's "pass N ended"
  line), `merp_to_detect_s` (Microsoft Error Reporting dismissed → that line,
  when the reporter was seen), `recover_s` ("pass N ended" → "carrying on with
  the same Word" / "Word answered"), `resume_s` (recovered → the next pass's
  first batch-log growth).
- `nudges`: focus flips the progress watcher made (each costs `nudge_wait`).
- outcomes: ok / failed / skipped, so a faster variant that loses outputs is
  visible as such.

    uv run scripts/word_ab.py stage      # pick 20 broken + 50 good into out/ab
    uv run scripts/word_ab.py run --set broken --variant baseline --variant crash1
    uv run scripts/word_ab.py run --set broken          # every variant
    uv run scripts/word_ab.py report                    # out/ab/AB_REPORT.md
"""

from __future__ import annotations

import contextlib
import json
import random
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import types
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Self

import typer
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
import word_pdf as wp

AB_ROOT = Path("out/ab")
BENCH_SRC = Path("out/bench_corpus_all/docx")
BENCH_MANIFEST = Path("out/bench_corpus_all/pdf/manifest.jsonl")
BROKEN_N = 20
GOOD_N = 50
SEED = 20261014
OPEN_LINE = "open POSIX file inP"


# ─── variants ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Variant:
    """One configuration of the driver, applied as overrides for one run."""

    name: str
    about: str
    session: dict[str, object] = field(default_factory=dict)  # WordSession attributes
    progress: dict[str, object] = field(default_factory=dict)  # _Progress class defaults
    watchdogs: dict[str, object] = field(default_factory=dict)  # Watchdogs(...) kwargs
    convert: dict[str, object] = field(default_factory=dict)  # convert_folder(...) kwargs
    focus: bool | None = None  # _focus ContextVar
    open_line: str | None = None  # replaces `open POSIX file inP` in the batch script
    ae_timeout: int | None = None  # replaces the AppleEvent `with timeout of N seconds`
    recovery: str = "close_all_first"  # or "quit_first"
    # macOS defaults written for the run and deleted after it: {domain: {key: bool}}
    defaults: dict[str, dict[str, bool]] = field(default_factory=dict)


# Every variant is pinned to the pre-A/B driver (crash limit 2, no crash
# signal) except for the knob it tests, so a rerun after the defaults changed
# still measures the same thing. `current` alone takes the driver as it ships.
_PINNED_CONVERT: dict[str, object] = {"crash_limit": 2}
_PINNED_WATCHDOGS: dict[str, object] = {"kill_pass_on_crash": False}


def _pinned(name: str, about: str, **overrides: object) -> Variant:
    convert = {**_PINNED_CONVERT, **overrides.pop("convert", {})}  # type: ignore[dict-item]
    watchdogs = {**_PINNED_WATCHDOGS, **overrides.pop("watchdogs", {})}  # type: ignore[dict-item]
    return Variant(name, about, convert=convert, watchdogs=watchdogs, **overrides)  # type: ignore[arg-type]


_MERP_DEFAULTS = {"com.microsoft.errorreporting": {"SendReportAutomatically": True, "QuitAfterGeneratingReport": True}}

VARIANTS: tuple[Variant, ...] = (
    _pinned("baseline", "the driver as it was before the 2026-10-14 A/B: close-all first, crash limit 2, nudges on, no crash signal"),
    Variant("current", "the driver as it ships now (no overrides): the A/B winner is its default"),
    _pinned("crash1", "a document that crashes Word once is not retried", convert={"crash_limit": 1}),
    _pinned("crash3", "three crashes before giving up on a document (cost of the extra retry)", convert={"crash_limit": 3}),
    _pinned("no_nudge", "no focus flips while an item is open (nudge_wait saved on slow documents)", focus=False),
    _pinned("poll1", "progress watcher polls the batch log every 1 s instead of 5", progress={"poll": 1.0}),
    _pinned("grace5", "waits at most 5 s (not 15) for Word to answer after the close-all", session={"answer_grace": 5.0}),
    _pinned("ae60", "AppleEvent timeout 60 s instead of 240 (a hung open costs 60 s, not 240)", ae_timeout=60),
    _pinned("open_norepair", "open with `repair false`: Word is told not to repair a broken file", open_line="open (POSIX file inP) repair false"),
    _pinned("open_readonly", "open with `read only true`", open_line="open (POSIX file inP) read only true"),
    _pinned("open_quiet", "open with `confirm conversions false add to recent files false` (the serial script's form)", open_line="open (POSIX file inP) confirm conversions false add to recent files false"),
    _pinned("watchdog_fast", "watchdogs poll every 0.25 s (error reporter dismissed sooner)", watchdogs={"poll": 0.25}),
    _pinned("quit_first", "the pre-2026-10-14 recovery: quit Word and relaunch instead of close-all first", recovery="quit_first"),
    _pinned("serial_crash1", "one osascript per document, crash limit 1", convert={"one_osascript": False, "crash_limit": 1}),
    _pinned("merp_kill", "the error reporter is the crash signal: on seeing it the watchdog marks the item [retry] and ends the pass at once", watchdogs={"kill_pass_on_crash": True}),
    _pinned("merp_kill_crash1", "merp_kill plus crash limit 1", watchdogs={"kill_pass_on_crash": True}, convert={"crash_limit": 1}),
    _pinned("merp_auto", "`defaults write com.microsoft.errorreporting SendReportAutomatically/QuitAfterGeneratingReport true` (keys read from the 16.115 binary, undocumented): does the reporter stay off screen, and what does that do to detection?", defaults=_MERP_DEFAULTS),
    _pinned("merp_auto_crash1", "merp_auto plus crash limit 1", defaults=_MERP_DEFAULTS, convert={"crash_limit": 1}),
)

BY_NAME = {v.name: v for v in VARIANTS}


def _quit_first_recycle(self: wp.WordSession, *folders: Path) -> bool:
    """The old policy, for the A/B only: no close-all, straight to quit, then relaunch."""
    self.restarts += 1
    tag = f"[word] recovery {self.restarts}:"
    if self._alive():
        logger.warning(f"{tag} asking Word to quit, running: {wp.shown(wp._QUIT)}")
        self._run_logged(tag, wp._QUIT, timeout=self.quit_grace + 5)
        if self._gone_within(self.quit_grace):
            logger.info(f"{tag} Word quit on request")
        else:
            term = ["pkill", "-x", wp.WORD_PROC]
            logger.warning(f"{tag} Word did not quit within {self.quit_grace:.0f} s; running: {wp.shown(term)}")
            self._run_logged(tag, term)
            self._gone_within(5.0)
    else:
        logger.warning(f"{tag} Word's process is gone (it crashed); relaunching it")
    self.clean_after_kill(*folders)
    return self.warm()


def _defaults(args: list[str]) -> None:
    """One `defaults …` command, logged with its result on the next line."""
    cmd = ["defaults", *args]
    logger.info(f"[ab] running: {wp.shown(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    err = (proc.stderr or proc.stdout or "").strip().splitlines()
    logger.info(f"[ab] returned rc={proc.returncode}" + (f", {err[0]}" if err else ""))


@contextlib.contextmanager
def applied(variant: Variant, session: wp.WordSession) -> Iterator[None]:
    """Apply `variant` to `word_pdf` and `session`; restore everything on exit."""
    saved: dict[str, object] = {
        "_EXPORT_BATCH": wp._EXPORT_BATCH,
        "_EXPORT_BATCH_KEEP_OPEN": wp._EXPORT_BATCH_KEEP_OPEN,
        "_EXPORT_PDF": wp._EXPORT_PDF,
        "_EXPORT_PDF_KEEP_OPEN": wp._EXPORT_PDF_KEEP_OPEN,
    }
    progress_cls = wp._Progress
    focus_token = wp._focus.set(variant.focus) if variant.focus is not None else None
    try:
        for k, v in variant.session.items():
            setattr(session, k, v)
        if variant.progress:
            # Dataclass defaults are bound into __init__ at class creation, so a
            # class attribute would change nothing: wrap the constructor instead.
            overrides = dict(variant.progress)

            def make_progress(*args: object, **kwargs: object) -> object:
                return progress_cls(*args, **{**overrides, **kwargs})

            wp._Progress = make_progress  # type: ignore[assignment]
        if variant.open_line is not None:
            for name in ("_EXPORT_BATCH", "_EXPORT_BATCH_KEEP_OPEN"):
                script = getattr(wp, name)
                if script.count(OPEN_LINE) != 1:
                    raise RuntimeError(f"{name} does not contain exactly one {OPEN_LINE!r}")
                setattr(wp, name, script.replace(OPEN_LINE, variant.open_line))
        if variant.ae_timeout is not None:
            pattern = re.compile(r"with timeout of \d+ seconds")
            for name in saved:
                setattr(wp, name, pattern.sub(f"with timeout of {variant.ae_timeout} seconds", getattr(wp, name)))
        if variant.recovery == "quit_first":
            session.recycle = types.MethodType(_quit_first_recycle, session)  # type: ignore[method-assign]
        elif variant.recovery != "close_all_first":
            raise ValueError(f"unknown recovery policy {variant.recovery!r}")
        for domain, keys in variant.defaults.items():
            for key, value in keys.items():
                _defaults(["write", domain, key, "-bool", "true" if value else "false"])
        yield
    finally:
        for domain, keys in variant.defaults.items():
            for key in keys:
                _defaults(["delete", domain, key])
        for name, value in saved.items():
            setattr(wp, name, value)
        wp._Progress = progress_cls
        if focus_token is not None:
            wp._focus.reset(focus_token)


# ─── measuring ───────────────────────────────────────────────────────────────


@dataclass
class Record:
    t: float  # monotonic seconds
    level: str
    message: str


@dataclass
class Growth:
    t: float
    lines: int


class BatchLogWatcher:
    """Poll the batch log the driver is writing (`word_pdf._BATCH_LOG`) and
    record every moment its line count grew, at 0.1 s resolution."""

    def __init__(self, poll: float = 0.1) -> None:
        self.poll = poll
        self.growth: list[Growth] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        last: tuple[Path | None, int] = (None, -1)
        while not self._stop.wait(self.poll):
            path = wp._BATCH_LOG
            if path is None:
                continue
            try:
                n = sum(1 for ln in path.read_text(errors="replace").splitlines() if ln.startswith(("[ok]", "[fail]", "[retry]")))
            except OSError:
                continue
            if (path, n) != last:
                last = (path, n)
                self.growth.append(Growth(time.monotonic(), n))

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=2)


_PASS_ENDED = re.compile(r"pass (\d+) ended at item (\d+): (.*?)(?:;|$)")
# Recovery is over when the same Word answers after the close-all, or a
# relaunched one has warmed up ("Word answered after N s; alerts off").
_RECOVERED = re.compile(r"carrying on with the same Word|Word answered after [\d.]+ s")
_MERP = re.compile(r"error report declined|Error Reporting shows")
_NUDGE = re.compile(r"\[focus\] item \d+/\d+ not finished")


@dataclass
class Crash:
    at: float
    item: int
    error: str
    detect_s: float | None = None
    merp_to_detect_s: float | None = None
    recover_s: float | None = None
    resume_s: float | None = None


def crashes_from(records: list[Record], growth: list[Growth]) -> list[Crash]:
    """Derive one `Crash` per "pass N ended" line, with its four timings.

    Recovery ends at the first "carrying on with the same Word" (close-all
    worked) or "Word answered after" (a relaunch warmed up) after the crash
    line; resume is the first batch-log growth after that.
    """
    crashes: list[Crash] = []
    for i, rec in enumerate(records):
        m = _PASS_ENDED.search(rec.message)
        if not m:
            continue
        crash = Crash(at=rec.t, item=int(m.group(2)), error=m.group(3).strip())
        before = [g.t for g in growth if g.t <= rec.t]
        if before:
            crash.detect_s = rec.t - before[-1]
        merps = [r.t for r in records[:i] if _MERP.search(r.message) and r.t >= (before[-1] if before else 0)]
        if merps:
            crash.merp_to_detect_s = rec.t - merps[-1]
        recovered_at: float | None = None
        for later in records[i + 1 :]:
            if _PASS_ENDED.search(later.message):
                break
            if _RECOVERED.search(later.message):
                recovered_at = later.t
                break
        if recovered_at is not None:
            crash.recover_s = recovered_at - rec.t
            after = [g.t for g in growth if g.t > recovered_at]
            if after:
                crash.resume_s = after[0] - recovered_at
        crashes.append(crash)
    return crashes


@dataclass
class RunResult:
    variant: str
    fixture_set: str
    started_at: str
    wall_s: float
    documents: int
    ok: int
    failed: int
    skipped: int
    crashes: list[Crash]
    nudges: int
    notes: str = ""

    def summary(self) -> dict[str, object]:
        def med(values: list[float | None]) -> float | None:
            xs = [v for v in values if v is not None]
            return round(statistics.median(xs), 2) if xs else None

        return {
            "variant": self.variant,
            "set": self.fixture_set,
            "started_at": self.started_at,
            "wall_s": round(self.wall_s, 1),
            "documents": self.documents,
            "ok": self.ok,
            "failed": self.failed,
            "skipped": self.skipped,
            "crashes": len(self.crashes),
            "detect_med_s": med([c.detect_s for c in self.crashes]),
            "merp_to_detect_med_s": med([c.merp_to_detect_s for c in self.crashes]),
            "recover_med_s": med([c.recover_s for c in self.crashes]),
            "resume_med_s": med([c.resume_s for c in self.crashes]),
            "per_crash_s": round(
                sum((c.recover_s or 0) + (c.resume_s or 0) for c in self.crashes) / len(self.crashes), 2
            )
            if self.crashes
            else None,
            "nudges": self.nudges,
            "notes": self.notes,
        }


def _capture(records: list[Record]) -> int:
    def sink(message: object) -> None:
        rec = message.record  # type: ignore[attr-defined]
        records.append(Record(time.monotonic(), rec["level"].name, rec["message"]))

    return logger.add(sink, level="DEBUG")


def run_variant(
    variant: Variant, src: Path, out_dir: Path, *, fixture_set: str, timeout: float = 180.0
) -> RunResult:
    """One measured `convert_folder` run under `variant`, into a fresh `out_dir`."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    records: list[Record] = []
    handler = _capture(records)
    session = wp.WordSession()
    started_at = datetime.now(UTC).isoformat(timespec="seconds")
    notes = ""
    try:
        with applied(variant, session):
            one = bool(variant.convert.get("one_osascript", True))
            problem = wp.preflight(session, allow_open_docs=False, one_osascript=one, close_documents=True)
            if problem:
                raise RuntimeError(problem)
            kwargs: dict[str, object] = {"timeout": timeout, "session": session, "close_documents": True}
            kwargs.update(variant.convert)
            started = time.monotonic()
            with wp.Watchdogs(**variant.watchdogs), BatchLogWatcher() as watcher:  # type: ignore[arg-type]
                results = wp.convert_folder(src, out_dir, **kwargs)  # type: ignore[arg-type]
            wall = time.monotonic() - started
    finally:
        logger.remove(handler)
    crashes = crashes_from(records, watcher.growth)
    nudges = sum(1 for r in records if _NUDGE.search(r.message))
    return RunResult(
        variant=variant.name,
        fixture_set=fixture_set,
        started_at=started_at,
        wall_s=wall,
        documents=len(results),
        ok=sum(1 for r in results if r.ok and not r.skipped),
        failed=sum(1 for r in results if not r.ok),
        skipped=sum(1 for r in results if r.skipped),
        crashes=crashes,
        nudges=nudges,
        notes=notes,
    )


# ─── fixtures ────────────────────────────────────────────────────────────────


def pick_fixtures(
    manifest_lines: list[dict[str, object]], *, broken_n: int = BROKEN_N, good_n: int = GOOD_N, seed: int = SEED
) -> tuple[list[str], list[str]]:
    """From a driver manifest: the documents that failed (Word crashed on them),
    and `good_n` random ones that rendered ok. Deterministic for a seed."""
    latest: dict[str, dict[str, object]] = {}
    for line in manifest_lines:
        if line.get("kind") == "pdf":
            latest[str(line["original_filename"])] = line
    broken = sorted(name for name, ln in latest.items() if ln.get("status") == "failed")
    good = sorted(name for name, ln in latest.items() if ln.get("status") in ("ok", "skipped"))
    rng = random.Random(seed)
    return broken[:broken_n], sorted(rng.sample(good, min(good_n, len(good))))


def stage_set(names: list[str], src: Path, dest: Path) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    staged = []
    for name in names:
        target = dest / name
        if not target.exists():
            shutil.copy2(src / name, target)
        staged.append(target)
    return staged


# ─── report ──────────────────────────────────────────────────────────────────


COLUMNS = (
    ("variant", "Variant"),
    ("set", "Set"),
    ("wall_s", "Wall s"),
    ("ok", "ok"),
    ("failed", "failed"),
    ("crashes", "Crashes"),
    ("detect_med_s", "Detect med s"),
    ("recover_med_s", "Recover med s"),
    ("resume_med_s", "Resume med s"),
    ("per_crash_s", "Per crash s"),
    ("nudges", "Nudges"),
)


def report_table(summaries: list[dict[str, object]]) -> str:
    head = "| " + " | ".join(title for _, title in COLUMNS) + " |"
    sep = "|" + "|".join("---" for _ in COLUMNS) + "|"
    rows = [head, sep]
    for s in sorted(summaries, key=lambda s: (str(s["set"]), float(s["wall_s"]))):
        rows.append("| " + " | ".join("" if s.get(k) is None else str(s.get(k)) for k, _ in COLUMNS) + " |")
    return "\n".join(rows)


def render_report(summaries: list[dict[str, object]], dropped: dict[str, str] | None = None) -> str:
    """The report. `dropped` maps a run's `started_at` to the reason it is left
    out of the tables (a run measured under a concurrent driver, say); the
    reasons are printed so the exclusion is on the record."""
    dropped = dropped or {}
    left_out = [s for s in summaries if str(s.get("started_at")) in dropped]
    summaries = [s for s in summaries if str(s.get("started_at")) not in dropped]
    about = "\n".join(f"- `{v.name}`: {v.about}" for v in VARIANTS)
    best: list[str] = []
    for fixture_set in sorted({str(s["set"]) for s in summaries}):
        rows = [s for s in summaries if s["set"] == fixture_set]
        full = [s for s in rows if s["failed"] == min(int(r["failed"]) for r in rows)]
        winner = min(full, key=lambda s: float(s["wall_s"]))
        best.append(
            f"- `{fixture_set}`: `{winner['variant']}` in {winner['wall_s']} s "
            f"({winner['ok']} ok, {winner['failed']} failed, {winner['crashes']} crashes); "
            f"fastest among the variants that lost no more documents than any other."
        )
    excluded = ""
    if left_out:
        excluded = "\n\n## Dropped\n\n" + "\n".join(
            f"- `{s['variant']}` on `{s['set']}` started {s.get('started_at')}: {dropped[str(s.get('started_at'))]}" for s in left_out
        )
    return (
        "# Word driver A/B\n\n"
        f"Generated {datetime.now(UTC).isoformat(timespec='seconds')} by `scripts/word_ab.py report`. "
        "One row per run; `Detect` is last batch-log growth to the driver's crash line, `Recover` that line "
        "to Word answering again, `Resume` to the next pass's first output. Medians over the run's crashes.\n\n"
        "## Variants\n\n" + about + "\n\n## Runs\n\n" + report_table(summaries) + "\n\n## Best\n\n" + "\n".join(best)
        + excluded + "\n"
    )


# ─── CLI ─────────────────────────────────────────────────────────────────────

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def stage(
    manifest: Annotated[Path, typer.Option(help="driver manifest to pick from")] = BENCH_MANIFEST,
    src: Annotated[Path, typer.Option(help="folder holding those docx")] = BENCH_SRC,
    root: Annotated[Path, typer.Option()] = AB_ROOT,
) -> None:
    """Pick the broken and good fixtures and copy them under `root`."""
    lines = [json.loads(ln) for ln in manifest.read_text(encoding="utf-8").splitlines() if ln.strip()]
    broken, good = pick_fixtures(lines)
    stage_set(broken, src, root / "broken" / "docx")
    stage_set(good, src, root / "good" / "docx")
    mixed = root / "mixed" / "docx"
    stage_set(broken + good, src, mixed)
    (root / "fixtures.json").write_text(json.dumps({"broken": broken, "good": good}, indent=1), encoding="utf-8")
    typer.echo(f"staged {len(broken)} broken, {len(good)} good, {len(broken) + len(good)} mixed under {root}")


@app.command()
def run(
    fixture_set: Annotated[str, typer.Option("--set", help="broken | good | mixed")] = "broken",
    variant: Annotated[list[str] | None, typer.Option("--variant", "-v", help="variant name(s); default all")] = None,
    root: Annotated[Path, typer.Option()] = AB_ROOT,
    log: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Run the chosen variants on one fixture set, one after another, appending to results.jsonl."""
    logger.remove()
    logger.add(wp.make_console_sink(), colorize=True, level="INFO")
    if log:
        logger.add(str(log), level="DEBUG")
    names = variant or [v.name for v in VARIANTS]
    unknown = [n for n in names if n not in BY_NAME]
    if unknown:
        raise typer.BadParameter(f"unknown variant(s): {unknown}; known: {sorted(BY_NAME)}")
    src = root / fixture_set / "docx"
    if not src.is_dir():
        raise typer.BadParameter(f"no fixture set at {src}; run `stage` first")
    results_path = root / "results.jsonl"
    for name in names:
        v = BY_NAME[name]
        logger.info(f"[ab] ===== {v.name} on {fixture_set}: {v.about}")
        result = run_variant(v, src, root / "runs" / fixture_set / v.name, fixture_set=fixture_set)
        summary = result.summary()
        with results_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**summary, "crash_detail": [c.__dict__ for c in result.crashes]}) + "\n")
        logger.info(f"[ab] {v.name}: {json.dumps(summary)}")


@app.command()
def report(
    root: Annotated[Path, typer.Option()] = AB_ROOT,
    drop: Annotated[list[str] | None, typer.Option("--drop", help="STARTED_AT=reason: leave that run out, on the record")] = None,
) -> None:
    """Write AB_REPORT.md from results.jsonl."""
    lines = [json.loads(ln) for ln in (root / "results.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    summaries = [{k: v for k, v in ln.items() if k != "crash_detail"} for ln in lines]
    dropped = dict(item.split("=", 1) for item in (drop or []))
    text = render_report(summaries, dropped)
    (root / "AB_REPORT.md").write_text(text, encoding="utf-8")
    typer.echo(text)


if __name__ == "__main__":
    app()
