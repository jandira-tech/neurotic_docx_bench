"""Controlled single-mutation DOCX probes (seed → mutated pairs).

Each probe applies exactly one structural mutation to a seed DOCX so a redline tool
can be scored per capability (did it catch an inserted sentence? a deleted table
row? a formatting-only change?) instead of one opaque corpus-level score.

The sentence probes (insert_sentence/delete_sentence) mutate text INSIDE a
paragraph — the paragraph count never changes — while the paragraph probes
(insert_paragraph/delete_paragraph) add/remove a whole paragraph. Structure
mutations (split/merge) preserve pPr and run-level rPr so the only delta a
redline tool should see is the intended one.

Only ``word/document.xml`` is rewritten; every other zip part is carried over
byte-identical with entry order preserved, so any diff a tool reports is
attributable to the single intended mutation.
"""

from __future__ import annotations

import io
import zipfile
from copy import deepcopy
from itertools import pairwise
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
DOCUMENT_PART = 'word/document.xml'


def _w(tag: str) -> str:
    return f'{{{W_NS}}}{tag}'


# ---------------------------------------------------------------------------
# Seed content — module constants shared with tests so delta assertions can't
# drift from what make_default_seed() actually emits.
# ---------------------------------------------------------------------------

SEED_CLAUSES: tuple[str, ...] = (
    'Section 1. This Agreement is entered into by the parties as of the Effective Date.',
    'Section 2. The Supplier shall deliver the goods to the Buyer at the designated facility.',
    'Section 3. Payment is due within thirty days of receipt. Late payments accrue interest.',
    'Section 4. Either party may terminate this Agreement upon sixty days written notice.',
    'Section 5. The parties shall keep the terms of this Agreement confidential.',
    'Section 6. This Agreement is governed by the laws of the State of Illinois.',
    'Section 7. Any dispute arising under this Agreement shall be resolved by arbitration.',
)

SEED_LIST_ITEMS: tuple[str, ...] = (
    'First deliverable: signed statement of work.',
    'Second deliverable: acceptance test plan.',
    'Third deliverable: final project report.',
)

SEED_TABLE_ROWS: tuple[tuple[str, str], ...] = (('Milestone', 'Date'), ('Kickoff', 'March 1'))

INSERTED_SENTENCE = 'The parties further acknowledge the inserted probe sentence.'
INSERTED_PARAGRAPH = 'Inserted clause: the parties acknowledge the mutation probe.'
ADDED_LIST_ITEM = 'Fourth deliverable: added list item probe.'


class ProbeNotApplicable(Exception):
    """The seed lacks the structure this probe mutates (no table, no list, ...)."""

    def __init__(self, name: str, reason: str) -> None:
        super().__init__(f'{name}: {reason}')
        self.name = name
        self.reason = reason


@dataclass(frozen=True)
class ProbeRecord:
    name: str
    path: Path | None
    applicable: bool
    reason: str | None = None


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------


def _para_text(p: etree._Element) -> str:
    return ''.join(t.text or '' for t in p.iter(_w('t')))


def _body(root: etree._Element) -> etree._Element:
    body = root.find(_w('body'))
    if body is None:
        raise ValueError('document.xml has no w:body')
    return body


def _top_level_paragraphs(body: etree._Element) -> list[etree._Element]:
    """Direct w:p children of the body (table-cell paragraphs excluded)."""
    return list(body.findall(_w('p')))


def _plain_paragraphs(body: etree._Element) -> list[etree._Element]:
    """Top-level text-bearing paragraphs that are not list items."""
    return [
        p
        for p in _top_level_paragraphs(body)
        if _para_text(p).strip() and p.find(f'{_w("pPr")}/{_w("numPr")}') is None
    ]


def _list_paragraphs(body: etree._Element) -> list[etree._Element]:
    """Top-level paragraphs carrying a w:numPr (numbered-list items)."""
    return [p for p in _top_level_paragraphs(body) if p.find(f'{_w("pPr")}/{_w("numPr")}') is not None]


def _make_run(text: str) -> etree._Element:
    r = etree.Element(_w('r'))
    t = etree.SubElement(r, _w('t'))
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return r


def _make_paragraph(text: str) -> etree._Element:
    p = etree.Element(_w('p'))
    p.append(_make_run(text))
    return p


def _trim_runs(p: etree._Element, start: int, end: int | None) -> None:
    """Keep only the character range [start, end) of p's text, in place.

    Runs whose text is emptied are dropped; pPr and every surviving run's rPr are
    untouched, so a paragraph trimmed to a sub-range keeps its formatting.
    """
    pos = 0
    for t in p.iter(_w('t')):
        text = t.text or ''
        lo = min(max(start - pos, 0), len(text))
        hi = len(text) if end is None else min(max(end - pos, 0), len(text))
        pos += len(text)
        t.text = text[lo:hi] if lo < hi else ''
    for r in list(p.findall(_w('r'))):
        ts = r.findall(_w('t'))
        if ts and not any(t.text for t in ts):
            p.remove(r)


def _make_list_paragraph(text: str, num_id: str, ilvl: str) -> etree._Element:
    p = _make_paragraph(text)
    ppr = etree.Element(_w('pPr'))
    numpr = etree.SubElement(ppr, _w('numPr'))
    etree.SubElement(numpr, _w('ilvl')).set(_w('val'), ilvl)
    etree.SubElement(numpr, _w('numId')).set(_w('val'), num_id)
    p.insert(0, ppr)
    return p


def split_parts(text: str) -> tuple[str, str]:
    """Deterministic sentence split used by split_paragraph (shared with tests)."""
    head, sep, tail = text.partition('. ')
    if not sep or not tail.strip():
        raise ValueError(f'no sentence boundary in {text!r}')
    return head + '.', tail


# ---------------------------------------------------------------------------
# Mutations — each mutates the parsed document root in place, or raises
# ProbeNotApplicable when the seed lacks the needed structure.
# ---------------------------------------------------------------------------


def _mut_insert_sentence(root: etree._Element) -> None:
    """Append a sentence INSIDE a mid-document clause — paragraph count unchanged."""
    plain = _plain_paragraphs(_body(root))
    if not plain:
        raise ProbeNotApplicable('insert_sentence', 'no text-bearing paragraph to extend')
    target = plain[len(plain) // 2]
    last = [t for t in target.iter(_w('t')) if (t.text or '').strip()][-1]
    last.text = f'{last.text} {INSERTED_SENTENCE}'
    last.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')


def _mut_delete_sentence(root: etree._Element) -> None:
    """Drop the trailing sentence of a multi-sentence clause — paragraph count unchanged.

    A section-labeled clause needs two '. ' boundaries (label + two sentences) for
    the trailing sentence to be removable without degenerating to a bare label.
    """
    for p in _plain_paragraphs(_body(root)):
        text = _para_text(p)
        if text.count('. ') < 2:
            continue
        head, _, _ = text.rpartition('. ')
        _trim_runs(p, 0, len(head) + 1)
        return
    raise ProbeNotApplicable('delete_sentence', 'no clause with a removable trailing sentence')


def _mut_split_paragraph(root: etree._Element) -> None:
    for p in _plain_paragraphs(_body(root)):
        text = _para_text(p)
        try:
            first, second = split_parts(text)
        except ValueError:
            continue
        # Both halves are deep copies of the source, so pPr and each run's rPr
        # survive; the separator space between the halves is dropped.
        head, tail = deepcopy(p), deepcopy(p)
        _trim_runs(head, 0, len(first))
        _trim_runs(tail, len(first) + 1, None)
        p.addprevious(head)
        p.addnext(tail)
        p.getparent().remove(p)
        return
    raise ProbeNotApplicable('split_paragraph', 'no paragraph with a sentence boundary')


def _mut_merge_paragraphs(root: etree._Element) -> None:
    body = _body(root)
    plain = _plain_paragraphs(body)
    top = _top_level_paragraphs(body)
    for a, b in pairwise(plain):
        if top.index(b) != top.index(a) + 1:
            continue  # not adjacent in the body
        # Keep a's pPr and move b's actual content children into a, so run
        # structure and formatting survive on both sides of the seam.
        if not _para_text(a).endswith(' ') and not _para_text(b).startswith(' '):
            a.append(_make_run(' '))
        for child in list(b):
            if child.tag != _w('pPr'):
                a.append(child)
        b.getparent().remove(b)
        return
    raise ProbeNotApplicable('merge_paragraphs', 'no two adjacent plain paragraphs')


def _mut_delete_table_row(root: etree._Element) -> None:
    tbl = _body(root).find(_w('tbl'))
    if tbl is None:
        raise ProbeNotApplicable('delete_table_row', 'document has no table')
    rows = tbl.findall(_w('tr'))
    if len(rows) < 2:
        raise ProbeNotApplicable('delete_table_row', 'table has fewer than 2 rows')
    tbl.remove(rows[0])


def _mut_add_list_item(root: etree._Element) -> None:
    items = _list_paragraphs(_body(root))
    if not items:
        raise ProbeNotApplicable('add_list_item', 'document has no numbered list')
    last = items[-1]
    num_id = last.find(f'{_w("pPr")}/{_w("numPr")}/{_w("numId")}').get(_w('val'))
    last.addnext(_make_list_paragraph(ADDED_LIST_ITEM, num_id=num_id, ilvl='0'))


def _mut_change_list_level(root: etree._Element) -> None:
    items = _list_paragraphs(_body(root))
    if not items:
        raise ProbeNotApplicable('change_list_level', 'document has no numbered list')
    target = items[1] if len(items) > 1 else items[0]
    numpr = target.find(f'{_w("pPr")}/{_w("numPr")}')
    ilvl = numpr.find(_w('ilvl'))
    if ilvl is None:
        ilvl = etree.Element(_w('ilvl'))
        numpr.insert(0, ilvl)
    ilvl.set(_w('val'), '0' if ilvl.get(_w('val')) == '1' else '1')


def _mut_move_clause(root: etree._Element) -> None:
    plain = _plain_paragraphs(_body(root))
    if len(plain) < 2:
        raise ProbeNotApplicable('move_clause', 'fewer than 2 text-bearing paragraphs')
    mover = plain[-1]
    mover.getparent().remove(mover)
    plain[0].addprevious(mover)


def _mut_format_only_bold(root: etree._Element) -> None:
    for p in _top_level_paragraphs(_body(root)):
        for r in p.findall(_w('r')):
            t = r.find(_w('t'))
            if t is None or not (t.text or '').strip():
                continue
            rpr = r.find(_w('rPr'))
            if rpr is None:
                rpr = etree.Element(_w('rPr'))
                r.insert(0, rpr)
            if rpr.find(_w('b')) is None:
                etree.SubElement(rpr, _w('b'))
            return
    raise ProbeNotApplicable('format_only_bold', 'no text-bearing run to embolden')


def _mut_insert_paragraph(root: etree._Element) -> None:
    plain = _plain_paragraphs(_body(root))
    if not plain:
        raise ProbeNotApplicable('insert_paragraph', 'no text-bearing paragraph to anchor on')
    plain[0].addnext(_make_paragraph(INSERTED_PARAGRAPH))


def _mut_delete_paragraph(root: etree._Element) -> None:
    plain = _plain_paragraphs(_body(root))
    if len(plain) < 2:
        raise ProbeNotApplicable('delete_paragraph', 'fewer than 2 text-bearing paragraphs')
    target = plain[1]
    target.getparent().remove(target)


MUTATIONS: dict[str, Callable[[etree._Element], None]] = {
    'insert_sentence': _mut_insert_sentence,
    'delete_sentence': _mut_delete_sentence,
    'insert_paragraph': _mut_insert_paragraph,
    'delete_paragraph': _mut_delete_paragraph,
    'split_paragraph': _mut_split_paragraph,
    'merge_paragraphs': _mut_merge_paragraphs,
    'delete_table_row': _mut_delete_table_row,
    'add_list_item': _mut_add_list_item,
    'change_list_level': _mut_change_list_level,
    'move_clause': _mut_move_clause,
    'format_only_bold': _mut_format_only_bold,
}


# ---------------------------------------------------------------------------
# Package plumbing
# ---------------------------------------------------------------------------


def _read_document_xml(docx_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        return zf.read(DOCUMENT_PART)


def replace_document_xml(docx_bytes: bytes, document_xml: bytes) -> bytes:
    """Rezip with only word/document.xml replaced — entry order and every other
    part's bytes preserved."""
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as src, zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            data = document_xml if info.filename == DOCUMENT_PART else src.read(info)
            entry = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = info.external_attr
            dst.writestr(entry, data)
    return out.getvalue()


def apply_mutation(docx_bytes: bytes, name: str) -> bytes:
    """Apply one named mutation to the seed's word/document.xml and rezip."""
    if name not in MUTATIONS:
        raise KeyError(f'unknown mutation {name!r}; known: {", ".join(MUTATIONS)}')
    root = etree.fromstring(_read_document_xml(docx_bytes))
    MUTATIONS[name](root)
    new_doc = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
    return replace_document_xml(docx_bytes, new_doc)


def extract_body_text(docx_bytes: bytes) -> list[str]:
    """Paragraph texts in document order — table-cell paragraphs INCLUDED (so
    delete_table_row shows a delta) — empties dropped."""
    root = etree.fromstring(_read_document_xml(docx_bytes))
    texts = (_para_text(p) for p in root.iter(_w('p')))
    return [t for t in texts if t.strip()]


def generate_probes(seed_docx: Path | None, out_dir: Path) -> list[ProbeRecord]:
    """Write out_dir/seed.docx plus one mutated DOCX per applicable probe."""
    seed_bytes = Path(seed_docx).read_bytes() if seed_docx is not None else make_default_seed()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'seed.docx').write_bytes(seed_bytes)

    records: list[ProbeRecord] = []
    for name in MUTATIONS:
        try:
            mutated = apply_mutation(seed_bytes, name)
        except ProbeNotApplicable as exc:
            records.append(ProbeRecord(name=name, path=None, applicable=False, reason=exc.reason))
            continue
        path = out_dir / f'{name}.docx'
        path.write_bytes(mutated)
        records.append(ProbeRecord(name=name, path=path, applicable=True))
    return records


# ---------------------------------------------------------------------------
# Built-in seed — a minimal 5-part package built from scratch (no template file).
# ---------------------------------------------------------------------------

_CONTENT_TYPES_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
</Types>
"""

_ROOT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""

_DOCUMENT_RELS_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>
</Relationships>
"""

_NUMBERING_XML = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:numbering xmlns:w="{W_NS}">
  <w:abstractNum w:abstractNumId="0">
    <w:multiLevelType w:val="multilevel"/>
    <w:lvl w:ilvl="0">
      <w:start w:val="1"/>
      <w:numFmt w:val="decimal"/>
      <w:lvlText w:val="%1."/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr>
    </w:lvl>
    <w:lvl w:ilvl="1">
      <w:start w:val="1"/>
      <w:numFmt w:val="lowerLetter"/>
      <w:lvlText w:val="%2."/>
      <w:lvlJc w:val="left"/>
      <w:pPr><w:ind w:left="1440" w:hanging="360"/></w:pPr>
    </w:lvl>
  </w:abstractNum>
  <w:num w:numId="1">
    <w:abstractNumId w:val="0"/>
  </w:num>
</w:numbering>
"""


def _seed_document_xml() -> bytes:
    nsmap = {'w': W_NS}
    root = etree.Element(_w('document'), nsmap=nsmap)
    body = etree.SubElement(root, _w('body'))
    for clause in SEED_CLAUSES:
        body.append(_make_paragraph(clause))
    for item in SEED_LIST_ITEMS:
        body.append(_make_list_paragraph(item, num_id='1', ilvl='0'))

    tbl = etree.SubElement(body, _w('tbl'))
    tblpr = etree.SubElement(tbl, _w('tblPr'))
    tblw = etree.SubElement(tblpr, _w('tblW'))
    tblw.set(_w('w'), '0')
    tblw.set(_w('type'), 'auto')
    borders = etree.SubElement(tblpr, _w('tblBorders'))
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        b = etree.SubElement(borders, _w(edge))
        b.set(_w('val'), 'single')
        b.set(_w('sz'), '4')
        b.set(_w('space'), '0')
        b.set(_w('color'), 'auto')
    grid = etree.SubElement(tbl, _w('tblGrid'))
    for _ in range(2):
        etree.SubElement(grid, _w('gridCol')).set(_w('w'), '4675')
    for row in SEED_TABLE_ROWS:
        tr = etree.SubElement(tbl, _w('tr'))
        for cell_text in row:
            tc = etree.SubElement(tr, _w('tc'))
            tcpr = etree.SubElement(tc, _w('tcPr'))
            tcw = etree.SubElement(tcpr, _w('tcW'))
            tcw.set(_w('w'), '4675')
            tcw.set(_w('type'), 'dxa')
            tc.append(_make_paragraph(cell_text))

    # Word requires a paragraph after a body-final table; empty, so it never
    # shows up in extract_body_text.
    etree.SubElement(body, _w('p'))

    sectpr = etree.SubElement(body, _w('sectPr'))
    pgsz = etree.SubElement(sectpr, _w('pgSz'))
    pgsz.set(_w('w'), '12240')
    pgsz.set(_w('h'), '15840')
    pgmar = etree.SubElement(sectpr, _w('pgMar'))
    for k, v in (
        ('top', '1440'),
        ('right', '1440'),
        ('bottom', '1440'),
        ('left', '1440'),
        ('header', '720'),
        ('footer', '720'),
        ('gutter', '0'),
    ):
        pgmar.set(_w(k), v)

    return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)


def make_default_seed() -> bytes:
    """Build the minimal valid 5-part seed package from scratch."""
    parts: tuple[tuple[str, bytes], ...] = (
        ('[Content_Types].xml', _CONTENT_TYPES_XML.encode()),
        ('_rels/.rels', _ROOT_RELS_XML.encode()),
        ('word/_rels/document.xml.rels', _DOCUMENT_RELS_XML.encode()),
        (DOCUMENT_PART, _seed_document_xml()),
        ('word/numbering.xml', _NUMBERING_XML.encode()),
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as zf:
        for name, data in parts:
            entry = zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(entry, data)
    return out.getvalue()
