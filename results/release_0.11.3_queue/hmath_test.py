"""H-math, tested against the corpus without Word: is a display equation short in jubarte?

    uv run python results/release_0.11.3_queue/hmath_test.py BINARY [--jobs N]

Prediction, written before the run (NOTES.md, H-math): Word paints an OMML display
equation (`m:oMathPara`) built up, several lines tall; jubarte paints it as one linear
line. If that costs height, documents holding `m:oMathPara` end on fewer pages than Word
more often than documents without math. Stated test: the share of documents with
jubarte pages < Word pages among math documents minus that share in a seeded control of
documents without any OMML (`m:oMath`), 95% bootstrap interval above zero. The control
has four times as many documents as the math set, drawn per state in the same
proportions (seed 20261004). Each document is converted once by BINARY with
`--revisions word --report`; Word's page count is its corpus PDF's.

Writes hmath_rows.jsonl (one row per document) and hmath_result.json beside this file.
Scratch PDFs go to jubarte-loop/release_0.11.3/hmath_scratch and are deleted.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import subprocess
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = ROOT / 'corpus' / 'word'
SCRATCH = Path('/Users/arthrod/temp/T/jubarte-loop/release_0.11.3/hmath_scratch')
SEED = 20261004


def math_kind(docx: Path) -> str | None:
    try:
        with zipfile.ZipFile(docx) as z:
            xml = z.read('word/document.xml')
    except (KeyError, zipfile.BadZipFile, OSError):
        return None
    if b'<m:oMathPara' in xml:
        return 'display'
    if b'<m:oMath' in xml:
        return 'inline'
    return 'none'


def word_pages(pdf: Path) -> int | None:
    out = subprocess.run(['pdfinfo', str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith('Pages:'):
            return int(line.split()[1])
    return None


def jubarte_pages(binary: str, docx: Path, stem: str) -> int | None:
    pdf = SCRATCH / f'{stem}.pdf'
    report = SCRATCH / f'{stem}.json'
    try:
        subprocess.run([binary, 'convert', str(docx), '-o', str(pdf), '--force', '--revisions', 'word',
                        '--report', str(report)], capture_output=True, timeout=300, check=False)
        return json.loads(report.read_text())['page_count'] if report.exists() else None
    except subprocess.TimeoutExpired:
        return None
    finally:
        pdf.unlink(missing_ok=True)
        report.unlink(missing_ok=True)


def share_short(rows: list[dict]) -> float:
    return sum(r['delta'] < 0 for r in rows) / len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('binary')
    ap.add_argument('--jobs', type=int, default=8)
    args = ap.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)

    docs = [r for r in csv.DictReader((CORPUS / 'documents.csv').open()) if r['pdf']]
    with ThreadPoolExecutor(args.jobs) as pool:
        kinds = list(pool.map(lambda r: math_kind(CORPUS / r['docx']), docs))
    for row, kind in zip(docs, kinds):
        row['math'] = kind
    math = [r for r in docs if r['math'] == 'display']
    plain = [r for r in docs if r['math'] == 'none']
    rng = random.Random(SEED)
    want = Counter(r['state'] for r in math)
    control: list[dict] = []
    for state, n in sorted(want.items()):
        pool_state = sorted((r for r in plain if r['state'] == state), key=lambda r: r['id'])
        control += rng.sample(pool_state, min(len(pool_state), 4 * n))
    print(f'documents {len(docs)}: display math {len(math)}, inline only '
          f'{sum(r["math"] == "inline" for r in docs)}, no math {len(plain)}; control {len(control)}')

    def measure(row: dict) -> dict:
        wp = word_pages(CORPUS / row['pdf'])
        jp = jubarte_pages(args.binary, CORPUS / row['docx'], row['id'])
        return {'id': row['id'], 'stem': row['stem'], 'state': row['state'], 'math': row['math'],
                'word_pages': wp, 'jubarte_pages': jp,
                'delta': None if wp is None or jp is None else jp - wp}

    with ThreadPoolExecutor(args.jobs) as pool:
        rows = list(pool.map(measure, math + control))
    with (HERE / 'hmath_rows.jsonl').open('w') as out:
        for row in rows:
            out.write(json.dumps(row) + '\n')

    groups = {'display': [r for r in rows if r['math'] == 'display' and r['delta'] is not None],
              'control': [r for r in rows if r['math'] == 'none' and r['delta'] is not None]}
    diffs = []
    for _ in range(4000):
        a = [rng.choice(groups['display']) for _ in groups['display']]
        b = [rng.choice(groups['control']) for _ in groups['control']]
        diffs.append(share_short(a) - share_short(b))
    diffs.sort()
    result = {
        'binary': args.binary, 'seed': SEED,
        'failed': sum(r['delta'] is None for r in rows),
        **{name: {'n': len(g), 'short': sum(r['delta'] < 0 for r in g), 'long': sum(r['delta'] > 0 for r in g),
                  'exact': sum(r['delta'] == 0 for r in g)} for name, g in groups.items()},
        'short_share_gap': share_short(groups['display']) - share_short(groups['control']),
        'ci95': [diffs[100], diffs[3899]],
    }
    result['holds'] = result['ci95'][0] > 0
    (HERE / 'hmath_result.json').write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
