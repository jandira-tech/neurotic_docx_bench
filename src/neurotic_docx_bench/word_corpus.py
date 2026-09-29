"""The Word corpus: ``corpus/word/<state>/docx|pdf|pdf_prior``, one tree for what Word produced.

Word is the source of truth for PDFs in this benchmark. Its output accumulated under
``grok_run/`` (gitignored working folders), under ``grok_run/word_based`` and its siblings,
under ``corpus/no_comments_pdf_was_generated_by_word/`` and in the ``_fixtures`` folder of
jubarte-first. This module gathers the docx Word made or was given, and the PDFs Word
printed of them, into one tree with one naming scheme, a rename record, the origins'
own notices, two tables and a sha256 manifest.

The scheme:

* A file's id is the first ten hex digits of the sha256 of the docx it represents. A
  document is ``<id>_<name>``; its Word PDF carries the same stem. A comparison (a Word
  compare of two documents) is ``<idA>_<a>__vs__<idB>_<b>_redline_<idC>`` where idC is
  the id of the compared docx, and its PDF carries that stem too. Names are lower-cased,
  anything but ``[a-z0-9_-]`` becomes ``_``, and they are cut at 48 characters; the
  original names are kept in the tables and in ``notices/RENAMED.csv``.
* A tool's output for a Word file is the Word stem plus ``_<tool>``; the scorer keys a
  candidate by stripping that suffix (see :mod:`pipeline`).
* Files live by state, read from the docx XML: ``clean``, ``tracking_without_comments``,
  ``with_comments_clean``, ``with_comments_tracking``. A comparison lives in the state
  of the compared docx. Under each state: ``docx/``, ``pdf/`` (the current Word render)
  and ``pdf_prior/`` (a render an earlier Word build made of the same docx).
* Byte-identical docx from several origins are one file: every origin name and set is
  recorded on the one entry. Two different docx sharing an id is an error.
* Only Word's own PDFs are in: the producer string of every PDF is read and a
  LibreOffice or tool render is refused and recorded. Where a set is a Word render run,
  a docx Word did not turn into a PDF is left out and recorded (``absent``).
* Origins are read, never written: the tree is built by COPY (a clone on APFS) and
  nothing under the origins is moved or deleted. A build is idempotent; a destination
  file whose bytes differ is an error unless ``force`` is passed.
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

from neurotic_docx_bench import hub
from neurotic_docx_bench.config import CorpusEntry
from neurotic_docx_bench.ledger import docset as docset_mod

MANIFEST_NAME = hub.MANIFEST_NAME
PROVENANCE_NAME = "PROVENANCE.json"
DOCUMENTS_NAME = "documents.csv"
COMPARISONS_NAME = "comparisons.csv"
RENAMED_NAME = "RENAMED.csv"
README_NAME = "README.md"
NOTICES_DIR = "notices"
POOLS_DIR = "pools"
LICENSE_FILE = "LICENSE-ODC-BY-1.0.txt"
LICENSE = "ODC-By-1.0"
DATASET = "superdoc-dev/docx-corpus"
DEFAULT_DEST = Path("corpus/word")
FIXTURES_PREFIX = "_fixtures"  # origins under the jubarte-first _fixtures folder, given separately
PAIR_SEP = "__vs__"
REDLINE = "_redline"
WORD_REDLINE = "_word_redline"
ID_LEN = 10
STEM_MAX = 48
ID_SCHEME = "sha256[:10] of the docx bytes"
STATES = ("clean", "tracking_without_comments", "with_comments_clean", "with_comments_tracking")
CLONE_COMMAND: tuple[str, ...] = ("cp", "-c")

# ``<stem>.pdf`` and ``<stem>.w<build>.pdf`` are current Word references,
# ``<stem>.outdated.pdf`` is the reference a later build superseded.
_TAGGED = re.compile(r"^(?P<stem>[^.]+)(?:\.(?P<tag>[^.]+))?\.pdf$")
_PRIOR_TAG = "outdated"
_BUILD_TAG = re.compile(r"^w\d+$")

# The document state, read from the docx XML: any revision element in the document,
# header, footer, footnote or endnote parts, and a comments part with a comment in it.
_CHANGE = re.compile(
    rb"<w:(?:ins|del|moveFrom|moveTo|rPrChange|pPrChange|sectPrChange|tblPrChange|tblGridChange"
    rb"|trPrChange|tcPrChange|numberingChange|cellIns|cellDel|cellMerge)\b"
)
_COMMENT = re.compile(rb"<w:comment\b")
_DOC_PARTS = ("word/document", "word/header", "word/footer", "word/footnotes", "word/endnotes")

# The Info dictionary of a PDF: ``/Producer`` and ``/Creator`` as literal strings (with escapes)
# or hex strings (UTF-16 with a byte-order mark, as LibreOffice writes them).
_PDF_STRING = re.compile(rb"/(?P<key>Producer|Creator)\s*(?:\((?P<lit>(?:[^()\\]|\\.)*)\)|<(?P<hex>[0-9A-Fa-f\s]*)>)")
_PDF_HEAD = 16 * 1024
_PDF_TAIL = 128 * 1024
_SLUG_BAD = re.compile(r"[^a-z0-9_-]+")
_PAIR_BAD = re.compile(r"[^a-z0-9]+")


class CorpusError(Exception):
    """The corpus cannot be planned or built as asked; the message says why."""


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


def state_name(state: DocxState) -> str:
    """The state folder of a docx in ``state``."""
    return STATES[int(state.tracked_changes) + 2 * int(state.comments)]


# --- names -------------------------------------------------------------------------


def file_id(path: Path) -> str:
    """The id of the docx at ``path``: the first ``ID_LEN`` hex digits of its sha256."""
    return hub.sha256_file(path)[:ID_LEN]


def slug(name: str) -> str:
    """``name`` lower-cased, anything but ``[a-z0-9_-]`` folded to ``_``, cut at ``STEM_MAX``."""
    return _SLUG_BAD.sub("_", name.lower())[:STEM_MAX].strip("_")


def document_stem(doc_id: str, name: str) -> str:
    return f"{doc_id}_{slug(name)}"


def comparison_stem(base_stem: str, next_stem: str, cmp_id: str) -> str:
    return f"{base_stem}{PAIR_SEP}{next_stem}{REDLINE}_{cmp_id}"


def pair_stem(name: str) -> str:
    """The mapping key of a compare named after its pair: the ``_word_redline`` / ``_redline``
    suffix dropped, lower-cased, anything but ``[a-z0-9]`` folded to ``_``."""
    stem = name.lower()
    for suffix in (WORD_REDLINE, REDLINE):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return fold_key(stem)


def fold_key(key: str) -> str:
    """A mapping ``pair_stem`` as :func:`pair_stem` folds a compare name, suffix left alone:
    lower-cased, anything but ``[a-z0-9]`` folded to ``_``."""
    return _PAIR_BAD.sub("_", key.lower()).strip("_")


# --- the PDF producer --------------------------------------------------------------


class PdfMeta(NamedTuple):
    producer: str
    creator: str


def _pdf_string(lit: bytes | None, hexs: bytes | None) -> str:
    if hexs is not None:
        raw = bytes.fromhex(re.sub(rb"\s+", b"", hexs).decode("ascii"))
        if raw.startswith(b"\xfe\xff"):
            return raw[2:].decode("utf-16-be", "replace")
        return raw.decode("latin-1")
    return re.sub(rb"\\(.)", rb"\1", lit or b"").decode("utf-8", "replace")


def pdf_meta(path: Path) -> PdfMeta:
    """``/Producer`` and ``/Creator`` of the PDF at ``path`` (empty when absent). The Info
    dictionary usually sits at the tail, so the head and the tail of the file are read; a long
    xref table can push it out of that window, and then the whole file is."""
    size = path.stat().st_size
    with path.open("rb") as fh:
        if size <= _PDF_HEAD + _PDF_TAIL:
            data = fh.read()
        else:
            head = fh.read(_PDF_HEAD)
            fh.seek(size - _PDF_TAIL)
            data = head + fh.read()
            if not _PDF_STRING.search(data):
                fh.seek(0)
                data = fh.read()
    producer = creator = ""
    for m in _PDF_STRING.finditer(data):
        value = _pdf_string(m.group("lit"), m.group("hex"))
        if m.group("key") == b"Producer":
            producer = value
        else:
            creator = value
    return PdfMeta(producer, creator)


def is_word_pdf(meta: PdfMeta) -> bool:
    """Word for Mac prints through Quartz (``/Producer`` names ``Quartz PDFContext``); the older
    Word export sets ``/Creator`` to ``Microsoft Word`` and no producer. Anything else (LibreOffice,
    a tool's own writer) is not Word's."""
    if "libreoffice" in (meta.producer + meta.creator).lower():
        return False
    if "Quartz PDFContext" in meta.producer:
        return True
    return meta.creator.startswith("Microsoft Word") and not meta.producer


def producer_name(meta: PdfMeta) -> str:
    return meta.producer or meta.creator


# --- the sets ----------------------------------------------------------------------


@dataclass(frozen=True)
class Group:
    """Files of one kind (documents or comparisons) of one set: docx folders and the folders of
    their Word PDFs. The ``pdf`` folders are the reference (a stem appears in one of them); the
    ``fallback`` folders only fill the stems the reference lacks, and those stems are reported as
    filled. ``tagged`` folders use the fixtures_500_pdf naming (current / ``.w<build>`` /
    ``.outdated``). ``require_pdf`` marks a Word render run: a docx without a PDF there is a Word
    failure and is left out."""

    docx: tuple[str, ...]
    pdf: tuple[str, ...] = ()
    fallback: tuple[str, ...] = ()
    tagged: bool = False
    require_pdf: bool = False


@dataclass(frozen=True)
class Note:
    """One file of the origin's own notes, copied into ``notices/`` when present."""

    origin: str
    dest: str  # file name under notices/


@dataclass(frozen=True)
class Exclusion:
    """What Word refused: a folder of docx it could not open (or compares that were rejected), or
    the blacklist TSV whose first column names documents Word hangs on."""

    origin: str
    label: str
    blacklist: bool = False


@dataclass(frozen=True)
class Docset:
    name: str
    description: str
    documents: Group | None = None
    comparisons: Group | None = None
    mapping: str | None = None  # centralized_mapping.csv (pair_stem, base, next) for the comparisons
    pair_split: bool = False  # comparisons named <base>__vs__<next>
    sources: str | None = None  # the set whose documents are the base/next of the comparisons
    notes: tuple[Note, ...] = ()
    exclusions: tuple[Exclusion, ...] = ()
    holdout: str | None = None  # a sealed list of this set's pairs, one legacy <base>_<next> key per line

    @property
    def folders(self) -> tuple[str, ...]:
        out: list[str] = []
        for group in (self.documents, self.comparisons):
            if group:
                out.extend(group.docx)
                out.extend(group.pdf)
                out.extend(group.fallback)
        return tuple(out)

    @property
    def fixtures(self) -> bool:
        return any(f.startswith(FIXTURES_PREFIX + "/") for f in self.folders)


_G = "grok_run"
_WB = f"{_G}/word_based"
_SD = f"{_G}/word_redlines_superdoc"
_NC = f"{_G}/no_comments_pdf_was_generated_by_word"
_OR = f"{_G}/wordpdf_redline_oracles"
_WR = f"{_G}/wr0926"
_FX = FIXTURES_PREFIX
_PF = f"{_G}/wr0928/pdf_fill"
_AT = f"{_G}/wr0928/accepted_tracking"
_RT = f"{_G}/wr0928/rejected_tracking"
_BLACKLIST = Exclusion(f"{_G}/word_blacklist/blacklist.tsv", "word_blacklist", blacklist=True)
#: Ids (``sha256[:10]`` of the docx) Word will not open cleanly: a repair / recover-contents
#: prompt, an error, a hang. Applies to every set by content, whatever a set calls the file,
#: and takes every compare built on such a document with it. First column the id, then why.
#: Only the corpus's own originals belong here; a tool's output Word will not open is that
#: tool's failure, scored against it, and never a reason to drop a corpus document.
WORD_INVALID = f"{_G}/word_invalid/word_invalid.tsv"
WORD_INVALID_LABEL = "word_invalid"
_FIXTURE_NOTES = (
    Note(f"{_G}/fixtures_500/{LICENSE_FILE}", LICENSE_FILE),
    Note(f"{_G}/fixtures_500/NOTICE", "NOTICE"),
    Note(f"{_G}/MANIFEST.json", "MANIFEST.json"),
)


def _wr_notes(name: str) -> tuple[Note, ...]:
    return tuple(
        Note(f"{_WR}/{name}/{file}", f"wr0926_{name}_{file}")
        for file in ("map.tsv", "identity.log", "redline_pass1.log", "redline_pass2.log", "word_pdf.log")
    )


DOCSETS: tuple[Docset, ...] = (
    Docset(
        "sources_500",
        "500 docx sampled from the superdoc docx-corpus with their Word PDFs; the stems a later "
        "Word build re-rendered keep the earlier render under pdf_prior.",
        documents=Group((f"{_G}/fixtures_500",), (f"{_G}/fixtures_500_pdf",), tagged=True, require_pdf=True),
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/fixtures_500/manifest.jsonl", "manifest.jsonl"),
            Note(f"{_G}/fixtures_500/split_a_100_b_10.json", "split_a_100_b_10.json"),
            Note(f"{_G}/fixtures_500_pdf/EXTRA_REFERENCES.md", "EXTRA_REFERENCES.md"),
        ),
        exclusions=(Exclusion(f"{_G}/fixtures_500_failed", "fixtures_500_failed"),),
    ),
    Docset(
        "en_pairs_500",
        "1000 English docx (500 base/next pairs, parts a and b) with the Word PDFs of the first Word "
        "pass; the second pass (run2) fills the stems the first pass lacks and otherwise stays behind.",
        documents=Group(
            (f"{_G}/500_docx_part_a_original", f"{_G}/500_docx_part_b_original"),
            (f"{_G}/500_pdf_part_a_original", f"{_G}/500_pdf_part_b_original"),
            fallback=(f"{_G}/500_pdf_part_a_run2", f"{_G}/500_pdf_part_b_run2"),
            require_pdf=True,
        ),
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/500_en_sources.jsonl", "500_en_sources.jsonl"),
            Note(f"{_G}/500_en_pairs.tsv", "500_en_pairs.tsv"),
        ),
        exclusions=(
            Exclusion(f"{_G}/500_docx_part_a_word_invalid", "500_docx_part_a_word_invalid"),
            Exclusion(f"{_G}/500_docx_part_b_word_invalid", "500_docx_part_b_word_invalid"),
        ),
    ),
    Docset(
        "redlines_a100_b10",
        "Word compares of 100 base documents against 10 next documents of sources_500 (a__vs__b) "
        "with the Word PDF of each compared document.",
        comparisons=Group(
            (f"{_G}/compared_a_100_vs_b_10_docx",), (f"{_G}/compared_a_100_vs_b_10_pdf",), require_pdf=True
        ),
        pair_split=True,
        sources="sources_500",
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/compared_a_100_vs_b_10_pdf/NOTE", "NOTE"),
            Note(f"{_G}/fixtures_500/split_a_100_b_10.json", "split_a_100_b_10.json"),
        ),
        exclusions=(_BLACKLIST,),
    ),
    Docset(
        "redlines_en_500",
        "Word compares of the en_pairs_500 base/next pairs with the Word PDF of each compared "
        "document; the pairs of a blacklisted document and the rejected compares are left out.",
        comparisons=Group((f"{_G}/500_extra_docx_redlines",), (f"{_G}/500_extra_pdf_redlines",), require_pdf=True),
        pair_split=True,
        sources="en_pairs_500",
        notes=_FIXTURE_NOTES
        + (
            Note(f"{_G}/500_en_pairs.tsv", "500_en_pairs.tsv"),
            Note(f"{_G}/word_blacklist/blacklist.tsv", "blacklist.tsv"),
        ),
        exclusions=(
            _BLACKLIST,
            Exclusion(f"{_G}/500_extra_redlines_rejected/500_extra_docx_redlines", "500_extra_redlines_rejected"),
        ),
    ),
    Docset(
        "word_based",
        "The word_based documents (docx_source) and Word's compares of their pairs (docx_redlines_word) "
        "with the September 2026 Word renders of those compares.",
        documents=Group((f"{_WB}/docx_source",)),
        comparisons=Group((f"{_WB}/docx_redlines_word",), (f"{_OR}/word_based",), require_pdf=True),
        mapping=f"{_WB}/centralized_mapping.csv",
        sources="word_based",
        holdout=f"{_WB}/holdout.txt",
    ),
    Docset(
        "word_based_randomized",
        "The randomized word_based documents and Word's compares of their pairs with the September "
        "2026 Word renders.",
        documents=Group((f"{_WB}/docx_source_randomized",)),
        comparisons=Group((f"{_WB}/docx_redlines_randomized",), (f"{_OR}/word_based_randomized",), require_pdf=True),
        mapping=f"{_WB}/centralized_mapping_randomized.csv",
        sources="word_based_randomized",
        holdout=f"{_WB}/holdout.txt",
    ),
    Docset(
        "word_redlines_superdoc",
        "The superdoc documents and Word's compares of their pairs with the September 2026 Word renders.",
        documents=Group((f"{_SD}/docx_source",)),
        comparisons=Group((f"{_SD}/docx_redlines_word",), (f"{_OR}/word_redlines_superdoc",), require_pdf=True),
        mapping=f"{_SD}/centralized_mapping.csv",
        sources="word_redlines_superdoc",
        holdout=f"{_SD}/holdout.txt",
    ),
    Docset(
        "word_based_accepted_word",
        "Word compares of the word_based pairs with every tracked change accepted in Word "
        "(word_working_roundtrip, named <pair>_word_redline_accepted), with the Word PDFs of the "
        "September 29 2026 render; the LibreOffice render of each was the visual_accepted_changes oracle.",
        documents=Group((f"{_WB}/word_working_roundtrip",), (f"{_G}/wr0929/word_based_accepted_word_pdf",)),
    ),
    Docset(
        "word_based_0926",
        "The September 2026 compare run of the word_based pairs: fresh Word compares with their Word PDFs.",
        comparisons=Group((f"{_WR}/word_based/docx",), (f"{_WR}/word_based/pdf",), require_pdf=True),
        mapping=f"{_WB}/centralized_mapping.csv",
        sources="word_based",
        notes=_wr_notes("word_based"),
    ),
    Docset(
        "word_based_randomized_0926",
        "The September 2026 compare run of the randomized word_based pairs.",
        comparisons=Group(
            (f"{_WR}/word_based_randomized/docx",), (f"{_WR}/word_based_randomized/pdf",), require_pdf=True
        ),
        mapping=f"{_WB}/centralized_mapping_randomized.csv",
        sources="word_based_randomized",
        notes=_wr_notes("word_based_randomized"),
    ),
    Docset(
        "word_redlines_superdoc_0926",
        "The September 2026 compare run of the superdoc pairs.",
        comparisons=Group(
            (f"{_WR}/word_redlines_superdoc/docx",), (f"{_WR}/word_redlines_superdoc/pdf",), require_pdf=True
        ),
        mapping=f"{_SD}/centralized_mapping.csv",
        sources="word_redlines_superdoc",
        notes=_wr_notes("word_redlines_superdoc"),
    ),
    Docset(
        "nocomments",
        "The July 2026 Word run over word_based with comments stripped: the documents with their Word "
        "PDFs and the compares (tracked changes, no comments) with theirs.",
        documents=Group((f"{_NC}/docx_source",), (f"{_NC}/pdf_source",), require_pdf=True),
        comparisons=Group((f"{_NC}/docx_redlines_word",), (f"{_NC}/pdf_redlines_word",), require_pdf=True),
        mapping=f"{_NC}/centralized_mapping.csv",
        sources="nocomments",
    ),
    Docset(
        "nocomments_randomized",
        "The July 2026 Word run over the randomized word_based pairs with comments stripped.",
        documents=Group((f"{_NC}/docx_source_randomized",), (f"{_NC}/pdf_source_randomized",), require_pdf=True),
        comparisons=Group((f"{_NC}/docx_redlines_randomized",), (f"{_NC}/pdf_redlines_randomized",), require_pdf=True),
        mapping=f"{_NC}/centralized_mapping_randomized.csv",
        sources="nocomments_randomized",
    ),
    Docset(
        "fixtures_originals",
        "The original fixtures of jubarte-first (_fixtures/original_fixtures): the docx the word_based "
        "documents were made from, some under their original names; no Word PDF of them exists.",
        documents=Group((f"{_FX}/original_fixtures",)),
    ),
    Docset(
        "fixtures_word_compares",
        "Word compares of the original fixtures (_fixtures/word_redlined_fixtures) resolved through the "
        "word_based mapping; no Word PDF of them exists.",
        comparisons=Group((f"{_FX}/word_redlined_fixtures",)),
        mapping=f"{_WB}/centralized_mapping.csv",
        sources="word_based",
    ),
    Docset(
        "pdf_fill_0928",
        "The September 28 2026 Word render of the documents and compares that had no Word PDF "
        "(notices/audit_2026-09-28_docx_without_word_pdf.csv); word_refused holds the documents Word "
        "would not open, left out through the word_invalid list.",
        documents=Group((f"{_PF}/documents_docx", f"{_PF}/word_refused"), (f"{_PF}/documents_pdf",), require_pdf=True),
        comparisons=Group((f"{_PF}/comparisons_docx",), (f"{_PF}/comparisons_pdf",), require_pdf=True),
        mapping=f"{_PF}/mapping.csv",
        sources="pdf_fill_0928",
    ),
    Docset(
        "accepted_tracking_0928",
        "100 Word compares (40 with comments, 60 without; accepted_tracking_selection.csv) with every "
        "tracked change accepted by Word, named <compare id>_accepted_tracking, with their Word PDFs.",
        documents=Group((f"{_AT}/docx",), (f"{_AT}/pdf",), require_pdf=True),
        notes=(Note(f"{_AT}/selection.csv", "accepted_tracking_selection.csv"),),
    ),
    Docset(
        "rejected_tracking_0928",
        "100 more Word compares (25 with comments, 75 without; rejected_tracking_selection.csv), none of "
        "them in accepted_tracking_0928, with every tracked change rejected by Word, named "
        "<compare id>_rejected_tracking, with their Word PDFs.",
        documents=Group((f"{_RT}/docx",), (f"{_RT}/pdf",), require_pdf=True),
        notes=(Note(f"{_RT}/selection.csv", "rejected_tracking_selection.csv"),),
    ),
)


def origins() -> tuple[str, ...]:
    """Every origin folder or file the sets read, in table order, once."""
    seen: dict[str, None] = {WORD_INVALID: None}
    for ds in DOCSETS:
        for rel in (*ds.folders, ds.mapping, *(n.origin for n in ds.notes), *(e.origin for e in ds.exclusions)):
            if rel:
                seen.setdefault(rel)
    return tuple(seen)


def docset(name: str) -> Docset:
    for ds in DOCSETS:
        if ds.name == name:
            return ds
    raise CorpusError(f"unknown docset {name!r}; known: {', '.join(d.name for d in DOCSETS)}")


# --- the plan ----------------------------------------------------------------------


@dataclass(eq=False)
class Document:
    """One docx of the corpus (deduplicated by bytes) and the Word PDFs of it."""

    id: str
    sha256: str
    stem: str
    state: str
    names: tuple[str, ...]
    sets: tuple[str, ...]
    docx_src: str
    pdf_src: str = ""
    pdf_prior_src: str = ""
    pdf_sha: str = ""
    pdf_prior_sha: str = ""
    producer: str = ""
    pdf_set: str = ""  # the set whose Word run made the current render

    @property
    def kind(self) -> str:
        return "document"

    @property
    def docx(self) -> str:
        return f"{self.state}/docx/{self.stem}.docx"

    @property
    def pdf(self) -> str:
        return f"{self.state}/pdf/{self.stem}.pdf" if self.pdf_src else ""

    @property
    def pdf_prior(self) -> str:
        return f"{self.state}/pdf_prior/{self.stem}.pdf" if self.pdf_prior_src else ""


@dataclass(eq=False)
class Comparison(Document):
    """A Word compare of two documents; ``stem`` is ``<base stem>__vs__<next stem>_redline_<id>``."""

    base_id: str = ""
    next_id: str = ""
    base_name: str = ""
    next_name: str = ""

    @property
    def kind(self) -> str:
        return "comparison"


@dataclass
class SetReport:
    name: str
    documents: tuple[str, ...] = ()  # ids, in origin-name order
    comparisons: tuple[str, ...] = ()
    absent: tuple[str, ...] = ()  # origin names without a Word PDF in a render run
    excluded: dict[str, tuple[str, ...]] = field(default_factory=dict)
    unresolved: dict[str, str] = field(default_factory=dict)  # compares whose base/next are unknown
    refused: dict[str, str] = field(default_factory=dict)  # PDF origin -> producer that is not Word
    orphans: tuple[str, ...] = ()  # PDF origins without a docx
    filled: tuple[str, ...] = ()  # names whose PDF came from a later folder
    superseded: tuple[str, ...] = ()  # names whose render of this set went to pdf_prior
    # names whose render is a third one of bytes that already carry a current and a prior render
    # (the same docx under several names of an untagged set, each rendered on its own): not copied
    redundant: tuple[str, ...] = ()


@dataclass(frozen=True)
class Rename:
    original: str
    new: str
    id: str
    sha256: str
    set: str


@dataclass(frozen=True)
class CopyItem:
    src: str  # origin (root-relative, or under FIXTURES_PREFIX)
    dst: str  # corpus-relative


@dataclass
class Plan:
    documents: tuple[Document, ...]
    comparisons: tuple[Comparison, ...]
    sets: dict[str, SetReport]
    renames: tuple[Rename, ...]
    notes: tuple[CopyItem, ...]
    skipped: tuple[str, ...]  # fixtures sets left out for want of a fixtures root
    holdout: tuple[str, ...] = ()  # comparison stems of the sealed holdout lists
    holdout_missing: dict[str, tuple[str, ...]] = field(default_factory=dict)  # list -> keys matching no compare

    @property
    def entries(self) -> tuple[Document, ...]:
        return (*self.documents, *self.comparisons)


def _select(only: Sequence[str] | None) -> tuple[Docset, ...]:
    if only is None:
        return DOCSETS
    wanted = {docset(name).name for name in only}
    return tuple(ds for ds in DOCSETS if ds.name in wanted)


class _Planner:
    def __init__(self, root: Path, fixtures: Path | None) -> None:
        self.root = root
        self.fixtures = fixtures
        self.documents: list[Document] = []
        self.comparisons: list[Comparison] = []
        self.by_sha: dict[str, Document] = {}
        self.by_id: dict[str, Document] = {}
        self.names: dict[str, dict[str, Document]] = {}  # set -> origin name -> document
        self.sets: dict[str, SetReport] = {}
        self.renames: list[Rename] = []
        self.mappings: dict[str, dict[str, tuple[str, str]]] = {}
        self.shas: dict[str, str] = {}
        self._invalid: set[str] | None = None
        self.invalid_names: dict[str, set[str]] = {}  # set -> origin names left out as Word-invalid

    # -- origins

    @property
    def invalid_ids(self) -> set[str]:
        if self._invalid is None:
            path = self.root / WORD_INVALID
            lines = path.read_text().splitlines() if path.is_file() else []
            self._invalid = {line.split("\t", 1)[0].strip() for line in lines if line.strip()}
        return self._invalid

    def resolve(self, rel: str) -> Path:
        if rel.startswith(FIXTURES_PREFIX + "/"):
            if self.fixtures is None:
                raise CorpusError(f"{rel} needs a fixtures root (--fixtures)")
            return self.fixtures / rel[len(FIXTURES_PREFIX) + 1 :]
        return self.root / rel

    def sha(self, rel: str) -> str:
        if rel not in self.shas:
            self.shas[rel] = hub.sha256_file(self.resolve(rel))
        return self.shas[rel]

    def files(self, folder: str, suffix: str) -> list[tuple[str, str]]:
        """``(name, origin)`` for the files of ``suffix`` in ``folder``, by name; Word lock files skipped."""
        path = self.resolve(folder)
        if not path.is_dir():
            raise CorpusError(f"missing origin folder {folder}")
        return [
            (p.name, f"{folder}/{p.name}")
            for p in sorted(path.iterdir())
            if p.is_file() and p.suffix == suffix and not p.name.startswith("~$")
        ]

    def mapping(self, rel: str) -> dict[str, tuple[str, str]]:
        if rel not in self.mappings:
            path = self.resolve(rel)
            if not path.is_file():
                raise CorpusError(f"missing mapping {rel}")
            with path.open(newline="") as fh:
                # keyed as pair_stem folds a compare name (the superdoc mapping keeps `__`)
                self.mappings[rel] = {fold_key(r["pair_stem"]): (r["base"], r["next"]) for r in csv.DictReader(fh)}
        return self.mappings[rel]

    def exclusions(self, ds: Docset) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for ex in ds.exclusions:
            path = self.resolve(ex.origin)
            if ex.blacklist:
                if not path.is_file():
                    continue
                stems = {line.split("\t", 1)[0].strip() for line in path.read_text().splitlines() if line.strip()}
            else:
                if not path.is_dir():
                    continue
                stems = {p.stem for p in path.iterdir() if p.is_file() and p.suffix in (".docx", ".pdf")}
            out[ex.label] = stems
        return out

    def pdfs(self, group: Group) -> tuple[dict[str, str], dict[str, str], set[str]]:
        """Current and prior PDF origins by stem, and the stems a fallback folder filled."""
        current: dict[str, str] = {}
        prior: dict[str, str] = {}
        filled: set[str] = set()
        for index, folder in enumerate(group.pdf + group.fallback):
            found: dict[str, str] = {}
            for name, rel in self.files(folder, ".pdf"):
                m = _TAGGED.match(name) if group.tagged else None
                if group.tagged:
                    stem, tag = (m.group("stem"), m.group("tag")) if m else ("", "")
                    if tag == _PRIOR_TAG:
                        prior[stem] = rel
                        continue
                    if not m or (tag is not None and not _BUILD_TAG.match(tag)):
                        raise CorpusError(
                            f"unexpected name in {folder}: {name} "
                            "(want <stem>.pdf, <stem>.w<build>.pdf or <stem>.outdated.pdf)"
                        )
                else:
                    stem = Path(name).stem
                if stem in found:
                    raise CorpusError(f"two current references for {stem} in {folder}: {found[stem]}, {rel}")
                found[stem] = rel
            for stem, rel in found.items():
                if stem in current:
                    continue  # a later folder only fills gaps
                current[stem] = rel
                if index >= len(group.pdf):
                    filled.add(stem)
        return current, prior, filled

    # -- entries

    def pair_names(self, ds: Docset, name: str) -> tuple[str, str] | str:
        """The base and next names of the compare ``name``, or why they are unknown."""
        if ds.pair_split:
            base, sep, nxt = name.partition(PAIR_SEP)
            if not sep or not base or not nxt:
                return f"not a <base>{PAIR_SEP}<next> name"
            return base, nxt
        key = pair_stem(name)
        pairs = self.mapping(ds.mapping or "")
        if key not in pairs:
            return f"pair {key} is not in {ds.mapping}"
        return pairs[key]

    def entry(self, ds: Docset, rel: str, name: str, base: Document | None, nxt: Document | None) -> Document:
        sha = self.sha(rel)
        existing = self.by_sha.get(sha)
        if existing is None:
            doc_id = sha[:ID_LEN]
            other = self.by_id.get(doc_id)
            if other is not None:
                raise CorpusError(f"id collision: {rel} and {other.docx_src} share the id {doc_id!r}")
            state = state_name(docx_state(self.resolve(rel)))
            if base is None or nxt is None:
                existing = Document(doc_id, sha, document_stem(doc_id, name), state, (name,), (ds.name,), rel)
                self.documents.append(existing)
            else:
                existing = Comparison(
                    doc_id,
                    sha,
                    comparison_stem(base.stem, nxt.stem, doc_id),
                    state,
                    (name,),
                    (ds.name,),
                    rel,
                    base_id=base.id,
                    next_id=nxt.id,
                    base_name=base.names[0],
                    next_name=nxt.names[0],
                )
                self.comparisons.append(existing)
            self.by_sha[sha] = self.by_id[doc_id] = existing
        else:
            if (base is not None) != isinstance(existing, Comparison):
                raise CorpusError(f"{rel} and {existing.docx_src} are the same bytes but not the same kind")
            if name not in existing.names:
                existing.names += (name,)
            if ds.name not in existing.sets:
                existing.sets += (ds.name,)
        self.names.setdefault(ds.name, {})[name] = existing
        self.renames.append(Rename(rel, existing.docx, existing.id, sha, ds.name))
        return existing

    def attach(
        self, ds: Docset, entry: Document, rel: str, *, prior: bool, name: str, group: Group | None = None
    ) -> None:
        sha = self.sha(rel)
        if not prior and not entry.pdf_src:
            entry.pdf_src, entry.pdf_sha, entry.pdf_set = rel, sha, ds.name
            entry.producer = producer_name(pdf_meta(self.resolve(rel)))
            self.renames.append(Rename(rel, entry.pdf, entry.id, sha, ds.name))
            return
        if sha in (entry.pdf_sha, entry.pdf_prior_sha):
            return  # the same render seen from another origin
        if entry.pdf_prior_src:
            if group and not group.tagged and entry.pdf_prior_src.rpartition("/")[0] in group.pdf + group.fallback:
                # the same docx under several names of this set, each rendered on its own
                self.sets[ds.name].redundant += (name,)
                return
            raise CorpusError(f"second prior render for {entry.stem}: {entry.pdf_prior_src} and {rel}")
        entry.pdf_prior_src, entry.pdf_prior_sha = rel, sha
        self.renames.append(Rename(rel, entry.pdf_prior, entry.id, sha, ds.name))
        report = self.sets[ds.name]
        report.superseded += (name,)

    def word_pdf(self, report: SetReport, rel: str) -> bool:
        meta = pdf_meta(self.resolve(rel))
        if is_word_pdf(meta):
            return True
        report.refused[rel] = producer_name(meta)
        return False

    def plan_group(self, ds: Docset, group: Group, comparisons: bool) -> None:
        report = self.sets[ds.name]
        excluded = self.exclusions(ds)
        current, prior, filled = self.pdfs(group)
        docx = [(Path(n).stem, rel) for folder in group.docx for n, rel in self.files(folder, ".docx")]
        docx.sort()
        stems = {stem for stem, _ in docx}
        report.orphans += tuple(sorted(rel for stem, rel in (*current.items(), *prior.items()) if stem not in stems))
        ids: list[str] = []
        for name, rel in docx:
            names: tuple[str, ...] = (name,)
            pair: tuple[str, str] | str = ""
            if comparisons:
                pair = self.pair_names(ds, name)
                if isinstance(pair, tuple):
                    names = (name, *pair)
            labels = [label for label, members in excluded.items() if any(n in members for n in names)]
            sources_invalid = self.invalid_names.get(ds.sources or ds.name, set()) if comparisons else set()
            if self.sha(rel)[:ID_LEN] in self.invalid_ids or sources_invalid.intersection(names[1:]):
                self.invalid_names.setdefault(ds.name, set()).add(name)
                labels.append(WORD_INVALID_LABEL)
            if labels:
                for label in labels:
                    report.excluded[label] = (*report.excluded.get(label, ()), name)
                continue
            pdf_rel = current.get(name, "")
            prior_rel = prior.get(name, "")
            if pdf_rel and not self.word_pdf(report, pdf_rel):
                pdf_rel = ""
            if prior_rel and not self.word_pdf(report, prior_rel):
                prior_rel = ""
            if group.require_pdf and not pdf_rel:
                report.absent += (name,)
                continue
            base = nxt = None
            if comparisons:
                if isinstance(pair, str):
                    report.unresolved[name] = pair
                    continue
                sources_name = ds.sources or ds.name
                sources = self.names.get(sources_name, {})
                base, nxt = sources.get(pair[0]), sources.get(pair[1])
                if base is None or nxt is None:
                    which, missing = ("base", pair[0]) if base is None else ("next", pair[1])
                    report.unresolved[name] = f"{which} {missing} is not a document of {sources_name}"
                    continue
            entry = self.entry(ds, rel, name, base, nxt)
            if pdf_rel:
                self.attach(ds, entry, pdf_rel, prior=False, name=name, group=group)
                if name in filled:
                    report.filled += (name,)
            if prior_rel:
                self.attach(ds, entry, prior_rel, prior=True, name=name, group=group)
            if entry.id not in ids:
                ids.append(entry.id)
        if comparisons:
            report.comparisons = tuple(ids)
        else:
            report.documents = tuple(ids)

    def notes(self, selected: Sequence[Docset]) -> tuple[CopyItem, ...]:
        items: dict[str, CopyItem] = {}
        for ds in selected:
            for note in ds.notes:
                if not self.resolve(note.origin).is_file():
                    continue
                dst = f"{NOTICES_DIR}/{note.dest}"
                item = CopyItem(note.origin, dst)
                if dst in items and items[dst].src != note.origin and self.sha(items[dst].src) != self.sha(note.origin):
                    raise CorpusError(f"two notes want {dst}: {items[dst].src}, {note.origin}")
                items.setdefault(dst, item)
        return tuple(items.values())

    def run(self, only: Sequence[str] | None) -> Plan:
        selected = list(_select(only))
        skipped: list[str] = []
        if self.fixtures is None:
            skipped = [ds.name for ds in selected if ds.fixtures]
            if only is not None and skipped:
                raise CorpusError(f"{', '.join(skipped)}: these sets need a fixtures root (--fixtures)")
            selected = [ds for ds in selected if not ds.fixtures]
        names = {ds.name for ds in selected}
        for ds in selected:
            if ds.comparisons and ds.sources and ds.sources not in names:
                raise CorpusError(f"{ds.name} needs its sources set {ds.sources} in the selection")
        for ds in selected:
            self.sets[ds.name] = SetReport(ds.name)
        for ds in selected:
            if ds.documents:
                self.plan_group(ds, ds.documents, comparisons=False)
        for ds in selected:
            if ds.comparisons:
                self.plan_group(ds, ds.comparisons, comparisons=True)
        holdout, missing = self.holdout(selected)
        return Plan(
            tuple(self.documents),
            tuple(self.comparisons),
            self.sets,
            tuple(self.renames),
            self.notes(selected),
            tuple(skipped),
            holdout,
            missing,
        )

    def holdout(self, selected: Sequence[Docset]) -> tuple[tuple[str, ...], dict[str, tuple[str, ...]]]:
        """The comparison stems of every sealed list of the selection, found through the legacy
        ``<base>_<next>`` keys of their origin names, and the keys of each list no compare carries."""
        lists: dict[str, list[str]] = {}
        for ds in selected:
            if ds.holdout:
                lists.setdefault(ds.holdout, []).append(ds.name)
        stems: list[str] = []
        missing: dict[str, tuple[str, ...]] = {}
        for rel, set_names in lists.items():
            path = self.resolve(rel)
            if not path.is_file():
                raise CorpusError(f"missing holdout list {rel}")
            keys = [k.strip() for k in path.read_text().splitlines() if k.strip() and not k.lstrip().startswith("#")]
            by_key: dict[str, str] = {}
            for c in self.comparisons:
                if set(c.sets) & set(set_names):
                    for name in c.names:
                        by_key.setdefault(pair_stem(name), c.stem)
            found = [by_key[fold_key(k)] for k in keys if fold_key(k) in by_key]
            stems.extend(s for s in found if s not in stems)
            gone = tuple(k for k in keys if fold_key(k) not in by_key)
            if gone:
                missing[rel] = gone
        return tuple(stems), missing


def plan(root: Path, *, fixtures: Path | None = None, only: Sequence[str] | None = None) -> Plan:
    """Plan the corpus from the origins under ``root`` (and ``fixtures``): every entry with its
    id, stem, state, sets and names, every PDF placed, every rename, and per-set records of what
    is left out and why. Nothing is written."""
    return _Planner(Path(root), None if fixtures is None else Path(fixtures)).run(only)


# --- building ----------------------------------------------------------------------


@dataclass(frozen=True)
class BuildReport:
    sets: tuple[str, ...]
    copied: int
    skipped: int
    overwritten: int
    plan: Plan

    def describe(self) -> str:
        return (
            f"copied {self.copied}, skipped {self.skipped} identical, overwritten {self.overwritten} "
            f"for {', '.join(self.sets)}"
        )


def _same_bytes(a: Path, b: Path) -> bool:
    return a.stat().st_size == b.stat().st_size and hub.sha256_file(a) == hub.sha256_file(b)


def _clone_enabled() -> bool:
    return sys.platform == "darwin"


def stage_list(list_csv: Path, out: Path) -> int:
    """Clone the files a pool table names into ``out/docx`` and ``out/pdf``; returns the
    number of docx. The table's ``docx`` / ``pdf`` columns are relative to the corpus
    root (the folder above ``pools/``); an empty ``pdf`` is skipped. Idempotent."""
    list_csv, out = Path(list_csv), Path(out)
    root = list_csv.resolve().parent.parent
    n = 0
    with list_csv.open(newline="") as fh:
        for row in csv.DictReader(fh):
            for column in ("docx", "pdf"):
                rel = row.get(column) or ""
                if not rel:
                    continue
                dst = out / column / Path(rel).name
                if not dst.exists():
                    copy_file(root / rel, dst)
            n += bool(row.get("docx"))
    return n


def copy_file(src: Path, dst: Path) -> None:
    """Copy ``src`` to ``dst``: a clone on APFS (``cp -c``), a plain copy elsewhere. Never a hardlink:
    an edit to the copy must not reach the origin."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if _clone_enabled():
        done = subprocess.run([*CLONE_COMMAND, str(src), str(dst)], capture_output=True)
        if done.returncode == 0:
            return
    shutil.copy2(src, dst)


def docset_id_for(plan_: Plan, set_name: str) -> str:
    """The docset id of a set: :func:`ledger.docset.docset_id` over the stems of its entries."""
    report = plan_.sets[set_name]
    ids = {*report.documents, *report.comparisons}
    return docset_mod.docset_id(e.stem for e in plan_.entries if e.id in ids)


def _items(plan_: Plan) -> tuple[CopyItem, ...]:
    items: list[CopyItem] = []
    for e in plan_.entries:
        items.append(CopyItem(e.docx_src, e.docx))
        if e.pdf_src:
            items.append(CopyItem(e.pdf_src, e.pdf))
        if e.pdf_prior_src:
            items.append(CopyItem(e.pdf_prior_src, e.pdf_prior))
    items.extend(plan_.notes)
    return tuple(items)


_DOC_COLUMNS = ("id", "stem", "state", "docx", "pdf", "pdf_prior", "sets", "names", "sha256", "producer")
_CMP_COLUMNS = (
    "id", "key", "base_id", "next_id", "state", "docx", "pdf", "pdf_prior", "sets", "names", "sha256", "producer"
)
_RENAMED_COLUMNS = ("original", "new", "id", "sha256", "set")
_PAIRS_COLUMNS = ("key", "base", "next", "base_name", "next_name", "docx", "pdf", "state")
_RENDERS_COLUMNS = ("key", "kind", "docx", "pdf", "state")
_LIST_SEP = ";"


def _write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)


def _doc_row(d: Document) -> tuple[str, ...]:
    return (
        d.id,
        d.stem,
        d.state,
        d.docx,
        d.pdf,
        d.pdf_prior,
        _LIST_SEP.join(d.sets),
        _LIST_SEP.join(d.names),
        d.sha256,
        d.producer,
    )


def _cmp_row(c: Comparison) -> tuple[str, ...]:
    row = _doc_row(c)
    return (c.id, c.stem, c.base_id, c.next_id, *row[2:])


def _set_entries(plan_: Plan, set_name: str) -> tuple[list[Document], list[Comparison]]:
    """The documents and comparisons of a set in its report order."""
    by_id = {e.id: e for e in plan_.entries}
    report = plan_.sets[set_name]
    docs = [by_id[i] for i in report.documents]
    cmps = [c for c in (by_id[i] for i in report.comparisons) if isinstance(c, Comparison)]
    return docs, cmps


HOLDOUT_NAME = "holdout.txt"


def _write_pools(dest: Path, plan_: Plan) -> None:
    by_id = {e.id: e for e in plan_.entries}
    holdout = dest / POOLS_DIR / HOLDOUT_NAME
    if plan_.holdout:
        origins = sorted({ds.holdout for ds in DOCSETS if ds.name in plan_.sets and ds.holdout})
        header = [
            "# Sealed holdout: comparison stems left out of every normal scoring run (bench run --holdout).",
            "# Translated from the legacy <base>_<next> keys of " + ", ".join(origins) + ".",
        ]
        holdout.parent.mkdir(parents=True, exist_ok=True)
        holdout.write_text("\n".join([*header, *plan_.holdout]) + "\n")
    elif holdout.exists():
        holdout.unlink()
    for name in plan_.sets:
        docs, cmps = _set_entries(plan_, name)
        pairs = dest / POOLS_DIR / f"{name}_pairs.csv"
        renders = dest / POOLS_DIR / f"{name}_renders.csv"
        if docset(name).comparisons:
            _write_csv(
                pairs,
                _PAIRS_COLUMNS,
                (
                    (
                        c.stem,
                        by_id[c.base_id].docx.removesuffix(".docx"),
                        by_id[c.next_id].docx.removesuffix(".docx"),
                        c.base_name,
                        c.next_name,
                        c.docx,
                        c.pdf,
                        c.state,
                    )
                    for c in cmps
                ),
            )
        elif pairs.exists():
            pairs.unlink()
        rendered = [e for e in (*docs, *cmps) if e.pdf_set == name]
        if rendered:
            _write_csv(renders, _RENDERS_COLUMNS, ((e.stem, e.kind, e.docx, e.pdf, e.state) for e in rendered))
        elif renders.exists():
            renders.unlink()


def _provenance(plan_: Plan) -> dict[str, Any]:
    sets: dict[str, Any] = {}
    for name, report in plan_.sets.items():
        ds = docset(name)
        sets[name] = {
            "description": ds.description,
            "origins": list(ds.folders),
            "mapping": ds.mapping,
            "sources": ds.sources or (name if ds.comparisons else None),
            "n_documents": len(report.documents),
            "n_comparisons": len(report.comparisons),
            "docset_id": docset_id_for(plan_, name),
            "absent": list(report.absent),
            "superseded": list(report.superseded),
            "redundant": list(report.redundant),
            "filled": list(report.filled),
            "orphans": list(report.orphans),
            "excluded": {k: list(v) for k, v in report.excluded.items()},
            "unresolved": dict(report.unresolved),
            "refused": dict(report.refused),
        }
    entries = plan_.entries
    return {
        "id_scheme": ID_SCHEME,
        "license": LICENSE,
        "dataset": DATASET,
        "states": list(STATES),
        "counts": {
            "documents": len(plan_.documents),
            "comparisons": len(plan_.comparisons),
            "pdf": sum(bool(e.pdf) for e in entries),
            "pdf_prior": sum(bool(e.pdf_prior) for e in entries),
        },
        "sets": sets,
        "skipped": list(plan_.skipped),
        "notes": [item.dst for item in plan_.notes],
        "holdout": {
            "list": f"{POOLS_DIR}/{HOLDOUT_NAME}" if plan_.holdout else None,
            "n": len(plan_.holdout),
            "missing": {k: list(v) for k, v in plan_.holdout_missing.items()},
        },
    }


_NAMING_NOTE = f"""# Names in the Word corpus

Every file carries the id of the docx it represents: the first {ID_LEN} hex digits of the
sha256 of that docx's bytes ({ID_SCHEME}).

* A file that is not a comparison: `<id>_<name>`, the id at the beginning. Its Word PDF has
  the same stem.
* A file that is a comparison (a Word compare of two documents): `<idA>_<a>{PAIR_SEP}<idB>_<b>{REDLINE}_<idC>`,
  the two compared documents with their ids, then `{REDLINE}_` and the id of the compare itself
  (a third id, different from the other two). Its Word PDF has the same stem.
* A tool's output for a Word file is the Word stem plus `_<tool>`: `<id>_<name>_<tool>` and
  `<idA>_<a>{PAIR_SEP}<idB>_<b>{REDLINE}_<idC>_<tool>`. The scorer keys a candidate by stripping
  that suffix.

Names are lower-cased, anything but `[a-z0-9_-]` becomes `_`, and a name is cut at {STEM_MAX}
characters (paths were failing the 256-character limit). The original names are kept in
`RENAMED.csv` (one row per origin file: original, new, id, sha256, set) and in the `names`
column of `documents.csv` and `comparisons.csv`.

Files live by the state of the docx, read from its XML: `{STATES[0]}`, `{STATES[1]}`,
`{STATES[2]}`, `{STATES[3]}`. A comparison lives in the state of the compared docx. Under
each state: `docx/`, `pdf/` (the current Word render) and `pdf_prior/` (a render an earlier
Word build made of the same docx, under the same name).

Byte-identical docx from several origins are one file; every origin name and set is recorded
on the one entry. Two different docx sharing an id fail the build.

The other files in this folder are the origins' own notices, copied as found: the license
of the superdoc docx-corpus sample, its NOTICE and manifests, the pair lists, the Word
blacklist and the logs of the compare runs.
"""


def _readme(rows: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# The Word corpus",
        "",
        "What Microsoft Word produced, gathered from its working folders by `bench corpus build`",
        "(the set table is `DOCSETS` in `neurotic_docx_bench/word_corpus.py`). Every file here is a",
        "copy; the origins were not moved or deleted. Only what Word finished is here: a docx Word",
        "could not open, a document or compare it did not render in a render run, a blacklisted",
        "document with the pairs that touch it, and a PDF another producer made are listed per set in",
        f"`{PROVENANCE_NAME}` (`excluded`, `absent`, `refused`) and not copied. `bench corpus check`",
        f"verifies the tree against `{MANIFEST_NAME}`; `bench corpus list` prints the table below.",
        "",
        f"Files are named by the id of their docx and live by state; `{NOTICES_DIR}/{README_NAME}` has the",
        f"scheme and `{NOTICES_DIR}/{RENAMED_NAME}` the rename record. `{DOCUMENTS_NAME}` and",
        f"`{COMPARISONS_NAME}` list every entry with its state, sets, origin names, sha256 and the",
        f"producer of its Word PDF. `{POOLS_DIR}/<set>_pairs.csv` (key, base, next, ...) is the manifest a",
        "generator takes with `--source-dir` pointing here, and `pools/<set>_renders.csv` lists the",
        "docx that set's Word run rendered with their PDFs.",
        "",
        "docx and PDF files are gitignored (they live in the fixtures dataset on the Hub); the",
        "manifest, provenance, tables, pools and notices are tracked.",
        "",
        "| set | documents | comparisons | docset id | absent | superseded | filled | unresolved "
        "| excluded | refused |",
        "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['name']} | {row['documents']} | {row['comparisons']} | {row['docset_id']} | {row['absent']} "
            f"| {row['superseded']} | {row['filled']} | {row['unresolved']} | {row['excluded']} | {row['refused']} |"
        )
    lines += ["", "## Sets", ""]
    for row in rows:
        ds = docset(row["name"])
        lines += [f"### {ds.name}", "", ds.description, ""]
        for group, kind in ((ds.documents, "documents"), (ds.comparisons, "comparisons")):
            if group:
                lines.append(f"* {kind}: " + ", ".join(f"`{o}`" for o in group.docx))
                if group.pdf:
                    lines.append("* their Word PDFs: " + ", ".join(f"`{o}`" for o in group.pdf))
                if group.fallback:
                    lines.append("* filling the gaps: " + ", ".join(f"`{o}`" for o in group.fallback))
        if ds.mapping:
            lines.append(f"* pairs: `{ds.mapping}`")
        if ds.comparisons:
            lines.append(f"* base/next documents: the `{ds.sources or ds.name}` set")
        lines.append("")
    return "\n".join(lines)


def _write_records(dest: Path, plan_: Plan) -> None:
    _write_csv(dest / DOCUMENTS_NAME, _DOC_COLUMNS, (_doc_row(d) for d in plan_.documents))
    _write_csv(dest / COMPARISONS_NAME, _CMP_COLUMNS, (_cmp_row(c) for c in plan_.comparisons))
    _write_csv(
        dest / NOTICES_DIR / RENAMED_NAME,
        _RENAMED_COLUMNS,
        ((r.original, r.new, r.id, r.sha256, r.set) for r in plan_.renames),
    )
    (dest / NOTICES_DIR / README_NAME).write_text(_NAMING_NOTE)
    _write_pools(dest, plan_)
    (dest / PROVENANCE_NAME).write_text(json.dumps(_provenance(plan_), indent=1, sort_keys=True) + "\n")
    (dest / README_NAME).write_text(_readme(summary(dest)) + "\n")


def build(
    root: Path,
    dest: Path,
    *,
    fixtures: Path | None = None,
    only: Sequence[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> BuildReport:
    """Copy the sets of ``only`` (default all) from the origins under ``root`` (and ``fixtures``)
    into ``dest`` and write the tables, pools, notices, provenance and manifest.

    Everything is planned and every existing destination file is compared before anything is
    copied, so a ``differs`` error leaves the tree as it was.
    """
    root, dest = Path(root), Path(dest)
    planner = _Planner(root, None if fixtures is None else Path(fixtures))
    plan_ = planner.run(only)
    actions: list[tuple[str, Path, Path]] = []  # ("copy" | "skip" | "overwrite", src, dst)
    for item in _items(plan_):
        src = planner.resolve(item.src)
        dst = dest / item.dst
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
    report = BuildReport(tuple(plan_.sets), copied, skipped, overwritten, plan_)
    if dry_run:
        return report
    for action, src, dst in actions:
        if action == "overwrite":
            dst.unlink()  # our own earlier copy; a fresh clone rather than a write into it
        if action != "skip":
            copy_file(src, dst)
    dest.mkdir(parents=True, exist_ok=True)
    _write_records(dest, plan_)
    hub.write_manifest(dest)
    return report


def check(dest: Path) -> hub.ManifestReport:
    """Verify ``dest`` against its manifest."""
    try:
        return hub.verify_manifest(Path(dest))
    except hub.ManifestError as exc:
        raise CorpusError(str(exc)) from exc


def summary(dest: Path) -> list[dict[str, Any]]:
    """One row per built set, in table order, from the provenance file; ``[]`` when nothing is built."""
    path = Path(dest) / PROVENANCE_NAME
    if not path.is_file():
        return []
    sets = json.loads(path.read_text())["sets"]
    rows: list[dict[str, Any]] = []
    for ds in DOCSETS:
        s = sets.get(ds.name)
        if s is None:
            continue
        rows.append(
            {
                "name": ds.name,
                "documents": s["n_documents"],
                "comparisons": s["n_comparisons"],
                "docset_id": s["docset_id"],
                "absent": len(s["absent"]),
                "superseded": len(s["superseded"]),
                "filled": len(s["filled"]),
                "orphans": len(s["orphans"]),
                "unresolved": len(s["unresolved"]),
                "excluded": sum(len(v) for v in s["excluded"].values()),
                "refused": len(s["refused"]),
            }
        )
    return rows


def corpus_entries(dest: Path = DEFAULT_DEST) -> tuple[CorpusEntry, ...]:
    """The built comparison sets as ``CorpusEntry`` pools: ``pools/<set>_pairs.csv`` is the base/next
    manifest and the corpus root is the source dir (base and next are corpus-relative stems).
    Not registered in bench.yaml by this module."""
    out = []
    for ds in DOCSETS:
        pairs = Path(dest) / POOLS_DIR / f"{ds.name}_pairs.csv"
        if ds.comparisons is None or not pairs.is_file():
            continue
        out.append(CorpusEntry(name=f"word_{ds.name}", manifest=pairs.as_posix(), source_dir=Path(dest).as_posix()))
    return tuple(out)
