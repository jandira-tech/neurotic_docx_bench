"""scripts/redline_sample_score.py: strata, binary freshness, failure scores, empty runs."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'redline_sample_score.py'
spec = importlib.util.spec_from_file_location('redline_sample_score', SCRIPT)
rss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rss)


def test_a_filtered_pair_is_counted_under_a_selected_set():
    assert rss.pick_set('alpha;beta', {'beta'}) == 'beta'
    assert rss.pick_set('alpha;beta', None) == 'alpha'
    assert rss.pick_set('alpha', {'beta'}) is None
    assert rss.pick_set('', None) == '?'


def test_another_binary_s_redlines_are_moved_aside_never_reused(tmp_path):
    cdir = tmp_path / 'cand_x'
    old, new = tmp_path / 'old_bin', tmp_path / 'new_bin'
    old.write_bytes(b'old')
    new.write_bytes(b'new')
    rss.fresh_candidates(cdir, old)
    (cdir / 'docx').mkdir()
    (cdir / 'docx' / 'a_x_redline.docx').write_bytes(b'from old')

    rss.fresh_candidates(cdir, old)
    assert (cdir / 'docx' / 'a_x_redline.docx').is_file()

    rss.fresh_candidates(cdir, new)
    assert not (cdir / 'docx').exists()
    assert (tmp_path / 'cand_x_stale' / '001' / 'docx' / 'a_x_redline.docx').read_bytes() == b'from old'
    rss.fresh_candidates(cdir, old)
    assert (tmp_path / 'cand_x_stale' / '002' / 'binary.sha256').is_file()


def test_a_candidate_that_fails_to_redline_or_render_scores_zero(tmp_path):
    chosen = [{'id': i} for i in ('ok', 'genfail', 'nopdf', 'nooracle')]
    for i in ('ok', 'genfail', 'nooracle'):
        (tmp_path / f'{i}_x_redline.pdf').write_bytes(b'%PDF-')
    got = {'ok': 81.5}
    assert rss.collect(chosen, {'genfail': 'boom'}, got, tmp_path, 'x') == {
        'ok': 81.5,
        'genfail': 0.0,
        'nopdf': 0.0,
        'nooracle': None,
    }


def test_a_run_with_no_fully_scored_pair_reports_instead_of_crashing(capsys):
    rss.report({'a': {'set': 's', 'main': None, 'x': 3.0}}, ['main', 'x'])
    assert 'nothing to compare' in capsys.readouterr().out


def test_a_failed_bench_command_stops_the_run(monkeypatch):
    class Done:
        returncode = 2
        stderr = 'usage'

    monkeypatch.setattr(rss.subprocess, 'run', lambda *a, **k: Done())
    with pytest.raises(SystemExit):
        rss.sh(['bench', 'compare'])
    Done.returncode = 1
    assert rss.sh(['bench', 'render'], ok=(0, 1)) == 1
