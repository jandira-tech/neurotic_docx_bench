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
import json
import tempfile
import time
from pathlib import Path

from superdoc import AsyncSuperDocClient

from neurotic_docx_bench.superdoc_gen import generate_one, parse_manifest


def _stats(xs: list[float]) -> dict:
    """Distribution stats — delegates to :mod:`neurotic_docx_bench.speed_stats` so the
    generation-speed rows share the exact percentile/rounding definition of every
    other speed benchmark. Kept as a thin wrapper for back-compat with callers.
    """
    from neurotic_docx_bench.speed_stats import stats as _stats_impl

    return dict(_stats_impl(xs))


async def run(pairs, reps: int, warmup: int) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="sd-speed."))
    samples: list[float] = []
    failures = 0
    t0 = time.perf_counter()
    async with AsyncSuperDocClient(user={"name": "speed", "email": "speed@x.com"}) as client:
        init_ms = (time.perf_counter() - t0) * 1000.0

        async def one(idx: int, base: Path, nxt: Path) -> float | None:
            out = tmp / f"o{idx}.docx"
            t = time.perf_counter()
            try:
                await generate_one(client, base, nxt, out, idx)
                return (time.perf_counter() - t) * 1000.0
            except Exception:
                return None

        for w in range(min(warmup, len(pairs))):  # warmup (untimed)
            await one(10_000 + w, pairs[w][0], pairs[w][1])
        idx = 0
        for _ in range(reps):
            for base, nxt in pairs:
                ms = await one(idx, base, nxt)
                idx += 1
                if ms is None:
                    failures += 1
                else:
                    samples.append(ms)
    return {
        "schema": 1,
        "kind": "speed",
        "tool": "superdoc",
        "runtime": "python",
        "init_ms": round(init_ms, 3),
        "failures": failures,
        "unit": "ms_per_redline",
        "note": "full file-based SDK cycle (open+capture+compare+apply+save), not in-memory",
        **_stats(samples),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SuperDoc redline generation speed benchmark")
    p.add_argument("--pairs", type=int, default=40)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--warmup", type=int, default=3)
    p.add_argument("--out", default="results/speed.jsonl")
    p.add_argument("--manifest", default="corpus/word_based/centralized_mapping.csv")
    p.add_argument("--source-dir", default="corpus/word_based/docx_source")
    p.add_argument("--run-ts", default="")
    args = p.parse_args(argv)

    src = Path(args.source_dir)
    chosen: list[tuple[Path, Path]] = []
    for base, nxt in parse_manifest(Path(args.manifest), {"ok"}):
        bp, np_ = src / f"{base}.docx", src / f"{nxt}.docx"
        if bp.exists() and np_.exists():
            chosen.append((bp, np_))
        if len(chosen) >= args.pairs:
            break

    print(f"superdoc-speed: {len(chosen)} pairs, reps={args.reps}, warmup={args.warmup}")
    row = asyncio.run(run(chosen, args.reps, args.warmup))
    row["run_ts"] = args.run_ts
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(
        f"  superdoc  init {row['init_ms']:.0f}ms  median {row['median']:.1f}ms  "
        f"mean {row['mean']:.1f}ms  p95 {row['p95']:.1f}ms  "
        f"{row['throughput_per_s']:.2f}/s  (n={row['n']}, fail={row['failures']})",
    )
    print(f"wrote 1 row → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
