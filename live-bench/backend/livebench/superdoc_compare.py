# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Single pair through the benchmark's existing yuch85 adapter, never a batch."""

import os
import sys
import tempfile
from pathlib import Path

from neurotic_docx_bench.superdoc_redlines_gen import generate_one


def main():
    previous, current, output = map(Path, sys.argv[1:])
    with tempfile.TemporaryDirectory(prefix="livebench-superdoc-") as tmp:
        generate_one(
            previous,
            current,
            output,
            repo=Path(os.environ.get("SUPERDOC_REPO", "/opt/superdoc-redlines")),
            author="Live Bench",
            workdir=Path(tmp),
        )


if __name__ == "__main__":
    main()
