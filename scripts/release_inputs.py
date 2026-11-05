#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = [
#     # The same environment as scripts/release_views.py (#134): the release
#     # contract rides in bench-ops, pinned; the rest is what release_cases imports.
#     "bench-ops @ git+https://github.com/arthrod/bench-ops@6478817465f67726c1450dbeaf090a9fa7ca44b2",
#     "aiofiles>=25.1.0",
#     "huggingface-hub>=2.0",
#     "numpy>=2.0",
#     "pydantic>=2.11",
#     "pymupdf>=1.24",
#     "pillow>=10.0",
#     "pyyaml>=6.0",
#     "scikit-image>=0.24,<0.28",
#     "scipy>=1.13",
#     "typer>=0.12",
# ]
# ///
"""Fetch the PDFs a versioned release's views are built from (#180).

    uv run scripts/release_inputs.py --release-version 0.17.0 [--root PATH]

Downloads each lane's candidate PDFs and Word exports from the results dataset at
the revision the release evidence pins, hash-verified, into the folders
scripts/release_views.py reads. Files already present with the hub's bytes are
skipped; a local file with other bytes stops the run (hub_get's rule).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from neurotic_docx_bench.ledger import release_inputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="release_inputs.py", description=__doc__.splitlines()[0])
    parser.add_argument("--release-version", required=True)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    inputs = release_inputs.fetch(args.root, args.release_version)
    print(f"{len(inputs)} input folders in place for release {args.release_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
