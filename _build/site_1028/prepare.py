"""Prepare immutable-source jobs; only writes inside this renewal directory."""
from __future__ import annotations
import argparse
import csv
import statistics
import hashlib
import json
from pathlib import Path
H = Path(__file__).resolve().parent
BENCH = H.parents[2]
INPUTS = H / 'inputs'


def load(path: Path):
    return json.loads(path.read_text())


def save_jobs(which: str, jobs: list[dict], check_files: bool = True) -> None:
    ids = [(j['group'], j['cid']) for j in jobs]
    assert len(ids) == len(set(ids)), f'Duplicate identities in {which}'
    missing = [str(p) for j in jobs for p in [Path(j['ref']), *[Path(v) for k,v in j['cands'].items() if k not in j['extra']['errors']]] if not p.is_file()]
    if check_files and missing:
        raise FileNotFoundError(f'{len(missing)} required PDFs absent; first: {missing[:5]}')
    (H / f'jobs_{which}.json').write_text(json.dumps(jobs, indent=1))
    print(f'{which}: {len(jobs)} jobs', flush=True)


def v1(check_files: bool = True) -> None:
    full = load(BENCH / 'results/docx_to_pdf_v1_89/full.json')
    lo = load(BENCH / 'results/docx_to_pdf_v1_89/soffice_full.json')
    assert full['stems'] == lo['stems'] and len(full['stems']) == 2925
    tools = {**full['tools'], 'libreoffice': lo['tools']['soffice']}
    fails = {k: {f['doc']: f['error'] for f in v['generate_failures']} for k,v in tools.items()}
    root = Path.home() / 'temp/T/ndb-v1/out/dx89'
    paths = {'docxodus': root/'full_work/docxodus/candidate', 'jubarte': root/'full_work/jubarte/candidate',
             'libreoffice': root/'soffice_work/soffice/candidate'}
    versions = {'reference': 'Word', 'jubarte': 'jubarte 0.14.0', 'libreoffice': 'LibreOffice 26.8.1.1', 'docxodus': 'docxodus 14.2.0'}
    jobs = []
    for stem in full['stems']:
        state, name = stem.split('__', 1)
        # fixtures get uses the corpus/word-relative layout
        ref = INPUTS / 'v1' / state / 'pdf' / f'{name}.pdf'
        jobs.append({'prefix':'d2p_v1', 'group':f'v1/{state}', 'cid':name.split('_')[0],
                     'ref':str(ref), 'cands':{k:str(p/f'{stem}.pdf') for k,p in paths.items()},
                     'extra':{'stem':stem, 'reference_app':'Microsoft Word', 'versions':versions,
                              'scores':{k:{'pixel':v['per_doc'][stem]} for k,v in tools.items()},
                              'times':{k:v['convert_seconds'][stem] for k,v in tools.items() if stem in v.get('convert_seconds',{})},
                              'errors':{k:f[stem] for k,f in fails.items() if stem in f}, 'set':'v1',
                              'dropped':[]}})
    save_jobs('v1', jobs, check_files=check_files)

def redlines() -> None:
    source=BENCH/'results/redlines_0929_split'
    pairs=list(csv.DictReader(open(source/'pool_pairs.csv')))
    assert len(pairs)==800
    scores={(r['tool'],r['action']):r for r in [json.loads(line) for line in (source/'scores.jsonl').read_text().splitlines()]}
    versions={'reference':"Word compare, accepted/rejected by Word", **load(source/'versions.json')}
    versions.pop('word-identity',None)
    engines=['jubarte-rust','docxodus','superdoc']
    jobs=[]
    for r in pairs:
        action=r['action'];key=r['key'];cid=key.rsplit('_',1)[1]
        suffix='_accepted_tracking' if action=='accept_all' else '_rejected_tracking'
        group=('accepted' if action=='accept_all' else 'rejected')+'/'+r['state']
        pixel={};errors={};cands={}
        for tool in engines:
            d=scores[(tool,action)]
            result=d['rows'].get(key.lower(),d['rows'].get(key))
            if result:
                # The split measure.py uses pipeline.overall_from_result: pagefair if present.
                pixel[tool]={'pixel':result.get('overall_score_pagefair',result['overall_score'])}
            else:
                assert key in d['missing'] or key.lower() in d['missing'],(tool,key)
                pixel[tool]={'pixel':0.0};errors[tool]='Recorded split-run failure: no scored Word PDF'
            cands[tool]=str(INPUTS/'redlines_split'/tool/action/'by_word'/f'{key}_{tool}{suffix}.pdf')
        jobs.append({'prefix':'redlines_0929ar','group':group,'cid':cid,
                     'ref':str(INPUTS/'v1_ar'/action/'pdf'/f'{key}.pdf'),'cands':cands,
                     'extra':{'pair':key,'base':r['base'],'next':r['next'],'state':r['state'],
                              'scores':pixel,'errors':errors,'versions':versions,'times':{},
                              'reference_app':'Microsoft Word','set':'redlines','dropped':[]}})
    for tool in engines:
        for action in ['accept_all','reject_all']:
            group='accepted/' if action=='accept_all' else 'rejected/'
            vals=[j['extra']['scores'][tool]['pixel'] for j in jobs if j['group'].startswith(group)]
            assert len(vals)==400 and abs(statistics.fmean(vals)-scores[(tool,action)]['itt_mean'])<1e-8
    save_jobs('redlines',jobs,check_files=False)


def wordcraft_version(tool: str, tools: dict) -> str:
    key = {'wordcraft':'wordcraft-cli', 'docxodus-12.6.5':'docxodus'}.get(tool, tool)
    info = tools[key]
    return info.get('version') or f"{tool.split('-')[0]} {info['package_version']}"


def wordcraft(phase: str) -> None:
    meta = H / 'metadata'
    tools = load(meta/'tools.json')
    report = load(meta/'REPORT.json')
    manifest = {line.split(None,1)[1].removeprefix('wordcraft-20261014/'):line.split()[0]
                for line in (H/'wordcraft_MANIFEST.sha256.txt').read_text().splitlines()}
    rows = list(csv.DictReader(open(meta/('comparisons.csv' if phase=='compare' else 'conversions.csv'))))
    assert len(rows)==400
    engines = sorted({k.split('/')[1] for k in manifest if k.startswith(phase+'/')} - {'oracle','oracle_docx'})
    scores = {tool:load(meta/phase/tool/'scores.json') for tool in engines if (meta/phase/tool/'scores.json').is_file()}
    versions = {'reference':f"Word {tools['word']['version']}"} | {tool:wordcraft_version(tool,tools) for tool in engines}
    jobs=[]
    for r in rows:
        cid=r['id'] if phase=='compare' else r['stem']
        refrel=f'{phase}/oracle/{cid}.pdf'
        assert refrel in manifest, refrel
        cands={}
        pixel={}
        errors={}
        not_applicable=[]
        for tool in engines:
            d=scores.get(tool)
            rel=f'{phase}/{tool}/pdf/{cid}.pdf'
            cands[tool]=str(INPUTS/'wordcraft'/rel)
            if d is None:
                errors[tool]='No published PDF or score; superseded lane (see cohort REPORT.md)'
                continue
            result=d['rows'].get(cid)
            if result:
                assert result['oracle_sha256']==manifest[refrel], (phase,tool,cid,'oracle mismatch')
                assert result['candidate_sha256']==manifest[rel], (phase,tool,cid,'candidate mismatch')
                pixel[tool]={'pixel':result['overall_score']}
            elif cid in d['failures']:
                errors[tool]=str(d['failures'][cid])
                pixel[tool]={'pixel':0.0}
            else:
                # PyMuPDF Pro was measured only on the <=3-page subset, not on all 400.
                assert d['requested']<400, (phase,tool,cid)
                not_applicable.append(tool)
                cands.pop(tool)
        jobs.append({'prefix':'wordcraft1014','group':f'wordcraft1014/{phase}','cid':cid,
                     'ref':str(INPUTS/'wordcraft'/refrel),'cands':cands,
                     'extra':{'stem':r.get('stem',r.get('key')), 'pair':r.get('key'),
                              'state':r['state'], 'sets':r.get('sets',''),
                              'scores':pixel,'errors':errors,'versions':versions,'times':{},
                              'reference_app':'Microsoft Word','set':f'wordcraft_{phase}',
                              'not_applicable':not_applicable,'unavailable':[tool for tool in engines if tool not in scores],
                              'dropped':not_applicable}})
    for tool,d in scores.items():
        vals=[j['extra']['scores'][tool]['pixel'] for j in jobs if tool in j['extra']['scores']]
        assert len(vals)==d['requested'], (tool,len(vals),d['requested'])
        published=report['summary'][phase][tool]['v1_mean']
        assert abs(statistics.fmean(vals)-published)<1e-8, (tool,published,statistics.fmean(vals))
    save_jobs(f'wordcraft_{phase}',jobs,check_files=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('which', choices=['v1','redlines','wordcraft_compare','wordcraft_convert'])
    args = parser.parse_args()
    {'v1':v1,'redlines':redlines,'wordcraft_compare':lambda:wordcraft('compare'),'wordcraft_convert':lambda:wordcraft('convert')}[args.which]()
