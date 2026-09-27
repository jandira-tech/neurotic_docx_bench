"""The ranking policy, written once, applied to every tool.

- A row is *eligible* when it is stamped (corpus_revision + per-doc scores), complete
  (its ITT n equals the document set size), not a holdout-only run, not retracted,
  from an active tool, and not a calibration row.
- Rows compare only inside one *group*: (benchmark, lens, document set, renderer,
  scorer). The *current* group of a benchmark is the one holding the newest eligible
  row.
- The headline shows one row per tool: the latest eligible run in the current group.
  There is no best-of-N over runs and no best pin; that is what history is for.
- Rank ties come from ``tie_fn`` (stats: the paired bootstrap interval of the median
  difference includes 0).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from neurotic_docx_bench.ledger.registry import Registry, ToolEntry
from neurotic_docx_bench.ledger.rows import ResultRow, SpeedRow

DEFAULT_RETRACTIONS_PATH = Path("results/retractions.jsonl")
CANONICAL_SPEED_FIXTURES = 1000
MIN_MICRO_N = 30


class Retraction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id_run: str
    benchmark: str | None = None
    reason: str
    retracted_at: datetime
    by: str


def load_retractions(path: Path) -> list[Retraction]:
    if not Path(path).is_file():
        return []
    out: list[Retraction] = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(Retraction.model_validate_json(raw))
    return out


def append_retraction(path: Path, retraction: Retraction) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(retraction.model_dump_json() + "\n")


def find_retraction(
    row: ResultRow, retractions: Sequence[Retraction]
) -> Retraction | None:
    for r in retractions:
        if r.id_run == row.id_run and (
            r.benchmark is None or r.benchmark == row.benchmark
        ):
            return r
    return None


class GroupKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: str
    lens: str
    docset: str
    renderer: str
    scorer: str


def group_key(row: ResultRow) -> GroupKey:
    return GroupKey(
        benchmark=row.benchmark,
        lens=row.lens,
        docset=row.docset_id or row.corpus_revision or "unstamped",
        renderer=row.renderer_id
        or (f"legacy-{row.render}" if row.render else "unknown"),
        scorer=row.scorer,
    )


def expected_n(
    rows: Sequence[ResultRow], docsets: Mapping[str, Mapping[str, object]]
) -> int:
    for r in rows:
        if r.docset_id and r.docset_id in docsets:
            n = docsets[r.docset_id].get("n")
            if isinstance(n, int) and n > 0:
                return n
    stamped = [r.itt_n for r in rows if r.provenance == "stamped"]
    return max(stamped) if stamped else max((r.itt_n for r in rows), default=0)


class Verdict(BaseModel):
    model_config = ConfigDict(frozen=True)

    eligible: bool
    reasons: tuple[str, ...] = ()


def eligibility(
    row: ResultRow,
    *,
    expected: int,
    retractions: Sequence[Retraction],
    registry: Registry,
) -> Verdict:
    reasons: list[str] = []
    entry = registry.by_id(row.tool_id)
    if row.provenance != "stamped":
        reasons.append("legacy provenance")
    if row.holdout_mode == "only":
        reasons.append("holdout-only run")
    if expected and row.itt_n != expected:
        reasons.append(f"incomplete: {row.itt_n} of {expected} documents")
    if entry.status == "retired":
        reasons.append("retired tool")
    if not entry.applies_to(row.benchmark):
        reasons.append("not applicable")
    if entry.role == "calibration":
        reasons.append("calibration row")
    retraction = find_retraction(row, retractions)
    if retraction is not None:
        reasons.append(f"retracted: {retraction.reason}")
    return Verdict(eligible=not reasons, reasons=tuple(reasons))


class RankedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: ResultRow
    rank: int
    tied_with_previous: bool = False


class ExcludedRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: ResultRow
    verdict: Verdict


class HeadlineTable(BaseModel):
    model_config = ConfigDict(frozen=True)

    benchmark: str
    group: GroupKey | None
    expected_n: int
    rows: list[RankedRow]
    calibration: list[ResultRow]
    excluded: list[ExcludedRow]
    not_applicable: list[ToolEntry]
    history_groups: list[GroupKey]


TieFn = Callable[[ResultRow, ResultRow], bool]


def _latest_per_tool(rows: Sequence[ResultRow]) -> list[ResultRow]:
    latest: dict[str, ResultRow] = {}
    for r in sorted(rows, key=lambda x: x.timestamp):
        latest[r.tool_id] = r
    return list(latest.values())


def rank_rows(rows: Sequence[ResultRow], tie_fn: TieFn) -> list[RankedRow]:
    ordered = sorted(rows, key=lambda r: (-r.itt_median, -r.itt_mean, r.display))
    out: list[RankedRow] = []
    for i, r in enumerate(ordered):
        if i == 0:
            out.append(RankedRow(row=r, rank=1))
            continue
        prev = out[-1]
        tied = tie_fn(prev.row, r)
        out.append(
            RankedRow(row=r, rank=prev.rank if tied else i + 1, tied_with_previous=tied)
        )
    return out


def select_headline(
    rows: Sequence[ResultRow],
    *,
    registry: Registry,
    retractions: Sequence[Retraction],
    docsets: Mapping[str, Mapping[str, object]],
    tie_fn: TieFn,
) -> dict[str, HeadlineTable]:
    by_bench: dict[str, list[ResultRow]] = {}
    for r in rows:
        by_bench.setdefault(r.benchmark, []).append(r)

    tables: dict[str, HeadlineTable] = {}
    for benchmark, bench_rows in sorted(by_bench.items()):
        groups: dict[GroupKey, list[ResultRow]] = {}
        for r in bench_rows:
            groups.setdefault(group_key(r), []).append(r)
        verdicts: dict[tuple[str, str], Verdict] = {}
        expected_by_group: dict[GroupKey, int] = {}
        for g, members in groups.items():
            exp = expected_n(members, docsets)
            expected_by_group[g] = exp
            for r in members:
                verdicts[(r.id_run, r.benchmark)] = eligibility(
                    r, expected=exp, retractions=retractions, registry=registry
                )

        def verdict(
            r: ResultRow, _v: dict[tuple[str, str], Verdict] = verdicts
        ) -> Verdict:
            return _v[(r.id_run, r.benchmark)]

        not_applicable = [t for t in registry.tools if not t.applies_to(benchmark)]
        eligible = [r for r in bench_rows if verdict(r).eligible]
        if not eligible:
            tables[benchmark] = HeadlineTable(
                benchmark=benchmark,
                group=None,
                expected_n=0,
                rows=[],
                calibration=[],
                excluded=[
                    ExcludedRow(row=r, verdict=verdict(r))
                    for r in _latest_per_tool(bench_rows)
                ],
                not_applicable=not_applicable,
                history_groups=sorted(groups, key=lambda g: g.docset),
            )
            continue
        newest = max(eligible, key=lambda r: r.timestamp)
        current = group_key(newest)
        members = groups[current]
        ranked = rank_rows(
            _latest_per_tool([r for r in members if verdict(r).eligible]), tie_fn
        )
        calibration = _latest_per_tool(
            [
                r
                for r in members
                if registry.by_id(r.tool_id).role == "calibration"
                and r.provenance == "stamped"
            ]
        )
        shown = {r.row.id_run for r in ranked} | {c.id_run for c in calibration}
        excluded = [
            ExcludedRow(row=r, verdict=verdict(r))
            for r in _latest_per_tool([m for m in members if not verdict(m).eligible])
            if r.id_run not in shown and registry.by_id(r.tool_id).role != "calibration"
        ]
        tables[benchmark] = HeadlineTable(
            benchmark=benchmark,
            group=current,
            expected_n=expected_by_group[current],
            rows=ranked,
            calibration=calibration,
            excluded=excluded,
            not_applicable=not_applicable,
            history_groups=sorted(
                (g for g in groups if g != current), key=lambda g: g.docset
            ),
        )
    return tables


# ---- speed ------------------------------------------------------------------


class RankedSpeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: SpeedRow
    rank: int


class ExcludedSpeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    row: SpeedRow
    verdict: Verdict


class SpeedHeadline(BaseModel):
    model_config = ConfigDict(frozen=True)

    large: list[RankedSpeed]
    micro: list[RankedSpeed]
    excluded: list[ExcludedSpeed]


def speed_eligibility(row: SpeedRow, registry: Registry) -> Verdict:
    reasons: list[str] = []
    entry = registry.by_id(row.tool_id)
    if not row.pin.pinned:
        reasons.append("unpinned speed row")
    if entry.status == "retired":
        reasons.append("retired tool")
    if row.kind == "large" and (row.fixture_count or 0) != CANONICAL_SPEED_FIXTURES:
        reasons.append(
            f"incomplete: {row.fixture_count or 0} of {CANONICAL_SPEED_FIXTURES} fixtures"
        )
    if row.kind == "micro" and row.n < MIN_MICRO_N:
        reasons.append(f"too few samples: {row.n} of {MIN_MICRO_N}")
    return Verdict(eligible=not reasons, reasons=tuple(reasons))


def select_speed_headline(
    rows: Sequence[SpeedRow], *, registry: Registry
) -> SpeedHeadline:
    excluded: dict[tuple[str, str, bool], ExcludedSpeed] = {}
    latest: dict[tuple[str, str, bool], SpeedRow] = {}
    for r in sorted(rows, key=lambda x: x.timestamp):
        v = speed_eligibility(r, registry)
        key = (r.kind, r.tool_id, r.inproc)
        if not v.eligible:
            excluded[key] = ExcludedSpeed(row=r, verdict=v)
            continue
        latest[key] = r
    tables: dict[str, list[SpeedRow]] = {"large": [], "micro": []}
    for (kind, _tool, _inproc), r in latest.items():
        tables[kind].append(r)
    ranked: dict[str, list[RankedSpeed]] = {}
    for kind, members in tables.items():
        ordered = sorted(members, key=lambda r: (r.median_ms, r.display))
        ranked[kind] = [RankedSpeed(row=r, rank=i + 1) for i, r in enumerate(ordered)]
    # A tool with an eligible row in a (kind, mode) is not listed as excluded there.
    shown = set(latest)
    return SpeedHeadline(
        large=ranked["large"],
        micro=ranked["micro"],
        excluded=[e for k, e in excluded.items() if k not in shown],
    )


def load_docsets_json(path: Path) -> dict[str, dict]:
    if not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text())
    return {str(k): dict(v) for k, v in data.items()} if isinstance(data, dict) else {}
