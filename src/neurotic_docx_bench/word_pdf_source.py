"""Which Word PDFs ``docx-to-pdf`` and ``docxide-metrics`` measure.

The source of truth is ``corpus/word/<state>/pdf`` next to ``<state>/docx``.
``pdf_prior`` is an earlier render of the same docx, not the oracle.

Two acceptance rules, and neither one is an error:

* Conversion: every Word PDF whose DOCX equivalent exists. A DOCX with no Word
  PDF, and a Word PDF with no DOCX, are warnings and are not converted.
* ``--score-only``: every Word PDF for which a PDF to score is also present
  (same stem, or that stem plus ``_<tool>``). The DOCX is not required.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from neurotic_docx_bench.docx_to_pdf import Fixture
from neurotic_docx_bench.pipeline import render_key
from neurotic_docx_bench.word_corpus import DEFAULT_DEST, STATES

ORIGINS = (*STATES, "all", "list")


@dataclass(frozen=True)
class CorpusWordSelection:
    """Fixtures to measure, warnings for what was left out, and score-only PDFs.

    ``candidates`` is keyed by :attr:`Fixture.stem` and is empty unless
    ``score_only`` was set. An empty ``fixtures`` list is a warning result,
    not an exception: the caller decides whether nothing-to-measure is fatal.
    """

    fixtures: list[Fixture] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    candidates: dict[str, Path] = field(default_factory=dict)


def word_pdf_from_config(path: Path | str) -> tuple[Path, tuple[str, ...]]:
    """``word_pdf.root`` and ``word_pdf.states`` from a bench yaml.

    Relative ``root`` is resolved against the yaml file's directory. Missing
    ``word_pdf`` falls back to :data:`word_corpus.DEFAULT_DEST` and
    :data:`word_corpus.STATES`.
    """
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    block = data.get("word_pdf") or {}
    raw_root = block.get("root") or DEFAULT_DEST.as_posix()
    root = Path(raw_root)
    if not root.is_absolute():
        root = path.parent / root
    states = tuple(block.get("states") or STATES)
    unknown = [name for name in states if name not in STATES]
    if unknown:
        raise ValueError(
            f"{path}: word_pdf.states has unknown state(s) {unknown}; known: {list(STATES)}",
        )
    return root, states


def select_corpus_word_pdfs(
    *,
    origin: str,
    root: Path | str = DEFAULT_DEST,
    states: Sequence[str] = STATES,
    files_list: Sequence[Path] = (),
    score_only: bool = False,
    locations: Sequence[Path] = (),
    tool: str | None = None,
) -> CorpusWordSelection:
    """Apply the conversion rule or the score-only rule to ``origin``.

    ``origin`` is one state name, ``all``, or ``list``. ``list`` requires
    ``files_list``. ``--files-list`` without ``list`` is an error. Entries must
    already live under ``<state>/docx`` or ``<state>/pdf``. ``score_only``
    requires ``locations`` (a folder of PDFs, or PDF paths).
    """
    root = Path(root)
    known = tuple(states)
    files = [Path(p) for p in files_list]
    locs = [Path(p) for p in locations]
    if origin not in (*known, "all", "list"):
        raise ValueError(f"unknown origin {origin!r}; known: {list(known)}, all, list")
    if files and origin != "list":
        raise ValueError("--files-list requires origin list")
    if origin == "list" and not files:
        raise ValueError("origin list requires --files-list")
    if score_only and not locs:
        raise ValueError("--score-only requires --location-to-score")
    if locs and not score_only:
        raise ValueError("--location-to-score requires --score-only")

    warnings: list[str] = []
    if origin == "list":
        rows = [_listed_row(path, root, known) for path in files]
    else:
        chosen = known if origin == "all" else (origin,)
        rows = []
        for state in chosen:
            rows.extend(_scan_state(root, state, warnings))

    if score_only:
        return _score_only(rows, warnings, locs, tool)
    return _for_conversion(rows, warnings)


def _scan_state(root: Path, state: str, warnings: list[str]) -> list[tuple[str, Path | None, Path | None]]:
    docx_dir = root / state / "docx"
    pdf_dir = root / state / "pdf"
    if not docx_dir.is_dir() and not pdf_dir.is_dir():
        warnings.append(f"no docx/ or pdf/ under {root / state}; skipped")
        return []
    docx = _files(docx_dir, ".docx") if docx_dir.is_dir() else {}
    pdfs = _files(pdf_dir, ".pdf") if pdf_dir.is_dir() else {}
    rows: list[tuple[str, Path | None, Path | None]] = []
    for stem in sorted(set(docx) | set(pdfs)):
        rows.append((state, docx.get(stem), pdfs.get(stem)))
    return rows


def _files(folder: Path, suffix: str) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in sorted(folder.glob(f"*{suffix}")):
        if not path.is_file() or path.name.startswith("~$"):
            continue
        found[path.stem] = path
    return found


def _listed_row(path: Path, root: Path, states: Sequence[str]) -> tuple[str, Path | None, Path | None]:
    resolved = path.expanduser().resolve()
    try:
        rel = resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{path} is not in the corpus under {root}") from exc
    parts = rel.parts
    if len(parts) != 3 or parts[0] not in states or parts[1] not in {"docx", "pdf"}:
        if len(parts) >= 2 and parts[1] == "pdf_prior":
            raise ValueError(
                f"{path} is in pdf_prior, which is not the current Word PDF; "
                f"use {parts[0]}/pdf/{Path(parts[-1]).stem}.pdf",
            )
        raise ValueError(
            f"{path} is not a corpus docx or Word PDF "
            f"(expected <state>/docx/<stem>.docx or <state>/pdf/<stem>.pdf)",
        )
    if not resolved.is_file():
        raise ValueError(f"{path} is not a file in the corpus")
    state, kind, name = parts
    stem = Path(name).stem
    if kind == "docx":
        if resolved.suffix.lower() != ".docx":
            raise ValueError(f"{path} is in docx/ but is not a .docx")
        pdf = root / state / "pdf" / f"{stem}.pdf"
        return state, resolved, pdf if pdf.is_file() else None
    if resolved.suffix.lower() != ".pdf":
        raise ValueError(f"{path} is in pdf/ but is not a .pdf")
    docx = root / state / "docx" / f"{stem}.docx"
    return state, docx if docx.is_file() else None, resolved


def _fixture(state: str, docx: Path | None, pdf: Path) -> Fixture:
    stem = pdf.stem
    return Fixture(
        stem=f"{state}__{stem}",
        kind=state,
        original_stem=stem,
        docx=docx if docx is not None else (pdf.parent.parent / "docx" / f"{stem}.docx"),
        oracle=pdf,
    )


def _for_conversion(
    rows: Sequence[tuple[str, Path | None, Path | None]],
    warnings: list[str],
) -> CorpusWordSelection:
    """Every Word PDF that has its DOCX. Anything unpaired is a warning."""
    fixtures: list[Fixture] = []
    seen: set[str] = set()
    for state, docx, pdf in rows:
        label = (docx or pdf)
        assert label is not None
        if pdf is None or not pdf.is_file():
            warnings.append(f"no Word PDF for {docx}; skipped")
            continue
        if docx is None or not docx.is_file():
            warnings.append(f"no DOCX for {pdf}; skipped")
            continue
        item = _fixture(state, docx, pdf)
        if item.stem in seen:
            continue
        seen.add(item.stem)
        fixtures.append(item)
    return CorpusWordSelection(fixtures=fixtures, warnings=warnings)


def _score_only(
    rows: Sequence[tuple[str, Path | None, Path | None]],
    warnings: list[str],
    locations: Sequence[Path],
    tool: str | None,
) -> CorpusWordSelection:
    """Every Word PDF that has a PDF to score. A missing DOCX is allowed."""
    index = _candidate_index(locations, tool)
    used: set[str] = set()
    fixtures: list[Fixture] = []
    candidates: dict[str, Path] = {}
    seen: set[str] = set()
    for state, docx, pdf in rows:
        if pdf is None or not pdf.is_file():
            if docx is not None:
                warnings.append(f"no Word PDF for {docx}; skipped")
            continue
        key = render_key(pdf.stem, None)
        cand = index.get(key)
        if cand is None:
            warnings.append(f"no PDF to score for {pdf}; skipped")
            continue
        item = _fixture(state, docx, pdf)
        if item.stem in seen:
            continue
        seen.add(item.stem)
        used.add(key)
        fixtures.append(item)
        candidates[item.stem] = cand
    for key, path in sorted(index.items()):
        if key not in used:
            warnings.append(f"no Word PDF for {path}; skipped")
    return CorpusWordSelection(fixtures=fixtures, warnings=warnings, candidates=candidates)


def _candidate_index(locations: Sequence[Path], tool: str | None) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for loc in locations:
        loc = loc.expanduser()
        if not loc.exists():
            raise ValueError(f"--location-to-score not found: {loc}")
        if loc.is_file():
            pdfs = [loc]
            if loc.suffix.lower() != ".pdf":
                raise ValueError(f"--location-to-score is not a PDF: {loc}")
        elif loc.is_dir():
            pdfs = [p for p in sorted(loc.glob("*.pdf")) if p.is_file() and not p.name.startswith("~$")]
            if not pdfs:
                raise ValueError(f"--location-to-score has no PDFs: {loc}")
        else:
            raise ValueError(f"--location-to-score is not a PDF or a folder: {loc}")
        for pdf in pdfs:
            key = render_key(pdf.stem, tool)
            previous = found.get(key)
            if previous is not None and previous.resolve() != pdf.resolve():
                raise ValueError(f"two PDFs to score share {key}: {previous} and {pdf}")
            found[key] = pdf
    return found
