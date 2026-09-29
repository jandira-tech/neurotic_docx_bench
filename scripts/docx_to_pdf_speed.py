# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""docx->pdf conversion speed: ms per document, every tool on the same documents.

Sequential and round-robin: each document is converted by every tool back to back
(tool order rotates per document), so background load lands on all tools alike. Each
sample is one CLI call (process start included) — the cost a user pays. soffice keeps
one warm user profile. Failed conversions are excluded from timing and counted.

--warm times a long-lived worker per tool instead (tools/d2p-warm, one binary per
tool, the same library calls as each CLI): read + convert + write, measured inside the
worker, with process start and one-time initialisation paid once, as a service would.
A worker past --timeout is killed, respawned, and the document counts as failed.
soffice has no warm worker here: driving it warm needs LibreOffice's bundled Python
(UNO), which macOS kills at start on this install (its app bundle seal is invalid).

Usage:
  uv run python scripts/docx_to_pdf_speed.py --jubarte BIN --corpus NAME=DIR [--corpus NAME=@LIST ...]
      [--tools jubarte,jubarte-compress,docxide,soffice,rdocx,office2pdf] [--limit N] [--warm]
      --out results/docx_to_pdf_speed
A corpus is a directory of .docx files or, with ``@``, a text file listing one .docx path
per line (kept in its order). ``jubarte-compress`` is the jubarte call plus ``--compress``.
Every PDF is written to one temp file per tool, overwritten by the next sample and removed
at the end: nothing converted is kept.
Writes <out>/<run_ts>/files.jsonl (one row per sample) and appends one row per tool and
corpus (plus a pooled row, corpus "all") to <out>/speed.jsonl (unit ms_per_docx).
"""

from __future__ import annotations

import argparse
import json
import selectors
import shutil
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def version_of(tool: str, jubarte: str) -> str:
    if tool == 'jubarte-compress':
        return version_of('jubarte', jubarte) + ' --compress'
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


def tool_cmd(tool: str, src: Path, dst: Path, *, jubarte: str, profile: Path, lo_dir: Path) -> list[str]:
    jub = [jubarte, 'convert', str(src), '-o', str(dst), '--force', '--revisions', 'word']
    return {
        'jubarte': jub,
        'jubarte-compress': [*jub, '--compress'],
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
            str(lo_dir),
            str(src),
        ],
    }[tool]


def load_corpus(spec: str) -> tuple[str, list[Path]]:
    """``NAME=DIR`` (sorted .docx, no ``~$`` lock files) or ``NAME=@LIST`` (paths in file order)."""
    name, _, where = spec.partition('=')
    if where.startswith('@'):
        docs = [Path(ln.strip()) for ln in Path(where[1:]).read_text().splitlines() if ln.strip()]
        missing = [d for d in docs if not d.is_file()]
        if missing:
            raise SystemExit(f'{spec}: {len(missing)} listed file(s) missing, first {missing[0]}')
        return name, docs
    return name, sorted(p for p in Path(where).glob('*.docx') if not p.name.startswith('~$'))


WARM_BIN = Path(__file__).resolve().parent.parent / 'tools' / 'd2p-warm' / 'bin'


class Worker:
    """One d2p-warm process: `src\tdst` in, `ok <ms>` / `err <ms> <msg>` out."""

    def __init__(self, tool: str, timeout: float) -> None:
        self.tool, self.timeout, self.proc = tool, timeout, None

    def start(self) -> None:
        self.proc = subprocess.Popen(
            [str(WARM_BIN / f'd2p-warm-{self.tool}'), self.tool],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

    def convert(self, src: Path, dst: Path) -> tuple[float, bool]:
        if self.proc is None or self.proc.poll() is not None:
            self.start()
        t0 = time.perf_counter()
        self.proc.stdin.write(f'{src}\t{dst}\n')
        self.proc.stdin.flush()
        sel = selectors.DefaultSelector()
        sel.register(self.proc.stdout, selectors.EVENT_READ)
        ready = sel.select(self.timeout)
        sel.close()
        line = self.proc.stdout.readline() if ready else ''
        if not line:
            self.proc.kill()
            self.proc.wait()
            self.proc = None
            return (time.perf_counter() - t0) * 1000, False
        status, ms, *_ = line.split(' ', 2)
        return float(ms), status == 'ok' and dst.exists() and dst.stat().st_size > 0

    def close(self) -> None:
        if self.proc is not None:
            self.proc.stdin.close()
            self.proc.wait()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--jubarte', required=True)
    ap.add_argument('--corpus', action='append', required=True, help='NAME=DIR of .docx files')
    ap.add_argument('--tools', default='jubarte,docxide,soffice,rdocx,office2pdf')
    ap.add_argument('--limit', type=int, default=0, help='documents per corpus (0 = all)')
    ap.add_argument('--timeout', type=int, default=120)
    ap.add_argument('--out', default='results/docx_to_pdf_speed')
    ap.add_argument('--warm', action='store_true', help='time warm workers (tools/d2p-warm)')
    args = ap.parse_args()

    tools = args.tools.split(',')
    if args.warm and 'soffice' in tools:
        tools.remove('soffice')
        print('--warm: soffice skipped (no warm worker; see the module docstring)', flush=True)
    workers = {t: Worker(t, args.timeout) for t in tools} if args.warm else {}
    # The warm jubarte row is labelled with --jubarte's version, so its worker must
    # be built from the same source: a worker older than that binary is stale.
    warm_jubarte = WARM_BIN / 'd2p-warm-jubarte'
    if 'jubarte' in workers and warm_jubarte.stat().st_mtime < Path(args.jubarte).stat().st_mtime:
        raise SystemExit(f'{warm_jubarte} predates {args.jubarte}: rebuild it from the same checkout')
    versions = {t: version_of(t, args.jubarte) for t in tools}
    run_ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')
    run_dir = Path(args.out) / run_ts
    run_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='d2p-speed.'))
    profile = work / 'lo_profile'

    def cmd(tool: str, src: Path, dst: Path) -> list[str]:
        return tool_cmd(tool, src, dst, jubarte=args.jubarte, profile=profile, lo_dir=work / 'lo')

    def once(tool: str, src: Path) -> tuple[float, bool]:
        dst = work / f'{tool}.pdf'
        dst.unlink(missing_ok=True)
        if tool in workers:
            return workers[tool].convert(src, dst)
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
        name, docs = load_corpus(spec)
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
                        json.dumps({
                            'corpus': name,
                            'doc': src.name,
                            'path': str(src),
                            'tool': t,
                            'ms': round(ms, 3),
                            'ok': ok,
                        })
                        + '\n'
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
                'total_s': round(sum(xs) / 1000, 3),
                'mean': round(statistics.fmean(xs), 3),
                'median': round(statistics.median(xs), 3),
                'p95': round(xs[min(len(xs) - 1, int(0.95 * len(xs)))], 3),
                'note': (
                    'warm: sequential round-robin, one long-lived worker per tool (library calls as the CLI, '
                    'read + convert + write timed in-process)'
                    if args.warm
                    else 'sequential round-robin, one CLI call per sample (process start included)'
                ),
                'mode': 'warm' if args.warm else 'cold',
            }
            out.write(json.dumps(row) + '\n')
            print(json.dumps(row), flush=True)
    for w in workers.values():
        w.close()
    shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
