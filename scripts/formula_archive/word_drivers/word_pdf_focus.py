#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12", "rich>=13.0", "loguru>=0.7"]
# ///
"""``word_pdf.py`` with one change: Word is brought forward to answer "No" and the OK after it.

    uv run python scripts/word_pdf_focus.py --src DOCX_DIR --out PDF_DIR --no-check-preset

Same CLI, same staging, same batch script: this module imports ``word_pdf`` and swaps in
``FocusWatchdogs`` and ``FocusProgress`` before running its ``app``. ``word_pdf.py`` itself is
unchanged.

Why (2026-09-30): after "No" on "Word found unreadable content", Word raises a second alert,
"Word experienced an error trying to open the file" (OK). While Word is in the background that
alert does not exist (System Events reports 0 windows), so nothing can press it and the batch
``open`` hangs until the 240 s AppleEvent timeout, which also ends the pass. Frontmost, Word
shows it at once. The repair prompt itself was also seen only after a timeout, once.

Two triggers, one action. ``_FORWARD_AND_PRESS`` makes Word frontmost, presses No, waits up to
``wait`` seconds for the OK and presses it (or presses a lone OK and stops), then gives focus
back to the app that had it and hides Word again (unless Word was the app in front).

- ``FocusProgress``: an item opened and not saved within ``nudge_after`` (5 s) seconds, then
  every ``nudge_every`` (10 s) while it stays open.
- ``FocusWatchdogs``: Word shows a "No" button in the background; if its OK has not appeared
  within the same activation, a poll that finds Word without a button fetches it, for
  ``owe_window`` seconds after the No.

Focus is taken for these checks only. A document that is merely slow to open costs ``wait``
seconds of focus per check.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import word_pdf  # noqa: E402  (must follow the sys.path guard above)

NO_STEP = "No"
OK_STEP = "OK|Ok"

# argv: process name, seconds each step may wait, then steps; a step is button names joined by
# "|", any one of which is pressed. Steps run in order with the process frontmost and stop at the
# first that finds none of its buttons. Returns the names pressed, joined by ",".
_FORWARD_AND_PRESS = """
on pressAny(procName, names)
  tell application "System Events"
    tell process procName
      repeat with w in windows
        repeat with target in {w} & (sheets of w)
          repeat with nm in names
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
end pressAny

on run argv
  set procName to item 1 of argv
  set waitFor to (item 2 of argv) as number
  set steps to items 3 thru -1 of argv
  set priorApp to ""
  set done to {}
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
    repeat (waitFor * 4) times
      delay 0.25
      set pressed to my pressAny(procName, names)
      if pressed is not "" then exit repeat
    end repeat
    if pressed is "" then exit repeat
    set end of done to pressed
    if pressed is "OK" or pressed is "Ok" then exit repeat
  end repeat
  tell application "System Events"
    -- Word goes back into hiding unless it was the app in front (someone working in it).
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
  set AppleScript's text item delimiters to ","
  set out to done as string
  set AppleScript's text item delimiters to od
  return out
end run
""".strip()


def forward(*steps: str, wait: float = 4.0) -> list[str]:
    """Run ``_FORWARD_AND_PRESS`` on Word; the buttons pressed, in order."""
    _, out, _ = word_pdf.osa(
        _FORWARD_AND_PRESS, word_pdf.WORD_PROC, str(wait), *steps, timeout=wait * len(steps) + 15
    )
    pressed = [p for p in out.split(",") if p]
    if pressed:
        logger.warning(f"[focus] brought Word forward, pressed {' then '.join(pressed)}; focus handed back")
    return pressed


@dataclass
class FocusWatchdogs(word_pdf.Watchdogs):
    """``Watchdogs`` whose "No" and the OK after it are pressed with Word frontmost."""

    owe_window: float = 30.0  # seconds after a No during which Word may still owe its OK
    wait: float = 4.0  # seconds each press waits for its button while Word is frontmost
    forwarded: int = 0
    _owed_until: float = 0.0

    def _forward(self, *steps: str) -> list[str]:
        pressed = forward(*steps, wait=self.wait)
        if pressed:
            self.forwarded += 1
        return pressed

    def _fetch_owed(self) -> None:
        if not self._owed_until:
            return
        if time.monotonic() > self._owed_until:
            self._owed_until = 0.0
            logger.warning("[watchdog] no OK appeared after the last No; stopped bringing Word forward")
            return
        if self._forward(OK_STEP):
            self._owed_until = 0.0

    def _loop_word(self) -> None:
        # word_pdf.Watchdogs._loop_word, with the No (and its OK) pressed with Word frontmost.
        while not self._stop.wait(self.poll):
            _, shown, _ = word_pdf.osa(word_pdf._DUMP_BUTTONS, word_pdf.WORD_PROC, timeout=8)
            if not shown:
                self._fetch_owed()
                continue
            self._note_buttons(word_pdf.WORD_PROC)
            if NO_STEP in {n.strip() for n in shown.split("\t")}:
                pressed = self._forward(NO_STEP, OK_STEP)
                if pressed:
                    self.declined += 1
                    self._owed_until = 0.0 if len(pressed) > 1 else time.monotonic() + self.owe_window
                    continue
            _, pressed, _ = word_pdf.osa(
                word_pdf._PRESS_ACTIVATED, word_pdf.WORD_PROC, *word_pdf.GRANT_BUTTONS, timeout=20
            )
            if pressed:
                self.granted += 1
                logger.warning(f"[watchdog] sandbox grant completed via {pressed!r}")
                continue
            _, pressed, _ = word_pdf.osa(word_pdf._PRESS, word_pdf.WORD_PROC, *word_pdf.DISMISS_BUTTONS, timeout=10)
            if pressed:
                self.dismissed += 1
                logger.warning(f"[watchdog] Word dialog dismissed via {pressed!r}")


@dataclass
class FocusProgress(word_pdf._Progress):
    """``_Progress`` that also checks on an item Word opened and has not saved.

    Word may not draw its repair prompt, or the OK after it, until it is frontmost, so an item
    with no ``[ok]``/``[fail]``/``[retry]`` line after ``nudge_after`` seconds brings Word
    forward to press No (then its OK) or a lone OK, and again every ``nudge_every`` seconds
    while that item stays open. A document that is merely slow costs ``wait`` seconds of focus.
    """

    nudge_after: float = 5.0
    nudge_every: float = 10.0
    wait: float = 4.0
    nudges: int = 0

    def _report(self, item: int) -> None:
        report = self.diagnose(self.log_path)
        logger.warning(
            f"[batch{self.label}] item {item}/{self.total} open for more than {self.stall_after:.0f} s:\n{report}"
        )

    def _loop(self) -> None:
        # word_pdf._Progress._loop, plus the check. One clock for both, restarted by any
        # [ok]/[fail]/[retry] line (word_pdf's counts only [ok]/[fail]), and the stall report
        # runs on its own thread: its osascript probes time out while Word is busy, which held
        # a check back 30 s in the first trial.
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
                threading.Thread(target=self._report, args=(item,), daemon=True).start()
            if now >= nudge_at:
                self.nudges += 1
                nudge_at = now + self.nudge_every
                logger.info(f"[focus] item {item}/{self.total} not saved after {now - item_since:.0f} s; checking Word")
                forward("No|OK|Ok", "OK|Ok", wait=self.wait)


def install() -> None:
    """Make ``word_pdf.main`` run ``FocusWatchdogs`` and ``FocusProgress``."""
    word_pdf.Watchdogs = FocusWatchdogs
    word_pdf._Progress = FocusProgress


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    install()
    word_pdf.app()
