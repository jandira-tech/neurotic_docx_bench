#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12", "rich>=13.0", "loguru>=0.7"]
# ///
"""Redline two folders of DOCX against each other with Microsoft Word for Mac.

Point it at folder A and folder B; every document in A is compared against its
counterpart in B (same filename) and Word's own "Compare Documents" result —
native `w:ins` / `w:del` tracked changes, the oracle this repo scores against —
is written out as PDF, DOCX, or both.

    ./word_redline.py --a ./before --b ./after
    ./word_redline.py --a ./before --b ./after --emit both --out ./redlines
    ./word_redline.py --a ./variants --b ./variants --cross --emit docx

All the Word-driving machinery lives in `word_pdf.py` and is imported, not
copied: process lifecycle (`WordSession`), container staging (`Stage`), the
dialog and error-report watchdogs (`Watchdogs`), and the PDF export itself
(`export_pdf`). This module adds only what is specific to comparing a pair.

Design decisions carried over from `docs/WORD_DRIVER_AUDIT.md`:

- **The comparison result is identified by exclusion.** Word leaves the base
  frontmost when a compare silently produces nothing, so saving whichever
  document is frontmost would ship a change-free file that looks valid and
  scores as garbage (§14.1).
- **Base health is checked before the compare runs**, not after. An unreadable
  base loads as a document with zero paragraphs and the compare then fails with
  an error naming the *other* file (§14.1).
- **Zero revisions is reported, not failed.** Two identical documents compare to
  no revisions legitimately; the count is surfaced so a batch of unexpected
  zeroes is visible instead of silently passing.
- **Both sides are staged under distinct names.** Name-paired redlines routinely
  compare `deal.docx` against `deal.docx`, and one staging inbox cannot hold
  both under one name.
- **One failed pair recycles Word.** After a bad document Word keeps answering,
  returning empty documents for every later open, with no error (§5, §6).

Two Word settings this script cannot set for you, both sticky, both worth one
minute by hand before a batch:

1. **PDF quality.** `save as … file format format PDF` inherits whatever
   "Optimize for" you last chose in Word's own Save As dialog. Pick the SECOND
   option, "Best for printing", once.
2. **Markup display.** A redline PDF shows the tracked changes the way Word is
   currently set to show them (Review ▸ Markup display, and Print Markup). Open
   one redline by hand and confirm it looks the way you want the whole batch to
   look before running the batch.

`--check-preset/--no-check-preset` controls whether that reminder prints.
"""

from __future__ import annotations

import os
import shutil
import signal
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import typer
from loguru import logger
from rich.table import Table

# Sibling import. Running the file directly (or via `uv run --script`) already
# puts this directory on sys.path; the guard is for importing it as a module.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from word_pdf import (  # noqa: E402  (must follow the sys.path guard above)
    Stage,
    Watchdogs,
    WordSession,
    classify_failure,
    console,
    export_pdf,
    iter_docx,
    osa,
    preflight,
    preset_notice,
)

MARKUP_REMINDER = (
    "A redline PDF shows tracked changes the way Word is currently set to show "
    "them (Review ▸ Markup display, and Print Markup).\n"
    "  Open one redline in Word by hand and confirm it looks right before "
    "running the batch — this script cannot set that for you."
)


class Emit(str, Enum):
    """What lands in the output folder."""

    PDF = "pdf"
    DOCX = "docx"
    BOTH = "both"


# ─── pure helpers ────────────────────────────────────────────────────────────


@dataclass(slots=True, frozen=True)
class Pairing:
    """Name-matched pairs, plus what each side had that the other did not."""

    pairs: list[tuple[Path, Path]]
    only_a: list[Path]
    only_b: list[Path]


def pair_by_name(a_docs: list[Path], b_docs: list[Path]) -> Pairing:
    """Match A against B on filename. Unmatched documents are reported, not dropped silently."""
    by_name_b = {p.name: p for p in b_docs}
    by_name_a = {p.name: p for p in a_docs}
    shared = sorted(set(by_name_a) & set(by_name_b))
    return Pairing(
        pairs=[(by_name_a[n], by_name_b[n]) for n in shared],
        only_a=[by_name_a[n] for n in sorted(set(by_name_a) - set(by_name_b))],
        only_b=[by_name_b[n] for n in sorted(set(by_name_b) - set(by_name_a))],
    )


def cross_pairs(a_docs: list[Path], b_docs: list[Path]) -> list[tuple[Path, Path]]:
    """Every A against every B.

    A document is never compared with itself, so pointing both folders at one
    directory yields each ordered pair once rather than N self-comparisons. The
    two orderings of a pair are kept: which side is the base changes the result.
    """
    return [
        (a, b) for a in a_docs for b in b_docs if a.resolve() != b.resolve()
    ]


def redline_stem(a: Path, b: Path) -> str:
    """Output name for one pair: the shared name, or both names when they differ."""
    return a.stem if a.stem == b.stem else f"{a.stem}__vs__{b.stem}"


@dataclass(slots=True, frozen=True)
class Outputs:
    """Where one pair's results are meant to land. `None` means "not wanted"."""

    docx: Path | None
    pdf: Path | None

    @property
    def wanted(self) -> list[Path]:
        return [p for p in (self.docx, self.pdf) if p is not None]


def plan_outputs(
    a: Path, b: Path, out_dir: Path, docx_dir: Path | None, emit: Emit
) -> Outputs:
    """Resolve one pair's destinations from the emit mode."""
    stem = redline_stem(a, b)
    return Outputs(
        docx=((docx_dir or out_dir) / f"{stem}.docx")
        if emit in (Emit.DOCX, Emit.BOTH)
        else None,
        pdf=(out_dir / f"{stem}.pdf") if emit in (Emit.PDF, Emit.BOTH) else None,
    )


def should_skip(outputs: Outputs, *, force: bool) -> bool:
    """True when every wanted output is already on disk and non-empty."""
    if force:
        return False
    wanted = outputs.wanted
    return bool(wanted) and all(p.exists() and p.stat().st_size > 0 for p in wanted)


def parse_revision_count(raw: str) -> int:
    """Word's revision count for the comparison, or -1 when it did not report one."""
    raw = raw.strip()
    return int(raw) if raw.isdigit() else -1


@dataclass(slots=True)
class PairResult:
    """Outcome for one comparison."""

    base: Path
    revision: Path
    docx: Path | None = None
    pdf: Path | None = None
    ok: bool = False
    skipped: bool = False
    revisions: int = -1
    error: str = ""
    seconds: float = 0.0

    @property
    def label(self) -> str:
        return f"{self.base.name} → {self.revision.name}"


# ─── Word: compare ───────────────────────────────────────────────────────────

# Word's own Compare Documents, run headless.
#
# `detect format changes true` makes Word emit *PrChange revisions (w:rPrChange,
# w:pPrChange, w:tblPrChange, …) for formatting-only differences. With it off, a
# pair differing only in font, bullet glyph, spacing or table properties
# compares to a document with no revisions at all — indistinguishable from
# "compare silently failed". It stays on: flipping it for part of a corpus
# silently changes what every score in that corpus means.
#
# `format document` is WdSaveFormat 12 (wdFormatXMLDocument, i.e. .docx). The
# legacy binary format is the separate `format document97` — not the same thing.
_COMPARE = """
on run argv
  set basePath to item 1 of argv
  set revPath to item 2 of argv
  set outPath to item 3 of argv
  set revisionCount to -1
  with timeout of 900 seconds
    tell application "Microsoft Word"
      open POSIX file basePath
      set baseDoc to document 1
      set baseName to name of baseDoc
      -- Health BEFORE the compare. An unreadable base loads as a document with
      -- zero paragraphs and the compare then fails with an error naming the
      -- OTHER file, which sends every diagnosis to the wrong document.
      if (count of paragraphs of baseDoc) is 0 then
        close every document saving no
        error "base loaded empty (Word could not read it)"
      end if
      compare baseDoc path revPath detect format changes true ignore all comparison warnings true add to recent files false
      -- Identify the result by exclusion rather than by whichever document is
      -- frontmost: a compare that silently produced nothing leaves the BASE
      -- frontmost, and saving that ships a change-free document that looks
      -- valid and scores as garbage.
      -- Index explicitly: `repeat with d in documents` makes AppleScript send
      -- `count` to `every document`, which this Word build rejects outright.
      set cmpDoc to missing value
      set docCount to count of documents
      repeat with i from 1 to docCount
        set dd to document i
        if (name of dd) is not baseName then set cmpDoc to dd
      end repeat
      if cmpDoc is missing value then
        close every document saving no
        error "compare produced no result document"
      end if
      try
        set revisionCount to count of revisions of cmpDoc
      end try
      save as cmpDoc file name outPath file format format document
      close every document saving no
    end tell
  end timeout
  return revisionCount as string
end run
""".strip()


def compare_pair(
    staged_base: Path, staged_revision: Path, staged_out: Path, *, timeout: float = 300.0
) -> tuple[bool, int, str]:
    """Compare one staged pair into one staged .docx. Returns (ok, revisions, error)."""
    rc, out, err = osa(
        _COMPARE,
        str(staged_base),
        str(staged_revision),
        str(staged_out),
        timeout=timeout,
    )
    produced = staged_out.exists() and staged_out.stat().st_size > 0
    if rc == 0 and produced:
        return True, parse_revision_count(out), ""
    return False, -1, classify_failure(rc, err, produced)


# ─── batch ───────────────────────────────────────────────────────────────────


def redline_folders(
    folder_a: Path,
    folder_b: Path,
    out_dir: Path,
    *,
    docx_dir: Path | None = None,
    emit: Emit = Emit.PDF,
    cross: bool = False,
    swap: bool = False,
    force: bool = False,
    timeout: float = 300.0,
    pdf_timeout: float = 180.0,
    session: WordSession | None = None,
) -> list[PairResult]:
    """Redline every pair drawn from two folders. Serial, by necessity.

    Word is a single-instance, user-session-bound application — there is no
    equivalent of LibreOffice's `-env:UserInstallation`, so a second worker
    would drive the same instance. Parallelism needs separate macOS user
    sessions or VMs (§9), which is why there is no `--jobs`.
    """
    a_docs, b_docs = iter_docx(folder_a), iter_docx(folder_b)
    if cross:
        pairs = cross_pairs(a_docs, b_docs)
    else:
        pairing = pair_by_name(a_docs, b_docs)
        pairs = pairing.pairs
        for orphan in pairing.only_a:
            logger.warning(f"no counterpart in B: {orphan.name}")
        for orphan in pairing.only_b:
            logger.warning(f"no counterpart in A: {orphan.name}")
    if swap:
        pairs = [(b, a) for a, b in pairs]

    if not pairs:
        logger.warning(f"nothing to compare between {folder_a} and {folder_b}")
        return []

    owns_session = session is None
    session = session or WordSession()
    if owns_session and not session.warm():
        return [
            PairResult(base=a, revision=b, error="Word did not become responsive")
            for a, b in pairs
        ]

    results: list[PairResult] = []
    with Stage(prefix="wordredline") as stage:
        try:
            for i, (base, revision) in enumerate(pairs, 1):
                outputs = plan_outputs(base, revision, out_dir, docx_dir, emit)
                label = f"{base.name} → {revision.name}"
                if should_skip(outputs, force=force):
                    results.append(
                        PairResult(
                            base=base,
                            revision=revision,
                            docx=outputs.docx,
                            pdf=outputs.pdf,
                            ok=True,
                            skipped=True,
                        )
                    )
                    logger.debug(f"[{i}/{len(pairs)}] skip (exists): {label}")
                    continue

                started = time.monotonic()
                result = _redline_one(
                    base,
                    revision,
                    outputs,
                    stage=stage,
                    timeout=timeout,
                    pdf_timeout=pdf_timeout,
                )
                result.seconds = time.monotonic() - started
                results.append(result)

                if result.ok:
                    note = "" if result.revisions < 0 else f", {result.revisions} revisions"
                    logger.info(f"[{i}/{len(pairs)}] ok ({result.seconds:.1f}s{note}): {label}")
                    if result.revisions == 0:
                        logger.warning(f"  compared clean (no revisions): {label}")
                else:
                    logger.error(f"[{i}/{len(pairs)}] FAIL: {label} — {result.error}")
                    # A bad document leaves Word answering but returning empty
                    # documents for every later open, silently. Recycle rather
                    # than carry on: in the old corpus one poison file cost 203.
                    session.recycle(stage.inbox, stage.outbox, folder_a, folder_b)
        finally:
            if owns_session:
                session.quit_if_ours()
    return results


def _redline_one(
    base: Path,
    revision: Path,
    outputs: Outputs,
    *,
    stage: Stage,
    timeout: float,
    pdf_timeout: float,
) -> PairResult:
    """One comparison, start to finish, entirely inside Word's own container.

    The redline .docx is always produced — Word yields the comparison only as an
    open document, and the PDF is exported from that file rather than from a
    second, separate save, so `--emit pdf` and `--emit both` render the same
    bytes. When only a PDF was asked for, the .docx stays in the staging
    directory and is discarded with it.
    """
    stem = redline_stem(base, revision)
    staged_base = stage.place_as(base, f"base__{stem}.docx")
    staged_revision = stage.place_as(revision, f"rev__{stem}.docx")
    staged_docx = stage.outbox / f"{stem}.docx"
    result = PairResult(base=base, revision=revision)

    try:
        ok, revisions, err = compare_pair(
            staged_base, staged_revision, staged_docx, timeout=timeout
        )
        result.revisions = revisions
        if not ok:
            result.error = err
            return result

        if outputs.pdf is not None:
            staged_pdf = stage.outbox / f"{stem}.pdf"
            ok, err = export_pdf(staged_docx, staged_pdf, timeout=pdf_timeout)
            if not ok:
                result.error = f"redline saved but PDF export failed: {err}"
                return result
            _deliver(staged_pdf, outputs.pdf)
            result.pdf = outputs.pdf

        if outputs.docx is not None:
            _deliver(staged_docx, outputs.docx)
            result.docx = outputs.docx

        result.ok = True
        return result
    finally:
        staged_base.unlink(missing_ok=True)
        staged_revision.unlink(missing_ok=True)
        staged_docx.unlink(missing_ok=True)


def _deliver(staged: Path, final: Path) -> None:
    final.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staged, final)


# ─── reporting ───────────────────────────────────────────────────────────────


def report_pairs(results: list[PairResult], title: str = "Word redline") -> int:
    """Print the batch summary and return the process exit code."""
    done = [r for r in results if r.ok and not r.skipped]
    skipped = [r for r in results if r.skipped]
    failed = [r for r in results if not r.ok]
    clean = [r for r in done if r.revisions == 0]

    table = Table(title=title, show_lines=False)
    table.add_column("outcome")
    table.add_column("count", justify="right")
    table.add_row("redlined", str(len(done)))
    table.add_row("skipped (exists)", str(len(skipped)))
    table.add_row("failed", str(len(failed)), style="red" if failed else None)
    if clean:
        table.add_row("compared clean (0 revisions)", str(len(clean)), style="yellow")
    if done:
        seconds = sorted(r.seconds for r in done)
        table.add_row("median seconds", f"{seconds[len(done) // 2]:.1f}")
        counted = [r.revisions for r in done if r.revisions >= 0]
        if counted:
            table.add_row("total revisions", str(sum(counted)))
    console.print(table)

    for r in clean:
        console.print(f"  [yellow]clean[/] {r.label}: Word found no differences")
    for r in failed:
        console.print(f"  [red]FAIL[/] {r.label}: {r.error}")
    return 1 if failed else 0


# ─── CLI ─────────────────────────────────────────────────────────────────────

app = typer.Typer(add_completion=False, help=__doc__)


@app.command()
def main(
    folder_a: Path = typer.Option(
        ..., "--a", "-a", help="Folder of originals (the base of each comparison)."
    ),
    folder_b: Path = typer.Option(
        ..., "--b", "-b", help="Folder of revisions (compared against A)."
    ),
    out: Path = typer.Option(
        Path("redlines"), "--out", "-o", help="Where the redlines land."
    ),
    docx_out: Path | None = typer.Option(
        None, "--docx-out", help="Separate folder for the .docx. Default: alongside --out."
    ),
    emit: Emit = typer.Option(
        Emit.PDF, "--emit", help="pdf | docx | both. Default pdf: the .docx is discarded."
    ),
    cross: bool = typer.Option(
        False, "--cross", help="Compare every A against every B instead of matching names."
    ),
    swap: bool = typer.Option(
        False, "--swap", help="Use B as the base and A as the revision."
    ),
    force: bool = typer.Option(False, "--force", help="Redo pairs whose output exists."),
    timeout: float = typer.Option(300.0, "--timeout", help="Seconds per comparison."),
    pdf_timeout: float = typer.Option(180.0, "--pdf-timeout", help="Seconds per PDF export."),
    check_preset: bool = typer.Option(
        True, "--check-preset/--no-check-preset", help="Print the Word-settings reminders."
    ),
    allow_open_docs: bool = typer.Option(
        False, "--allow-open-docs", help="Run even if Word already has documents open."
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Errors and summary only."),
    log_file: Path | None = typer.Option(None, "--log", help="Also write a log file."),
) -> None:
    """Redline folder A against folder B using Microsoft Word's Compare Documents."""
    logger.remove()
    logger.add(lambda m: console.print(m, end=""), level="ERROR" if quiet else "INFO")
    if log_file:
        logger.add(str(log_file), level="DEBUG", rotation="10 MB")

    for label, folder in (("--a", folder_a), ("--b", folder_b)):
        if not folder.is_dir():
            console.print(f"[red]{label} is not a folder:[/] {folder}")
            raise typer.Exit(2)

    if check_preset:
        if emit is not Emit.DOCX:
            preset_notice()
            console.print(f"[yellow]▸[/] {MARKUP_REMINDER}")
        if emit is Emit.PDF:
            console.print(
                "[yellow]▸[/] --emit pdf discards the tracked-changes .docx once the "
                "PDF is rendered. Use --emit both to keep it."
            )

    session = WordSession()
    if problem := preflight(session, allow_open_docs=allow_open_docs):
        console.print(f"[red]{problem}[/]")
        raise typer.Exit(2)

    with Watchdogs():
        results = redline_folders(
            folder_a,
            folder_b,
            out,
            docx_dir=docx_out,
            emit=emit,
            cross=cross,
            swap=swap,
            force=force,
            timeout=timeout,
            pdf_timeout=pdf_timeout,
            session=session,
        )
        session.quit_if_ours()
    raise typer.Exit(report_pairs(results, f"redline: {folder_a.name} → {folder_b.name}"))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    app()
