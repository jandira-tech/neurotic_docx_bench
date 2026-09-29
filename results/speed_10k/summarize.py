"""Summarise the 10k speed runs into SUMMARY.md.

    uv run python results/speed_10k/summarize.py redlines   # per_pair/<method>.jsonl + pairs_10k.csv
    uv run python results/speed_10k/summarize.py pdf        # pdf/<run_ts>/files.jsonl + pdf_docs_10k.csv

Every row is one timed call. Failed calls are counted, and their time is shown apart, never
mixed into the success distribution. Breakdowns: by pair category or document family, and
by size quartile (base size for redlines, document size for PDFs).
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent


def pct(xs: list[float], q: float) -> float:
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def stats(rows: list[dict]) -> dict:
    ok = sorted(r['ms'] for r in rows if r['ok'])
    bad = [r['ms'] for r in rows if not r['ok'] and r.get('ms') is not None]
    out = {'n': len(rows), 'ok': len(ok), 'failed': len(rows) - len(ok)}
    if ok:
        out |= {
            'median': statistics.median(ok),
            'mean': statistics.fmean(ok),
            'p95': pct(ok, 0.95),
            'p99': pct(ok, 0.99),
            'max': ok[-1],
            'total_s': sum(ok) / 1000,
        }
    out['failed_total_s'] = sum(bad) / 1000
    return out


def table(title: str, groups: dict[tuple[str, str], list[dict]], label: str) -> list[str]:
    lines = [
        f'## {title}',
        '',
        f'| tool | {label} | n | ok | failed | median ms | mean ms | p95 ms | p99 ms | max ms | ok total s |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for (tool, g), rows in sorted(groups.items()):
        s = stats(rows)
        if s['ok']:
            nums = ' | '.join(f'{s[k]:.1f}' for k in ('median', 'mean', 'p95', 'p99', 'max', 'total_s'))
        else:
            nums = ' | '.join(['-'] * 6)
        lines.append(f'| {tool} | {g} | {s["n"]} | {s["ok"]} | {s["failed"]} | {nums} |')
    return [*lines, '']


def quartiles(sizes: list[int]) -> list[int]:
    s = sorted(sizes)
    return [s[len(s) * q // 4] for q in (1, 2, 3)]


def redlines() -> None:
    out = HERE / 'redlines'
    plan = {r['key']: r for r in csv.DictReader(open(HERE / 'pairs_10k.csv'))}
    cuts = quartiles([int(r['base_bytes']) for r in plan.values()])
    by_cat: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_q: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for f in sorted((out / 'per_pair').glob('*.jsonl')):
        tool = f.stem
        for line in f.open():
            r = json.loads(line)
            p = plan[r['key']]
            q = sum(int(p['base_bytes']) >= c for c in cuts)
            for key in ((tool, 'all'), (tool, r['category'])):
                by_cat[key].append(r)
            by_q[tool, f'Q{q + 1}'].append(r)
    md = [
        '# Redline speed, 10,000 planned pairs',
        '',
        'One call per pair, engines run one after another on the same machine. Node lanes time an '
        'in-memory `compare(base, next)`; `jubarte-rust` spawns the CLI per pair (process start and file '
        "I/O included); SuperDoc's SDK is file based (open, compare, apply, save). No redline is kept.",
        f'Base size quartile cuts: {cuts} bytes. Machine state: ENV.txt.',
        '',
        *table('By pair category', by_cat, 'category'),
        *table('By base size quartile', by_q, 'quartile'),
    ]
    (out / 'SUMMARY.md').write_text('\n'.join(md))
    print('\n'.join(md))


def pdf() -> None:
    root = HERE / 'pdf'
    docs = {r['path']: r for r in csv.DictReader(open(HERE / 'pdf_docs_10k.csv'))}
    by_fam: dict[tuple[str, str], list[dict]] = defaultdict(list)
    by_q: dict[tuple[str, str], list[dict]] = defaultdict(list)
    runs = sorted(p for p in root.iterdir() if p.is_dir() and (p / 'files.jsonl').exists())
    for line in (runs[-1] / 'files.jsonl').open():
        r = json.loads(line)
        d = docs.get(r.get('path', ''), {})
        fam = d.get('family', '?').split('/')[0].split(':')[0]
        by_fam[r['tool'], 'all'].append(r)
        by_fam[r['tool'], fam].append(r)
        by_q[r['tool'], f'Q{int(d.get("quartile", -1)) + 1}'].append(r)
    md = [
        '# DOCX to PDF speed, 10,000 documents',
        '',
        'Sequential round robin: each document goes through every tool back to back, tool order '
        'rotating per document. One CLI call per sample (process start included). No PDF is kept.',
        f'Run: {runs[-1].name}. Machine state: ENV.txt.',
        '',
        *table('By source family', by_fam, 'family'),
        *table('By document size quartile', by_q, 'quartile'),
    ]
    (root / 'SUMMARY.md').write_text('\n'.join(md))
    print('\n'.join(md))


if __name__ == '__main__':
    {'redlines': redlines, 'pdf': pdf}[sys.argv[1]]()
