"""Schema-v4 typed ``Results`` JSONL emission — one self-contained line per
``(vendor, benchmark)`` pair.

Each line is a serialised :class:`~neurotic_docx_bench.results_schema.Results`
with stable key order: ``id_run``, ``vendor``, ``benchmark`` first, followed by
aggregate scores, speed stats, config metadata, and embedded per-doc detail.

Legacy read helpers (``read_lines``, ``last_line_for_tool``, ``has_already_ran``)
can still consume v2 lines (multi-benchmark-in-one) and v3 lines (``tool``/``stage``
keyed).  New production emission MUST go through ``build_results_line`` →
``append_line`` (or ``append_if_changed``).  ``build_line`` is deprecated and
retained only for backward-compatible test assertions.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from neurotic_docx_bench.aggregate import compute_aggregate
from neurotic_docx_bench.benchmarks import BenchmarkName
from neurotic_docx_bench.config import BenchConfig
from neurotic_docx_bench.results_schema import build_results as build_typed_results

SCHEMA = 4

# Default stage names. The render-* stages are claimed by Phase D (playwright).
STAGE_REDLINE = "redline"
STAGE_ACCEPTED = "accepted"
STAGE_ROUNDTRIP = "roundtrip"


PerDocResult = dict[str, list[dict[str, float]]]
FailureEntry = dict[str, str]
JsonlLine = dict[str, object]


def build_line(
    *,
    tool: str,
    tool_version: str | None,
    render: str,
    baseline_ref: str,
    scores: dict[str, float],
    stage: str = STAGE_REDLINE,
    per_doc: dict[str, dict[str, float | int | bool | list[dict[str, object]] | dict[str, object]]] | None = None,
    failures: list[dict[str, str]] | None = None,
    timings: dict[str, dict[str, float]] | None = None,
    config_hash: str,
    run_id: str,
    run_ts: str,
    git_sha: str,
    uuid7_str: str | None = None,
    datetime_iso: str | None = None,
) -> dict[str, object]:
    """Assemble one schema-v3 line for a single ``(tool, stage)``.

    **Deprecated** — use :func:`build_results_line` for all new emissions.
    This function is kept only so that backward-compatible readers (tests,
    snapshots, gate) can still be exercised against legacy-v3-shaped dicts.

    Scores are rounded to 4 dp for stable change-detection.

    ``failures`` records which documents did NOT work and why — each entry is
    ``{"doc": <base>_<next>, "stage": "generate"|"missing_source"|"render", "error": str}`` —
    so every run permanently logs what it couldn't redline/render/score.

    ``timings`` records per-doc step durations (seconds, from ``perf_counter_ns``):
    ``{"<base>_<next>": {"generate_s": …, "render_s": …, "raster_s": …, "score_s": …}}``.

    ``uuid7_str`` defaults to a fresh ``uuid.uuid7()`` (Python 3.14 native); ``datetime_iso``
    defaults to ``datetime.now(UTC).isoformat()``. The JSONL key order leads with ``tool``
    so a ``head -1 | jq .tool`` works.
    """
    rounded = {k: round(float(v), 4) for k, v in scores.items()}
    aggregate = compute_aggregate(rounded, per_doc=per_doc).to_dict()
    failures = failures or []
    timings = timings or {}
    return {
        "tool": tool,
        "stage": stage,
        "tool_version": tool_version,
        "uuid7": uuid7_str or str(uuid.uuid7()),
        "run_id": run_id,
        "run_ts": run_ts,
        "datetime": datetime_iso or datetime.now(UTC).isoformat(),
        "render": render,
        "git_sha": git_sha,
        "baseline_ref": baseline_ref,
        "config_hash": config_hash,
        "vendor": tool,  # schema v4 compatibility: tool name doubles as vendor
        "schema": SCHEMA,
        "n_docs": len(rounded),
        "n_failures": len(failures),
        "scores": rounded,
        "aggregate": aggregate,
        "failures": failures,
        "timings": timings,
    }


def build_results_line(
    *,
    id_run: uuid.UUID,
    vendor: str,
    benchmark: BenchmarkName,
    scores: dict[str, float],
    per_doc: dict[str, dict[str, object]] | None,
    speed_samples_ms: list[float],
    environment_config: BenchConfig,
    timestamp: datetime,
    tool_version: str | None = None,
    build_recipe: dict[str, list[str]] | None = None,
    config_hash: str | None = None,
    failures: list[dict[str, str]] | None = None,
    timings: dict[str, dict[str, float]] | None = None,
    n_oracle_unmatched: int | None = None,
    scorer: str = "v1",
    corpus_revision: str | None = None,
    holdout_mode: str | None = None,
) -> dict[str, object]:
    """Build a schema-v4 ``Results`` JSONL dict from a vendor×benchmark outcome.

    This is the canonical emission path: each line is a self-contained
    :class:`~neurotic_docx_bench.results_schema.Results` keyed by
    ``id_run``/``vendor``/``benchmark``. ``tool_version`` and ``config_hash`` are
    carried so skip-already-ran and change-detection can key on the full identity
    without a separate legacy ``tool``/``stage`` line. ``build_recipe`` (TODO §2)
    records the wasm build flags that shape the artifact beyond the engine pin.
    ``scores``/``per_doc``/
    ``failures``/``timings`` are embedded so the gate, snapshots, and consumers
    can read per-doc data from the one line.
    """
    return build_typed_results(
        id_run=id_run,
        vendor=vendor,
        benchmark=benchmark,
        scores=scores,
        per_doc=per_doc,
        speed_samples_ms=speed_samples_ms,
        environment_config=environment_config,
        timestamp=timestamp,
        tool_version=tool_version,
        build_recipe=build_recipe,
        config_hash=config_hash,
        failures=failures,
        timings=timings,
        n_oracle_unmatched=n_oracle_unmatched,
        scorer=scorer,
        corpus_revision=corpus_revision,
        holdout_mode=holdout_mode,
    ).to_json_dict()


def read_lines(jsonl_path: Path) -> list[dict[str, object]]:
    if not jsonl_path.is_file():
        return []
    out: list[dict[str, object]] = []
    for raw in jsonl_path.read_text().splitlines():
        raw = raw.strip()
        if raw:
            out.append(cast("dict[str, object]", json.loads(raw)))
    return out


def has_already_ran(
    jsonl_path: Path,
    *,
    tool: str,
    tool_version: str | None,
    config_hash: str,
    stage: str = STAGE_REDLINE,
) -> dict[str, object] | None:
    """Return the matching prior line if ``(tool, stage, tool_version, config_hash)``
    already exists in the JSONL log, else None. Used by ``bench run`` to skip unchanged
    reruns (Phase B: skip-already-ran by default; ``--rerun`` / ``BENCH_RERUN=1`` overrides).

    Legacy v2 lines (no ``stage`` key) are treated as ``"redline"``.
    """
    if tool_version is None:
        return None
    for line in read_lines(jsonl_path):
        if (
            line.get("tool") == tool
            and line.get("stage", STAGE_REDLINE) == stage
            and line.get("tool_version") == tool_version
            and line.get("config_hash") == config_hash
        ):
            return line
    return None


def last_line_for_tool(
    jsonl_path: Path,
    tool: str,
    render: str | None = None,
    stage: str = STAGE_REDLINE,
) -> dict[str, object] | None:
    """Most recent line for this ``(tool, stage)`` (optionally scoped to a ``render``
    backend). Legacy v2 lines (no ``stage`` key) are treated as ``"redline"``.
    """
    match = None
    for line in read_lines(jsonl_path):
        if line.get("tool") != tool:
            continue
        if render is not None and line.get("render") != render:
            continue
        if line.get("stage", STAGE_REDLINE) != stage:
            continue
        match = line
    return match


def _changed(new: dict[str, object], prev: dict[str, object]) -> bool:
    """A run changed iff its rounded ``scores`` differ from the last line for the same
    identity. Schema-v3 lines also compare the nested ``aggregate`` dict; schema-v4
    ``Results`` lines carry aggregate fields at the top level, so ``scores`` alone is
    sufficient and stable there.
    """
    if new.get("scores") != prev.get("scores"):
        return True
    # Legacy v3 lines embed an ``aggregate`` dict; compare it too for back-compat.
    if "aggregate" in new or "aggregate" in prev:
        return new.get("aggregate") != prev.get("aggregate")
    return False


def append_line(jsonl_path: Path, line: dict[str, object]) -> bool:
    """Always append ``line`` to the JSONL trend log (never truncates/rewrites the file).

    This is the default: the log is an append-only history where every run is recorded.
    Returns True (a line was appended).

    Crash-safety: the line is serialised, written to a sibling ``*.tmp`` file, then
    appended to the log under an exclusive ``fcntl.flock`` and ``fsync``-flushed. A
    crash mid-write therefore leaves at most the tmp file orphaned — the trend log
    itself is never left with a truncated last line (which would corrupt every
    subsequent skip-already-ran / delta-log read). Concurrent ``bench`` invocations
    on the same ``results/`` serialise on the lock.
    """
    import fcntl
    import os

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    # sort_keys=False (the default) preserves the stable insertion order
    # required by the schema — id_run / vendor / benchmark first for v4
    # Results lines, tool / stage first for legacy v3 lines.  Python ≥3.7
    # guarantees dict insertion order.
    payload = json.dumps(line) + "\n"
    lock_path = jsonl_path.with_suffix(jsonl_path.suffix + ".lock")
    with lock_path.open("w") as lock_fh:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        # Append under the lock; fsync so the bytes hit disk before the lock drops.
        with jsonl_path.open("a", encoding="utf-8") as fh:
            _ = fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
    return True


def append_if_changed(jsonl_path: Path, line: dict[str, object]) -> bool:
    """Append ``line`` only if its scores/aggregate differ from the last line for the same
    ``(tool, stage, render)`` — the delta-log variant (PLAN §j). Returns True if appended,
    False if skipped as unchanged. Opt in via ``bench run --only-on-change``.

    Schema-v4 ``Results`` lines (``vendor``/``benchmark``) are matched on
    ``(vendor, benchmark)``; legacy v3 lines (``tool``/``stage``) keep matching on
    ``(tool, stage)``. The trend log is heterogeneous during the cut-over.
    """
    if "vendor" in line and "benchmark" in line:
        prev = last_line_for_benchmark(
            jsonl_path,
            cast("str", line["vendor"]),
            cast("str", line["benchmark"]),
        )
    else:
        prev = last_line_for_tool(
            jsonl_path,
            cast("str", line["tool"]),
            render=cast("str | None", line.get("render")),
            stage=cast("str", line.get("stage", STAGE_REDLINE)),
        )
    if prev is not None and not _changed(line, prev):
        return False
    return append_line(jsonl_path, line)


# --- schema v4: (vendor, benchmark)-keyed readers --------------------------------


def has_already_ran_benchmark(
    jsonl_path: Path,
    *,
    vendor: str,
    benchmark: str,
    tool_version: str | None,
    config_hash: str,
    holdout_only: bool | None = None,
) -> dict[str, object] | None:
    """Return the matching prior ``Results`` line if ``(vendor, benchmark,
    tool_version, config_hash)`` already exists, else None.

    Used by ``bench run`` to skip unchanged reruns. A line matches when its
    ``vendor``/``benchmark``/``tool_version``/``config_hash`` all agree; legacy
    schema-v3 lines (which lack ``benchmark``) never match.

    ``holdout_only`` (when given) additionally requires the line's
    ``holdout_mode`` to be — or not be — ``"only"``: a holdout-only rerun must
    never be satisfied by a full-corpus line, nor the reverse. Lines without the
    field (pre-holdout vintage) count as full-corpus, so normal-run identity is
    unchanged.
    """
    if tool_version is None:
        return None
    for line in read_lines(jsonl_path):
        if (
            line.get("vendor") == vendor
            and line.get("benchmark") == benchmark
            and line.get("tool_version") == tool_version
            and line.get("config_hash") == config_hash
            and (
                holdout_only is None
                or (line.get("holdout_mode") == "only") == holdout_only
            )
        ):
            return line
    return None


def last_line_for_benchmark(
    jsonl_path: Path, vendor: str, benchmark: str,
) -> dict[str, object] | None:
    """Most recent ``Results`` line for ``(vendor, benchmark)``."""
    match = None
    for line in read_lines(jsonl_path):
        if line.get("vendor") == vendor and line.get("benchmark") == benchmark:
            match = line
    return match
