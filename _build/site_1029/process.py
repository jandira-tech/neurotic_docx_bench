"""Score/encode phase-3a jobs, with resumable content/scorer-keyed records.

python process.py [--limit N] [--workers 6]
All temporary rasters are deleted after each scoring/encoding stage.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

H = Path(__file__).resolve().parent
BUILD = H / 'build'
sys.path.insert(0, str(H / 'scorer-source/src'))
from neurotic_docx_bench import content_cache, kernels, pipeline
from common import KEY, VERSION
import reference_process_1028
from reference_process_1028 import draw, encode, metrics, run
reference_process_1028.METRICS_BIN = H / 'bin/page-metrics'


def failure_row(job: dict, error: str) -> dict:
    return {'group': job['group'], 'case': job['case'], 'shown': job['shown'],
            'pages': {KEY: [None] * len(job['shown'])}, 'pdfs': {},
            'page_counts': {KEY: 0}, 'times': {},
            'scores': {KEY: {'pixel': 0}}, 'errors': {KEY: error},
            'versions': {KEY: VERSION}}


def case(job: dict) -> dict:
    if job['failure']:
        return failure_row(job, job['failure'])
    ref, pdf = Path(job['ref']), Path(job['pdf'])
    for path in (ref, pdf):
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != job['hashes'][str(path)]:
            raise ValueError(f'Input changed: {path}')
    row = {'group': job['group'], 'case': job['case'], 'shown': job['shown'],
           'pages': {}, 'pdfs': {}, 'page_counts': {}, 'times': {},
           'scores': {}, 'errors': {}, 'versions': {KEY: VERSION}, 'metric_diagnostics': {}}
    with tempfile.TemporaryDirectory(prefix='c_', dir=BUILD) as temp:
        tmp = Path(temp)
        result = pipeline.score_pdf_pair(ref, pdf, tmp / 'pixel',
                    dpi=job['provenance']['pixel_dpi'], key='pair', cache=None)
        pixel = pipeline.overall_from_result(result)
        row['scores'][KEY] = {'pixel': pixel}
        row['page_counts'][KEY] = result['page_count_candidate']
        if result['page_count_oracle'] != job['reference_pages']:
            raise ValueError('Reference page count changed')
        # Preserve the full current-main scorer result (including raw/pagefair and
        # the #98 port's metrics) as evidence, separate from 150-DPI upstream metrics.
        row['pixel_result'] = result
        shutil.rmtree(tmp / 'pixel')
        draw(ref, tmp / 'reference', 150)
        draw(pdf, tmp / KEY, 150)
        diagnostics = {}
        row['scores'][KEY].update(metrics(ref, pdf, tmp / 'reference', tmp / KEY, diagnostics))
        row['metric_diagnostics'][KEY] = diagnostics
        shutil.rmtree(tmp / 'reference')
        shutil.rmtree(tmp / KEY)
        show = job['shown']
        n = row['page_counts'][KEY]
        want = [p for p in show if p <= n]
        paths = {}
        base = BUILD / 'renew1028/d2p' / job['group'] / job['case'] / KEY
        if want:
            spec = ','.join(map(str, want))
            draw(pdf, tmp / 'shown', 180, spec)
            pngs = sorted((tmp / 'shown').glob('page_*.png'))
            if len(pngs) != len(want):
                raise ValueError('Wrong shown page count')
            for p, png in zip(want, pngs):
                dst = base / f'page_{p:03d}.webp'
                encode(png, dst)
                paths[p] = dst.relative_to(BUILD).as_posix()
                png.unlink()
            dst = base / 'pages.pdf'
            run(['mutool', 'clean', '-gggz', str(pdf), str(dst), spec])
            if not dst.is_file() or not dst.stat().st_size:
                raise ValueError('No page PDF')
            row['pdfs'][KEY] = dst.relative_to(BUILD).as_posix()
        row['pages'][KEY] = [paths.get(p) for p in show]
    return row


def build_one(job: dict) -> dict:
    if content_cache.scorer_fingerprint() != job['provenance']['scorer_fingerprint']:
        raise ValueError('Scorer fingerprint changed')
    if kernels.backend_id() != job['provenance']['scorer_backend']:
        raise ValueError('Scorer backend changed')
    fingerprint = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
    record = BUILD / 'records' / f"{job['key']}.json"
    if record.is_file():
        saved = json.loads(record.read_text())
        if saved['fingerprint'] == fingerprint:
            return saved['row']
    row = case(job)
    record.parent.mkdir(parents=True, exist_ok=True)
    part = record.with_suffix('.tmp')
    part.write_text(json.dumps({'fingerprint': fingerprint, 'row': row}, ensure_ascii=False))
    part.replace(record)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    jobs = json.loads((H / 'jobs_d2p_jubarte.json').read_text())
    if args.limit:
        jobs = jobs[:args.limit]
    BUILD.mkdir(exist_ok=True)
    rows, errors = {}, []
    with ProcessPoolExecutor(args.workers) as pool:
        pending = {pool.submit(build_one, job): i for i, job in enumerate(jobs)}
        for future in as_completed(pending):
            i = pending[future]
            try:
                rows[i] = future.result()
            except Exception as error:
                errors.append({'index': i, 'case': jobs[i]['key'], 'error': str(error)})
                print(f'BUILD ERROR {jobs[i]["key"]}: {error}', flush=True)
            if (len(rows) + len(errors)) % 10 == 0 or len(rows) + len(errors) == len(jobs):
                print(f'{len(rows)}/{len(jobs)} complete, {len(errors)} build errors', flush=True)
    if errors:
        (H / 'errors.json').write_text(json.dumps(errors, indent=2))
        raise SystemExit(f'{len(errors)} build errors; completed records retained')
    name = 'cases_d2p_jubarte' + ('_sample' if args.limit else '') + '.json'
    (BUILD / name).write_text(json.dumps([rows[i] for i in range(len(jobs))], indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
