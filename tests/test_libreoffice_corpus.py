"""The LibreOffice corpus: ``corpus/libreoffice/<state>/pdf/<word stem>.pdf`` and ``word_map.csv``.

The bench's oracles were LibreOffice renders of Word files. Each is filed under the stem of the
Word docx it rendered, found by the sha256 of that docx in the built Word corpus, and mapped to
the Word PDF of the same docx. The miniature tree is the one ``test_word_corpus`` builds.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from test_word_corpus import SD, WB, _docx, _pdf, make_tree

from neurotic_docx_bench import hub, libreoffice_corpus, word_corpus

WORD_SETS = ['word_based', 'word_based_randomized', 'word_redlines_superdoc', 'word_based_accepted_word']


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    root = make_tree(tmp_path / 'repo')
    lo = 'libreoffice'
    # the LibreOffice renders the bench scored against, beside the docx they rendered
    _pdf(root / WB / 'pdf_redlines_word' / 'x_y_redline.pdf', 'lo x y', producer=lo)
    _pdf(root / WB / 'pdf_redlines_word' / 'y_z_word_redline.pdf', 'lo y z', producer=lo)
    _pdf(root / WB / 'pdf_redlines_randomized' / 'pdf' / 'file_1_file_2_redline.pdf', 'lo 1 2', producer=lo)
    _pdf(root / SD / 'pdf_redlines_word' / 'p_q_redline.pdf', 'lo p q', producer=lo)
    _pdf(root / WB / 'pdf_source' / 'x.pdf', 'lo x', producer=lo)
    _pdf(root / WB / 'pdf_source' / 'gone.pdf', 'lo of a docx no longer there', producer=lo)
    _pdf(root / WB / 'pdf_accepted_word' / 'x_y_word_redline_accepted.pdf', 'lo x y acc', producer=lo)
    # the same docx under a second name, rendered again (other bytes: a fresh timestamp)
    (root / WB / 'docx_source' / 'x_again.docx').write_bytes((root / WB / 'docx_source' / 'x.docx').read_bytes())
    _pdf(root / WB / 'pdf_source' / 'x_again.pdf', 'lo x rendered again', producer=lo)
    # a Word render filed among them is not a LibreOffice oracle
    _pdf(root / WB / 'pdf_source' / 'y.pdf', 'a Word pdf of y')
    word_corpus.build(root, root / 'corpus' / 'word', only=WORD_SETS)
    # a docx the Word corpus does not hold (it came after the build)
    _docx(root / WB / 'docx_source' / 'stray.docx', 'stray')
    _pdf(root / WB / 'pdf_source' / 'stray.pdf', 'lo stray', producer=lo)
    return root


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='') as fh:
        return list(csv.DictReader(fh))


def test_plan_files_each_render_under_the_stem_of_its_word_docx(tree: Path) -> None:
    plan_ = libreoffice_corpus.plan(tree, tree / 'corpus' / 'word')
    words = {
        r['sha256']: r for r in _rows(tree / 'corpus/word/comparisons.csv') + _rows(tree / 'corpus/word/documents.csv')
    }
    by_origin = {e.origin: e for e in plan_.entries}
    xy = by_origin[f'{WB}/pdf_redlines_word/x_y_redline.pdf']
    word_xy = words[hub.sha256_file(tree / WB / 'docx_redlines_word' / 'x_y_redline.docx')]
    assert xy.dest == f'{word_xy["state"]}/pdf/{word_xy["key"]}.pdf'
    assert (xy.word_id, xy.kind, xy.word_pdf) == (word_xy['id'], 'comparison', word_xy['pdf'])
    assert xy.docx_origin == f'{WB}/docx_redlines_word/x_y_redline.docx'
    assert xy.set == 'word_based_redlines' and 'LibreOffice' in xy.producer
    x = by_origin[f'{WB}/pdf_source/x.pdf']
    assert x.kind == 'document' and x.dest.endswith(
        f'/pdf/{words[hub.sha256_file(tree / WB / "docx_source" / "x.docx")]["stem"]}.pdf'
    )
    acc = by_origin[f'{WB}/pdf_accepted_word/x_y_word_redline_accepted.pdf']
    assert acc.word_pdf.endswith("_x_y_word_redline_accepted.pdf")  # the Word render of the same docx
    assert by_origin[f'{WB}/pdf_redlines_randomized/pdf/file_1_file_2_redline.pdf'].kind == 'comparison'
    assert by_origin[f'{SD}/pdf_redlines_word/p_q_redline.pdf'].set == 'word_redlines_superdoc_redlines'
    sources = plan_.sets['word_based_sources']
    assert sources.unmatched == {
        f'{WB}/pdf_source/gone.pdf': f'no docx {WB}/docx_source/gone.docx',
        f'{WB}/pdf_source/stray.pdf': f'{WB}/docx_source/stray.docx is not in the Word corpus',
    }
    assert set(sources.refused) == {f'{WB}/pdf_source/y.pdf'}
    assert sources.redundant == [f'{WB}/pdf_source/x_again.pdf']


def test_build_copies_writes_the_map_and_a_manifest(tree: Path) -> None:
    dest = tree / 'corpus' / 'libreoffice'
    libreoffice_corpus.build(tree, dest, word=tree / 'corpus' / 'word')
    rows = _rows(dest / 'word_map.csv')
    assert len(rows) == 6
    xy = next(r for r in rows if r['origin'].endswith('pdf_redlines_word/x_y_redline.pdf'))
    assert (dest / xy['libreoffice_pdf']).read_bytes() == (tree / xy['origin']).read_bytes()
    assert (tree / 'corpus' / 'word' / xy['word_pdf']).is_file()
    assert (tree / 'corpus' / 'word' / xy['word_docx']).is_file()
    assert xy['word_pdf_producer'].startswith('macOS') and xy['key'] == Path(xy['word_docx']).stem
    assert hub.verify_manifest(dest).ok
    prov = json.loads((dest / 'PROVENANCE.json').read_text())
    assert prov['sets']['word_based_sources']['n'] == 1 and len(prov['sets']['word_based_sources']['unmatched']) == 2
    # idempotent; the origins are left alone
    libreoffice_corpus.build(tree, dest, word=tree / 'corpus' / 'word')
    assert (tree / WB / 'pdf_redlines_word' / 'x_y_redline.pdf').is_file()


def test_build_refuses_without_a_word_corpus(tmp_path: Path) -> None:
    with pytest.raises(libreoffice_corpus.LibreofficeCorpusError, match='no Word corpus'):
        libreoffice_corpus.build(tmp_path, tmp_path / 'lo', word=tmp_path / 'word')
