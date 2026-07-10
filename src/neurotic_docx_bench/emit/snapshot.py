"""Per-(vendor, benchmark) accepted score baselines (schema v4).

Schema v4 snapshots live at ``results/score-snapshots/{vendor}__{benchmark}.json``
(tab-indented). Each benchmark (``script_redlines``, ``accepted_changes``,
``roundtrip``, ``visual_*``) is gated independently against its own baseline.

Legacy schema-v3 paths ``{tool}__{stage}.json`` (and the older ``{tool}.json``)
are still *read* by :func:`load_snapshot` via the stage→benchmark fallback so
existing baselines keep loading, but :func:`write_snapshot` always writes the
``{vendor}__{benchmark}.json`` path.
"""

from __future__ import annotations

import json
from pathlib import Path

from neurotic_docx_bench.benchmarks import LEGACY_STAGE_TO_BENCHMARK
from neurotic_docx_bench.emit.jsonl import STAGE_REDLINE
from neurotic_docx_bench.results_schema import BenchmarkName


def snapshot_path(snapshots_dir: Path, tool: str, stage: str = STAGE_REDLINE) -> Path:
    """Resolve the snapshot path for ``(tool, stage)``.

    For ``stage="redline"`` only, fall back to the legacy ``{tool}.json`` path if it
    exists and the stage-suffixed ``{tool}__redline.json`` does not — so pre-v3
    baselines keep loading.
    """
    staged = snapshots_dir / f"{tool}__{stage}.json"
    if stage == STAGE_REDLINE and not staged.is_file():
        legacy = snapshots_dir / f"{tool}.json"
        if legacy.is_file():
            return legacy
    return staged


def write_snapshot(
    snapshots_dir: Path, tool: str, scores: dict[str, float], stage: str = STAGE_REDLINE,
) -> Path:
    """Write ``{doc: score}`` as tab-indented, key-sorted JSON. Returns the path.

    Always writes the stage-suffixed path (``{tool}__{stage}.json``); legacy
    ``{tool}.json`` snapshots are left in place but superseded.
    """
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    path = snapshots_dir / f"{tool}__{stage}.json"
    rounded = {k: round(float(v), 4) for k, v in scores.items()}
    path.write_text(json.dumps(rounded, indent="\t", sort_keys=True) + "\n")
    return path


def load_snapshot(
    snapshots_dir: Path, tool: str, stage: str = STAGE_REDLINE,
) -> dict[str, float] | None:
    """Return the accepted baseline for ``(tool, stage)``, or ``None`` if none exists."""
    path = snapshot_path(snapshots_dir, tool, stage=stage)
    if not path.is_file():
        return None
    return {k: float(v) for k, v in json.loads(path.read_text()).items()}


# --- schema v4: (vendor, benchmark)-keyed snapshots ------------------------------


def snapshot_path_for_benchmark(
    snapshots_dir: Path, vendor: str, benchmark: BenchmarkName,
) -> Path:
    """Resolve the snapshot path for a ``(vendor, benchmark)`` pair.

    Falls back to the legacy ``{vendor}__{stage}.json`` (or ``{vendor}.json``)
    path by mapping the benchmark back to its legacy stage name — so baselines
    accepted under schema v3 keep loading after the cut-over.
    """
    primary = snapshots_dir / f"{vendor}__{benchmark}.json"
    if primary.is_file():
        return primary
    # Fall back to any legacy stage that maps to this benchmark.
    for legacy_stage, bm in LEGACY_STAGE_TO_BENCHMARK.items():
        if bm == benchmark:
            legacy_staged = snapshots_dir / f"{vendor}__{legacy_stage}.json"
            if legacy_staged.is_file():
                return legacy_staged
            if legacy_stage == STAGE_REDLINE:
                legacy_unstaged = snapshots_dir / f"{vendor}.json"
                if legacy_unstaged.is_file():
                    return legacy_unstaged
    return primary


def write_snapshot_for_benchmark(
    snapshots_dir: Path, vendor: str, benchmark: BenchmarkName, scores: dict[str, float],
) -> Path:
    """Write ``{doc: score}`` as tab-indented, key-sorted JSON to
    ``{vendor}__{benchmark}.json``. Returns the path.
    """
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    path = snapshots_dir / f"{vendor}__{benchmark}.json"
    rounded = {k: round(float(v), 4) for k, v in scores.items()}
    path.write_text(json.dumps(rounded, indent="\t", sort_keys=True) + "\n")
    return path


def load_snapshot_for_benchmark(
    snapshots_dir: Path, vendor: str, benchmark: BenchmarkName,
) -> dict[str, float] | None:
    """Return the accepted baseline for ``(vendor, benchmark)``, or ``None``."""
    path = snapshot_path_for_benchmark(snapshots_dir, vendor, benchmark)
    if not path.is_file():
        return None
    return {k: float(v) for k, v in json.loads(path.read_text()).items()}
