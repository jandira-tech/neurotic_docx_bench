"""The LibreOffice corpus: ``corpus/libreoffice/<state>/pdf/<word stem>.pdf`` and ``word_map.csv``.

Before Word printed its own PDFs, the bench scored against LibreOffice 26.2.4.2 renders of
Word's files: the redline oracle (``script_redlines``, ``visual_redlines``), the source
renders (``visual_rendering``) and the renders of Word's accept-all (``visual_accepted_changes``).
They lived beside the docx they rendered, under the docx's own name. Here each is filed under
the stem that docx has in the Word corpus (found by its sha256 in ``documents.csv`` /
``comparisons.csv``), so a LibreOffice render and the Word PDF of the same docx share a name,
and ``word_map.csv`` maps every render to the Word docx and the Word PDF.

A render whose docx is gone, whose docx is not in the Word corpus, or whose producer is not
LibreOffice is left out and recorded in ``PROVENANCE.json``. Origins are read, never written;
the tree is built by copy and a build is idempotent.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neurotic_docx_bench import hub
from neurotic_docx_bench.word_corpus import (
    _SD,
    _WB,
    COMPARISONS_NAME,
    DOCUMENTS_NAME,
    PROVENANCE_NAME,
    README_NAME,
    copy_file,
    pdf_meta,
    producer_name,
)

DEFAULT_DEST = Path('corpus/libreoffice')
DEFAULT_WORD = Path('corpus/word')
MAP_NAME = 'word_map.csv'


class LibreofficeCorpusError(Exception):
    pass


@dataclass(frozen=True)
class LoSet:
    name: str
    pdf: str  # the LibreOffice renders
    docx: str  # the docx they rendered, same stem
    used_as: str  # what the bench scored against them


LO_SETS: tuple[LoSet, ...] = (
    LoSet(
        'word_based_redlines',
        f'{_WB}/pdf_redlines_word',
        f'{_WB}/docx_redlines_word',
        'script_redlines and visual_redlines oracle (bench.yaml source_of_truth)',
    ),
    LoSet(
        'word_based_randomized_redlines',
        f'{_WB}/pdf_redlines_randomized/pdf',
        f'{_WB}/docx_redlines_randomized',
        'script_redlines oracle (bench.yaml extra_oracle_dirs)',
    ),
    LoSet(
        'word_redlines_superdoc_redlines',
        f'{_SD}/pdf_redlines_word',
        f'{_SD}/docx_redlines_word',
        'script_redlines oracle (bench.yaml extra_oracle_dirs)',
    ),
    LoSet('word_based_sources', f'{_WB}/pdf_source', f'{_WB}/docx_source', 'visual_rendering oracle'),
    LoSet(
        'word_based_accepted_word',
        f'{_WB}/pdf_accepted_word',
        f'{_WB}/word_working_roundtrip',
        'visual_accepted_changes oracle',
    ),
)

_MAP_COLUMNS = (
    'libreoffice_pdf',
    'key',
    'kind',
    'word_id',
    'word_docx',
    'word_pdf',
    'word_pdf_producer',
    'set',
    'used_as',
    'origin',
    'docx_origin',
    'producer',
    'sha256',
)


@dataclass(frozen=True)
class Entry:
    set: str
    origin: str  # the LibreOffice PDF, repo-relative
    docx_origin: str
    sha256: str
    producer: str
    word_id: str
    kind: str  # document | comparison
    state: str
    stem: str
    word_docx: str  # relative to the Word corpus
    word_pdf: str  # relative to the Word corpus; "" when Word never printed that docx
    word_pdf_producer: str

    @property
    def dest(self) -> str:
        return f'{self.state}/pdf/{self.stem}.pdf'


@dataclass
class SetReport:
    entries: list[Entry] = field(default_factory=list)
    unmatched: dict[str, str] = field(default_factory=dict)
    refused: dict[str, str] = field(default_factory=dict)  # origin -> producer
    redundant: list[str] = field(default_factory=list)  # a further render of a docx already filed


@dataclass(frozen=True)
class Plan:
    entries: tuple[Entry, ...]
    sets: dict[str, SetReport]


def _word_rows(word: Path) -> dict[str, tuple[str, dict[str, str]]]:
    """sha256 of the docx -> (kind, row) over the Word corpus tables."""
    if not (word / DOCUMENTS_NAME).is_file():
        raise LibreofficeCorpusError(f'no Word corpus at {word}; run `bench corpus build` first')
    out: dict[str, tuple[str, dict[str, str]]] = {}
    for kind, name in (('document', DOCUMENTS_NAME), ('comparison', COMPARISONS_NAME)):
        path = word / name
        if not path.is_file():
            continue
        with path.open(newline='') as fh:
            for row in csv.DictReader(fh):
                out[row['sha256']] = (kind, row)
    return out


def _is_libreoffice(producer: str) -> bool:
    return 'libreoffice' in producer.lower()


def plan(root: Path, word: Path = DEFAULT_WORD, sets: Sequence[LoSet] = LO_SETS) -> Plan:
    root, word = Path(root), Path(word)
    rows = _word_rows(word)
    reports: dict[str, SetReport] = {}
    entries: list[Entry] = []
    taken: dict[str, Entry] = {}
    for lo in sets:
        report = reports[lo.name] = SetReport()
        folder = root / lo.pdf
        if not folder.is_dir():
            raise LibreofficeCorpusError(f'missing origin folder {lo.pdf}')
        for pdf in sorted(p for p in folder.iterdir() if p.is_file() and p.suffix == '.pdf'):
            origin = f'{lo.pdf}/{pdf.name}'
            meta = pdf_meta(pdf)
            producer = producer_name(meta)
            if not _is_libreoffice(meta.producer + meta.creator):
                report.refused[origin] = producer
                continue
            docx_origin = f'{lo.docx}/{pdf.stem}.docx'
            docx = root / docx_origin
            if not docx.is_file():
                report.unmatched[origin] = f'no docx {docx_origin}'
                continue
            hit = rows.get(hub.sha256_file(docx))
            if hit is None:
                report.unmatched[origin] = f'{docx_origin} is not in the Word corpus'
                continue
            kind, row = hit
            stem = row.get('stem') or row['key']
            sha = hub.sha256_file(pdf)
            pdf_producer = row['producer'] if row['pdf'] else ''
            entry = Entry(
                lo.name,
                origin,
                docx_origin,
                sha,
                producer,
                row['id'],
                kind,
                row['state'],
                stem,
                row['docx'],
                row['pdf'],
                pdf_producer,
            )
            if entry.dest in taken:
                # the same docx under another name, rendered again: the first render stands
                report.redundant.append(origin)
                continue
            taken[entry.dest] = entry
            report.entries.append(entry)
            entries.append(entry)
    return Plan(tuple(entries), reports)


def _provenance(plan_: Plan, sets: Sequence[LoSet]) -> dict[str, Any]:
    by_name = {s.name: s for s in sets}
    return {
        'scheme': '<state>/pdf/<stem>.pdf, the stem of the rendered docx in corpus/word',
        'sets': {
            name: {
                'pdf': by_name[name].pdf,
                'docx': by_name[name].docx,
                'used_as': by_name[name].used_as,
                'n': len(r.entries),
                'with_word_pdf': sum(1 for e in r.entries if e.word_pdf),
                'unmatched': dict(sorted(r.unmatched.items())),
                'refused': dict(sorted(r.refused.items())),
                'redundant': sorted(r.redundant),
            }
            for name, r in plan_.sets.items()
        },
    }


def _readme(prov: dict[str, Any]) -> str:
    lines = [
        '# The LibreOffice corpus',
        '',
        'LibreOffice renders of Word files that the bench once used as its source of truth, each',
        'filed under the stem its docx has in `corpus/word`, so the render and the Word PDF of the',
        'same docx share a name. `word_map.csv` maps every render to that Word docx and Word PDF',
        '(`word_pdf` empty where Word never printed the docx). Built by `bench corpus libreoffice`',
        '(`neurotic_docx_bench/libreoffice_corpus.py`); `PROVENANCE.json` lists what was left out.',
        '',
        '| set | renders | with a Word PDF | unmatched | refused | used as |',
        '|---|---:|---:|---:|---:|---|',
    ]
    for name, s in prov['sets'].items():
        lines.append(
            f'| {name} | {s["n"]} | {s["with_word_pdf"]} | {len(s["unmatched"])} | {len(s["refused"])} | {s["used_as"]} |'
        )
    return '\n'.join(lines) + '\n'


def build(
    root: Path,
    dest: Path = DEFAULT_DEST,
    *,
    word: Path = DEFAULT_WORD,
    sets: Sequence[LoSet] = LO_SETS,
    dry_run: bool = False,
) -> Plan:
    root, dest, word = Path(root), Path(dest), Path(word)
    plan_ = plan(root, word, sets)
    for e in plan_.entries:
        dst = dest / e.dest
        if dst.exists():
            if hub.sha256_file(dst) == e.sha256:
                continue
            raise LibreofficeCorpusError(f'{dst} differs from {e.origin}')
        if not dry_run:
            copy_file(root / e.origin, dst)
    if dry_run:
        return plan_
    dest.mkdir(parents=True, exist_ok=True)
    with (dest / MAP_NAME).open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(_MAP_COLUMNS)
        for e in plan_.entries:
            w.writerow((
                e.dest,
                e.stem,
                e.kind,
                e.word_id,
                e.word_docx,
                e.word_pdf,
                e.word_pdf_producer,
                e.set,
                next(s.used_as for s in sets if s.name == e.set),
                e.origin,
                e.docx_origin,
                e.producer,
                e.sha256,
            ))
    prov = _provenance(plan_, sets)
    (dest / PROVENANCE_NAME).write_text(json.dumps(prov, indent=1, sort_keys=True) + '\n')
    (dest / README_NAME).write_text(_readme(prov))
    hub.write_manifest(dest)
    return plan_
