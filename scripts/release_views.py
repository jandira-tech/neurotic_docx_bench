#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     # The release contract (Cases/Speed models, dumps_compact), pinned to the
#     # same reviewed commit ndb's pyproject carried before #134 moved it here.
#     "bench-ops @ git+https://github.com/arthrod/bench-ops@35ab2cbeb8bc44d5059878d14176dc90c5b46f5d",
#     # Everything third-party reachable from neurotic_docx_bench.ledger.build,
#     # checked import by import (#134): the package __init__ pulls the scoring
#     # core (numpy, pillow, pymupdf, scipy, scikit-image — capped like pyproject,
#     # score.py's skimage API), tables -> docset -> pipeline adds aiofiles, the
#     # registry pyyaml, the models pydantic, and the legacy_cases snapshot
#     # download huggingface-hub (bench-ops declares pydantic and huggingface-hub
#     # too). Nothing else: typer/rich/lxml/polars and the optional torch scorer
#     # are not on this path. tests/test_ledger_build.py pins this exact list.
#     "aiofiles>=25.1.0",
#     "huggingface-hub>=2.0",
#     "numpy>=2.0",
#     "pydantic>=2.11",
#     "pymupdf>=1.24",
#     "pillow>=10.0",
#     "pyyaml>=6.0",
#     "scikit-image>=0.24,<0.28",
#     "scipy>=1.13",
# ]
# ///
"""Build, check or write the published views that need bench-ops (#134).

The half of the old `bench report` that speaks the release contract: it
downloads the legacy_cases snapshot when only the committed pointer
results/legacy_cases.ref.json exists, builds every view — the pages
(RESULTS.md, RESULTS_DETAILED.md, the README vendor table, results/scores.json)
plus the results/release/ bundle (cases/index.json, one shard per group,
speed.json) — then checks them all or freezes and writes them. `bench report`
keeps only the pages: bench-ops is not a venv dependency, it rides in the
PEP 723 block above, so the two `bench` console scripts cannot shadow each
other.

Run it as a script (uv builds the environment from the block and never installs
ndb — the repo's src/ is put on sys.path):

    uv run scripts/release_views.py [--root PATH] [--check] [--allow-no-cases]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The PEP 723 environment carries the dependencies, not the package: ndb is
# imported from this checkout's source tree.
sys.path.insert(0, str(ROOT / "src"))

from neurotic_docx_bench.ledger import build as ledger_build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="release_views.py",
        description=(
            "Build, check or write every published view that needs bench-ops: the "
            "pages plus the results/release/ bundle (the half of the old `bench "
            "report` that moved out of the venv, #134)."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root (default: the checkout this script lives in)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 when a published view is stale; write nothing",
    )
    parser.add_argument(
        "--allow-no-cases",
        action="store_true",
        help="emit the release even when no case source exists (no legacy_cases snapshot, no pointer)",
    )
    args = parser.parse_args(argv)
    return ledger_build.run_release_views(
        args.root, check=args.check, allow_no_cases=args.allow_no_cases
    )


if __name__ == "__main__":
    raise SystemExit(main())
