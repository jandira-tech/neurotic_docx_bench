"""Microsoft Word ground-truth renderer (macOS + Word only — LOCAL-ONLY, NEVER in CI).

Drives Word via AppleScript to open each DOCX and export it to PDF, for regenerating the
committed oracle from source on a machine that has Word. CI never invokes this (it scores
against the committed PDFs, or regenerates them with LibreOffice — see the CI workflow).

CAUTION: Word may prompt for automation permission (grant it) and can block on modal
dialogs. Run interactively, not from unattended automation.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from neurotic_docx_bench.render.base import RenderReport, RenderResult

# Open the DOCX in Word and export the active document to PDF, then close without saving.
_APPLESCRIPT = """
on run argv
  set inPath to item 1 of argv
  set outPath to item 2 of argv
  tell application "Microsoft Word"
    open inPath
    set theDoc to active document
    save as theDoc file name outPath file format format PDF
    close theDoc saving no
  end tell
end run
""".strip()

_WORD_APP = Path("/Applications/Microsoft Word.app")


def word_available() -> bool:
    """True only on macOS with Word installed and osascript present."""
    return (
        platform.system() == "Darwin"
        and _WORD_APP.exists()
        and shutil.which("osascript") is not None
    )


def convert_one(
    docx: Path, out_dir: Path, *, force: bool = False, timeout: float = 180.0,
) -> RenderResult:
    """Export a single DOCX to PDF via Microsoft Word (blocking; run interactively)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = out_dir / f"{docx.stem}.pdf"
    if pdf.exists() and not force:
        return RenderResult(source=docx, pdf=pdf, ok=True, skipped=True)
    try:
        proc = subprocess.run(
            ["osascript", "-e", _APPLESCRIPT, str(docx.resolve()), str(pdf.resolve())],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return RenderResult(source=docx, pdf=None, ok=False, error="Word timed out (dialog?)")
    if proc.returncode == 0 and pdf.exists():
        return RenderResult(source=docx, pdf=pdf, ok=True)
    return RenderResult(
        source=docx, pdf=None, ok=False, error=(proc.stderr or f"exit {proc.returncode}").strip(),
    )


# Open the document in Word and immediately close it (no export). A file that is
# not "Word valid" (per the standing definition: opens with zero warning/error/
# repair prompts) makes the AppleScript `open` block on a modal dialog; a corrupt
# package makes osascript exit nonzero; a clean open echoes the document name.
_VALIDATE_APPLESCRIPT = """
on run argv
  set inPath to item 1 of argv
  set inFile to POSIX file inPath
  tell application "Microsoft Word"
    open inFile
    set docName to name of active document
    close active document saving no
    return docName
  end tell
end run
""".strip()

# Ask System Events whether the Word process currently shows a sheet or a dialog
# window — an ACTUAL modal, as opposed to merely being slow (TODO §1: timeout ≠
# dialog; a ~1000-page document takes longer than any fixed window just to open).
_MODAL_PROBE_APPLESCRIPT = """
tell application "System Events"
  if not (exists process "Microsoft Word") then return "no-process"
  tell process "Microsoft Word"
    set sheetCount to 0
    set dialogCount to 0
    repeat with w in windows
      try
        set sheetCount to sheetCount + (count of sheets of w)
      end try
      try
        if subrole of w is "AXDialog" then set dialogCount to dialogCount + 1
      end try
    end repeat
    return (sheetCount as text) & " " & (dialogCount as text)
  end tell
end tell
""".strip()

_CLOSE_APPLESCRIPT = 'tell application "Microsoft Word" to close active document saving no'
_ESCAPE_APPLESCRIPT = 'tell application "System Events" to key code 53'  # Escape


@dataclass(frozen=True)
class ValidationResult:
    """WV-1 outcome. ``unjudgeable`` = the budget ran out with NO modal observed —
    Word was merely slow on this machine; recorded, never treated as invalid."""

    outcome: Literal["valid", "invalid", "unjudgeable"]
    error: str | None = None
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return self.outcome == "valid"


def _budget(timeout: float, reference_duration_s: float | None, k: float) -> float:
    """Per-doc open budget: ``max(timeout, k × measured reference open)`` — the
    reference (a known-Word-valid doc) calibrates for machine/Word slowness."""
    if reference_duration_s is None:
        return timeout
    return max(timeout, k * reference_duration_s)


def _interpret_modal_probe(stdout: str, returncode: int) -> bool | None:
    """True/False = modal present/absent; None = probe could not tell (pure)."""
    if returncode != 0:
        return None
    out = stdout.strip()
    if out == "no-process":
        return False
    try:
        counts = [int(x) for x in out.split()]
    except ValueError:
        return None
    if not counts:
        return None
    return any(c > 0 for c in counts)


def _interpret_open_exit(
    *, returncode: int | None, stdout: str, stderr: str, duration_s: float,
) -> ValidationResult:
    """Outcome of a COMPLETED osascript open (pure). A clean open echoes the
    document name and exits 0; anything else is invalid."""
    if returncode == 0 and stdout.strip():
        return ValidationResult("valid", None, duration_s)
    return ValidationResult(
        "invalid", (stderr or f"exit {returncode}").strip(), duration_s,
    )


class ModalProbeError(RuntimeError):
    """System Events / Accessibility probe failed — validity cannot be judged."""


def probe_modal(*, timeout: float = 10.0) -> bool | None:
    """Does Word currently show a sheet/dialog? None when the probe fails."""
    try:
        proc = subprocess.run(
            ["osascript", "-e", _MODAL_PROBE_APPLESCRIPT],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    return _interpret_modal_probe(proc.stdout, proc.returncode)


def _close_active_document(*, timeout: float = 15.0) -> None:
    """Targeted close of whatever Word is holding, so retries do not stack
    windows: close saving no; on failure, Escape (dismiss a sheet) and retry."""
    for script in (_CLOSE_APPLESCRIPT, _ESCAPE_APPLESCRIPT, _CLOSE_APPLESCRIPT):
        try:
            proc = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True, timeout=timeout,
            )
        except (subprocess.TimeoutExpired, OSError):
            continue
        if script == _CLOSE_APPLESCRIPT and proc.returncode == 0:
            return


def measure_reference_open(reference: Path, *, timeout: float = 600.0) -> float | None:
    """Open+close a known-Word-valid reference, returning the measured duration
    (the calibration for :func:`_budget`); None when the open fails."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            ["osascript", "-e", _VALIDATE_APPLESCRIPT, str(reference.resolve())],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        _close_active_document()
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return time.monotonic() - start


def validate_one(
    docx: Path,
    *,
    timeout: float = 60.0,
    reference: Path | None = None,
    reference_duration_s: float | None = None,
    k: float = 4.0,
    poll_interval: float = 2.0,
) -> ValidationResult:
    """Word-validity gate: open in Microsoft Word; an observed modal is INVALID,
    a clean open is VALID, budget exhaustion with no modal is UNJUDGEABLE.

    LOCAL/INTERACTIVE only (never CI). Grant permission prompts (they do not fail
    validity per the standing definition). The budget is ``max(timeout, k×d)``
    where ``d`` is the measured open time of a known-Word-valid ``reference`` —
    pass ``reference_duration_s`` directly to reuse one measurement across many
    docs (the CLI measures once per invocation).
    """
    if reference is not None and reference_duration_s is None:
        reference_duration_s = measure_reference_open(reference, timeout=max(timeout, 600.0))
    budget = _budget(timeout, reference_duration_s, k)
    start = time.monotonic()
    proc = subprocess.Popen(
        ["osascript", "-e", _VALIDATE_APPLESCRIPT, str(docx.resolve())],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    while True:
        try:
            proc.wait(timeout=poll_interval)
        except subprocess.TimeoutExpired:
            pass
        elapsed = time.monotonic() - start
        if proc.poll() is not None:
            out, err = proc.communicate()
            return _interpret_open_exit(
                returncode=proc.returncode, stdout=out, stderr=err, duration_s=elapsed,
            )
        modal = probe_modal()
        if modal is True:
            _close_active_document()
            proc.kill()
            proc.communicate()  # reap the killed osascript process
            return ValidationResult(
                "invalid", "repair dialog (modal detected)", elapsed,
            )
        if modal is None:
            # Probe unavailable (permissions / osascript failure): do not treat as
            # "no modal" — that would mis-label a blocked repair dialog as UNJUDGEABLE.
            _close_active_document()
            proc.kill()
            proc.communicate()
            raise ModalProbeError(
                "Word modal probe failed (grant Accessibility / System Events "
                "permissions for osascript); cannot judge validity safely",
            )
        if elapsed > budget:
            _close_active_document()
            proc.kill()
            proc.communicate()
            return ValidationResult(
                "unjudgeable",
                f"slow open — no dialog observed within {budget:.0f}s budget",
                elapsed,
            )


class WordRenderer:
    name: str = "word"

    def to_pdfs(
        self,
        source_dir: Path,
        work_dir: Path,
        *,
        force: bool = False,
        jobs: int = 12,
    ) -> RenderReport:
        if not word_available():
            raise RuntimeError(
                "Word renderer requires macOS with Microsoft Word installed "
                "(local-only; never invoked in CI)",
            )
        out_dir = work_dir / "pdf"
        out_dir.mkdir(parents=True, exist_ok=True)
        # Sequential: a single Word instance, one document at a time (Word is not
        # safely concurrent via AppleScript).
        docs = sorted(source_dir.glob("*.docx"))
        results = [convert_one(docx, out_dir, force=force) for docx in docs]
        return RenderReport(pdf_dir=out_dir, results=results)
