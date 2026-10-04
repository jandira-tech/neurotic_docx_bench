#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["neurotic-docx-bench", "typer"]
# [tool.uv.sources]
# neurotic-docx-bench = { path = "..", editable = true }
# ///
"""Write a jubarte release's six release_info/ evidence files.

    scripts/jubarte_release_info.py 0.11.3 --plan
    scripts/jubarte_release_info.py 0.11.3 --engine-dir ../jubarte-redlines --binary PATH
        [--adopt-redline CSV] [--adopt-conversion FILE] [--only STAGES] [--skip STAGES]

Stages: install, sample, generate, export (Word), measure, convert, score,
write. See neurotic_docx_bench.jubarte_release_info.

The full-corpus scoring that publishes the bench's own pages is
scripts/release_jubarte.py.
"""

from neurotic_docx_bench.jubarte_release_info import app

if __name__ == '__main__':
    app()
