"""Decide whether a Word redline is actually the pair its name claims.

Word's compare result is only correct while the document it saved is the
comparison it just made. After a dropped connection it has saved a different
open document under the next pair's filename: the before-text and the after-text
are the same foreign file, and neither named side is in it.

This check is deliberately loose. Word rewrites quotes, checkboxes, headers and
field results, so the redline will not equal the sources character for character.
It only has to be *that* pair and not some other document. A swapped file scores
near zero against both named sides; a real redline scores high against both.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"

# Each source is checked on its own. A window of file A must occur in the
# redline's before-text, and a window of file B must occur in the after-text.
# The two fractions are not averaged: a blend that is half A and half B fails
# both sides. 0.9 leaves room for a checkbox or a page mark Word inserts.
MIN_COVERAGE = 0.9


@dataclass(frozen=True, slots=True)
class Identity:
    ok: bool
    sim_base: float
    sim_revision: float
    reason: str


def _norm(text: str) -> str:
    return " ".join(text.replace("\u00a0", " ").replace("\u200b", "").split())


def _text(element: ET.Element, view: str) -> str:
    """`original` keeps deletions and drops insertions. `revised` does the opposite."""
    out: list[str] = []

    def walk(node: ET.Element, in_ins: bool, in_del: bool) -> None:
        tag = node.tag
        if tag == f"{MC}AlternateContent":
            choice = node.find(f"{MC}Choice")
            target = choice if choice is not None else node.find(f"{MC}Fallback")
            if target is not None:
                walk(target, in_ins, in_del)
            return
        if tag == f"{W}ins":
            in_ins = True
        elif tag == f"{W}del":
            in_del = True
        elif tag == f"{W}t":
            take = (
                view == "plain"
                or (view == "revised" and not in_del)
                or (view == "original" and not in_ins)
            )
            if take:
                out.append(node.text or "")
        elif tag == f"{W}delText" and view in ("plain", "original") and not in_ins:
            out.append(node.text or "")
        elif tag in (f"{W}p", f"{W}br", f"{W}cr"):
            out.append("\n")
        for child in list(node):
            walk(child, in_ins, in_del)

    walk(element, False, False)
    return _norm("".join(out))


def body_text(path: Path, view: str = "plain") -> str:
    """Visible body text of one .docx. `view` is plain, original, or revised."""
    with zipfile.ZipFile(path) as package:
        root = ET.fromstring(package.read("word/document.xml"))
    return _text(root, view)


def coverage(source: str, haystack: str, window: int = 40) -> float:
    """Fraction of `source` that actually occurs inside `haystack`.

    This is not a similarity against a blend. Each window is taken from one
    file only, and it has to be found verbatim in the redline view for that file.
    """
    if not source:
        return 1.0
    if len(source) <= window:
        return 1.0 if source in haystack else 0.0
    slices = [source[i : i + window] for i in range(0, len(source) - window + 1, window)]
    if not slices:
        return 1.0
    return sum(1 for piece in slices if piece in haystack) / len(slices)


def matches_pair(
    redline: Path,
    base: Path,
    revision: Path,
    *,
    min_coverage: float = MIN_COVERAGE,
) -> Identity:
    """True only when A's text is in the before-view and B's text is in the after-view.

    The two coverages are not combined. Either file missing fails the redline.
    So does any of the three that is not a docx package: Word's own `save as`
    always writes one, so a redline that is not a package is a truncated or
    foreign save, and a source that is not one cannot have been compared.
    """
    for path in (redline, base, revision):
        try:
            package = zipfile.is_zipfile(path)
        except OSError:
            package = False
        if not package:
            return Identity(False, 0.0, 0.0, f"not a docx package: {path.name}")
    try:
        before = body_text(redline, "original")
        after = body_text(redline, "revised")
        base_text = body_text(base, "plain")
        revision_text = body_text(revision, "plain")
    except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
        return Identity(False, 0.0, 0.0, f"could not unpack: {exc}")
    got_base = coverage(base_text, before)
    got_revision = coverage(revision_text, after)
    if got_base >= min_coverage and got_revision >= min_coverage:
        return Identity(True, got_base, got_revision, "")
    missing = []
    if got_base < min_coverage:
        missing.append(f"base {got_base:.0%}")
    if got_revision < min_coverage:
        missing.append(f"revision {got_revision:.0%}")
    return Identity(
        False,
        got_base,
        got_revision,
        "redline is missing "
        + " and ".join(missing)
        + " of that file; the two sides are not averaged",
    )
