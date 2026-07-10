"""Accept / reject tracked changes in DOCX files, wrapping the docx-revisions package
(https://github.com/balalofernandez/docx-revisions — see README provenance).

`bench accept <in_folder> --out <out_folder>` walks a folder of tracked-change DOCX and
writes an accepted (or rejected) copy of each, e.g. to turn the Word redline corpus into
its accepted form (comparable to corpus/word_based/docx_accepted_word).
"""

from __future__ import annotations

import shutil
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from docx.oxml.ns import qn
from docx_revisions import RevisionDocument


def _strip_paragraph_mark_revisions(doc: RevisionDocument) -> None:
    """Remove residual paragraph-mark revision markers that docx-revisions leaves behind.

    docx-revisions accepts/rejects run- and block-level ``<w:ins>``/``<w:del>``, but leaves
    the paragraph-glyph revisions stored as ``<w:ins>``/``<w:del>`` children of a
    ``<w:pPr>``'s ``<w:rPr>`` — which Word still renders as tracked changes. We strip those
    markers so the result shows NO revisions (the "Word valid" bar).

    LIMITATION: a *deleted* paragraph mark, fully accepted, should MERGE its paragraph with
    the next; here we only remove the marker (content preserved, paragraphs not merged).
    Sufficient for the bench's accepted-corpus comparison; flagged for a stricter pass.
    """
    # Strip the residual markers in-memory on the wrapped python-docx Document
    # (rdoc.document.element) before save() — no reopen/reparse round-trip.
    for rpr in doc.document.element.iter(qn("w:rPr")):
        for tag in ("w:ins", "w:del"):
            for el in list(rpr.findall(qn(tag))):
                rpr.remove(el)


@dataclass(frozen=True)
class ChangeResult:
    source: Path
    out: Path | None
    ok: bool
    error: str | None = None


def accept_all(in_path: Path | str, out_path: Path | str) -> Path:
    """Accept every tracked change in ``in_path``, saving to ``out_path``."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(in_path, out)
    rdoc = RevisionDocument(str(out))
    rdoc.accept_all()
    _strip_paragraph_mark_revisions(rdoc)
    rdoc.save(str(out))
    return out


def reject_all(in_path: Path | str, out_path: Path | str) -> Path:
    """Reject every tracked change in ``in_path``, saving to ``out_path``."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(in_path, out)
    rdoc = RevisionDocument(str(out))
    rdoc.reject_all()
    _strip_paragraph_mark_revisions(rdoc)
    rdoc.save(str(out))
    return out


def _process_one(args: tuple[Path, Path, bool]) -> ChangeResult:
    """Worker for process_folder — accept/reject a single DOCX (process-safe).

    Must be a module-level function so ProcessPoolExecutor can pickle it.
    """
    docx, out, reject = args
    if docx.name.startswith("~$"):  # skip Word lock/temp files
        return ChangeResult(source=docx, out=None, ok=False, error="skipped (lock file)")
    try:
        apply = reject_all if reject else accept_all
        apply(docx, out)
        return ChangeResult(source=docx, out=out, ok=True)
    except Exception as exc:
        return ChangeResult(source=docx, out=None, ok=False, error=str(exc))


def process_folder(
    in_dir: Path | str,
    out_dir: Path | str,
    *,
    reject: bool = False,
    jobs: int = 8,
) -> list[ChangeResult]:
    """Accept (or reject) tracked changes for every ``*.docx`` in ``in_dir`` → ``out_dir``.

    Uses a process pool (``jobs`` workers) because ``docx-revisions`` / ``python-docx``
    operations are CPU-bound and the GIL would serialize them under threads.
    """
    in_dir = Path(in_dir)
    out_dir = Path(out_dir)
    if not in_dir.is_dir():
        raise NotADirectoryError(f"input is not a directory: {in_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    docs = sorted(
        d for d in in_dir.glob("*.docx") if not d.name.startswith("~$")
    )
    if not docs:
        return []

    tasks = [(docx, out_dir / docx.name, reject) for docx in docs]
    if jobs and jobs > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            return list(pool.map(_process_one, tasks))
    return [_process_one(t) for t in tasks]
