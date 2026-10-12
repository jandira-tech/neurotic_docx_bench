# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Per-lane speed over the pairs (or redlines) that EVERY lane converted successfully.

redline_speed_bench.ts already leaves failed samples out of each lane's median/p95, but
each lane still answers over its own successes, and its throughput uses wall time, which
carries the time a timeout burned. This view is the generous one: a pair any lane failed
is dropped from every lane, and throughput is 1000 / mean of the surviving samples.

Usage:
  uv run python scripts/speed_common_set.py RUN_DIR [--kind redline|pdf|both] [--out FILE.md]
Reads RUN_DIR/per_pair/<lane>.jsonl (redlines) and RUN_DIR/per_pdf/<lane>.jsonl (PDFs).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path


def load(path: Path) -> dict[str, dict]:
    rows = {}
    for line in path.read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r['key']] = r
    return rows


def pct(xs: list[float], p: float) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, round(p / 100 * len(s) + 0.5) - 1))]


def table(title: str, lanes: dict[str, dict[str, dict]]) -> list[str]:
    if not lanes:
        return []
    ok = {name: {k for k, r in rows.items() if r.get('ok')} for name, rows in lanes.items()}
    planned = set().union(*(set(rows) for rows in lanes.values()))
    common = set.intersection(*ok.values())
    out = [
        f'## {title}',
        '',
        f'- pairs seen: {len(planned)}; common successful set: {len(common)}',
        *[f'- {name}: {len(planned) - len(ok[name])} failed or missing' for name in lanes],
        '',
        '| lane | n | median ms | mean ms | p90 | p95 | p99 | max | /s (1000/mean) |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |',
    ]
    stats = []
    for name, rows in lanes.items():
        xs = [rows[k]['ms'] for k in common]
        mean = statistics.fmean(xs)
        stats.append((statistics.median(xs), name, xs, mean))
    for med, name, xs, mean in sorted(stats):
        out.append(
            f'| {name} | {len(xs)} | {med:.1f} | {mean:.1f} | {pct(xs, 90):.1f} | {pct(xs, 95):.1f} | '
            f'{pct(xs, 99):.1f} | {max(xs):.1f} | {1000 / mean:.2f} |'
        )
    return out + ['']


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('run_dir', type=Path)
    ap.add_argument('--kind', choices=('redline', 'pdf', 'both'), default='both')
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    md = [f'# Common-set speed: {a.run_dir}', '']
    for kind, sub, title in (('redline', 'per_pair', 'Redlines (ms per redline)'),
                             ('pdf', 'per_pdf', 'docx→PDF (ms per PDF)')):
        if a.kind not in (kind, 'both'):
            continue
        d = a.run_dir / sub
        lanes = {p.stem: load(p) for p in sorted(d.glob('*.jsonl'))} if d.is_dir() else {}
        md += table(title, lanes)
    text = '\n'.join(md) + '\n'
    if a.out:
        if a.out.exists():
            print(f'refusing to overwrite {a.out}', file=sys.stderr)
            return 1
        a.out.write_text(text)
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
