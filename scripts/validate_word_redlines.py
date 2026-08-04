#!/usr/bin/env python3
"""Validate the Word-produced redlines and stamp the provenance manifest.

Plan reference: ``plans/agent-execution-plan.md`` Chapter 2.3, teaching doc §5.

Per redline this checks, in order:

1. the file exists,
2. the zip container is intact (``testzip``),
3. ``word/document.xml`` is present and parses as XML,
4. it carries at least one ``w:ins`` or ``w:del`` — a compare that produced no
   tracked changes yields a document that opens fine and looks valid but is
   worthless as ground truth, so it must never be shipped as one.

Successful rows get their SHA-256 written back into ``pair_provenance.csv``, so
every row ends up carrying all three hashes (base, next, redline).

The LibreOffice render smoke test is deliberately NOT here: rendering the whole
folder with ``bench render`` produces the oracle PDFs anyway, and a document
that fails to render simply produces no PDF.

Usage::

    uv run python scripts/validate_word_redlines.py [--jobs 12]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import NamedTuple
from xml.etree import ElementTree

DEFAULT_CORPUS = Path(__file__).resolve().parents[1] / "corpus" / "word_redlines_superdoc"

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_INS = f"{_W_NS}ins"
_DEL = f"{_W_NS}del"


class Result(NamedTuple):
    path: Path
    status: str
    sha256: str
    insertions: int
    deletions: int
    error: str


def validate_one(path: Path) -> Result:
    """Validate a single redline docx. Never raises — every failure is a status."""
    if not path.is_file() or path.stat().st_size == 0:
        return Result(path, "missing", "", 0, 0, "file absent or empty")

    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()

    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                return Result(path, "corrupt_zip", sha, 0, 0, "bad member in archive")
            try:
                document = archive.read("word/document.xml")
            except KeyError:
                return Result(path, "no_document_xml", sha, 0, 0, "word/document.xml absent")
    except zipfile.BadZipFile as exc:
        return Result(path, "corrupt_zip", sha, 0, 0, str(exc))

    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as exc:
        return Result(path, "bad_xml", sha, 0, 0, str(exc))

    # Count ELEMENTS, not substrings: `w:insideH` (table borders) starts with
    # `w:ins`, so a text search reports tracked insertions in documents that
    # have none and lets an empty redline pass as valid.
    insertions = sum(1 for _ in root.iter(_INS))
    deletions = sum(1 for _ in root.iter(_DEL))
    if insertions == 0 and deletions == 0:
        return Result(path, "empty_redline", sha, 0, 0, "no w:ins or w:del elements")

    return Result(path, "ok", sha, insertions, deletions, "")


def _validate_path(path_str: str) -> tuple[str, str, str, int, int, str]:
    r = validate_one(Path(path_str))
    return (str(r.path), r.status, r.sha256, r.insertions, r.deletions, r.error)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--jobs", type=int, default=12)
    args = parser.parse_args(argv)

    provenance = args.corpus / "pair_provenance.csv"
    redline_dir = args.corpus / "docx_redlines_word"
    if not provenance.is_file():
        print(f"missing {provenance} — run scripts/build_superdoc_pairs.py first", file=sys.stderr)
        return 2

    with provenance.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
        fields = list(rows[0]) if rows else []

    paths = [str(redline_dir / row["redline_docx"]) for row in rows]
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(_validate_path, paths, chunksize=8))

    counts: dict[str, int] = {}
    total_ins = total_del = 0
    for row, (_, status, sha, ins, dels, error) in zip(rows, results, strict=True):
        row["status"] = status
        row["redline_sha256"] = sha if status == "ok" else ""
        row["error"] = error
        counts[status] = counts.get(status, 0) + 1
        total_ins += ins
        total_del += dels

    with provenance.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    ok = counts.get("ok", 0)
    print(f"validated {len(rows)} rows -> {provenance}")
    for status, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {status:16} {n}")
    print(f"  tracked changes: {total_ins} insertions, {total_del} deletions")
    print(f"  ok rate: {ok}/{len(rows)} ({100 * ok / max(1, len(rows)):.1f}%)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
