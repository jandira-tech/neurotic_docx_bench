"""Score a jubarte binary's PDFs of the H-math set against Word's, and compare two runs.

    uv run python results/release_0.11.3_queue/math_bench.py run TAG BINARY
    uv run python results/release_0.11.3_queue/math_bench.py cmp OLD_TAG NEW_TAG

The set is hmath_rows.jsonl: the 29 corpus documents holding a display equation
(`m:oMathPara`) and the seeded control of 116 without any OMML. `run` converts each with
`--revisions word` into jubarte-loop/release_0.11.3/math_lanes/TAG, scores every PDF
against the document's corpus Word PDF (docxide-metrics: jaccard, ssim,
text_boundary, as jubarte-loop/enbench.py does) and writes math_scores_TAG.json beside this file. `cmp` prints the paired deltas
for the math set and for the control. A math change must leave every control PDF's text
and page count as they were; `cmp` counts the control documents whose candidate PDF
hash moved and whose score moved by more than 0.01.
"""

from __future__ import annotations

import json
import random
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCORER = str(ROOT / 'src/neurotic_docx_bench/utils/docxide-metrics/target/release/docxide-metrics')

CORPUS = ROOT / 'corpus' / 'word'
LANES = Path('/Users/arthrod/temp/T/jubarte-loop/release_0.11.3/math_lanes')
TOOL = 'jubarte'


def documents() -> list[dict]:
    rows = [json.loads(line) for line in (HERE / 'hmath_rows.jsonl').read_text().splitlines()]
    by_id = {r['id']: r for r in (json.loads(json.dumps(x)) for x in rows)}
    import csv
    for doc in csv.DictReader((CORPUS / 'documents.csv').open()):
        if doc['id'] in by_id:
            by_id[doc['id']] |= {'docx': doc['docx'], 'pdf': doc['pdf']}
    return list(by_id.values())


def run(tag: str, binary: str) -> None:
    lane = LANES / tag
    lane.mkdir(parents=True, exist_ok=True)
    docs = documents()

    def convert(doc: dict) -> None:
        subprocess.run([binary, 'convert', str(CORPUS / doc['docx']), '-o', str(lane / f'{doc["id"]}_{TOOL}.pdf'),
                        '--force', '--revisions', 'word'], capture_output=True, timeout=300, check=False)

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(convert, docs))
    with tempfile.TemporaryDirectory(prefix='math-bench.') as tmp:
        jobs = [{'stem': doc['id'], 'oracle': str(CORPUS / doc['pdf']),
                 'candidate': str(lane / f'{doc["id"]}_{TOOL}.pdf')} for doc in docs]
        (Path(tmp) / 'jobs.json').write_text(json.dumps(jobs))
        subprocess.run([SCORER, '--jobs', str(Path(tmp) / 'jobs.json'), '--scratch', str(Path(tmp) / 'raster'),
                        '--out', str(Path(tmp) / 'out.json'), '--workers', '10'], check=True, capture_output=True)
        got = {r['stem']: r for r in json.loads((Path(tmp) / 'out.json').read_text())}
    out = {}
    for doc in docs:
        pdf = lane / f'{doc["id"]}_{TOOL}.pdf'
        row = got.get(doc['id']) or {}
        out[doc['id']] = {'math': doc['math'], 'stem': doc['stem'],
                          'candidate_sha256': sha256(pdf.read_bytes()).hexdigest() if pdf.is_file() else None,
                          **{k: row.get(k) for k in ('jaccard', 'ssim', 'text_boundary', 'pages', 'ref_pages')}}
        out[doc['id']]['jaccard'] = out[doc['id']]['jaccard'] or 0.0
    (HERE / f'math_scores_{tag}.json').write_text(json.dumps({'binary': binary, 'rows': out}, indent=1, sort_keys=True))
    for group in ('display', 'none'):
        xs = [r['jaccard'] for r in out.values() if r['math'] == group]
        print(f'{tag} {group}: n={len(xs)} mean {statistics.fmean(xs):.2f} median {statistics.median(xs):.2f}')


def cmp(old: str, new: str) -> None:
    a = json.loads((HERE / f'math_scores_{old}.json').read_text())['rows']
    b = json.loads((HERE / f'math_scores_{new}.json').read_text())['rows']
    rng = random.Random(20261004)
    for group in ('display', 'none'):
        keys = sorted(k for k in a if k in b and a[k]['math'] == group)
        for term in ('jaccard', 'ssim', 'text_boundary'):
            pairs = [(a[k].get(term), b[k].get(term)) for k in keys]
            d = [y - x for x, y in pairs if x is not None and y is not None]
            if not d:
                continue
            boot = sorted(statistics.fmean(rng.choices(d, k=len(d))) for _ in range(4000))
            print(f'{group:7} {term:14} n={len(d):3} delta {statistics.fmean(d):+.4f} '
                  f'[{boot[100]:+.4f},{boot[3899]:+.4f}] up {sum(x > 0.01 for x in d)} down {sum(x < -0.01 for x in d)}')
        moved = [k for k in keys if a[k]['candidate_sha256'] != b[k]['candidate_sha256']]
        print(f'{group:7} PDFs changed: {len(moved)}/{len(keys)}; '
              f'jaccard moved >0.01: {sum(abs(b[k]["jaccard"] - a[k]["jaccard"]) > 0.01 for k in keys)}')
        for k in sorted(keys, key=lambda k: b[k]['jaccard'] - a[k]['jaccard'])[:3]:
            print(f'   worst {b[k]["jaccard"] - a[k]["jaccard"]:+.4f} {a[k]["stem"]}')


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        run(sys.argv[2], sys.argv[3])
    else:
        cmp(sys.argv[2], sys.argv[3])
