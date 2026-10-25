"""results/release_0.11.3_queue: a failed conversion is never scored or hashed as a fresh one (PR #64 review).

The scripts reuse a TAG's output folder, so a PDF an earlier run left there must not stand in
for a conversion that failed now. A fake converter and a fake docxide-metrics scorer replace
the real binaries; nothing here needs the corpus.
"""

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

QUEUE = Path(__file__).resolve().parents[1] / 'results' / 'release_0.11.3_queue'

# Fake jubarte: `convert DOCX -o PDF --force --revisions word`. A docx named *fail* exits 3
# without output, *partial* writes a truncated PDF and exits 3; anything else writes bytes
# that name the binary, so two binaries always disagree.
CONVERTER = """#!/bin/sh
case "$(basename "$2")" in
  *fail*) exit 3 ;;
  *partial*) printf partial > "$4"; exit 3 ;;
esac
printf 'pdf-by-%s-of-%s' "$(basename "$0")" "$(basename "$2")" > "$4"
"""

# Fake docxide-metrics: one row per job, and the candidates it was given appended to a log.
SCORER = f"""#!{sys.executable}
import json, sys
a = sys.argv
jobs = json.load(open(a[a.index('--jobs') + 1]))
with open(a[0] + '.log', 'a') as log:
    log.writelines(j['candidate'] + '\\n' for j in jobs)
rows = [{{'stem': j['stem'], 'jaccard': 50.0, 'ssim': 0.5, 'text_boundary': 0.5, 'pages': 1, 'ref_pages': 1}}
        for j in jobs]
json.dump(rows, open(a[a.index('--out') + 1], 'w'))
"""


def load(name: str):
    spec = importlib.util.spec_from_file_location(f'queue_{name}', QUEUE / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tool(path: Path, text: str) -> str:
    path.write_text(text)
    path.chmod(0o755)
    return str(path)


def docx(path: Path, body: str) -> None:
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('word/document.xml', body)


def corpus(root: Path, ids: list[str]) -> Path:
    """A documents.csv naming one docx (with and without math) and one Word PDF per id."""
    root.mkdir()
    lines = ['id,stem,docx,pdf']
    for i in ids:
        docx(root / f'{i}.docx', '<w:body><m:oMath/></w:body>' if 'math' in i else '<w:body/>')
        (root / f'{i}.pdf').write_bytes(b'word pdf')
        lines.append(f'{i},stem_{i},{i}.docx,{i}.pdf')
    (root / 'documents.csv').write_text('\n'.join(lines) + '\n')
    return root


def test_math_bench_never_scores_a_pdf_left_by_an_earlier_run(tmp_path, monkeypatch):
    mb = load('math_bench')
    here = tmp_path / 'here'
    here.mkdir()
    math = {'ok': 'display', 'fail': 'display', 'partial': 'display', 'control': 'none'}  # run() reports both groups
    (here / 'hmath_rows.jsonl').write_text(''.join(
        json.dumps({'id': i, 'stem': f'stem_{i}', 'math': m}) + '\n' for i, m in math.items()))
    monkeypatch.setattr(mb, 'HERE', here)
    monkeypatch.setattr(mb, 'CORPUS', corpus(tmp_path / 'corpus', list(math)))
    monkeypatch.setattr(mb, 'LANES', tmp_path / 'lanes')
    scorer = tool(tmp_path / 'scorer', SCORER)
    monkeypatch.setattr(mb, 'SCORER', scorer)
    lane = tmp_path / 'lanes' / 'T'
    lane.mkdir(parents=True)
    stale = lane / 'fail_jubarte.pdf'
    stale.write_bytes(b'pdf from an earlier binary')

    mb.run('T', tool(tmp_path / 'jubarte', CONVERTER))

    rows = json.loads((here / 'math_scores_T.json').read_text())['rows']
    assert rows['ok']['candidate_sha256'] is not None
    assert not rows['ok'].get('failed')
    for bad in ('fail', 'partial'):
        assert rows[bad]['failed'] is True
        assert rows[bad]['candidate_sha256'] is None
    scored = Path(scorer + '.log').read_text().split()
    assert sorted(scored) == [str(lane / 'control_jubarte.pdf'), str(lane / 'ok_jubarte.pdf')]
    assert not stale.exists()
    assert not (lane / 'partial_jubarte.pdf').exists()


def test_math_bench_cmp_leaves_failed_conversions_out(tmp_path, monkeypatch, capsys):
    mb = load('math_bench')
    monkeypatch.setattr(mb, 'HERE', tmp_path)

    def row(sha, jaccard, failed=False):
        return {'math': 'display', 'stem': 's', 'candidate_sha256': sha, 'jaccard': jaccard,
                'ssim': 0.5, 'text_boundary': 0.5, **({'failed': True} if failed else {})}

    (tmp_path / 'math_scores_old.json').write_text(json.dumps(
        {'rows': {'a': row('x', 50.0), 'b': row('y', 50.0)}}))
    (tmp_path / 'math_scores_new.json').write_text(json.dumps(
        {'rows': {'a': row('x', 50.0), 'b': row(None, 0.0, failed=True)}}))

    mb.cmp('old', 'new')

    out = capsys.readouterr().out
    assert 'PDFs changed: 0/1' in out


def test_predict_scope_convert_never_hashes_a_stale_pdf(tmp_path):
    ps = load('predict_scope')
    binary = tool(tmp_path / 'jubarte', CONVERTER)
    stale = tmp_path / 'fail.pdf'
    stale.write_bytes(b'pdf from an earlier binary')
    partial = tmp_path / 'partial.pdf'

    assert ps.convert(binary, tmp_path / 'fail.docx', stale) is None
    assert ps.convert(binary, tmp_path / 'partial.docx', partial) is None
    assert ps.convert(binary, tmp_path / 'ok.docx', tmp_path / 'ok.pdf') is not None
    assert not stale.exists()
    assert not partial.exists()


def test_predict_scope_leaves_failed_documents_out_of_the_matrix(tmp_path, monkeypatch):
    ps = load('predict_scope')
    here = tmp_path / 'here'
    here.mkdir()
    monkeypatch.setattr(ps, 'HERE', here)
    monkeypatch.setattr(ps, 'CORPUS', corpus(tmp_path / 'corpus', ['math_ok', 'plain_fail']))
    monkeypatch.setattr(ps, 'OUT', tmp_path / 'scope')
    monkeypatch.setattr(ps, 'SCORER', tool(tmp_path / 'scorer', SCORER))
    for side, text in (('old', b'old run'), ('new', b'new run')):  # an earlier run's PDFs, different per side
        (tmp_path / 'scope' / 'T' / side).mkdir(parents=True)
        (tmp_path / 'scope' / 'T' / side / 'plain_fail.pdf').write_bytes(text)
    old = tool(tmp_path / 'old_bin', CONVERTER)
    new = tool(tmp_path / 'new_bin', CONVERTER)
    monkeypatch.setattr(sys, 'argv', ['predict_scope.py', old, new, 'T'])

    ps.main()

    result = json.loads((here / 'scope_T.json').read_text())
    assert sum(result['matrix'].values()) == 1
    assert result['matrix']['predicted=True changed=True'] == 1
    assert result['surprises'] == []
    assert result['failed'] == ['stem_plain_fail']
    assert result['failed_old'] == result['failed_new'] == 1


def test_scratch_folders_follow_jubarte_loop_dir(tmp_path, monkeypatch):
    monkeypatch.setenv('JUBARTE_LOOP_DIR', str(tmp_path))
    base = tmp_path / 'release_0.11.3'
    assert load('hmath_test').SCRATCH == base / 'hmath_scratch'
    assert load('math_bench').LANES == base / 'math_lanes'
    assert load('predict_scope').OUT == base / 'scope'


def test_scratch_folders_default_under_home(monkeypatch):
    monkeypatch.delenv('JUBARTE_LOOP_DIR', raising=False)
    assert load('hmath_test').SCRATCH == Path.home() / 'temp/T/jubarte-loop/release_0.11.3/hmath_scratch'
