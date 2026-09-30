#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = ["neurotic-docx-bench[gpu]"]
#
# [tool.uv.sources]
# neurotic-docx-bench = { path = "..", editable = true }
# ///
"""A/B the scorer kernels across devices on one random sample of documents.

For a seeded random sample of matched (oracle, candidate) redline pairs, the script
runs the raster + score stage once per device (default: the numpy path, then
``mps``), with the content cache off and a fresh work folder per pass, and reports
per device: the backend that actually ran (an unavailable device falls back to numpy
with a warning, and the table says so), wall time, raster and score seconds, and the
ITT mean and median of the overall scores. Every device after the first is compared
document by document against the first one: max and mean absolute difference and
the number of documents whose score moved by more than ``--tolerance`` points.

Generation and rendering are not timed: ``--device`` only touches the scorer, so the
candidates must already be PDFs (a ``runs/<run>_<stamp>/pdf`` folder from ``bench
run --only <run>``, or any folder of ``<base>_<next>_<tool>_redline.pdf`` files). The
run name is the one in ``bench.yaml`` (``jubarte-rust``, not ``jubarte``). The script
header already pulls the ``gpu`` extra, so plain ``uv run`` is enough.

Examples (from the repository root)::

    uv run scripts/device_ab.py                       # --run jubarte-rust, the bench.yaml run name
    uv run scripts/device_ab.py --candidates runs/jubarte-rust_2026-09-26_14-41/pdf --tool jubarte-rust
    uv run scripts/device_ab.py --run jubarte-rust --devices numpy,cpu,mps --seed 11 --repeat 3

Nothing is written under ``results/``; the JSON report goes to ``--json`` (default
``out/device_ab_<seed>.json``).
"""

from __future__ import annotations

import json
import os
import random
import statistics
import tempfile
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from neurotic_docx_bench import content_cache, hardware, kernels, pipeline
from neurotic_docx_bench.config import load_config

console = Console()
app = typer.Typer(add_completion=False)

NUMPY = "numpy"


def newest_run_pdfs(runs_dir: Path, run: str) -> Path:
    """The ``pdf`` folder of the newest ``runs/<run>_<stamp>`` work folder."""
    candidates = sorted(
        (p for p in runs_dir.glob(f"{run}_*") if (p / "pdf").is_dir()),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise typer.BadParameter(
            f"no {runs_dir}/{run}_*/pdf folder; run `bench run --only {run}` first or pass --candidates"
        )
    return candidates[-1] / "pdf"


def oracle_dirs(config: Path, override: Path | None) -> list[Path]:
    if override is not None:
        return [override]
    cfg = load_config(config)
    return [cfg.source_of_truth, *cfg.extra_oracle_dirs]


def pick_keys(keys: list[str], sample: int, seed: int) -> list[str]:
    ordered = sorted(keys)
    if sample >= len(ordered):
        return ordered
    return sorted(random.Random(seed).sample(ordered, sample))


def score_pass(
    *,
    device: str,
    oracles: list[Path],
    candidates: Path,
    tool: str | None,
    keys: set[str],
    dpi: int,
    jobs: int,
) -> dict[str, Any]:
    """One uncached raster + score pass over ``keys`` on ``device``."""
    spec = None if device == NUMPY else device
    fallbacks: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with kernels.device_env(spec), tempfile.TemporaryDirectory(prefix=f"device-ab.{device}.") as work:
            backend = kernels.backend_id()
            t0 = time.perf_counter()
            per_doc = pipeline.score_folders_full(
                oracles,
                candidates,
                Path(work),
                dpi=dpi,
                jobs=jobs,
                candidate_tool=tool,
                only_keys=keys,
                strict_filter_keys=False,
            )
            wall = time.perf_counter() - t0
        fallbacks = [str(w.message) for w in caught if "using the numpy path" in str(w.message)]
    docs = {
        key: {
            "score": pipeline.overall_from_result(result),
            "raster_s": result.get("raster_ns", 0) / 1e9,
            "score_s": result.get("score_ns", 0) / 1e9,
        }
        for key, result in per_doc.items()
    }
    itt = [docs[k]["score"] if k in docs else 0.0 for k in sorted(keys)]
    return {
        "device": device,
        "backend": backend,
        "fell_back": bool(fallbacks) or (spec is not None and backend == NUMPY),
        "warnings": fallbacks,
        "wall_s": wall,
        "raster_s": sum(d["raster_s"] for d in docs.values()),
        "score_s": sum(d["score_s"] for d in docs.values()),
        "scored": len(docs),
        "itt_mean": statistics.fmean(itt) if itt else 0.0,
        "itt_median": statistics.median(itt) if itt else 0.0,
        "docs": docs,
    }


def compare(base: dict[str, Any], other: dict[str, Any], tolerance: float) -> dict[str, Any]:
    deltas = {k: other["docs"][k]["score"] - base["docs"][k]["score"] for k in base["docs"] if k in other["docs"]}
    missing = sorted(set(base["docs"]) ^ set(other["docs"]))
    moved = sorted((k for k, d in deltas.items() if abs(d) > tolerance), key=lambda k: -abs(deltas[k]))
    return {
        "against": base["device"],
        "compared": len(deltas),
        "max_abs_delta": max((abs(d) for d in deltas.values()), default=0.0),
        "mean_abs_delta": statistics.fmean(abs(d) for d in deltas.values()) if deltas else 0.0,
        "moved": moved,
        "scored_on_one_side_only": missing,
        "speedup_wall": base["wall_s"] / other["wall_s"] if other["wall_s"] else None,
        "speedup_score_stage": base["score_s"] / other["score_s"] if other["score_s"] else None,
    }


def render(passes: list[dict[str, Any]], comparisons: dict[str, dict[str, Any]], tolerance: float) -> Table:
    table = Table(
        box=box.SIMPLE_HEAD,
        padding=(0, 1),
        collapse_padding=True,
        caption=(
            "seconds; raster and score are per-document stage sums, wall is the pass; "
            f"max|Δ| and moved (>{tolerance:g} points) are against the first device of the cycle; "
            "× is the baseline wall over this wall"
        ),
    )
    for col in (
        "cyc",
        "device",
        "backend",
        "wall",
        "raster",
        "score",
        "doc/s",
        "mean",
        "median",
        "max|Δ|",
        "moved",
        "×",
    ):
        table.add_column(col, justify="left" if col in ("cyc", "device", "backend") else "right", no_wrap=True)
    for p in passes:
        cmp = comparisons.get(f"{p['cycle']}:{p['device']}")
        backend = p["backend"] + (" (fallback)" if p["fell_back"] else "")
        table.add_row(
            str(p["cycle"]),
            p["device"],
            backend,
            f"{p['wall_s']:.2f}",
            f"{p['raster_s']:.2f}",
            f"{p['score_s']:.2f}",
            f"{p['scored'] / p['wall_s']:.2f}" if p["wall_s"] else "n/a",
            f"{p['itt_mean']:.2f}",
            f"{p['itt_median']:.2f}",
            f"{cmp['max_abs_delta']:.3f}" if cmp else "-",
            str(len(cmp["moved"])) if cmp else "-",
            f"{cmp['speedup_wall']:.2f}" if cmp and cmp["speedup_wall"] else "-",
        )
    return table


@app.command()
def main(
    run: str = typer.Option(
        "jubarte-rust", "--run", help="bench.yaml run name: picks runs/<run>_*/pdf and the tool token"
    ),
    candidates: Path | None = typer.Option(None, "--candidates", help="folder of candidate redline PDFs"),
    tool: str | None = typer.Option(None, "--tool", help="tool token in candidate names; default: --run"),
    config: Path = typer.Option(Path("bench.yaml"), "--config", "-c"),
    oracle: Path | None = typer.Option(None, "--oracle", help="one oracle folder instead of the config's"),
    runs_dir: Path = typer.Option(Path("runs"), "--runs-dir"),
    sample: int = typer.Option(100, "--sample", min=1, help="documents drawn at random from the matched pairs"),
    seed: int | None = typer.Option(None, "--seed", help="sample seed; default: a fresh random one, printed"),
    devices: str = typer.Option("numpy,mps", "--devices", help="comma list; the first is the baseline"),
    jobs: int = typer.Option(os.cpu_count() or 1, "--jobs", "-j"),
    dpi: int | None = typer.Option(None, "--dpi", help="default: the config's scoring.dpi"),
    repeat: int = typer.Option(1, "--repeat", min=1, help="cycles over the device list (variance check)"),
    tolerance: float = typer.Option(0.01, "--tolerance", help="points; a larger per-doc move counts as moved"),
    json_out: Path | None = typer.Option(None, "--json", help="default: out/device_ab_<seed>.json"),
) -> None:
    """Score the same random sample with and without the torch backend and compare."""
    tool = tool or run
    cand_dir = candidates if candidates is not None else newest_run_pdfs(runs_dir, run)
    oracles = oracle_dirs(config, oracle)
    use_dpi = dpi if dpi is not None else load_config(config).scoring.dpi
    device_list = [d.strip() for d in devices.split(",") if d.strip()]
    for d in device_list:
        if d != NUMPY and d not in kernels.DEVICE_SPECS:
            raise typer.BadParameter(
                f"unknown device {d!r}; expected numpy or one of {', '.join(kernels.DEVICE_SPECS)}"
            )
    if seed is None:
        seed = random.SystemRandom().randrange(2**31)

    matched = pipeline.match_by_stem(oracles, cand_dir, candidate_tool=tool)
    if not matched:
        raise typer.BadParameter(f"no candidate in {cand_dir} matches an oracle in {oracles} for tool {tool!r}")
    keys = pick_keys([m[0] for m in matched], sample, seed)
    console.print(
        f"{len(matched)} matched pairs in {cand_dir}; sample {len(keys)} (seed {seed}), dpi {use_dpi}, "
        f"jobs {jobs}, devices {', '.join(device_list)}, cache off"
    )
    content_cache.configure(None)

    passes: list[dict[str, Any]] = []
    comparisons: dict[str, dict[str, Any]] = {}
    for cycle in range(1, repeat + 1):
        baseline: dict[str, Any] | None = None
        for device in device_list:
            console.print(f"cycle {cycle}: {device} ...", end=" ")
            result = score_pass(
                device=device,
                oracles=oracles,
                candidates=cand_dir,
                tool=tool,
                keys=set(keys),
                dpi=use_dpi,
                jobs=jobs,
            )
            result["cycle"] = cycle
            console.print(f"{result['backend']} {result['wall_s']:.2f} s")
            for w in result["warnings"]:
                console.print(f"  [yellow]{w}[/yellow]")
            passes.append(result)
            if baseline is None:
                baseline = result
            else:
                comparisons[f"{cycle}:{device}"] = compare(baseline, result, tolerance)
    console.print(render(passes, comparisons, tolerance))
    for key, cmp in comparisons.items():
        if cmp["moved"]:
            shown = ", ".join(cmp["moved"][:5])
            console.print(f"{key}: {len(cmp['moved'])} document(s) moved by more than {tolerance:g}: {shown}")
        if cmp["scored_on_one_side_only"]:
            console.print(f"[red]{key}: scored on one side only: {cmp['scored_on_one_side_only']}[/red]")
    if any(p["fell_back"] for p in passes):
        console.print(
            "[red]a requested device fell back to the numpy path; that pass measures numpy, not the device[/red]"
        )

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "seed": seed,
        "sample": len(keys),
        "keys": keys,
        "candidates": str(cand_dir),
        "oracles": [str(o) for o in oracles],
        "tool": tool,
        "dpi": use_dpi,
        "jobs": jobs,
        "tolerance": tolerance,
        "scorer_fingerprint": content_cache.scorer_fingerprint(),
        "raster_engine": content_cache.raster_engine(),
        "hardware": hardware.hardware_info(),
        "passes": passes,
        "comparisons": comparisons,
    }
    out = json_out if json_out is not None else Path("out") / f"device_ab_{seed}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    console.print(f"wrote {out}")


if __name__ == "__main__":
    app()
