"""Integration tests explicitly use real local source viewers, PDFs, and upstream scorer."""
import json
import copy
import subprocess
import shutil
from pathlib import Path
import pytest
import patch_site
import prepare
import process
pytestmark=pytest.mark.integration
H=Path(__file__).resolve().parent


def test_preview_patches_both_real_viewers_and_javascript_parses(tmp_path):
    added={'group':'v1/clean','case':'synthetic-check','pages':{'reference':['d2p_v1/check.webp']},
           'page_counts':{'reference':1},'scores':{'docxodus':{'pixel':12.5,'jaccard':None}},
           'pdfs':{},'errors':{'docxodus':'recorded failure'},'times':{},'shown':[1],
           'versions':{'reference':'Word','docxodus':'docxodus 14.2.0'}}
    for rel in ['index.html','redlines/index.html']:
        source=(patch_site.SITE/rel).read_text()
        out=patch_site.patch_html(source,[added],{})
        _,rows,tail=patch_site.split(out)
        assert len(rows)==len(patch_site.split(source)[1])+1
        assert rows[-1]['scores']['docxodus']['pixel']==12.5
        assert rows[-1]['versions']['docxodus']=='docxodus 14.2.0'
        assert 'const METRICS = ["pixel",' in tail
        assert 'tableCols' in tail and 'versionLabel' in tail
        assert 'c.errors?.[key]' in tail
        assert 'ENGINE_COLORS' in tail
        js=out.split('<script>',1)[1].split('</script>',1)[0]
        script=tmp_path/(rel.replace('/','_')+'.js');script.write_text(js)
        subprocess.run(['node','--check',str(script)],check=True,capture_output=True)


def test_wordcraft_preparation_matches_recorded_report_and_manifest():
    for phase in ['compare','convert']:
        prepare.wordcraft(phase)  # asserts per-row hashes and every published pixel mean
        jobs=json.loads((H/f'jobs_wordcraft_{phase}.json').read_text())
        assert len(jobs)==400
        assert all(j['extra']['versions']['reference']=='Word 16.115' for j in jobs)
    convert=json.loads((H/'jobs_wordcraft_convert.json').read_text())
    assert sum('pymupdf-pro-1.28.2' in j['extra']['scores'] for j in convert)==253
    assert sum('pymupdf-pro-1.28.2' in j['extra']['not_applicable'] for j in convert)==147


def source_pdfs(job):
    saved=process.build_one('v1',job)
    ref=Path(job['ref'])
    if ref.is_file():return ref,{k:Path(v) for k,v in job['cands'].items()}
    return process.BUILD/saved['pdfs']['reference'], {k:process.BUILD/saved['pdfs'][k] for k in saved['pdfs'] if k!='reference'}


def test_real_v1_case_all_pages_metrics_first_three_assets():
    job=json.loads((H/'jobs_v1.json').read_text())[0]
    ref,candidates=source_pdfs(job)
    try:
        actual=process.case('__integration',job['group'],job['cid'],ref,candidates,copy.deepcopy(job['extra']))
        assert process.build_one('v1',job)['shown']==actual['shown']
        assert actual['shown']==list(range(1,min(3,actual['page_counts']['reference'])+1))
        assert actual['scores']['jubarte']['pixel']==job['extra']['scores']['jubarte']['pixel']
        assert 'reference' in actual['pages'] and 'reference' in actual['pdfs']
        assert set(actual['scores']['jubarte'])=={'pixel','jaccard','ssim','text_boundary'}
        for key,pages in actual['pages'].items():
            assert len(pages)==len(actual['shown'])
            for p in filter(None,pages):assert (process.BUILD/p).is_file()
            assert actual['pdfs'][key].endswith('pages.pdf')
    finally:
        shutil.rmtree(process.BUILD/'__integration',ignore_errors=True)


def test_v1_preparation_retains_itt_failures_and_rejects_missing_successes():
    prepare.v1(check_files=False)
    jobs=json.loads((H/'jobs_v1.json').read_text())
    assert len(jobs)==2925
    assert sum('docxodus' in j['extra']['errors'] for j in jobs)==175
    assert sum('libreoffice' in j['extra']['errors'] for j in jobs)==1
    assert all(j['extra']['scores'][k]['pixel']==0 for j in jobs for k in j['extra']['errors'])
    invalid=[dict(jobs[0],ref=str(H/'inputs/definitely_absent.pdf'))]
    with pytest.raises(FileNotFoundError,match='required PDFs absent'):
        prepare.save_jobs('invalid',invalid)


def test_real_failed_candidates_stay_failed_and_missing_success_refuses():
    job=json.loads((H/'jobs_v1.json').read_text())[4]
    assert 'docxodus' in job['extra']['errors']
    ref,candidates=source_pdfs(job)
    try:
        actual=process.case('__integration',job['group'],job['cid'],ref,candidates,copy.deepcopy(job['extra']))
        assert actual['scores']['docxodus']=={'pixel':0.0}
        assert 'docxodus' not in actual['pages']
        bad={'nonexistent':H/'inputs/no_candidate.pdf'}
        with pytest.raises(FileNotFoundError,match='Recorded success has no PDF'):
            process.case('__integration','test','missing',ref,bad)
        with pytest.raises(RuntimeError,match='exit'):
            process.draw(H/'inputs/no_reference.pdf', H/'build/test-empty-draw')
    finally:
        shutil.rmtree(process.BUILD/'__integration',ignore_errors=True)
        shutil.rmtree(process.BUILD/'test-empty-draw',ignore_errors=True)


def test_cli_paths_and_completed_case_resume():
    patch_site.main(['--allow-partial'])
    process.main(['v1','--limit','1'])
    assert json.loads((H/'build/cases_v1_sample.json').read_text())[0]['shown']


def test_verified_wordcraft_metadata_transport_and_cache(tmp_path):
    import fetch_wordcraft
    key='wordcraft-20261014/README.md'
    destination=tmp_path/'readme.md'
    assert fetch_wordcraft.fetch((key,destination))==key
    assert fetch_wordcraft.fetch((key,destination))==key
    fetch_wordcraft.main(['metadata'])


def test_split_preparation_matches_recorded_pagefair_itt():
    prepare.redlines()  # asserts all six ITT means against measure.py's record
    jobs=json.loads((H/'jobs_redlines.json').read_text())
    assert len(jobs)==800
    assert sum('docxodus' in j['extra']['errors'] for j in jobs)==21
    assert sum('superdoc' in j['extra']['errors'] for j in jobs)==693
    aliases=json.loads((H/'redline_replacements.json').read_text())
    added=[{'group':j['group'],'case':j['cid'],'pages':{},'pdfs':{}} for j in jobs]
    original=patch_site.split((patch_site.SITE/'redlines/index.html').read_text())[1]
    merged=patch_site.merge_cases(original,added,aliases)
    assert len(aliases)==8 and len(merged)==len(original)+800-8
    assert len({(r['group'],r['case']) for r in merged})==len(merged)


def test_completed_asset_report():
    import report
    report.main(['--allow-partial'])


def test_cli_help_smoke(capsys):
    with pytest.raises(SystemExit) as exc:
        process.main(['--help'])
    assert exc.value.code==0
    assert 'wordcraft_compare' in capsys.readouterr().out


def test_upstream_identity_metrics_smoke(tmp_path):
    rows=json.loads((H/'build/cases_v1.json').read_text())
    ref=process.BUILD/rows[0]['pdfs']['reference']
    assert process.draw(ref,tmp_path/'raster',150)==len(rows[0]['shown'])
    # Upstream itself is the authority; identical real text pages must score 100.
    assert process.metrics(ref,ref,tmp_path/'raster',tmp_path/'raster')=={
        'jaccard':100.0,'ssim':100.0,'text_boundary':100.0}
