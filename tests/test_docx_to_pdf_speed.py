"""docx_to_pdf_speed: the jubarte --compress variant and file-list corpora."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    'docx_to_pdf_speed', Path(__file__).resolve().parent.parent / 'scripts' / 'docx_to_pdf_speed.py'
)
speed = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(speed)


def test_jubarte_compress_is_the_jubarte_call_plus_compress():
    src, dst, lo = Path('a.docx'), Path('a.pdf'), Path('lo')
    plain = speed.tool_cmd('jubarte', src, dst, jubarte='bin/jubarte', profile=lo, lo_dir=lo)
    packed = speed.tool_cmd('jubarte-compress', src, dst, jubarte='bin/jubarte', profile=lo, lo_dir=lo)
    assert plain == ['bin/jubarte', 'convert', 'a.docx', '-o', 'a.pdf', '--force', '--revisions', 'word']
    assert packed == [*plain, '--compress']


def test_corpus_from_a_list_file_keeps_its_order_and_skips_blanks(tmp_path: Path):
    for n in ('b.docx', 'a.docx'):
        (tmp_path / n).write_bytes(b'x')
    listing = tmp_path / 'docs.txt'
    listing.write_text(f'{tmp_path / "b.docx"}\n\n{tmp_path / "a.docx"}\n')
    name, docs = speed.load_corpus(f'mix=@{listing}')
    assert name == 'mix'
    assert docs == [tmp_path / 'b.docx', tmp_path / 'a.docx']


def test_corpus_from_a_list_file_refuses_a_missing_path(tmp_path: Path):
    listing = tmp_path / 'docs.txt'
    listing.write_text(f'{tmp_path / "gone.docx"}\n')
    with pytest.raises(SystemExit):
        speed.load_corpus(f'mix=@{listing}')


def test_corpus_from_a_directory_is_sorted_without_lock_files(tmp_path: Path):
    for n in ('b.docx', 'a.docx', '~$a.docx', 'c.txt'):
        (tmp_path / n).write_bytes(b'x')
    assert speed.load_corpus(f'd={tmp_path}') == ('d', [tmp_path / 'a.docx', tmp_path / 'b.docx'])


def _count(cmdline: str) -> int:
    import subprocess

    out = subprocess.run(['ps', '-Ao', 'command'], capture_output=True, text=True).stdout
    return sum(line.strip() == cmdline for line in out.splitlines())


def test_run_capped_kills_the_whole_process_group_on_timeout():
    before = _count('sleep 3602')
    rc, timed_out = speed.run_capped(['sh', '-c', 'sleep 3602 & sleep 3602'], timeout=0.5)
    assert timed_out and rc != 0
    import time

    time.sleep(0.3)
    assert _count('sleep 3602') == before


def test_run_capped_returns_the_exit_code():
    assert speed.run_capped(['sh', '-c', 'exit 3'], timeout=5) == (3, False)
