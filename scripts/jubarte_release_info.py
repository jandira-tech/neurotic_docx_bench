#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["neurotic-docx-bench", "typer"]
# [tool.uv.sources]
# neurotic-docx-bench = { path = "..", editable = true }
# ///
"""Write a jubarte release's six release_info/ evidence files.

    scripts/jubarte_release_info.py 0.11.3 --plan
    scripts/jubarte_release_info.py 0.11.3 --engine-dir src/neurotic_docx_bench/utils/jubarte/jubarte-redlines --binary PATH
        [--convert-set CSV] [--redline-set CSV] [--only STAGES] [--skip STAGES]

Stages: install, sets (the fixed sets, #130), generate, export (Word),
measure, convert, write — jubarte only; the comparators are read from the
vendor refresh lanes (#129). --draw-sample runs the old flow (sample, docxodus
and soffice included) for regenerating archived evidence. See
neurotic_docx_bench.jubarte_release_info.

The full-corpus scoring that publishes the bench's own pages is
scripts/release_jubarte.py.
"""

from neurotic_docx_bench.jubarte_release_info import app

if __name__ == '__main__':
    app()
