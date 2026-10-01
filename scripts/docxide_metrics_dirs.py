"""docxide-pdf's Jaccard and text-boundary metrics (150 DPI) on a folder of candidate PDFs.

Candidate stems are ``<state>__<stem>``; each is matched to the Word oracle of the same stem in
``--oracle``. Resumable through the checkpoint ``score_candidates`` keeps beside ``--json``.

    uv run python scripts/docxide_metrics_dirs.py --candidate DIR --oracle DIR --json OUT.json
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from neurotic_docx_bench import docx_to_pdf as d2p
from neurotic_docx_bench.docxide_metrics import score_candidates


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--json", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 8)
    args = ap.parse_args()
    fixtures = [
        d2p.Fixture(stem=p.stem, kind="", original_stem=p.stem, docx=Path(), oracle=args.oracle / p.name)
        for p in sorted(args.candidate.glob("*.pdf"))
        if (args.oracle / p.name).is_file()
    ]
    rows = score_candidates(fixtures, args.candidate, args.json, workers=args.workers)
    print(f"{len(rows)} documents -> {args.json}")


if __name__ == "__main__":
    main()
