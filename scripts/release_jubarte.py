#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["neurotic-docx-bench", "typer"]
# [tool.uv.sources]
# neurotic-docx-bench = { path = "..", editable = true }
# ///
"""Score a jubarte release on the bench and open the results pull request.

    scripts/release_jubarte.py 0.10.2 --plan
    scripts/release_jubarte.py 0.10.2 [--only STAGES] [--skip STAGES] [--no-hub]

Stages: install, convert, metrics, redlines (Word), report, publish. See
neurotic_docx_bench.jubarte_bench_release.

The engine's release_info/ evidence comes from the sample-based flow instead:
uv run python -m neurotic_docx_bench.jubarte_release_info x.y.z --engine-dir …
"""

from neurotic_docx_bench.jubarte_bench_release import app

if __name__ == '__main__':
    app()
