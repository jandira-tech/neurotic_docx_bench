# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""One-off (2026-10-11): move the DOCX→PDF pins from the old pool names to corpus/ names.

    uv run python scripts/docx_to_pdf_migrate_pins.py

The two tracks were pinned as ``kind<TAB>original_stem`` rows plus a sha256 per Word PDF, under
pool folders (``pdf_source/``, ``pdf_accepted_word/``, …) that the corpus build renamed. Each
pinned PDF is found again by its sha256 in corpus/MANIFEST.sha256.json (every one matches exactly
one file); its DOCX is the one corpus/word's tables give that PDF (``pdf`` or ``pdf_prior``), or
the ``docx_*`` sibling in corpus/word_unindexed. Pins whose DOCX the corpus does not hold are
dropped and listed. Writes src/neurotic_docx_bench/docx_to_pdf_pins/<track>.tsv.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "corpus"
OLD = CORPUS / "word_unindexed/no_comments_pdf_was_generated_by_word"
OUT = ROOT / "src/neurotic_docx_bench/docx_to_pdf_pins"
TRACKS = {  # track: (old pin list, old sha manifest, {kind: old pdf folder})
    "docx_to_pdf": ("docx_to_pdf_fixtures.txt", "docx_to_pdf_oracle_sha256.json",
                    {"accepted": "pdf_accepted_word", "redline_randomized": "pdf_redlines_randomized"}),
    "docx_to_pdf_no_redline_docs": ("docx_to_pdf_no_redline_fixtures.txt", "docx_to_pdf_no_redline_oracle_sha256.json",
                                    {"source": "pdf_source", "source_randomized": "pdf_source_randomized"}),
}


def docx_of_pdf() -> dict[str, str]:
    out: dict[str, str] = {}
    for table in ("documents.csv", "comparisons.csv"):
        for r in csv.DictReader(open(CORPUS / "word" / table)):
            for col in ("pdf", "pdf_prior"):
                if r[col]:
                    out["word/" + r[col]] = "word/" + r["docx"]
    return out


def main() -> None:
    files = json.loads((CORPUS / "MANIFEST.sha256.json").read_text())["files"]
    by_sha: dict[str, list[str]] = defaultdict(list)
    for rel, sha in files.items():
        by_sha[sha].append(rel)
    docx_of = docx_of_pdf()
    OUT.mkdir(parents=True, exist_ok=True)
    for track, (pin_list, sha_json, folders) in TRACKS.items():
        shas = json.loads((OLD / sha_json).read_text())
        shas = shas.get("files", shas)
        rows, dropped, seen = [], [], set()
        for raw in (OLD / pin_list).read_text().splitlines():
            if not raw.strip() or raw.startswith("#"):
                continue
            kind, original = raw.split("\t")
            sha = shas[f"{folders[kind]}/{original}.pdf"]
            (pdf,) = by_sha[sha]  # exactly one file per pinned PDF
            if pdf in docx_of:
                docx = docx_of[pdf]
            else:  # corpus/word_unindexed keeps the pool folders: pdf_x/ ↔ docx_x/
                parts = pdf.split("/")
                parts[-2] = parts[-2].replace("pdf_", "docx_", 1)
                parts[-1] = parts[-1][:-4] + ".docx"
                docx = "/".join(parts)
            if docx not in files:
                dropped.append((kind, original, pdf))
                continue
            stem = Path(pdf).stem + ("__prior" if "/pdf_prior/" in pdf else "")
            assert (kind, stem) not in seen, (kind, stem)
            seen.add((kind, stem))
            rows.append((kind, stem, docx, pdf, sha, original))
        dest = OUT / f"{track}.tsv"
        with dest.open("w", newline="") as fh:
            fh.write(f"# {track}: Word-export DOCX→PDF pins, paths relative to corpus/ (migrated 2026-10-11\n")
            fh.write("# from the pool names by scripts/docx_to_pdf_migrate_pins.py; original_stem is the old name).\n")
            for kind, original, pdf in dropped:
                fh.write(f"# dropped, no DOCX in corpus/: {kind}\t{original}\t{pdf}\n")
            w = csv.writer(fh, delimiter="\t", lineterminator="\n")
            w.writerow(("kind", "stem", "docx", "pdf", "pdf_sha256", "original_stem"))
            w.writerows(rows)
        print(f"{track}: {len(rows)} pins, {len(dropped)} dropped -> {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
