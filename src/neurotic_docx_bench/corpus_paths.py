"""The files of a corpus set, read from the corpus tables: the one way code finds corpus documents.

``corpus/word/pools/<set>_pairs.csv`` lists a set's Word compares (base, next, Word's redline and
its PDF); ``<set>_renders.csv`` lists every document and comparison of the set with Word's PDF.
``corpus/libreoffice/word_map.csv`` files LibreOffice's render of a Word docx under the same stem.
Paths in the tables are relative to their corpus root; everything returned here is resolved.

A pair keeps the name it had before the corpus existed (``stem``, the ``<base>_<next>`` of the
redline it was copied from, per ``notices/RENAMED.csv``) so results keyed by it still line up. The
table's ``base_name``/``next_name`` are the corpus's one name per distinct document bytes, which
can differ from that.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

WORD = Path("corpus/word")
LIBREOFFICE = Path("corpus/libreoffice")
POOLS = "pools"
WORD_MAP = "word_map.csv"
RENAMED = Path("notices") / "RENAMED.csv"
PAIR_SEP = "__vs__"
_REDLINE_SUFFIX = re.compile(r"(?:_word)?_redline$")
_WORD_CAPTURE = "_word_redline"
#: the three sets of Word compares the redline research scripts walk
REDLINE_SETS = ("word_based", "word_based_randomized", "word_redlines_superdoc")


class UnknownSet(KeyError):
    """No pool table for the set name."""


@dataclass(frozen=True)
class Pair:
    set: str
    key: str
    stem: str
    base_name: str
    next_name: str
    base: Path
    next: Path
    redline: Path
    redline_pdf: Path
    state: str
    base_pdf: Path | None
    next_pdf: Path | None
    libreoffice_pdf: Path | None
    base_libreoffice_pdf: Path | None
    next_libreoffice_pdf: Path | None


@dataclass(frozen=True)
class Entry:
    set: str
    key: str
    kind: str  # document | comparison
    docx: Path
    pdf: Path
    state: str
    libreoffice_pdf: Path | None


def _table(word: Path, set_name: str, suffix: str) -> list[dict[str, str]]:
    path = word / POOLS / f"{set_name}_{suffix}.csv"
    if not path.is_file():
        known = sorted(p.stem.rsplit("_", 1)[0] for p in (word / POOLS).glob("*_*.csv"))
        raise UnknownSet(f"no {path.name} under {word / POOLS}; sets: {', '.join(dict.fromkeys(known))}")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


@cache
def _libreoffice_map(libreoffice: Path) -> dict[str, Path]:
    """Word docx (relative to corpus/word) -> LibreOffice's render of it."""
    path = libreoffice / WORD_MAP
    if not path.is_file():
        return {}
    with open(path, newline="") as f:
        return {r["word_docx"]: libreoffice / r["libreoffice_pdf"] for r in csv.DictReader(f)}


@cache
def _legacy_stems(word: Path) -> tuple[dict[tuple[str, str], str], dict[str, str], frozenset[str]]:
    """Compare docx (relative) -> the pair stem of the redline it was copied from, by
    ``(docx, set)`` and by docx alone, and the compares copied from a ``_word_redline`` file
    (``notices/RENAMED.csv``)."""
    by_set: dict[tuple[str, str], str] = {}
    by_docx: dict[str, str] = {}
    captures: set[str] = set()
    path = word / RENAMED
    if not path.is_file():
        return by_set, by_docx, frozenset()
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if not r["new"].endswith(".docx") or PAIR_SEP not in r["new"]:
                continue
            original = Path(r["original"]).stem
            stem = _REDLINE_SUFFIX.sub("", original)
            by_set.setdefault((r["new"], r["set"]), stem)
            by_docx.setdefault(r["new"], stem)
            if original.endswith(_WORD_CAPTURE):
                captures.add(r["new"])
    return by_set, by_docx, frozenset(captures)


def clear_caches() -> None:
    """Forget the tables read so far (a test that rewrites one in place)."""
    for f in (_libreoffice_map, _word_pdfs, _legacy_stems):
        f.cache_clear()


@cache
def _word_pdfs(word: Path) -> dict[str, Path]:
    """Word docx (relative) -> Word's PDF of it, over every render table."""
    out: dict[str, Path] = {}
    for table in sorted((word / POOLS).glob("*_renders.csv")):
        with open(table, newline="") as f:
            for r in csv.DictReader(f):
                out.setdefault(r["docx"], word / r["pdf"])
    return out


def pairs(set_name: str, *, word: Path = WORD, libreoffice: Path = LIBREOFFICE) -> list[Pair]:
    """The set's Word compares, in table order."""
    lo, pdfs = _libreoffice_map(libreoffice), _word_pdfs(word)
    by_set, by_docx, _ = _legacy_stems(word)
    out = []
    for r in _table(word, set_name, "pairs"):
        base, nxt = f"{r['base']}.docx", f"{r['next']}.docx"
        stem = by_set.get((r["docx"], set_name)) or by_docx.get(r["docx"]) or f"{r['base_name']}_{r['next_name']}"
        out.append(Pair(
            set=set_name, key=r["key"], stem=stem,
            base_name=r["base_name"], next_name=r["next_name"],
            base=word / base, next=word / nxt, redline=word / r["docx"], redline_pdf=word / r["pdf"],
            state=r["state"], base_pdf=pdfs.get(base), next_pdf=pdfs.get(nxt),
            libreoffice_pdf=lo.get(r["docx"]), base_libreoffice_pdf=lo.get(base),
            next_libreoffice_pdf=lo.get(nxt),
        ))
    return out


def by_stem(set_name: str, *, word: Path = WORD, libreoffice: Path = LIBREOFFICE) -> dict[str, Pair]:
    """One pair per legacy stem, in table order. The old folders held some pairs twice
    (``<stem>_redline.docx`` and ``<stem>_word_redline.docx``) and the corpus keeps both
    compares; the ``_word_redline`` capture wins, as it did in the scripts keyed by stem."""
    captures = _legacy_stems(word)[2]
    out: dict[str, Pair] = {}
    for p in pairs(set_name, word=word, libreoffice=libreoffice):
        held = out.get(p.stem)
        if held is None or (p.redline.relative_to(word).as_posix() in captures
                            and held.redline.relative_to(word).as_posix() not in captures):
            out[p.stem] = p
    return out


def entries(set_name: str, *, word: Path = WORD, libreoffice: Path = LIBREOFFICE) -> list[Entry]:
    """Every document and comparison of the set with Word's PDF, in table order."""
    lo = _libreoffice_map(libreoffice)
    return [Entry(set=set_name, key=r["key"], kind=r["kind"], docx=word / r["docx"], pdf=word / r["pdf"],
                  state=r["state"], libreoffice_pdf=lo.get(r["docx"]))
            for r in _table(word, set_name, "renders")]


def documents(set_name: str, **roots: Path) -> list[Entry]:
    return [e for e in entries(set_name, **roots) if e.kind == "document"]


def comparisons(set_name: str, **roots: Path) -> list[Entry]:
    return [e for e in entries(set_name, **roots) if e.kind == "comparison"]
