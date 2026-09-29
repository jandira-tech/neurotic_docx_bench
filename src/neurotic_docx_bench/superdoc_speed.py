"""Meticulous redline-GENERATION speed benchmark for the native SuperDoc SDK (Python).

Same rigor as scripts/speed-bench.ts (init timed separately; warmup; per-pair reps; full
distribution; failures excluded from timing). NOTE the fairness caveat: SuperDoc's SDK is
file-path based (open path → capture → compare → apply → save path), so each timed sample
is the FULL SDK cycle **including disk I/O + session management** — not an in-memory
compare like the Node engines. Reported as-is (that's the tool's real generation cost),
with the caveat recorded in the JSONL row (`note`).

Usage:
  uv run python -m neurotic_docx_bench.superdoc_speed --pairs 40 --reps 3 --warmup 3 \
    --out results/speed.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import shutil
import tempfile
import time
from pathlib import Path

from superdoc import AsyncSuperDocClient

from neurotic_docx_bench.superdoc_gen import generate_one, parse_manifest

USER = {'name': 'speed', 'email': 'speed@x.com'}


def _stats(xs: list[float]) -> dict:
    """Distribution stats — delegates to :mod:`neurotic_docx_bench.speed_stats` so the
    generation-speed rows share the exact percentile/rounding definition of every
    other speed benchmark. Kept as a thin wrapper for back-compat with callers.
    """
    from neurotic_docx_bench.speed_stats import stats as _stats_impl

    return dict(_stats_impl(xs))


def pairs_from_csv(path: Path) -> list[tuple[str, Path, Path, str]]:
    """A planned pair list: header ``key,base,next[,category,...]`` (``results/speed_10k``)."""
    with path.open(newline='') as fh:
        reader = csv.DictReader(fh)
        missing = {'key', 'base', 'next'} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'{path}: missing column(s) {sorted(missing)}')
        rows, seen = [], set()
        for r in reader:
            if r['key'] in seen:
                raise ValueError(f'{path}: duplicate key {r["key"]}')
            seen.add(r['key'])
            rows.append((r['key'], Path(r['base']), Path(r['next']), r.get('category') or ''))
    return rows


async def run(pairs, reps: int, warmup: int, *, per_pair_out: Path | None = None, timeout_s: float = 120.0) -> dict:
    """Time every pair; each output is deleted as soon as it is timed (speed only, nothing kept).

    ``pairs`` holds ``(base, next)`` or ``(key, base, next, category)`` tuples. A pair that
    raises or passes ``timeout_s`` is a failure, excluded from the timing distribution; its
    time is still written to ``per_pair_out`` (one JSON line per sample) when given.
    """
    tmp = Path(tempfile.mkdtemp(prefix='sd-speed.'))
    plan = [p if len(p) == 4 else (f'pair{i}', p[0], p[1], '') for i, p in enumerate(pairs)]
    samples: list[float] = []
    failures = 0
    timeouts = 0
    restarts = 0
    log = per_pair_out.open('w') if per_pair_out else None
    t0 = time.perf_counter()
    client = AsyncSuperDocClient(user=USER)
    try:
        await client.connect()
        init_ms = (time.perf_counter() - t0) * 1000.0

        async def one(idx: int, base: Path, nxt: Path) -> tuple[bool, float, str]:
            nonlocal client, restarts
            out = tmp / f'o{idx}.docx'
            t = time.perf_counter()
            try:
                await asyncio.wait_for(generate_one(client, base, nxt, out, idx), timeout=timeout_s)
                return True, (time.perf_counter() - t) * 1000.0, ''
            except TimeoutError:
                ms = (time.perf_counter() - t) * 1000.0
                # The cancelled call only ends the await: the SDK host is still computing
                # that pair. Dispose it (the SDK kills a host that does not shut down) and
                # start a fresh one, untimed, so the next pair does not queue behind it.
                await client.dispose()
                client = AsyncSuperDocClient(user=USER)
                await client.connect()
                restarts += 1
                return False, ms, 'timeout'
            except Exception as e:  # the SDK refuses many pairs; that is a failure, not a crash
                return False, (time.perf_counter() - t) * 1000.0, str(e)[:300]
            finally:
                out.unlink(missing_ok=True)

        for w in range(min(warmup, len(plan))):  # warmup (untimed)
            await one(100_000 + w, plan[w][1], plan[w][2])
        restarts = 0
        idx = 0
        for _ in range(reps):
            for key, base, nxt, category in plan:
                ok, ms, err = await one(idx, base, nxt)
                idx += 1
                if ok:
                    samples.append(ms)
                else:
                    failures += 1
                    timeouts += err == 'timeout'
                if log:
                    rec = {'key': key, 'category': category, 'ok': ok, 'ms': round(ms, 3)}
                    if not ok:
                        rec['error'] = err
                    log.write(json.dumps(rec) + '\n')
                    log.flush()  # a stopped run keeps every pair it finished
    finally:
        await client.dispose()
        if log:
            log.close()
        shutil.rmtree(tmp, ignore_errors=True)
    return {
        'schema': 1,
        'kind': 'speed',
        'tool': 'superdoc',
        'runtime': 'python',
        'init_ms': round(init_ms, 3),
        'failures': failures,
        'timeouts': timeouts,
        'host_restarts': restarts,
        'unit': 'ms_per_redline',
        'note': 'full file-based SDK cycle (open+capture+compare+apply+save), not in-memory',
        **_stats(samples),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description='SuperDoc redline generation speed benchmark')
    p.add_argument('--pairs', type=int, default=40)
    p.add_argument('--reps', type=int, default=3)
    p.add_argument('--warmup', type=int, default=3)
    p.add_argument('--out', default='results/speed.jsonl')
    p.add_argument('--manifest', default='corpus/word/pools/word_based_pairs.csv')
    p.add_argument('--source-dir', default='corpus/word')
    p.add_argument('--run-ts', default='')
    p.add_argument('--pairs-csv', default='', help='planned pair list (key,base,next,category); overrides --pairs')
    p.add_argument('--per-pair-out', default='', help='write one JSON line per timed sample here')
    p.add_argument('--timeout', type=float, default=120.0, help='seconds per pair before it counts as failed')
    args = p.parse_args(argv)

    chosen: list = []
    if args.pairs_csv:
        chosen = pairs_from_csv(Path(args.pairs_csv))
    else:
        src = Path(args.source_dir)
        for base, nxt in parse_manifest(Path(args.manifest), {'ok'}):
            bp, np_ = src / f'{base}.docx', src / f'{nxt}.docx'
            if bp.exists() and np_.exists():
                chosen.append((bp, np_))
            if len(chosen) >= args.pairs:
                break

    print(f'superdoc-speed: {len(chosen)} pairs, reps={args.reps}, warmup={args.warmup}')
    per_pair = Path(args.per_pair_out) if args.per_pair_out else None
    if per_pair:
        per_pair.parent.mkdir(parents=True, exist_ok=True)
    row = asyncio.run(run(chosen, args.reps, args.warmup, per_pair_out=per_pair, timeout_s=args.timeout))
    row['run_ts'] = args.run_ts
    if args.pairs_csv:
        row['pairs_csv'] = args.pairs_csv
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('a') as fh:
        fh.write(json.dumps(row) + '\n')
    print(
        f'  superdoc  init {row["init_ms"]:.0f}ms  median {row["median"]:.1f}ms  '
        f'mean {row["mean"]:.1f}ms  p95 {row["p95"]:.1f}ms  '
        f'{row["throughput_per_s"]:.2f}/s  (n={row["n"]}, fail={row["failures"]})'
    )
    print(f'wrote 1 row → {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
