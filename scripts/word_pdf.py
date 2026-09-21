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
- **The document acted on is the one that was named, never `active document`.**
  A script should name the document it means, or find it by exclusion, rather
  than take whichever one Word happens to have in front (§5.18). Used by
  `word_redline.py`, where `compare` returns its result as a new document;
  kept here because the rule is the same for any save.
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
- **Word is pre-warmed, and an already-running Word is left exactly as found.**
  A cold start is ~30s, and budgets that cover launch *and* work are wrong in
  both directions at once (§10). But warming never restarts a Word that is
  already up: it returns the running instance untouched and does not claim
  ownership of it, so the batch cannot quit someone else's session on the way
  out. That matters beyond tidiness — the two sticky settings below live in
  that instance, and losing them mid-batch would change every later PDF
  without anything failing.

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
from typing import Annotated, Self

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

# Word's "repair this document?" prompt, matched on WINDOW TEXT rather than on a
# button name. The answer has to be "No": "Yes" makes Word rewrite the document
# and we would then be measuring Word's repair, not the file we were handed.
# Matching on text is what makes the No specific — a blind press of "No" from the
# generic list could land on an unrelated alert. Strings and the fallback to
# Escape are word-convert.sh's (decline_unreadable_dialog), which is the one
# handler in the audited corpus that gets this right.
REPAIR_MARKERS = (
    "Word found unreadable content",
    "Do you want to recover the contents of this document",
)


# ─── pure helpers (no Word, no macOS — unit-testable anywhere) ────────────────


def is_word_temp(name: str) -> bool:
    """Word owner/lock files look like documents and are not documents.

    They are created beside any open document and left behind by a killed Word.
    """
    return name.startswith(("~$", ".~"))


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
    timing_exact: bool = True
    """False when `seconds` is a per-item average from a batch pass, not a
    measurement of this document. The summary labels the row accordingly."""


# ─── osascript ───────────────────────────────────────────────────────────────


def osa(script: str, *args: str, timeout: float = 60.0) -> tuple[int | None, str, str]:
    """Run AppleScript with arguments passed as argv. Never raises.

    Arguments reach the script through `on run argv`, so nothing is interpolated
    into the source and any path character is safe.

    On timeout the child is SIGKILLed, which is what a blocked `osascript`
    needs — held on an unanswered Apple event it ignores SIGTERM. That is
    `subprocess.run`'s own behaviour: it calls `Popen.kill()`, not `terminate()`.
    The distinction matters against shell `timeout(1)`, which sends SIGTERM
    unless given `-k`, and it is why nothing here reaches for `pkill`.

    Never `pkill osascript`. It would match every `osascript` on the machine:
    this module's OWN watchdog threads (each poll is an `osascript`), any other
    automation running in the user's session, and anything they are running by
    hand. `subprocess.run` already kills exactly the child it started.
    """
    try:
        proc = subprocess.run(
            ["osascript", "-e", script, *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
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

# Closing *ours* rather than everything. Only correct when we know the name, and
# only needed when Word is not ours alone (`--allow-open-docs`): there, `close
# every document saving no` would discard a human's unsaved work to clean up
# after our own bad file.
_CLOSE_NAMED = """
on run argv
  tell application "Microsoft Word"
    repeat with i from (count documents) to 1 by -1
      if name of document i is (item 1 of argv) then close document i saving no
    end repeat
  end tell
end run
""".strip()

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
        close theDoc saving no
        error "document loaded empty (Word could not read it)"
      end if
      save as theDoc file name outPath file format format PDF
      close theDoc saving no
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


# Walk a window's text, press "No" if it is the repair prompt, Escape if the
# button is not reachable. `-1` as the marker count means "no repair dialog
# found", which the watchdog uses to fall through to the generic handlers.
_DECLINE_REPAIR = """
on textOf(el)
  set acc to ""
  try
    set acc to acc & (name of el as string) & " "
  end try
  try
    set acc to acc & (value of el as string) & " "
  end try
  try
    set acc to acc & (title of el as string) & " "
  end try
  try
    repeat with child in UI elements of el
      set acc to acc & my textOf(child)
    end repeat
  end try
  return acc
end textOf

on pressNamed(el, nm)
  try
    perform action "AXPress" of button nm of el
    return true
  end try
  try
    repeat with child in UI elements of el
      if my pressNamed(child, nm) then return true
    end repeat
  end try
  return false
end pressNamed

on run argv
  set markers to items 1 thru -1 of argv
  tell application "System Events"
    if not (exists process "Microsoft Word") then return ""
    tell process "Microsoft Word"
      repeat with w in windows
        set wText to my textOf(w)
        repeat with m in markers
          if wText contains (m as string) then
            if my pressNamed(w, "No") then return "No"
            key code 53
            return "escape"
          end if
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
    declined: int = 0

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
            # The repair prompt first, and answered "No". It is matched on window
            # text, so this cannot fire on an unrelated alert — and it has to run
            # before the generic handlers, which would otherwise press "OK" on it.
            _, pressed, _ = osa(_DECLINE_REPAIR, *REPAIR_MARKERS, timeout=15)
            if pressed:
                self.declined += 1
                logger.warning(f"[watchdog] repair prompt declined via {pressed!r}")
                continue
            # Accept a sandbox grant next. Never Cancel one: denying guarantees
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

    def __enter__(self) -> Self:
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
    started: float = field(default_factory=time.time)
    """Wall clock, because it is compared against file mtimes. Everything
    older than this belongs to someone else and is never deleted."""
    started_clean: bool = True
    """True only once `preflight` has seen Word holding **zero** documents.

    This is what makes the mtime cutoff in `clean_after_kill` mean anything. With
    no document open when we start, every AutoRecovery entry written afterwards
    is ours. Under `--allow-open-docs` that premise is gone and the cutoff stops
    protecting anyone: Word's AutoRecover interval defaults to 10 minutes, so a
    human's open document has its recovery copy rewritten *during* a longer run,
    with an mtime past ours, and "newer than the run" would sweep it up. So the
    precondition is the control, not the timestamp.
    """

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
        subprocess.run(["open", "-g", "-a", str(WORD_APP)], capture_output=True, check=False)
        deadline = time.monotonic() + self.warm_timeout
        while time.monotonic() < deadline:
            if self.responsive():
                osa(_SET_ALERTS, "false", timeout=10)
                return True
            time.sleep(2)
        return False

    def clean_after_kill(self, *folders: Path) -> None:
        """Remove what a killed Word left behind **in this run**, and nothing else.

        AutoRecovery files make the next launch open the Document Recovery pane,
        which appears before any script command runs; lock files become work
        items for the next glob (§12).

        The cutoff is not decoration. That directory is the user's, not this
        run's: it holds the recovery copies for every document Word has open,
        including a human's unsaved work. Deleting all of it to clear our own
        residue would destroy theirs — so only entries modified at or after this
        session started are removed, and a pre-existing file is left alone even
        when it would be convenient to drop it. The same cutoff applies to `~$`
        lock files, on top of the folders already being ours.

        "Ours" is literal: only folders this run created are ever passed in. Word
        never opens anything from `--src`, because `Stage.place` copies each
        document into the container inbox and Word opens the copy. So a `~$` file
        in the user's own folder is some other Word's, and the cutoff would not
        save it if that person opened their document while we were running.
        `iter_docx()` already keeps `~$*` out of the work list, so sweeping their
        folder buys nothing and can only break a stranger's lock.

        A file Word wrote *before* we started is by definition not ours. That
        alone is not enough, which is why `started_clean` gates this: see its
        docstring for the autosave-during-the-run case the timestamp cannot
        catch. When we did not start clean, AutoRecovery is left entirely alone
        and the Document Recovery pane is the price. Lock files in the folders
        we staged are still ours.
        """
        if self.started_clean:
            entries = _entries_since(AUTORECOVERY, self.started)
        else:
            entries = []
            logger.warning(
                "[word] Word held documents at startup; leaving AutoRecovery "
                "untouched. Expect the Document Recovery pane on relaunch."
            )
        for child in entries:
            with contextlib_suppress():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
        for folder in folders:
            for lock in _entries_since(folder, self.started, pattern="~$*"):
                with contextlib_suppress():
                    lock.unlink(missing_ok=True)

    def recycle(self, *folders: Path) -> bool:
        """Graceful quit, then SIGTERM, then SIGKILL — then clean and re-warm.

        `pkill -x` matches the process NAME. `-f` matches whole command lines and
        would also kill helper `osascript`s and any unrelated process whose
        arguments mention Word (§14.5).
        """
        if not self.started_clean:
            # `recycle` quits Word `saving no`. With a human's documents open
            # that discards their work, which no failure of ours justifies.
            logger.error(
                "[word] refusing to restart Word: it held documents at startup "
                "(--allow-open-docs), and a restart would discard them unsaved. "
                "Close them and re-run without the flag to enable recovery."
            )
            return False

        if not self.launched_by_us:
            # Starting clean only means no documents were open. Word itself may
            # have been running, and a restart takes its sticky settings with
            # it. Recovery is still worth more than the risk, so this warns
            # rather than refusing — but it must not be silent.
            logger.warning(
                "[word] restarting a Word this run did not launch. If you set "
                '"Optimize for: Best for printing" by hand, re-check it before '
                "trusting the PDFs rendered after this point."
            )
        self.restarts += 1
        logger.warning(f"[word] recycling (restart {self.restarts})")
        osa('tell application "Microsoft Word" to quit saving no', timeout=15)
        time.sleep(2)
        if self._alive():
            subprocess.run(["pkill", "-x", WORD_PROC], capture_output=True, check=False)
            time.sleep(2)
        if self._alive():
            subprocess.run(["pkill", "-9", "-x", WORD_PROC], capture_output=True, check=False)
            time.sleep(1)
        self.clean_after_kill(*folders)
        return self.warm()

    @staticmethod
    def _alive() -> bool:
        proc = subprocess.run(
            ["pgrep", "-x", WORD_PROC], capture_output=True, check=False
        )
        return proc.returncode == 0

    def quit_if_ours(self) -> None:
        if self.launched_by_us:
            osa(_CLOSE_ALL, timeout=15)
            osa('tell application "Microsoft Word" to quit saving no', timeout=15)


def _entries_since(folder: Path, cutoff: float, *, pattern: str = "*") -> list[Path]:
    """Direct children of `folder` last modified at or after `cutoff`.

    Anything older predates this run and is left alone. Unreadable entries are
    skipped rather than guessed at: cleanup must never delete on a stat failure.
    """
    if not folder or not folder.is_dir():
        return []
    found: list[Path] = []
    for child in folder.glob(pattern):
        try:
            if child.stat().st_mtime >= cutoff:
                found.append(child)
        except OSError:
            continue
    return found


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

    def __enter__(self) -> Self:
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


# ─── malformed documents ─────────────────────────────────────────────────────


def recover_after_failure(
    session: WordSession, *folders: Path, only: str | None = None
) -> bool:
    """Answer the repair prompt "No", close whatever is open, and keep going.

    This is the cheap path, and it is the one that should run almost always: a
    malformed document costs one failed open, not a ~30s Word restart. Only if
    Word does not come back clean — still answering, with no document left open —
    does it escalate to a full recycle.

    The escalation is not optional. The audit found that after a bad document
    Word keeps answering Apple events while returning EMPTY documents for every
    later open, with no error at all (§5, §6): one poison file cost 203 others.
    The paragraph-count check on every open is what catches that, and a Word that
    cannot be brought back to zero open documents is assumed to be in it.
    """
    osa(_DECLINE_REPAIR, *REPAIR_MARKERS, timeout=15)
    if session.started_clean:
        # Every open document is ours, so closing all of them is exactly right.
        osa(_CLOSE_ALL, timeout=20)
        if session.open_document_count() == 0:
            return True
    elif only:
        # Word is not ours alone. Close the one document we opened and leave the
        # rest of the session standing: the operator asked us to coexist with
        # their documents, not to discard them to tidy up after our own file.
        osa(_CLOSE_NAMED, only, timeout=20)
        return True
    else:
        logger.warning("[word] Word was not ours at startup and no document name was given; leaving it alone")
        return True
    logger.warning("[word] did not come back clean after a failure; recycling")
    return session.recycle(*folders)


# ─── one-osascript batch mode ────────────────────────────────────────────────


def safe_stage_name(index: int, name: str) -> str:
    """A staged filename that cannot break a tab-separated manifest.

    Manifest rows are TSV, so a tab, CR or newline in a source filename would
    split one row into two and silently misalign every field after it. The index
    prefix also makes the name unique, so two folders' same-named documents can
    share one inbox.
    """
    cleaned = "".join("_" if ch in "\t\r\n" else ch for ch in name)
    return f"{index:05d}__{cleaned}"


def write_manifest(rows: list[tuple[str, ...]], path: Path) -> Path:
    """Write TSV rows for a batch script to read. Returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join("\t".join(r) + "\n" for r in rows), encoding="utf-8")
    return path


@dataclass(slots=True)
class BatchLog:
    """What a batch script recorded: per-item outcome, and whether it finished."""

    results: dict[str, tuple[bool, str]] = field(default_factory=dict)
    done: bool = False


def parse_batch_log(text: str) -> BatchLog:
    """Read a batch script's append-only log.

    Only `[ok]`, `[fail]` and `[done]` lines are read; anything else is ignored,
    which is what makes an error message containing a newline harmless. An item
    with no line at all was never reached — the run died before it — and that is
    the difference between "failed" and "retry in the next pass".
    """
    log = BatchLog()
    for line in text.splitlines():
        fields = line.split("\t")
        head = fields[0]
        if head == "[ok]" and len(fields) >= 2:
            log.results[fields[1]] = (True, "\t".join(fields[2:]).strip())
        elif head == "[fail]" and len(fields) >= 2:
            detail = "\t".join(fields[2:]).strip()
            log.results[fields[1]] = (False, detail or "unspecified error")
        elif head == "[done]":
            log.done = True
    return log


@dataclass(slots=True)
class BatchRun:
    """One invocation of a monolithic batch script."""

    log: BatchLog
    returncode: int | None
    stderr: str = ""

    @property
    def wedged(self) -> bool:
        """True when the script did not reach its own `[done]` line."""
        return not self.log.done


@dataclass
class _Progress:
    """Tail a batch log so a long monolithic run is not silent.

    A batch script is one blocking `osascript`, so its own `logLine` calls are
    the only signal available while it runs.
    """

    log_path: Path
    total: int
    label: str = ""
    poll: float = 5.0
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def _loop(self) -> None:
        seen = -1
        while not self._stop.wait(self.poll):
            try:
                text = self.log_path.read_text(errors="replace")
            except OSError:
                continue
            count = sum(1 for ln in text.splitlines() if ln.startswith(("[ok]", "[fail]")))
            if count != seen:
                seen = count
                logger.info(f"[batch{self.label}] {count}/{self.total}")

    def __enter__(self) -> Self:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)


def batch_timeout(per_item: float, count: int, *, floor: float = 120.0) -> float:
    """Whole-batch budget. A per-item budget cannot bound a monolithic run.

    `floor` is headroom on top of the per-item budget — Word's warm-up, the final
    close, the manifest read — and it is also what an empty batch gets. A
    negative `per_item` is clamped rather than shortening the budget.
    """
    return floor + max(0.0, per_item) * count


def run_batch(
    script: str,
    rows: list[tuple[str, ...]],
    work_dir: Path,
    *,
    timeout: float,
    label: str = "",
) -> BatchRun:
    """Run one monolithic AppleScript over a manifest of work items.

    Nothing is interpolated into the script: it receives two argv paths, the
    manifest and its log, and reads the rest itself. That also sidesteps
    `ARG_MAX` — a thousand pairs of absolute paths on argv is tens of thousands
    of characters, and this passes two.
    """
    manifest = write_manifest(rows, work_dir / "manifest.tsv")
    log_path = work_dir / "batch.log"
    log_path.write_text("", encoding="utf-8")
    with _Progress(log_path, len(rows), label):
        rc, _, err = osa(script, str(manifest), str(log_path), timeout=timeout)
    try:
        text = log_path.read_text(errors="replace")
    except OSError:
        text = ""
    return BatchRun(log=parse_batch_log(text), returncode=rc, stderr=err)


def run_batch_with_resume(
    script: str,
    rows: list[tuple[str, ...]],
    work_dir: Path,
    *,
    per_item_timeout: float,
    session: WordSession,
    recycle_paths: tuple[Path, ...] = (),
    max_passes: int = 3,
    label: str = "",
) -> dict[str, tuple[bool, str]]:
    """Run a batch script, retrying only the items it never reached.

    Three outcomes per item, and they are not interchangeable:

    - `[ok]` / `[fail]` — the script reached it and said so. Final either way; a
      malformed document is not retried, because it will be malformed next pass
      too.
    - **no line at all** — the run died before getting there. That is the only
      case worth another pass, and it gets one after Word is recycled.

    Items already recorded are dropped from the next manifest, so a wedge costs
    the remainder of one pass rather than the whole batch.
    """
    final: dict[str, tuple[bool, str]] = {}
    pending = list(rows)
    for attempt in range(1, max_passes + 1):
        if not pending:
            break
        run = run_batch(
            script,
            pending,
            work_dir,
            timeout=batch_timeout(per_item_timeout, len(pending)),
            label=f"{label} {attempt}",
        )
        still: list[tuple[str, ...]] = []
        for row in pending:
            recorded = run.log.results.get(row[0])
            if recorded is None:
                still.append(row)
            else:
                final[row[0]] = recorded
        pending = still
        if pending:
            why = "wedged before [done]" if run.wedged else "ended without reaching them"
            logger.warning(
                f"[batch{label}] {len(pending)} item(s) never reached ({why}); "
                f"recycling Word and retrying (pass {attempt + 1} of {max_passes})"
            )
            session.recycle(*recycle_paths)
    for row in pending:
        final[row[0]] = (False, f"never reached in {max_passes} batch pass(es)")
    return final


# One osascript for the whole folder. The per-document
# `try … on error … close theDoc saving no … end try` IS the malformed-document
# contract: answer nothing, close the document we opened, record it, move to the
# next file. It closes `theDoc` and never `every document`, because a document
# this script did not open is someone else's unsaved work. `preflight` refuses
# `--one-osascript` while Word holds documents, which is the real guarantee;
# this is what keeps the script safe when `convert_folder` is called directly.
# The repair prompt itself is answered concurrently by the watchdog, which runs
# in its own process and can act while this script is blocked on `open`.
_EXPORT_BATCH = r"""
on splitTabs(t)
  set od to AppleScript's text item delimiters
  set AppleScript's text item delimiters to tab
  set parts to text items of t
  set AppleScript's text item delimiters to od
  return parts
end splitTabs

on logLine(logPath, msg)
  do shell script "printf '%s\\n' " & quoted form of msg & " >> " & quoted form of logPath
end logLine

on run argv
  set manifestPath to item 1 of argv
  set logPath to item 2 of argv
  set rows to paragraphs of (read POSIX file manifestPath)
  tell application "Microsoft Word"
    set displayAlerts to false
  end tell
  set okCount to 0
  set failCount to 0
  repeat with r in rows
    set rowText to r as string
    if rowText is not "" then
      set f to my splitTabs(rowText)
      if (count of f) is 3 then
        set itemId to item 1 of f
        set inP to item 2 of f
        set outP to item 3 of f
        set theDoc to missing value
        try
          with timeout of 600 seconds
            tell application "Microsoft Word"
              open POSIX file inP
              set theDoc to document 1
              if (count of paragraphs of theDoc) is 0 then
                close theDoc saving no
                set theDoc to missing value
                error "document loaded empty (Word could not read it)"
              end if
              save as theDoc file name outP file format format PDF
              close theDoc saving no
              set theDoc to missing value
            end tell
          end timeout
          set okCount to okCount + 1
          my logLine(logPath, "[ok]" & tab & itemId)
        on error errMsg
          set failCount to failCount + 1
          try
            if theDoc is not missing value then
              tell application "Microsoft Word" to close theDoc saving no
            end if
          end try
          my logLine(logPath, "[fail]" & tab & itemId & tab & errMsg)
        end try
      end if
    end if
  end repeat
  my logLine(logPath, "[done]" & tab & okCount & tab & failCount)
  return "ok=" & okCount & " fail=" & failCount
end run
""".strip()


def convert_folder(
    src: Path,
    out_dir: Path | None,
    *,
    force: bool = False,
    timeout: float = 180.0,
    session: WordSession | None = None,
    stage: Stage | None = None,
    one_osascript: bool = True,
    max_passes: int = 3,
    poison_streak: int = 3,
) -> list[Result]:
    """Export every real .docx in `src` to PDF. Serial, by necessity.

    Word is a single-instance, user-session-bound application; there is no
    equivalent of LibreOffice's `-env:UserInstallation`, so a second worker
    would drive the same instance. Parallelism here needs separate macOS user
    sessions or VMs (§9). The signature therefore takes no `jobs`.

    `one_osascript` (the default) runs the whole folder inside a single
    monolithic AppleScript instead of one `osascript` per document. The per-file
    process spawn and Apple-event connection it saves are modest; what it gives
    up is the ability to act between documents. That ability is worth less than
    it looks, because the batch writes an `[ok]` / `[fail]` line per item as it
    goes and resumes from that log when a run wedges — so the folder-sized batch
    is the normal shape, and `one_osascript=False` is the opt-out for when you
    genuinely need a process boundary around every document.
    """
    docs = iter_docx(src)
    if not docs:
        logger.warning(f"no .docx in {src} (lock files excluded)")
        return []

    owns_session = session is None
    owns_stage = stage is None
    session = session or WordSession()

    if owns_session and not session.warm():
        return [Result(source=d, error="Word did not become responsive") for d in docs]

    ctx = Stage(prefix="wordpdf") if owns_stage else None
    stage = stage or (ctx.__enter__() if ctx else None)
    assert stage is not None
    try:
        run = _convert_batched if one_osascript else _convert_serial
        return run(
            docs,
            out_dir,
            src,
            stage=stage,
            session=session,
            force=force,
            timeout=timeout,
            max_passes=max_passes,
            poison_streak=poison_streak,
        )
    finally:
        if ctx:
            ctx.__exit__(None, None, None)
        if owns_session:
            session.quit_if_ours()


def _convert_serial(
    docs: list[Path],
    out_dir: Path | None,
    src: Path,
    *,
    stage: Stage,
    session: WordSession,
    force: bool,
    timeout: float,
    max_passes: int = 3,
    poison_streak: int = 3,
) -> list[Result]:
    """One `osascript` per document, with the malformed-document path in Python."""
    results: list[Result] = []
    streak: list[Path] = []
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
            streak.clear()
            final_pdf.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staged_out), final_pdf)
            results.append(Result(source=docx, output=final_pdf, ok=True, seconds=elapsed))
            logger.info(f"[{i}/{len(docs)}] ok ({elapsed:.1f}s): {docx.name}")
        else:
            streak.append(docx)
            results.append(Result(source=docx, error=err, seconds=elapsed))
            logger.error(f"[{i}/{len(docs)}] FAIL: {docx.name} — {err}")
            staged_out.unlink(missing_ok=True)
            # Decline the repair prompt, close whatever is open, move on. A
            # restart costs ~30s and is not what a malformed document needs.
            recover_after_failure(session, stage.inbox, stage.outbox, only=staged_in.name)
            if len(streak) >= poison_streak:
                # Unless they keep failing. A Word degraded by a bad document
                # answers normally and returns empty documents for everything
                # after it (§5, §6), which is what a failure run looks like.
                logger.warning(
                    f"[word] {len(streak)} failures in a row — recycling rather than "
                    "trusting Word to still be reading documents"
                )
                if session.recycle(stage.inbox, stage.outbox):
                    _replay(streak, results, out_dir=out_dir, stage=stage, timeout=timeout)
                streak.clear()

        staged_in.unlink(missing_ok=True)
    return results


def _replay(
    docs: list[Path],
    results: list[Result],
    *,
    out_dir: Path | None,
    stage: Stage,
    timeout: float,
) -> None:
    """Re-run a failure streak against a freshly restarted Word, in place.

    The streak is why we restarted: a Word degraded by one bad document answers
    normally and returns empty documents for everything after it (§5, §6). The
    paragraph-count check turns those into failures rather than false passes,
    which is the half that matters — but they are failures of *Word*, and
    nothing in a `[fail]` distinguishes them from a genuinely malformed file.
    Leaving them would report healthy documents as permanently broken.

    So the streak gets one attempt against the fresh Word. Whatever fails again
    is the file's own fault and keeps its original verdict.
    """
    for docx in docs:
        final_pdf = pdf_path_for(docx, out_dir)
        staged_in = stage.place(docx)
        staged_out = stage.outbox / final_pdf.name
        started = time.monotonic()
        ok, err = export_pdf(staged_in, staged_out, timeout=timeout)
        elapsed = time.monotonic() - started
        staged_in.unlink(missing_ok=True)
        if not ok:
            staged_out.unlink(missing_ok=True)
            logger.info(f"[replay] still failing, so it is the file: {docx.name} — {err}")
            continue
        final_pdf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_out), final_pdf)
        logger.info(f"[replay] ok after restart ({elapsed:.1f}s): {docx.name}")
        for n, prior in enumerate(results):
            if prior.source == docx and not prior.ok:
                results[n] = Result(source=docx, output=final_pdf, ok=True, seconds=elapsed)
                break


def _convert_batched(
    docs: list[Path],
    out_dir: Path | None,
    src: Path,
    *,
    stage: Stage,
    session: WordSession,
    force: bool,
    timeout: float,
    max_passes: int = 3,
    poison_streak: int = 3,
) -> list[Result]:
    """One monolithic AppleScript for the whole folder, resumed if it dies.

    Every input is staged before the run starts, because the manifest references
    all of them at once — that is inherent to a single-script batch, and it is
    the mode's real cost: N copies live in the container until the run ends.
    """
    outcomes: dict[Path, Result] = {}
    todo: list[Path] = []
    for doc in docs:
        final = pdf_path_for(doc, out_dir)
        if final.exists() and final.stat().st_size > 0 and not force:
            outcomes[doc] = Result(source=doc, output=final, ok=True, skipped=True)
        else:
            todo.append(doc)
    if not todo:
        return [outcomes[doc] for doc in docs]

    rows: list[tuple[str, ...]] = []
    staged: dict[str, tuple[Path, Path, Path]] = {}
    for i, doc in enumerate(todo):
        item = str(i)
        staged_in = stage.place_as(doc, safe_stage_name(i, doc.name))
        staged_out = stage.outbox / f"{safe_stage_name(i, doc.stem)}.pdf"
        rows.append((item, str(staged_in), str(staged_out)))
        staged[item] = (doc, staged_in, staged_out)

    logger.info(f"[batch] one osascript for {len(rows)} document(s)")
    started = time.monotonic()
    recorded = run_batch_with_resume(
        _EXPORT_BATCH,
        rows,
        stage.root or stage.inbox.parent,
        per_item_timeout=timeout,
        session=session,
        recycle_paths=(stage.inbox, stage.outbox),
        max_passes=max_passes,
        label=" pdf",
    )
    per_item = (time.monotonic() - started) / max(1, len(rows))

    for item, (doc, staged_in, staged_out) in staged.items():
        staged_in.unlink(missing_ok=True)
        ok, detail = recorded[item]
        produced = staged_out.exists() and staged_out.stat().st_size > 0
        if ok and produced:
            final = pdf_path_for(doc, out_dir)
            final.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staged_out), final)
            outcomes[doc] = Result(
                source=doc, output=final, ok=True, seconds=per_item, timing_exact=False
            )
        else:
            outcomes[doc] = Result(
                source=doc,
                error=classify_failure(0 if ok else 1, detail, produced),
                seconds=per_item,
                timing_exact=False,
            )
            staged_out.unlink(missing_ok=True)
            logger.error(f"[batch] FAIL: {doc.name} — {outcomes[doc].error}")

    return [outcomes[doc] for doc in docs]


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
        seconds = sorted(r.seconds for r in ok)
        if all(r.timing_exact for r in ok):
            table.add_row("median seconds", f"{seconds[len(ok) // 2]:.1f}")
        else:
            # A batch pass times the whole run, not each document in it.
            table.add_row("seconds per document (batch avg)", f"{seconds[len(ok) // 2]:.1f}")
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


def preflight(
    session: WordSession, *, allow_open_docs: bool, one_osascript: bool = False
) -> str:
    """Refuse to start on a machine that is not ready. Returns '' when ready.

    `--allow-open-docs` is a trade the operator is entitled to make for the
    serial path: it costs them Word restarts, and the export binds the document
    it opened and closes only that one. `--one-osascript` cannot offer the same
    deal. It sets `displayAlerts` to false for the whole run and has no way to
    act between documents, so it is refused while Word holds anything, the way
    `word_redline.py` refuses the flag outright.
    """
    if not WordSession.available():
        return "needs macOS with Microsoft Word installed"
    if not session.warm():
        return "Word did not become responsive"
    count = session.open_document_count()
    session.started_clean = count == 0
    if count > 0 and one_osascript:
        return (
            f"Word has {count} document(s) open, and the default monolithic run "
            "suppresses Word's alerts for the whole run and cannot act between "
            "documents. --allow-open-docs does not waive this. Close them, or "
            "pass --no-one-osascript to export one document per osascript."
        )
    if count > 0 and not allow_open_docs:
        return (
            f"Word has {count} document(s) open and this batch closes documents "
            "without saving. Close them, or pass --allow-open-docs — which keeps "
            "your documents open, but disables Word restarts, so a wedged Word "
            "ends the run instead of being recovered."
        )
    return ""


# ─── CLI ─────────────────────────────────────────────────────────────────────

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
    src: Annotated[Path, typer.Option("--src", "-s", help="Folder of .docx to export.")],
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Where PDFs go. Default: beside each .docx."),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Re-export even if the PDF exists.")
    ] = False,
    timeout: Annotated[
        float, typer.Option("--timeout", help="Seconds per document.")
    ] = 180.0,
    one_osascript: Annotated[
        bool,
        typer.Option(
            "--one-osascript/--no-one-osascript",
            help="Run the whole folder in ONE monolithic AppleScript (default) "
            "instead of one osascript per document. Resumes automatically if the "
            "run wedges. --no-one-osascript pays a process per document to gain a "
            "boundary between them.",
        ),
    ] = True,
    check_preset: Annotated[
        bool,
        typer.Option(
            "--check-preset/--no-check-preset", help="Print the PDF-preset reminder."
        ),
    ] = True,
    allow_open_docs: Annotated[
        bool,
        typer.Option("--allow-open-docs", help="Run even if Word already has documents open."),
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Errors and summary only.")
    ] = False,
    log_file: Annotated[
        Path | None, typer.Option("--log", help="Also write a log file.")
    ] = None,
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
    if problem := preflight(
        session, allow_open_docs=allow_open_docs, one_osascript=one_osascript
    ):
        console.print(f"[red]{problem}[/]")
        raise typer.Exit(2)

    with Watchdogs():
        results = convert_folder(
            src,
            out,
            force=force,
            timeout=timeout,
            session=session,
            one_osascript=one_osascript,
        )
        session.quit_if_ours()
    raise typer.Exit(report(results, f"DOCX → PDF: {src}"))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    app()
