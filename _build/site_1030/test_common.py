"""Pure helper tests: no network, disk, database or clock dependencies."""
import copy
import json
import pytest
from common import FIELDS, OLD_KEYS, R2, VERSIONS, merge_ar, patch_html, replace_case, shown_pages, split, summary


def original(name='one'):
    return dict(group='redlines/state', case=name, shown=[1],
                pages={'reference':['word/page_001.webp'],'jubarte-rust':['stale.webp'],'other':['keep']},
                page_counts={'reference':1}, scores={'other':{'pixel':7}},
                versions={'other':'unchanged'}, pdfs={'jubarte-rust':'stale.pdf'}, dropped=['jubarte-rust'], metadata=['keep'])


def row(tool='jubarte', name='one', failure=None):
    col = 'jubarte-rust' if tool=='jubarte' else tool
    return dict(group='redlines/state', case=name, tool=tool, column=col, shown=[1],
                pages={col:[None if failure else 'renew1030/redlines/page_001.webp']},
                pdfs={} if failure else {col:'renew1030/redlines/pages.pdf'},
                scores={col:{'pixel':0} if failure else {'pixel':80,'jaccard':None,'ssim':90,'text_boundary':70}},
                versions={col:VERSIONS[tool]}, page_counts={col:0 if failure else 1},
                errors={col:failure} if failure else {}, times={}, failure_type='word' if failure else None)


def html(cases):
    return 'immutable head const DATA = '+json.dumps(cases,ensure_ascii=False)+';\nimmutable tail'


def test_two_tools_replace_only_their_maps_and_remove_all_stale_lanes():
    old=original(); old['errors']={'jubarte-rust':'stale','other':'keep'}
    for f in FIELDS:
        old.setdefault(f,{}).update({k:'stale' for k in OLD_KEYS})
    before=copy.deepcopy(old)
    new=replace_case(old,[row(),row('docxodus')])
    assert old==before
    assert new['pages']['reference']==old['pages']['reference']
    assert new['pages']['jubarte-rust']==[R2+'renew1030/redlines/page_001.webp']
    assert new['pdfs']['docxodus']==R2+'renew1030/redlines/pages.pdf'
    assert new['versions']['jubarte-rust']==VERSIONS['jubarte']
    assert 'jubarte-rust' not in new['errors'] and 'jubarte-rust' not in new['dropped']
    assert set(OLD_KEYS)<=set(new['dropped'])
    for f in FIELDS:
        assert all(k not in new.get(f,{}) for k in OLD_KEYS)
        assert new.get(f,{}).get('other')==old.get(f,{}).get('other')
    assert new['metadata']==old['metadata']


def test_failure_clears_candidate_assets_and_remains_visible_itt_zero():
    new=replace_case(original(),[row(failure='Word declined repair')])
    assert new['scores']['jubarte-rust']=={'pixel':0}
    assert new['pages']['jubarte-rust']==[None]
    assert 'jubarte-rust' not in new['pdfs']
    assert new['errors']['jubarte-rust']=='Word declined repair'
    assert 'jubarte-rust' not in new['dropped']


def test_wordcraft_list_availability_clears_only_superseded_tools():
    old=original();old['unavailable']=['jubarte-rust','docxodus-12.6.5','stemma-0.5.0']
    old['not_applicable']=['docxodus','other']
    new=replace_case(old,[row(),row('docxodus')])
    assert new['unavailable']==['stemma-0.5.0']
    assert new['not_applicable']==['other']


def test_shown_implicit_first_three_and_empty_or_sparse():
    c=original(); c.pop('shown'); assert shown_pages(c)==[1]
    c['shown']=[1,7]; c['pages']['reference']=['x/page_001.webp','x/page_007.webp']; assert shown_pages(c)==[1,7]
    c['shown']=[]; c['pages']['reference']=[]; assert shown_pages(c)==[]


@pytest.mark.parametrize('change',['length','number','duplicate','negative'])
def test_bad_page_selections_refused(change):
    c=original()
    if change=='length':c['shown']=[1,2]
    elif change=='number':c['pages']['reference']=['x/page_002.webp']
    elif change=='duplicate':c['shown']=[1,1];c['pages']['reference']=['a','a']
    else:c['shown']=[-1]
    with pytest.raises(ValueError):shown_pages(c)


@pytest.mark.parametrize('change',['identity','shown','duplicate_tool'])
def test_replace_refuses_ambiguous_rows(change):
    r=row(); rows=[r]
    if change=='identity':r['case']='wrong'
    elif change=='shown':r['shown']=[2]
    else:rows.append(row())
    with pytest.raises(ValueError):replace_case(original(),rows)


def test_patch_appends_ar_preserves_envelope_order_and_untouched_row_bytes():
    before=html([original(),original('untouched')]);added={'group':'ar/accept_all','case':'ar'}
    after=patch_html(before,[row(),row('docxodus')],[added])
    a,b,c=split(after);x,y,z=split(before)
    assert (a,c)==(x,z) and b[1]==y[1] and b[-1]==added
    assert json.dumps(y[1],ensure_ascii=False) in after


@pytest.mark.parametrize('change',['missing','noncanonical','duplicate','collision'])
def test_patch_refuses_missing_or_duplicate_inputs(change):
    before=html([original()]);rows=[row()];added=[]
    if change=='missing':rows[0]['case']='missing'
    elif change=='noncanonical':before=before.replace('"group": ','"group":')
    elif change=='duplicate':rows*=2
    else:added=[original()]
    with pytest.raises(ValueError):patch_html(before,rows,added)


def test_merge_ar_sets_versions_assets_and_drops_unmeasured_tools():
    rows=[]
    for tool in ('reference','jubarte','docxodus','superdoc'):
        r=row(tool);r['group']='ar/accept_all';rows.append(r)
    result=merge_ar(rows,['reference','jubarte-rust','docxodus','superdoc','other'])
    assert len(result)==1
    assert result[0]['dropped']==['other']
    assert result[0]['versions']['reference']==VERSIONS['reference']
    assert result[0]['pages']['reference'][0].startswith(R2)
    assert result[0]['shown']==[1]
    with pytest.raises(ValueError):merge_ar(rows+rows[:1],[])
    with pytest.raises(ValueError):merge_ar(rows[:-1],[])


def test_summary_per_group_tool_null_denominators_and_failure_stages():
    a=row();b=row(failure='bad');b['failure_type']='generation'
    c=row('docxodus',failure='Word');s=summary([a,b,c,row('reference')])['redlines/state']
    assert s['jubarte']['metrics']['pixel']=={'mean':40,'n':2}
    assert s['jubarte']['metrics']['jaccard']=={'mean':None,'n':0}
    assert s['jubarte']['metrics']['ssim']=={'mean':90,'n':1}
    assert s['jubarte']['failures']=={'generation':1,'word':0}
    assert s['docxodus']['failures']=={'generation':0,'word':1}
