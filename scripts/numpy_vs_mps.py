"""Time the scorer on the same many-page fixtures under numpy and mps.

Waits until the machine is quiet (1-minute load average below ``--max-load`` for
``--quiet-samples`` samples in a row), then scores the ``--n`` fixtures with the most
pages once per backend, in the same process pool settings, and writes
``results/numpy_vs_mps_<stamp>.json``. The file carries ``started_at`` and
``last_at`` and is rewritten after every stage, so a killed run still says when it began
and how far it got.

    uv run python scripts/numpy_vs_mps.py --work results/jubarte_0.10.1_docx_to_pdf_work
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

os.environ["BENCH_NO_CACHE"] = "1"  # a cache hit would time nothing

import fitz  # noqa: E402

from neurotic_docx_bench import kernels  # noqa: E402
from neurotic_docx_bench.docx_to_pdf import score_folder_pair  # noqa: E402


def now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot() -> dict[str, float]:
    one, five, fifteen = os.getloadavg()
    return {"load1": one, "load5": five, "load15": fifteen, "cpus": os.cpu_count() or 1}


class Record:
    def __init__(self, path: Path, args: argparse.Namespace) -> None:
        self.path = path
        self.data: dict = {"started_at": now(), "last_at": now(), "stage": "waiting", "args": vars(args) | {"work": str(args.work)}}
        self.flush()

    def update(self, **fields: object) -> None:
        self.data.update(fields, last_at=now())
        self.flush()

    def flush(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, default=str))


def wait_until_quiet(rec: Record, max_load: float, quiet_samples: int, interval: float, give_up_s: float) -> bool:
    quiet = 0
    waited = 0.0
    while True:
        snap = snapshot()
        quiet = quiet + 1 if snap["load1"] < max_load else 0
        rec.update(stage="waiting", load=snap, quiet_samples=quiet)
        print(f"{now()} load1 {snap['load1']:.1f} (need < {max_load}), quiet {quiet}/{quiet_samples}", flush=True)
        if quiet >= quiet_samples:
            return True
        if waited >= give_up_s:
            return False
        time.sleep(interval)
        waited += interval


def pick_fixtures(work: Path, n: int) -> list[tuple[str, int]]:
    cand = {p.stem for p in (work / "jubarte" / "candidate").glob("*.pdf")}
    pages: list[tuple[str, int]] = []
    for pdf in (work / "oracle").glob("*.pdf"):
        if pdf.stem in cand:
            with fitz.open(pdf) as doc:
                pages.append((pdf.stem, doc.page_count))
    pages.sort(key=lambda t: (-t[1], t[0]))
    return pages[:n]


def stage_fixtures(work: Path, stems: list[str], dest: Path) -> tuple[Path, Path]:
    oracle, cand = dest / "oracle", dest / "candidate"
    for d in (oracle, cand):
        shutil.rmtree(d, ignore_errors=True)
        d.mkdir(parents=True)
    for stem in stems:
        shutil.copy2(work / "oracle" / f"{stem}.pdf", oracle / f"{stem}.pdf")
        shutil.copy2(work / "jubarte" / "candidate" / f"{stem}.pdf", cand / f"{stem}.pdf")
    return oracle, cand


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", type=Path, required=True, help="docx-to-pdf work dir holding oracle/ and jubarte/candidate/")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 8)
    ap.add_argument(
        "--configs",
        default="numpy,mps",
        help="comma list of backend[:jobs] to time on the same fixtures, e.g. mps:4,mps:12,numpy:12",
    )
    ap.add_argument("--dpi", type=int, default=144)
    ap.add_argument("--max-load", type=float, default=3.0, help="1-minute load average that counts as quiet")
    ap.add_argument("--quiet-samples", type=int, default=3)
    ap.add_argument("--interval", type=float, default=10.0)
    ap.add_argument("--give-up", type=float, default=3600.0, help="seconds to wait for a quiet machine")
    ap.add_argument("--out", type=Path, default=Path("results"))
    args = ap.parse_args()

    out = args.out / f"numpy_vs_mps_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    rec = Record(out, args)
    if not wait_until_quiet(rec, args.max_load, args.quiet_samples, args.interval, args.give_up):
        rec.update(stage="gave_up", note="machine never went quiet; nothing was timed")
        print(f"{now()} gave up waiting for a quiet machine", flush=True)
        return 2

    picked = pick_fixtures(args.work, args.n)
    stems = [s for s, _ in picked]
    scratch = args.out / "numpy_vs_mps_scratch"
    oracle, cand = stage_fixtures(args.work, stems, scratch)
    rec.update(stage="staged", fixtures=[{"stem": s, "pages": p} for s, p in picked], pages_total=sum(p for _, p in picked))

    runs: dict[str, dict] = {}
    for spec in args.configs.split(","):
        backend, _, j = spec.partition(":")
        jobs = int(j) if j else args.jobs
        name = f"{backend}_j{jobs}"
        before = snapshot()
        rec.update(stage=f"scoring:{name}", load_before=before)
        print(f"{now()} scoring {len(stems)} fixtures on {backend} with {jobs} workers", flush=True)
        with kernels.device_env(backend):
            t0 = time.monotonic()
            result = score_folder_pair(oracle, cand, scratch / f"score_{name}", dpi=args.dpi, jobs=jobs)
            wall = time.monotonic() - t0
            used = kernels.backend_id()
        scores = {k: v["overall_score"] for k, v in result.items()}
        shutil.rmtree(scratch / f"score_{name}", ignore_errors=True)  # rasters are not kept
        runs[name] = {
            "backend": used,
            "jobs": jobs,
            "wall_s": round(wall, 2),
            "s_per_doc": round(wall / max(1, len(scores)), 2),
            "mean": round(statistics.fmean(scores.values()), 4),
            "load_before": before,
            "load_after": snapshot(),
            "finished_at": now(),
            "scores": scores,
        }
        rec.update(runs=runs)
        print(f"{now()} {name}: {wall:.1f}s, mean {runs[name]['mean']}", flush=True)

    ref = next(iter(runs.values()))["scores"]
    rec.update(
        stage="done",
        wall_s_by_config={k: v["wall_s"] for k, v in runs.items()},
        max_abs_score_diff=max(abs(ref[k] - r["scores"][k]) for r in runs.values() for k in ref),
    )
    shutil.rmtree(scratch, ignore_errors=True)
    print(json.dumps({k: rec.data[k] for k in ("started_at", "last_at", "wall_s_by_config", "max_abs_score_diff")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
