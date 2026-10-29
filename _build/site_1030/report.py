"""Full real-file audit, reports and SHA256 manifest. Writes only this build."""
import hashlib
import json
import math
from pathlib import Path
from collections import Counter
import pymupdf
from PIL import Image
from common import FIELDS, LIST_FIELDS, OLD_KEYS, R2, split, shown_pages, summary

H=Path(__file__).resolve().parent
B=H/'build'
SITE=H.parents[1]
WORK=Path('/Users/arthrod/temp/T/renew_1028')

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    provenance=json.loads((H/'source_hashes.json').read_text())
    assert digest(SITE/'index.html')==provenance['site_sha256']
    assert digest(SITE/'redlines/index.html')==provenance['redlines_sha256']
    assert (H/'preview/index.html').read_bytes()==(SITE/'index.html').read_bytes()
    assert digest(WORK/'MANIFEST.sha256.txt')==provenance['phase1_manifest_sha256']
    for name,sha in provenance['source_hashes'].items():assert digest(H/'scorer-source'/name)==sha
    assert digest(H/'bin/page-metrics')==provenance['page_metrics_binary_sha256']
    for section in ('selection_hashes','word_manifests','word_logs','generation_failures'):
        for name,sha in provenance[section].items():
            assert digest(WORK/name if section=='selection_hashes' else Path(name))==sha
    jobs=json.loads((H/'jobs_prepared.json').read_text())
    rows=json.loads((B/'cases.json').read_text())
    assert len(jobs)==len(rows)==6000
    by_id={}
    input_hashes={}
    expected_assets=set()
    failures=[]
    for job,row in zip(jobs,rows):
        assert (job['group'],job['case'],job['column'])==(row['group'],row['case'],row['column'])
        assert row['shown']==job['shown'] and row['failure_type']==job['failure_type']
        saved=json.loads((B/'records'/f"{job['key']}.json").read_text())
        assert saved['fingerprint']==hashlib.sha256(json.dumps(job,sort_keys=True).encode()).hexdigest()
        assert saved['row']==row
        for name,sha in job['hashes'].items():
            assert name not in input_hashes or input_hashes[name]==sha
            input_hashes[name]=sha
        identity=row['group'],row['case'],row['column']
        assert identity not in by_id
        by_id[identity]=row
        key=row['column']
        scores=row['scores'].get(key,{})
        assert all(v is None or (math.isfinite(v) and 0<=v<=100.00001) for v in scores.values())
        if row['failure_type']:
            assert scores=={'pixel':0} and row['pages'][key]==[None]*len(row['shown']) and key not in row['pdfs']
            assert row['errors'][key]==job['failure']
            failures.append({'group':row['group'],'case':row['case'],'tool':row['tool'],'stage':row['failure_type'],
                             'reason':row['errors'][key],'evidence':row.get('failure_evidence',[])})
            continue
        if row['tool']!='reference':
            pixel=row['pixel_result']
            assert scores['pixel']==pixel.get('overall_score_pagefair',pixel['overall_score'])
            assert pixel['page_count_candidate']==row['page_counts'][key]
            assert pixel['page_count_oracle']==job['reference_pages']
            assert all(scores.get(m) is None or scores[m]==round(scores[m],1) for m in ('jaccard','ssim','text_boundary'))
        want=[p for p in row['shown'] if p<=row['page_counts'][key]]
        assert len(row['pages'][key])==len(row['shown'])
        for p,relative in zip(row['shown'],row['pages'][key]):
            if p not in want:
                assert relative is None
                continue
            assert relative.startswith('renew1030/') and relative.endswith(f'/page_{p:03d}.webp')
            path=B/relative
            with Image.open(path) as image:
                assert image.format=='WEBP' and min(image.size)>0
                image.verify()
            expected_assets.add(path)
        if want:
            path=B/row['pdfs'][key]
            with pymupdf.open(path) as doc:assert len(doc)==len(want)
            expected_assets.add(path)
        else:assert key not in row['pdfs']
    for name,sha in input_hashes.items():assert digest(Path(name))==sha,f'Input changed: {name}'
    head,old,tail=split((SITE/'redlines/index.html').read_text())
    new_head,new,new_tail=split((H/'preview/redlines/index.html').read_text())
    assert (head,tail)==(new_head,new_tail),'HTML outside DATA changed'
    assert len(old)==1429 and len(new)==2229
    selected={(j['group'],j['case']) for j in jobs if j['viewer']=='redlines'}
    assert len(selected)==1400
    removed=set(OLD_KEYS)|{'jubarte-rust','docxodus'}
    dropped_counts=Counter()
    untouched=0
    preview_text=(H/'preview/redlines/index.html').read_text()
    for before,after in zip(old,new[:len(old)]):
        identity=before['group'],before['case']
        assert identity==(after['group'],after['case'])
        if identity not in selected:
            assert before==after and json.dumps(before,ensure_ascii=False) in preview_text
            untouched+=1
            continue
        assert shown_pages(before)==shown_pages(after)
        for field in set(before)|set(after):
            if field in FIELDS:
                strip=lambda c:{k:v for k,v in c.get(field,{}).items() if k not in removed}
                assert strip(before)==strip(after),(identity,field)
                assert not any(k in after.get(field,{}) for k in OLD_KEYS)
            elif field in LIST_FIELDS:
                assert [k for k in before.get(field,[]) if k not in removed]==after.get(field,[])
            elif field=='dropped':
                assert set(after[field])-set(before.get(field,[]))<=set(OLD_KEYS)
                assert set(before.get(field,[]))-set(after[field])<={'jubarte-rust','docxodus'}
            else:assert before.get(field)==after.get(field),(identity,field)
        assert before['pages']['reference']==after['pages']['reference']
        for key in OLD_KEYS:
            if any(key in before.get(f,{}) for f in FIELDS):
                assert key in after['dropped'];dropped_counts[key]+=1
        for col in ('jubarte-rust','docxodus'):
            row=by_id[(*identity,col)]
            assert col not in after['dropped']
            for field in FIELDS:
                value=row.get(field,{}).get(col)
                if field=='pages':value=[R2+p if p else None for p in value]
                elif field=='pdfs' and value:value=R2+value
                assert after.get(field,{}).get(col)==value
    ar=new[len(old):]
    assert Counter(c['group'] for c in ar)=={'ar/accept_all':400,'ar/reject_all':400}
    for case in ar:
        assert set(case['pages'])=={'reference','jubarte-rust','docxodus','superdoc'}
        for col in case['pages']:
            row=by_id[(case['group'],case['case'],col)]
            assert case['shown']==row['shown']
            assert col not in case['dropped']
            for field in FIELDS:
                value=row.get(field,{}).get(col)
                if field=='pages':value=[R2+p if p else None for p in value]
                elif field=='pdfs' and value:value=R2+value
                assert case.get(field,{}).get(col)==value
    actual={p for p in (B/'renew1030').rglob('*') if p.is_file()}
    assert actual==expected_assets,'Asset inventory mismatch'
    assert not list(B.rglob('*.png')),'Temporary PNGs remain'
    groups=summary(rows)
    asset_bytes=sum(p.stat().st_size for p in actual)
    report={'redlines_cases_replaced':1400,'redlines_columns_replaced':2800,'original_cases_untouched':untouched,
            'ar_cases_added':800,'tool_rows':5200,'reference_rows':800,'groups':groups,'failures':failures,
            'failure_totals':dict(Counter(f['stage'] for f in failures)),'dropped_old_columns':dict(dropped_counts),
            'assets':len(actual),'asset_bytes':asset_bytes,'scorer':provenance,'pngs_remaining':0,
            'audit':{'all_inputs_verified':len(input_hashes),'all_checkpoints_verified':6000,'outside_DATA_unchanged':True,
                     'other_tools_and_Word_unchanged':True,'case_order_unchanged':True,'source_viewers_unchanged':True}}
    lines=['# Phase 3b — redlines and accept/reject renewal','',
           '1,400 redlines cases updated (2,800 tool rows), 29 historical cases retained byte-identical; 800 Set B cases appended (2,400 tool rows + 800 Word reference rows).',
           '', '| Group | Tool | Cases | Generation failures | Word failures | Pixel (n) | J (n) | SSIM (n) | TB (n) |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for group,tools in groups.items():
        for tool,value in tools.items():
            cells=[f'{m["mean"]:.4f} (n={m["n"]})' if m['mean'] is not None else f'— (n={m["n"]})' for m in value['metrics'].values()]
            lines.append(f'| {group} | {tool} | {value["cases"]} | {value["failures"]["generation"]} | {value["failures"]["word"]} | '+' | '.join(cells)+' |')
    lines+=['',f'Assets: {len(actual):,} files, {asset_bytes:,} bytes ({asset_bytes/2**20:.2f} MiB).',
            f'Bench main `{provenance["bench_commit"]}`, scorer `{provenance["scorer_fingerprint"]}`; deterministic numpy backend, 144 DPI, no cache, display pipeline.overall_from_result (pagefair).',
            'J/SSIM/TB: upstream a72d91bc page-metrics, verified binary SHA256, full 150-DPI mutool rasters, x100 rounded to one decimal. Nulls remain null and means exclude them with per-metric denominators. Pixel includes every ITT-zero failure.',
            'Images: 180 DPI → 2/3 Lanczos → 16 colours → lossless WebP method 4. PDFs: shown pages via mutool clean -gggz. Redlines retain existing shown selections; Set B shows first three Word pages. Missing candidate pages remain null gaps.',
            'Audit passed for all inputs, checkpoints, metrics, every WebP/PDF, exact asset inventory, original case order, other engines, Word columns, untouched rows and HTML outside DATA. Source viewers unchanged. No temporary PNGs remain.',
            'No Word invocation, upload, commit, push, GitHub post or live viewer write. Preview: http://127.0.0.1:8180/redlines/.','',
            '## Per-document failures','', '| Group | Tool | Stage | Case | Reason and evidence |','|---|---|---|---|---|']
    for failure in failures:
        clean=lambda v:str(v).replace('|','\\|').replace('\n',' ')
        lines.append('| '+' | '.join(clean(failure[k]) for k in ('group','tool','stage','case'))+' | '+clean(failure['reason'])+' '+clean(failure['evidence'])+' |')
    manifest_files=actual|{B/'cases.json'}
    (B/'MANIFEST.sha256.txt').write_text(''.join(f'{digest(p)}  {p.relative_to(B).as_posix()}\n' for p in sorted(manifest_files)))
    for _ in range(8):
        report['build_bytes']=sum(p.stat().st_size for p in B.rglob('*') if p.is_file())
        (B/'REPORT.json').write_text(json.dumps(report,indent=2)+'\n')
        (B/'REPORT.md').write_text('\n'.join(lines)+f'\n\nComplete build: {report["build_bytes"]:,} bytes ({report["build_bytes"]/2**20:.2f} MiB), including records/reports/manifest.\n')
        if sum(p.stat().st_size for p in B.rglob('*') if p.is_file())==report['build_bytes']:break
    else:raise AssertionError('Build size did not stabilize')
    print(json.dumps({k:report[k] for k in ('redlines_cases_replaced','ar_cases_added','failure_totals','assets','asset_bytes','build_bytes','audit')}))

if __name__=='__main__':main()
