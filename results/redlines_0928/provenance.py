"""Label every Word-made file of the 0928 tool runs with its provenance.

    uv run python results/redlines_0928/provenance.py            # dry run: print what would change
    uv run python results/redlines_0928/provenance.py --apply    # rename folders, write manifests

Two kinds of folder hold files Microsoft Word made from a tool's redline:

- ``<tool>/pdf`` -> ``<tool>/pdf_by_word``: the tool's redline DOCX (``<tool>/docx``)
  opened in Word and exported to PDF by ``scripts/word_pdf.py``.
- ``<tool>/accepted/out`` -> ``<tool>/accepted/by_word``: the tool's redline
  (``<tool>/accepted/src``) opened in Word, every tracked change accepted, saved as DOCX,
  and that DOCX exported to PDF (``word_pdf.py --accept-all``).

The PDFs themselves carry no Word marker (Word for Mac exports through macOS, so the PDF
``Producer`` is ``Quartz PDFContext``), so provenance lives next to them: each folder gets
``PROVENANCE.md`` and ``provenance.csv`` with one row per file (the redline tool and its
version, the source DOCX and its sha256, what Word did, the file's sha256 and the PDF
``Producer``/creation date). Nothing is deleted; a folder that is already renamed is only
re-labelled. Refuses to rename while a ``word_pdf.py`` process is running.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import plistlib
import subprocess
import sys
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent
TOOLS = {
    "jubarte-rust": "jubarte-redlines 0.9.3 @673aff74 (native CLI)",
    "docxodus": "docxodus 12.6.4",
    "superdoc": "superdoc-sdk 2.15.0",
}
WORD_PLIST = Path("/Applications/Microsoft Word.app/Contents/Info.plist")
# (old name, new name, source folder relative to the tool, what Word did)
KINDS = [
    ("pdf", "pdf_by_word", "docx", "opened the redline DOCX in Word and exported it to PDF"),
    (
        "accepted/out",
        "accepted/by_word",
        "accepted/src",
        "opened the redline DOCX in Word, accepted all tracked changes, saved the DOCX, exported it to PDF",
    ),
]
FIELDS = [
    "file",
    "kind",
    "redline_tool",
    "redline_tool_version",
    "source_docx",
    "source_sha256",
    "made_by",
    "word_action",
    "sha256",
    "pdf_producer",
    "pdf_created",
]


def word_version() -> str:
    info = plistlib.loads(WORD_PLIST.read_bytes())
    return f"Microsoft Word {info['CFBundleShortVersionString']} ({info['CFBundleVersion']})"


def sha256(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def word_running_batch() -> bool:
    out = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True).stdout
    return any("word_pdf.py" in line and "provenance.py" not in line for line in out.splitlines())


def source_for(file: Path, src_dir: Path, tool: str) -> Path | None:
    """The tool redline this Word file came from, matched by stem."""
    stem = file.stem
    for cand in (f"{stem}.docx", f"{stem.replace('_accepted_tracking_', '_')}.docx"):
        if (src_dir / cand).exists():
            return src_dir / cand
    # accepted copies are named <cmp>_accepted_tracking_<tool>; sources <cmp>_<tool> or <key>_<tool>
    cmp_id = stem.removesuffix(f"_accepted_tracking_{tool}")
    hits = sorted(src_dir.glob(f"{cmp_id}*.docx"))
    return hits[0] if len(hits) == 1 else None


def rows_for(folder: Path, src_dir: Path, tool: str, action: str, made_by: str) -> list[dict]:
    rows = []
    for f in sorted(p for p in folder.iterdir() if p.suffix in (".pdf", ".docx")):
        src = source_for(f, src_dir, tool)
        producer = created = ""
        if f.suffix == ".pdf":
            with pymupdf.open(f) as doc:
                producer = doc.metadata.get("producer", "")
                created = doc.metadata.get("creationDate", "")
        rows.append(
            {
                "file": f.name,
                "kind": "pdf rendered by Word" if f.suffix == ".pdf" else "docx saved by Word",
                "redline_tool": tool,
                "redline_tool_version": TOOLS[tool],
                "source_docx": str(src.relative_to(HERE)) if src else "",
                "source_sha256": sha256(src) if src else "",
                "made_by": made_by,
                "word_action": action,
                "sha256": sha256(f),
                "pdf_producer": producer,
                "pdf_created": created,
            }
        )
    return rows


def readme(tool: str, action: str, made_by: str, rows: list[dict], src_rel: str) -> str:
    pdfs = sum(r["file"].endswith(".pdf") for r in rows)
    docx = len(rows) - pdfs
    return (
        f"# Made by Microsoft Word from {tool} redlines\n\n"
        f"Every file in this folder was produced by **{made_by}**, not by {tool}.\n\n"
        f"- Redline tool: {TOOLS[tool]}\n"
        f"- Source redlines: `{src_rel}/` (the DOCX files {tool} generated)\n"
        f"- What Word did: {action}\n"
        f"- Driver: `scripts/word_pdf.py` (one osascript per batch)\n"
        f"- Files: {pdfs} PDF, {docx} DOCX\n\n"
        "The PDFs carry no Word marker in their metadata: Word for Mac exports through macOS, "
        "so the PDF Producer reads `Quartz PDFContext`. `provenance.csv` lists each file with "
        "its source DOCX, both sha256 values and the PDF Producer and creation date.\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="rename folders and write the manifests")
    ap.add_argument("--tools", nargs="*", default=list(TOOLS))
    args = ap.parse_args()
    if args.apply and word_running_batch():
        print("word_pdf.py is running; not renaming folders it may still write to", file=sys.stderr)
        return 2
    made_by = f"{word_version()} via scripts/word_pdf.py"
    for tool in args.tools:
        for old_rel, new_rel, src_rel, action in KINDS:
            old, new = HERE / tool / old_rel, HERE / tool / new_rel
            if old.exists() and new.exists():
                print(f"{tool}: both {old_rel} and {new_rel} exist; resolve by hand", file=sys.stderr)
                return 1
            folder = new if new.exists() else old
            if not folder.exists():
                print(f"{tool}: no {old_rel}")
                continue
            rows = rows_for(folder, HERE / tool / src_rel, tool, action, made_by)
            unmatched = sum(not r["source_docx"] for r in rows)
            print(f"{tool}: {folder.relative_to(HERE)} -> {new_rel}: {len(rows)} files, {unmatched} without a source match")
            if not args.apply:
                continue
            if folder == old:
                old.rename(new)
            with (new / "provenance.csv").open("w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(rows)
            (new / "PROVENANCE.md").write_text(readme(tool, action, made_by, rows, f"{tool}/{src_rel}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
