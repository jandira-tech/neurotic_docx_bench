"""Deterministic tests: no filesystem, network, database, or wall clock dependencies."""
import copy
import pytest
from patch_site import merge_cases, once, remote, split
from prepare import wordcraft_version


def row(group='v1/clean',cid='a'):
    return {'group':group,'case':cid,'scores':{'engine':{'pixel':0}},
            'pages':{'reference':['d2p_v1/a.webp',None]},'pdfs':{'reference':'d2p_v1/pages.pdf'},
            'errors':{'engine':'recorded failure'},'versions':{'engine':'1.0'},'shown':[1,2]}


def test_remote_preserves_zero_gaps_errors_and_versions_without_mutation():
    original=row(); before=copy.deepcopy(original); out=remote(original)
    assert out['pages']['reference'][0].endswith('/d2p_v1/a.webp')
    assert out['pages']['reference'][0].startswith('https://')
    assert out['pages']['reference'][1] is None
    assert out['pdfs']['reference'].endswith('/d2p_v1/pages.pdf')
    assert out['scores']['engine']['pixel']==0
    assert out['errors']==before['errors']
    out['versions']['engine']='changed'
    assert original==before


def test_remote_accepts_case_without_pdf_links():
    r=row();r.pop('pdfs');assert remote(r)['pdfs']=={}


def test_split_roundtrip_leaves_surrounding_viewer_unchanged():
    html='HEAD\nconst DATA = [{"group":"x","case":"a"}];\nTAIL'
    head,data,tail=split(html)
    assert head=='HEAD\n' and tail==';\nTAIL'
    assert data==[{'group':'x','case':'a'}]


@pytest.mark.parametrize('text',['absent','anchor anchor'])
def test_once_refuses_changed_template(text):
    with pytest.raises(ValueError,match='Expected one anchor'):once(text,'anchor','replacement')


def test_once_replaces_single_anchor():
    assert once('a anchor b','anchor','new')=='a new b'


def test_merge_replaces_pair_alias_and_preserves_different_pairs():
    old=[row('accepted/clean','old-id'),row('rejected/clean','different')]
    added=[row('accepted/clean','new-id')]
    out=merge_cases(old,added,{'accepted/clean/old-id':'accepted/clean/new-id'})
    assert [(r['group'],r['case']) for r in out]==[('rejected/clean','different'),('accepted/clean','new-id')]
    assert out[1]['scores']['engine']['pixel']==0
    assert old[0]['case']=='old-id'


def test_merge_keeps_alias_until_replacement_set_is_available():
    old=[row('accepted/clean','old-id')]
    assert merge_cases(old,[],{'accepted/clean/old-id':'accepted/clean/new-id'})==old


def test_merge_overwrites_exact_identity_and_rejects_duplicate_new_rows():
    r=row()
    assert len(merge_cases([r],[r],{}))==1
    with pytest.raises(ValueError,match='Duplicate'):merge_cases([],[r,r],{})


@pytest.mark.parametrize(('lane','tools','expected'),[
    ('wordcraft',{'wordcraft-cli':{'version':'wordcraft-cli 0.6.1'}},'wordcraft-cli 0.6.1'),
    ('docxodus-12.6.5',{'docxodus':{'package_version':'12.6.5'}},'docxodus 12.6.5'),
    ('folio-0.60.0',{'folio-0.60.0':{'package_version':'0.60.0'}},'folio 0.60.0'),
])
def test_wordcraft_versions_follow_metadata_aliases(lane,tools,expected):
    assert wordcraft_version(lane,tools)==expected


def test_report_means_use_metric_specific_denominators_and_itt_zeros():
    from report import summarize
    a=row();a['scores']={'engine':{'pixel':0,'jaccard':None,'ssim':None,'text_boundary':None}}
    b=row(cid='b');b['scores']={'engine':{'pixel':80,'jaccard':50,'ssim':90,'text_boundary':100}};b['errors']={}
    b['pdfs']={'engine':'file.pdf'}
    summary=summarize([a,b]);engine=summary['tools']['engine']
    assert summary['cases']==2 and summary['groups']=={'v1/clean':2}
    assert engine['failures']==1 and engine['pdfs']==1
    assert engine['metrics']['pixel']=={'n':2,'mean':40}
    assert engine['metrics']['jaccard']=={'n':1,'mean':50}
    assert summarize([dict(a,scores={})])['tools']['engine']['metrics']['pixel']=={'n':0,'mean':None}
