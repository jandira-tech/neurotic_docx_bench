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
from pathlib import Path

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


class WordRenderer:
    name: str = "word"

    def to_pdfs(
        self,
        source_dir: Path,
        work_dir: Path,
        *,
        force: bool = False,
        jobs: int = 4,
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
