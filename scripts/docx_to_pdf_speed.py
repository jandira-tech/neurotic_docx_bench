# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""docx->pdf conversion speed: ms per document, every tool on the same documents.

Sequential and round-robin: each document is converted by every tool back to back
(tool order rotates per document), so background load lands on all tools alike. Each
sample is one CLI call (process start included) — the cost a user pays. soffice keeps
one warm user profile. Failed conversions are excluded from timing and counted.

Usage:
  uv run python scripts/docx_to_pdf_speed.py --jubarte BIN --corpus NAME=DIR [--corpus ...]
      [--tools jubarte,docxide,soffice,rdocx,office2pdf] [--limit N] --out results/docx_to_pdf_speed
Writes <out>/<run_ts>/files.jsonl (one row per sample) and appends one row per tool and
corpus (plus a pooled row, corpus "all") to <out>/speed.jsonl (unit ms_per_docx).
"""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def version_of(tool: str, jubarte: str) -> str:
    probes = {
        'jubarte': [jubarte, '--version'],
        'soffice': ['soffice', '--version'],
        'rdocx': ['rdocx', '--version'],
        'office2pdf': ['office2pdf', '--version'],
    }
    if tool == 'docxide':
        out = subprocess.run(['cargo', 'install', '--list'], capture_output=True, text=True).stdout
        line = next((ln for ln in out.splitlines() if ln.startswith('docxide-pdf ')), '')
        return line.rstrip(':').strip() or 'docxide-pdf'
    out = subprocess.run(probes[tool], capture_output=True, text=True)
    version = (out.stdout or out.stderr).strip().splitlines()[0]
    # A jubarte binary named jubarte-<sha> records the source commit it was built from.
    if tool == 'jubarte' and '-' in Path(jubarte).name:
        version += '@' + Path(jubarte).name.rsplit('-', 1)[1]
    return version


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--jubarte', required=True)
    ap.add_argument('--corpus', action='append', required=True, help='NAME=DIR of .docx files')
    ap.add_argument('--tools', default='jubarte,docxide,soffice,rdocx,office2pdf')
    ap.add_argument('--limit', type=int, default=0, help='documents per corpus (0 = all)')
    ap.add_argument('--timeout', type=int, default=120)
    ap.add_argument('--out', default='results/docx_to_pdf_speed')
    args = ap.parse_args()

    tools = args.tools.split(',')
    versions = {t: version_of(t, args.jubarte) for t in tools}
    run_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')
    run_dir = Path(args.out) / run_ts
    run_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='d2p-speed.'))
    profile = work / 'lo_profile'

    def cmd(tool: str, src: Path, dst: Path) -> list[str]:
        return {
            'jubarte': [args.jubarte, 'convert', str(src), '-o', str(dst), '--force', '--revisions', 'word'],
            'docxide': ['docxide-pdf', str(src), str(dst)],
            'rdocx': ['rdocx', 'convert', '--to', 'pdf', '-o', str(dst), str(src)],
            'office2pdf': ['office2pdf', '-o', str(dst), str(src)],
            'soffice': [
                'soffice',
                f'-env:UserInstallation=file://{profile}',
                '--headless',
                '--convert-to',
                'pdf',
                '--outdir',
                str(work / 'lo'),
                str(src),
            ],
        }[tool]

    def once(tool: str, src: Path) -> tuple[float, bool]:
        dst = work / f'{tool}.pdf'
        dst.unlink(missing_ok=True)
        t0 = time.perf_counter()
        try:
            rc = subprocess.run(cmd(tool, src, dst), capture_output=True, timeout=args.timeout).returncode
        except subprocess.TimeoutExpired:
            rc = -1
        ms = (time.perf_counter() - t0) * 1000
        if tool == 'soffice':
            lo = work / 'lo' / (src.stem + '.pdf')
            if lo.exists():
                shutil.move(str(lo), str(dst))
        return ms, rc == 0 and dst.exists() and dst.stat().st_size > 0

    corpora = []
    for spec in args.corpus:
        name, _, d = spec.partition('=')
        docs = sorted(p for p in Path(d).glob('*.docx') if not p.name.startswith('~$'))
        corpora.append((name, docs[: args.limit] if args.limit else docs))
    # Warm every tool once (soffice profile creation, page cache) — untimed.
    first = corpora[0][1][0]
    for t in tools:
        once(t, first)

    samples: dict[tuple[str, str], list[float]] = {}
    failed: dict[tuple[str, str], int] = {}
    with open(run_dir / 'files.jsonl', 'w') as rows:
        i = 0
        for name, docs in corpora:
            for src in docs:
                order = tools[i % len(tools) :] + tools[: i % len(tools)]
                i += 1
                for t in order:
                    ms, ok = once(t, src)
                    rows.write(
                        json.dumps({'corpus': name, 'doc': src.name, 'tool': t, 'ms': round(ms, 3), 'ok': ok}) + '\n'
                    )
                    for key in ((t, name), (t, 'all')):
                        if ok:
                            samples.setdefault(key, []).append(ms)
                        else:
                            failed[key] = failed.get(key, 0) + 1
            print(f'{name}: {len(docs)} docs done', flush=True)

    with open(Path(args.out) / 'speed.jsonl', 'a') as out:
        for (t, name), xs in sorted(samples.items()):
            xs.sort()
            row = {
                'unit': 'ms_per_docx',
                'tool': t,
                'version': versions[t],
                'corpus': name,
                'run_ts': run_ts,
                'n': len(xs),
                'failed': failed.get((t, name), 0),
                'mean': round(statistics.fmean(xs), 3),
                'median': round(statistics.median(xs), 3),
                'p95': round(xs[min(len(xs) - 1, int(0.95 * len(xs)))], 3),
                'note': 'sequential round-robin, one CLI call per sample (process start included)',
            }
            out.write(json.dumps(row) + '\n')
            print(json.dumps(row), flush=True)
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
