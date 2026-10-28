"""Pin input hashes and prepare only phase-3a d2p jobs. No generation/network."""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
import yaml
from common import shown_pages, split

H = Path(__file__).resolve().parent
ROOT = H.parents[2]
WORK = Path.home() / 'temp/T/renew_1028'
SOURCE = H / 'scorer-source'
sys.path.insert(0, str(SOURCE / 'src'))
from neurotic_docx_bench import content_cache, kernels


def sha(path: Path) -> str:
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def main() -> None:
    jobs = [j for j in json.loads((WORK / 'jobs.json').read_text()) if j['viewer'] == 'd2p']
    html = (ROOT / 'site/index.html').read_text()
    cases = {(c['group'], c['case']): c for c in split(html)[1]}
    manifest = {line[66:]: line[:64] for line in (WORK / 'MANIFEST.sha256.txt').read_text().splitlines()}
    failures = json.loads((WORK / 'out/d2p/jubarte/generate_failures.json').read_text())
    assert not failures, 'Inspect the phase-1 failure schema before preparing a changed generation set'
    dpi = yaml.safe_load((SOURCE / 'bench.yaml').read_text())['scoring']['dpi']
    provenance = {
        'bench_commit': (H / 'scorer_commit.txt').read_text().strip(),
        'scorer_fingerprint': content_cache.scorer_fingerprint(),
        'scorer_backend': kernels.backend_id(), 'raster_engine': content_cache.raster_engine(),
        'pixel_dpi': dpi, 'pixel_aggregate': 'pipeline.overall_from_result (overall_score_pagefair), as docx_to_pdf._overall_map',
        'page_metrics_commit': subprocess.check_output(['git', '-C', str(Path.home() / 'temp/T/docxide-pdf'), 'rev-parse', 'HEAD'], text=True).strip(),
        'page_metrics_binary_sha256': sha(H / 'bin/page-metrics'),
        'page_metrics_dpi': 150,
        'site_sha256': sha(ROOT / 'site/index.html'),
        'redlines_sha256': sha(ROOT / 'site/redlines/index.html'),
        'phase1_manifest_sha256': sha(WORK / 'MANIFEST.sha256.txt'),
        'source_hashes': {str(p.relative_to(SOURCE)): sha(p) for p in sorted((SOURCE / 'src/neurotic_docx_bench').glob('*.py'))},
    }
    assert provenance['page_metrics_commit'].startswith('a72d91bc')
    (H / 'source_hashes.json').write_text(json.dumps(provenance, indent=2) + '\n')
    prepared = []
    for job in jobs:
        case = cases[job['group'], job['case']]
        ref = Path(job['reference']['path'])
        pdf = Path(job['outputs']['jubarte'])
        hashes = {}
        for path in (ref, pdf):
            actual = sha(path)
            assert manifest[path.relative_to(WORK).as_posix()] == actual, path
            hashes[str(path)] = actual
        prepared.append({
            'key': job['key'], 'group': job['group'], 'case': job['case'],
            'ref': str(ref), 'pdf': str(pdf), 'hashes': hashes,
            'shown': shown_pages(case), 'reference_pages': case['page_counts']['reference'],
            'columns': job['columns'], 'failure': None,
            'provenance': {k: v for k, v in provenance.items() if k != 'source_hashes'},
        })
    assert len(prepared) == 1276
    (H / 'jobs_d2p_jubarte.json').write_text(json.dumps(prepared, indent=1) + '\n')
    print(f'{len(prepared)} jobs; scorer={provenance["scorer_fingerprint"]}; backend={provenance["scorer_backend"]}; dpi={dpi}')


if __name__ == '__main__':
    main()
