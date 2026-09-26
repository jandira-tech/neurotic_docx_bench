#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12"]
# ///
"""Unpack redline docx files and reject any that are not the named pair.

Filenames are ``<base-stem>__vs__<revision-stem>.docx``. Word may rewrite
punctuation, headers and field results, so the texts do not have to match.
What this refuses is a file whose before-text is not the base and whose
after-text is not the revision — the symptom of Word saving a leftover
document under the next pair's name.

    ./check_redline_identity.py --a grok_run/folder_a_100 --b grok_run/folder_b_10 \\
        --redlines grok_run/compared_a_100_vs_b_10_docx \\
        --pdf-dir grok_run/compared_a_100_vs_b_10_pdf --delete
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from redline_identity import matches_pair

app = typer.Typer(add_completion=False, help=__doc__)


def _stem_pair(path: Path) -> tuple[str, str] | None:
    if "__vs__" not in path.stem:
        return None
    base, revision = path.stem.split("__vs__", 1)
    if not base or not revision:
        return None
    return base, revision


@app.command()
def main(
    folder_a: Path = typer.Option(..., "--a", help="Folder of base documents."),
    folder_b: Path = typer.Option(..., "--b", help="Folder of revision documents."),
    redlines: Path = typer.Option(..., "--redlines", help="Folder of A__vs__B.docx redlines."),
    pdf_dir: Path | None = typer.Option(
        None, "--pdf-dir", help="Matching PDFs to delete along with a bad docx."
    ),
    delete: bool = typer.Option(False, "--delete", help="Delete redlines that fail the check."),
) -> None:
    """Exit 1 when any redline is not the pair its filename names."""
    bad = 0
    checked = 0
    for path in sorted(redlines.glob("*.docx")):
        pair = _stem_pair(path)
        if pair is None:
            print(f"SKIP {path.name}: name is not <base>__vs__<revision>")
            continue
        base_stem, revision_stem = pair
        base = folder_a / f"{base_stem}.docx"
        revision = folder_b / f"{revision_stem}.docx"
        if not base.is_file() or not revision.is_file():
            print(f"BAD  {path.name}: named source is missing")
            bad += 1
            if delete:
                path.unlink()
                if pdf_dir is not None:
                    (pdf_dir / f"{path.stem}.pdf").unlink(missing_ok=True)
            continue
        checked += 1
        verdict = matches_pair(path, base, revision)
        if verdict.ok:
            continue
        bad += 1
        print(
            f"BAD  {base_stem[:12]} vs {revision_stem[:12]} "
            f"before/base={verdict.sim_base:.2f} after/revision={verdict.sim_revision:.2f}"
        )
        if delete:
            path.unlink()
            if pdf_dir is not None:
                pdf = pdf_dir / f"{path.stem}.pdf"
                pdf.unlink(missing_ok=True)
            print("     deleted")
    print(f"checked={checked} bad={bad}")
    raise typer.Exit(1 if bad else 0)


if __name__ == "__main__":
    app()
