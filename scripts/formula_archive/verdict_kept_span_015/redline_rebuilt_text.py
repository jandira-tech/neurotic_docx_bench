#!/usr/bin/env -S uv run --script
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# /// script
# requires-python = ">=3.14"
# dependencies = ["typer>=0.12"]
# ///
"""Rebuild both sides of a redline and require an exact match to the sources.

The identity check can still pass when someone types during a Word batch.
Those keystrokes become phantom deletions: the redline is still "the same
document" under a loose overlap, and the extra characters are real. This
check rebuilds the before-text and the after-text from the tracked-change
XML and compares them, character for character, to the two named files.

    redline_rebuilt_text.py REDLINE.docx ORIGINAL.docx REVISED.docx

Exit 0 when both sides match. Exit 1 on the first character that does not.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import typer

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
STRICT_W = "{http://purl.oclc.org/ooxml/wordprocessingml/main}"

app = typer.Typer(add_completion=False, help=__doc__)


def _local(tag: str) -> str:
    if tag.startswith(STRICT_W):
        return W + tag[len(STRICT_W) :]
    return tag


@dataclass(frozen=True, slots=True)
class ParagraphText:
    """One paragraph, without the newline the document join adds."""

    before: str
    after: str
    retained: tuple[tuple[int, int, int, int], ...]
    """Retained spans as (before_start, before_end, after_start, after_end)."""

    has_revision: bool


@dataclass(frozen=True, slots=True)
class Rebuilt:
    before: str
    after: str
    paragraphs: tuple[ParagraphText, ...]


def _walk_paragraph(paragraph: ET.Element) -> ParagraphText:
    before: list[str] = []
    after: list[str] = []
    retained: list[tuple[int, int, int, int]] = []
    bpos = 0
    apos = 0
    revised = False

    def add_retained(text: str) -> None:
        nonlocal bpos, apos
        if not text:
            return
        start_b, start_a = bpos, apos
        before.append(text)
        after.append(text)
        bpos += len(text)
        apos += len(text)
        if retained and retained[-1][1] == start_b and retained[-1][3] == start_a:
            prev = retained[-1]
            retained[-1] = (prev[0], bpos, prev[2], apos)
        else:
            retained.append((start_b, bpos, start_a, apos))

    def add_before(text: str) -> None:
        nonlocal bpos, revised
        if not text:
            return
        revised = True
        before.append(text)
        bpos += len(text)

    def add_after(text: str) -> None:
        nonlocal apos, revised
        if not text:
            return
        revised = True
        after.append(text)
        apos += len(text)

    def walk(node: ET.Element, in_ins: bool, in_del: bool) -> None:
        tag = _local(node.tag) if isinstance(node.tag, str) else ""
        if tag == f"{MC}AlternateContent":
            choice = node.find(f"{MC}Choice")
            target = choice if choice is not None else node.find(f"{MC}Fallback")
            if target is not None:
                walk(target, in_ins, in_del)
            return
        if tag in (f"{W}ins", f"{W}moveTo"):
            in_ins = True
        elif tag in (f"{W}del", f"{W}moveFrom"):
            in_del = True
        elif tag == f"{W}t":
            text = node.text or ""
            if in_del and not in_ins:
                add_before(text)
            elif in_ins and not in_del:
                add_after(text)
            elif not in_ins and not in_del:
                add_retained(text)
        elif tag == f"{W}delText" and not in_ins:
            add_before(node.text or "")
        elif tag in (f"{W}br", f"{W}cr", f"{W}tab"):
            piece = "\t" if tag == f"{W}tab" else "\n"
            if in_del and not in_ins:
                add_before(piece)
            elif in_ins and not in_del:
                add_after(piece)
            elif not in_ins and not in_del:
                add_retained(piece)
        for child in list(node):
            walk(child, in_ins, in_del)

    walk(paragraph, False, False)
    return ParagraphText("".join(before), "".join(after), tuple(retained), revised)


def _document_root(path: Path) -> ET.Element:
    with zipfile.ZipFile(path) as package:
        try:
            payload = package.read("word/document.xml")
        except KeyError as exc:
            raise ValueError(f"{path} has no word/document.xml") from exc
    return ET.fromstring(payload)


def rebuilt(path: Path) -> Rebuilt:
    """Before-text and after-text of one docx, joined by a newline per paragraph."""
    root = _document_root(path)
    paragraphs = tuple(_walk_paragraph(p) for p in root.iter(f"{W}p"))
    # A strict document that used the strict namespace still needs its paragraphs.
    if not paragraphs:
        paragraphs = tuple(
            _walk_paragraph(p) for p in root.iter(f"{STRICT_W}p")
        )
    before = "".join(f"{p.before}\n" for p in paragraphs)
    after = "".join(f"{p.after}\n" for p in paragraphs)
    return Rebuilt(before, after, paragraphs)


def _first_diff(left: str, right: str) -> str:
    limit = min(len(left), len(right))
    for index in range(limit):
        if left[index] != right[index]:
            start = max(0, index - 12)
            stop = index + 12
            return (
                f"at {index}: redline {left[index]!r} source {right[index]!r} "
                f"redline[{start}:{stop}]={left[start:stop]!r} "
                f"source[{start}:{stop}]={right[start:stop]!r}"
            )
    if len(left) != len(right):
        return f"at {limit}: lengths redline={len(left)} source={len(right)}"
    return "equal"


@dataclass(frozen=True, slots=True)
class ExactMatch:
    ok: bool
    before_diff: str
    after_diff: str


def exact_match(redline: Path, original: Path, revised: Path) -> ExactMatch:
    got = rebuilt(redline)
    base = rebuilt(original)
    nxt = rebuilt(revised)
    before_ok = got.before == base.before
    # The revised file is read as its own after-text, which on a clean source
    # is the text Word was given. Compare that to the redline's after-text.
    after_ok = got.after == nxt.after
    return ExactMatch(
        before_ok and after_ok,
        "equal" if before_ok else _first_diff(got.before, base.before),
        "equal" if after_ok else _first_diff(got.after, nxt.after),
    )


@app.command()
def main(
    redline: Path = typer.Argument(..., help="Redline docx whose XML is rebuilt."),
    original: Path = typer.Argument(..., help="Named base document."),
    revised: Path = typer.Argument(..., help="Named revision document."),
) -> None:
    """Exit 1 when either rebuilt side differs from its named source."""
    for path in (redline, original, revised):
        if not path.is_file():
            typer.echo(f"missing {path}")
            raise typer.Exit(2)
    try:
        result = exact_match(redline, original, revised)
    except (zipfile.BadZipFile, ET.ParseError, ValueError) as exc:
        typer.echo(f"unreadable: {exc}")
        raise typer.Exit(2) from exc
    if result.ok:
        typer.echo("exact before and after")
        raise typer.Exit(0)
    typer.echo(f"before {result.before_diff}")
    typer.echo(f"after {result.after_diff}")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
