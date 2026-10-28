"""Validate completed case sets and write build/REPORT.{md,json} + an asset manifest.

python report.py [--allow-partial]
"""
from __future__ import annotations
import argparse
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from PIL import Image
import pymupdf
from process import BUILD,H
EXPECTED={'v1':2925,'redlines':800,'wordcraft_compare':400,'wordcraft_convert':400}
FIELDS=['pixel','jaccard','ssim','text_boundary']


def summarize(rows: list[dict]) -> dict:
    keys=sorted({k for r in rows for f in ('scores','errors') for k in r.get(f,{})})
    tools={}
    for key in keys:
        stats={}
        for metric in FIELDS:
            vals=[r['scores'][key][metric] for r in rows if r.get('scores',{}).get(key,{}).get(metric) is not None]
            stats[metric]={'n':len(vals),'mean':statistics.fmean(vals) if vals else None}
        tools[key]={'failures':sum(key in r.get('errors',{}) and key not in r.get('unavailable',[]) for r in rows),
                    'unavailable':sum(key in r.get('unavailable',[]) for r in rows),
                    'pdfs':sum(key in r.get('pdfs',{}) for r in rows),
                    'not_applicable':sum(key in r.get('not_applicable',[]) for r in rows),
                    'metrics':stats}
    return {'cases':len(rows),'groups':dict(sorted(Counter(r['group'] for r in rows).items())),
            'tools':tools}


def validate_set(name: str, rows: list[dict]) -> set[str]:
    assert len(rows)==EXPECTED[name],(name,len(rows))
    jobs=json.loads((H/f'jobs_{name}.json').read_text())
    jobs={(j['group'],j['cid']):j for j in jobs}
    assert len(jobs)==len(rows)
    seen=set();assets=set()
    for r in rows:
        identity=(r['group'],r['case'])
        assert identity not in seen,identity
        seen.add(identity)
        j=jobs[identity]
        assert r['shown']==list(range(1,min(3,r['page_counts']['reference'])+1)),identity
        for key,score in j['extra']['scores'].items():
            assert r['scores'][key]['pixel']==score['pixel'],(identity,key,'changed pixel')
        for key in r['errors']:
            assert key not in r['pages'] and key not in r['pdfs'],(identity,key,'failed output shown')
        for key,pages in r['pages'].items():
            assert len(pages)==len(r['shown']),(identity,key)
            if key!='reference':
                assert all(m in r['scores'][key] for m in FIELDS),(identity,key)
            for i,p in enumerate(pages,1):
                assert bool(p)==(i<=r['page_counts'][key]),(identity,key,i)
                if not p:continue
                assert not Path(p).is_absolute() and '..' not in Path(p).parts
                file=BUILD/p
                assert file.is_file() and file.stat().st_size>0,str(file)
                with Image.open(file) as im:
                    assert im.format=='WEBP' and im.width>0 and im.height>0,str(file)
                assets.add(p)
            pdf=r['pdfs'][key]
            assert pdf.endswith('/pages.pdf'),pdf
            with pymupdf.open(BUILD/pdf) as doc:
                assert len(doc)==min(len(r['shown']),r['page_counts'][key]),pdf
            assets.add(pdf)
    return assets


def main(argv: list[str] | None = None) -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-partial',action='store_true')
    args=parser.parse_args(argv)
    missing=[name for name in EXPECTED if not (BUILD/f'cases_{name}.json').is_file()]
    if missing and not args.allow_partial:raise SystemExit(f'Missing sets: {missing}')
    sets={};assets=set()
    for name in EXPECTED:
        p=BUILD/f'cases_{name}.json'
        if not p.is_file():continue
        rows=json.loads(p.read_text())
        assets.update(validate_set(name,rows));sets[name]=summarize(rows)
    total_bytes=sum(p.stat().st_size for p in BUILD.rglob('*') if p.is_file())
    asset_bytes=sum((BUILD/p).stat().st_size for p in assets)
    out={'missing_sets':missing,'build_bytes':total_bytes,'asset_bytes':asset_bytes,
         'asset_files':len(assets),'sets':sets}
    (BUILD/'REPORT.json').write_text(json.dumps(out,indent=2))
    lines=['# 2026-10-28 review-site build report','',
           ('PARTIAL: missing '+', '.join(missing)+'.' if missing else 'All four case files validated.'),'',
           f'Assets: {len(assets):,} files, {asset_bytes/2**30:.3f} GiB. Build tree at validation: {total_bytes/2**30:.3f} GiB.','',
           'Scores are percentages. Pixel is copied exactly from the recorded bench score, with recorded ITT zeros. '
           'J/SSIM/TB means use available upstream values (rounded to one decimal per case, as site_1011 does); '
           'each metric has its own n. All PDF pages are rasterized at 150 DPI; upstream ignores extra pages and '
           'skips incompatible page dimensions or text layouts. No missing metric is imputed as zero.','']
    for name,summary in sets.items():
        lines += [f'## {name} — {summary["cases"]:,} cases','', '| Group | Cases |','|---|---:|']
        lines += [f'| {group} | {n:,} |' for group,n in summary['groups'].items()]
        lines += ['', '| Engine | PDFs | Failures | Unavailable | Pixel (n) | J (n) | SSIM (n) | TB (n) |',
                  '|---|---:|---:|---:|---:|---:|---:|---:|']
        for key,t in summary['tools'].items():
            vals=[('—' if t['metrics'][m]['mean'] is None else f"{t['metrics'][m]['mean']:.4f}")+f" ({t['metrics'][m]['n']})" for m in FIELDS]
            lines.append(f'| {key} | {t["pdfs"]} | {t["failures"]} | {t["unavailable"]} | '+' | '.join(vals)+' |')
        lines += ['']
    lines += ['## Source and preview boundaries','',
              'Upstream: docxide-pdf a72d91bca065be5c96b659e5daadc3cf3ffc9fb2. '
              'Wordcraft metadata and selected PDFs are checked against the public MANIFEST.sha256.txt and score-record hashes. '
              'No live viewer edits, uploads, commits, or pushes. Eight old accept/reject cases map to the same split pairs; '
              'the other five are distinct and remain.','']
    if 'redlines' in missing:
        lines += ['The 800 split score records exist, but their candidate PDFs are absent locally and in the current '
                  '`redlines-0929` hub preset. That preset has the older 100+100 run (598 candidate PDFs across four lanes), '
                  'not the split run. Candidate sources are required to build this set without substituting different outputs.','']
    (BUILD/'REPORT.md').write_text('\n'.join(lines))
    # Manifest includes uploadable asset keys and completed case records, never temporary rasters.
    manifest=[]
    for rel in sorted(assets|{f'cases_{name}.json' for name in sets}):
        manifest.append(hashlib.sha256((BUILD/rel).read_bytes()).hexdigest()+'  '+rel)
    (BUILD/'MANIFEST.sha256.txt').write_text('\n'.join(manifest)+'\n')
    print(json.dumps({'sets':{k:v['cases'] for k,v in sets.items()},'missing':missing,
                      'asset_files':len(assets),'asset_gib':round(asset_bytes/2**30,3)}),flush=True)

if __name__=='__main__':main()
