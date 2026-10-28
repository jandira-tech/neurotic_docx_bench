"""Score/encode prepared jobs. No network or publishing. See README.md.

python process.py v1|redlines|wordcraft_compare|wordcraft_convert [--limit N]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

H = Path(__file__).resolve().parent
BUILD = H / 'build'
METRICS_BIN = Path.home() / 'temp/T/docxide-pdf/tools/target/release/page-metrics'
METRICS = ['jaccard', 'ssim', 'text_boundary']
JOBS = 6


def run(cmd: list[str]) -> str:
    p = subprocess.run(list(map(str, cmd)), capture_output=True, text=True,
                       env={**os.environ, 'RAYON_NUM_THREADS': '1'})
    if p.returncode:
        raise RuntimeError(f'{cmd[0]} exit {p.returncode}: {p.stderr[-2000:]}')
    return p.stdout


def draw(pdf: Path, out: Path, dpi: int = 150, pages: str = '') -> int:
    out.mkdir(parents=True, exist_ok=True)
    cmd = ['mutool', 'draw', '-q', '-F', 'png', '-r', str(dpi), '-o', str(out / 'page_%03d.png'), str(pdf)]
    if pages:
        cmd.append(pages)
    run(cmd)
    n = len(list(out.glob('page_*.png')))
    if not n:
        raise RuntimeError(f'No pages rasterized: {pdf}')
    return n


def metrics(ref: Path, pdf: Path, ref_dir: Path, dir_: Path, diagnostics: dict | None = None) -> dict:
    m = json.loads(run([str(METRICS_BIN), str(ref), str(pdf), str(ref_dir), str(dir_)]))
    if diagnostics is not None:
        diagnostics.update({k: m[k] for k in ('ref_pages', 'pages', 'scored_pages', 'max_break_drift')})
    # Upstream skips page pairs with incompatible dimensions and may return null TB.
    # Preserve those nulls: neither invent a score nor discard a recorded pixel result.
    return {k: round(m[k] * 100, 1) if m.get(k) is not None else None for k in METRICS}


def encode(png: Path, dst: Path) -> None:
    with Image.open(png) as source:
        im = source.convert('RGB')
        im = im.resize((round(im.width * 2 / 3), round(im.height * 2 / 3)), Image.Resampling.LANCZOS)
        im = im.quantize(colors=16, method=Image.Quantize.MEDIANCUT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, 'WEBP', lossless=True, method=4)


def case(prefix: str, group: str, cid: str, ref: Path, cands: dict[str, Path],
         extra: dict | None = None, first: int = 3) -> dict:
    """Score all pages, preserve recorded pixel scores, include Word's shown pages too."""
    base = BUILD / prefix / group / cid
    row = {'group': group, 'case': cid, 'pages': {}, 'page_counts': {}, 'scores': {},
           'pdfs': {}, 'times': {}, 'errors': {}, **(extra or {})}
    with tempfile.TemporaryDirectory(prefix='c_', dir=BUILD) as tmp_:
        tmp = Path(tmp_)
        n_ref = draw(ref, tmp / 'reference')
        row['page_counts']['reference'] = n_ref
        for key, pdf in cands.items():
            if key in row['errors']:  # a recorded ITT failure stays a failure, even if retried later
                continue
            if not pdf.is_file() or not pdf.stat().st_size:
                raise FileNotFoundError(f'Recorded success has no PDF: {pdf}')
            row['page_counts'][key] = draw(pdf, tmp / key)
            row['scores'].setdefault(key, {}).update(metrics(ref, pdf, tmp / 'reference', tmp / key,
                    row.setdefault('metric_diagnostics', {}).setdefault(key, {})))
            shutil.rmtree(tmp / key)
        shutil.rmtree(tmp / 'reference')
        show = list(range(1, min(first, n_ref) + 1))
        row['shown'] = show
        for key, pdf in {'reference': ref, **cands}.items():
            n = row['page_counts'].get(key, 0)
            if not n:
                continue
            want = [p for p in show if p <= n]
            spec = ','.join(map(str, want))
            d = tmp / f'img_{key}'
            draw(pdf, d, 180, spec)
            pngs = sorted(d.glob('page_*.png'))
            if len(pngs) != len(want):
                raise RuntimeError(f'Wrong shown-page count: {pdf}')
            paths = {}
            for p, png in zip(want, pngs):
                dst = base / key / f'page_{p:03d}.webp'
                encode(png, dst)
                paths[p] = dst.relative_to(BUILD).as_posix()
            row['pages'][key] = [paths.get(p) for p in show]
            sub = base / key / 'pages.pdf'
            run(['mutool', 'clean', '-gggz', str(pdf), str(sub), spec])
            if not sub.is_file() or not sub.stat().st_size:
                raise RuntimeError(f'No page PDF: {sub}')
            row['pdfs'][key] = sub.relative_to(BUILD).as_posix()
            shutil.rmtree(d)
    return row


def build_one(which: str, job: dict) -> dict:
    fingerprint = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
    record = BUILD / 'records' / which / f"{job['group'].replace('/', '_')}__{job['cid']}.json"
    if record.is_file():
        saved = json.loads(record.read_text())
        if saved['fingerprint'] == fingerprint:
            return saved['row']
    row = case(job['prefix'], job['group'], job['cid'], Path(job['ref']),
               {k: Path(v) for k, v in job['cands'].items()}, job['extra'], first=3)
    record.parent.mkdir(parents=True, exist_ok=True)
    part = record.with_suffix('.tmp')
    part.write_text(json.dumps({'fingerprint': fingerprint, 'row': row}, ensure_ascii=False))
    part.replace(record)
    return row


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('which', choices=['v1', 'redlines', 'wordcraft_compare', 'wordcraft_convert'])
    parser.add_argument('--limit', type=int)
    args = parser.parse_args(argv)
    jobs = json.loads((H / f'jobs_{args.which}.json').read_text())
    if args.limit:
        jobs = jobs[:args.limit]
    BUILD.mkdir(exist_ok=True)
    rows = {}
    failures = []
    with ThreadPoolExecutor(JOBS) as ex:
        pending = {ex.submit(build_one, args.which, job): i for i, job in enumerate(jobs)}
        for future in as_completed(pending):
            i = pending[future]
            try:
                rows[i] = future.result()
            except Exception as exc:
                failures.append({'index': i, 'case': jobs[i]['cid'], 'error': str(exc)})
                print(f'BUILD ERROR {jobs[i]["cid"]}: {exc}', flush=True)
                continue
            if len(rows) % 10 == 0 or len(rows) == len(jobs):
                print(f'{args.which}: {len(rows)}/{len(jobs)} complete', flush=True)
    if failures:
        (H / f'errors_{args.which}.json').write_text(json.dumps(failures, indent=1))
        raise SystemExit(f'{len(failures)} build errors; successful records retained, rerun after fixing')
    name = f'cases_{args.which}' + ('_sample' if args.limit else '') + '.json'
    (BUILD / name).write_text(json.dumps([rows[i] for i in range(len(jobs))], indent=1, ensure_ascii=False))

if __name__ == '__main__':
    main()
