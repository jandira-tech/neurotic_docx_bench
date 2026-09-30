"""Word's Accept All / Reject All of pool comparisons: ``corpus/word/<action>/{docx,pdf}/<key>.*``.

``pools/accept_reject_split.csv`` (``key, pool, state, action, seed``) assigns each
comparison one action. ``scripts/word_pdf.py --accept-all`` / ``--reject-all`` writes
``<key>_accepted_tracking`` / ``<key>_rejected_tracking`` (docx and PDF) into an output
folder; here each is filed under the comparison's own key, so a tool's accepted copy
``<key>_<tool>`` pairs with it the way its redline pairs with the Word redline.
``pools/<action>.csv`` lists every row of the split with its status: ``ok`` (docx and
PDF), ``no_pdf`` (Word saved it but did not print it) or ``failed`` (no output).
Origins are read, never written; the build copies and is idempotent.
"""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Mapping
from pathlib import Path

from neurotic_docx_bench import hub
from neurotic_docx_bench.word_corpus import COMPARISONS_NAME, POOLS_DIR, copy_file

SPLIT_NAME = "accept_reject_split.csv"
SUFFIX = {"accept_all": "_accepted_tracking", "reject_all": "_rejected_tracking"}
COLUMNS = ("key", "pool", "state", "status", "docx", "pdf", "source_docx", "origin_docx", "origin_pdf")


class WordActionsError(Exception):
    pass


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _file(src: Path, dst: Path) -> None:
    if dst.exists():
        if hub.sha256_file(dst) == hub.sha256_file(src):
            return
        dst.unlink()  # our own earlier copy of an output Word has since rewritten
    copy_file(src, dst)


def build(root: Path, dest: Path, outputs: Mapping[str, Path]) -> dict[str, dict[str, int]]:
    """File the Word outputs of every split row; returns ``{action: {status: n}}``."""
    root, dest = Path(root), Path(dest)
    split = dest / POOLS_DIR / SPLIT_NAME
    if not split.is_file():
        raise WordActionsError(f"no split list at {split}")
    for action, folder in outputs.items():
        if action not in SUFFIX:
            raise WordActionsError(f"unknown action {action!r} (known: {sorted(SUFFIX)})")
        if not Path(folder).is_dir():
            raise WordActionsError(f"no output folder {folder} for {action}")
    sources: dict[str, str] = {}
    if (dest / COMPARISONS_NAME).is_file():
        with (dest / COMPARISONS_NAME).open(newline="") as fh:
            sources = {r["key"]: r["docx"] for r in csv.DictReader(fh)}
    with split.open(newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["action"] in outputs]
    counts: dict[str, Counter[str]] = {action: Counter() for action in outputs}
    listed: dict[str, list[tuple[str, ...]]] = {action: [] for action in outputs}
    for row in rows:
        action, key = row["action"], row["key"]
        folder = Path(outputs[action])
        origin_docx = folder / f"{key}{SUFFIX[action]}.docx"
        origin_pdf = folder / f"{key}{SUFFIX[action]}.pdf"
        docx = pdf = ""
        if origin_docx.is_file():
            docx = f"{action}/docx/{key}.docx"
            _file(origin_docx, dest / docx)
        if origin_docx.is_file() and origin_pdf.is_file():
            pdf = f"{action}/pdf/{key}.pdf"
            _file(origin_pdf, dest / pdf)
        status = "ok" if pdf else "no_pdf" if docx else "failed"
        counts[action][status] += 1
        listed[action].append((
            key,
            row["pool"],
            row["state"],
            status,
            docx,
            pdf,
            sources.get(key, ""),
            _rel(origin_docx, root) if docx else "",
            _rel(origin_pdf, root) if pdf else "",
        ))
    for action, entries in listed.items():
        with (dest / POOLS_DIR / f"{action}.csv").open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(COLUMNS)
            w.writerows(sorted(entries))
    hub.write_manifest(dest)
    return {action: dict(c) for action, c in counts.items()}
