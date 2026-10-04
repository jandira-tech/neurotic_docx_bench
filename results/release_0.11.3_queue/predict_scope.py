"""Does a converter change touch only the documents it predicts? Corpus-wide check.

    uv run python results/release_0.11.3_queue/predict_scope.py OLD_BIN NEW_BIN TAG [--marker '<m:oMath']

Prediction, written before the run: converting every corpus document that has a Word PDF
(documents.csv) with OLD_BIN and NEW_BIN gives byte-identical PDFs except for documents
whose main story or any other story part (headers, footers, notes, comments) holds MARKER
(default `<m:oMath`, the math work of engine PR #351). Prints the confusion matrix
(predicted change x observed change) and lists every surprise; scores both sides of each
changed document against Word's PDF with docxide-metrics and reports the paired deltas
with a 95% bootstrap interval. Writes scope_TAG.json beside this file. PDFs go to
jubarte-loop/release_0.11.3/scope/TAG/{old,new} and are kept for inspection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
import subprocess
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = ROOT / 'corpus' / 'word'
SCORER = str(ROOT / 'src/neurotic_docx_bench/utils/docxide-metrics/target/release/docxide-metrics')
OUT = Path('/Users/arthrod/temp/T/jubarte-loop/release_0.11.3/scope')


def holds_marker(docx: Path, marker: bytes) -> bool:
    try:
        with zipfile.ZipFile(docx) as z:
            return any(marker in z.read(n) for n in z.namelist() if n.startswith('word/') and n.endswith('.xml'))
    except (zipfile.BadZipFile, OSError):
        return False


def convert(binary: str, docx: Path, pdf: Path) -> str | None:
    subprocess.run([binary, 'convert', str(docx), '-o', str(pdf), '--force', '--revisions', 'word'],
                   capture_output=True, timeout=300, check=False)
    return hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.is_file() else None


def score(pairs: list[tuple[str, Path, Path]]) -> dict[str, float]:
    with tempfile.TemporaryDirectory(prefix='scope.') as tmp:
        jobs = [{'stem': k, 'oracle': str(o), 'candidate': str(c)} for k, o, c in pairs]
        (Path(tmp) / 'jobs.json').write_text(json.dumps(jobs))
        subprocess.run([SCORER, '--jobs', str(Path(tmp) / 'jobs.json'), '--scratch', str(Path(tmp) / 'r'),
                        '--out', str(Path(tmp) / 'out.json'), '--workers', '10'], check=True, capture_output=True)
        return {r['stem']: r.get('jaccard') or 0.0 for r in json.loads((Path(tmp) / 'out.json').read_text())}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('old')
    ap.add_argument('new')
    ap.add_argument('tag')
    ap.add_argument('--marker', default='<m:oMath')
    args = ap.parse_args()
    docs = [r for r in csv.DictReader((CORPUS / 'documents.csv').open()) if r['pdf']]
    old_dir, new_dir = OUT / args.tag / 'old', OUT / args.tag / 'new'
    old_dir.mkdir(parents=True, exist_ok=True)
    new_dir.mkdir(parents=True, exist_ok=True)

    def one(doc: dict) -> dict:
        docx = CORPUS / doc['docx']
        return {'id': doc['id'], 'stem': doc['stem'], 'pdf': doc['pdf'],
                'predicted': holds_marker(docx, args.marker.encode()),
                'old': convert(args.old, docx, old_dir / f'{doc["id"]}.pdf'),
                'new': convert(args.new, docx, new_dir / f'{doc["id"]}.pdf')}

    with ThreadPoolExecutor(10) as pool:
        rows = list(pool.map(one, docs))
    matrix = {f'predicted={p} changed={c}': 0 for p in (True, False) for c in (True, False)}
    surprises = []
    for r in rows:
        r['changed'] = r['old'] != r['new']
        matrix[f'predicted={r["predicted"]} changed={r["changed"]}'] += 1
        if r['predicted'] != r['changed']:
            surprises.append(r['stem'])
    changed = [r for r in rows if r['changed'] and r['old'] and r['new']]
    a = score([(r['id'], CORPUS / r['pdf'], old_dir / f'{r["id"]}.pdf') for r in changed]) if changed else {}
    b = score([(r['id'], CORPUS / r['pdf'], new_dir / f'{r["id"]}.pdf') for r in changed]) if changed else {}
    deltas = [b[k] - a[k] for k in a if k in b]
    rng = random.Random(20261004)
    boot = sorted(statistics.fmean(rng.choices(deltas, k=len(deltas))) for _ in range(4000)) if deltas else [0.0] * 4000
    result = {'old': args.old, 'new': args.new, 'marker': args.marker, 'documents': len(rows),
              'failed_old': sum(r['old'] is None for r in rows), 'failed_new': sum(r['new'] is None for r in rows),
              'matrix': matrix, 'surprises': surprises,
              'changed_jaccard': {'n': len(deltas), 'old_mean': statistics.fmean(a.values()) if a else None,
                                  'new_mean': statistics.fmean(b.values()) if b else None,
                                  'delta': statistics.fmean(deltas) if deltas else None,
                                  'ci95': [boot[100], boot[3899]],
                                  'up': sum(d > 0.01 for d in deltas), 'down': sum(d < -0.01 for d in deltas),
                                  'worst': sorted(((b[k] - a[k], k) for k in a if k in b))[:5]},
              'holds': not surprises}
    (HERE / f'scope_{args.tag}.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'surprises'} | {'surprises': surprises[:20]}, indent=1))


if __name__ == '__main__':
    main()
