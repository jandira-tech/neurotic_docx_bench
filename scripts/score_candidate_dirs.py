"""Score a folder of candidate PDFs (stems ``<state>__<stem>``) against the Word oracle folder.

Writes per-document scores to ``--json`` and a resumable checkpoint beside it; page rasters
live under ``--work`` and are deleted when scoring ends.

    uv run python scripts/score_candidate_dirs.py --candidate results/docxide_0.17.1_work/candidate \
        --oracle results/jubarte_0.10.1_docx_to_pdf_work/oracle --json results/docx_to_pdf_docxide_0.17.1.json
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from neurotic_docx_bench.docx_to_pdf import score_folder_pair


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--oracle", type=Path, required=True)
    ap.add_argument("--json", type=Path, required=True)
    ap.add_argument("--work", type=Path)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 8)
    ap.add_argument("--dpi", type=int, default=144)
    ap.add_argument(
        "--only-missing", action="store_true",
        help="score only candidates the checkpoint holds no row for (a regenerated PDF may differ in bytes)",
    )
    args = ap.parse_args()
    work = args.work or args.json.with_suffix(".work")
    checkpoint = args.json.with_suffix(".checkpoint.jsonl")
    candidate = args.candidate
    if args.only_missing and checkpoint.is_file():
        done = {json.loads(line)["key"] for line in checkpoint.read_text().splitlines() if line.endswith("}")}
        candidate = work.with_name(work.name + ".todo")
        shutil.rmtree(candidate, ignore_errors=True)
        candidate.mkdir(parents=True)
        for pdf in args.candidate.glob("*.pdf"):
            if pdf.stem not in done:
                (candidate / pdf.name).symlink_to(pdf.resolve())
        print(f"{len(done)} already scored, {len(list(candidate.glob('*.pdf')))} to score", flush=True)
    result = score_folder_pair(args.oracle, candidate, work, dpi=args.dpi, jobs=args.jobs, checkpoint=checkpoint)
    if candidate != args.candidate:
        shutil.rmtree(candidate, ignore_errors=True)
    rows = {}
    for line in checkpoint.read_text().splitlines():
        if line.endswith("}"):
            row = json.loads(line)
            rows[row["key"]] = row["result"]
    args.json.write_text(json.dumps({"n": len(rows), "scores": rows}, indent=1, default=str))
    result = rows
    shutil.rmtree(work, ignore_errors=True)  # rasters are not kept
    print(f"{len(result)} documents -> {args.json}")


if __name__ == "__main__":
    main()
