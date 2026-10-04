#!/usr/bin/env python3
"""Stage the Word export of the full 0.11.2 lane.

The 600 redlines identical to the release sample's (identity_0112_full.tsv)
reuse that lane's Word PDFs, linked under this lane's names. The other
2011 are linked into jubarte-0.11.2-full/todo for scripts/word_pdf.py,
except a pair whose base or next is on corpus/word/notices/blacklist.tsv
(Word hangs on it): those are listed in blacklisted.txt and score as Word
failures of the source, not of jubarte.
"""

import csv
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LANE = HERE / "jubarte-0.11.2-full"
SAMPLE_PDF = HERE / "jubarte-0.11.2" / "pdf_by_word"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    black = {line.split("\t")[0] for line in (ROOT / "corpus/word/notices/blacklist.tsv").read_text().splitlines() if line}
    verdict = dict(line.split("\t") for line in (HERE / "identity_0112_full.tsv").read_text().splitlines())
    pdf_dir, todo = LANE / "pdf_by_word", LANE / "todo"
    pdf_dir.mkdir(exist_ok=True)
    todo.mkdir(exist_ok=True)
    reused = queued = 0
    blacklisted = []
    with open(HERE / "gen_pairs.csv", newline="") as f:
        for row in csv.DictReader(f):
            key = row["key"]
            if verdict.get(key) == "same":
                src = SAMPLE_PDF / f"{key}_jubarte-0.11.2.pdf"
                dst = pdf_dir / f"{key}_jubarte-0.11.2-full.pdf"
                if src.exists() and not dst.exists():
                    dst.symlink_to(src)
                reused += src.exists()
                continue
            sources = [ROOT / "corpus/word" / f"{row[k]}.docx" for k in ("base", "next")]
            if any(s.exists() and sha(s) in black for s in sources):
                blacklisted.append(key)
                continue
            link = todo / f"{key}_jubarte-0.11.2-full.docx"
            if not link.exists():
                link.symlink_to(LANE / "docx" / link.name)
            queued += 1
    (LANE / "blacklisted.txt").write_text("".join(f"{k}\n" for k in blacklisted))
    print(f"reused {reused} Word PDFs | queued {queued} for Word | blacklisted {len(blacklisted)}")


if __name__ == "__main__":
    main()
