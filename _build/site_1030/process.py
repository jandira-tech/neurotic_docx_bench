"""Score/encode phase-3b jobs, with input/scorer-keyed resumable records.

python process.py [--limit N] [--workers 6] [--which all|redlines|ar|references]
Temporary rasters are removed at the end of each stage; no source PDF is changed.
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
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent
BUILD = H / 'build'
os.environ['BENCH_DEVICE'] = 'numpy'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, str(H / 'scorer-source/src'))
from neurotic_docx_bench import content_cache, kernels, pipeline
import reference_process_1028
from reference_process_1028 import draw, encode, metrics, run
reference_process_1028.METRICS_BIN = H / 'bin/page-metrics'
METRICS_SHA = '2213ff317059873a15e9605825387a6f41e1514a21a1c9c7e4b7187a7f37925c'


def empty_row(job: dict) -> dict:
    key = job['column']
    return {'group': job['group'], 'case': job['case'], 'tool': job['tool'], 'column': key,
            'key': job['key'], 'phase1_key': job['phase1_key'], 'viewer': job['viewer'],
            'shown': job['shown'], 'pages': {}, 'pdfs': {}, 'page_counts': {},
            'times': {}, 'scores': {}, 'errors': {}, 'versions': {key: job['version']},
            'metric_diagnostics': {}, 'failure_type': job['failure_type']}


def failure_row(job: dict, error: str) -> dict:
    row, key = empty_row(job), job['column']
    row.update(pages={key: [None] * len(job['shown'])}, page_counts={key: 0},
               scores={key: {'pixel': 0}}, errors={key: error},
               failure_evidence=job.get('failure_evidence', []))
    return row


def encode_shown(job: dict, row: dict, pdf: Path, tmp: Path) -> None:
    key = job['column']
    show = job['shown']
    want = [p for p in show if p <= row['page_counts'][key]]
    paths = {}
    group = job['group'].removeprefix('ar/') if job['viewer'] == 'ar' else job['group']
    base = BUILD / 'renew1030' / job['viewer'] / group / job['case'] / key
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
        row['pdfs'][key] = dst.relative_to(BUILD).as_posix()
    row['pages'][key] = [paths.get(p) for p in show]


def case(job: dict) -> dict:
    # Hash every selected phase-1 input, generated document and exported output,
    # including failed jobs: a checkpoint is evidence for exactly these bytes.
    for name, expected in job['hashes'].items():
        with Path(name).open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != expected:
            raise ValueError(f'Input changed: {name}')
    if job['failure']:
        return failure_row(job, job['failure'])
    ref, pdf, key = Path(job['ref']), Path(job['pdf']), job['column']
    row = empty_row(job)
    with tempfile.TemporaryDirectory(prefix='c_', dir=BUILD) as temp:
        tmp = Path(temp)
        if job['tool'] == 'reference':
            import pymupdf
            with pymupdf.open(ref) as doc:
                row['page_counts'][key] = len(doc)
            if row['page_counts'][key] != job['reference_pages']:
                raise ValueError('Reference page count changed')
        else:
            result = pipeline.score_pdf_pair(ref, pdf, tmp / 'pixel',
                        dpi=job['provenance']['pixel_dpi'], key='pair', cache=None)
            row['scores'][key] = {'pixel': pipeline.overall_from_result(result)}
            row['page_counts'][key] = result['page_count_candidate']
            if result['page_count_oracle'] != job['reference_pages']:
                raise ValueError('Reference page count changed')
            row['pixel_result'] = result
            shutil.rmtree(tmp / 'pixel')
            draw(ref, tmp / 'reference', 150)
            draw(pdf, tmp / key, 150)
            diagnostics = {}
            row['scores'][key].update(metrics(ref, pdf, tmp / 'reference', tmp / key, diagnostics))
            row['metric_diagnostics'][key] = diagnostics
            shutil.rmtree(tmp / 'reference')
            shutil.rmtree(tmp / key)
        encode_shown(job, row, pdf, tmp)
    return row


def assets_exist(row: dict) -> bool:
    assets = [p for values in row.get('pages', {}).values() for p in values if p]
    assets += list(row.get('pdfs', {}).values())
    return all((BUILD / p).is_file() and (BUILD / p).stat().st_size for p in assets)


def build_one(job: dict) -> dict:
    if content_cache.scorer_fingerprint() != job['provenance']['scorer_fingerprint']:
        raise ValueError('Scorer fingerprint changed')
    if kernels.backend_id() != job['provenance']['scorer_backend']:
        raise ValueError('Scorer backend changed')
    with (H / 'bin/page-metrics').open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != METRICS_SHA:
            raise ValueError('Upstream page-metrics binary changed')
    fingerprint = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
    record = BUILD / 'records' / f"{job['key']}.json"
    if record.is_file():
        saved = json.loads(record.read_text())
        if saved['fingerprint'] == fingerprint and assets_exist(saved['row']):
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
    parser.add_argument('--which', choices=('all', 'redlines', 'ar', 'references'), default='all')
    args = parser.parse_args()
    filename = 'jobs_prepared' if args.which == 'all' else 'jobs_' + args.which
    jobs = json.loads((H / (filename + '.json')).read_text())
    if args.limit:
        jobs = jobs[:args.limit]
    if args.workers < 1 or args.workers > 6:
        parser.error('--workers must be between 1 and 6')
    BUILD.mkdir(exist_ok=True)
    rows, errors = {}, []
    def progress(message: str) -> None:
        line = f'{datetime.now(timezone.utc).isoformat()} {message}'
        print(line, flush=True)
        with (H / 'process.log').open('a') as log:
            log.write(line + '\n')
    progress(f'Start {args.which}: {len(jobs)} jobs, {args.workers} workers')
    with ProcessPoolExecutor(args.workers) as pool:
        pending = {pool.submit(build_one, job): i for i, job in enumerate(jobs)}
        for future in as_completed(pending):
            i = pending[future]
            try:
                rows[i] = future.result()
            except Exception as error:
                errors.append({'index': i, 'case': jobs[i]['key'], 'error': str(error)})
                progress(f'BUILD ERROR {jobs[i]["key"]}: {error}')
            count = len(rows) + len(errors)
            if count % 10 == 0 or count == len(jobs):
                progress(f'{args.which}: {len(rows)}/{len(jobs)} complete, {len(errors)} build errors')
    if errors:
        (H / f'errors_{args.which}.json').write_text(json.dumps(errors, indent=2))
        raise SystemExit(f'{len(errors)} build errors; completed records retained')
    name = 'cases' + ('' if args.which == 'all' else '_' + args.which) + ('_sample' if args.limit else '')
    (BUILD / (name + '.json')).write_text(json.dumps([rows[i] for i in range(len(jobs))], indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
