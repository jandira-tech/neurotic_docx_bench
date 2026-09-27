"""scripts/docx_to_pdf_speed.py: probes, corpora and the per-tool summary rows."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'docx_to_pdf_speed.py'


def _load():
    spec = importlib.util.spec_from_file_location('docx_to_pdf_speed', _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules['docx_to_pdf_speed'] = mod
    spec.loader.exec_module(mod)
    return mod


d2p = _load()


def test_a_hung_version_probe_does_not_stop_the_run(monkeypatch):
    def hang(cmd, **kw):
        assert kw.get('timeout'), 'every probe needs a timeout'
        raise subprocess.TimeoutExpired(cmd, kw['timeout'])

    monkeypatch.setattr(d2p.subprocess, 'run', hang)
    assert d2p.version_of('rdocx', 'jubarte') == 'rdocx (version probe timed out)'
    assert d2p.version_of('docxide', 'jubarte') == 'docxide (version probe timed out)'


def test_a_silent_version_probe_names_the_tool(monkeypatch):
    monkeypatch.setattr(d2p.subprocess, 'run', lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, '', ''))
    assert d2p.version_of('office2pdf', 'jubarte') == 'office2pdf'


def test_an_empty_corpus_stops_before_any_conversion(tmp_path):
    full, empty = tmp_path / 'full', tmp_path / 'empty'
    full.mkdir()
    empty.mkdir()
    (full / 'a.docx').write_bytes(b'x')
    (empty / '~$lock.docx').write_bytes(b'x')
    with pytest.raises(SystemExit, match='empty'):
        d2p.load_corpora([f'full={full}', f'empty={empty}'], 0)
    assert [(n, [p.name for p in docs]) for n, docs in d2p.load_corpora([f'full={full}'], 0)] == [('full', ['a.docx'])]


def test_a_tool_without_one_success_still_gets_a_row():
    samples = {('jubarte', 'c'): [3.0, 1.0, 2.0], ('jubarte', 'all'): [3.0, 1.0, 2.0]}
    failed = {('rdocx', 'c'): 3, ('rdocx', 'all'): 3}
    rows = d2p.summary_rows(
        ['jubarte', 'rdocx'], ['c'], samples, failed, {'jubarte': 'j', 'rdocx': 'r'}, 'ts', warm=False
    )
    by = {(r['tool'], r['corpus']): r for r in rows}
    assert set(by) == {('jubarte', 'c'), ('jubarte', 'all'), ('rdocx', 'c'), ('rdocx', 'all')}
    assert (by['rdocx', 'c']['n'], by['rdocx', 'c']['failed']) == (0, 3)
    assert by['rdocx', 'c']['mean'] is None and by['rdocx', 'c']['p95'] is None
    assert by['jubarte', 'c']['median'] == pytest.approx(2.0)


def test_p95_is_the_nearest_rank_sample():
    xs = [float(i) for i in range(1, 21)]
    (row,) = d2p.summary_rows(['t'], [], {('t', 'all'): xs}, {}, {'t': 'v'}, 'ts', warm=True)
    # ceil(0.95 * 20) - 1 = 18 -> the 19th sample, not the maximum.
    assert row['p95'] == pytest.approx(19.0)
    assert row['mode'] == 'warm'
