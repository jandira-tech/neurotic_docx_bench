"""Per-stage timing summaries for ``bench profile`` (plan item 9b).

Pure functions over the per-document timings that ``bench run`` already collects
(``generate_s``, ``render_s``, ``raster_s``, ``score_s`` seconds per document key).
The CLI samples a deterministic subset of the source documents, drives the normal
pipeline with the content cache disabled, and hands the timings here for
aggregation; nothing in this module touches the filesystem.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any, TypedDict

from neurotic_docx_bench import content_cache, kernels

STAGES: tuple[str, ...] = ("generate_s", "render_s", "raster_s", "score_s")


class StageStats(TypedDict):
    n: int
    total_s: float
    mean_s: float
    median_s: float
    p95_s: float
    max_s: float
    share: float


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile of ``values`` (``pct`` in 0..100)."""
    if not values:
        raise ValueError("percentile of an empty sample")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def summarize(timings: dict[str, dict[str, float]]) -> dict[str, StageStats]:
    """Aggregate per-document stage seconds into per-stage statistics.

    Stages appear in pipeline order and only when at least one document timed
    them. ``share`` is the stage total over the sum of every stage total, so the
    shares of one summary add up to one.
    """
    samples: dict[str, list[float]] = {stage: [] for stage in STAGES}
    for per_doc in timings.values():
        for stage in STAGES:
            value = per_doc.get(stage)
            if value is not None:
                samples[stage].append(float(value))
    grand = sum(sum(v) for v in samples.values())
    out: dict[str, StageStats] = {}
    for stage in STAGES:
        values = samples[stage]
        if not values:
            continue
        total = sum(values)
        out[stage] = StageStats(
            n=len(values),
            total_s=total,
            mean_s=total / len(values),
            median_s=_median(values),
            p95_s=percentile(values, 95),
            max_s=max(values),
            share=(total / grand) if grand else 0.0,
        )
    return out


def sample_files(files: list[Path], n: int, seed: int) -> list[Path]:
    """Deterministic sample of ``n`` paths (sorted), the whole list when ``n`` covers it."""
    ordered = sorted(files)
    if n >= len(ordered):
        return ordered
    return sorted(random.Random(seed).sample(ordered, n))


def build_report(
    runs: dict[str, dict[str, Any]],
    *,
    sample: int,
    seed: int,
    dpi: int,
    backend: str | None = None,
) -> dict[str, Any]:
    """Assemble the ``bench profile --json`` document.

    ``runs`` maps run name to ``{"renderer_id", "wall_s", "benchmarks": {benchmark:
    {doc_key: {stage: seconds}}}}``; every benchmark is kept, summarised (empty when
    no document timed it). ``backend`` is the scorer kernel backend the sample ran on
    (``kernels.backend_id()`` at run time; the current one when omitted).
    """
    return {
        "cached": False,
        "sample": sample,
        "seed": seed,
        "dpi": dpi,
        "scorer_fingerprint": content_cache.scorer_fingerprint(),
        "raster_engine": content_cache.raster_engine(),
        "scorer_backend": backend if backend is not None else kernels.backend_id(),
        "runs": {
            name: {
                "renderer_id": run.get("renderer_id"),
                "wall_s": run.get("wall_s"),
                "benchmarks": {
                    bench: summarize(timings)
                    for bench, timings in run.get("benchmarks", {}).items()
                },
            }
            for name, run in runs.items()
        },
    }


def table_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten a report into one row per run, benchmark and stage (stage order)."""
    rows: list[dict[str, Any]] = []
    for run_name, run in report["runs"].items():
        for bench, stats in run["benchmarks"].items():
            for stage in STAGES:
                if stage not in stats:
                    continue
                rows.append({"run": run_name, "benchmark": bench, "stage": stage, **stats[stage]})
    return rows


def render_tables(report: dict[str, Any]) -> list[Any]:
    """One rich table per run: a row per benchmark stage, the run's wall time and
    renderer in the title. Narrow enough for an 80-column terminal."""
    from rich import box
    from rich.table import Table

    tables: list[Any] = []
    for run_name, run in report["runs"].items():
        wall = run.get("wall_s")
        wall_text = f"{wall:.2f} s" if isinstance(wall, (int, float)) else "n/a"
        table = Table(
            title=f"{run_name}: wall {wall_text}, renderer {run.get('renderer_id')}",
            box=box.SIMPLE_HEAD,
            padding=(0, 1),
            collapse_padding=True,
        )
        for col in ("benchmark", "stage", "n", "total", "mean", "median", "p95", "max", "share"):
            table.add_column(col, justify="left" if col in ("benchmark", "stage") else "right", no_wrap=True)
        for row in table_rows(report):
            if row["run"] != run_name:
                continue
            table.add_row(
                row["benchmark"],
                row["stage"].removesuffix("_s"),
                str(row["n"]),
                f"{row['total_s']:.2f}",
                f"{row['mean_s']:.3f}",
                f"{row['median_s']:.3f}",
                f"{row['p95_s']:.3f}",
                f"{row['max_s']:.3f}",
                f"{row['share'] * 100:.1f}%",
            )
        tables.append(table)
    return tables
