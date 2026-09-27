"""Normalized rows: one shape for every store the report reads.

``row_from_bench_line`` is the only place that understands the raw ``bench.jsonl``
line. It recomputes intent-to-treat stats from per-doc scores when the line did
not emit them (legacy lines) and separates *failure events* (records) from *failed
documents* (documents that produced no score and enter the ITT pool at 0).
"""

from __future__ import annotations

import json
import statistics
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench.benchmarks import BENCHMARKS, LEGACY_STAGE_TO_BENCHMARK
from neurotic_docx_bench.ledger.pins import ToolPin
from neurotic_docx_bench.ledger.registry import Registry

Provenance = Literal["stamped", "legacy"]


class ResultRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: Literal["bench", "converter"]
    id_run: str
    tool_id: str
    display: str
    affiliated: bool
    benchmark: str
    lens: str = "pixel"
    pin: ToolPin
    timestamp: datetime
    corpus_revision: str | None = None
    docset_id: str | None = None
    renderer_id: str | None = None
    scorer: str = "v1"
    n_scored: int
    n_failed_docs: int
    n_failure_events: int
    n_oracle_unmatched: int = 0
    itt_n: int
    itt_mean: float
    itt_median: float
    itt_approx: bool = False
    mean: float
    median: float
    exact_100: int
    scores: dict[str, float] = {}
    holdout_mode: str | None = None
    hardware: dict[str, object] | None = None
    render: str | None = None
    run_name: str | None = None
    configuration: str | None = None

    @property
    def provenance(self) -> Provenance:
        """Return "stamped" when a corpus revision and scores exist and ITT is not approximate.

        Otherwise return "legacy".
        """
        if self.corpus_revision and self.scores and not self.itt_approx:
            return "stamped"
        return "legacy"


def _num(value: object, default: float = 0.0) -> float:
    """Convert numbers or numeric text, using default for booleans or invalid text.

    TypeError and ValueError from text conversion use default; OverflowError
    from converting an integer to float propagates.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except TypeError, ValueError:
        return default


def _run_meta(data: dict) -> tuple[str, str]:
    """Read the first configured run's name/render, falling back to tool/render or empty text."""
    env = data.get("environment_config") or {}
    runs = env.get("runs") if isinstance(env, dict) else None
    first = (
        runs[0] if isinstance(runs, list) and runs and isinstance(runs[0], dict) else {}
    )
    run_name = str(first.get("name") or data.get("tool") or "")
    render = str(first.get("render") or data.get("render") or "")
    return run_name, render


def _benchmark_name(data: dict) -> str | None:
    """Return a known benchmark or None, using legacy stage only when benchmark is falsy."""
    name = data.get("benchmark")
    if not name and isinstance(data.get("stage"), str):
        name = LEGACY_STAGE_TO_BENCHMARK.get(data["stage"])
    return name if name in BENCHMARKS else None


def _timestamp(data: dict) -> datetime:
    """Parse timestamp or run_ts, using the UTC epoch for missing or invalid ISO text.

    Treat naive timestamps as UTC and preserve offsets already present.
    """
    raw = data.get("timestamp") or data.get("run_ts") or ""
    try:
        ts = datetime.fromisoformat(str(raw))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=UTC)
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def _failed_docs(data: dict) -> list[str]:
    """Return truthy document IDs from failure mappings as strings, preserving duplicates."""
    out: list[str] = []
    for f in data.get("failures") or []:
        if isinstance(f, dict) and f.get("doc"):
            out.append(str(f["doc"]))
    return out


def row_from_bench_line(data: dict, registry: Registry) -> ResultRow | None:
    """Normalize a bench record, returning None for an unknown benchmark or unresolved tool.

    Use emitted intent-to-treat (ITT) statistics when both ``itt_median`` and
    ``itt_n_docs`` are non-None. Otherwise, nonempty scores are pooled with one
    zero per distinct failed document lacking a score. Without scores, approximate
    the pool using ``n_docs`` copies of ``overall_median`` and one zero per failure
    event. Recomputed means and medians are rounded to four decimal places.

    Malformed record structures and numeric count conversions can raise
    AttributeError, TypeError, ValueError, or OverflowError; model validation
    errors also propagate. These errors are not converted to None.
    """
    benchmark = _benchmark_name(data)
    if benchmark is None:
        return None
    vendor = str(data.get("vendor") or data.get("tool") or "")
    run_name, render = _run_meta(data)
    entry = registry.resolve_bench(vendor=vendor, run_name=run_name, render=render)
    if entry is None:
        return None

    scores_raw = data.get("scores")
    scores = (
        {str(k): _num(v) for k, v in scores_raw.items()}
        if isinstance(scores_raw, dict)
        else {}
    )
    failures = data.get("failures") or []
    n_failure_events = (
        len(failures)
        if isinstance(failures, list)
        else int(_num(data.get("n_failures")))
    )
    failed_docs = set(_failed_docs(data))
    n_scored = len(scores) if scores else int(_num(data.get("n_docs")))

    if data.get("itt_median") is not None and data.get("itt_n_docs") is not None:
        itt_n = int(_num(data["itt_n_docs"]))
        itt_mean = _num(data.get("itt_mean"))
        itt_median = _num(data["itt_median"])
        itt_approx = False
        n_failed_docs = (
            len(failed_docs - scores.keys()) if scores else max(itt_n - n_scored, 0)
        )
    elif scores:
        zeroed = sorted(failed_docs - scores.keys())
        values = list(scores.values()) + [0.0] * len(zeroed)
        itt_n = len(values)
        itt_mean = round(statistics.mean(values), 4)
        itt_median = round(statistics.median(values), 4)
        itt_approx = False
        n_failed_docs = len(zeroed)
    else:
        n_failed_docs = n_failure_events
        values = [_num(data.get("overall_median"))] * n_scored + [0.0] * n_failed_docs
        itt_n = len(values)
        itt_mean = round(statistics.mean(values), 4) if values else 0.0
        itt_median = round(statistics.median(values), 4) if values else 0.0
        itt_approx = True

    hardware = data.get("hardware")
    return ResultRow(
        source="bench",
        id_run=str(data.get("id_run") or data.get("uuid7") or ""),
        tool_id=entry.id,
        display=entry.display,
        affiliated=entry.affiliated,
        benchmark=benchmark,
        lens="pixel",
        pin=ToolPin.parse(data.get("tool_version")),
        timestamp=_timestamp(data),
        corpus_revision=(
            str(data["corpus_revision"]) if data.get("corpus_revision") else None
        ),
        docset_id=(str(data["docset_id"]) if data.get("docset_id") else None),
        renderer_id=(str(data["renderer_id"]) if data.get("renderer_id") else None),
        scorer=str(data.get("scorer") or "v1"),
        n_scored=n_scored,
        n_failed_docs=n_failed_docs,
        n_failure_events=n_failure_events,
        n_oracle_unmatched=int(_num(data.get("n_oracle_unmatched"))),
        itt_n=itt_n,
        itt_mean=itt_mean,
        itt_median=itt_median,
        itt_approx=itt_approx,
        mean=_num(data.get("overall_mean")),
        median=_num(data.get("overall_median")),
        exact_100=int(_num(data.get("exact_100"))),
        scores=scores,
        holdout_mode=(str(data["holdout_mode"]) if data.get("holdout_mode") else None),
        hardware=hardware if isinstance(hardware, dict) else None,
        render=render or None,
        run_name=run_name or None,
        configuration=entry.configuration,
    )


def load_bench_rows(
    path: Path, registry: Registry
) -> tuple[list[ResultRow], list[dict]]:
    """Read UTF-8 JSONL into normalized rows and metadata summaries of unmapped records.

    Skip blank lines and invalid JSON. Unknown benchmarks or unresolved tools
    produce summaries with vendor, run_name, benchmark, and id_run, rather than
    full input records. Preserve input order within each returned list.

    File read and decoding errors propagate, as do normalization errors from
    ``row_from_bench_line``; valid JSON that is not a mapping is not skipped.
    """
    rows: list[ResultRow] = []
    unmapped: list[dict] = []
    with Path(path).open(encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            row = row_from_bench_line(data, registry)
            if row is None:
                run_name, _ = _run_meta(data)
                unmapped.append(
                    {
                        "vendor": data.get("vendor") or data.get("tool"),
                        "run_name": run_name,
                        "benchmark": data.get("benchmark") or data.get("stage"),
                        "id_run": data.get("id_run"),
                    }
                )
                continue
            rows.append(row)
    return rows, unmapped
