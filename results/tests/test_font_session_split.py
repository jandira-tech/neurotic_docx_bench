"""results/redlines_0929_full/font_session_split.py reads the PDFs each score row was scored on."""

import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

SCRIPT = Path(__file__).resolve().parents[1] / 'results' / 'redlines_0929_full' / 'font_session_split.py'
spec = importlib.util.spec_from_file_location('font_session_split', SCRIPT)
fss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fss)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_rows_resolve_to_the_fresh_oracle_and_the_first_key_candidate(tmp_path, monkeypatch):
    monkeypatch.setattr(fss, 'HERE', tmp_path)
    (tmp_path / 'pool_pairs.csv').write_text('key,id,base,next\nk1,i1,a,b\nk2,i2,a,b\nk3,i3,c,d\n')
    (tmp_path / 'gen_pairs.csv').write_text('key,base,next\nk1,a,b\nk2,a,b\nk3,c,d\n')
    lane = tmp_path / 'lane' / 'pdf_by_word'
    lane.mkdir(parents=True)
    fresh = tmp_path / 'fresh'
    fresh.mkdir()
    for key in ('k1', 'k3'):
        (lane / f'{key}_lane.pdf').write_bytes(f'cand {key}'.encode())
        (fresh / f'{key}.pdf').write_bytes(f'oracle {key}'.encode())
    (fresh / 'k2.pdf').write_bytes(b'oracle k2')

    def oracles(pool, fresh_dir):
        assert fresh_dir == fresh
        return {r['key']: (fresh_dir / f'{r["key"]}.pdf', 'fresh') for r in pool}

    rows = {
        # k2 repeats k1's pair: measure.py scored k1's candidate for it
        'k1': {'oracle_sha256': _sha(fresh / 'k1.pdf'), 'candidate_sha256': _sha(lane / 'k1_lane.pdf')},
        'k2': {'oracle_sha256': _sha(fresh / 'k2.pdf'), 'candidate_sha256': _sha(lane / 'k1_lane.pdf')},
        'k3': {'oracle_sha256': _sha(fresh / 'k3.pdf'), 'candidate_sha256': 'f' * 64},
    }
    scores = {'summary': {'fresh_dir': str(fresh)}, 'rows': rows}
    got = fss.scored_pdfs('lane', scores, {'k1', 'k2', 'k3'}, SimpleNamespace(oracles=oracles))
    assert got == {
        'k1': (fresh / 'k1.pdf', lane / 'k1_lane.pdf'),
        'k2': (fresh / 'k2.pdf', lane / 'k1_lane.pdf'),
    }
