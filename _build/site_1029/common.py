"""Pure renewal data helpers; viewer markup outside DATA is an immutable input."""
from __future__ import annotations
import copy
import json
import re

KEY = 'jubarte'
VERSION = 'jubarte 0.14.0'
OLD_KEYS = ('jubarte-0.11.0', 'jubarte-0.12.0')
FIELDS = ('pages', 'page_counts', 'scores', 'pdfs', 'times', 'errors', 'versions', 'metric_diagnostics')
R2 = 'https://pub-92c80eda1059428394970066c8500eda.r2.dev/'


def split(html: str) -> tuple[str, list[dict], str]:
    start = html.index('const DATA = ') + len('const DATA = ')
    end = html.index(';\n', start)
    return html[:start], json.loads(html[start:end]), html[end:]


def shown_pages(case: dict) -> list[int]:
    if case.get('shown') is not None:
        shown = case['shown'][:]
    else:
        n = case['page_counts']['reference']
        shown = list(range(1, min(3, n) + 1))
    reference = case['pages']['reference']
    if len(shown) != len(reference):
        raise ValueError('Shown pages do not line up with existing Word column')
    for p, url in zip(shown, reference):
        match = re.search(r'page_(\d+)\.webp$', url or '')
        if match and int(match[1]) != p:
            raise ValueError('Word asset page number disagrees with shown')
    return shown


def replace_case(original: dict, row: dict) -> dict:
    if (original['group'], original['case']) != (row['group'], row['case']):
        raise ValueError('Case identity mismatch')
    if shown_pages(original) != row['shown']:
        raise ValueError('Shown pages changed since build')
    result = copy.deepcopy(original)
    removed = set()
    for field in FIELDS:
        old_map = result.get(field, {})
        for key in OLD_KEYS:
            if key in old_map:
                removed.add(key)
                del old_map[key]
        if KEY in row.get(field, {}):
            value = copy.deepcopy(row[field][KEY])
            if field == 'pages':
                value = [R2 + p if p else None for p in value]
            elif field == 'pdfs':
                value = R2 + value
            result.setdefault(field, {})[KEY] = value
        else:
            old_map.pop(KEY, None)
    result['dropped'] = sorted((set(result.get('dropped', [])) | removed) - {KEY})
    return result


def patch_html(html: str, rows: list[dict]) -> str:
    head, cases, tail = split(html)
    by_id = {(r['group'], r['case']): r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError('Duplicate replacement identity')
    seen = set()
    # Preserve every unmodified row's exact original bytes. Current live DATA is
    # canonical json.dumps; refuse a different representation instead of rewriting it.
    canonical = json.dumps(cases, ensure_ascii=False)
    if head + canonical + tail != html:
        raise ValueError('Current DATA is not canonical; refusing incidental byte changes')
    output = []
    for case in cases:
        identity = (case['group'], case['case'])
        if identity in by_id:
            output.append(replace_case(case, by_id[identity]))
            seen.add(identity)
        else:
            output.append(case)
    if seen != set(by_id):
        raise ValueError('Replacement cases missing from current site')
    return head + json.dumps(output, ensure_ascii=False) + tail


def summary(rows: list[dict]) -> dict:
    groups = {}
    for group in sorted({r['group'] for r in rows}):
        selected = [r for r in rows if r['group'] == group]
        metrics = {}
        for metric in ('pixel', 'jaccard', 'ssim', 'text_boundary'):
            values = [r['scores'][KEY].get(metric) for r in selected]
            values = [v for v in values if v is not None]
            metrics[metric] = {'mean': sum(values) / len(values) if values else None, 'n': len(values)}
        groups[group] = {'cases': len(selected), 'failures': sum(KEY in r['errors'] for r in selected), 'metrics': metrics}
    return groups
