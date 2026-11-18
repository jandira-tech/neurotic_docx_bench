#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC

# SPDX-License-Identifier: AGPL-3.0-only

"""Subprocess access to the reference jubarte binary for grading.

Grading always uses arm A's binary (`jubarte read --json` and `jubarte
validate`), so both arms are measured with the same reference tool.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CommandResult:
    argv: list[str]
    return_code: int
    stdout: str
    stderr: str


@dataclass
class Snapshot:
    """What `jubarte read --json` reported about an artifact (or the failure)."""

    ok: bool
    command: CommandResult | None = None
    document: dict | None = None
    error: str = ""
    paragraphs: list[dict] = field(default_factory=list)
    revisions: list[dict] = field(default_factory=list)
    comments: list[dict] = field(default_factory=list)


def paragraph_rows(snapshot) -> list[dict]:
    """All exposed stories, with story-qualified identities for alignment."""
    rows = [dict(p, _story="body") for p in snapshot.paragraphs]
    for story in (getattr(snapshot, "document", None) or {}).get("stories", []):
        rows.extend(dict(p, _story=story["id"]) for p in story.get("paragraphs", []))
    return rows


def paragraph_key(paragraph: dict) -> str:
    pid = str(paragraph.get("id", ""))
    story = paragraph.get("_story", "body")
    return pid if story == "body" else f"{story}:{pid}"


def _run(argv: list[str], timeout: float = 120.0) -> CommandResult:
    proc = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
    )
    return CommandResult(
        argv=argv,
        return_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def read_snapshot(binary: Path, artifact: Path) -> Snapshot:
    """`jubarte read FILE --json -o -` … the CLI writes the snapshot to a
    file, so the snapshot lands in a temp file that is read back here."""

    import tempfile

    with tempfile.TemporaryDirectory(prefix="pilot-snap-") as tmp:
        out = Path(tmp) / "snapshot.json"
        result = _run([str(binary), "read", str(artifact), "--json", "-o", str(out)])
        if result.return_code != 0 or not out.is_file():
            return Snapshot(ok=False, command=result, error=result.stderr.strip())
        try:
            document = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return Snapshot(ok=False, command=result, error=f"bad snapshot JSON: {exc}")
        return Snapshot(
            ok=True,
            command=result,
            document=document,
            paragraphs=list(document.get("paragraphs", [])),
            revisions=list(document.get("changes", [])),
            comments=list(document.get("comments", [])),
        )


def validate(
    binary: Path,
    artifact: Path,
    *,
    original: Path | None = None,
    author: str | None = None,
) -> tuple[CommandResult, list[dict]]:
    """Run `jubarte validate` and return its parsed JSONL findings."""

    argv = [str(binary), "validate", str(artifact), "--json"]
    if original is not None:
        argv += ["--original", str(original)]
        if author is not None:
            argv += ["--author", author]
    result = _run(argv)
    findings: list[dict] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return result, findings
