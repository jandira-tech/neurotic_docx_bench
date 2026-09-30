#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["neurotic-docx-bench", "typer"]
# [tool.uv.sources]
# neurotic-docx-bench = { path = "..", editable = true }
# ///
"""Release neurotic-docx-bench to PyPI and GitHub, after the Word gate.

    scripts/release.py --check   # gate only
    scripts/release.py           # gate, then tag + build + publish + GitHub release

Refuses unless Microsoft Word on this machine answers, renders, and rendered the rows
in results/bench.jsonl; unless the pages are current, the tree is clean, the tag is
free and CHANGELOG.md has the version's section. See neurotic_docx_bench.release.
"""

from neurotic_docx_bench.release import app

if __name__ == "__main__":
    app()
