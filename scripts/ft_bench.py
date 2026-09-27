#!/usr/bin/env python3
"""Score-stage timing under a process pool vs a thread pool.

Rasterized pages are read from ``--pages DIR/<key>/{oracle,cand}/page_*.png`` so
PyMuPDF is not imported at all; only numpy/scipy/scikit-image run. This isolates the
part of the scorer that free-threaded CPython could parallelize with threads.

Usage: PYTHONPATH=src python ft_bench.py --pages DIR --mode process|thread --workers N
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path


def _score_key(args: tuple[str, list[str], list[str]]) -> tuple[str, float, float]:
    from neurotic_docx_bench import score

    key, oracle, cand = args
    t0 = time.perf_counter()
    result = score.score_document([Path(p) for p in oracle], [Path(p) for p in cand])
    return key, float(result["overall_score"]), time.perf_counter() - t0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=Path, required=True)
    ap.add_argument("--mode", choices=("process", "thread", "serial"), default="process")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--json", type=Path)
    ns = ap.parse_args()

    tasks = []
    for key_dir in sorted(p for p in ns.pages.iterdir() if p.is_dir()):
        oracle = sorted(str(p) for p in (key_dir / "oracle").glob("*.png"))
        cand = sorted(str(p) for p in (key_dir / "cand").glob("*.png"))
        if oracle and cand:
            tasks.append((key_dir.name, oracle, cand))
    if ns.limit:
        tasks = tasks[: ns.limit]

    gil = sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else True
    t0 = time.perf_counter()
    if ns.mode == "serial":
        results = [_score_key(t) for t in tasks]
    elif ns.mode == "thread":
        with ThreadPoolExecutor(max_workers=ns.workers) as pool:
            results = list(pool.map(_score_key, tasks))
    else:
        with ProcessPoolExecutor(max_workers=ns.workers) as pool:
            results = list(pool.map(_score_key, tasks, chunksize=1))
    wall = time.perf_counter() - t0
    cpu_sum = sum(r[2] for r in results)
    report = {
        "python": sys.version.split()[0] + ("t" if "free-threading" in sys.version else ""),
        "gil_enabled": gil,
        "mode": ns.mode,
        "workers": ns.workers,
        "docs": len(results),
        "wall_s": round(wall, 2),
        "per_doc_sum_s": round(cpu_sum, 2),
        "speedup_vs_sum": round(cpu_sum / wall, 2) if wall else None,
        "omp": os.environ.get("OMP_NUM_THREADS"),
        "scores": {k: round(s, 4) for k, s, _ in results},
    }
    print(json.dumps({k: v for k, v in report.items() if k != "scores"}))
    if ns.json:
        ns.json.write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
