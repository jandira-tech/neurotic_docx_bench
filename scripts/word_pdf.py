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
- **After any kill: cleanup is scoped to what this run owns.** AutoRecovery
  entries and `~$` lock files are removed only when they were written at or
  after this session started, and only in folders this run created; anything
  older is a person's and is left alone. When preflight did **not** establish
  that Word held zero documents, AutoRecovery is not touched at all and the
  Document Recovery pane is the price. Nothing here ever wipes that directory
  (§12 step 4).
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
- **Word's alerts are read and answered in one round trip each, and everything
  they say is logged.** One `osascript` per poll returns every alert's buttons
  *and* its text; a repair prompt is recognised from that (its wording, or its
  Yes/No pair when the wording is not readable) and answered by a second script
  that brings Word forward, presses No, waits for the "Word experienced an error
  trying to open the file" OK that follows, presses it, and hands focus back.
  Until 2026-10-14 the text-matched handler never fired in any logged run (0 ×
  "repair prompt declined" against 259 × "dismissed via 'No'" from the generic
  fallback, ~6 s and three osascripts later), and the OK after it was never
  pressed while Word sat in the background, where that alert does not exist for
  System Events: each broken fixture then cost the full 240 s AppleEvent timeout
  and one of the three batch passes. `--no-focus` keeps the old background-only
  behaviour.

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

import fcntl
import hashlib
import json
import math
import os
import re
from collections.abc import Callable
from contextvars import ContextVar
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Annotated, Self

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

console = Console()


def make_console_sink(target: Console = console) -> Callable[[str], None]:
    """A loguru sink that prints a log line exactly as logged, in colour.

    Rich's defaults read `[word]`, `[batch]`, `[ok]` as markup tags and drop
    them, and turn `:recycle:` into an emoji: the 2026-10-14 screen logs showed
    `recovery 1:` for `[word] recovery 1:` and `♻` in the function name while
    the file log was right. So the text is taken as text: loguru's own level
    colours (add the sink with `colorize=True`) come in as ANSI and are kept,
    rich's highlighter still colours numbers, paths and quoted strings, and
    nothing is parsed as markup or emoji.
    """
    from rich.highlighter import ReprHighlighter
    from rich.text import Text

    highlight = ReprHighlighter()

    def sink(message: str) -> None:
        # The highlighter returns a highlighted copy; it does not edit in place.
        text = highlight(Text.from_ansi(message.rstrip("\n")))
        target.print(text, soft_wrap=True)

    return sink

WORD_APP = Path("/Applications/Microsoft Word.app")
WORD_PROC = "Microsoft Word"
MERP_PROC = "Microsoft Error Reporting"
CONTAINER_TMP = Path.home() / "Library/Containers/com.microsoft.Word/Data/tmp"
AUTORECOVERY = (
    Path.home()
    / "Library/Containers/com.microsoft.Word/Data/Library/Preferences/AutoRecovery"
)
# One Word, one driver. Every driver takes an exclusive flock on this file for the
# whole run; a second one waits, saying who holds it, instead of closing the first
# run's documents and restarting Word under it (which is what two concurrent runs did
# to each other on 2026-10-14: 63 of 64 pairs failed in one, every item after the
# collision in the other).
WORD_LOCK_PATH = Path.home() / "Library/Containers/com.microsoft.Word/Data/word_driver.lock"

# MERP's decline control. The straight and curly apostrophes are both listed
# because macOS UI labels normally use U+2019 and a straight-quote match would
# silently never fire. The watchdog logs every button it actually sees the first
# time it meets this dialog, so the real label is recorded rather than guessed.
#
# Don't Send stays first: when that button exists, it is the one that refuses
# the report. OK is last. On this Mac the window has no Don't Send — its
# buttons are OK, More Information, and an unnamed control reported as
# "missing value". OK closes that window. More Information only opens the
# details pane, so it is not listed.
MERP_DECLINE = (
    "Don't Send",
    "Don\u2019t Send",
    "Cancel",
    "Close",
    "Quit",
    "No",
    "OK",
    "Ok",
)

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

# The steps `answer_alert` runs for a repair prompt: No, then the OK Word raises after it.
NO_STEP = "No"
OK_STEP = "OK|Ok"

# Field separators in what `_DUMP_DIALOGS` and `_ANSWER` return: one record per alert
# (RS), its button names tab-joined, then US, then the alert's text. Neither byte can
# occur in a button label or in Word's prose, so no quoting is needed on either side.
_RS = "\x1e"
_US = "\x1f"


# ─── pure helpers (no Word, no macOS — unit-testable anywhere) ────────────────


@dataclass(slots=True, frozen=True)
class Dialog:
    """One alert as System Events showed it: its buttons, and the text beside them."""

    buttons: tuple[str, ...]
    text: str = ""


@dataclass(slots=True, frozen=True)
class DialogEvent:
    """One answer the watchdog gave: which buttons it pressed, and what the alert said."""

    at: float
    process: str
    pressed: tuple[str, ...]
    text: str


def parse_dialogs(dump: str) -> list[Dialog]:
    """Read `_DUMP_DIALOGS`'s output. A record with no US is a bare button list."""
    dialogs: list[Dialog] = []
    for record in dump.split(_RS):
        if not record.strip():
            continue
        names, _, text = record.partition(_US)
        buttons = tuple(n.strip() for n in names.split("\t") if n.strip())
        text = text.strip(" |")
        # The first static text of a Word alert is its title, the process name.
        for title in (WORD_PROC, MERP_PROC):
            text = text.removeprefix(f"{title} | ")
        if buttons:
            dialogs.append(Dialog(buttons, text))
    return dialogs


def is_repair_prompt(dialog: Dialog) -> bool:
    """Word's "repair this document?" prompt, by its words, or by its Yes/No pair.

    The words are the specific match. The Yes/No pair stands in for them because the
    text is not always readable through System Events, and the generic fallback has
    answered that pair "No" 259 times in the logged runs anyway: the only change is
    that it is now answered first, with the OK that follows, and on the record.
    """
    if any(marker in dialog.text for marker in REPAIR_MARKERS):
        return True
    return {"Yes", "No"} <= set(dialog.buttons)


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


# ─── output names, input names, manifest ─────────────────────────────────────
#
# Every file a tool writes carries the tool in its name: `deal_byword.pdf`,
# `deal_bysoffice.pdf`, `deal_bydocxide.pdf`, ... so a folder of renders from
# several engines never needs a side table to say which engine made which.

TOOL = "word"
NAME_LIMIT = 80
MANIFEST_NAME = "manifest.jsonl"


def by_tool(stem: str, tool: str = TOOL) -> str:
    """`<stem>_by<tool>`: the stem of every file `tool` writes."""
    return f"{stem}_by{tool}"


def pdf_path_for(docx: Path, out_dir: Path | None) -> Path:
    """Where a document's PDF goes: `<stem>_byword.pdf` beside it, or into `out_dir`."""
    return (out_dir or docx.parent) / f"{by_tool(docx.stem)}.pdf"


def legacy_output(path: Path, tool: str = TOOL) -> Path | None:
    """The same output under the spelling before `_by<tool>` (2026-10-14), or None."""
    mark = f"_by{tool}"
    if not path.stem.endswith(mark):
        return None
    return path.with_name(f"{path.stem[: -len(mark)]}{path.suffix}")


def existing_output(path: Path) -> Path | None:
    """`path` when it is already on disk and non-empty, else the same output
    under its pre-`_byword` spelling, else None.

    The suffix arrived with 1194 corpus PDFs already written as `<stem>.pdf`;
    a run must skip those rather than redo them, and the manifest records the
    skip with the path that was found.
    """
    for candidate in (path, legacy_output(path)):
        if candidate is not None and candidate.exists() and candidate.stat().st_size > 0:
            return candidate
    return None


def trim_name(name: str, limit: int = NAME_LIMIT) -> str:
    """A file name of at most `limit` characters, unique per original name.

    Names within the limit come back unchanged. Longer ones become
    `<stem cut to fit>_<8 hex of sha1(original)><ext>`: the digest keeps two
    long names that share a prefix apart, and the same original always trims
    to the same name, so a second run finds the file it renamed.
    """
    if len(name) <= limit:
        return name
    ext = Path(name).suffix
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    keep = limit - len(ext) - 1 - len(digest)
    stem = Path(name).stem[:keep].rstrip(" ._")
    return f"{stem}_{digest}{ext}"


def trim_long_names(docs: list[Path], manifest: Path | None, limit: int = NAME_LIMIT) -> list[Path]:
    """Rename on disk every document whose file name is longer than `limit`.

    Returns the same documents, in the same order, under their names on disk
    afterwards. A rename that would land on an existing file is skipped (the
    long name stays, with a warning) rather than overwrite anything. Each
    rename is appended to `manifest` as a `renamed` line when one is given.
    """
    renamed: list[Path] = []
    lines: list[dict[str, object]] = []
    for doc in docs:
        short = trim_name(doc.name, limit)
        if short == doc.name:
            renamed.append(doc)
            continue
        target = doc.with_name(short)
        if target.exists():
            logger.warning(
                f"[names] {doc.name} is {len(doc.name)} characters, over {limit}, but "
                f"{short} already exists beside it; leaving the long name alone"
            )
            renamed.append(doc)
            continue
        doc.rename(target)
        logger.info(f"[names] renamed ({len(doc.name)} characters, over {limit}): {doc.name} -> {short}")
        renamed.append(target)
        lines.append(manifest_line(doc, target, status="renamed", kind="rename", tool="driver"))
    if manifest is not None and lines:
        append_manifest(manifest, lines)
    return renamed


def manifest_path_for(out_dir: Path | None, src: Path) -> Path:
    """`manifest.jsonl` lives where the outputs go: `out_dir`, else beside the sources."""
    return (out_dir or src) / MANIFEST_NAME


def manifest_line(
    source: Path,
    output: Path | None,
    *,
    status: str,
    kind: str,
    error: str = "",
    seconds: float = 0.0,
    tool: str = TOOL,
    **extra: object,
) -> dict[str, object]:
    """One `manifest.jsonl` record. The first four keys are the contract; the rest is context."""
    return {
        "original_filename": source.name,
        "path_origin": str(source),
        "converted_filename": output.name if output else "",
        "path_out": str(output) if output else "",
        "status": status,
        "kind": kind,
        "tool": tool,
        "error": error,
        "seconds": round(seconds, 3),
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        **extra,
    }


def manifest_lines(results: list[Result], *, kind: str) -> list[dict[str, object]]:
    """A record per file each result produced (or one, empty, for a failure)."""
    lines: list[dict[str, object]] = []
    for r in results:
        status = "skipped" if r.skipped else "ok" if r.ok else "failed"
        outputs: list[Path | None] = [r.output, *r.also] if (r.output or r.also) else [None]
        for out in outputs:
            lines.append(
                manifest_line(r.source, out, status=status, kind=kind, error=r.error, seconds=r.seconds)
            )
    return lines


def append_manifest(path: Path, lines: list[dict[str, object]]) -> int:
    """Append JSON lines to `path` (created with its folder as needed). Returns how many."""
    if not lines:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
    return len(lines)


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
    also: tuple[Path, ...] = ()
    """Other files Word wrote for this document besides `output` (accept-all's docx)."""


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
    except (ValueError, OverflowError) as exc:
        # `subprocess.run` converts the timeout to an integer, so `nan` raises
        # ValueError and `inf` raises OverflowError before the child is ever
        # spawned. The CLI rejects both, but this function promises never to
        # raise and is reachable from the API, so it keeps that promise here
        # rather than relying on every caller having validated first.
        return None, "", f"invalid timeout ({timeout!r}): {exc}"
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def positive_seconds(value: float, param: str) -> float:
    """A timeout has to be a real, positive duration.

    Neither half of this is pedantry. `nan` and `inf` reach `subprocess.run`
    and break it before the child is spawned, and zero or a negative value is
    worse than an error: `subprocess.run` accepts it and reports TimeoutExpired
    immediately, so every call "times out" and the run fails uniformly with a
    plausible-looking reason.
    """
    try:
        return require_positive_seconds(value, param)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint=param) from exc


def require_positive_seconds(value: float, name: str) -> float:
    """`positive_seconds` for API callers: the same rule, as a ValueError."""
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive number of seconds, not {value!r}")
    return value


_SET_ALERTS = """
on run argv
  tell application "Microsoft Word" to set displayAlerts to (item 1 of argv is "true")
end run
""".strip()

_COUNT_DOCS = 'tell application "Microsoft Word" to count of documents'

_CLOSE_ALL = 'tell application "Microsoft Word" to close every document saving no'

# Closing one document by name. Used only under `--do-not-close`, where the
# operator keeps their documents open and the run may close just the item that
# failed. The default policy is `_CLOSE_ALL`, whoever opened what.
_CLOSE_NAMED = """
on run argv
  tell application "Microsoft Word"
    repeat with i from (count documents) to 1 by -1
      if name of document i is (item 1 of argv) then close document i saving no
    end repeat
  end tell
end run
""".strip()

# How long one AppleEvent to Word (open, save, close) may block before AppleScript
# gives up. A hung document costs this much per pass; it was 600 s.
APPLE_EVENT_TIMEOUT = 240

# Open, save as PDF, close. `document 1` rather than `active document`: the
# indexed form is what the audit found working from a script file, and it is
# never ambiguous (§5.2, §14.1).
_EXPORT_PDF = """
on baseName(p)
  set od to AppleScript's text item delimiters
  set AppleScript's text item delimiters to "/"
  set parts to text items of p
  set AppleScript's text item delimiters to od
  return item -1 of parts
end baseName

on run argv
  set inPath to item 1 of argv
  set outPath to item 2 of argv
  set wantName to my baseName(inPath)
  with timeout of __AE_TIMEOUT__ seconds
    tell application "Microsoft Word"
      set theDoc to missing value
      close every document saving no
      set seenBeforeOpen to {}
      repeat with i from 1 to (count of documents)
        set end of seenBeforeOpen to name of document i
      end repeat
      open (POSIX file inPath) confirm conversions false add to recent files false
      -- The document is the NEW one NAMED after the file, never `document 1`
      -- (§5.18). A document that survived the close-all was saved under a
      -- broken file's name when that file's open produced nothing, and a
      -- ghost whose name reads as missing value before the open shows up as
      -- "Document1" after it, so "the one new document" is not enough either
      -- (both seen live 2026-10-14).
      set newCount to 0
      repeat with i from 1 to (count of documents)
        set nm to missing value
        try
          set nm to name of document i
        end try
        if seenBeforeOpen does not contain nm then
          set newCount to newCount + 1
          if (nm as string) is wantName then set theDoc to document i
        end if
      end repeat
      if theDoc is missing value then
        repeat with i from (count of documents) to 1 by -1
          try
            if (name of document i as string) is wantName then close document i saving no
          end try
        end repeat
        error "open produced " & newCount & " new documents, none named " & wantName & "; refusing to guess"
      end if
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

# `--do-not-close`: close only the document this export opened.
# Default closes every document. `--do-not-close` flips this for the export
# that is about to run. A context var so callers that replace `export_pdf`
# in tests are not forced to grow a parameter.
_close_documents: ContextVar[bool] = ContextVar("word_close_documents", default=True)
# Word names the staged file in its dialogs ("Word found unreadable content in …").
# A label in front of that name says whose file it is while a run is watched.
_stage_label: ContextVar[str] = ContextVar("word_stage_label", default="")
_LABEL = re.compile(r"[A-Za-z0-9._-]+")
# `--focus/--no-focus`: whether the run may bring Word forward to answer an alert (and
# hand focus straight back). Word's alert after "No" does not exist for System Events
# while Word is in the background, so without this the open hangs to its timeout.
_focus: ContextVar[bool] = ContextVar("word_focus", default=True)
# Only one script drives Word's focus at a time: the watchdog's answer and the batch
# progress nudge are separate threads and would otherwise fight over frontmost.
_FOCUS_LOCK = threading.Lock()
# The batch log of the monolithic script now running, if any (set by `run_batch`). The
# watchdog appends `[declined]\t<file>` to it when it declines a repair prompt, so the
# script can tell a file Word refused from Word's poison state: both open as an empty
# document, but only the second is a reason to stop the pass and recycle Word.
_BATCH_LOG: Path | None = None
# What the watchdog writes into a batch log when it ends a pass on the error reporter.
_SIGNAL_MARK = "the error reporter appeared: Word crashed on this item"
_DECLINED_FILE = re.compile(r"unreadable content in (.+?\.docx)")


def declined_file(text: str) -> str:
    """The file a repair prompt named, from Word's own sentence; '' when it did not."""
    match = _DECLINED_FILE.search(text)
    return match.group(1) if match else ""


def mark_declined(name: str) -> None:
    """Record a declined file in the running batch log, when there is one."""
    log = _BATCH_LOG
    if not log or not name:
        return
    try:
        with log.open("a", encoding="utf-8") as fh:
            fh.write(f"[declined]\t{name}\n")
    except OSError as exc:
        logger.warning(f"[watchdog] could not record the declined file in {log.name}: {exc}")

_EXPORT_PDF = _EXPORT_PDF.replace("__AE_TIMEOUT__", str(APPLE_EVENT_TIMEOUT))

_EXPORT_PDF_KEEP_OPEN = _EXPORT_PDF.replace(
    "close every document saving no",
    "if theDoc is not missing value then close theDoc saving no",
)


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

# One poll: every window and sheet of the process that carries buttons, as one record
# each — the button names tab-joined, US, the static text beside them (direct children,
# and one level of groups, which is where an alert keeps its sentences; never the whole
# UI tree, which on a document window runs to thousands of elements). A window with no
# buttons is not an alert and is skipped before its text is read, so a document window
# costs one `buttons of` query. Every System Events term sits inside a `tell application
# "System Events"` block, including the handlers: terms used outside one do not compile,
# and a script that does not compile answers nothing and says nothing in the loop.
_DUMP_DIALOGS = """
on textOf(target)
  set acc to ""
  tell application "System Events"
    try
      repeat with stx in (static texts of target)
        try
          set v to (value of stx) as string
          if v is not "" then set acc to acc & v & " | "
        end try
      end repeat
    end try
    try
      repeat with g in (groups of target)
        repeat with stx in (static texts of g)
          try
            set v to (value of stx) as string
            if v is not "" then set acc to acc & v & " | "
          end try
        end repeat
      end repeat
    end try
  end tell
  return acc
end textOf

on buttonsOf(target)
  set names to ""
  tell application "System Events"
    try
      repeat with b in (buttons of target)
        try
          set names to names & ((name of b) as string) & tab
        end try
      end repeat
    end try
  end tell
  return names
end buttonsOf

on run argv
  set procName to item 1 of argv
  set out to ""
  tell application "System Events"
    if not (exists process procName) then return ""
    tell process procName
      repeat with w in windows
        set targets to {w}
        try
          set targets to {w} & (sheets of w)
        end try
        repeat with target in targets
          set names to my buttonsOf(target)
          if names is not "" then
            set out to out & names & (character id 31) & (my textOf(target)) & (character id 30)
          end if
        end repeat
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


# Bring the process forward, press a sequence of buttons, hand focus back. argv: process
# name, seconds each step may wait, then the steps; a step is button names joined by "|",
# any one of which is pressed. Steps run in order and stop at the first that finds none
# of its buttons, or after an OK, which is the last thing Word says. Returns one record
# per press: the button, US, the text of the alert it was on (read before the press).
#
# This is what answers the repair prompt. "No" is the answer — "Yes" makes Word rewrite
# the document and we would then be measuring Word's repair, not the file we were
# handed — and it has to be followed by the OK on "Word experienced an error trying to
# open the file", which Word raises after the No but, while it is in the background,
# does not show to System Events at all (0 windows); the open then blocks until the
# AppleEvent timeout. Frontmost, Word shows it at once (2026-09-30, `word_pdf_focus`).
# The wait is bounded by the clock, not by a count of System Events calls: while Word
# is busy each call can take a second, and the focus trial's 10 s check took 28 s.
# Word goes back into hiding unless it was the app in front (someone working in it).
_ANSWER = """
on textOf(target)
  set acc to ""
  tell application "System Events"
    try
      repeat with stx in (static texts of target)
        try
          set v to (value of stx) as string
          if v is not "" then set acc to acc & v & " | "
        end try
      end repeat
    end try
    try
      repeat with g in (groups of target)
        repeat with stx in (static texts of g)
          try
            set v to (value of stx) as string
            if v is not "" then set acc to acc & v & " | "
          end try
        end repeat
      end repeat
    end try
  end tell
  return acc
end textOf

on pressAny(procName, names)
  tell application "System Events"
    tell process procName
      repeat with w in windows
        set targets to {w}
        try
          set targets to {w} & (sheets of w)
        end try
        repeat with target in targets
          repeat with nm in names
            try
              if exists button (nm as string) of target then
                set said to my textOf(target)
                perform action "AXPress" of button (nm as string) of target
                return {nm as string, said}
              end if
            end try
          end repeat
        end repeat
      end repeat
    end tell
  end tell
  return {"", ""}
end pressAny

on run argv
  set procName to item 1 of argv
  set waitFor to (item 2 of argv) as number
  set steps to items 3 thru -1 of argv
  set priorApp to ""
  set done to ""
  tell application "System Events"
    try
      set priorApp to name of first process whose frontmost is true
    end try
    if not (exists process procName) then return ""
    tell process procName to set frontmost to true
  end tell
  set od to AppleScript's text item delimiters
  repeat with stepText in steps
    set AppleScript's text item delimiters to "|"
    set names to text items of (stepText as string)
    set AppleScript's text item delimiters to od
    set pressed to ""
    set said to ""
    set t0 to current date
    repeat
      set hit to my pressAny(procName, names)
      set pressed to item 1 of hit
      set said to item 2 of hit
      if pressed is not "" then exit repeat
      if ((current date) - t0) ≥ waitFor then exit repeat
      delay 0.25
    end repeat
    if pressed is "" then exit repeat
    set done to done & pressed & (character id 31) & said & (character id 30)
    if pressed is "OK" or pressed is "Ok" then exit repeat
  end repeat
  tell application "System Events"
    if priorApp is not procName then
      try
        set visible of process procName to false
      end try
      if priorApp is not "" then
        try
          set frontmost of (first process whose name is priorApp) to true
        end try
      end if
    end if
  end tell
  return done
end run
""".strip()


def answer_alert(
    *steps: str, wait: float, process: str = WORD_PROC, skip_if_busy: bool = False
) -> list[tuple[str, str]]:
    """Run `_ANSWER`: bring `process` forward, press `steps` in order, hand focus back.

    Returns `(button, text)` per press, in order. Focus-taking is serialised through
    `_FOCUS_LOCK`; with `skip_if_busy` a caller that merely wanted to look (the batch
    progress nudge) returns empty instead of queueing behind an answer in progress.
    """
    if skip_if_busy:
        if not _FOCUS_LOCK.acquire(blocking=False):
            return []
    else:
        _FOCUS_LOCK.acquire()
    try:
        _, out, _ = osa(_ANSWER, process, str(wait), *steps, timeout=wait * len(steps) + 15)
    finally:
        _FOCUS_LOCK.release()
    return [(d.buttons[0], d.text) for d in parse_dialogs(out)]


def _parse_etime(text: str) -> float:
    """Seconds from `ps -o etime` text: [[D-]HH:]MM:SS."""
    text = text.strip()
    days = 0
    if "-" in text:
        d, text = text.split("-", 1)
        days = int(d)
    parts = [int(x) for x in text.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, sec = parts
    return days * 86400 + h * 3600 + m * 60 + sec


def word_pid() -> str:
    """Word's process id, or "none": a changing pid in the log means someone else restarted it."""
    found = subprocess.run(["pgrep", "-n", "-x", WORD_PROC], capture_output=True, text=True, check=False)
    pids = (getattr(found, "stdout", "") or "").split()
    return pids[-1] if pids else "none"


def process_age_seconds(name: str) -> float | None:
    """How long the newest process called `name` has been running, or None when there is none."""
    found = subprocess.run(["pgrep", "-n", "-x", name], capture_output=True, text=True, check=False)
    pid = (getattr(found, "stdout", "") or "").strip().splitlines()
    if getattr(found, "returncode", None) != 0 or not pid:
        return None
    aged = subprocess.run(["ps", "-o", "etime=", "-p", pid[-1]], capture_output=True, text=True, check=False)
    try:
        return _parse_etime(getattr(aged, "stdout", "") or "")
    except ValueError:
        return None


def _said(text: str) -> str:
    """How an alert's words appear in a log line."""
    return f'Word said: "{text}"' if text else "Word showed no readable text"


@dataclass
class Watchdogs:
    """Two pollers: Word's own modals, and Microsoft Error Reporting.

    MERP runs as its own process, so a handler aimed at Word cannot see it — the
    single reason no script in the audited corpus could dismiss it (§12.1).
    Every button label encountered is logged the first time, so the real control
    names are recorded from a live run instead of assumed, and so is every
    distinct thing an alert says; each answer given is kept in `events`.

    One `osascript` per poll reads every alert's buttons and text. A repair
    prompt is answered by `answer_alert`, which brings Word forward for the OK
    that follows the No (`focus`); when that OK has not appeared within `wait`
    seconds, Word still owes it, and for the next `owe_window` seconds a poll
    that finds no alert brings Word forward again to look for it, at most once
    per `owe_every`. With `focus` off the No is pressed where Word is and
    nothing is activated, which is the pre-2026-10-14 behaviour.

    Measured on 2026-10-14 (3 repair-prompt fixtures + 2 controls, one run):
    the dump reads the prompt's wording; two prompts were answered No then OK
    inside one activation within a second of being seen; for one file Word
    raised its OK only ~35 s after the No (its own time, the screen log shows
    nothing in between), which is why the window is 90 s and the batch
    progress check also looks every 15 s. No AppleEvent timeout; the batch
    finished in 3 m 41 s with the right verdict on all five.
    """

    poll: float = 1.0
    focus: bool = field(default_factory=lambda: _focus.get())
    wait: float = 3.0  # seconds each press waits for its button while Word is frontmost
    owe_window: float = 90.0  # seconds after a No during which Word may still owe its OK
    owe_every: float = 5.0  # seconds between looks for that OK (each one is a focus flip)
    # The error reporter appears a median 4 to 5 s before the batch osascript
    # gets `Connection is invalid` (A/B of 2026-10-14, out/ab/AB_REPORT.md).
    # With this on, seeing it marks the item Word was on as a crash in the batch
    # log and ends that pass at once: detection fell from 4.7 s to 2.4 s median
    # and 20 crashers took 251 s instead of 382 s with no output lost. On by
    # default; `--no-crash-signal` turns it off.
    kill_pass_on_crash: bool = True
    _signalled: set[tuple[Path, int]] = field(default_factory=set)
    _stop: threading.Event = field(default_factory=threading.Event)
    _threads: list[threading.Thread] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    said: set[str] = field(default_factory=set)
    events: list[DialogEvent] = field(default_factory=list)
    dismissed: int = 0
    granted: int = 0
    declined: int = 0
    forwarded: int = 0
    owed_until: float = 0.0
    _owed_next: float = 0.0

    def _note_dialogs(self, proc: str, dialogs: list[Dialog]) -> None:
        for dialog in dialogs:
            for name in dialog.buttons:
                if (key := f"{proc}:{name}") not in self.seen:
                    self.seen.add(key)
                    # System Events answers `missing value` for a button with
                    # no title and "" for an empty one; say which it was.
                    if name == "missing value":
                        what = "a button with no name (AppleScript 'missing value')"
                    elif not name:
                        what = "a button with an empty name"
                    else:
                        what = f"button {name!r}"
                    logger.info(f"[watchdog] {proc} shows {what}")
            if dialog.text and dialog.text not in self.said:
                self.said.add(dialog.text)
                logger.info(f"[watchdog] {proc} says: {dialog.text!r}")

    def _note_buttons(self, proc: str) -> None:
        """One extra dump, for a caller that has not already read the alerts."""
        _, out, _ = osa(_DUMP_DIALOGS, proc, timeout=8)
        self._note_dialogs(proc, parse_dialogs(out))

    def _record(self, proc: str, pressed: tuple[str, ...], text: str) -> None:
        self.events.append(DialogEvent(time.monotonic(), proc, pressed, text))

    def _forward(self, *steps: str) -> list[tuple[str, str]]:
        presses = answer_alert(*steps, wait=self.wait)
        if presses:
            self.forwarded += 1
        return presses

    def _decline_repair(self, dialog: Dialog) -> None:
        """Answer the repair prompt: No, then the OK Word raises after it."""
        if self.focus:
            presses = self._forward(NO_STEP, OK_STEP)
        else:
            _, pressed, _ = osa(_PRESS, WORD_PROC, NO_STEP, timeout=10)
            presses = [(pressed, dialog.text)] if pressed else []
        if not presses:
            logger.warning(f"[watchdog] repair prompt seen but no button could be pressed; {_said(dialog.text)}")
            return
        self.declined += 1
        buttons = tuple(b for b, _ in presses)
        text = next((t for _, t in presses if t), dialog.text)
        self._record(WORD_PROC, buttons, text)
        mark_declined(declined_file(text))
        how = " then ".join(repr(b) for b in buttons)
        where = " with Word brought forward" if self.focus else ""
        logger.warning(f"[watchdog] repair prompt declined via {how}{where}; {_said(text)}")
        for button, said in presses[1:]:
            if said:
                logger.warning(f"[watchdog] after the No, Word showed {button!r}; {_said(said)}")
        # An OK pressed in the same activation settles the debt; otherwise Word still
        # owes it and the next empty polls go looking, for `owe_window` seconds.
        answered_ok = any(b in ("OK", "Ok") for b in buttons)
        self.owed_until = 0.0 if answered_ok or not self.focus else time.monotonic() + self.owe_window
        self._owed_next = 0.0

    def _fetch_owed(self) -> None:
        if not self.owed_until:
            return
        now = time.monotonic()
        if now > self.owed_until:
            self.owed_until = 0.0
            logger.warning("[watchdog] no OK appeared after the last No; stopped bringing Word forward")
            return
        if now < self._owed_next:
            return
        self._owed_next = now + self.owe_every
        presses = self._forward(OK_STEP)
        if presses:
            self.owed_until = 0.0
            button, text = presses[0]
            self._record(WORD_PROC, (button,), text)
            logger.warning(f"[watchdog] the OK Word owed after the No was pressed with Word brought forward; {_said(text)}")

    def _loop_word(self) -> None:
        while not self._stop.wait(self.poll):
            _, dump, _ = osa(_DUMP_DIALOGS, WORD_PROC, timeout=8)
            dialogs = parse_dialogs(dump)
            if not dialogs:
                self._fetch_owed()
                continue
            self._note_dialogs(WORD_PROC, dialogs)
            # The repair prompt first, answered "No" and followed to its OK. It has
            # to run before the generic handlers, which would otherwise press "OK"
            # on it, and before any 240 s AppleEvent timeout does.
            repair = next((d for d in dialogs if is_repair_prompt(d)), None)
            if repair is not None:
                self._decline_repair(repair)
                continue
            # Accept a sandbox grant next. Never Cancel one: denying guarantees
            # a re-prompt on every later file (§14.3).
            # A grant must be pressed with Word frontmost or the panel never
            # renders to accept it (§6.1). Focus is handed straight back. The
            # dump already names the buttons, so Word is only activated when
            # one of them is a grant; an ordinary alert no longer costs a focus
            # flip and a 20 s budget to find that out.
            if any(name in GRANT_BUTTONS for d in dialogs for name in d.buttons):
                _, pressed, _ = osa(_PRESS_ACTIVATED, WORD_PROC, *GRANT_BUTTONS, timeout=20)
                if pressed:
                    self.granted += 1
                    self._record(WORD_PROC, (pressed,), dialogs[0].text)
                    logger.warning(f"[watchdog] sandbox grant completed via {pressed!r}")
                    continue
            # Everything else is an ordinary alert; no activation needed, and
            # Cancel here is safe because a grant would have matched above.
            _, pressed, _ = osa(_PRESS, WORD_PROC, *DISMISS_BUTTONS, timeout=10)
            if pressed:
                self.dismissed += 1
                text = next((d.text for d in dialogs if pressed in d.buttons and d.text), dialogs[0].text)
                self._record(WORD_PROC, (pressed,), text)
                logger.warning(f"[watchdog] Word dialog dismissed via {pressed!r}; {_said(text)}")
                if pressed in ("OK", "Ok"):
                    self.owed_until = 0.0

    def _loop_merp(self) -> None:
        while not self._stop.wait(self.poll):
            _, out, _ = osa(_DUMP_DIALOGS, MERP_PROC, timeout=8)
            dialogs = parse_dialogs(out)
            if not dialogs:
                continue
            self._note_dialogs(MERP_PROC, dialogs)
            self._crash_signal(dialogs[0].text)
            _, pressed, _ = osa(_PRESS, MERP_PROC, *MERP_DECLINE, timeout=10)
            if pressed:
                self.dismissed += 1
                self._record(MERP_PROC, (pressed,), dialogs[0].text)
                logger.warning(f"[watchdog] error report declined via {pressed!r}; {_said(dialogs[0].text)}")
            else:
                logger.error(
                    f"[watchdog] {MERP_PROC} is showing a dialog whose buttons match "
                    f"none of {MERP_DECLINE}. Labels seen are logged above — add the "
                    "real one to MERP_DECLINE."
                )

    def _crash_signal(self, text: str) -> None:
        """The error reporter is up, so Word has crashed: end the running pass now.

        The item Word was on is the first manifest row without a line in the
        batch log. It gets a `[retry]` line carrying the crash mark, so the
        resume logic counts it against `--crash-limit` and sends it to the back
        exactly as it would after the osascript's own `Connection is invalid`;
        then that pass's osascript is ended. It is found by its manifest path,
        which no other process carries: never a blanket `pkill osascript`
        (§14.5). Once per item: the reporter stays up until its OK is pressed.
        """
        log_path = _BATCH_LOG
        if not self.kill_pass_on_crash or log_path is None:
            return
        manifest = log_path.with_suffix(".tsv")
        try:
            lines = log_path.read_text(errors="replace").splitlines()
            rows = [ln.split("\t") for ln in manifest.read_text(encoding="utf-8").splitlines() if ln]
            pass_age = time.time() - manifest.stat().st_mtime
        except OSError:
            return
        if lines and (_SIGNAL_MARK in lines[-1] or (lines[-1].startswith("[retry]") and any(m in lines[-1] for m in _CRASH_MARKS))):
            return  # the pass is already ending on this crash: ours, or the script saw it itself
        index = sum(1 for ln in lines if ln.startswith(("[ok]", "[fail]", "[retry]", "[defer]")))
        key = (log_path, index)
        if key in self._signalled or index >= len(rows):
            return
        # The reporter for the previous crash can surface after the next pass
        # has begun (mixed-set A/B, 2026-10-14: five good documents were marked
        # as crashers that way). One older than this pass's manifest is not
        # about the current item.
        reporter_age = process_age_seconds(MERP_PROC)
        if reporter_age is not None and reporter_age > pass_age:
            self._signalled.add(key)
            logger.info(
                f"[watchdog] the error reporter is older than this pass ({reporter_age:.0f} s vs "
                f"{pass_age:.0f} s): it reports the previous crash, not item {rows[index][0]}; ignoring it"
            )
            return
        self._signalled.add(key)
        rid = rows[index][0]
        # pkill -f takes an extended regex: escape the metacharacters a path can
        # hold, and nothing else, so the log shows the path as it is.
        pattern = re.sub(r"([.+*?^$()\[\]{}|\\])", r"\\\1", str(manifest))
        cmd = ["pkill", "-f", pattern]
        logger.warning(
            f"[watchdog] Word crashed on item {rid} (error reporter up; {_said(text)}); "
            f"ending the pass now rather than waiting for the AppleEvent to fail, running: {shown(cmd)}"
        )
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        rc = getattr(proc, "returncode", None)
        if rc != 0:
            logger.info(f"[watchdog] returned rc={rc}, no pass to end (it had already ended on its own; its log stands)")
            return
        logger.info(f"[watchdog] returned rc={rc}, the pass is ending")
        # Mark only now, after the script is gone and cannot add a line of its own.
        try:
            tail = log_path.read_text(errors="replace").splitlines()
        except OSError:
            tail = lines
        if tail and tail[-1].startswith("[retry]") and any(m in tail[-1] for m in _CRASH_MARKS):
            return  # it logged the crash in its last breath; that line names the right item
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[retry]\t{rid}\tConnection is invalid ({_SIGNAL_MARK})\n")

    def start(self) -> None:
        for fn in (self._loop_word, self._loop_merp):
            t = threading.Thread(target=fn, daemon=True)
            t.start()
            self._threads.append(t)

    def stop(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=3)
        if self._threads:
            logger.info(
                f"[watchdog] tally: declined={self.declined} dismissed={self.dismissed} "
                f"granted={self.granted} forwarded={self.forwarded} alerts_seen={len(self.said)}"
            )
            self._threads.clear()

    def __enter__(self) -> Self:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()


def shown(cmd: list[str] | str, *args: str) -> str:
    """A command as it would be typed, for a log line that says what is run.

    An AppleScript is shown as `osascript -e '<script>' <args>`; a multi-line
    script is folded onto one line so the log line stays one line.
    """
    import shlex

    if isinstance(cmd, str):
        script = " ".join(cmd.split())
        parts = ["osascript", "-e", script, *args]
    else:
        parts = [*cmd, *args]
    return " ".join(shlex.quote(part) for part in parts)


_QUIT = 'tell application "Microsoft Word" to quit saving no'
_LAUNCH = ["open", "-g", "-a", str(WORD_APP)]


# ─── one Word, one driver ────────────────────────────────────────────────────


class WordBusy(RuntimeError):
    """Another driver holds Word and did not let go within the wait."""


@dataclass
class WordLock:
    """An exclusive, cross-process claim on Word for the length of a run.

    `flock` on `WORD_LOCK_PATH`, which also records the holder (pid, label, since)
    so a waiter can say who it is waiting for. The lock dies with the process, so
    a killed run never leaves Word locked. `wait` is how long to wait for the
    holder; 0 refuses at once.
    """

    label: str = ""
    wait: float = 900.0
    poll: float = 2.0
    say_every: float = 30.0
    held: bool = False
    _fh: object = None

    def holder(self) -> str:
        try:
            return WORD_LOCK_PATH.read_text().strip() or "another driver"
        except OSError:
            return "another driver"

    def __enter__(self) -> Self:
        if self.held:
            return self
        WORD_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fh = open(WORD_LOCK_PATH, "a+", encoding="utf-8")  # noqa: SIM115 (held for the run)
        deadline = time.monotonic() + self.wait
        last_said = -math.inf
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                now = time.monotonic()
                who = self.holder()
                if now - last_said >= self.say_every:
                    logger.warning(
                        f"[word] Word is in use by {who}; waiting up to {max(0.0, deadline - now):.0f} s more"
                    )
                    last_said = now
                if now >= deadline:
                    fh.close()
                    raise WordBusy(f"Word is in use by {who}") from None
                time.sleep(self.poll)
        fh.seek(0)
        fh.truncate()
        fh.write(f"pid {os.getpid()} {self.label} since {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.flush()
        self._fh = fh
        self.held = True
        return self

    def __exit__(self, *exc: object) -> None:
        fh = self._fh
        if fh is None:
            return
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        finally:
            fh.close()
            self._fh = None
            self.held = False


# ─── Word lifecycle ──────────────────────────────────────────────────────────


def _first_line(text: str) -> str:
    """The first non-blank line of a command's output, trimmed to 160 characters."""
    text = (text or "").strip()
    return text.splitlines()[0][:160] if text else ""


@dataclass
class WordSession:
    """Owns Word's process lifecycle: warm, recycle, clean up after a kill."""

    warm_timeout: float = 90.0
    answer_grace: float = 15.0
    """Seconds Word gets to answer an Apple event after the close-all before the
    recovery escalates to quit; the log then says it was unresponsive that long."""
    quit_grace: float = 20.0
    """Seconds a running Word gets to quit on request before it is signalled.
    A Word with documents to close takes more than the 2 s this used to wait,
    and a SIGTERM on a Word that was quitting anyway leaves recovery files that
    come back as ghost documents on the next launch (seen 2026-10-14)."""
    launched_by_us: bool = False
    restarts: int = 0
    closes_documents: bool = True
    """The run's close policy, as `preflight` recorded it. The default closes
    every open document without asking (AGENTS.md: that is expected), so a Word
    that held documents at startup is still ours to restart. Only
    `--do-not-close` keeps the operator's documents, and only then is a
    `quit saving no` not ours to send."""
    started: float = field(default_factory=time.time)
    """Wall clock, because it is compared against file mtimes. Everything
    older than this belongs to someone else and is never deleted."""
    preflighted: bool = False
    """True only once `preflight` has actually asked Word how many documents
    it holds.

    `started_clean` defaults to True, which is a claim, not an observation: a
    session nobody preflighted asserts a clean Word without having looked. That
    was safe while every entry point ran `preflight` first, and stopped being
    safe the moment a caller could reach `redline_folders()` by importing the
    module. So ownership now needs both flags: this one says the question was
    put to Word, `started_clean` says what Word answered.
    """
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
        """How many documents Word holds, or **-1 when the question failed**.

        The -1 is not "none". It means the Apple event did not come back with a
        number -- Word is wedged, launching, or not answering -- and callers
        must treat it as unknown rather than empty. `preflight` refuses on it
        for exactly that reason: every close-all and every AutoRecovery sweep
        in this module rests on having *established* that Word was empty, and
        a failed query establishes nothing.
        """
        rc, out, _ = osa(_COUNT_DOCS, timeout=10)
        return int(out) if rc == 0 and out.isdigit() else -1

    def warm(self) -> bool:
        """Launch Word in the background and wait until it answers Apple events.

        `open -g` so the batch never takes the screen from whoever is using the
        machine, and the wait happens here so no per-document budget has to
        cover a ~30s cold start (§10).
        """
        # The process check comes first. An Apple event to a Word that is not
        # running launches it, so asking `responsive()` first launched Word and
        # then recorded it as "already running": `launched_by_us` was False in
        # every run on 2026-10-14, including ones that started with no Word at
        # all, and the flag gates both the restart policy and `quit_if_ours`.
        if self._alive():
            if self.responsive():
                return True
            logger.warning("[word] Word is running but not answering Apple events; waiting for it")
        else:
            self.launched_by_us = True
            logger.info(f"[word] launching Word in the background, running: {shown(_LAUNCH)}")
            subprocess.run(_LAUNCH, capture_output=True, check=False)
        started = time.monotonic()
        deadline = started + self.warm_timeout
        while time.monotonic() < deadline:
            if self.responsive():
                osa(_SET_ALERTS, "false", timeout=10)
                logger.info(f"[word] Word answered after {time.monotonic() - started:.0f} s; alerts off")
                return True
            time.sleep(2)
        logger.error(f"[word] Word did not answer within {self.warm_timeout:.0f} s")
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

    def recycle(self, *folders: Path, restart: bool = False, because: str = "") -> bool:
        """Close-all first; quit, SIGTERM, SIGKILL and relaunch only when that fails.

        `restart=True` skips the close-all: for a Word that answers and returns
        nothing (three empty loads in a row, 2026-10-14 22:22 and 22:45) the
        close-all succeeds on an empty Word and changes nothing, and the same
        degraded instance was reused 39 times. `because` is logged with the quit.

        `pkill -x` matches the process NAME. `-f` matches whole command lines and
        would also kill helper `osascript`s and any unrelated process whose
        arguments mention Word (§14.5).
        """
        if not self.started_clean and not self.closes_documents:
            # `recycle` quits Word `saving no`. Under --do-not-close the operator
            # keeps their documents, and discarding them is not ours to do. Under
            # the default policy the run closes every document anyway, so a Word
            # that held documents at startup is still ours to restart: refusing
            # here left a crashed, self-relaunched Word in place for 537 items
            # on 2026-10-14, every pass after it failing within seconds.
            logger.error(
                "[word] refusing to restart Word: it held documents at startup and "
                "--do-not-close keeps them, so a restart would discard them unsaved. "
                "Close them and re-run, or drop --do-not-close, to enable recovery."
            )
            return False

        self.restarts += 1
        n = self.restarts
        tag = f"[word] recovery {n}:"
        if not self._alive():
            # Word crashed (or was quit by something else). A `quit` AppleEvent to a
            # Word that is not running would launch it just to kill it again, and
            # that launch is what restores the crash's ghost documents.
            logger.warning(f"{tag} Word's process is gone (it crashed); relaunching it")
            self.clean_after_kill(*folders)
            return self.warm()

        # A running Word is first told to close every document (saving no: the
        # default policy). When that works and Word answers, that is the whole
        # recovery: no quit, no relaunch, settings kept. Only when the close-all
        # errors, or Word stays unresponsive after it, does it escalate. A
        # `restart` goes straight to the quit, saying why.
        if restart:
            why = f"because {because or 'a restart was asked for'}"
        else:
            logger.warning(f"{tag} Word is running (pid {word_pid()}); closing every document, running: {shown(_CLOSE_ALL)}")
            ok, detail = self._run_logged(tag, _CLOSE_ALL, timeout=30)
            if ok:
                waited = self._answers_within(self.answer_grace)
                if waited is not None:
                    logger.info(f"{tag} Word answers ({waited:.1f} s after the close-all); carrying on with the same Word")
                    return True
                why = f"because Word was unresponsive for {self.answer_grace:.0f} s after the close-all"
            else:
                why = f"because the close-all returned an error ({detail or 'no message'})"

        logger.warning(f"{tag} {why}; asking Word to quit, running: {shown(_QUIT)}")
        self._run_logged(tag, _QUIT, timeout=self.quit_grace + 5)
        if self._gone_within(self.quit_grace):
            logger.info(f"{tag} Word quit on request")
        else:
            term = ["pkill", "-x", WORD_PROC]
            logger.warning(f"{tag} Word did not quit within {self.quit_grace:.0f} s; running: {shown(term)}")
            self._run_logged(tag, term)
            if self._gone_within(5.0):
                logger.info(f"{tag} Word's process is gone after SIGTERM")
            else:
                kill = ["pkill", "-9", "-x", WORD_PROC]
                logger.warning(f"{tag} Word ignored SIGTERM; running: {shown(kill)}")
                self._run_logged(tag, kill)
                logger.info(f"{tag} Word's process is {'gone' if self._gone_within(3.0) else 'STILL THERE'} after SIGKILL")
        self.clean_after_kill(*folders)
        return self.warm()

    def _run_logged(
        self, tag: str, cmd: str | list[str], *args: str, timeout: float = 30.0
    ) -> tuple[bool, str]:
        """Run one recovery command and log its result on the very next line.

        Returns (returned 0, first line of its output or error). An AppleScript
        goes through `osa` with `args` as its argv; a list is a plain command
        (`pkill …`).
        """
        started = time.monotonic()
        if isinstance(cmd, str):
            rc, out, err = osa(cmd, *args, timeout=timeout)
        else:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            rc = getattr(proc, "returncode", None)
            out, err = (getattr(proc, "stdout", "") or ""), (getattr(proc, "stderr", "") or "")
        took = time.monotonic() - started
        first = _first_line
        if rc == 0:
            got = first(out)
            if got == "missing value":
                # osascript prints AppleScript's `missing value` when the
                # statement produced nothing to return (a `close` does not).
                detail, what = "", "no value came back (AppleScript 'missing value')"
            elif got:
                detail, what = got, f"got: {got}"
            elif first(err):
                detail, what = first(err), f"got (on stderr): {first(err)}"
            else:
                detail, what = "", "no output"
        else:
            detail = first(err) or first(out)
            what = f"error: {detail}" if detail else "no error text"
        line = f"{tag} returned rc={rc} in {took:.1f} s, {what}"
        (logger.info if rc == 0 else logger.warning)(line)
        return rc == 0, detail

    def _answers_within(self, seconds: float, step: float = 1.0) -> float | None:
        """Seconds until Word answered an Apple event, or None when it did not within `seconds`."""
        started = time.monotonic()
        for _ in range(int(seconds / step) + 1):
            if self.responsive():
                return time.monotonic() - started
            time.sleep(step)
        return None

    @staticmethod
    def _alive() -> bool:
        proc = subprocess.run(
            ["pgrep", "-x", WORD_PROC], capture_output=True, check=False
        )
        return getattr(proc, "returncode", None) == 0

    def _gone_within(self, seconds: float, step: float = 0.5) -> bool:
        """Poll until Word's process is gone; False when it is still there after `seconds`."""
        for _ in range(int(seconds / step) + 1):
            if not self._alive():
                return True
            time.sleep(step)
        return not self._alive()

    def quit_if_ours(self) -> None:
        """Quit the Word this run launched, and only when nothing is open.

        `launched_by_us` says the run started the *process*. It says nothing
        about the documents in it: a person can open one in that instance while
        the batch is running, and the close-all-then-quit this used to do
        discarded it unsaved. By the time this fires the run's own documents
        are already closed, so anything still open is either a cleanup that did
        not finish or someone else's — neither of which is ours to throw away.
        Leaving Word running costs nothing; the alternative costs their work.
        """
        if not self.launched_by_us:
            return
        count = self.open_document_count()
        if count != 0:
            logger.warning(
                f"[word] leaving Word running: {count} document(s) still open at "
                "exit, and this run cannot prove they are its own"
                if count > 0
                else "[word] leaving Word running: could not determine whether "
                "any documents are open"
            )
            return
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
    script = _EXPORT_PDF if _close_documents.get() else _EXPORT_PDF_KEEP_OPEN
    rc, _, err = osa(script, str(staged_docx), str(staged_pdf), timeout=timeout)
    produced = staged_pdf.exists() and staged_pdf.stat().st_size > 0
    if rc == 0 and produced:
        return True, ""
    return False, classify_failure(rc, err, produced)


# ─── malformed documents ─────────────────────────────────────────────────────


def decline_repair_prompt() -> list[tuple[str, str]]:
    """Answer a repair prompt that may be up after a failed export: No, then its OK.

    The serial path's export has already returned (errored or timed out) when this
    runs, so there is no watchdog race to lose: with focus allowed Word is brought
    forward for the OK, as the watchdog does; without it the No is pressed in place.
    Returns what was pressed, with the alert's words, and logs them.
    """
    if _focus.get():
        presses = answer_alert(NO_STEP, OK_STEP, wait=3.0)
    else:
        _, pressed, _ = osa(_PRESS, WORD_PROC, NO_STEP, timeout=10)
        presses = [(pressed, "")] if pressed else []
    for button, text in presses:
        logger.warning(f"[word] after the failure, pressed {button!r}; {_said(text)}")
    return presses


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
    later open, with no error at all (§5.20): one poison file cost 203 others.
    The paragraph-count check on every open is what catches that, and a Word that
    cannot be brought back to zero open documents is assumed to be in it.

    The default policy closes every document, saving no, whoever opened Word
    and whatever it held at startup; the command and what came back are logged
    on consecutive lines. Only `--do-not-close` closes by name, because there
    the operator keeps their documents.
    """
    decline_repair_prompt()
    tag = "[word] after the failure:"
    if not session.closes_documents:
        if only:
            logger.warning(
                f"{tag} --do-not-close keeps the other documents, so closing only "
                f"'{only}', running: {shown(_CLOSE_NAMED, only)}"
            )
            session._run_logged(tag, _CLOSE_NAMED, only, timeout=20)
        else:
            logger.warning(f"{tag} --do-not-close and no document name to close; leaving Word as it is")
        return True

    logger.warning(f"{tag} closing every document, running: {shown(_CLOSE_ALL)}")
    ok, detail = session._run_logged(tag, _CLOSE_ALL, timeout=20)
    if ok:
        count = session.open_document_count()
        if count == 0:
            logger.info(f"{tag} Word answers and holds no document; carrying on with the same Word")
            return True
        why = (
            f"Word still holds {count} document(s)"
            if count > 0
            else "Word did not answer the document count"
        )
    else:
        why = f"the close-all returned an error ({detail or 'no message'})"
    logger.warning(f"{tag} {why} after the close-all; recycling")
    return session.recycle(*folders)


def labelled(name: str) -> str:
    """`name` with the run's label in front, when the run has one."""
    label = _stage_label.get()
    return f"{label}__{name}" if label else name


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
    # every `[retry]` item with its message, and the subset Word died on
    retried: dict[str, str] = field(default_factory=dict)
    crashed: dict[str, str] = field(default_factory=dict)
    # staged file names whose repair prompt the watchdog declined
    declined: set[str] = field(default_factory=set)
    # items the script skipped because they share a file with one that failed earlier in
    # the pass (`[defer]`): never reached, so they run in the next pass, at the back
    deferred: set[str] = field(default_factory=set)


_CRASH_MARKS = ("Connection is invalid", "isn't running", "isn’t running")


def parse_batch_log(text: str) -> BatchLog:
    """Read a batch script's append-only log.

    Only `[ok]`, `[fail]`, `[retry]` and `[done]` lines are read; anything else is
    ignored, which is what makes an error message containing a newline harmless.
    An item with no line at all was never reached — the run died before it — and
    that is the difference between "failed" and "retry in the next pass". A
    `[retry]` is never a result; one for a dropped connection names the item Word
    died on (`crashed`), while an empty load is poison from an earlier item.
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
        elif head == "[retry]" and len(fields) >= 2:
            detail = "\t".join(fields[2:]).strip()
            log.retried[fields[1]] = detail
            if any(mark in detail for mark in _CRASH_MARKS):
                log.crashed[fields[1]] = detail
        elif head == "[declined]" and len(fields) >= 2 and fields[1]:
            log.declined.add(fields[1])
        elif head == "[defer]" and len(fields) >= 2:
            log.deferred.add(fields[1])
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


DIAGNOSTIC_REPORTS = Path.home() / "Library/Logs/DiagnosticReports"
_STALL_PROBES = (
    ("Word windows {name, subrole}",
     'tell application "System Events" to tell process "Microsoft Word" to get {name, subrole} of every window'),
    # A modal's own name is usually empty; its text is what says what it is
    # ("Word found unreadable content in ...").
    ("Word window text",
     'tell application "System Events" to tell process "Microsoft Word" to get value of every static text of every window'),
    ("crash reporters",
     'tell application "System Events" to get name of every process whose name contains "Error Reporting" or name contains "Crash"'),
)


def stall_report(log_path: Path, *, diagnostic_reports: Path = DIAGNOSTIC_REPORTS) -> str:
    """What Word is doing while an item sits in the batch: its windows and their
    text, any crash reporter, the batch log so far, the newest diagnostic reports."""
    parts = []
    for title, script in _STALL_PROBES:
        _, out, err = osa(script, timeout=10)
        parts.append(f"-- {title}: {(out or err).strip()}")
    try:
        log = log_path.read_text(errors="replace").strip()
    except OSError as exc:
        log = str(exc)
    parts.append(f"-- {log_path.name}:\n{log}")
    try:
        newest = sorted(diagnostic_reports.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        parts.append("-- newest diagnostic reports: " + ", ".join(p.name for p in newest))
    except OSError as exc:
        parts.append(f"-- diagnostic reports: {exc}")
    return "\n".join(parts)


@dataclass
class _Progress:
    """Tail a batch log so a long monolithic run is not silent.

    A batch script is one blocking `osascript`, so its own `logLine` calls are
    the only signal available while it runs. An item still open after
    `stall_after` seconds gets one `diagnose` report (logged, nothing pressed or
    killed); the next item that stalls gets its own.

    It also checks on an item Word opened and has not finished. Word may not
    draw its repair prompt, or the OK after it, until it is frontmost, so an
    item with no `[ok]`/`[fail]`/`[retry]` line after `nudge_after` seconds
    brings Word forward to press No (then its OK) or a lone OK, and again every
    `nudge_every` seconds while that item stays open (`focus` only). A document
    that is merely slow costs `nudge_wait` seconds of focus per check, which is
    why the thresholds are above what a large document takes to open and save,
    and nothing is pressed unless an alert is actually there. The check and the
    stall report each run on their own thread: their osascript probes can take
    tens of seconds while Word is busy, and the clock must not wait on them.
    """

    log_path: Path
    total: int
    label: str = ""
    poll: float = 5.0
    stall_after: float = 30.0
    diagnose: Callable[[Path], str] = stall_report
    focus: bool = field(default_factory=lambda: _focus.get())
    nudge_after: float = 10.0
    nudge_every: float = 15.0
    nudge_wait: float = 2.0
    nudges: int = 0
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None
    _busy: threading.Lock = field(default_factory=threading.Lock)

    def _finished(self) -> int:
        """Items with an [ok]/[fail]/[retry] line in the batch log right now."""
        try:
            lines = self.log_path.read_text(errors="replace").splitlines()
        except OSError:
            return -1
        return sum(1 for ln in lines if ln.startswith(("[ok]", "[fail]", "[retry]")))

    def _report(self, item: int, since: float) -> None:
        # The probes can take tens of seconds (System Events waits on a busy
        # Word), so what they describe may be stale by the time they return.
        # Re-read the log before saying anything: an item that finished in the
        # meantime was slow, not stuck, and its diagnostics would mislead.
        open_for = time.monotonic() - since
        report = self.diagnose(self.log_path)
        finished = self._finished()
        if finished >= item:
            logger.info(
                f"[batch{self.label}] item {item}/{self.total} finished while I was looking "
                f"({finished} done now; it had been open {open_for:.0f} s when the probes "
                f"started, which took {time.monotonic() - since - open_for:.0f} s); "
                "nothing is stuck, report dropped"
            )
            return
        logger.warning(
            f"[batch{self.label}] item {item}/{self.total} open for more than "
            f"{self.stall_after:.0f} s:\n{report}"
        )

    def _nudge(self, item: int, open_for: float) -> None:
        # One check at a time; a check still running when the next is due is skipped.
        if not self._busy.acquire(blocking=False):
            return
        try:
            self.nudges += 1
            logger.info(
                f"[focus] item {item}/{self.total} not finished after {open_for:.0f} s; "
                "bringing Word forward to look for an alert"
            )
            presses = answer_alert(f"{NO_STEP}|{OK_STEP}", OK_STEP, wait=self.nudge_wait, skip_if_busy=True)
            if presses:
                how = " then ".join(repr(b) for b, _ in presses)
                text = next((t for _, t in presses if t), "")
                logger.warning(f"[focus] item {item}/{self.total}: pressed {how} with Word brought forward; {_said(text)}")
                if any(b == NO_STEP for b, _ in presses):
                    mark_declined(declined_file(text))
        finally:
            self._busy.release()

    def _loop(self) -> None:
        # One clock for both checks, restarted by any [ok]/[fail]/[retry] line
        # (progress counts only [ok]/[fail]).
        seen = ended = -1
        item_since = time.monotonic()
        nudge_at = item_since + self.nudge_after
        probed = False
        while not self._stop.wait(self.poll):
            try:
                text = self.log_path.read_text(errors="replace")
            except OSError:
                text = None
            if text is not None:
                lines = text.splitlines()
                count = sum(1 for ln in lines if ln.startswith(("[ok]", "[fail]")))
                if count != seen:
                    seen = count
                    logger.info(f"[batch{self.label}] {count}/{self.total}")
                finished = sum(1 for ln in lines if ln.startswith(("[ok]", "[fail]", "[retry]")))
                if finished != ended:
                    ended = finished
                    item_since = time.monotonic()
                    nudge_at = item_since + self.nudge_after
                    probed = False
            item = max(ended, 0) + 1
            now = time.monotonic()
            if not probed and now - item_since > self.stall_after:
                probed = True
                threading.Thread(target=self._report, args=(item, item_since), daemon=True).start()
            if self.focus and now >= nudge_at:
                nudge_at = now + self.nudge_every
                threading.Thread(target=self._nudge, args=(item, now - item_since), daemon=True).start()

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
    # One name per pass and stage ("batch-compare-2"), so a later pass does not
    # overwrite the log that records how far an earlier one got.
    name = "-".join(["batch", *re.findall(r"[A-Za-z0-9]+", label)])
    manifest = write_manifest(rows, work_dir / f"{name}.tsv")
    log_path = work_dir / f"{name}.log"
    log_path.write_text("", encoding="utf-8")
    global _BATCH_LOG
    _BATCH_LOG = log_path
    try:
        with _Progress(log_path, len(rows), label):
            rc, _, err = osa(script, str(manifest), str(log_path), timeout=timeout)
    finally:
        _BATCH_LOG = None
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
    crash_limit: int = 2,
    label: str = "",
    groups: dict[str, frozenset[str]] | None = None,
) -> dict[str, tuple[bool, str]]:
    """Run a batch script, retrying only the items it never reached.

    Four outcomes per item, and they are not interchangeable:

    - `[ok]` / `[fail]` — the script reached it and said so. Final either way; a
      malformed document is not retried, because it will be malformed next pass
      too.
    - **no line at all** — the run died before getting there. That is the only
      case worth another pass, and it gets one after Word is recycled.
    - **`[retry]`** — Word died on it (`crashed`) or it loaded empty (poison from
      an earlier file). It is retried after Word is recycled, and after
      `crash_limit` such passes it is a final failure. An empty load whose repair
      prompt the watchdog declined (`[declined]`) is the file's own fault and is
      final at once; the batch script fails it itself when the marker was there
      in time, and this closes the gap when it was not.
    - **the item a wedged pass stopped on** (the first one without a line when
      the run never reached `[done]`) is retried too.

    Every retried item goes to the back of the next manifest, so one bad file no
    longer leads every pass while the rest of the folder waits behind it. A pass
    that logged a `[retry]` named its culprit and made progress; only the other
    passes spend `max_passes`.

    Items already recorded are dropped from the next manifest, so a wedge costs
    the remainder of one pass rather than the whole batch.

    `groups` maps an item to the files it is made of (a redline pair: its base
    and its revision). When an item fails or crashes Word, every pending item
    that shares a file with it is sent to the back too, and a script that
    skipped such siblings itself (`[defer]`) hands them to the next pass without
    a Word restart: a pass that finished, with nothing crashed, timed out or
    wedged, is not a sick Word, only a queue to reorder. With thousands of pairs
    to choose from, a bad file should cost the batch its own pair, not every
    pair it appears in, and not a restart per pair.
    """
    final: dict[str, tuple[bool, str]] = {}
    retries: dict[str, int] = {}  # [retry] lines per item, capped by crash_limit
    moved: dict[str, int] = {}  # times an item was sent to the back
    pending = list(rows)
    attempt = stalls = 0
    while pending and stalls < max_passes:
        attempt += 1
        run = run_batch(
            script,
            pending,
            work_dir,
            timeout=batch_timeout(per_item_timeout, len(pending)),
            label=f"{label} {attempt}",
        )
        still: list[tuple[str, ...]] = []
        named = False
        bad_keys: set[str] = set()  # files of the items that failed or crashed this pass
        for row in pending:
            rid = row[0]
            recorded = run.log.results.get(rid)
            declined = len(row) > 1 and Path(row[1]).name in run.log.declined
            if recorded is not None:
                ok, detail = recorded
                if not ok and declined and "new documents" in detail:
                    # The open came back empty before the watchdog's marker landed
                    # (seen 7 times in 10 on 2026-10-14): same final verdict, right reason.
                    recorded = (False, f"repair prompt declined; Word could not read it ({detail})")
                if not ok and groups:
                    bad_keys |= groups.get(rid, frozenset())
                final[rid] = recorded
                continue
            if rid in run.log.retried and declined:
                # The watchdog declined this file's repair prompt, so the empty load
                # is the file's, not Word's: final, no retry, and no recycle for it.
                final[rid] = (False, f"repair prompt declined; Word could not read it: {run.log.retried[rid]}")
                continue
            if rid in run.log.retried:
                named = True
                moved[rid] = moved.get(rid, 0) + 1
                retries[rid] = retries.get(rid, 0) + 1
                if groups:
                    bad_keys |= groups.get(rid, frozenset())
                if retries[rid] >= crash_limit:
                    what = "Word crashed on it" if rid in run.log.crashed else "Word could not load it"
                    final[rid] = (False, f"{what} in {retries[rid]} passes: {run.log.retried[rid]}")
                    continue
            still.append(row)
        if run.wedged and not named and still:
            stuck = still[0][0]  # the first item without a line: where the run hung
            moved[stuck] = moved.get(stuck, 0) + 1
        if groups and bad_keys:
            siblings = [r[0] for r in still if groups.get(r[0], frozenset()) & bad_keys]
            for rid in siblings:
                moved[rid] = moved.get(rid, 0) + 1
            if siblings:
                logger.info(
                    f"[batch{label}] {len(siblings)} item(s) share a file with one that failed; "
                    "sent to the back"
                )
        pending = sorted(still, key=lambda r: moved.get(r[0], 0))
        timed_out = any(not ok and "timed out" in detail for ok, detail in run.log.results.values())
        deferred_only = (
            bool(pending)
            and not named
            and not run.wedged
            and not timed_out
            and all(r[0] in run.log.deferred for r in pending)
        )
        if deferred_only:
            # The script finished and skipped these itself, behind a failing file. Word
            # answered everything it was asked: nothing to restart, nothing stalled.
            logger.info(
                f"[batch{label}] {len(pending)} item(s) deferred behind a failed file; "
                f"next pass without restarting Word (pass {attempt + 1})"
            )
            continue
        if not named:
            stalls += 1
        if pending:
            if named:
                culprits = [rid for rid in run.log.retried if rid in {r[0] for r in rows}]
                detail = "; ".join(
                    f"item {rid}: {run.log.retried[rid]} ({'Word crashed' if rid in run.log.crashed else 'loaded empty'})"
                    for rid in culprits[-3:]
                )
                why = f"ended at {detail}"
            elif run.wedged:
                why = f"wedged before [done] (osascript rc={run.returncode}, {run.stderr.strip()[:120] or 'no stderr'})"
            elif timed_out:
                why = "ended after an AppleEvent timeout, which leaves Word returning empty documents (§5.20)"
            else:
                why = "ended without reaching them"
            to_retry = sum(1 for r in pending if r[0] in run.log.retried)
            logger.warning(
                f"[batch{label}] pass {attempt} {why}; {len(pending) - to_retry} item(s) not reached, "
                f"{to_retry} to retry. Recovering Word (see the [word] line), then pass {attempt + 1} "
                f"runs them, retried items last ({stalls} of {max_passes} stalled passes used)"
            )
            empty = [rid for rid in run.log.retried if rid not in run.log.crashed]
            if named and not run.log.crashed and empty:
                # Word answered every item and returned nothing: a modal System
                # Events cannot see from the background (2026-10-14 23:00: another
                # driver's repair prompt), or the degraded instance of §5.20. One
                # look with Word brought forward, then a restart: a close-all on
                # an empty Word succeeds and fixes nothing.
                logger.warning(
                    f"[batch{label}] Word returned nothing for {len(empty)} document(s) in a row; "
                    "bringing it forward once to look for a modal, then restarting it"
                )
                seen = decline_repair_prompt()
                if seen:
                    logger.warning(f"[batch{label}] found and answered: {seen}")
                session.recycle(
                    *recycle_paths, restart=True,
                    because=f"Word returned nothing for {len(empty)} document(s) in a row (it answers, but opens nothing)",
                )
            else:
                session.recycle(*recycle_paths)
    for row in pending:
        final[row[0]] = (False, f"never reached in {max_passes} batch pass(es)")
    return final


# One osascript for the whole folder. The per-document
# `try … on error … close theDoc saving no … end try` IS the malformed-document
# contract: answer nothing, close what is open, record it, move to the next
# file. By default every document is closed before each open and after each
# save (never Word itself), because a leftover document is what got saved under
# the next file's name after a dropped connection; open documents are closed
# without a prompt. `_EXPORT_BATCH_KEEP_OPEN` (`--do-not-close`) closes only
# `theDoc`, and `preflight` refuses that mode while Word holds documents.
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

on restoreAlerts(priorAlerts)
  if priorAlerts is missing value then return
  try
    tell application "Microsoft Word" to set displayAlerts to priorAlerts
  end try
end restoreAlerts

on baseName(p)
  set od to AppleScript's text item delimiters
  set AppleScript's text item delimiters to "/"
  set parts to text items of p
  set AppleScript's text item delimiters to od
  return item -1 of parts
end baseName

-- The watchdog appends "[declined]<tab><file>" to the log when it answers the repair
-- prompt for a file. An empty load of that file is the file's fault, a final [fail];
-- an empty load with no such line is Word's poison and still counts toward the streak.
on wasDeclined(logPath, p)
  try
    set logText to read POSIX file logPath as «class utf8»
    return logText contains ("[declined]" & tab & my baseName(p))
  end try
  return false
end wasDeclined

on run argv
  set manifestPath to item 1 of argv
  set logPath to item 2 of argv
  set rows to paragraphs of (read POSIX file manifestPath)
  set priorAlerts to missing value
  tell application "Microsoft Word"
    try
      set priorAlerts to displayAlerts
    end try
    set displayAlerts to false
  end tell
  set okCount to 0
  set failCount to 0
  set emptyStreak to 0
  try
    repeat with r in rows
      set rowText to r as string
      if rowText is not "" then
        set f to my splitTabs(rowText)
        if (count of f) is 3 then
          set itemId to item 1 of f
          set inP to item 2 of f
          set outP to item 3 of f
          set wantName to my baseName(inP)
          set theDoc to missing value
          try
            with timeout of __AE_TIMEOUT__ seconds
              tell application "Microsoft Word"
                set theDoc to missing value
                close every document saving no
                set seenBeforeOpen to {}
                repeat with i from 1 to (count of documents)
                  set end of seenBeforeOpen to name of document i
                end repeat
                open POSIX file inP
                -- The document is the NEW one NAMED after the file, never `document 1`
                -- (§5.18). A document that survived the close-all was saved under a
                -- broken file's name when that file's open produced nothing, and a ghost
                -- whose name reads as missing value before the open shows up as
                -- "Document1" after it, so "the one new document" is not enough either
                -- (both seen live 2026-10-14).
                set newCount to 0
                repeat with i from 1 to (count of documents)
                  set nm to missing value
                  try
                    set nm to name of document i
                  end try
                  if seenBeforeOpen does not contain nm then
                    set newCount to newCount + 1
                    if (nm as string) is wantName then set theDoc to document i
                  end if
                end repeat
                if theDoc is missing value then
                  repeat with i from (count of documents) to 1 by -1
                    try
                      if (name of document i as string) is wantName then close document i saving no
                    end try
                  end repeat
                  error "open produced " & newCount & " new documents, none named " & wantName & "; refusing to guess"
                end if
                if (count of paragraphs of theDoc) is 0 then
                  close every document saving no
                  set theDoc to missing value
                  error "document loaded empty (Word could not read it)"
                end if
                save as theDoc file name outP file format format PDF
                close every document saving no
                set theDoc to missing value
              end tell
            end timeout
            set emptyStreak to 0
            set okCount to okCount + 1
            my logLine(logPath, "[ok]" & tab & itemId)
          on error errMsg
            try
              tell application "Microsoft Word" to close every document saving no
            end try
            -- A timeout leaves Word returning empty documents for later opens
            -- (§5.20). Record that file as a final failure and stop, so the
            -- tail is retried after a recycle and this file is not first again.
            -- Three empty loads in a row is the same poison when the timeout was
            -- in a previous process. [retry] is not a [fail]: the parser ignores
            -- it, so those rows are retried instead of frozen.
            if errMsg contains "timed out" then
              set failCount to failCount + 1
              my logLine(logPath, "[fail]" & tab & itemId & tab & errMsg)
              exit repeat
            else if errMsg contains "Connection is invalid" or errMsg contains "isn't running" or errMsg contains ("isn" & (character id 8217) & "t running") then
              my logLine(logPath, "[retry]" & tab & itemId & tab & errMsg)
              exit repeat
            else if errMsg contains "loaded empty" or errMsg contains "new documents" or errMsg contains "understand" then
              -- Word answered and gave nothing: an empty load, an open that produced no
              -- document, or an AppleEvent it "doesn't understand". A declined repair
              -- prompt makes it the file's fault; otherwise it is Word's state (2026-10-14
              -- 22:22: a relaunched Word did this for 70 documents in 5 s), so the item
              -- is retried and three in a row end the pass for a recycle.
              if my wasDeclined(logPath, inP) then
                set emptyStreak to 0
                set failCount to failCount + 1
                my logLine(logPath, "[fail]" & tab & itemId & tab & "repair prompt declined; Word could not read it")
              else
                set emptyStreak to emptyStreak + 1
                my logLine(logPath, "[retry]" & tab & itemId & tab & errMsg)
                if emptyStreak ≥ 3 then exit repeat
              end if
            else
              set emptyStreak to 0
              set failCount to failCount + 1
              my logLine(logPath, "[fail]" & tab & itemId & tab & errMsg)
            end if
          end try
        end if
      end if
    end repeat
  on error errText
    my restoreAlerts(priorAlerts)
    error errText
  end try
  my restoreAlerts(priorAlerts)
  my logLine(logPath, "[done]" & tab & okCount & tab & failCount)
  return "ok=" & okCount & " fail=" & failCount
end run
""".strip()

# `--do-not-close` closes only the document this batch opened.
_EXPORT_BATCH = _EXPORT_BATCH.replace("__AE_TIMEOUT__", str(APPLE_EVENT_TIMEOUT))

_EXPORT_BATCH_KEEP_OPEN = _EXPORT_BATCH.replace(
    "close every document saving no",
    "if theDoc is not missing value then close theDoc saving no",
)

# `--accept-all`: Word's own Accept All Changes, the result saved as docx and the
# same open document then exported as PDF, so the PDF is the render of the docx
# delivered next to it. Rows carry a fourth field, the docx path. `--reject-all`
# is the same batch with Word's Reject All Changes in place of the accept.
ACCEPT_SUFFIX = "_accepted_tracking"
REJECT_SUFFIX = "_rejected_tracking"
_ACCEPT_EDITS = (
    ("if (count of f) is 3 then", "if (count of f) is 4 then"),
    ("set outP to item 3 of f", "set outP to item 3 of f\n          set docxP to item 4 of f"),
    (
        "                save as theDoc file name outP file format format PDF",
        "                accept all revisions theDoc\n"
        "                save as theDoc file name docxP file format format document\n"
        "                set theDoc to document (my baseName(docxP))\n"
        "                save as theDoc file name outP file format format PDF",
    ),
)


def batch_script(*, close_documents: bool, accept: bool, reject: bool = False) -> str:
    """The monolithic batch AppleScript for the chosen close policy.

    `accept` resolves every tracked change before the docx + PDF are saved:
    Word's Accept All, or its Reject All when `reject` is set too.
    """
    script = _EXPORT_BATCH if close_documents else _EXPORT_BATCH_KEEP_OPEN
    if not accept:
        return script
    for old, new in _ACCEPT_EDITS:
        if reject:
            new = new.replace("accept all revisions", "reject all revisions")
        if script.count(old) != 1:
            raise RuntimeError(f"accept-all edit does not apply to the batch script: {old!r}")
        script = script.replace(old, new)
    return script


def accepted_paths_for(docx: Path, out_dir: Path | None, suffix: str) -> tuple[Path, Path]:
    """The accepted docx and its PDF: `<stem><suffix>_byword.docx|.pdf` in `out_dir` (default beside it)."""
    folder = out_dir or docx.parent
    stem = by_tool(f"{docx.stem}{suffix}")
    return folder / f"{stem}.docx", folder / f"{stem}.pdf"


def publish(staged: Path, final: Path) -> str:
    """Put one finished artifact at `final`, whole or not at all. '' on success.

    `shutil.move` and `copy2` write the destination in place, so a copy that
    dies partway (a full disk, a vanished network share) truncates whatever
    result was already there, and the staging directory holding the good copy
    is removed with the run. This copies beside the destination first and
    `os.replace`s it in, which is atomic within one filesystem. The staged file
    is left for the stage to clean up. A failure is returned as that item's
    error, never raised: one undeliverable file is not a reason to stop a batch.
    """
    temp = final.with_name(f".{final.name}.{os.getpid()}.part")
    try:
        final.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(staged, temp)
        os.replace(temp, final)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        return f"could not deliver {final.name}: {exc}"
    return ""


def convert_folder(
    src: Path,
    out_dir: Path | None,
    *,
    force: bool = False,
    timeout: float = 180.0,
    session: WordSession | None = None,
    stage: Stage | None = None,
    one_osascript: bool = True,
    close_documents: bool = True,
    max_passes: int = 3,
    poison_streak: int = 3,
    accept_suffix: str = "",
    reject: bool = False,
    label: str = "",
    crash_limit: int = 2,
    lock_wait: float = 900.0,
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

    `accept_suffix` turns on accept-all: Word accepts every tracked change and
    the result lands as `<stem><suffix>.docx` with its PDF `<stem><suffix>.pdf`.
    Only the batch path does this. `reject` makes it Word's Reject All
    instead; it needs the suffix too.

    `crash_limit` is how many passes a file that crashes Word (or loads empty
    without a declined repair prompt) gets before it is a final failure; each
    one costs a Word restart. 2 tells a bad file from a bad Word; 1 is for a
    corpus already known to crash it.

    `lock_wait` is how long to wait for another driver that holds Word
    (`WordLock`); when it does not let go, every document is reported as not
    attempted, with the holder named, rather than run against a Word that is
    closing and restarting under someone else.
    """
    require_positive_seconds(timeout, "timeout")
    if crash_limit < 1:
        raise ValueError("crash_limit must be at least 1")
    if reject and not accept_suffix:
        raise ValueError("reject-all needs an output suffix (accept_suffix)")
    if accept_suffix and not one_osascript:
        raise ValueError("accept-all runs only in the batch path (one_osascript=True)")
    if label and not _LABEL.fullmatch(label):
        raise ValueError("label takes letters, digits, '.', '_' and '-' only: it goes into a file name")
    docs = iter_docx(src)
    if not docs:
        logger.warning(f"no .docx in {src} (lock files excluded)")
        return []
    # First thing, before Word sees a name: file names over NAME_LIMIT are
    # trimmed on disk, and every rename goes into the manifest.
    manifest = manifest_path_for(out_dir, src)
    docs = trim_long_names(docs, manifest)

    owns_session = session is None
    owns_stage = stage is None
    session = session or WordSession()

    # The API is held to the CLI's check. `started_clean` defaults to True, so
    # a bare session claims a clean Word nobody asked, and recovery trusts that
    # claim before a close-all or a recycle (`quit saving no`). A session we
    # create is preflighted here; one we are handed must show it was.
    if owns_session:
        problem = preflight(
            session,
            allow_open_docs=False,
            one_osascript=one_osascript,
            close_documents=close_documents,
        )
    elif not session.preflighted:
        problem = (
            "this session has not been preflighted, so nothing has established "
            "what Word holds. Call preflight() first, or pass session=None and "
            "let convert_folder() do it."
        )
    else:
        problem = ""
    if problem:
        logger.error(f"[word] {problem}")
        return [Result(source=d, error=problem) for d in docs]

    lock = WordLock(label=f"word_pdf.py {src}", wait=lock_wait)
    try:
        lock.__enter__()
    except WordBusy as busy:
        logger.error(f"[word] {busy}; nothing attempted")
        return [Result(source=d, error=f"{busy}; not attempted") for d in docs]

    ctx = Stage(prefix="wordpdf") if owns_stage else None
    stage = stage or (ctx.__enter__() if ctx else None)
    assert stage is not None
    labelling = _stage_label.set(label)
    try:
        run = (
            partial(_convert_batched, accept_suffix=accept_suffix, reject=reject)
            if one_osascript
            else _convert_serial
        )
        logger.info(
            f"[word] export: one_osascript={one_osascript} documents={len(docs)} "
            f"accept_all={bool(accept_suffix) and not reject} reject_all={reject}"
        )
        results = run(
            docs,
            out_dir,
            src,
            stage=stage,
            session=session,
            force=force,
            timeout=timeout,
            max_passes=max_passes,
            poison_streak=poison_streak,
            close_documents=close_documents,
            crash_limit=crash_limit,
        )
        kind = "reject_all" if reject else "accept_all" if accept_suffix else "pdf"
        n = append_manifest(manifest, manifest_lines(results, kind=kind))
        logger.info(f"[manifest] appended {n} line(s) to {manifest}")
        return results
    finally:
        _stage_label.reset(labelling)
        if ctx:
            ctx.__exit__(None, None, None)
        if owns_session:
            session.quit_if_ours()
        lock.__exit__(None, None, None)


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
    close_documents: bool = True,
    crash_limit: int = 2,  # part of the shared dispatch signature; batch-only
) -> list[Result]:
    """One `osascript` per document, with the malformed-document path in Python."""
    results: list[Result] = []
    streak: list[Path] = []
    for i, docx in enumerate(docs, 1):
        final_pdf = pdf_path_for(docx, out_dir)
        found = None if force else existing_output(final_pdf)
        if found is not None:
            results.append(Result(source=docx, output=found, ok=True, skipped=True))
            logger.debug(f"[{i}/{len(docs)}] skip (exists): {docx.name} -> {found.name}")
            continue

        started = time.monotonic()
        staged_in = stage.place_as(docx, labelled(docx.name))
        staged_out = stage.outbox / final_pdf.name
        token = _close_documents.set(close_documents)
        try:
            ok, err = export_pdf(staged_in, staged_out, timeout=timeout)
        finally:
            _close_documents.reset(token)
        elapsed = time.monotonic() - started

        if ok:
            # Word did its part, so a delivery failure is not a poison signal:
            # it is recorded against the file and Word is left alone.
            streak.clear()
            undelivered = publish(staged_out, final_pdf)
            staged_out.unlink(missing_ok=True)
            if undelivered:
                results.append(Result(source=docx, error=undelivered, seconds=elapsed))
                logger.error(f"[{i}/{len(docs)}] FAIL: {docx.name} — {undelivered}")
            else:
                results.append(
                    Result(source=docx, output=final_pdf, ok=True, seconds=elapsed)
                )
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
                # after it (§5.20), which is what a failure run looks like.
                logger.warning(
                    f"[word] {len(streak)} failures in a row — recycling rather than "
                    "trusting Word to still be reading documents"
                )
                if session.recycle(stage.inbox, stage.outbox):
                    _replay(
                        streak,
                        results,
                        out_dir=out_dir,
                        stage=stage,
                        timeout=timeout,
                        close_documents=close_documents,
                    )
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
    close_documents: bool = True,
) -> None:
    """Re-run a failure streak against a freshly restarted Word, in place.

    The streak is why we restarted: a Word degraded by one bad document answers
    normally and returns empty documents for everything after it (§5.20). The
    paragraph-count check turns those into failures rather than false passes,
    which is the half that matters — but they are failures of *Word*, and
    nothing in a `[fail]` distinguishes them from a genuinely malformed file.
    Leaving them would report healthy documents as permanently broken.

    So the streak gets one attempt against the fresh Word. Whatever fails again
    is the file's own fault and keeps its original verdict.
    """
    for docx in docs:
        final_pdf = pdf_path_for(docx, out_dir)
        staged_in = stage.place_as(docx, labelled(docx.name))
        staged_out = stage.outbox / final_pdf.name
        started = time.monotonic()
        token = _close_documents.set(close_documents)
        try:
            ok, err = export_pdf(staged_in, staged_out, timeout=timeout)
        finally:
            _close_documents.reset(token)
        elapsed = time.monotonic() - started
        staged_in.unlink(missing_ok=True)
        if not ok:
            staged_out.unlink(missing_ok=True)
            logger.info(f"[replay] still failing, so it is the file: {docx.name} — {err}")
            continue
        undelivered = publish(staged_out, final_pdf)
        staged_out.unlink(missing_ok=True)
        if undelivered:
            logger.error(f"[replay] converted but {undelivered}")
            continue
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
    close_documents: bool = True,
    accept_suffix: str = "",
    reject: bool = False,
    crash_limit: int = 2,
) -> list[Result]:
    """One monolithic AppleScript for the whole folder, resumed if it dies.

    Every input is staged before the run starts, because the manifest references
    all of them at once — that is inherent to a single-script batch, and it is
    the mode's real cost: N copies live in the container until the run ends.
    """
    def finals(doc: Path) -> tuple[Path, Path | None]:
        if accept_suffix:
            docx_out, pdf_out = accepted_paths_for(doc, out_dir, accept_suffix)
            return pdf_out, docx_out
        return pdf_path_for(doc, out_dir), None

    outcomes: dict[Path, Result] = {}
    todo: list[Path] = []
    for doc in docs:
        final, final_docx = finals(doc)
        wanted = [p for p in (final, final_docx) if p is not None]
        found = [] if force else [f for f in map(existing_output, wanted) if f is not None]
        if found and len(found) == len(wanted):
            outcomes[doc] = Result(
                source=doc, output=found[0], also=tuple(found[1:]), ok=True, skipped=True
            )
        else:
            todo.append(doc)
    if not todo:
        return [outcomes[doc] for doc in docs]

    rows: list[tuple[str, ...]] = []
    staged: dict[str, tuple[Path, Path, Path, Path | None]] = {}
    for i, doc in enumerate(todo):
        item = str(i)
        staged_in = stage.place_as(doc, safe_stage_name(i, labelled(doc.name)))
        staged_out = stage.outbox / f"{safe_stage_name(i, doc.stem)}.pdf"
        staged_docx = stage.outbox / f"{safe_stage_name(i, doc.stem)}.docx" if accept_suffix else None
        rows.append((item, str(staged_in), str(staged_out), *([str(staged_docx)] if staged_docx else [])))
        staged[item] = (doc, staged_in, staged_out, staged_docx)

    logger.info(f"[batch] one osascript for {len(rows)} document(s)")
    started = time.monotonic()
    recorded = run_batch_with_resume(
        batch_script(close_documents=close_documents, accept=bool(accept_suffix), reject=reject),
        rows,
        stage.root or stage.inbox.parent,
        per_item_timeout=timeout,
        session=session,
        recycle_paths=(stage.inbox, stage.outbox),
        max_passes=max_passes,
        crash_limit=crash_limit,
        label=" pdf",
    )
    per_item = (time.monotonic() - started) / max(1, len(rows))

    for item, (doc, staged_in, staged_out, staged_docx) in staged.items():
        staged_in.unlink(missing_ok=True)
        ok, detail = recorded[item]
        produced = all(p.exists() and p.stat().st_size > 0 for p in (staged_out, staged_docx) if p is not None)
        undelivered = ""
        final, final_docx = finals(doc)
        if ok and produced:
            if staged_docx is not None and final_docx is not None:
                undelivered = publish(staged_docx, final_docx)
                staged_docx.unlink(missing_ok=True)
            undelivered = undelivered or publish(staged_out, final)
            staged_out.unlink(missing_ok=True)
        if undelivered:
            outcomes[doc] = Result(
                source=doc, error=undelivered, seconds=per_item, timing_exact=False
            )
            logger.error(f"[batch] FAIL: {doc.name} — {undelivered}")
        elif ok and produced:
            outcomes[doc] = Result(
                source=doc,
                output=final,
                also=(final_docx,) if final_docx is not None else (),
                ok=True,
                seconds=per_item,
                timing_exact=False,
            )
        else:
            outcomes[doc] = Result(
                source=doc,
                error=classify_failure(0 if ok else 1, detail, produced),
                seconds=per_item,
                timing_exact=False,
            )
            staged_out.unlink(missing_ok=True)
            if staged_docx is not None:
                staged_docx.unlink(missing_ok=True)
            logger.error(f"[batch] FAIL: {doc.name} — {outcomes[doc].error}")

    return [outcomes[doc] for doc in docs]


# ─── reporting ───────────────────────────────────────────────────────────────


def report(results: list[Result], title: str = "Word export") -> int:
    """Print the run summary and return the process exit code.

    Skipped items are not failures: they are outputs that already existed and
    were left alone, so they count against neither column. The exit code is
    non-zero only when something was actually attempted and did not work.
    """
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
    """Print the PDF-preset reminder.

    Separate from the export because nothing here can *set* the preset:
    `save as … file format format PDF` inherits whatever "Optimize for" was
    last chosen in Word's own Save As dialog, so the only remedy is a human
    picking it once.
    """
    console.print(f"[yellow]▸[/] {PRESET_REMINDER}")


def preflight(
    session: WordSession,
    *,
    allow_open_docs: bool,
    one_osascript: bool = False,
    close_documents: bool = True,
) -> str:
    """Refuse to start on a machine that is not ready. Returns '' when ready.

    By default the run closes every open document without saving and without
    asking (never Word itself), so documents already open are not a refusal.
    The refusals below are for `--do-not-close`: there `--allow-open-docs` is a
    trade the operator may make for the serial path (it costs them Word
    restarts, and the export closes only the document it opened), while the
    one-osascript batch sets `displayAlerts` to false for the whole run and
    cannot act between documents, so it is refused while Word holds anything.
    """
    if not WordSession.available():
        return "needs macOS with Microsoft Word installed"
    if not session.warm():
        return "Word did not become responsive"
    count = session.open_document_count()
    session.started_clean = count == 0
    session.closes_documents = close_documents
    session.preflighted = True
    logger.info(
        f"[word] preflight: word_pid={word_pid()} open_documents={count} started_clean={session.started_clean} "
        f"launched_by_us={session.launched_by_us} close_documents={close_documents}"
    )
    if count < 0:
        # -1 means the query itself failed, not that Word is empty. Both guards
        # below test `count > 0`, so an unknown count used to slip past them and
        # the run proceeded having established nothing. The batch binds
        # `document 1` after each open and closes it without saving, so a
        # document the failed query hid could be the one it takes.
        return (
            "could not determine whether Word has documents open (the count "
            "query failed). Refusing rather than assuming it is empty: close "
            "Word, or make sure it is responding, and re-run."
        )
    # Default closes every document and does not quit Word. --do-not-close is
    # the only mode that still has to refuse a batch while something is open,
    # because that mode will not clear a leftover before the next save.
    if count > 0 and not close_documents and one_osascript:
        return (
            f"Word has {count} document(s) open. --do-not-close will not close "
            "them, and the monolithic run would then save whichever document "
            "is open. Drop --do-not-close (the default closes documents, not "
            "Word), or pass --no-one-osascript."
        )
    if count > 0 and not close_documents and not allow_open_docs:
        return (
            f"Word has {count} document(s) open. --do-not-close keeps them, and "
            "keeping them means a failed document is never recovered by a Word "
            "restart, so a wedged Word ends the run. Close them, or pass "
            "--allow-open-docs to accept that."
        )
    if close_documents:
        # Health check. A Word that answers the count but errors on the close-all
        # ("every document doesn't understand the close message") is the degraded
        # instance of 2026-10-14 22:22, which then produced nothing for every open
        # and cost a 70-document batch in 5 s. The default policy closes everything
        # anyway, so this costs nothing when Word is well, and recycles it when not.
        tag = "[word] preflight:"
        logger.info(f"{tag} closing every document (health check), running: {shown(_CLOSE_ALL)}")
        ok, detail = session._run_logged(tag, _CLOSE_ALL, timeout=30)
        if not ok:
            logger.warning(f"{tag} Word errored on the close-all ({detail or 'no message'}); recycling it before the batch")
            if not session.recycle():
                return f"Word errored on the close-all ({detail or 'no message'}) and could not be recycled"
            ok, detail = session._run_logged(tag, _CLOSE_ALL, timeout=30)
            if not ok:
                return (
                    f"Word still errors on `close every document` after a recycle ({detail or 'no message'}); "
                    "it is not in a state to run a batch. Quit it by hand and re-run."
                )
            count = session.open_document_count()
            session.started_clean = count == 0
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
    do_not_close: Annotated[
        bool,
        typer.Option(
            "--do-not-close",
            help="Do not close documents Word already has open. The default closes "
            "every document and leaves Word itself running.",
        ),
    ] = False,
    accept_all: Annotated[
        bool,
        typer.Option(
            "--accept-all",
            help="Accept every tracked change in Word first; writes <stem><suffix>.docx "
            "and its PDF <stem><suffix>.pdf. Batch mode only.",
        ),
    ] = False,
    accept_suffix: Annotated[
        str, typer.Option("--accept-suffix", help="Suffix of the accepted outputs.")
    ] = ACCEPT_SUFFIX,
    reject_all: Annotated[
        bool,
        typer.Option(
            "--reject-all",
            help="Reject every tracked change in Word first; writes <stem><suffix>.docx "
            "and its PDF <stem><suffix>.pdf. Batch mode only.",
        ),
    ] = False,
    reject_suffix: Annotated[
        str, typer.Option("--reject-suffix", help="Suffix of the rejected outputs.")
    ] = REJECT_SUFFIX,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Errors and summary only.")
    ] = False,
    log_file: Annotated[
        Path | None, typer.Option("--log", help="Also write a log file.")
    ] = None,
    label: Annotated[
        str,
        typer.Option(
            "--label",
            help="A word put in front of every staged file name, so a Word dialog "
            "says whose file it is (a tool's name, say).",
        ),
    ] = "",
    focus: Annotated[
        bool,
        typer.Option(
            "--focus/--no-focus",
            help="Bring Word forward (and hand focus straight back) to answer the "
            "repair prompt and the OK after it, and to check on an item that is "
            "not finished after 10 s. --no-focus presses only what Word shows in "
            "the background, where the OK after a No does not appear and the open "
            "waits out its 240 s timeout.",
        ),
    ] = True,
    crash_limit: Annotated[
        int,
        typer.Option(
            "--crash-limit",
            min=1,
            help="Passes a file that crashes Word, or loads empty, gets before it is a final "
            "failure; each costs a crash and a recovery. 2 (default) keeps one retry for the "
            "cases that are Word's and not the file's: a degraded Word, or a crash signalled "
            "against the wrong item. 1 for a corpus you already know crashes Word: a true "
            "crasher crashed it again on every retry in the 2026-10-14 A/B.",
        ),
    ] = 2,
    crash_signal: Annotated[
        bool,
        typer.Option(
            "--crash-signal/--no-crash-signal",
            help="Treat the Microsoft Error Reporting dialog as the crash: mark the item and end "
            "the pass at once instead of waiting 4 to 5 s for the AppleEvent to fail.",
        ),
    ] = True,
    lock_wait: Annotated[
        float,
        typer.Option(
            "--lock-wait",
            min=0.0,
            help="Seconds to wait for another word_pdf.py / word_redline.py that holds "
            "Word (one Word, one driver). 0 refuses at once and names the holder.",
        ),
    ] = 900.0,
) -> None:
    """Export every .docx in a folder to PDF using Microsoft Word.

    Do not work in Word during a run: by default every open document is
    closed without saving (Word itself keeps running). --do-not-close keeps
    documents that were open before the run.
    """
    timeout = positive_seconds(timeout, "--timeout")
    focus_token = _focus.set(focus)
    try:
        _main(
            src, out, force=force, timeout=timeout, one_osascript=one_osascript,
            check_preset=check_preset, allow_open_docs=allow_open_docs, do_not_close=do_not_close,
            accept_all=accept_all, accept_suffix=accept_suffix, reject_all=reject_all,
            reject_suffix=reject_suffix, quiet=quiet, log_file=log_file, label=label,
            crash_limit=crash_limit, lock_wait=lock_wait, crash_signal=crash_signal,
        )
    finally:
        _focus.reset(focus_token)


def _main(
    src: Path,
    out: Path | None,
    *,
    force: bool,
    timeout: float,
    one_osascript: bool,
    check_preset: bool,
    allow_open_docs: bool,
    do_not_close: bool,
    accept_all: bool,
    accept_suffix: str,
    reject_all: bool,
    reject_suffix: str,
    quiet: bool,
    log_file: Path | None,
    label: str,
    crash_limit: int = 2,
    lock_wait: float = 900.0,
    crash_signal: bool = True,
) -> None:
    logger.remove()
    logger.add(make_console_sink(), colorize=True, level="ERROR" if quiet else "INFO")
    if log_file:
        logger.add(str(log_file), level="DEBUG", rotation="10 MB")

    if not src.is_dir():
        console.print(f"[red]not a folder:[/] {src}")
        raise typer.Exit(2)
    if label and not _LABEL.fullmatch(label):
        console.print("[red]--label takes letters, digits, '.', '_' and '-' only[/]")
        raise typer.Exit(2)
    if accept_all and reject_all:
        console.print("[red]--accept-all and --reject-all are mutually exclusive[/]")
        raise typer.Exit(2)
    if accept_all and (not one_osascript or not accept_suffix):
        console.print("[red]--accept-all needs --one-osascript and a non-empty --accept-suffix[/]")
        raise typer.Exit(2)
    if reject_all and (not one_osascript or not reject_suffix):
        console.print("[red]--reject-all needs --one-osascript and a non-empty --reject-suffix[/]")
        raise typer.Exit(2)
    if check_preset:
        preset_notice()

    session = WordSession()
    if problem := preflight(
        session,
        allow_open_docs=allow_open_docs,
        one_osascript=one_osascript,
        close_documents=not do_not_close,
    ):
        console.print(f"[red]{problem}[/]")
        raise typer.Exit(2)

    with Watchdogs(kill_pass_on_crash=crash_signal):
        results = convert_folder(
            src,
            out,
            force=force,
            timeout=timeout,
            session=session,
            one_osascript=one_osascript,
            close_documents=not do_not_close,
            accept_suffix=accept_suffix if accept_all else reject_suffix if reject_all else "",
            reject=reject_all,
            label=label,
            crash_limit=crash_limit,
            lock_wait=lock_wait,
        )
        session.quit_if_ours()
    title = (
        "accept all → DOCX + PDF"
        if accept_all
        else "reject all → DOCX + PDF"
        if reject_all
        else "DOCX → PDF"
    )
    raise typer.Exit(report(results, f"{title}: {src}"))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    app()
