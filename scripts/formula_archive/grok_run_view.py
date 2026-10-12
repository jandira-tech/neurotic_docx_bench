# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Rebuild the old working-folder layout the archived probes read, as links into corpus/.

    uv run python scripts/formula_archive/grok_run_view.py     # → results/grok_run_view/{grok_run,grok_run_archive}/...

The probes here were written against `grok_run/` (removed 2026-09-30, never in git) and
`~/temp/T/grok_run_archive/` (removed 2026-10-11). Every Word file of those folders survives in
`corpus/` under a new name; this maps each original path back to it:

* `corpus/word/notices/RENAMED.csv` — original → new, for corpus/word;
* `corpus/libreoffice/word_map.csv` — origin → LibreOffice render;
* `corpus/word_unindexed/sources.tsv` — origin_path → path, for corpus/word_unindexed;
* `results/grok_run_removal/deleted_20261011.tsv` — files deleted as `duplicate_of_corpus`,
  found again by sha256 in `corpus/MANIFEST.sha256.json`.

What it cannot give back are the tool outputs those folders also held (jubarte, LibreOffice and
docxide-pdf renders, wr0926 A–D, en_jubarte_*): they were not Word files and were deleted.
Links are relative, so the view survives a move of the repo; `corpus/`'s files must be present
(`uv run bench fixtures download`) for them to resolve.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "corpus"
VIEW = ROOT / "results" / "grok_run_view"


def mapping() -> dict[str, Path]:
    """Original path (relative to ~/temp/T, e.g. ``grok_run/fixtures_500/x.docx``) → file in corpus/."""
    out: dict[str, Path] = {}
    for r in csv.DictReader(open(CORPUS / "word/notices/RENAMED.csv")):
        out[r["original"]] = CORPUS / "word" / r["new"]
    for r in csv.DictReader(open(CORPUS / "libreoffice/word_map.csv")):
        if r.get("origin"):
            out.setdefault(r["origin"], CORPUS / "libreoffice" / r["libreoffice_pdf"])
    for r in csv.DictReader(open(CORPUS / "word_unindexed/sources.tsv"), delimiter="\t"):
        out.setdefault(r["origin_path"], CORPUS / "word_unindexed" / r["path"])
    by_sha: dict[str, str] = {}
    for rel, sha in json.loads((CORPUS / "MANIFEST.sha256.json").read_text())["files"].items():
        by_sha.setdefault(sha, rel)
    ledger = ROOT / "results/grok_run_removal/deleted_20261011.tsv"
    for r in csv.DictReader(open(ledger), delimiter="\t"):
        if r["reason"] == "duplicate_of_corpus" and r["sha256"] in by_sha:
            out.setdefault(r["path"], CORPUS / by_sha[r["sha256"]])
    out.setdefault("grok_run/word_blacklist/blacklist.tsv", CORPUS / "word/notices/blacklist.tsv")
    return out


def main() -> None:
    if VIEW.exists():
        shutil.rmtree(VIEW)
    m = mapping()
    for orig, target in sorted(m.items()):
        if not orig.startswith(("grok_run/", "grok_run_archive/")):
            continue
        link = VIEW / orig
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(os.path.relpath(target, link.parent))
    tops: dict[str, int] = {}
    for orig in m:
        if orig.startswith(("grok_run/", "grok_run_archive/")):
            key = "/".join(orig.split("/")[:2])
            tops[key] = tops.get(key, 0) + 1
    print(f"{sum(tops.values())} links under {VIEW.relative_to(ROOT)}")
    for k, n in sorted(tops.items(), key=lambda kv: -kv[1])[:25]:
        print(f"  {n:5d}  {k}")


if __name__ == "__main__":
    main()
