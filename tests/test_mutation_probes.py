"""Mutation-probe generator: every probe on the built-in seed must produce a valid
package whose body text differs from the seed in exactly the intended way, with
every other zip part byte-identical. Self-contained — never touches the corpus."""

from __future__ import annotations

import io
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from lxml import etree

from neurotic_docx_bench.mutation_probes import (
    ADDED_LIST_ITEM,
    DOCUMENT_PART,
    INSERTED_SENTENCE,
    MUTATIONS,
    SEED_CLAUSES,
    SEED_LIST_ITEMS,
    SEED_TABLE_ROWS,
    W_NS,
    ProbeNotApplicable,
    apply_mutation,
    extract_body_text,
    generate_probes,
    make_default_seed,
    replace_document_xml,
    split_parts,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
W = f'{{{W_NS}}}'

SEED_TABLE_CELLS = [cell for row in SEED_TABLE_ROWS for cell in row]
SEED_TEXTS = list(SEED_CLAUSES) + list(SEED_LIST_ITEMS) + SEED_TABLE_CELLS


@pytest.fixture(scope='module')
def seed() -> bytes:
    return make_default_seed()


def _document_root(docx_bytes: bytes) -> etree._Element:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
        return etree.fromstring(zf.read(DOCUMENT_PART))


def _strip_element(docx_bytes: bytes, tag: str) -> bytes:
    """Return a copy of the package with every body-level <w:{tag}> removed."""
    root = _document_root(docx_bytes)
    body = root.find(f'{W}body')
    for el in body.findall(f'{W}{tag}'):
        body.remove(el)
    return replace_document_xml(docx_bytes, etree.tostring(root, xml_declaration=True, encoding='UTF-8'))


def test_seed_text_matches_constants(seed):
    assert extract_body_text(seed) == SEED_TEXTS


def test_seed_is_valid_package(seed):
    with zipfile.ZipFile(io.BytesIO(seed)) as zf:
        assert zf.testzip() is None
        names = zf.namelist()
        assert names == [
            '[Content_Types].xml',
            '_rels/.rels',
            'word/_rels/document.xml.rels',
            DOCUMENT_PART,
            'word/numbering.xml',
        ]
        for name in names:
            etree.fromstring(zf.read(name))


@pytest.mark.parametrize('name', list(MUTATIONS))
def test_mutation_yields_valid_zip(seed, name):
    mutated = apply_mutation(seed, name)
    with zipfile.ZipFile(io.BytesIO(mutated)) as zf:
        assert zf.testzip() is None
        etree.fromstring(zf.read(DOCUMENT_PART))


@pytest.mark.parametrize('name', list(MUTATIONS))
def test_only_document_xml_changes(seed, name):
    mutated = apply_mutation(seed, name)
    with zipfile.ZipFile(io.BytesIO(seed)) as zs, zipfile.ZipFile(io.BytesIO(mutated)) as zm:
        assert zm.namelist() == zs.namelist()  # entry order preserved
        for part in zs.namelist():
            if part == DOCUMENT_PART:
                assert zm.read(part) != zs.read(part)
            else:
                assert zm.read(part) == zs.read(part)


def test_unknown_mutation_rejected(seed):
    with pytest.raises(KeyError):
        apply_mutation(seed, 'reverse_polarity')


# ---------------------------------------------------------------------------
# Per-probe text/XML deltas
# ---------------------------------------------------------------------------


def test_insert_sentence_adds_one_paragraph(seed):
    texts = extract_body_text(apply_mutation(seed, 'insert_sentence'))
    expected = SEED_TEXTS.copy()
    expected.insert(1, INSERTED_SENTENCE)
    assert texts == expected


def test_delete_sentence_removes_one_paragraph(seed):
    texts = extract_body_text(apply_mutation(seed, 'delete_sentence'))
    expected = SEED_TEXTS.copy()
    expected.remove(SEED_CLAUSES[1])
    assert texts == expected


def test_split_paragraph_turns_one_into_two(seed):
    texts = extract_body_text(apply_mutation(seed, 'split_paragraph'))
    first, second = split_parts(SEED_CLAUSES[0])
    expected = [first, second, *SEED_TEXTS[1:]]
    assert texts == expected
    assert f'{first} {second}' == SEED_CLAUSES[0]


def test_merge_paragraphs_turns_two_into_one(seed):
    texts = extract_body_text(apply_mutation(seed, 'merge_paragraphs'))
    expected = [f'{SEED_CLAUSES[0]} {SEED_CLAUSES[1]}', *SEED_TEXTS[2:]]
    assert texts == expected


def test_delete_table_row_removes_first_row_cells(seed):
    texts = extract_body_text(apply_mutation(seed, 'delete_table_row'))
    expected = list(SEED_CLAUSES) + list(SEED_LIST_ITEMS) + list(SEED_TABLE_ROWS[1])
    assert texts == expected


def test_add_list_item_appends_after_last_item(seed):
    mutated = apply_mutation(seed, 'add_list_item')
    texts = extract_body_text(mutated)
    expected = SEED_TEXTS.copy()
    expected.insert(len(SEED_CLAUSES) + len(SEED_LIST_ITEMS), ADDED_LIST_ITEM)
    assert texts == expected
    # the new item is a real list paragraph on the same numId
    root = _document_root(mutated)
    new_p = next(p for p in root.iter(f'{W}p') if ADDED_LIST_ITEM in ''.join(p.itertext()))
    num_id = new_p.find(f'{W}pPr/{W}numPr/{W}numId')
    assert num_id is not None and num_id.get(f'{W}val') == '1'


def test_change_list_level_changes_only_ilvl(seed):
    mutated = apply_mutation(seed, 'change_list_level')
    assert extract_body_text(mutated) == SEED_TEXTS  # zero text change

    def ilvls(docx: bytes) -> list[str]:
        root = _document_root(docx)
        return [el.get(f'{W}val') for el in root.iter(f'{W}numPr') for el in el.findall(f'{W}ilvl')]

    assert ilvls(seed) == ['0', '0', '0']
    assert ilvls(mutated) == ['0', '1', '0']  # second list item promoted


def test_move_clause_reorders_but_preserves_multiset(seed):
    texts = extract_body_text(apply_mutation(seed, 'move_clause'))
    expected = [SEED_CLAUSES[-1], *SEED_CLAUSES[:-1], *SEED_LIST_ITEMS, *SEED_TABLE_CELLS]
    assert texts == expected
    assert texts != SEED_TEXTS
    assert sorted(texts) == sorted(SEED_TEXTS)


def test_format_only_bold_changes_no_text(seed):
    mutated = apply_mutation(seed, 'format_only_bold')
    assert extract_body_text(mutated) == SEED_TEXTS  # zero text change
    assert len(list(_document_root(seed).iter(f'{W}b'))) == 0
    root = _document_root(mutated)
    bolds = list(root.iter(f'{W}b'))
    assert len(bolds) == 1
    # the w:b sits in the rPr of the first clause's run
    run = bolds[0].getparent().getparent()
    assert run.tag == f'{W}r'
    assert ''.join(run.itertext()) == SEED_CLAUSES[0]


# ---------------------------------------------------------------------------
# Applicability
# ---------------------------------------------------------------------------


def test_delete_table_row_not_applicable_without_table(seed):
    tableless = _strip_element(seed, 'tbl')
    with pytest.raises(ProbeNotApplicable) as exc_info:
        apply_mutation(tableless, 'delete_table_row')
    assert exc_info.value.name == 'delete_table_row'
    assert exc_info.value.reason


@pytest.mark.parametrize('name', ['add_list_item', 'change_list_level'])
def test_list_probes_not_applicable_without_list(seed, name):
    root = _document_root(seed)
    for p in list(root.iter(f'{W}p')):
        if p.find(f'{W}pPr/{W}numPr') is not None:
            p.getparent().remove(p)
    listless = replace_document_xml(seed, etree.tostring(root, xml_declaration=True, encoding='UTF-8'))
    with pytest.raises(ProbeNotApplicable):
        apply_mutation(listless, name)


def test_generate_probes_records_inapplicable(seed, tmp_path):
    seed_path = tmp_path / 'tableless.docx'
    seed_path.write_bytes(_strip_element(seed, 'tbl'))
    records = generate_probes(seed_path, tmp_path / 'out')
    by_name = {r.name: r for r in records}
    rec = by_name['delete_table_row']
    assert not rec.applicable
    assert rec.path is None
    assert rec.reason


# ---------------------------------------------------------------------------
# generate_probes + CLI
# ---------------------------------------------------------------------------


def test_generate_probes_writes_files_and_records(seed, tmp_path):
    seed_path = tmp_path / 'myseed.docx'
    seed_path.write_bytes(seed)
    out = tmp_path / 'probes'
    records = generate_probes(seed_path, out)

    assert [r.name for r in records] == list(MUTATIONS)
    assert (out / 'seed.docx').read_bytes() == seed
    for rec in records:
        assert rec.applicable, f'{rec.name} unexpectedly inapplicable: {rec.reason}'
        assert rec.path == out / f'{rec.name}.docx'
        assert rec.path.is_file()


def test_generate_probes_default_seed(tmp_path):
    records = generate_probes(None, tmp_path)
    assert (tmp_path / 'seed.docx').read_bytes() == make_default_seed()
    assert all(r.applicable for r in records)


def test_cli_end_to_end(tmp_path):
    out = tmp_path / 'probes'
    result = subprocess.run(
        [sys.executable, 'scripts/mutation_probes_gen.py', '--out', str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    manifest = (out / 'probes_manifest.csv').read_text().splitlines()
    assert manifest[0] == (
        'pair_stem,base,next,origin,docx_source_base,docx_source_next,redline_docx,'
        'redline_docx_word,accepted_docx,pdf_redline,pdf_accepted,missing'
    )
    rows = [line.split(',') for line in manifest[1:]]
    assert [r[0] for r in rows] == list(MUTATIONS)
    for row in rows:
        pair_stem, base, nxt, origin, src_base, src_next, *rest = row
        assert base == 'seed'  # stems in base/next
        assert nxt == pair_stem
        assert origin == 'mutation_probe'
        assert src_base == 'seed.docx'  # filenames in docx_source_*
        assert src_next == f'{pair_stem}.docx'
        assert rest == [''] * 6
        assert (out / src_next).is_file()
    assert (out / 'seed.docx').is_file()
