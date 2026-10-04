#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12"]
# ///
"""Print the current written rule's verdict for two paragraphs.

This does not call Word and it does not call the endpoint. The rule is the
hypothesis file. A verdict printed here is that file applied to the text,
which is what gets frozen before a measurement.

    predict_paragraph_verdict.py --rule hypothesis.json --before 'aaa' --after 'bbb'
    predict_paragraph_verdict.py --rule hypothesis.json --pairs pairs.jsonl --out prediction.jsonl

``pairs.jsonl`` lines are ``{"doc", "id", "before", "after"}``. The output
repeats the rule on the first line and then one verdict per paragraph.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, help=__doc__)

SIDES = ("shorter", "longer", "total")


def longest_shared_run(before: str, after: str) -> tuple[int, int, int]:
    """Earliest longest consecutive run shared by both strings.

    Returns ``(start_before, start_after, length)``. Length 0 means no run.
    """
    if not before or not after:
        return (0, 0, 0)
    best = (0, 0, 0)
    prev = [0] * (len(after) + 1)
    for i, ca in enumerate(before, start=1):
        cur = [0] * (len(after) + 1)
        for j, cb in enumerate(after, start=1):
            if ca != cb:
                continue
            cur[j] = prev[j - 1] + 1
            if cur[j] > best[2]:
                length = cur[j]
                best = (i - length, j - length, length)
        prev = cur
    return best


def load_rule(path: Path) -> dict:
    rule = json.loads(path.read_text())
    side = rule.get("side")
    if side not in SIDES:
        raise ValueError(f"rule side must be one of {SIDES}")
    threshold = float(rule["threshold"])
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("rule threshold must be between 0 and 1")
    min_chars = int(rule.get("min_chars", 0))
    if min_chars < 0:
        raise ValueError("rule min_chars must be >= 0")
    if rule.get("shared", "longest-run") != "longest-run":
        raise ValueError("this script only applies shared=longest-run")
    if rule.get("unit", "chars") != "chars":
        raise ValueError("this script only applies unit=chars")
    return rule


def _place(start: int, end: int, length: int) -> str:
    if end <= start:
        return "none"
    if start == 0 and end == length:
        return "full"
    if start == 0:
        return "prefix"
    if end == length:
        return "suffix"
    return "middle"


def verdict_for(before: str, after: str, rule: dict) -> dict:
    """Apply ``rule`` to one paragraph pair."""
    if before == after:
        end = len(before)
        anchors = (
            [{"before": [0, end], "after": [0, end], "place": "full"}] if end else []
        )
        return {"verdict": "unchanged", "anchors": anchors, "shared_run": end, "fraction": 1.0}
    start_b, start_a, length = longest_shared_run(before, after)
    shorter = min(len(before), len(after))
    longer = max(len(before), len(after))
    if rule["side"] == "shorter":
        denom = shorter
    elif rule["side"] == "longer":
        denom = longer
    else:
        denom = len(before) + len(after)
    fraction = (length / denom) if denom else 0.0
    if shorter < int(rule.get("min_chars", 0)):
        kind = "word-level"
    elif fraction >= float(rule["threshold"]):
        kind = "word-level"
    else:
        kind = "replace"
    if kind == "replace" or length == 0:
        anchors: list[dict] = []
    else:
        anchors = [
            {
                "before": [start_b, start_b + length],
                "after": [start_a, start_a + length],
                "place": _place(start_b, start_b + length, len(before)),
            }
        ]
    return {
        "verdict": kind,
        "anchors": anchors,
        "shared_run": length,
        "fraction": fraction,
    }


def predict_pairs(pairs: list[dict], rule: dict) -> list[dict]:
    lines = [
        {
            "kind": "rule",
            "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "rule": rule,
        }
    ]
    for pair in pairs:
        verdict = verdict_for(pair["before"], pair["after"], rule)
        lines.append(
            {
                "kind": "paragraph",
                "doc": pair.get("doc", ""),
                "id": pair["id"],
                "before": pair["before"],
                "after": pair["after"],
                **verdict,
            }
        )
    return lines


@app.command()
def main(
    rule_path: Path = typer.Option(..., "--rule", help="Written hypothesis JSON."),
    before: str | None = typer.Option(None, "--before", help="One before-paragraph."),
    after: str | None = typer.Option(None, "--after", help="One after-paragraph."),
    pairs: Path | None = typer.Option(None, "--pairs", help="JSONL of paragraph pairs."),
    out: Path | None = typer.Option(None, "--out", help="Where to write the frozen prediction."),
) -> None:
    """Print verdicts. Do not call Word or the endpoint."""
    try:
        rule = load_rule(rule_path)
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as exc:
        typer.echo(f"rule: {exc}")
        raise typer.Exit(2) from exc
    if pairs is not None:
        rows = []
        for line_no, raw in enumerate(pairs.read_text().splitlines(), start=1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if "before" not in row or "after" not in row or "id" not in row:
                typer.echo(f"pairs line {line_no} needs id, before, after")
                raise typer.Exit(2)
            rows.append(row)
        predicted = predict_pairs(rows, rule)
    elif before is not None and after is not None:
        predicted = predict_pairs([{"id": "p", "doc": "", "before": before, "after": after}], rule)
    else:
        typer.echo("give --before and --after, or --pairs")
        raise typer.Exit(2)
    text = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in predicted)
    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        typer.echo(f"wrote {out} paragraphs={len(predicted) - 1}")
    else:
        typer.echo(text, nl=False)


if __name__ == "__main__":
    app()
