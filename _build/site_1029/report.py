"""Real-file integration audit, asset manifest, preservation checks and group report."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import pymupdf
from PIL import Image
from common import FIELDS, KEY, OLD_KEYS, VERSION, shown_pages, split, summary

H = Path(__file__).resolve().parent
BUILD = H / 'build'
SITE = H.parents[1]


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    provenance = json.loads((H / 'source_hashes.json').read_text())
    assert digest(SITE / 'index.html') == provenance['site_sha256'], 'Live source changed'
    assert digest(SITE / 'redlines/index.html') == provenance['redlines_sha256'], 'Redlines viewer changed'
    for relative, sha in provenance['source_hashes'].items():
        assert digest(H / 'scorer-source' / relative) == sha
    assert digest(H / 'bin/page-metrics') == provenance['page_metrics_binary_sha256']
    jobs = json.loads((H / 'jobs_d2p_jubarte.json').read_text())
    work = Path.home() / 'temp/T/renew_1028'
    assert digest(work / 'MANIFEST.sha256.txt') == provenance['phase1_manifest_sha256']
    for job in jobs:
        for path, sha in job['hashes'].items():
            assert digest(Path(path)) == sha, f'Scoring input changed: {path}'
    rows = json.loads((BUILD / 'cases_d2p_jubarte.json').read_text())
    source_html, preview_html = (SITE / 'index.html').read_text(), (H / 'preview/index.html').read_text()
    head, original, tail = split(source_html)
    new_head, patched, new_tail = split(preview_html)
    assert (head, tail) == (new_head, new_tail), 'Markup, globals or viewer logic changed'
    assert len(rows) == len(jobs) == 1276
    for job, row in zip(jobs, rows):
        assert (job['group'], job['case']) == (row['group'], row['case'])
        saved = json.loads((BUILD / 'records' / f"{job['key']}.json").read_text())
        assert saved['fingerprint'] == hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
        assert saved['row'] == row
    assert len(original) == len(patched)
    by_id = {(r['group'], r['case']): r for r in rows}
    assert len(by_id) == len(rows)
    expected_assets, dropped_counts, untouched, updated = set(), {}, 0, 0
    for old, new in zip(original, patched):
        identity = old['group'], old['case']
        assert identity == (new['group'], new['case']), 'Case order changed'
        if identity not in by_id:
            assert old == new
            assert json.dumps(old, ensure_ascii=False) in preview_html
            untouched += 1
            continue
        row = by_id[identity]
        updated += 1
        assert shown_pages(old) == row['shown']
        assert new['pages']['reference'] == old['pages']['reference']
        assert new['versions'][KEY] == VERSION and KEY not in new['dropped']
        assert new['scores'][KEY] == row['scores'][KEY]
        assert all(k not in new.get(f, {}) for f in FIELDS for k in OLD_KEYS)
        for key in OLD_KEYS:
            if any(key in old.get(f, {}) for f in FIELDS):
                assert key in new['dropped']
                dropped_counts[key] = dropped_counts.get(key, 0) + 1
        for field in set(old) | set(new):
            if field == 'dropped':
                assert set(new[field]) - set(old.get(field, [])) <= set(OLD_KEYS)
                assert set(old.get(field, [])) - set(new[field]) <= {KEY}
            elif field in FIELDS:
                strip = lambda c: {k: v for k, v in c.get(field, {}).items() if k not in (KEY, *OLD_KEYS)}
                assert strip(old) == strip(new), (identity, field)
            else:
                assert old.get(field) == new.get(field), (identity, field)
        score = row['scores'][KEY]
        assert all(v is None or (math.isfinite(v) and 0 <= v <= 100.00001) for v in score.values())
        if KEY in row['errors']:
            assert score['pixel'] == 0 and not any(row['pages'][KEY]) and KEY not in row['pdfs']
            continue
        result = row['pixel_result']
        assert score['pixel'] == result.get('overall_score_pagefair', result['overall_score'])
        assert result['page_count_candidate'] == row['page_counts'][KEY]
        expected_pages = [p for p in row['shown'] if p <= row['page_counts'][KEY]]
        assert len(row['pages'][KEY]) == len(old['pages']['reference'])
        for p, relative in zip(row['shown'], row['pages'][KEY]):
            if p not in expected_pages:
                assert relative is None
                continue
            assert relative.startswith('renew1028/d2p/') and relative.endswith(f'/page_{p:03d}.webp')
            path = BUILD / relative
            with Image.open(path) as image:
                assert image.format == 'WEBP' and min(image.size) > 0
                image.verify()
            expected_assets.add(path)
        if expected_pages:
            path = BUILD / row['pdfs'][KEY]
            with pymupdf.open(path) as pdf:
                assert len(pdf) == len(expected_pages)
            expected_assets.add(path)
    actual_assets = {p for p in (BUILD / 'renew1028').rglob('*') if p.is_file()}
    assert actual_assets == expected_assets, f'Asset inventory mismatch: missing={expected_assets-actual_assets}, extra={actual_assets-expected_assets}'
    assert not list(BUILD.rglob('*.png')), 'Temporary PNGs remain'
    groups = summary(rows)
    total_bytes = sum(p.stat().st_size for p in BUILD.rglob('*') if p.is_file()
                      and p.name not in ('REPORT.json', 'REPORT.md', 'MANIFEST.sha256.txt'))
    asset_bytes = sum(p.stat().st_size for p in actual_assets)
    report = {'cases_replaced': updated, 'cases_untouched_byte_identical': untouched,
              'failures': [{'group': r['group'], 'case': r['case'], 'error': r['errors'][KEY]} for r in rows if KEY in r['errors']],
              'dropped_old_columns': dropped_counts, 'groups': groups, 'scorer': provenance,
              'assets': len(actual_assets), 'asset_bytes': asset_bytes, 'build_bytes_before_reports': total_bytes,
              'pngs_remaining': 0, 'source_and_redlines_unchanged': True}
    lines = ['# Phase 3a — jubarte 0.14.0 DOCX→PDF', '',
        f'{updated:,} cases replaced; {untouched:,} cases retained byte-identical. {len(report["failures"])} failures (Pixel ITT zero).', '',
        '| Group | Replaced | Failures | Pixel | J | SSIM | TB |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for group, values in groups.items():
        cells = [f'{v["mean"]:.4f} (n={v["n"]})' if v['mean'] is not None else f'— (n={v["n"]})' for v in values['metrics'].values()]
        lines.append(f'| {group} | {values["cases"]} | {values["failures"]} | ' + ' | '.join(cells) + ' |')
    lines += ['', f'Assets: {len(actual_assets):,} files, {asset_bytes:,} bytes ({asset_bytes/2**20:.2f} MiB).',
        f'Build data excluding report/manifest files: {total_bytes:,} bytes ({total_bytes/2**20:.2f} MiB), including checkpoint records and full scorer results.',
        '', f'Bench main `{provenance["bench_commit"]}`; scorer fingerprint `{provenance["scorer_fingerprint"]}`, backend `{provenance["scorer_backend"]}`, {provenance["pixel_dpi"]} DPI.',
        'Pixel uses `pipeline.overall_from_result` (`overall_score_pagefair` when present), exactly as the bench DOCX→PDF command. Raw `overall_score` is also retained in each row\'s `pixel_result`.',
        'J/SSIM/TB: upstream page-metrics a72d91bc at 150 DPI over all compatible common pages, multiplied by 100 and rounded to one decimal as site_1028. Upstream nulls remain null; means exclude only nulls, with denominators shown.',
        'Shown pages are the current case\'s existing selection; cases without shown use first 3. Candidate pages beyond the reference selection are not shown; missing candidate pages retain null gaps.',
        'Encoding: 180-DPI mutool PNG → 2/3 Lanczos resize → 16-colour median-cut → lossless WebP method 4; shown-page PDF via mutool clean -gggz.',
        f'Old Wordcraft lanes removed and marked dropped: {dropped_counts}.',
        'All non-jubarte data, Word columns, case order, untouched rows, and all HTML outside DATA validated unchanged. Source index.html and redlines/index.html SHA256 unchanged. No temporary PNGs remain.',
        'No Word invocation, upload, commit, external posting or live viewer write.']
    manifest_files = sorted(actual_assets | {BUILD / 'cases_d2p_jubarte.json'})
    (BUILD / 'MANIFEST.sha256.txt').write_text(''.join(f'{digest(p)}  {p.relative_to(BUILD).as_posix()}\n' for p in manifest_files))
    # Include the report files themselves without an approximate or stale total.
    for _ in range(5):
        report['build_bytes'] = sum(p.stat().st_size for p in BUILD.rglob('*') if p.is_file())
        (BUILD / 'REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
        size_line = f'Final build directory: {report["build_bytes"]:,} bytes ({report["build_bytes"]/2**20:.2f} MiB), including reports and the asset manifest.'
        (BUILD / 'REPORT.md').write_text('\n'.join(lines) + '\n\n' + size_line + '\n')
        if sum(p.stat().st_size for p in BUILD.rglob('*') if p.is_file()) == report['build_bytes']:
            break
    else:
        raise AssertionError('Build size did not stabilize')
    print(json.dumps({k: report[k] for k in ('cases_replaced', 'cases_untouched_byte_identical', 'dropped_old_columns', 'assets', 'asset_bytes', 'pngs_remaining')}))


if __name__ == '__main__':
    main()
