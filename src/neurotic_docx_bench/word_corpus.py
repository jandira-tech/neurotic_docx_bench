"""The Word corpus: one canonical tree, ``corpus/word/``, for what Word produced.

Word is the source of truth for PDFs in this benchmark. Its output accumulated
under ``grok_run/`` (gitignored, 12 GB of working folders) and under
``corpus/no_comments_pdf_was_generated_by_word/``; this module gathers the parts
that are reference material into docsets, each a folder with a fixed layout, a
``PROVENANCE.json`` and a CSV that names every document or pair, under one
sha256 manifest.

Rules that hold everywhere here:

* Origins are read, never written: a docset is built by COPY (a clone on APFS),
  and nothing under ``grok_run/`` or ``corpus/`` is moved or deleted.
* A build is idempotent. A destination file whose bytes already match is
  skipped; one that differs is an error unless ``force`` is passed, so an
  edited reference cannot be replaced by accident.
* Keys are the scorer's keys: a document's stem for a render docset, the
  ``<base>__vs__<next>`` pair stem for a redline docset, and
  :func:`pipeline.oracle_pair_key` for the oracle renders, so a docset id here is
  the id a run scored on the same files would carry.
* Only what Word finished is in: a docx Word could not open, a docx or compare
  Word did not turn into a PDF, and a blacklisted document (with the pairs that
  touch it) are recorded under ``excluded`` / ``absent`` and not copied.
* Every document carries its state, read from the docx XML: ``tracked_changes``,
  ``comments`` and the ``pdf_markup`` Word printed (``none``, ``tracked``,
  ``comments``, ``tracked_comments``); ``index.csv`` at the corpus root lists
  every document of every docset with it, so "all docx with comments" is a filter,
  not a folder.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import subprocess
import sys
import zipfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from neurotic_docx_bench import hub, pipeline
from neurotic_docx_bench.config import CorpusEntry
from neurotic_docx_bench.ledger import docset as docset_mod

MANIFEST_NAME = hub.MANIFEST_NAME
PROVENANCE_NAME = "PROVENANCE.json"
DOCUMENTS_NAME = "documents.csv"
PAIRS_NAME = "pairs.csv"
ORACLES_NAME = "oracles.csv"
INDEX_NAME = "index.csv"
README_NAME = "README.md"
LICENSE_FILE = "LICENSE-ODC-BY-1.0.txt"
LICENSE = "ODC-By-1.0"
DATASET = "superdoc-dev/docx-corpus"
WORD_PRODUCER = "Microsoft Word for Mac (PDF via macOS Quartz PDFContext)"
DEFAULT_DEST = Path("corpus/word")
PAIR_SEP = "__vs__"

# Folder names inside a docset. The first five hold documents and are counted;
# ``notes`` holds the origin's own notes and ``""`` is the docset root (license).
DESTS = ("docx", "pdf_word", "pdf_word_prior", "docx_redline", "pdf_redline_word", "notes", "")
DOC_DESTS = DESTS[:5]

# ``<stem>.pdf`` and ``<stem>.w<build>.pdf`` are current Word references,
# ``<stem>.outdated.pdf`` is the reference a later build superseded.
_TAGGED = re.compile(r"^(?P<stem>[^.]+)(?:\.(?P<tag>[^.]+))?\.pdf$")
_PRIOR_TAG = "outdated"
_BUILD_TAG = re.compile(r"^w\d+$")

CLONE_COMMAND: tuple[str, ...] = ("cp", "-c")
_GENERATED_PER_DOCSET = 2  # PROVENANCE.json and one table
_GENERATED_PER_CORPUS = 2  # README.md and index.csv

# The document state, read from the docx XML: any revision element in the document,
# header, footer, footnote or endnote parts, and a comments part with a comment in it.
_CHANGE = re.compile(
    rb"<w:(?:ins|del|moveFrom|moveTo|rPrChange|pPrChange|sectPrChange|tblPrChange|tblGridChange"
    rb"|trPrChange|tcPrChange|numberingChange|cellIns|cellDel|cellMerge)\b"
)
_COMMENT = re.compile(rb"<w:comment\b")
_DOC_PARTS = ("word/document", "word/header", "word/footer", "word/footnotes", "word/endnotes")
MARKUPS = ("none", "tracked", "comments", "tracked_comments")


class CorpusError(Exception):
    """A docset cannot be planned or built as asked; the message says why."""


# --- the document state ----------------------------------------------------------


class DocxState(NamedTuple):
    tracked_changes: bool
    comments: bool


def docx_state(path: Path) -> DocxState:
    """Whether the docx at ``path`` carries tracked changes and whether it carries comments."""
    tracked = comments = False
    try:
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if name == "word/comments.xml":
                    comments = _COMMENT.search(zf.read(name)) is not None
                elif not tracked and name.endswith(".xml") and name.startswith(_DOC_PARTS):
                    tracked = _CHANGE.search(zf.read(name)) is not None
    except zipfile.BadZipFile as exc:
        raise CorpusError(f"not a docx: {path}") from exc
    return DocxState(tracked, comments)


def markup(state: DocxState) -> str:
    """What Word prints for a document in ``state``: its PDF shows the markup the docx carries."""
    return MARKUPS[int(state.tracked_changes) + 2 * int(state.comments)]


# --- the docset table ----------------------------------------------------------


@dataclass(frozen=True)
class Source:
    """Documents of one kind copied from one origin folder into one dest folder."""

    origin: str  # repo-relative folder
    dest: str  # a DOC_DESTS member
    suffix: str  # ".docx" | ".pdf"
    tagged: bool = False  # fixtures_500_pdf naming: current / .w<build> / .outdated
    prefix: str = ""  # oracles: the corpus the renders belong to
    docx_dir: str = ""  # oracles: repo-relative folder of the docx these PDFs render
    fallback: bool = False  # pdf_word: used only for stems the other pdf_word sources lack


@dataclass(frozen=True)
class Note:
    """One file of the origin's own notes, copied when present."""

    origin: str  # repo-relative file
    dest: str  # docset-relative path


@dataclass(frozen=True)
class Exclusion:
    """Documents Word refused: a folder of docx it could not open, or a blacklist TSV."""

    origin: str  # repo-relative folder of docx, or the TSV
    label: str
    blacklist: bool = False


@dataclass(frozen=True)
class Docset:
    name: str
    family: str  # "render" | "redline"
    description: str
    sources: tuple[Source, ...]
    notes: tuple[Note, ...] = ()
    exclusions: tuple[Exclusion, ...] = ()
    sources_docset: str | None = None  # redline docsets: the render docset their base/next docx live in
    license: str | None = LICENSE
    dataset: str | None = DATASET

    @property
    def oracles(self) -> bool:
        return any(s.prefix for s in self.sources)


_G = "grok_run"
_NC = "corpus/no_comments_pdf_was_generated_by_word"
_FIXTURE_NOTES = (
    Note(f"{_G}/fixtures_500/{LICENSE_FILE}", LICENSE_FILE),
    Note(f"{_G}/fixtures_500/NOTICE", "notes/NOTICE"),
    Note(f"{_G}/MANIFEST.json", "notes/MANIFEST.json"),
)

DOCSETS: tuple[Docset, ...] = (
    Docset(
        "sources_500",
        "render",
        "500 docx sampled from the superdoc docx-corpus, each with its Word PDF; 18 stems were "
        "re-rendered by a later Word build (the earlier render is kept under pdf_word_prior).",
        (
            Source(f"{_G}/fixtures_500", "docx", ".docx"),
            Source(f"{_G}/fixtures_500_pdf", "pdf_word", ".pdf", tagged=True),
        ),
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/fixtures_500/manifest.jsonl", "notes/manifest.jsonl"),
            Note(f"{_G}/fixtures_500/split_a_100_b_10.json", "notes/split_a_100_b_10.json"),
            Note(f"{_G}/fixtures_500_pdf/EXTRA_REFERENCES.md", "notes/EXTRA_REFERENCES.md"),
        ),
        exclusions=(Exclusion(f"{_G}/fixtures_500_failed", "fixtures_500_failed"),),
    ),
    Docset(
        "en_pairs_500",
        "render",
        "1000 English docx (500 base/next pairs, parts a and b) with Word PDFs from the first Word "
        "pass; the second pass (run2, same Word build, the same render up to live date fields) fills "
        "the stems the first pass lacks and is otherwise left in grok_run.",
        (
            Source(f"{_G}/500_docx_part_a_original", "docx", ".docx"),
            Source(f"{_G}/500_docx_part_b_original", "docx", ".docx"),
            Source(f"{_G}/500_pdf_part_a_original", "pdf_word", ".pdf"),
            Source(f"{_G}/500_pdf_part_b_original", "pdf_word", ".pdf"),
            Source(f"{_G}/500_pdf_part_a_run2", "pdf_word", ".pdf", fallback=True),
            Source(f"{_G}/500_pdf_part_b_run2", "pdf_word", ".pdf", fallback=True),
        ),
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/500_en_sources.jsonl", "notes/500_en_sources.jsonl"),
            Note(f"{_G}/500_en_pairs.tsv", "notes/500_en_pairs.tsv"),
        ),
        exclusions=(
            Exclusion(f"{_G}/500_docx_part_a_word_invalid", "500_docx_part_a_word_invalid"),
            Exclusion(f"{_G}/500_docx_part_b_word_invalid", "500_docx_part_b_word_invalid"),
        ),
    ),
    Docset(
        "redlines_a100_b10",
        "redline",
        "Word compares of 100 base documents against 10 next documents from sources_500 "
        "(a__vs__b), each with the Word PDF of the compared document; a pair Word did not "
        "render is left out.",
        (
            Source(f"{_G}/compared_a_100_vs_b_10_docx", "docx_redline", ".docx"),
            Source(f"{_G}/compared_a_100_vs_b_10_pdf", "pdf_redline_word", ".pdf"),
        ),
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/compared_a_100_vs_b_10_pdf/NOTE", "notes/NOTE"),
            Note(f"{_G}/fixtures_500/split_a_100_b_10.json", "notes/split_a_100_b_10.json"),
        ),
        exclusions=(Exclusion(f"{_G}/word_blacklist/blacklist.tsv", "word_blacklist", blacklist=True),),
        sources_docset="sources_500",
    ),
    Docset(
        "redlines_en_500",
        "redline",
        "Word compares of the en_pairs_500 base/next pairs, each with the Word PDF of the compared "
        "document; a pair Word did not render, and the pairs of a blacklisted document, are left out.",
        (
            Source(f"{_G}/500_extra_docx_redlines", "docx_redline", ".docx"),
            Source(f"{_G}/500_extra_pdf_redlines", "pdf_redline_word", ".pdf"),
        ),
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/500_en_pairs.tsv", "notes/500_en_pairs.tsv"),
            Note(f"{_G}/word_blacklist/blacklist.tsv", "notes/blacklist.tsv"),
        ),
        exclusions=(
            Exclusion(f"{_G}/word_blacklist/blacklist.tsv", "word_blacklist", blacklist=True),
            Exclusion(f"{_G}/500_extra_redlines_rejected/500_extra_docx_redlines", "500_extra_redlines_rejected"),
        ),
        sources_docset="en_pairs_500",
    ),
    Docset(
        "oracles_wordpdf",
        "redline",
        "Word renders (September 2026) of the tracked redline docx of word_based, word_based_randomized "
        "and word_redlines_superdoc, comments printed where the docx carries them: the Word PDF oracle "
        "for those corpora, keyed like the scorer keys them.",
        (
            Source(
                f"{_G}/wordpdf_redline_oracles/word_based",
                "pdf_redline_word",
                ".pdf",
                prefix="word_based",
                docx_dir="corpus/word_based/docx_redlines_word",
            ),
            Source(
                f"{_G}/wordpdf_redline_oracles/word_based_randomized",
                "pdf_redline_word",
                ".pdf",
                prefix="word_based_randomized",
                docx_dir="corpus/word_based/docx_redlines_randomized",
            ),
            Source(
                f"{_G}/wordpdf_redline_oracles/word_redlines_superdoc",
                "pdf_redline_word",
                ".pdf",
                prefix="word_redlines_superdoc",
                docx_dir="corpus/word_redlines_superdoc/docx_redlines_word",
            ),
        ),
        license=None,
        dataset=None,
    ),
    Docset(
        "oracles_wordpdf_nocomments",
        "redline",
        "Word renders (July 2026) of the word_based tracked redline docx with their comments stripped: "
        "the same pairs as oracles_wordpdf in the state 'tracked changes, no comments'. The origin is "
        f"the tracked folder {_NC} (which stays where it is).",
        (
            Source(
                f"{_NC}/pdf_redlines_word",
                "pdf_redline_word",
                ".pdf",
                prefix="word_based",
                docx_dir=f"{_NC}/docx_redlines_word",
            ),
        ),
        license=None,
        dataset=None,
    ),
)


def docset(name: str) -> Docset:
    for ds in DOCSETS:
        if ds.name == name:
            return ds
    raise CorpusError(f"unknown docset {name!r}; known: {', '.join(d.name for d in DOCSETS)}")


# --- planning ------------------------------------------------------------------


@dataclass(frozen=True)
class CopyItem:
    src: Path  # repo-relative
    dst: str  # docset-relative
    dest: str  # DESTS member


@dataclass(frozen=True)
class PairRow:
    pair_stem: str
    base: str
    next: str
    docx: str
    pdf: str
    tracked_changes: bool
    comments: bool
    pdf_markup: str


@dataclass(frozen=True)
class DocRow:
    key: str
    docx: str
    pdf_word: str
    pdf_word_prior: str
    tracked_changes: bool
    comments: bool
    pdf_markup: str
    pdf_word_origin: str = ""  # repo-relative folder the reference PDF came from
    corpus: str = ""  # oracles only
    stem: str = ""  # oracles only: the file's own stem (the key can be shared by two capture variants)


@dataclass(frozen=True)
class Plan:
    docset: Docset
    items: tuple[CopyItem, ...]
    keys: tuple[str, ...]
    absent: tuple[str, ...]  # docx (or compares) Word did not render: left out, reported
    superseded: tuple[str, ...]  # keys whose earlier render is kept under pdf_word_prior
    orphans: tuple[str, ...]  # PDFs whose docx is gone (reported, not copied)
    excluded: dict[str, tuple[str, ...]]  # label → stems Word refused
    pairs: tuple[PairRow, ...] = ()
    documents: tuple[DocRow, ...] = ()
    origins: dict[str, tuple[str, ...]] = field(default_factory=dict)
    corpora: dict[str, dict[str, Any]] = field(default_factory=dict)  # oracles: per-corpus keys and ids
    filled: tuple[str, ...] = ()  # keys whose reference PDF came from a fallback source

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in self.items:
            if item.dest in DOC_DESTS:
                out[item.dest] = out.get(item.dest, 0) + 1
        return out

    @property
    def states(self) -> dict[str, Any]:
        rows: Sequence[PairRow | DocRow] = self.pairs or self.documents
        by_markup: dict[str, int] = {}
        for row in rows:
            by_markup[row.pdf_markup] = by_markup.get(row.pdf_markup, 0) + 1
        return {
            "tracked_changes": sum(1 for r in rows if r.tracked_changes),
            "comments": sum(1 for r in rows if r.comments),
            "pdf_markup": dict(sorted(by_markup.items())),
        }


@dataclass(frozen=True)
class Collected:
    current: dict[str, Path]  # stem → repo-relative path of the reference
    prior: dict[str, Path]  # stem → the render a later build superseded
    origin: dict[str, str]  # stem → repo-relative folder the reference came from
    filled: tuple[str, ...]  # stems whose reference came from a fallback source


def _files(root: Path, origin: str, suffix: str) -> dict[str, Path]:
    """``{filename: repo-relative path}`` for the files of ``suffix`` under ``origin``
    (``plan`` has checked that the origin folders exist)."""
    folder = root / origin
    return {p.name: Path(origin) / p.name for p in sorted(folder.iterdir()) if p.is_file() and p.suffix == suffix}


def _split_pair(stem: str) -> tuple[str, str]:
    base, sep, nxt = stem.partition(PAIR_SEP)
    if not sep or not base or not nxt:
        raise CorpusError(f"not a <base>{PAIR_SEP}<next> name: {stem}")
    return base, nxt


def _tagged_pdfs(root: Path, source: Source) -> tuple[dict[str, Path], dict[str, Path]]:
    """Current and prior Word references of a tagged folder, keyed by stem."""
    current: dict[str, Path] = {}
    prior: dict[str, Path] = {}
    for name, rel in _files(root, source.origin, source.suffix).items():
        m = _TAGGED.match(name)
        stem, tag = (m.group("stem"), m.group("tag")) if m else ("", "")
        if tag == _PRIOR_TAG:
            prior[stem] = rel
        elif m and (tag is None or _BUILD_TAG.match(tag)):
            if stem in current:
                raise CorpusError(f"two current references for {stem} in {source.origin}: {current[stem].name}, {name}")
            current[stem] = rel
        else:
            raise CorpusError(
                f"unexpected name in {source.origin}: {name} "
                "(want <stem>.pdf, <stem>.w<build>.pdf or <stem>.outdated.pdf)"
            )
    return current, prior


def _plain_pdfs(root: Path, source: Source) -> dict[str, Path]:
    return {Path(name).stem: rel for name, rel in _files(root, source.origin, source.suffix).items()}


def _collect(root: Path, sources: Iterable[Source], dest: str) -> Collected:
    """Merge the sources of one dest by stem; a fallback source only fills what the others lack."""
    current: dict[str, Path] = {}
    prior: dict[str, Path] = {}
    origin: dict[str, str] = {}
    filled: list[str] = []
    chosen = [s for s in sources if s.dest == dest]
    for source in sorted(chosen, key=lambda s: s.fallback):
        if source.tagged:
            cur, pri = _tagged_pdfs(root, source)
        elif source.suffix == ".pdf":
            cur, pri = _plain_pdfs(root, source), {}
        else:
            cur, pri = {Path(n).stem: r for n, r in _files(root, source.origin, source.suffix).items()}, {}
        for stem, rel in cur.items():
            if stem in current:
                if source.fallback:
                    continue
                raise CorpusError(f"two current references for {stem}: {current[stem]}, {rel}")
            current[stem] = rel
            origin[stem] = source.origin
            if source.fallback:
                filled.append(stem)
        prior.update(pri)
    return Collected(current, prior, origin, tuple(sorted(filled)))


def _origins(ds: Docset) -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for s in ds.sources:
        out.setdefault(s.dest, []).append(s.origin)
        if s.tagged:
            out.setdefault("pdf_word_prior", []).append(s.origin)
    return {k: tuple(v) for k, v in out.items()}


def _notes(root: Path, ds: Docset) -> list[CopyItem]:
    items = []
    for note in ds.notes:
        if (root / note.origin).is_file():
            items.append(CopyItem(Path(note.origin), note.dest, "notes" if note.dest.startswith("notes/") else ""))
    return items


def _docx_stems(root: Path, ds: Docset) -> set[str]:
    stems: set[str] = set()
    for source in ds.sources:
        if source.dest == "docx":
            stems.update(Path(n).stem for n in _files(root, source.origin, source.suffix))
    return stems


def _exclusions(root: Path, ds: Docset, universe: set[str] | None) -> dict[str, tuple[str, ...]]:
    """Stems Word refused, per label; a blacklist is narrowed to ``universe`` (the docset's own stems)."""
    out: dict[str, tuple[str, ...]] = {}
    for ex in ds.exclusions:
        path = root / ex.origin
        if ex.blacklist:
            if not path.is_file():
                continue
            stems = [line.split("\t", 1)[0].strip() for line in path.read_text().splitlines() if line.strip()]
            stems = [s for s in stems if universe is None or s in universe]
        else:
            if not path.is_dir():
                continue
            stems = sorted({p.stem for p in path.iterdir() if p.is_file() and p.suffix in (".docx", ".pdf")})
        if stems:
            out[ex.label] = tuple(dict.fromkeys(stems))
    return out


def _plan_render(root: Path, ds: Docset) -> Plan:
    docx = _collect(root, ds.sources, "docx").current
    pdfs = _collect(root, ds.sources, "pdf_word")
    current, prior = pdfs.current, pdfs.prior
    keys = tuple(k for k in sorted(docx) if k in current)  # a docx Word did not render is left out
    items: list[CopyItem] = []
    documents: list[DocRow] = []
    for key in keys:
        items.append(CopyItem(docx[key], f"docx/{key}.docx", "docx"))
        items.append(CopyItem(current[key], f"pdf_word/{key}.pdf", "pdf_word"))
        pri = ""
        if key in prior:
            pri = f"pdf_word_prior/{key}.pdf"
            items.append(CopyItem(prior[key], pri, "pdf_word_prior"))
        state = docx_state(root / docx[key])
        documents.append(
            DocRow(
                key,
                f"docx/{key}.docx",
                f"pdf_word/{key}.pdf",
                pri,
                state.tracked_changes,
                state.comments,
                markup(state),
                pdf_word_origin=pdfs.origin[key],
            )
        )
    orphans = [f"pdf_word/{k}.pdf" for k in current if k not in docx]
    orphans += [f"pdf_word_prior/{k}.pdf" for k in prior if k not in docx]
    items.extend(_notes(root, ds))
    return Plan(
        ds,
        tuple(items),
        keys,
        absent=tuple(k for k in sorted(docx) if k not in current),
        superseded=tuple(k for k in keys if k in prior),
        orphans=tuple(sorted(orphans)),
        excluded=_exclusions(root, ds, None),
        documents=tuple(documents),
        origins=_origins(ds),
        filled=tuple(k for k in pdfs.filled if k in docx),
    )


def _plan_redline(root: Path, ds: Docset) -> Plan:
    docx = _collect(root, ds.sources, "docx_redline").current
    pdf = _collect(root, ds.sources, "pdf_redline_word").current
    universe = _docx_stems(root, docset(ds.sources_docset)) if ds.sources_docset else None
    excluded = _exclusions(root, ds, universe)
    blacklisted = set(excluded.get("word_blacklist", ()))
    stems = sorted(docx)
    split = {stem: _split_pair(stem) for stem in stems}
    dropped = tuple(s for s in stems if blacklisted & set(split[s]))
    if dropped:
        excluded["word_blacklist_pairs"] = dropped
    keys = tuple(s for s in stems if s in pdf and s not in dropped)
    items: list[CopyItem] = []
    pairs: list[PairRow] = []
    for key in keys:
        base, nxt = split[key]
        items.append(CopyItem(docx[key], f"docx_redline/{key}.docx", "docx_redline"))
        items.append(CopyItem(pdf[key], f"pdf_redline_word/{key}.pdf", "pdf_redline_word"))
        state = docx_state(root / docx[key])
        pairs.append(
            PairRow(
                key,
                base,
                nxt,
                f"docx_redline/{key}.docx",
                f"pdf_redline_word/{key}.pdf",
                state.tracked_changes,
                state.comments,
                markup(state),
            )
        )
    items.extend(_notes(root, ds))
    return Plan(
        ds,
        tuple(items),
        keys,
        absent=tuple(s for s in stems if s not in pdf and s not in dropped),
        superseded=(),
        orphans=tuple(sorted(f"pdf_redline_word/{k}.pdf" for k in pdf if k not in docx)),
        excluded=excluded,
        pairs=tuple(pairs),
        origins=_origins(ds),
    )


def _plan_oracles(root: Path, ds: Docset) -> Plan:
    """Word renders matched to the tracked redline docx BY STEM (a pair can have two capture
    variants, ``a_b_redline`` and ``a_b_word_redline``, each with its own render); keys are the
    scorer's pair keys of the matched files, so they can repeat across rows but not in ``keys``."""
    items: list[CopyItem] = []
    documents: list[DocRow] = []
    keys: set[str] = set()
    absent: list[str] = []
    orphans: list[str] = []
    corpora: dict[str, dict[str, Any]] = {}
    for source in ds.sources:
        pdfs = {Path(n).stem: rel for n, rel in _files(root, source.origin, source.suffix).items()}
        pdfs = {stem: rel for stem, rel in pdfs.items() if pipeline.is_redline(stem)}
        docx_dir = root / source.docx_dir
        docx = {
            p.stem: Path(source.docx_dir) / p.name
            for p in (sorted(docx_dir.iterdir()) if docx_dir.is_dir() else ())
            if p.is_file() and p.suffix == ".docx" and pipeline.is_redline(p.stem)
        }
        matched = sorted(stem for stem in pdfs if stem in docx)
        corpus_keys = sorted({pipeline.oracle_pair_key(stem) for stem in matched})
        for stem in matched:
            dst = f"{source.prefix}/{source.dest}/{stem}.pdf"
            items.append(CopyItem(pdfs[stem], dst, source.dest))
            state = docx_state(root / docx[stem])
            documents.append(
                DocRow(
                    pipeline.oracle_pair_key(stem),
                    docx[stem].as_posix(),
                    dst,
                    "",
                    state.tracked_changes,
                    state.comments,
                    markup(state),
                    pdf_word_origin=source.origin,
                    corpus=source.prefix,
                    stem=stem,
                )
            )
        absent.extend(f"{source.prefix}/{stem}" for stem in sorted(docx) if stem not in pdfs)
        orphans.extend(f"{source.prefix}/{source.dest}/{stem}.pdf" for stem in sorted(pdfs) if stem not in docx)
        keys.update(corpus_keys)
        corpora[source.prefix] = {
            "docx_dir": source.docx_dir,
            "n_files": len(matched),
            "n_keys": len(corpus_keys),
            "docset_id": docset_mod.docset_id(corpus_keys),
        }
    items.extend(_notes(root, ds))
    return Plan(
        ds,
        tuple(items),
        tuple(sorted(keys)),
        absent=tuple(absent),
        superseded=(),
        orphans=tuple(orphans),
        excluded=_exclusions(root, ds, None),
        documents=tuple(documents),
        origins=_origins(ds),
        corpora=corpora,
    )


def missing_origins(root: Path, ds: Docset) -> tuple[str, ...]:
    """The origin folders of ``ds`` (and of its sources docset) that are not under ``root``."""
    sources = list(ds.sources)
    if ds.sources_docset:
        sources += docset(ds.sources_docset).sources
    return tuple(s.origin for s in sources if not (Path(root) / s.origin).is_dir())


def plan(root: Path, ds: Docset) -> Plan:
    """What building ``ds`` from the tree under ``root`` would copy and record."""
    root = Path(root)
    missing = missing_origins(root, ds)
    if missing:
        raise CorpusError(f"{ds.name}: origin folders missing under {root}: {', '.join(missing)}")
    if ds.oracles:
        return _plan_oracles(root, ds)
    if ds.family == "redline":
        return _plan_redline(root, ds)
    return _plan_render(root, ds)


# --- building ------------------------------------------------------------------


@dataclass(frozen=True)
class BuildReport:
    docsets: tuple[str, ...]
    copied: int
    skipped: int
    overwritten: int
    written: int  # generated files (provenance, tables, README)
    plans: tuple[Plan, ...] = ()

    def describe(self) -> str:
        return (
            f"copied {self.copied}, skipped {self.skipped} identical, overwritten {self.overwritten}, "
            f"written {self.written} generated files for {', '.join(self.docsets)}"
        )


def _same_bytes(a: Path, b: Path) -> bool:
    return a.stat().st_size == b.stat().st_size and hub.sha256_file(a) == hub.sha256_file(b)


def _clone_enabled() -> bool:
    return sys.platform == "darwin"


def copy_file(src: Path, dst: Path) -> None:
    """Copy ``src`` to ``dst``: a clone on APFS (``cp -c``), a plain copy elsewhere. Never a hardlink:
    an edit to the copy must not reach the origin."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if _clone_enabled():
        done = subprocess.run([*CLONE_COMMAND, str(src), str(dst)], capture_output=True)
        if done.returncode == 0:
            return
    shutil.copy2(src, dst)


def _select(only: Sequence[str] | None) -> tuple[Docset, ...]:
    if only is None:
        return DOCSETS
    return tuple(docset(name) for name in only)


def table_name(ds: Docset) -> str:
    """The CSV a docset writes: pairs for compares, oracles for Word renders of corpus redlines,
    documents otherwise."""
    if ds.oracles:
        return ORACLES_NAME
    return PAIRS_NAME if ds.family == "redline" else DOCUMENTS_NAME


def _provenance(plan_: Plan) -> dict[str, Any]:
    ds = plan_.docset
    doc: dict[str, Any] = {
        "docset": ds.name,
        "family": ds.family,
        "description": ds.description,
        "license": ds.license,
        "dataset": ds.dataset,
        "producer": WORD_PRODUCER,
        "origins": {k: list(v) for k, v in plan_.origins.items()},
        "counts": plan_.counts,
        "n_keys": len(plan_.keys),
        "docset_id": docset_mod.docset_id(plan_.keys),
        "sources_docset": ds.sources_docset,
        "absent": list(plan_.absent),
        "superseded": list(plan_.superseded),
        "filled": list(plan_.filled),
        "orphans": list(plan_.orphans),
        "excluded": {k: list(v) for k, v in plan_.excluded.items()},
        "states": plan_.states,
        "notes": [item.dst for item in plan_.items if item.dest not in DOC_DESTS],
        "table": table_name(ds),
    }
    if plan_.corpora:
        doc["corpora"] = plan_.corpora
    return doc


def _write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _flag(value: bool) -> str:
    return "true" if value else "false"


_STATE_COLUMNS = ("tracked_changes", "comments", "pdf_markup")


def _write_tables(folder: Path, plan_: Plan) -> int:
    (folder / PROVENANCE_NAME).write_text(json.dumps(_provenance(plan_), indent=1, sort_keys=True) + "\n")
    ds = plan_.docset
    table = table_name(ds)
    if table == PAIRS_NAME:
        _write_csv(
            folder / PAIRS_NAME,
            ("pair_stem", "base", "next", "docx_redline", "pdf_redline_word", *_STATE_COLUMNS),
            (
                (p.pair_stem, p.base, p.next, p.docx, p.pdf, _flag(p.tracked_changes), _flag(p.comments), p.pdf_markup)
                for p in plan_.pairs
            ),
        )
    elif table == ORACLES_NAME:
        _write_csv(
            folder / ORACLES_NAME,
            ("corpus", "key", "stem", "docx", "pdf_redline_word", *_STATE_COLUMNS),
            (
                (d.corpus, d.key, d.stem, d.docx, d.pdf_word, _flag(d.tracked_changes), _flag(d.comments), d.pdf_markup)
                for d in plan_.documents
            ),
        )
    else:
        _write_csv(
            folder / DOCUMENTS_NAME,
            ("key", "docx", "pdf_word", "pdf_word_prior", "pdf_word_origin", *_STATE_COLUMNS),
            (
                (
                    d.key,
                    d.docx,
                    d.pdf_word,
                    d.pdf_word_prior,
                    d.pdf_word_origin,
                    _flag(d.tracked_changes),
                    _flag(d.comments),
                    d.pdf_markup,
                )
                for d in plan_.documents
            ),
        )
    return _GENERATED_PER_DOCSET


INDEX_COLUMNS = ("docset", "family", "key", "stem", "docx", "pdf", *_STATE_COLUMNS)


def index_rows(dest: Path) -> list[dict[str, str]]:
    """One row per document of every built docset under ``dest``, read from the docset tables:
    where its docx and its Word PDF are (corpus-relative, except an oracle's docx, which is
    repo-relative) and the state the docx carries."""
    rows: list[dict[str, str]] = []
    for ds in DOCSETS:
        folder = Path(dest) / ds.name
        if not (folder / PROVENANCE_NAME).is_file():
            continue
        table = json.loads((folder / PROVENANCE_NAME).read_text())["table"]
        with (folder / table).open(newline="") as fh:
            for r in csv.DictReader(fh):
                if table == PAIRS_NAME:
                    key, stem, docx, pdf = r["pair_stem"], r["pair_stem"], r["docx_redline"], r["pdf_redline_word"]
                elif table == ORACLES_NAME:
                    key, stem, docx, pdf = r["key"], r["stem"], r["docx"], r["pdf_redline_word"]
                else:
                    key, stem, docx, pdf = r["key"], r["key"], r["docx"], r["pdf_word"]
                if table != ORACLES_NAME:
                    docx = f"{ds.name}/{docx}"
                rows.append(
                    {
                        "docset": ds.name,
                        "family": ds.family,
                        "key": key,
                        "stem": stem,
                        "docx": docx,
                        "pdf": f"{ds.name}/{pdf}",
                        **{c: r[c] for c in _STATE_COLUMNS},
                    }
                )
    return rows


def _readme(rows: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# Word corpus",
        "",
        "Reference material produced by Microsoft Word, gathered from its working folders by",
        "`bench corpus build` (see `neurotic_docx_bench/word_corpus.py` for the docset table). Every",
        "file here is a copy; the origins were not moved or deleted. Only what Word finished is here:",
        "a docx Word could not open, a document or compare it did not render, and a blacklisted",
        "document with the pairs that touch it are listed in each docset's `PROVENANCE.json`",
        "(`excluded`, `absent`) and not copied. `bench corpus check` verifies the tree against",
        f"`{MANIFEST_NAME}`; `bench corpus list` prints the table below from the",
        f"`{PROVENANCE_NAME}` of each docset.",
        "",
        "Every document row carries its state, read from the docx XML: `tracked_changes`, `comments`",
        "and `pdf_markup`, the markup Word printed into the PDF (`none`, `tracked`, `comments`,",
        f"`tracked_comments`). `{INDEX_NAME}` lists every document of every docset with it, so a",
        "state is a filter over the corpus rather than a folder of it.",
        "",
        "docx and PDF files are gitignored (they live in the fixtures dataset on the Hub); the",
        "manifests, provenance, tables and notes are tracked.",
        "",
        "| docset | family | keys | docset id | counts | tracked | comments | absent | superseded |",
        "|---|---|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        counts = ", ".join(f"{k} {v}" for k, v in row["counts"].items())
        lines.append(
            f"| {row['name']} | {row['family']} | {row['n_keys']} | {row['docset_id']} | {counts} "
            f"| {row['tracked_changes']} | {row['comments']} | {row['absent']} | {row['superseded']} |"
        )
    lines += ["", "## Docsets", ""]
    for row in rows:
        ds = docset(row["name"])
        lines += [f"### {ds.name}", "", ds.description, ""]
        for dest_name, origins in _origins(ds).items():
            lines.append(f"* `{dest_name}/` from " + ", ".join(f"`{o}`" for o in origins))
        if ds.sources_docset:
            lines.append(f"* base/next docx: `{ds.sources_docset}/docx/`")
        if ds.license:
            lines.append(f"* license {ds.license} ({ds.dataset}); see `{LICENSE_FILE}`")
        lines.append("")
    return "\n".join(lines)


def build(
    root: Path,
    dest: Path,
    *,
    only: Sequence[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> BuildReport:
    """Copy the docsets of ``only`` (default all) from ``root`` into ``dest`` and write their records.

    Every docset is planned and every existing destination file is compared before anything is
    copied, so a ``differs`` error leaves the tree as it was.
    """
    root, dest = Path(root), Path(dest)
    selected = _select(only)
    plans = [plan(root, ds) for ds in selected]
    actions: list[tuple[str, Path, Path]] = []  # ("copy" | "skip" | "overwrite", src, dst)
    for plan_ in plans:
        for item in plan_.items:
            src = root / item.src
            dst = dest / plan_.docset.name / item.dst
            if not dst.exists():
                actions.append(("copy", src, dst))
            elif _same_bytes(src, dst):
                actions.append(("skip", src, dst))
            elif force:
                actions.append(("overwrite", src, dst))
            else:
                raise CorpusError(f"{dst} differs from {src}; pass --force to replace it")
    copied = sum(1 for a in actions if a[0] == "copy")
    skipped = sum(1 for a in actions if a[0] == "skip")
    overwritten = sum(1 for a in actions if a[0] == "overwrite")
    written = _GENERATED_PER_DOCSET * len(plans) + _GENERATED_PER_CORPUS  # plus README and index
    names = tuple(p.docset.name for p in plans)
    if dry_run:
        return BuildReport(names, copied, skipped, overwritten, written, tuple(plans))
    for action, src, dst in actions:
        if action == "overwrite":
            dst.unlink()  # our own earlier copy; a fresh clone rather than a write into it
        if action != "skip":
            copy_file(src, dst)
    for plan_ in plans:
        folder = dest / plan_.docset.name
        folder.mkdir(parents=True, exist_ok=True)
        _write_tables(folder, plan_)
    _write_csv(dest / INDEX_NAME, INDEX_COLUMNS, ([r[c] for c in INDEX_COLUMNS] for r in index_rows(dest)))
    (dest / README_NAME).write_text(_readme(summary(dest)) + "\n")
    hub.write_manifest(dest)
    return BuildReport(names, copied, skipped, overwritten, written, tuple(plans))


def check(dest: Path) -> hub.ManifestReport:
    """Verify ``dest`` against its manifest."""
    try:
        return hub.verify_manifest(Path(dest))
    except hub.ManifestError as exc:
        raise CorpusError(str(exc)) from exc


def summary(dest: Path) -> list[dict[str, Any]]:
    """One row per built docset, in table order, from the provenance files."""
    rows: list[dict[str, Any]] = []
    for ds in DOCSETS:
        path = Path(dest) / ds.name / PROVENANCE_NAME
        if not path.is_file():
            continue
        prov = json.loads(path.read_text())
        rows.append(
            {
                "name": ds.name,
                "family": ds.family,
                "n_keys": prov["n_keys"],
                "docset_id": prov["docset_id"],
                "counts": prov["counts"],
                "absent": len(prov["absent"]),
                "superseded": len(prov["superseded"]),
                "filled": len(prov["filled"]),
                "orphans": len(prov["orphans"]),
                "excluded": sum(len(v) for v in prov["excluded"].values()),
                "tracked_changes": prov["states"]["tracked_changes"],
                "comments": prov["states"]["comments"],
                "pdf_markup": prov["states"]["pdf_markup"],
            }
        )
    return rows


def corpus_entries(dest: Path = DEFAULT_DEST) -> tuple[CorpusEntry, ...]:
    """The redline docsets as ``CorpusEntry`` pools: ``pairs.csv`` is a base/next manifest and the
    sources docset's ``docx/`` folder holds the documents. Not registered in bench.yaml by this module."""
    out = []
    for ds in DOCSETS:
        if ds.family != "redline" or ds.sources_docset is None:
            continue
        out.append(
            CorpusEntry(
                name=f"word_{ds.name}",
                manifest=(Path(dest) / ds.name / PAIRS_NAME).as_posix(),
                source_dir=(Path(dest) / ds.sources_docset / "docx").as_posix(),
            )
        )
    return tuple(out)
