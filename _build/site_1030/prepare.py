"""Verify phase-1 inputs and prepare redline/accept-reject Word-export jobs."""
from __future__ import annotations
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
from collections import Counter
from functools import cache
from pathlib import Path
import yaml

H = Path(__file__).resolve().parent
ROOT = H.parents[2]
WORK = Path.home() / 'temp/T/renew_1028'
SOURCE = H / 'scorer-source'
os.environ['BENCH_DEVICE'] = 'numpy'
sys.path.insert(0, str(SOURCE / 'src'))
from neurotic_docx_bench import content_cache, kernels
from neurotic_docx_bench.word_outputs import current_name, find_output, read_manifest
from common import VERSIONS, shown_pages, split
from prepare_helpers import manifest_hashes_text, word_output_confirmed, word_log_evidence, word_failure_reason

METRICS_SHA = '2213ff317059873a15e9605825387a6f41e1514a21a1c9c7e4b7187a7f37925c'


@cache
def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def manifest_hashes(path: Path) -> dict[str, str]:
    return manifest_hashes_text(path.read_text())


def failure_details(folder: Path, original: str, kind: str) -> tuple[str, list[dict]]:
    """Keep the manifest error and exact per-document driver evidence."""
    lines = read_manifest(folder)
    renamed = current_name(lines, original)
    tool = folder.relative_to(WORK / 'out').parts[1]
    action = 'redline' if kind == 'pdf' else kind.removesuffix('_all')
    evidence = []
    for suffix in ('log', 'console'):
        log = WORK / 'logs' / f'{tool}_{action}.{suffix}'
        if not log.is_file():
            continue
        evidence.extend(word_log_evidence(log.read_text(), original, str(log)))
    return word_failure_reason(lines, original, renamed, kind, evidence), evidence


def main() -> None:
    if 'ALLDONE' not in (WORK / 'logs_word_master.txt').read_text():
        raise SystemExit('SuperDoc Word batches have not finished')
    phase_hashes = manifest_hashes(WORK / 'MANIFEST.sha256.txt')
    provenance_hashes = manifest_hashes(WORK / 'PROVENANCE.sha256.txt')
    for name in ('case-keys.json', 'jobs.json', 'REPORT.md', 'PLAN.md', 'MANIFEST.sha256.txt',
                 'provenance/tool-versions.json'):
        if sha(WORK / name) != provenance_hashes[name]:
            raise ValueError(f'Phase-1 provenance changed: {name}')
    jobs = [j for j in json.loads((WORK / 'jobs.json').read_text()) if j['viewer'] in ('redlines', 'ar')]
    keys = json.loads((WORK / 'case-keys.json').read_text())
    cases = {(c['group'], c['case']): c for c in split((ROOT / 'site/redlines/index.html').read_text())[1]}
    dpi = yaml.safe_load((SOURCE / 'bench.yaml').read_text())['scoring']['dpi']
    provenance = {
        'bench_commit': (H / 'scorer_commit.txt').read_text().strip(),
        'bench_ref': 'origin/main (local main branch predates scorer PR #98)',
        'scorer_fingerprint': content_cache.scorer_fingerprint(),
        'scorer_backend': kernels.backend_id(), 'raster_engine': content_cache.raster_engine(),
        'pixel_dpi': dpi, 'pixel_cache': None,
        'pixel_aggregate': 'pipeline.overall_from_result (overall_score_pagefair), as docx_to_pdf._overall_map',
        'page_metrics_commit': subprocess.check_output(['git', '-C', str(Path.home() / 'temp/T/docxide-pdf'), 'rev-parse', 'HEAD'], text=True).strip(),
        'page_metrics_binary_sha256': sha(H / 'bin/page-metrics'), 'page_metrics_dpi': 150,
        'site_sha256': sha(ROOT / 'site/index.html'),
        'redlines_sha256': sha(ROOT / 'site/redlines/index.html'),
        'phase1_manifest_sha256': sha(WORK / 'MANIFEST.sha256.txt'),
        'phase1_provenance_sha256': sha(WORK / 'PROVENANCE.sha256.txt'),
        'source_hashes': {str(p.relative_to(SOURCE)): sha(p) for p in sorted((SOURCE / 'src/neurotic_docx_bench').glob('*.py'))},
        'selection_hashes': {n: sha(WORK / n) for n in ('jobs.json', 'case-keys.json', 'REPORT.md', 'PLAN.md')},
        'word_output_resolution': 'neurotic_docx_bench.word_outputs.find_output; manifest-confirmed outputs only',
    }
    assert provenance['scorer_fingerprint'] == '5e481477e2196f6b', provenance
    assert provenance['scorer_backend'] == 'numpy', provenance
    assert provenance['page_metrics_binary_sha256'] == METRICS_SHA
    assert provenance['page_metrics_commit'].startswith('a72d91bc')
    prepared, refs, failures = [], [], []
    folder_cache = {}
    def verified(path: Path) -> str:
        actual = sha(path)
        if phase_hashes[path.relative_to(WORK).as_posix()] != actual:
            raise ValueError(f'Phase-1 input hash mismatch: {path}')
        return actual
    for job in jobs:
        if any(keys[job['key']].get(k) != v for k, v in job.items()):
            raise ValueError(f'case-keys join changed: {job["key"]}')
        ref = Path(job['reference']['path'])
        ref_hash = verified(ref)
        input_hashes = {v['path']: verified(Path(v['path'])) for v in job['inputs'].values()}
        if job['viewer'] == 'redlines':
            old = cases[job['group'], job['case']]
            show, n_ref = shown_pages(old), old['page_counts']['reference']
            if show != job['shown'] or n_ref != job['reference_pages']:
                raise ValueError(f'Viewer/phase1 page-selection disagreement: {job["key"]}')
            group = job['group']
        else:
            import pymupdf
            with pymupdf.open(ref) as doc:
                n_ref = len(doc)
            show = list(range(1, min(n_ref, 3) + 1))
            group = 'ar/' + job['action']
        shared = {'group': group, 'case': job['case'], 'phase1_key': job['key'],
                  'viewer': job['viewer'], 'shown': show, 'reference_pages': n_ref,
                  'ref': str(ref), 'failure': None, 'failure_type': None,
                  'hashes': {str(ref): ref_hash, **input_hashes},
                  'provenance': {k: v for k, v in provenance.items() if k != 'source_hashes'},
                  'reference': job['reference'], 'state': job.get('state'), 'pool': job.get('pool')}
        if job['viewer'] == 'ar':
            refs.append({**shared, 'tool': 'reference', 'column': 'reference',
                         'version': VERSIONS['reference'], 'pdf': str(ref),
                         'key': job['key'] + '__reference'})
        for tool in job['tools']:
            original = Path(job['outputs'][tool])
            folder = original.parent.parent / 'pdf'
            if folder not in folder_cache:
                gen = folder.parent / 'generate_failures.json'
                folder_cache[folder] = ({x['case']: x['error'] for x in json.loads(gen.read_text())},
                                        read_manifest(folder), gen)
            gen_failures, output_manifest, gen_path = folder_cache[folder]
            row = {**shared, 'hashes': shared['hashes'].copy(), 'tool': tool,
                   'column': 'jubarte-rust' if tool == 'jubarte' else tool,
                   'version': VERSIONS[tool], 'key': job['key'] + '__' + tool,
                   'pdf': None, 'word_manifest': str(folder / 'manifest.jsonl'),
                   'word_manifest_sha256': sha(folder / 'manifest.jsonl'),
                   'generation_failures_sha256': sha(gen_path)}
            if job['key'] in gen_failures:
                row.update(failure=gen_failures[job['key']], failure_type='generation',
                           failure_evidence=[{'path': str(gen_path), 'case': job['key']}])
            else:
                row['hashes'][str(original)] = verified(original)
                kind = 'pdf' if job['viewer'] == 'redlines' else job['action']
                suffix = '' if kind == 'pdf' else ('_accepted_tracking' if kind == 'accept_all' else '_rejected_tracking')
                pdf = find_output(folder, original.name, kind=kind, ext='.pdf', suffix=suffix)
                # The resolver's legacy filename fallback cannot turn absent manifest
                # exports into success; phase 3 uses only this completed Word run.
                confirmed = word_output_confirmed(pdf, output_manifest, original.name,
                                                   current_name(output_manifest, original.name), kind)
                if confirmed:
                    row['pdf'] = str(pdf)
                    row['hashes'][str(pdf)] = sha(pdf)
                    if job['viewer'] == 'ar':
                        accepted = find_output(folder, original.name, kind=kind, ext='.docx', suffix=suffix)
                        if not word_output_confirmed(accepted, output_manifest, original.name,
                                                     current_name(output_manifest, original.name), kind):
                            raise ValueError(f'Word success missing manifest-confirmed accepted/rejected DOCX: {original}')
                        row['word_action_docx'] = str(accepted)
                        row['hashes'][str(accepted)] = sha(accepted)
                else:
                    reason, evidence = failure_details(folder, original.name, kind)
                    row.update(failure=reason, failure_type='word', failure_evidence=evidence)
            prepared.append(row)
            if row['failure']:
                failures.append({k: row[k] for k in ('key', 'group', 'case', 'tool', 'column', 'failure_type', 'failure', 'failure_evidence')})
    redlines = [j for j in prepared if j['viewer'] == 'redlines']
    ar = [j for j in prepared if j['viewer'] == 'ar']
    assert len(redlines) == 2800 and len(ar) == 2400 and len(refs) == 800
    assert len({j['key'] for j in prepared + refs}) == 6000
    assert sum(j['failure_type'] == 'generation' for j in prepared) == 693
    provenance['generation_failures'] = {str(gen_path): sha(gen_path) for _, _, gen_path in folder_cache.values()}
    provenance['word_manifests'] = {str(p / 'manifest.jsonl'): sha(p / 'manifest.jsonl') for p in folder_cache}
    provenance['word_logs'] = {str(p): sha(p) for p in sorted((WORK / 'logs').glob('*')) if p.suffix in ('.log', '.console')}
    (H / 'source_hashes.json').write_text(json.dumps(provenance, indent=2) + '\n')
    for name, data in [('jobs_redlines', redlines), ('jobs_ar', ar), ('jobs_references', refs),
                       ('jobs_prepared', refs + prepared), ('failures_prepared', failures)]:
        (H / (name + '.json')).write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n')
    runtime = {'python': sys.version, 'platform': platform.platform(),
               'packages': {n: importlib.metadata.version(n) for n in ('numpy', 'scipy', 'scikit-image', 'Pillow', 'PyMuPDF', 'PyYAML')},
               'mutool': subprocess.run(['mutool', '-v'], capture_output=True, text=True).stderr.strip(),
               'node': subprocess.check_output(['node', '--version'], text=True).strip()}
    (H / 'runtime.json').write_text(json.dumps(runtime, indent=2) + '\n')
    print(f'{len(redlines)} redline + {len(ar)} AR + {len(refs)} reference jobs; scorer={provenance["scorer_fingerprint"]}')
    print('Failure counts:', Counter((j['viewer'], j['tool'], j['failure_type']) for j in prepared if j['failure']))


if __name__ == '__main__':
    main()
