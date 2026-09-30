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
    # Bench version that produced the line (absent before 0.7.0).
    bench_version: str | None = None
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
    # Documents that produced no score and enter the ITT pool at 0.
    failed_docs: tuple[str, ...] = ()
    holdout_mode: str | None = None
    hardware: dict[str, object] | None = None
    render: str | None = None
    run_name: str | None = None
    configuration: str | None = None
    # Secondary metrics of a multi-metric lens (docxide_metrics: ssim, text_boundary),
    # each as {"mean": x, "median": y}; the primary metric is in the score fields.
    extra: dict[str, dict[str, float]] = {}
    # Lens-disagreement bench-health alarm carried from the line; never a ranking input.
    n_lens_disagree: int | None = None
    lens_disagree_rate: float | None = None
    # True for rows read from results/archive/: history only, never ranked.
    archived: bool = False

    @property
    def provenance(self) -> Provenance:
        """"stamped" or "legacy". Approximate ITT is always legacy; a converter row is
        stamped when it names its docset, a bench row when it carries a corpus revision
        and per-document scores."""
        if self.itt_approx:
            return "legacy"
        if self.source == "converter":
            return "stamped" if self.docset_id else "legacy"
        if self.corpus_revision and self.scores:
            return "stamped"
        return "legacy"

    @property
    def key(self) -> str:
        """One run id can carry several benchmarks; this names one row."""
        return f"{self.id_run}|{self.benchmark}"

    def itt_scores(self) -> dict[str, float]:
        """Per-document scores over the ITT pool: scored docs plus failed docs at 0."""
        return {**self.scores, **{d: 0.0 for d in self.failed_docs}}


def _num(value: object, default: float = 0.0) -> float:
    """A number or numeric text as float; ``default`` for booleans, None and text that is
    not a number. An int too large for a float raises OverflowError."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except TypeError, ValueError:
        return default


def _run_meta(data: dict) -> tuple[str, str]:
    """(run name, render) of the first ``environment_config`` run, else the line's own
    ``tool`` / ``render``, else empty strings."""
    env = data.get("environment_config") or {}
    runs = env.get("runs") if isinstance(env, dict) else None
    first = (
        runs[0] if isinstance(runs, list) and runs and isinstance(runs[0], dict) else {}
    )
    run_name = str(first.get("name") or data.get("tool") or "")
    render = str(first.get("render") or data.get("render") or "")
    return run_name, render


def _benchmark_name(data: dict) -> str | None:
    """A known benchmark name or None; the legacy ``stage`` is read only when
    ``benchmark`` is empty."""
    name = data.get("benchmark")
    if not name and isinstance(data.get("stage"), str):
        name = LEGACY_STAGE_TO_BENCHMARK.get(data["stage"])
    return name if name in BENCHMARKS else None


def _timestamp(data: dict) -> datetime:
    """``timestamp``, else ``run_ts``, as an aware datetime: a naive value is UTC, an
    offset is kept, and missing or unparsable text is the UTC epoch."""
    raw = data.get("timestamp") or data.get("run_ts") or ""
    try:
        ts = datetime.fromisoformat(str(raw))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=UTC)
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)


def _failed_docs(data: dict) -> list[str]:
    """The non-empty ``doc`` of every failure record, as strings, duplicates kept."""
    out: list[str] = []
    for f in data.get("failures") or []:
        if isinstance(f, dict) and f.get("doc"):
            out.append(str(f["doc"]))
    return out


def row_from_bench_line(data: dict, registry: Registry) -> ResultRow | None:
    """One bench line as a ResultRow; None for an unknown benchmark or a tool the registry
    cannot resolve.

    ITT comes from the line when both ``itt_median`` and ``itt_n_docs`` are set. Else,
    with per-document scores, the pool is the scores plus one 0 per distinct failed
    document without a score. Without scores it is approximated: ``n_docs`` copies of
    ``overall_median`` plus one 0 per failure event (``itt_approx``). Recomputed means
    and medians are rounded to 4 places.

    A malformed line (a non-mapping, a count that does not convert) raises
    AttributeError, TypeError, ValueError or OverflowError, and pydantic validation
    errors propagate; none of them become None.
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
        bench_version=(
            str(data["bench_version"]) if data.get("bench_version") else None
        ),
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
        failed_docs=tuple(sorted(failed_docs - scores.keys())) if scores else (),
        holdout_mode=(str(data["holdout_mode"]) if data.get("holdout_mode") else None),
        hardware=hardware if isinstance(hardware, dict) else None,
        render=render or None,
        run_name=run_name or None,
        configuration=entry.configuration,
        n_lens_disagree=(
            int(_num(data["n_lens_disagree"]))
            if data.get("n_lens_disagree") is not None
            else None
        ),
        lens_disagree_rate=(
            _num(data["lens_disagree_rate"])
            if data.get("lens_disagree_rate") is not None
            else None
        ),
    )


def load_bench_rows(
    path: Path, registry: Registry, *, archived: bool = False
) -> tuple[list[ResultRow], list[dict]]:
    """All rows in the UTF-8 JSONL ``path``, plus a summary (vendor, run_name, benchmark,
    id_run) of each line the registry could not map, both in file order. ``archived``
    marks every row as history-only.

    Blank lines and invalid JSON are skipped. Read and decode errors propagate, as do
    ``row_from_bench_line`` errors: valid JSON that is not a mapping is not skipped.
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
            rows.append(row.model_copy(update={"archived": True}) if archived else row)
    return rows, unmapped


# ---- speed rows ---------------------------------------------------------------


class SpeedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool_id: str
    display: str
    affiliated: bool
    kind: Literal["large", "micro"]
    inproc: bool
    runtime: str
    pin: ToolPin
    timestamp: datetime
    fixture_count: int | None
    pair_count: int | None
    n: int
    failures: int
    median_ms: float
    mean_ms: float
    p95_ms: float | None
    hardware: dict[str, object] | None = None
    source_path: str = ""


_LARGE_KINDS = {"speed_redlines", "redline_speed_bench"}


def speed_row_from_line(
    data: dict, registry: Registry, *, source_path: str = ""
) -> SpeedRow | None:
    if str(data.get("unit") or "ms_per_redline") != "ms_per_redline":
        return None
    if data.get("error") and data.get("median") is None:
        return None
    kind: Literal["large", "micro"] = (
        "large" if str(data.get("kind") or "speed") in _LARGE_KINDS else "micro"
    )
    tool = str(data.get("tool") or data.get("engine") or "")
    entry, inproc = registry.resolve_speed(tool)
    if entry is None or not tool:
        return None
    n = int(_num(data.get("n")))
    if n <= 0:
        return None
    fixture = data.get("fixture_count", data.get("fixture_target"))
    pair = data.get("pair_count")
    hardware = data.get("hardware")
    return SpeedRow(
        tool_id=entry.id,
        display=entry.display,
        affiliated=entry.affiliated,
        kind=kind,
        inproc=inproc,
        runtime=str(data.get("runtime") or ""),
        pin=ToolPin.parse(data.get("tool_version")),
        timestamp=_timestamp(data),
        fixture_count=int(_num(fixture)) if fixture is not None else None,
        pair_count=int(_num(pair)) if pair is not None else None,
        n=n,
        failures=int(_num(data.get("failures"))),
        median_ms=_num(data.get("median")),
        mean_ms=_num(data.get("mean")),
        p95_ms=_num(data["p95"]) if data.get("p95") is not None else None,
        hardware=hardware if isinstance(hardware, dict) else None,
        source_path=source_path,
    )


def load_speed_rows(
    speed_jsonl: Path, summaries_root: Path, registry: Registry
) -> tuple[list[SpeedRow], list[dict]]:
    """Rows from ``results/speed.jsonl`` and every ``summary.json`` under
    ``results/redline_speed_bench``, plus the tool names the registry cannot map."""
    rows: list[SpeedRow] = []
    unmapped: list[dict] = []

    def ingest(
        data: dict, source: str, fixtures: object = None, pairs: object = None
    ) -> None:
        data = dict(data)
        if data.get("fixture_count") is None and fixtures is not None:
            data["fixture_count"] = fixtures
        if data.get("pair_count") is None and pairs is not None:
            data["pair_count"] = pairs
        row = speed_row_from_line(data, registry, source_path=source)
        if row is None:
            tool = data.get("tool") or data.get("engine")
            if tool and registry.resolve_speed(str(tool))[0] is None:
                unmapped.append({"tool": tool, "source": source})
            return
        rows.append(row)

    if Path(speed_jsonl).is_file():
        with Path(speed_jsonl).open(encoding="utf-8") as fh:
            for raw in fh:
                if not raw.strip():
                    continue
                try:
                    ingest(json.loads(raw), str(speed_jsonl))
                except json.JSONDecodeError:
                    continue
    if Path(summaries_root).is_dir():
        for summary in sorted(Path(summaries_root).rglob("summary.json")):
            try:
                payload = json.loads(summary.read_text())
            except json.JSONDecodeError, OSError:
                continue
            for raw_row in payload.get("rows") or []:
                if not isinstance(raw_row, dict):
                    continue
                data = dict(raw_row)
                if not data.get("kind"):
                    data["kind"] = "speed_redlines"
                if not data.get("run_ts") and payload.get("runTs"):
                    data["run_ts"] = payload["runTs"]
                ingest(
                    data, str(summary), payload.get("fixtures"), payload.get("pairs")
                )
    return rows, unmapped


# ---- converter rows -----------------------------------------------------------


def row_from_converter_line(data: dict, registry: Registry) -> ResultRow | None:
    tool = str(data.get("tool") or "")
    entry = registry.resolve_converter(tool)
    track = str(data.get("track") or "")
    if entry is None or not track:
        return None
    scores = {str(k): _num(v) for k, v in (data.get("scores") or {}).items()}
    failed = tuple(
        sorted(str(d) for d in (data.get("failed_docs") or []) if str(d) not in scores)
    )
    itt_n = int(_num(data.get("itt_n")))
    n_scored = int(_num(data.get("n_scored")))
    docset = str(data.get("docset_id") or "") or None
    extra_raw = data.get("extra") or {}
    extra = {
        str(k): {str(m): _num(x) for m, x in v.items()}
        for k, v in extra_raw.items()
        if isinstance(v, dict)
    }
    hardware = data.get("hardware")
    return ResultRow(
        source="converter",
        id_run=str(data.get("id_run") or ""),
        tool_id=entry.id,
        display=entry.display,
        affiliated=entry.affiliated,
        benchmark=track,
        lens=str(data.get("lens") or "pixel"),
        pin=ToolPin.parse(data.get("version")),
        timestamp=_timestamp(data),
        corpus_revision=docset,
        docset_id=docset,
        renderer_id=f"oracle:{data.get('oracle') or 'unknown'}",
        bench_version=(
            str(data["bench_version"]) if data.get("bench_version") else None
        ),
        scorer=str(data.get("scorer") or "v1"),
        n_scored=n_scored,
        n_failed_docs=max(itt_n - n_scored, 0),
        n_failure_events=int(_num(data.get("failures"))),
        itt_n=itt_n,
        itt_mean=_num(data.get("mean")),
        itt_median=_num(data.get("median")),
        itt_approx=False,
        # The report's mean/median are ITT (failures score 0); the table's Mean and
        # Median columns are over the documents that produced a score.
        mean=round(statistics.mean(scores.values()), 4) if scores else 0.0,
        median=round(statistics.median(scores.values()), 4) if scores else 0.0,
        exact_100=int(_num(data.get("perfects"))),
        scores=scores,
        failed_docs=failed,
        hardware=hardware if isinstance(hardware, dict) else None,
        extra=extra,
    )


def load_converter_rows(
    path: Path, registry: Registry
) -> tuple[list[ResultRow], list[dict]]:
    rows: list[ResultRow] = []
    unmapped: list[dict] = []
    if not Path(path).is_file():
        return rows, unmapped
    with Path(path).open(encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            row = row_from_converter_line(data, registry)
            if row is None:
                unmapped.append(
                    {
                        "tool": data.get("tool"),
                        "track": data.get("track"),
                        "id_run": data.get("id_run"),
                    }
                )
                continue
            rows.append(row)
    return rows, unmapped
