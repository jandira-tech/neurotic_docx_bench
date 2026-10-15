"""Finding the files Word's drivers wrote.

``scripts/word_pdf.py`` and ``scripts/word_redline.py`` (2026-10-14) name every
file Word writes ``<stem>_byword.<ext>``, trim input file names over 80
characters on disk before Word sees them, and append one JSON line per output
to ``manifest.jsonl`` in the output folder (``original_filename``,
``path_origin``, ``converted_filename``, ``path_out``, plus ``status``,
``kind``, ``tool``, ``error``, ``seconds``, ``run_at``). A consumer that wants
"the PDF Word made for this docx" reads that manifest first, and falls back to
the name conventions, new then old, so folders rendered before the suffix
existed still resolve.
"""

from __future__ import annotations

import json
from pathlib import Path

MANIFEST_NAME = "manifest.jsonl"
BY_WORD = "_byword"


def read_manifest(folder: Path) -> list[dict[str, object]]:
    """Every line of ``folder/manifest.jsonl``, in order; empty when there is none.

    A line that does not parse is skipped rather than failing the read: the file
    is append-only across runs and a torn last line must not hide the rest.
    """
    path = folder / MANIFEST_NAME
    if not path.is_file():
        return []
    lines: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            line = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(line, dict):
            lines.append(line)
    return lines


def current_name(lines: list[dict[str, object]], original: str) -> str:
    """The name a docx has on disk now, following the manifest's ``renamed`` lines."""
    name = original
    for line in lines:
        if line.get("status") == "renamed" and line.get("original_filename") == name:
            name = str(line.get("converted_filename") or name)
    return name


def find_output(
    folder: Path, original: str, *, kind: str, ext: str, suffix: str = ""
) -> Path | None:
    """The file Word wrote in ``folder`` for the docx named ``original``.

    ``kind`` is the manifest's (``pdf``, ``accept_all``, ``reject_all``,
    ``redline``), ``ext`` the wanted extension, ``suffix`` what the run added
    before the tool mark (``_accepted_tracking``). Resolution, first hit wins:

    1. the newest manifest line for that docx (under its trimmed name, if it was
       renamed) of that kind whose output has that extension and still exists;
    2. ``<stem><suffix>_byword<ext>`` in ``folder``;
    3. ``<stem><suffix><ext>``, the spelling before 2026-10-14.
    """
    lines = read_manifest(folder)
    name = current_name(lines, original)
    for line in reversed(lines):
        if line.get("kind") != kind or line.get("original_filename") not in (name, original):
            continue
        if line.get("status") not in ("ok", "skipped"):
            continue
        out = str(line.get("path_out") or "")
        if out.endswith(ext) and Path(out).is_file():
            return Path(out)
    stem = Path(name).stem
    for candidate in (f"{stem}{suffix}{BY_WORD}{ext}", f"{stem}{suffix}{ext}"):
        if (folder / candidate).is_file():
            return folder / candidate
    return None
