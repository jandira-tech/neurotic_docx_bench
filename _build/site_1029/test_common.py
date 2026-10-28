"""Deterministic unit tests; no filesystem, network, clock or generic mocks."""
import copy
import json
import pytest
from common import FIELDS, KEY, OLD_KEYS, R2, VERSION, patch_html, replace_case, shown_pages, split, summary


def original(group='cases', name='fixture'):
    return {'group': group, 'case': name,
            'pages': {'reference': ['old/reference/page_001.webp'], KEY: ['old/jubarte.webp'], 'other': ['old/other.webp']},
            'page_counts': {'reference': 1, KEY: 9, 'other': 2},
            'scores': {KEY: {'pixel': 99}, 'other': {'jaccard': 42}},
            'times': {KEY: 123, 'other': 7}, 'errors': {KEY: 'stale'},
            'pdfs': {KEY: 'stale.pdf', 'reference': 'word.pdf'},
            'versions': {KEY: 'old version', 'other': 'keep'},
            'dropped': [KEY, 'unrelated'], 'metadata': ['preserve', 'exactly']}


def replacement():
    return {'group': 'cases', 'case': 'fixture', 'shown': [1],
            'pages': {KEY: ['renew1028/d2p/cases/fixture/jubarte/page_001.webp']},
            'page_counts': {KEY: 1}, 'scores': {KEY: {'pixel': 88, 'jaccard': 77, 'ssim': 90, 'text_boundary': None}},
            'times': {}, 'errors': {}, 'pdfs': {KEY: 'renew1028/d2p/cases/fixture/jubarte/pages.pdf'},
            'versions': {KEY: VERSION}, 'metric_diagnostics': {KEY: {'scored_pages': 1}}}


def html(cases):
    return '<html>\n<script>\nconst DATA = ' + json.dumps(cases, ensure_ascii=False) + ';\nIMMUTABLE TAIL\n</script>'


def test_replacement_preserves_other_engines_and_metadata():
    old, row = original(), replacement()
    before = copy.deepcopy(old)
    result = replace_case(old, row)
    assert old == before
    assert result['versions'][KEY] == VERSION
    assert result['pages'][KEY] == [R2 + row['pages'][KEY][0]]
    assert result['pdfs'][KEY] == R2 + row['pdfs'][KEY]
    assert KEY not in result['times'] and KEY not in result['errors']
    assert KEY not in result['dropped'] and 'unrelated' in result['dropped']
    for field in FIELDS:
        assert {k: v for k, v in result.get(field, {}).items() if k != KEY} == {k: v for k, v in old.get(field, {}).items() if k != KEY}
    assert result['metadata'] == old['metadata']
    for field in ('pages', 'page_counts', 'scores', 'pdfs', 'versions'):
        assert list(result[field]) == list(old[field])


def test_wordcraft_removes_every_versioned_lane_and_marks_dropped():
    old = original()
    for field in FIELDS:
        old.setdefault(field, {}).update({key: f'{field} stale' for key in OLD_KEYS})
    new = replace_case(old, replacement())
    for field in FIELDS:
        assert all(key not in new.get(field, {}) for key in OLD_KEYS)
    assert set(OLD_KEYS) <= set(new['dropped'])


def test_failure_clears_stale_success_and_stays_visible_with_itt_zero():
    row = replacement()
    row.update(pages={KEY: [None]}, pdfs={}, page_counts={KEY: 0}, scores={KEY: {'pixel': 0}}, errors={KEY: 'conversion failed'})
    new = replace_case(original(), row)
    assert new['pages'][KEY] == [None]
    assert KEY not in new['pdfs']
    assert new['scores'][KEY] == {'pixel': 0}
    assert new['errors'][KEY] == 'conversion failed'
    assert KEY not in new['dropped']


def test_existing_sparse_shown_and_first_three():
    old = original()
    old['shown'] = [1, 7]
    old['pages']['reference'] = ['old/page_001.webp', 'old/page_007.webp']
    assert shown_pages(old) == [1, 7]
    old.pop('shown')
    old['page_counts']['reference'] = 8
    old['pages']['reference'] = [f'old/page_{i:03d}.webp' for i in (1, 2, 3)]
    assert shown_pages(old) == [1, 2, 3]


@pytest.mark.parametrize('change', ['length', 'number'])
def test_page_selection_refuses_misalignment(change):
    old = original()
    if change == 'length':
        old['shown'] = [1, 2]
    else:
        old['pages']['reference'] = ['old/page_002.webp']
    with pytest.raises(ValueError):
        shown_pages(old)


@pytest.mark.parametrize('change', ['identity', 'shown'])
def test_replacement_refuses_identity_or_shown_drift(change):
    row = replacement()
    row['case' if change == 'identity' else 'shown'] = 'wrong' if change == 'identity' else [2]
    with pytest.raises(ValueError):
        replace_case(original(), row)


def test_patch_keeps_all_other_rows_and_envelope_byte_identical():
    cases = [original(), original('v1/clean', 'current'), original('untouched', 'different')]
    before = html(cases)
    after = patch_html(before, [replacement()])
    old_head, _, old_tail = split(before)
    new_head, output, new_tail = split(after)
    assert (new_head, new_tail) == (old_head, old_tail)
    assert output[1:] == cases[1:]
    assert all(json.dumps(c, ensure_ascii=False) in after for c in cases[1:])


@pytest.mark.parametrize('change', ['duplicate', 'missing', 'noncanonical'])
def test_patch_refuses_incomplete_or_ambiguous_input(change):
    rows, before = [replacement()], html([original()])
    if change == 'duplicate':
        rows *= 2
    elif change == 'missing':
        rows[0]['case'] = 'absent'
    else:
        before = before.replace('"group": "cases"', '"group":"cases"')
    with pytest.raises(ValueError):
        patch_html(before, rows)


def test_means_include_itt_zero_and_preserve_per_metric_denominators():
    good, failed = replacement(), replacement()
    failed.update(scores={KEY: {'pixel': 0}}, errors={KEY: 'failed'})
    groups = summary([good, failed])
    assert groups['cases']['cases'] == 2
    assert groups['cases']['failures'] == 1
    assert groups['cases']['metrics']['pixel'] == {'mean': 44, 'n': 2}
    assert groups['cases']['metrics']['jaccard'] == {'mean': 77, 'n': 1}
    assert groups['cases']['metrics']['text_boundary'] == {'mean': None, 'n': 0}
