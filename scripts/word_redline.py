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

- **The comparison result is the new document Word creates, delivered as is.**
  `compare` yields its result as a fresh, unsaved document. That document is
  the redline; nothing is reconstructed from it. Because it is unsaved, Word
  would prompt for a location, which is exactly why `save as` is handed the
  path instead. The script finds it by exclusion — the open document whose
  name is not the base's — because naming the document you mean is the rule
  (§5.18), not because the base would otherwise be served up in its place.
- **Base health is checked before the compare runs**, not after. An unreadable
  base loads as a document with zero paragraphs and the compare then fails with
  an error naming the *other* file (§14.1).
- **Zero revisions is reported, not failed.** Two identical documents compare to
  no revisions legitimately; the count is surfaced so a batch of unexpected
  zeroes is visible instead of silently passing.
- **One failed pair recycles Word.** After a bad document Word keeps answering,
  returning empty documents for every later open, with no error (§5, §7).

Plumbing, noted because it is visible in the staging directory and is not a
finding: the two sides of a pair go in under `base__` / `rev__` prefixes. A pair
is `A/deal.docx` against `B/deal.docx` — one pair, with one name between its two
sides — and a single inbox cannot hold two files called `deal.docx`. That says
nothing about duplicates *inside* either folder, which a filesystem forbids
anyway.

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
from typing import Annotated

import typer
from loguru import logger
from rich.table import Table

# Sibling import. Running the file directly (or via `uv run --script`) already
# puts this directory on sys.path; the guard is for importing it as a module.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from word_pdf import (  # must follow the sys.path guard above
    _EXPORT_BATCH,
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
    recover_after_failure,
    run_batch_with_resume,
    safe_stage_name,
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
    """Output name for one pair: always both sides, joined.

    Same-stem pairs used to collapse to the bare shared name, so comparing
    `before/deal.docx` against `after/deal.docx` landed as `deal.docx` — a
    tracked-changes document named exactly like both of the documents it came
    from. Naming both sides every time keeps a redline distinguishable from
    its own inputs, and changes nothing when the stems already differ.
    """
    return f"{a.stem}__vs__{b.stem}"


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
    timing_exact: bool = True
    """False when `seconds` is a per-pair average from a batch pass."""

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
      -- `compare` yields its result as a NEW unsaved document, and that
      -- document as created is what ships. Find it by exclusion (the one whose
      -- name is not the base's) rather than by `active document`, because the
      -- rule is to name the document you mean (§5.18). The `save as` below
      -- supplies the path, which is what stops Word prompting for one.
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


# The same comparison, once per manifest row, inside one osascript. The
# per-pair `try … on error … close every document saving no … end try` IS the
# malformed-document contract: answer nothing, close whatever is open, record
# it, move to the next pair. `[ok]` carries the revision count as a third
# field; the repair prompt is answered concurrently by the watchdog.
_COMPARE_BATCH = r"""
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
      if (count of f) is 4 then
        set itemId to item 1 of f
        set baseP to item 2 of f
        set revP to item 3 of f
        set outP to item 4 of f
        set revisionCount to -1
        try
          with timeout of 900 seconds
            tell application "Microsoft Word"
              open POSIX file baseP
              set baseDoc to document 1
              set baseName to name of baseDoc
              if (count of paragraphs of baseDoc) is 0 then
                close every document saving no
                error "base loaded empty (Word could not read it)"
              end if
              compare baseDoc path revP detect format changes true ignore all comparison warnings true add to recent files false
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
              save as cmpDoc file name outP file format format document
              close every document saving no
            end tell
          end timeout
          set okCount to okCount + 1
          my logLine(logPath, "[ok]" & tab & itemId & tab & revisionCount)
        on error errMsg
          set failCount to failCount + 1
          try
            tell application "Microsoft Word" to close every document saving no
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


def redline_preflight(session: WordSession, *, allow_open_docs: bool) -> str:
    """Refuse to redline while Word holds documents that are not ours.

    `word_pdf.py`'s `--allow-open-docs` is a trade the operator is entitled to
    make: it costs them Word restarts, and the export closes only the document
    it opened. Redlining cannot offer the same deal, because its *correctness*
    rests on the precondition, not just its tidiness.

    `_COMPARE` identifies the result by exclusion — it walks `document i` and
    takes the one whose name is not the base's, because `compare` returns its
    result as a new document and that is how a script names the one it means.
    That walk is sound exactly while every open document is ours. With a human's document open it can select *theirs* and save it as
    the redline: a wrong artifact that looks like a real one, which is the
    failure this pair exists to prevent.

    So the flag is accepted on the command line and declined here, with the
    reason, rather than honoured silently.
    """
    if problem := preflight(session, allow_open_docs=allow_open_docs):
        return problem
    if not session.started_clean:
        return (
            "Word has documents open. Redlining identifies its result by "
            "exclusion (the document that is not the base), which only holds "
            "while every open document is ours — with yours open it can save "
            "your document as the redline. --allow-open-docs cannot waive this. "
            "Close them and re-run."
        )
    return ""


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
    one_osascript: bool = False,
    max_passes: int = 3,
    poison_streak: int = 3,
) -> list[PairResult]:
    """Redline every pair drawn from two folders. Serial, by necessity.

    Word is a single-instance, user-session-bound application — there is no
    equivalent of LibreOffice's `-env:UserInstallation`, so a second worker
    would drive the same instance. Parallelism needs separate macOS user
    sessions or VMs (§9), which is why there is no `--jobs`.

    `one_osascript` runs the whole job as TWO monolithic AppleScripts — every
    comparison, then every PDF — instead of one `osascript` per step per pair.
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

    with Stage(prefix="wordredline") as stage:
        try:
            run = _redline_batched if one_osascript else _redline_serial
            return run(
                pairs,
                out_dir,
                docx_dir,
                emit,
                stage=stage,
                session=session,
                folder_a=folder_a,
                folder_b=folder_b,
                force=force,
                timeout=timeout,
                pdf_timeout=pdf_timeout,
                max_passes=max_passes,
                poison_streak=poison_streak,
            )
        finally:
            if owns_session:
                session.quit_if_ours()


def _redline_serial(
    pairs: list[tuple[Path, Path]],
    out_dir: Path,
    docx_dir: Path | None,
    emit: Emit,
    *,
    stage: Stage,
    session: WordSession,
    folder_a: Path,
    folder_b: Path,
    force: bool,
    timeout: float,
    pdf_timeout: float,
    max_passes: int = 3,
    poison_streak: int = 3,
) -> list[PairResult]:
    """One `osascript` per comparison, with the malformed-document path in Python."""
    results: list[PairResult] = []
    streak: list[tuple[Path, Path, Outputs]] = []
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
            streak.clear()
            note = "" if result.revisions < 0 else f", {result.revisions} revisions"
            logger.info(f"[{i}/{len(pairs)}] ok ({result.seconds:.1f}s{note}): {label}")
            if result.revisions == 0:
                logger.warning(f"  compared clean (no revisions): {label}")
        else:
            streak.append((base, revision, outputs))
            logger.error(f"[{i}/{len(pairs)}] FAIL: {label} — {result.error}")
            # Decline the repair prompt, close whatever is open, move on. A
            # restart costs ~30s and is not what a malformed document needs.
            recover_after_failure(session, stage.inbox, stage.outbox)
            if len(streak) >= poison_streak:
                # Unless they keep failing. A Word degraded by a bad document
                # answers normally and returns empty documents for everything
                # after it (§5, §7), which is what a failure run looks like.
                logger.warning(
                    f"[word] {len(streak)} failures in a row — recycling rather than "
                    "trusting Word to still be reading documents"
                )
                if session.recycle(stage.inbox, stage.outbox):
                    _replay_pairs(
                        streak, results, stage=stage, timeout=timeout, pdf_timeout=pdf_timeout
                    )
                streak.clear()
    return results


def _replay_pairs(
    pending: list[tuple[Path, Path, Outputs]],
    results: list[PairResult],
    *,
    stage: Stage,
    timeout: float,
    pdf_timeout: float,
) -> None:
    """Re-run a failure streak against a freshly restarted Word, in place.

    The streak is the reason for the restart: a Word degraded by one bad
    document answers normally and returns empty documents for everything after
    it (§5, §7). The base paragraph-count check turns those into failures rather
    than false passes, which is the half that matters — but nothing in a failure
    distinguishes Word's fault from the file's, so leaving them would report
    healthy pairs as permanently broken. Whatever fails again keeps its verdict.
    """
    for base, revision, outputs in pending:
        started = time.monotonic()
        again = _redline_one(
            base, revision, outputs, stage=stage, timeout=timeout, pdf_timeout=pdf_timeout
        )
        again.seconds = time.monotonic() - started
        if not again.ok:
            logger.info(f"[replay] still failing, so it is the pair: {base.name}")
            continue
        logger.info(f"[replay] ok after restart ({again.seconds:.1f}s): {base.name}")
        for n, prior in enumerate(results):
            if prior.base == base and prior.revision == revision and not prior.ok:
                results[n] = again
                break


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


def _redline_batched(
    pairs: list[tuple[Path, Path]],
    out_dir: Path,
    docx_dir: Path | None,
    emit: Emit,
    *,
    stage: Stage,
    session: WordSession,
    folder_a: Path,
    folder_b: Path,
    force: bool,
    timeout: float,
    pdf_timeout: float,
    max_passes: int = 3,
    poison_streak: int = 3,  # part of the shared dispatch signature; serial-only
) -> list[PairResult]:
    """Two monolithic AppleScripts: every compare, then every PDF.

    They have to be two. Word yields a comparison only as an open document, so
    every redline .docx has to exist on disk before anything can be rendered from
    it — the second script's input list is the first script's output list. Doing
    both in one script would mean one wedge losing both halves of the work.

    The second script is `word_pdf`'s own `_EXPORT_BATCH`, unchanged: a redline
    .docx is a .docx, and nothing about rendering one differs.
    """
    outcomes: dict[tuple[Path, Path], PairResult] = {}
    todo: list[tuple[Path, Path]] = []
    plans: dict[tuple[Path, Path], Outputs] = {}
    for base, revision in pairs:
        outputs = plan_outputs(base, revision, out_dir, docx_dir, emit)
        plans[(base, revision)] = outputs
        if should_skip(outputs, force=force):
            outcomes[(base, revision)] = PairResult(
                base=base,
                revision=revision,
                docx=outputs.docx,
                pdf=outputs.pdf,
                ok=True,
                skipped=True,
            )
        else:
            todo.append((base, revision))
    if not todo:
        return [outcomes[p] for p in pairs]

    # ── pass 1: every comparison ────────────────────────────────────────────
    rows: list[tuple[str, ...]] = []
    staged: dict[str, tuple[tuple[Path, Path], Path, Path, Path]] = {}
    for i, (base, revision) in enumerate(todo):
        item = str(i)
        stem = redline_stem(base, revision)
        staged_base = stage.place_as(base, safe_stage_name(i, f"base__{stem}.docx"))
        staged_rev = stage.place_as(revision, safe_stage_name(i, f"rev__{stem}.docx"))
        staged_docx = stage.outbox / safe_stage_name(i, f"{stem}.docx")
        rows.append((item, str(staged_base), str(staged_rev), str(staged_docx)))
        staged[item] = ((base, revision), staged_base, staged_rev, staged_docx)

    logger.info(f"[batch] one osascript for {len(rows)} comparison(s)")
    started = time.monotonic()
    compared = run_batch_with_resume(
        _COMPARE_BATCH,
        rows,
        stage.root or stage.inbox.parent,
        per_item_timeout=timeout,
        session=session,
        recycle_paths=(stage.inbox, stage.outbox),
        max_passes=max_passes,
        label=" compare",
    )
    per_pair = (time.monotonic() - started) / max(1, len(rows))

    # ── pass 2: every PDF, from the redlines that pass 1 actually produced ───
    pdf_rows: list[tuple[str, ...]] = []
    pdf_staged: dict[str, Path] = {}
    for item, (pair, staged_base, staged_rev, staged_docx) in staged.items():
        staged_base.unlink(missing_ok=True)
        staged_rev.unlink(missing_ok=True)
        ok, detail = compared[item]
        produced = ok and staged_docx.exists() and staged_docx.stat().st_size > 0
        if produced and plans[pair].pdf is not None:
            staged_pdf = stage.outbox / f"{staged_docx.stem}.pdf"
            pdf_rows.append((item, str(staged_docx), str(staged_pdf)))
            pdf_staged[item] = staged_pdf

    rendered: dict[str, tuple[bool, str]] = {}
    if pdf_rows:
        logger.info(f"[batch] one osascript for {len(pdf_rows)} redline PDF(s)")
        rendered = run_batch_with_resume(
            _EXPORT_BATCH,
            pdf_rows,
            stage.root or stage.inbox.parent,
            per_item_timeout=pdf_timeout,
            session=session,
            recycle_paths=(stage.inbox, stage.outbox),
            max_passes=max_passes,
            label=" pdf",
        )

    # ── deliver ─────────────────────────────────────────────────────────────
    for item, (pair, _base_in, _rev_in, staged_docx) in staged.items():
        base, revision = pair
        outputs = plans[pair]
        result = PairResult(
            base=base, revision=revision, seconds=per_pair, timing_exact=False
        )
        ok, detail = compared[item]
        result.revisions = parse_revision_count(detail) if ok else -1
        produced = staged_docx.exists() and staged_docx.stat().st_size > 0

        if not ok or not produced:
            result.error = classify_failure(0 if ok else 1, detail, produced)
            logger.error(f"[batch] FAIL: {result.label} — {result.error}")
        elif outputs.pdf is not None:
            pdf_ok, pdf_detail = rendered.get(item, (False, "PDF pass never ran"))
            staged_pdf = pdf_staged.get(item)
            pdf_made = (
                staged_pdf is not None
                and staged_pdf.exists()
                and staged_pdf.stat().st_size > 0
            )
            if pdf_ok and pdf_made:
                assert staged_pdf is not None
                _deliver(staged_pdf, outputs.pdf)
                result.pdf = outputs.pdf
                result.ok = True
            else:
                result.error = (
                    "redline saved but PDF export failed: "
                    + classify_failure(0 if pdf_ok else 1, pdf_detail, pdf_made)
                )
                logger.error(f"[batch] FAIL: {result.label} — {result.error}")
        else:
            result.ok = True

        if result.ok and outputs.docx is not None:
            _deliver(staged_docx, outputs.docx)
            result.docx = outputs.docx
        if result.ok and result.revisions == 0:
            logger.warning(f"  compared clean (no revisions): {result.label}")

        staged_docx.unlink(missing_ok=True)
        if (staged_pdf := pdf_staged.get(item)) is not None:
            staged_pdf.unlink(missing_ok=True)
        outcomes[pair] = result

    return [outcomes[p] for p in pairs]


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
        middle = f"{seconds[len(done) // 2]:.1f}"
        if all(r.timing_exact for r in done):
            table.add_row("median seconds", middle)
        else:
            # A batch pass times the whole run, not each pair in it.
            table.add_row("seconds per pair (batch avg)", middle)
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
    folder_a: Annotated[
        Path,
        typer.Option("--a", "-a", help="Folder of originals (the base of each comparison)."),
    ],
    folder_b: Annotated[
        Path, typer.Option("--b", "-b", help="Folder of revisions (compared against A).")
    ],
    out: Annotated[
        Path, typer.Option("--out", "-o", help="Where the redlines land.")
    ] = Path("redlines"),
    docx_out: Annotated[
        Path | None,
        typer.Option(
            "--docx-out", help="Separate folder for the .docx. Default: alongside --out."
        ),
    ] = None,
    emit: Annotated[
        Emit,
        typer.Option(
            "--emit", help="pdf | docx | both. Default pdf: the .docx is discarded."
        ),
    ] = Emit.PDF,
    cross: Annotated[
        bool,
        typer.Option(
            "--cross", help="Compare every A against every B instead of matching names."
        ),
    ] = False,
    swap: Annotated[
        bool, typer.Option("--swap", help="Use B as the base and A as the revision.")
    ] = False,
    force: Annotated[
        bool, typer.Option("--force", help="Redo pairs whose output exists.")
    ] = False,
    timeout: Annotated[
        float, typer.Option("--timeout", help="Seconds per comparison.")
    ] = 300.0,
    pdf_timeout: Annotated[
        float, typer.Option("--pdf-timeout", help="Seconds per PDF export.")
    ] = 180.0,
    one_osascript: Annotated[
        bool,
        typer.Option(
            "--one-redline-osascript",
            help="Run the job as TWO monolithic AppleScripts — every comparison, then "
            "every PDF — instead of one osascript per step per pair. Resumes "
            "automatically if either run wedges.",
        ),
    ] = False,
    check_preset: Annotated[
        bool,
        typer.Option(
            "--check-preset/--no-check-preset", help="Print the Word-settings reminders."
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
    if problem := redline_preflight(session, allow_open_docs=allow_open_docs):
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
            one_osascript=one_osascript,
        )
        session.quit_if_ours()
    raise typer.Exit(report_pairs(results, f"redline: {folder_a.name} → {folder_b.name}"))


if __name__ == "__main__":
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    signal.signal(signal.SIGINT, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    app()
