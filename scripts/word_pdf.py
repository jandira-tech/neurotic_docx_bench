#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12", "rich>=13.0", "loguru>=0.7"]
# ///
"""Drive Microsoft Word for Mac to export DOCX to PDF, unattended.

The reusable half of the pair: `word_redline.py` imports `WordSession`, `Stage`,
`Watchdogs` and `export_pdf` from here rather than duplicating the Word-driving
code.

Every design decision below traces to a finding in `docs/WORD_DRIVER_AUDIT.md`,
which reviewed the 21 scripts this one replaces:

- **Paths are never interpolated into AppleScript.** `osascript -e SCRIPT a b`
  with `on run argv`, so a quote, backslash or newline in a filename is inert
  (§5.10).
- **`~$*.docx` is excluded everywhere.** Word's owner/lock files are DOCX by
  extension and unopenable in fact; 102 of them are committed into the old
  generated batches, each costing a full AppleEvent timeout (§5.5).
- **Staged inside Word's container, in a fresh directory per run.** Outside the
  container the Grant File Access sheet fires *per file* — the grant does not
  carry to the next file in the same folder (§6.1). A per-run `mktemp` avoids
  the file-access error other scripts hit when reusing one shared staging
  directory (§5.3).
- **The result is identified by exclusion, never `active document`.** A compare
  that silently produces nothing leaves the base frontmost, and saving that
  ships a change-free document that scores as garbage (§14.1). Used by
  `word_redline.py`; kept here because the rule is the same for any save.
- **Health is evaluated before success is recorded**, not after (§14.1).
- **`osascript` is killed with SIGKILL.** Blocked on an unanswered Apple event
  it ignores SIGTERM, so a plain timeout never fires (§14.2).
- **Escalation is graceful-first:** `quit saving no`, then `pkill -x` (SIGTERM,
  exact name — never `-f`, which matches any command line mentioning Word),
  then `pkill -9 -x` (§12, §14.5).
- **After any kill: AutoRecovery is wiped and lock files removed**, or the next
  launch opens the Document Recovery pane and blocks before any script command
  runs (§12).
- **Two watchdogs, not one.** Word's own modal dialogs *and* Microsoft Error
  Reporting, which is a separate process: all 13 `tell process` blocks in the
  audited corpus targeted `"Microsoft Word"`, so none of them could ever see
  MERP's prompt (§12.1).
- **Word is pre-warmed.** A cold start is ~30s; budgets that cover launch *and*
  work are wrong in both directions at once (§10).

PDF preset: `save as … file format format PDF` inherits whatever "Optimize for"
was last chosen in Word's own Save As dialog. For print-fidelity output pick
**"Best for printing"** — the second option — once by hand. `--check-preset`
prints the reminder; `--no-check-preset` suppresses it.

Usage:
    ./word_pdf.py --src ./docx --out ./pdf
    ./word_pdf.py --src ./docx                 # writes PDFs beside the DOCX
    ./word_pdf.py --src ./docx --force --timeout 300
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

console = Console()

WORD_APP = Path("/Applications/Microsoft Word.app")
WORD_PROC = "Microsoft Word"
MERP_PROC = "Microsoft Error Reporting"
CONTAINER_TMP = Path.home() / "Library/Containers/com.microsoft.Word/Data/tmp"
AUTORECOVERY = (
    Path.home()
    / "Library/Containers/com.microsoft.Word/Data/Library/Preferences/AutoRecovery"
)

# MERP's decline control. The straight and curly apostrophes are both listed
# because macOS UI labels normally use U+2019 and a straight-quote match would
# silently never fire. The watchdog logs every button it actually sees the first
# time it meets this dialog, so the real label is recorded rather than guessed.
MERP_DECLINE = ("Don't Send", "Don’t Send", "Cancel", "Close", "Quit", "No")

# Word's own alerts. Grant/Select/Open/Allow are pressed to ACCEPT a sandbox
# prompt; Cancel is pressed only on a non-grant alert. Pressing Cancel on a
# Grant sheet denies the access and guarantees a re-prompt on every later file —
# the defect §14.3 found in the old watchdog.
GRANT_BUTTONS = ("Grant Access", "Grant", "Select…", "Select...", "Select", "Open", "Allow")
DISMISS_BUTTONS = ("OK", "Ok", "Close", "Don't Save", "No", "Cancel")


# ─── pure helpers (no Word, no macOS — unit-testable anywhere) ────────────────


def is_word_temp(name: str) -> bool:
    """Word owner/lock files look like documents and are not documents.

    They are created beside any open document and left behind by a killed Word.
    """
    return name.startswith("~$") or name.startswith(".~")


def iter_docx(folder: Path) -> list[Path]:
    """Every real .docx directly in `folder`, sorted, lock files excluded."""
    return sorted(
        p
        for p in folder.glob("*.docx")
        if p.is_file() and not is_word_temp(p.name)
    )


def pdf_path_for(docx: Path, out_dir: Path | None) -> Path:
    """Where a document's PDF goes: beside it, or into `out_dir`."""
    return (out_dir or docx.parent) / f"{docx.stem}.pdf"


def classify_failure(returncode: int | None, stderr: str, produced: bool) -> str:
    """One-line reason for a failed conversion (pure)."""
    if produced:
        return ""
    if returncode is None:
        return "timed out (Word may be holding a modal)"
    if stderr.strip():
        return stderr.strip().splitlines()[0][:200]
    return f"osascript exit {returncode}, no output file"


@dataclass(slots=True)
class Result:
    """Outcome for one document."""

    source: Path
    output: Path | None = None
    ok: bool = False
    skipped: bool = False
    error: str = ""
    seconds: float = 0.0


# ─── osascript ───────────────────────────────────────────────────────────────


def osa(script: str, *args: str, timeout: float = 60.0) -> tuple[int | None, str, str]:
    """Run AppleScript with arguments passed as argv. Never raises.

    Arguments reach the script through `on run argv`, so nothing is interpolated
    into the source and any path character is safe.

    SIGKILL rather than the default SIGTERM: an `osascript` blocked on an
    unanswered Apple event ignores SIGTERM, so a plain timeout never lands.
    """
    try:
        proc = subprocess.run(
            ["osascript", "-e", script, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        subprocess.run(["pkill", "-9", "-x", "osascript"], capture_output=True)
        return None, "", "osascript timed out"
    except OSError as exc:  # osascript missing: not a macOS box
        return None, "", str(exc)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


_SET_ALERTS = """
on run argv
  tell application "Microsoft Word" to set displayAlerts to (item 1 of argv is "true")
end run
""".strip()

_COUNT_DOCS = 'tell application "Microsoft Word" to count of documents'

_CLOSE_ALL = 'tell application "Microsoft Word" to close every document saving no'

# Open, save as PDF, close. `document 1` rather than `active document`: the
# indexed form is what the audit found working from a script file, and it is
# never ambiguous (§5.2, §14.1).
_EXPORT_PDF = """
on run argv
  set inPath to item 1 of argv
  set outPath to item 2 of argv
  with timeout of 600 seconds
    tell application "Microsoft Word"
      open (POSIX file inPath) confirm conversions false add to recent files false
      set theDoc to document 1
      set paraCount to count of paragraphs of theDoc
      if paraCount is 0 then
        close every document saving no
        error "document loaded empty (Word could not read it)"
      end if
      save as theDoc file name outPath file format format PDF
      close every document saving no
    end tell
  end timeout
  return "ok"
end run
""".strip()


# ─── watchdogs ───────────────────────────────────────────────────────────────

_DUMP_BUTTONS = """
on run argv
  set procName to item 1 of argv
  set out to ""
  tell application "System Events"
    if not (exists process procName) then return ""
    tell process procName
      repeat with w in windows
        try
          repeat with b in buttons of w
            try
              set out to out & (name of b) & tab
            end try
          end repeat
        end try
        try
          repeat with sh in sheets of w
            repeat with b in buttons of sh
              try
                set out to out & (name of b) & tab
              end try
            end repeat
          end repeat
        end try
      end repeat
    end tell
  end tell
  return out
end run
""".strip()

# Activate the target process, press, then hand focus back to whoever had it.
# The Grant File Access panel will not render or accept an AXPress unless Word
# is the active app — the single reason two of the three audited grant handlers
# granted nothing and re-prompted on every file (§6.1). The caller's app is
# restored immediately, so net focus stays with the user.
_PRESS_ACTIVATED = """
on run argv
  set procName to item 1 of argv
  set wanted to items 2 thru -1 of argv
  set priorApp to ""
  tell application "System Events"
    try
      set priorApp to name of first process whose frontmost is true
    end try
    if not (exists process procName) then return ""
    tell process procName
      set frontmost to true
    end tell
    delay 0.4
    set pressed to ""
    tell process procName
      repeat with w in windows
        repeat with target in {w} & (sheets of w)
          repeat with nm in wanted
            try
              if pressed is "" and (exists button (nm as string) of target) then
                perform action "AXPress" of button (nm as string) of target
                set pressed to (nm as string)
              end if
            end try
          end repeat
        end repeat
      end repeat
    end tell
    if priorApp is not "" and priorApp is not procName then
      try
        set frontmost of (first process whose name is priorApp) to true
      end try
    end if
    return pressed
  end tell
end run
""".strip()

_PRESS = """
on run argv
  set procName to item 1 of argv
  set wanted to items 2 thru -1 of argv
  tell application "System Events"
    if not (exists process procName) then return ""
    tell process procName
      repeat with w in windows
        repeat with target in {w} & (sheets of w)
          repeat with nm in wanted
            try
              if exists button (nm as string) of target then
                perform action "AXPress" of button (nm as string) of target
                return (nm as string)
              end if
            end try
          end repeat
        end repeat
      end repeat
    end tell
  end tell
  return ""
end run
""".strip()


@dataclass
class Watchdogs:
    """Two pollers: Word's own modals, and Microsoft Error Reporting.

    MERP runs as its own process, so a handler aimed at Word cannot see it — the
    single reason no script in the audited corpus could dismiss it (§12.1).
    Every button label encountered is logged the first time, so the real control
    names are recorded from a live run instead of assumed.
    """

    poll: float = 1.5
    _stop: threading.Event = field(default_factory=threading.Event)
    _threads: list[threading.Thread] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    dismissed: int = 0
    granted: int = 0

    def _note_buttons(self, proc: str) -> None:
        _, out, _ = osa(_DUMP_BUTTONS, proc, timeout=8)
        for name in (n.strip() for n in out.split("\t")):
            if name and (key := f"{proc}:{name}") not in self.seen:
                self.seen.add(key)
                logger.info(f"[watchdog] {proc} shows button {name!r}")

    def _loop_word(self) -> None:
        while not self._stop.wait(self.poll):
            _, count, _ = osa(_DUMP_BUTTONS, WORD_PROC, timeout=8)
            if not count:
                continue
            self._note_buttons(WORD_PROC)
            # Accept a sandbox grant first. Never Cancel one: denying guarantees
            # a re-prompt on every later file (§14.3).
            # A grant must be pressed with Word frontmost or the panel never
            # renders to accept it (§6.1). Focus is handed straight back.
            _, pressed, _ = osa(_PRESS_ACTIVATED, WORD_PROC, *GRANT_BUTTONS, timeout=20)
            if pressed:
                self.granted += 1
                logger.warning(f"[watchdog] sandbox grant completed via {pressed!r}")
                continue
            # Everything else is an ordinary alert; no activation needed, and
            # Cancel here is safe because a grant would have matched above.
            _, pressed, _ = osa(_PRESS, WORD_PROC, *DISMISS_BUTTONS, timeout=10)
            if pressed:
                self.dismissed += 1
                logger.warning(f"[watchdog] Word dialog dismissed via {pressed!r}")

    def _loop_merp(self) -> None:
        while not self._stop.wait(self.poll):
            _, out, _ = osa(_DUMP_BUTTONS, MERP_PROC, timeout=8)
            if not out:
                continue
            self._note_buttons(MERP_PROC)
            _, pressed, _ = osa(_PRESS, MERP_PROC, *MERP_DECLINE, timeout=10)
            if pressed:
                self.dismissed += 1
                logger.warning(f"[watchdog] error report declined via {pressed!r}")
            else:
                logger.error(
                    f"[watchdog] {MERP_PROC} is showing a dialog whose buttons match "
                    f"none of {MERP_DECLINE}. Labels seen are logged above — add the "
                    "real one to MERP_DECLINE."
                )

    def start(self) -> None:
        for fn in (self._loop_word, self._loop_merp):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=3)

    def __enter__(self) -> Watchdogs:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()


# ─── Word lifecycle ──────────────────────────────────────────────────────────


@dataclass
class WordSession:
    """Owns Word's process lifecycle: warm, recycle, clean up after a kill."""

    warm_timeout: float = 90.0
    launched_by_us: bool = False
    restarts: int = 0

    @staticmethod
    def available() -> bool:
        return WORD_APP.exists() and shutil.which("osascript") is not None

    def responsive(self) -> bool:
        rc, out, _ = osa(_COUNT_DOCS, timeout=10)
        return rc == 0 and out.isdigit()

    def open_document_count(self) -> int:
        rc, out, _ = osa(_COUNT_DOCS, timeout=10)
        return int(out) if rc == 0 and out.isdigit() else -1

    def warm(self) -> bool:
        """Launch Word in the background and wait until it answers Apple events.

        `open -g` so the batch never takes the screen from whoever is using the
        machine, and the wait happens here so no per-document budget has to
        cover a ~30s cold start (§10).
        """
        if self.responsive():
            return True
        self.launched_by_us = True
        subprocess.run(["open", "-g", "-a", str(WORD_APP)], capture_output=True)
        deadline = time.monotonic() + self.warm_timeout
        while time.monotonic() < deadline:
            if self.responsive():
                osa(_SET_ALERTS, "false", timeout=10)
                return True
            time.sleep(2)
        return False

    def clean_after_kill(self, *folders: Path) -> None:
        """Remove what a killed Word leaves behind.

        AutoRecovery files make the next launch open the Document Recovery pane,
        which appears before any script command runs; lock files become work
        items for the next glob (§12).
        """
        if AUTORECOVERY.is_dir():
            for child in AUTORECOVERY.iterdir():
                with contextlib_suppress():
                    if child.is_dir():
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        child.unlink(missing_ok=True)
        for folder in folders:
            if folder and folder.is_dir():
                for lock in folder.glob("~$*"):
                    with contextlib_suppress():
                        lock.unlink(missing_ok=True)

    def recycle(self, *folders: Path) -> bool:
        """Graceful quit, then SIGTERM, then SIGKILL — then clean and re-warm.

        `pkill -x` matches the process NAME. `-f` matches whole command lines and
        would also kill helper `osascript`s and any unrelated process whose
        arguments mention Word (§14.5).
        """
        self.restarts += 1
        logger.warning(f"[word] recycling (restart {self.restarts})")
        osa('tell application "Microsoft Word" to quit saving no', timeout=15)
        time.sleep(2)
        if self._alive():
            subprocess.run(["pkill", "-x", WORD_PROC], capture_output=True)
            time.sleep(2)
        if self._alive():
            subprocess.run(["pkill", "-9", "-x", WORD_PROC], capture_output=True)
            time.sleep(1)
        self.clean_after_kill(*folders)
        return self.warm()

    @staticmethod
    def _alive() -> bool:
        return (
            subprocess.run(["pgrep", "-x", WORD_PROC], capture_output=True).returncode == 0
        )

    def quit_if_ours(self) -> None:
        if self.launched_by_us:
            osa(_CLOSE_ALL, timeout=15)
            osa('tell application "Microsoft Word" to quit saving no', timeout=15)


class contextlib_suppress:
    """Tiny suppress(): cleanup must never abort a run."""

    def __enter__(self) -> None:
        return None

    def __exit__(self, *exc: object) -> bool:
        return True


@dataclass
class Stage:
    """A fresh staging directory inside Word's own container.

    Inside the container Word needs no sandbox grant at all. Outside it, the
    Grant File Access sheet fires per file, because the grant does not carry to
    the next file in the same folder (§6.1). A unique directory per run avoids
    the intermittent file-access error other scripts hit when reusing one shared
    staging path (§5.3).
    """

    prefix: str = "wordrun"
    root: Path | None = None

    def __enter__(self) -> Stage:
        CONTAINER_TMP.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix=f"{self.prefix}.", dir=CONTAINER_TMP))
        (self.root / "in").mkdir()
        (self.root / "out").mkdir()
        return self

    def __exit__(self, *exc: object) -> None:
        if self.root:
            shutil.rmtree(self.root, ignore_errors=True)

    @property
    def inbox(self) -> Path:
        assert self.root
        return self.root / "in"

    @property
    def outbox(self) -> Path:
        assert self.root
        return self.root / "out"

    def place(self, src: Path) -> Path:
        """Copy a source in under its own name and return its staged path."""
        return self.place_as(src, src.name)

    def place_as(self, src: Path, name: str) -> Path:
        """Copy a source in under `name` and return its staged path.

        Redlines pair two documents that routinely share a filename (folder A's
        `deal.docx` against folder B's `deal.docx`), and one inbox cannot hold
        both under one name. The caller supplies the disambiguating name.
        """
        dst = self.inbox / name
        shutil.copy2(src, dst)
        return dst


# ─── conversion ──────────────────────────────────────────────────────────────


def export_pdf(
    staged_docx: Path, staged_pdf: Path, *, timeout: float = 180.0
) -> tuple[bool, str]:
    """Open one staged DOCX and save it as PDF. Returns (ok, error)."""
    rc, _, err = osa(_EXPORT_PDF, str(staged_docx), str(staged_pdf), timeout=timeout)
    produced = staged_pdf.exists() and staged_pdf.stat().st_size > 0
    if rc == 0 and produced:
        return True, ""
    return False, classify_failure(rc, err, produced)


def convert_folder(
    src: Path,
    out_dir: Path | None,
    *,
    force: bool = False,
    timeout: float = 180.0,
    session: WordSession | None = None,
    stage: Stage | None = None,
) -> list[Result]:
    """Export every real .docx in `src` to PDF. Serial, by necessity.

    Word is a single-instance, user-session-bound application; there is no
    equivalent of LibreOffice's `-env:UserInstallation`, so a second worker
    would drive the same instance. Parallelism here needs separate macOS user
    sessions or VMs (§9). The signature therefore takes no `jobs`.
    """
    docs = iter_docx(src)
    if not docs:
        logger.warning(f"no .docx in {src} (lock files excluded)")
        return []

    owns_session = session is None
    owns_stage = stage is None
    session = session or WordSession()
    results: list[Result] = []

    if owns_session and not session.warm():
        return [Result(source=d, error="Word did not become responsive") for d in docs]

    ctx = Stage(prefix="wordpdf") if owns_stage else None
    stage = stage or (ctx.__enter__() if ctx else None)
    assert stage is not None
    try:
        for i, docx in enumerate(docs, 1):
            final_pdf = pdf_path_for(docx, out_dir)
            if final_pdf.exists() and final_pdf.stat().st_size > 0 and not force:
                results.append(Result(source=docx, output=final_pdf, ok=True, skipped=True))
                logger.debug(f"[{i}/{len(docs)}] skip (exists): {docx.name}")
                continue

            started = time.monotonic()
            staged_in = stage.place(docx)
            staged_out = stage.outbox / final_pdf.name
            ok, err = export_pdf(staged_in, staged_out, timeout=timeout)
            elapsed = time.monotonic() - started

            if ok:
                final_pdf.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staged_out), final_pdf)
                results.append(
                    Result(source=docx, output=final_pdf, ok=True, seconds=elapsed)
                )
                logger.info(f"[{i}/{len(docs)}] ok ({elapsed:.1f}s): {docx.name}")
            else:
                results.append(Result(source=docx, error=err, seconds=elapsed))
                logger.error(f"[{i}/{len(docs)}] FAIL: {docx.name} — {err}")
                # One bad document leaves Word returning empty documents for
                # every later open, silently. Recycle rather than carry on
                # (§5/§6: one poison file cost 203 others in the old corpus).
                session.recycle(stage.inbox, stage.outbox, src)

            staged_in.unlink(missing_ok=True)
    finally:
        if ctx:
            ctx.__exit__(None, None, None)
        if owns_session:
            session.quit_if_ours()
    return results


# ─── reporting ───────────────────────────────────────────────────────────────


def report(results: list[Result], title: str = "Word export") -> int:
    ok = [r for r in results if r.ok and not r.skipped]
    skipped = [r for r in results if r.skipped]
    failed = [r for r in results if not r.ok]
    table = Table(title=title, show_lines=False)
    table.add_column("outcome")
    table.add_column("count", justify="right")
    table.add_row("converted", str(len(ok)))
    table.add_row("skipped (exists)", str(len(skipped)))
    table.add_row("failed", str(len(failed)), style="red" if failed else None)
    if ok:
        table.add_row("median seconds", f"{sorted(r.seconds for r in ok)[len(ok) // 2]:.1f}")
    console.print(table)
    for r in failed:
        console.print(f"  [red]FAIL[/] {r.source.name}: {r.error}")
    return 1 if failed else 0


PRESET_REMINDER = (
    "PDF quality is sticky: `save as … file format format PDF` inherits whatever "
    "'Optimize for' you last chose in Word's own Save As dialog.\n"
    "  Open any document in Word once, File > Save As > PDF, and pick the SECOND "
    "option, [bold]Best for printing[/].\n"
    "  That choice persists; this script cannot set it. Pass --no-check-preset to "
    "stop seeing this."
)


def preset_notice() -> None:
    console.print(f"[yellow]▸[/] {PRESET_REMINDER}")


def preflight(session: WordSession, *, allow_open_docs: bool) -> str:
    """Refuse to start on a machine that is not ready. Returns '' when ready."""
    if not WordSession.available():
        return "needs macOS with Microsoft Word installed"
    if not session.warm():
        return "Word did not become responsive"
    count = session.open_document_count()
    if count > 0 and not allow_open_docs:
        return (
            f"Word has {count} document(s) open and this batch closes documents "
            "without saving. Close them, or pass --allow-open-docs."
        )
    return ""


# ─── CLI ─────────────────────────────────────────────────────────────────────

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
    src: Path = typer.Option(..., "--src", "-s", help="Folder of .docx to export."),
    out: Path | None = typer.Option(
        None, "--out", "-o", help="Where PDFs go. Default: beside each .docx."
    ),
    force: bool = typer.Option(False, "--force", help="Re-export even if the PDF exists."),
    timeout: float = typer.Option(180.0, "--timeout", help="Seconds per document."),
    check_preset: bool = typer.Option(
        True, "--check-preset/--no-check-preset", help="Print the PDF-preset reminder."
    ),
    allow_open_docs: bool = typer.Option(
        False, "--allow-open-docs", help="Run even if Word already has documents open."
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Errors and summary only."),
    log_file: Path | None = typer.Option(None, "--log", help="Also write a log file."),
) -> None:
    """Export every .docx in a folder to PDF using Microsoft Word."""
    logger.remove()
    logger.add(lambda m: console.print(m, end=""), level="ERROR" if quiet else "INFO")
    if log_file:
        logger.add(str(log_file), level="DEBUG", rotation="10 MB")

    if not src.is_dir():
        console.print(f"[red]not a folder:[/] {src}")
        raise typer.Exit(2)
    if check_preset:
        preset_notice()

    session = WordSession()
    if problem := preflight(session, allow_open_docs=allow_open_docs):
        console.print(f"[red]{problem}[/]")
        raise typer.Exit(2)

    with Watchdogs():
        results = convert_folder(src, out, force=force, timeout=timeout, session=session)
        session.quit_if_ours()
    raise typer.Exit(report(results, f"DOCX → PDF: {src}"))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    app()
