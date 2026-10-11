"""scripts/probe_trailing_page_break.py: tables cut one by one, renders per binary."""

import importlib.util
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'probe_trailing_page_break.py'
spec = importlib.util.spec_from_file_location('probe_trailing_page_break', SCRIPT)
ptb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ptb)

BREAK = '<w:r><w:br w:type="page"/></w:r>'
CELL = '<w:tr><w:tc><w:p><w:r><w:t>cell</w:t></w:r>{}</w:p></w:tc></w:tr>'


def _docx(tmp_path: Path, body: str) -> Path:
    path = tmp_path / 'd.docx'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('word/document.xml', f'<w:document><w:body>{body}</w:body></w:document>')
    return path


def test_a_paragraph_between_two_tables_survives_the_cut():
    body = f'<w:tbl>{CELL.format("")}</w:tbl><w:p>between</w:p><w:tbl>{CELL.format("")}</w:tbl>'
    assert ptb.cut_tables(body) == '<w:TBL/><w:p>between</w:p><w:TBL/>'


def test_a_nested_table_goes_with_its_outer_table():
    inner = f'<w:tbl>{CELL.format("")}</w:tbl>'
    body = f'<w:tbl><w:tr><w:tc>{inner}<w:p/></w:tc></w:tr></w:tbl><w:p>after</w:p>'
    assert ptb.cut_tables(body) == '<w:TBL/><w:p>after</w:p>'


def test_the_last_body_paragraph_is_read_past_earlier_tables(tmp_path):
    # a page break inside the second table's cell must not make the last
    # body paragraph (between the tables) 'trailing'
    body = (
        f'<w:tbl>{CELL.format("")}</w:tbl><w:p><w:r><w:t>last body text</w:t></w:r></w:p>'
        f'<w:tbl>{CELL.format(BREAK)}</w:tbl><w:sectPr/>'
    )
    assert ptb.classify(_docx(tmp_path, body)) == {'class': 'none'}


def test_renders_of_another_binary_move_aside(tmp_path):
    one, two = tmp_path / 'one', tmp_path / 'two'
    one.write_bytes(b'1')
    two.write_bytes(b'2')
    pdf_dir = tmp_path / 'out' / 'pdf'
    ptb.fresh_renders(pdf_dir, one)
    (pdf_dir / 'a.pdf').write_bytes(b'%PDF-')
    ptb.fresh_renders(pdf_dir, one)
    assert (pdf_dir / 'a.pdf').is_file()
    ptb.fresh_renders(pdf_dir, two)
    assert not (pdf_dir / 'a.pdf').exists()
    assert (tmp_path / 'out' / 'pdf_stale' / '001' / 'a.pdf').is_file()
