#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12"]
# ///
"""Score a frozen prediction against a Word redline and list every miss.

The prediction file is the one ``predict_paragraph_verdict.py`` wrote before
the redline existed. This script does not change it and does not refit the rule.

    score_paragraph_verdicts.py prediction.jsonl redline.docx --doc equal

A miss is a paragraph whose verdict or retained anchors differ from the
prediction. Exit 1 when any paragraph misses or the paragraph counts differ.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from redline_rebuilt_text import rebuilt

app = typer.Typer(add_completion=False, help=__doc__)


def actual_verdict(paragraph) -> dict:
    if not paragraph.has_revision:
        end_b = len(paragraph.before)
        end_a = len(paragraph.after)
        anchors = (
            [{"before": [0, end_b], "after": [0, end_a], "place": "full"}]
            if paragraph.before or paragraph.after
            else []
        )
        return {"verdict": "unchanged", "anchors": anchors}
    anchors = [
        {"before": [b0, b1], "after": [a0, a1]}
        for b0, b1, a0, a1 in paragraph.retained
    ]
    if anchors:
        return {"verdict": "word-level", "anchors": anchors}
    return {"verdict": "replace", "anchors": []}


def _anchor_key(anchors: list[dict]) -> tuple:
    return tuple(
        (tuple(item["before"]), tuple(item["after"]))
        for item in anchors
    )


def score_document(prediction: list[dict], redline: Path, doc: str) -> tuple[int, int, list[str]]:
    rows = [row for row in prediction if row.get("kind") == "paragraph" and row.get("doc") == doc]
    got = rebuilt(redline).paragraphs
    misses: list[str] = []
    hits = 0
    if len(got) != len(rows):
        misses.append(f"paragraph count predicted={len(rows)} redline={len(got)}")
    for index, (row, paragraph) in enumerate(zip(rows, got)):
        actual = actual_verdict(paragraph)
        reasons = []
        if actual["verdict"] != row["verdict"]:
            reasons.append(f"verdict predicted={row['verdict']} actual={actual['verdict']}")
        if _anchor_key(actual["anchors"]) != _anchor_key(row.get("anchors") or []):
            reasons.append(
                f"anchors predicted={row.get('anchors')} actual={actual['anchors']}"
            )
        if reasons:
            misses.append(f"{row['id']} " + "; ".join(reasons))
        else:
            hits += 1
    extra = len(got) - len(rows)
    if extra > 0:
        for paragraph in got[len(rows) :]:
            misses.append(f"extra redline paragraph {actual_verdict(paragraph)['verdict']} {paragraph.before!r}")
    elif extra < 0:
        for row in rows[len(got) :]:
            misses.append(f"{row['id']} missing from redline")
    return hits, len(rows), misses


@app.command()
def main(
    prediction: Path = typer.Argument(..., help="Frozen JSONL from predict_paragraph_verdict.py."),
    redline: Path = typer.Argument(..., help="Word redline docx for one probe document."),
    doc: str = typer.Option(..., "--doc", help="doc field in the prediction to score."),
) -> None:
    """List every miss. Exit 1 if the frozen prediction is not what Word did."""
    rows = [json.loads(line) for line in prediction.read_text().splitlines() if line.strip()]
    hits, n, misses = score_document(rows, redline, doc)
    for miss in misses:
        typer.echo(f"MISS {miss}")
    rate = (hits / n) if n else 0.0
    typer.echo(f"hit={hits} miss={len(misses)} n={n} rate={rate:.4f} doc={doc}")
    raise typer.Exit(1 if misses else 0)


if __name__ == "__main__":
    app()
