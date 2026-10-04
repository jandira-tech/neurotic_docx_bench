#!/usr/bin/env python3
"""Where two PDFs of one document first start a page on different text.

For each document of a queue (release_conv_queue.py's queue.tsv) whose page
count is not Word's, prints the first page that opens on different words in
Word's PDF and in jubarte's, with the words each opens on and how many lines
the previous page holds in each. The page before that one is where the two
layouts part: it holds more, or less, than Word put on it.

usage (from the bench root):
  python3 scripts/first_page_divergence.py ENGINE_DIR VERSION QUEUE_TSV [--all]
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import re
import subprocess
import sys
from pathlib import Path


def page_texts(pdf: Path) -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True)
    return out.stdout.split("\f")


def words(text: str, n: int = 8) -> str:
    return " ".join(re.findall(r"\S+", text)[:n])


def lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("engine_dir", type=Path)
    ap.add_argument("version")
    ap.add_argument("queue", type=Path)
    ap.add_argument("--all", action="store_true", help="every queue row, not only page mismatches")
    args = ap.parse_args()
    sample = glob.glob(str(args.engine_dir / "release_info" / f"sample_conversion_{args.version}_*.csv"))
    if len(sample) != 1:
        sys.exit("no single conversion sample for that version")
    with open(sample[0], newline="") as f:
        paths = {r["stem"]: r for r in csv.DictReader(f)}
    with open(args.queue, newline="") as f:
        queue = list(csv.DictReader(f, delimiter="\t"))
    for row in queue:
        if not args.all and row["page_delta"] in ("", "0"):
            continue
        p = paths[row["stem"]]
        word, mine = page_texts(Path(p["word_pdf"])), page_texts(Path(p["jubarte_pdf"]))
        first = next((i for i, (a, b) in enumerate(zip(word, mine)) if words(a) != words(b)), None)
        found = {"rank": int(row["rank"]), "stem": row["stem"][:70], "pages": f'{row["word_pages"]}/{row["jubarte_pages"]}',
                 "score": row["jubarte"]}
        if first is None:
            found["first_divergent_page"] = None
        else:
            found.update({
                "first_divergent_page": first + 1,
                "word_opens": words(word[first]),
                "jubarte_opens": words(mine[first]),
                "prev_page_lines_word": lines(word[first - 1]) if first else None,
                "prev_page_lines_jubarte": lines(mine[first - 1]) if first else None,
            })
        print(json.dumps(found, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
