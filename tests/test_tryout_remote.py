"""Spec for ``tryout_remote`` (``bench try remote``): random documents from the superdoc
docx-corpus, scored against our Word SOT when we hold it, else against the fallback SOT
(docxodus for redlines, soffice for DOCX->PDF, pdftoppm for PDF->PNG)."""

from __future__ import annotations

import csv
import shutil
from pathlib import Path

import polars as pl
import pymupdf
import pytest

from neurotic_docx_bench import tryout_remote as tr


def _pdf(path: Path, text: str = 'hello', pages: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), f'{text} {i}', fontsize=14)
        page.draw_rect(pymupdf.Rect(72, 200, 300, 260), color=(1, 0, 0), fill=(0, 0, 1))
    doc.save(path)
    return path


def _index(n: int = 20) -> pl.DataFrame:
    return pl.DataFrame({
        'id': [f'{i:064x}' for i in range(n)],
        'filename': ['f'] * n,
        'type': ['legal' if i % 2 else 'forms' for i in range(n)],
        'topic': ['general'] * n,
        'language': ['en' if i < n // 2 else 'fr' for i in range(n)],
        'word_count': [100] * n,
        'confidence': [0.9] * n,
        'url': [f'https://docxcorp.us/documents/{i:064x}.docx' for i in range(n)],
    })


def _doc(tmp: Path, name: str, body: bytes) -> tr.Doc:
    path = tmp / 'docs' / name / f'{name}.docx'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return tr.Doc(id=name, url=f'u/{name}', path=path, sha256=tr.sha256_file(path))


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _sot_corpus(root: Path, a: tr.Doc, b: tr.Doc) -> Path:
    """A corpus/word with Word PDFs of a and b and Word's compare of a -> b."""
    word = root / 'corpus' / 'word'
    _pdf(word / 'clean' / 'pdf' / 'a.pdf', 'word a')
    _write_csv(
        word / 'documents.csv',
        [
            {
                'id': a.sha256[:10],
                'stem': 'a',
                'state': 'clean',
                'docx': 'clean/docx/a.docx',
                'pdf': 'clean/pdf/a.pdf',
                'pdf_prior': '',
                'sets': 's',
                'names': a.id,
                'sha256': a.sha256,
                'producer': 'Word',
            },
            {
                'id': b.sha256[:10],
                'stem': 'b',
                'state': 'clean',
                'docx': 'clean/docx/b.docx',
                'pdf': '',
                'pdf_prior': '',
                'sets': 's',
                'names': b.id,
                'sha256': b.sha256,
                'producer': '',
            },
        ],
    )
    red = word / 'tracking_without_comments'
    (red / 'docx').mkdir(parents=True)
    (red / 'docx' / 'ab.docx').write_bytes(b'word redline')
    _pdf(red / 'pdf' / 'ab.pdf', 'word redline')
    _write_csv(
        word / 'comparisons.csv',
        [
            {
                'id': 'r1',
                'key': 'ab',
                'base_id': a.sha256[:10],
                'next_id': b.sha256[:10],
                'state': 'tracking_without_comments',
                'docx': 'tracking_without_comments/docx/ab.docx',
                'pdf': 'tracking_without_comments/pdf/ab.pdf',
                'pdf_prior': '',
                'sets': 's',
                'names': f'{a.id}__vs__{b.id}',
                'sha256': 'x',
                'producer': 'Word',
            }
        ],
    )
    return word


def _copy_tool(name: str, source: Path) -> tr.Tool:
    """A tool whose every output is a copy of ``source`` (a PDF or a folder of PNGs)."""

    def runner(inputs, out, dpi):
        out.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            for p in source.glob('*.png'):
                shutil.copy(p, out / p.name)
            return out
        return Path(shutil.copy(source, out / source.name))

    return tr.Tool(name=name, version=f'{name} 1', runners={t: runner for t in tr.TASKS})


def _pymupdf_pages(pdf: Path, out: Path, dpi: int) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(pdf) as d:
        for i, page in enumerate(d, 1):
            page.get_pixmap(dpi=dpi, alpha=False).save(out / f'page-{i:03d}.png')
    return out


# --- picking -------------------------------------------------------------------------


def test_pick_rows_is_repeatable_by_seed_and_filters_language_and_type():
    df = _index()
    a = tr.pick_rows(df, 2, seed=7, language='en')
    assert a == tr.pick_rows(df, 2, seed=7, language='en')
    assert len({r['id'] for r in a}) == 2 and all(r['language'] == 'en' for r in a)
    assert all(r['type'] == 'legal' for r in tr.pick_rows(df, 3, seed=1, doc_type='legal'))
    with pytest.raises(tr.RemoteError, match='3 rows match'):
        tr.pick_rows(df.head(3), 4, seed=1)


def test_with_sot_picks_documents_and_pairs_we_hold_word_sot_for(tmp_path):
    df = _index()
    ids = df['id'].to_list()
    word = tmp_path / 'word'
    _write_csv(
        word / 'documents.csv',
        [
            {'id': 'x', 'state': 'clean', 'docx': '', 'pdf': 'p.pdf', 'names': f'alias;{ids[3]}', 'sha256': 's3'},
            {'id': 'y', 'state': 'clean', 'docx': '', 'pdf': 'p.pdf', 'names': ids[5], 'sha256': 's5'},
            {'id': 'z', 'state': 'clean', 'docx': '', 'pdf': 'p.pdf', 'names': 'not_a_corpus_doc', 'sha256': 's9'},
        ],
    )
    _write_csv(
        word / 'comparisons.csv',
        [
            {
                'id': 'r',
                'base_id': 'x',
                'next_id': 'y',
                'state': 'tracking_without_comments',
                'docx': 'r.docx',
                'pdf': '',
                'names': f'{ids[3]}__vs__{ids[5]}',
                'sha256': 'r',
            }
        ],
    )
    (word / 'p.pdf').write_bytes(b'%PDF')
    (word / 'r.docx').write_bytes(b'PK')
    sot = tr.load_sot(word)
    assert sot.corpus_ids() == {ids[3], ids[5]}
    assert sot.corpus_pairs() == [(ids[3], ids[5])]
    one = tr.pick_rows(df, 1, seed=4, sot=sot)
    assert one[0]['id'] in {ids[3], ids[5]}
    two = tr.pick_rows(df, 2, seed=4, sot=sot)
    assert [r['id'] for r in two] == [ids[3], ids[5]]  # a pair keeps its base -> next order


def test_download_doc_writes_the_bytes_under_their_own_folder(tmp_path):
    row = _index().row(0, named=True)
    doc = tr.download_doc(row, tmp_path, fetch=lambda url: b'docx bytes')
    assert doc.path.read_bytes() == b'docx bytes' and doc.path.parent.parent == tmp_path
    assert doc.id == row['id'] and doc.url == row['url'] and doc.sha256 == tr.sha256_file(doc.path)


# --- the SOT index ---------------------------------------------------------------------


def test_the_sot_index_finds_word_pdfs_and_word_redlines_by_content(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    sot = tr.load_sot(word)
    assert sot.word_pdf(a.sha256) == word / 'clean' / 'pdf' / 'a.pdf'
    assert sot.word_pdf(b.sha256) is None  # no Word PDF recorded
    docx, pdf = sot.word_redline(a.sha256, b.sha256)
    assert docx == word / 'tracking_without_comments' / 'docx' / 'ab.docx'
    assert pdf == word / 'tracking_without_comments' / 'pdf' / 'ab.pdf'
    assert sot.word_redline(b.sha256, a.sha256) is None  # direction matters
    assert tr.load_sot(tmp_path / 'nowhere').word_pdf(a.sha256) is None


def test_a_word_pdf_listed_but_absent_on_disk_is_not_a_sot(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    (word / 'clean' / 'pdf' / 'a.pdf').unlink()
    assert tr.load_sot(word).word_pdf(a.sha256) is None


# --- tools ---------------------------------------------------------------------------


def test_known_tools_run_only_the_tasks_they_can():
    assert tr.KNOWN_TASKS['jubarte'] == ('redline', 'convert', 'png')
    assert tr.KNOWN_TASKS['docxodus'] == ('redline',)
    assert tr.KNOWN_TASKS['soffice'] == ('convert',)
    assert tr.KNOWN_TASKS['pdftoppm'] == ('png',)
    tool = tr.Tool(name='soffice', version='v', runners={'convert': lambda *a: None})
    assert tr.select_tasks(tool, None) == ['convert']
    with pytest.raises(tr.RemoteError, match='soffice cannot run redline'):
        tr.select_tasks(tool, ['redline'])


@pytest.mark.parametrize(
    ('template', 'tasks'),
    [
        ('mytool {base} {next} -o {out}', ['redline']),
        ('mytool {input} {out}', ['convert']),
        ('mytool {pdf} --dpi {dpi} {outdir}', ['png']),
    ],
)
def test_a_template_runs_the_task_its_placeholders_name(template, tasks):
    assert tr.select_tasks(tr.template_tool(template), None) == tasks


def test_a_name_that_is_neither_known_nor_a_template_is_refused(tmp_path):
    with pytest.raises(tr.RemoteError, match=r'known tools: .*jubarte'):
        tr.make_tool('nosuchtool', root=tmp_path)
    with pytest.raises(tr.RemoteError, match='for jubarte only'):
        tr.make_tool('soffice', version='1.0', root=tmp_path)


def test_a_template_tool_writes_through_a_shell_command(tmp_path):
    src = _pdf(tmp_path / 'in.pdf')
    tool = tr.template_tool('cp {input} {out}')
    out = tool.runners['convert']({'input': src}, tmp_path / 'o', 144)
    assert out.suffix == '.pdf' and out.read_bytes() == src.read_bytes()


# --- running ---------------------------------------------------------------------------


def _fallbacks(tmp_path: Path, pdf: Path, redline_pdf: Path) -> dict[str, tr.Tool]:
    return {
        'convert': _copy_tool('soffice', pdf),
        'redline': _copy_tool('docxodus', redline_pdf),
        'png': tr.Tool(
            name='pdftoppm',
            version='pdftoppm 1',
            runners={'png': lambda inputs, out, dpi: _pymupdf_pages(inputs['pdf'], out, dpi)},
        ),
    }


def _render_pdf_as_is(docx: Path, work: Path) -> Path:
    """Test renderer: the 'docx' fixtures here are PDFs already."""
    return docx


def test_convert_scores_against_words_pdf_when_we_have_it(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    tool = _copy_tool('cand', word / 'clean' / 'pdf' / 'a.pdf')
    fb = _fallbacks(tmp_path, _pdf(tmp_path / 'lo.pdf', 'other'), _pdf(tmp_path / 'dx.pdf'))
    rows = tr.run(tool, [a, b], tr.load_sot(word), ['convert'], fallback=fb, render_docx=_render_pdf_as_is, dpi=72)
    (row,) = rows
    assert row['ok'] and row['sot']['source'] == 'word' and row['scores']['overall'] == pytest.approx(100.0)
    assert row['tool_version'] == 'cand 1' and row['inputs'][0]['id'] == 'a'


def test_convert_without_a_word_pdf_falls_back_to_soffice(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    lo = _pdf(tmp_path / 'lo.pdf', 'soffice')
    fb = _fallbacks(tmp_path, lo, _pdf(tmp_path / 'dx.pdf'))
    (row,) = tr.run(
        _copy_tool('cand', lo),
        [a, b],
        tr.load_sot(tmp_path / 'none'),
        ['convert'],
        fallback=fb,
        render_docx=_render_pdf_as_is,
        dpi=72,
    )
    assert row['ok'] and row['sot'] == {'source': 'soffice', 'version': 'soffice 1', 'renderer': None}
    assert row['scores']['overall'] == pytest.approx(100.0)


def test_the_fallback_sot_is_not_scored_against_itself(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    lo = _pdf(tmp_path / 'lo.pdf')
    fb = _fallbacks(tmp_path, lo, lo)
    (row,) = tr.run(
        _copy_tool('soffice', lo),
        [a, b],
        tr.load_sot(tmp_path / 'none'),
        ['convert'],
        fallback=fb,
        render_docx=_render_pdf_as_is,
        dpi=72,
    )
    assert not row['ok'] and "is this task's SOT" in row['skipped']


def test_redline_without_words_compare_uses_docxodus_rendered_like_the_candidate(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    dx = _pdf(tmp_path / 'dx.pdf', 'docxodus redline')
    fb = _fallbacks(tmp_path, _pdf(tmp_path / 'lo.pdf'), dx)
    rendered: list[Path] = []

    def render(docx: Path, work: Path) -> Path:
        rendered.append(docx)
        return docx

    (row,) = tr.run(
        _copy_tool('cand', dx),
        [a, b],
        tr.load_sot(tmp_path / 'none'),
        ['redline'],
        fallback=fb,
        render_docx=render,
        renderer='soffice',
        dpi=72,
    )
    assert row['ok'] and row['sot']['source'] == 'docxodus' and row['sot']['renderer'] == 'soffice'
    assert row['scores']['overall'] == pytest.approx(100.0)
    assert len(rendered) == 2  # the SOT redline and the candidate, through the same renderer


def test_redline_with_words_compare_reuses_the_word_pdf_under_the_word_renderer(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    word_pdf = word / 'tracking_without_comments' / 'pdf' / 'ab.pdf'
    fb = _fallbacks(tmp_path, _pdf(tmp_path / 'lo.pdf'), _pdf(tmp_path / 'dx.pdf', 'docxodus'))
    rendered: list[Path] = []

    def render(docx: Path, work: Path) -> Path:
        rendered.append(docx)
        return docx

    (row,) = tr.run(
        _copy_tool('cand', word_pdf),
        [a, b],
        tr.load_sot(word),
        ['redline'],
        fallback=fb,
        render_docx=render,
        renderer='word',
        dpi=72,
    )
    assert row['ok'] and row['sot']['source'] == 'word' and row['scores']['overall'] == pytest.approx(100.0)
    assert len(rendered) == 1  # only the candidate; Word's own render of its compare is the SOT


def test_redline_with_words_compare_under_soffice_reads_the_libreoffice_render(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    lo_pdf = _pdf(tmp_path / 'corpus' / 'libreoffice' / 'tracking_without_comments' / 'pdf' / 'ab.pdf', 'lo')
    _write_csv(
        tmp_path / 'corpus' / 'libreoffice' / 'word_map.csv',
        [{'libreoffice_pdf': 'tracking_without_comments/pdf/ab.pdf', 'producer': 'LibreOffice 26.2.4.2 (AARCH64)'}],
    )
    fb = _fallbacks(tmp_path, _pdf(tmp_path / 'lo.pdf'), _pdf(tmp_path / 'dx.pdf'))
    (row,) = tr.run(
        _copy_tool('cand', lo_pdf),
        [a, b],
        tr.load_sot(word),
        ['redline'],
        fallback=fb,
        render_docx=_render_pdf_as_is,
        renderer='soffice',
        renderer_version='LibreOffice 26.2.4.2 abc',
        dpi=72,
    )
    assert row['ok'] and row['sot']['source'] == 'word' and row['scores']['overall'] == pytest.approx(100.0)
    assert row['sot']['files']['pdf'].endswith('libreoffice/tracking_without_comments/pdf/ab.pdf')


def test_a_libreoffice_render_from_another_version_is_rendered_again(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    _pdf(tmp_path / 'corpus' / 'libreoffice' / 'tracking_without_comments' / 'pdf' / 'ab.pdf', 'lo')
    _write_csv(
        tmp_path / 'corpus' / 'libreoffice' / 'word_map.csv',
        [{'libreoffice_pdf': 'tracking_without_comments/pdf/ab.pdf', 'producer': 'LibreOffice 26.2.4.2 (AARCH64)'}],
    )
    fb = _fallbacks(tmp_path, _pdf(tmp_path / 'lo.pdf'), _pdf(tmp_path / 'dx.pdf'))
    rendered: list[Path] = []

    def render(docx: Path, work: Path) -> Path:
        rendered.append(docx)
        return word / 'tracking_without_comments' / 'pdf' / 'ab.pdf'

    (row,) = tr.run(
        _copy_tool('cand', _pdf(tmp_path / 'c.pdf')),
        [a, b],
        tr.load_sot(word),
        ['redline'],
        fallback=fb,
        render_docx=render,
        renderer='soffice',
        renderer_version='LibreOffice 26.8.0.3 bce0998',
        dpi=72,
    )
    assert row['ok'] and row['sot']['source'] == 'word'
    assert [p.name for p in rendered] == ['ab.docx', 'c.pdf']  # Word's compare re-rendered, then the tool's


def test_png_rasterizes_the_sot_pdf_with_pdftoppm_and_scores_pages(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    fb = _fallbacks(tmp_path, _pdf(tmp_path / 'lo.pdf'), _pdf(tmp_path / 'dx.pdf'))
    cand = tr.Tool(
        name='pymupdf',
        version='mu 1',
        runners={'png': lambda inputs, out, dpi: _pymupdf_pages(inputs['pdf'], out, dpi)},
    )
    (row,) = tr.run(cand, [a, b], tr.load_sot(word), ['png'], fallback=fb, render_docx=_render_pdf_as_is, dpi=72)
    assert row['ok'] and row['sot']['source'] == 'pdftoppm'
    assert row['sot']['files']['pdf'].endswith('clean/pdf/a.pdf')  # Word's PDF is the input
    assert row['scores']['pixel'] == pytest.approx(100.0) and row['scores']['jaccard'] == pytest.approx(100.0)


def test_a_failing_tool_is_a_row_and_rasters_never_outlive_the_run(tmp_path):
    a, b = _doc(tmp_path, 'a', b'A'), _doc(tmp_path, 'b', b'B')
    word = _sot_corpus(tmp_path, a, b)
    fb = _fallbacks(tmp_path, _pdf(tmp_path / 'lo.pdf'), _pdf(tmp_path / 'dx.pdf'))

    def boom(inputs, out, dpi):
        raise RuntimeError('tool crashed')

    good = _copy_tool('cand', word / 'clean' / 'pdf' / 'a.pdf')
    bad = tr.Tool(name='bad', version='b 1', runners={'convert': boom})
    before = set(tmp_path.rglob('*.png'))
    (row,) = tr.run(bad, [a, b], tr.load_sot(word), ['convert'], fallback=fb, render_docx=_render_pdf_as_is, dpi=72)
    assert not row['ok'] and 'tool crashed' in row['error']
    tr.run(good, [a, b], tr.load_sot(word), ['convert', 'png'], fallback=fb, render_docx=_render_pdf_as_is, dpi=72)
    assert set(tmp_path.rglob('*.png')) == before


def test_a_template_gets_absolute_paths_even_from_a_relative_input(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _pdf(tmp_path / 'rel' / 'in.pdf')
    tool = tr.template_tool('cp {input} {out}')
    out = tool.runners['convert']({'input': Path('rel/in.pdf')}, Path('o'), 72)
    assert out.is_file()
    assert tr.load_sot(Path('word')).root.is_absolute()
