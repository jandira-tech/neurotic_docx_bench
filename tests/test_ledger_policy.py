"""One policy for every tool: eligibility, comparability groups, latest eligible run, ranks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger.pins import ToolPin
from neurotic_docx_bench.ledger.registry import load_registry
from neurotic_docx_bench.ledger.rows import ResultRow, SpeedRow

T0 = datetime(2026, 8, 1, tzinfo=UTC)


@pytest.fixture
def registry(tmp_path: Path):
    doc = {
        "schema_version": 1,
        "tools": [
            {
                "id": "a",
                "vendor": "a",
                "display": "A",
                "role": "generator",
                "engine": "a",
                "bench_vendors": ["a"],
            },
            {
                "id": "b",
                "vendor": "b",
                "display": "B",
                "role": "generator",
                "engine": "b",
                "bench_vendors": ["b"],
                "affiliated": True,
            },
            {
                "id": "old",
                "vendor": "old",
                "display": "Old",
                "role": "generator",
                "engine": "old",
                "bench_vendors": ["old"],
                "status": "retired",
            },
            {
                "id": "cal",
                "vendor": "bench",
                "display": "oracle",
                "role": "calibration",
                "engine": "pipeline",
                "bench_vendors": ["cal"],
            },
            {
                "id": "null-baseline",
                "vendor": "bench",
                "display": "null baseline",
                "role": "calibration",
                "engine": "pipeline",
                "bench_vendors": ["null-baseline"],
            },
            {
                "id": "na",
                "vendor": "na",
                "display": "NA",
                "role": "converter",
                "engine": "na",
                "not_applicable": ["script_redlines"],
            },
        ],
    }
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def row(
    tool: str,
    *,
    median: float,
    mean: float | None = None,
    n: int = 3,
    days: int = 0,
    docset: str | None = "d1",
    renderer: str | None = "word-16.1",
    scores: dict | None = None,
    holdout: str | None = "excluded",
    pin: str = "1.0",
    benchmark: str = "script_redlines",
    affiliated: bool = False,
    crev: str | None = "rev1",
) -> ResultRow:
    scores = scores if scores is not None else {f"doc{i}": median for i in range(n)}
    return ResultRow(
        source="bench",
        id_run=f"run-{tool}-{days}",
        tool_id=tool,
        display=tool.upper(),
        affiliated=affiliated,
        benchmark=benchmark,
        pin=ToolPin.parse(pin),
        timestamp=T0 + timedelta(days=days),
        corpus_revision=crev,
        docset_id=docset,
        renderer_id=renderer,
        scorer="pagefair-v2",
        n_scored=len(scores),
        n_failed_docs=0,
        n_failure_events=0,
        itt_n=len(scores),
        itt_mean=mean if mean is not None else median,
        itt_median=median,
        mean=mean if mean is not None else median,
        median=median,
        exact_100=0,
        scores=scores,
        holdout_mode=holdout,
    )


def srow(
    tool,
    *,
    median,
    pinned=True,
    fixtures=1000,
    days=0,
    inproc=False,
    kind="large",
    n=5000,
):
    return SpeedRow(
        tool_id=tool,
        display=tool.upper(),
        affiliated=False,
        kind=kind,
        inproc=inproc,
        runtime="x",
        pin=ToolPin.parse("1.0" if pinned else None),
        timestamp=T0 + timedelta(days=days),
        fixture_count=fixtures,
        pair_count=5000 if fixtures == 1000 else 50,
        n=n,
        failures=0,
        median_ms=median,
        mean_ms=median,
        p95_ms=None,
    )


def _with_gates(rows, docsets):
    """A passing gate row per (tool, benchmark, docset, renderer) plus a null-baseline
    row on every full docset's gate set, so tests about other rules can rank rows."""
    docsets = dict(docsets)
    full_ids = [d for d, v in docsets.items() if not v.get("gate_of")]
    extra = []
    for did in full_ids:
        gid = f"g-{did}"
        docsets[gid] = {"n": 2, "gate_of": did}
        seen = set()
        for r in rows:
            if r.docset_id != did or r.tool_id == "null-baseline":
                continue
            sig = (r.tool_id, r.benchmark, r.renderer_id)
            if sig in seen:
                continue
            seen.add(sig)
            extra.append(
                row(
                    r.tool_id,
                    median=90,
                    n=2,
                    days=-1,
                    docset=gid,
                    renderer=r.renderer_id,
                    benchmark=r.benchmark,
                ).model_copy(update={"id_run": f"gate-{r.tool_id}-{r.benchmark}-{gid}"})
            )
        for benchmark in sorted({r.benchmark for r in rows if r.docset_id == did}):
            extra.append(
                row(
                    "null-baseline",
                    median=10,
                    n=2,
                    days=-1,
                    docset=gid,
                    benchmark=benchmark,
                ).model_copy(update={"id_run": f"gate-null-{benchmark}-{gid}"})
            )
    return list(rows) + extra, docsets


def _select(rows, registry, retractions=(), docsets=None, tie=False, gates=True):
    docsets = docsets if docsets is not None else {"d1": {"n": 3}}
    if gates:
        rows, docsets = _with_gates(rows, docsets)
    return pol.select_headline(
        rows,
        registry=registry,
        retractions=list(retractions),
        docsets=docsets,
        tie_fn=lambda x, y: tie,
    )


def test_group_key_uses_docset_then_corpus_revision_then_unstamped() -> None:
    assert pol.group_key(row("a", median=1)).docset == "d1"
    assert pol.group_key(row("a", median=1, docset=None)).docset == "rev1"
    assert (
        pol.group_key(row("a", median=1, docset=None, crev=None)).docset == "unstamped"
    )
    assert pol.group_key(row("a", median=1, renderer=None)).renderer == "unknown"


def test_expected_n_prefers_recorded_docset_size() -> None:
    rows = [row("a", median=1, n=3), row("b", median=1, n=5)]
    assert pol.expected_n(rows, {"d1": {"n": 4}}) == 4
    assert pol.expected_n(rows, {}) == 5


def test_expected_n_accepts_a_single_document_docset() -> None:
    assert pol.expected_n([row("a", median=1, n=3)], {"d1": {"n": 1}}) == 1


def test_expected_n_fallbacks_prefer_stamped_rows_then_any_row_then_zero() -> None:
    stamped = row("a", median=1, n=3)
    legacy = row("b", median=1, n=5, docset=None, crev=None)
    assert legacy.provenance == "legacy"
    assert pol.expected_n([stamped, legacy], {}) == 3
    assert pol.expected_n([legacy], {}) == 5
    assert pol.expected_n([], {}) == 0
    # a docset record without a usable size is ignored, not trusted
    assert pol.expected_n([stamped], {"d1": {"n": 0}}) == 3
    assert pol.expected_n([stamped], {"d1": {"n": "4"}}) == 3
    assert pol.expected_n([stamped], {"d1": {}}) == 3


def test_eligibility_reason_strings_for_archived_calibration_and_not_applicable(
    registry,
) -> None:
    def verdict(r: ResultRow) -> pol.Verdict:
        return pol.eligibility(r, expected=3, retractions=[], registry=registry)

    assert verdict(
        row("a", median=1).model_copy(update={"archived": True})
    ).reasons == ("archived",)
    assert verdict(row("cal", median=1)).reasons == ("calibration row",)
    assert verdict(row("na", median=1)).reasons == ("not applicable",)
    assert verdict(row("na", median=1, benchmark="accepted_changes")).eligible
    assert verdict(row("old", median=1)).reasons == ("retired tool",)


def test_eligibility_reasons(registry) -> None:
    ok = pol.eligibility(
        row("a", median=1, n=3), expected=3, retractions=[], registry=registry
    )
    assert ok.eligible and ok.reasons == ()
    legacy = pol.eligibility(
        row("a", median=1, n=3, crev=None, docset=None),
        expected=3,
        retractions=[],
        registry=registry,
    )
    assert not legacy.eligible and "legacy provenance" in legacy.reasons
    short = pol.eligibility(
        row("a", median=1, n=2), expected=3, retractions=[], registry=registry
    )
    assert not short.eligible and "incomplete: 2 of 3 documents" in short.reasons
    hold = pol.eligibility(
        row("a", median=1, holdout="only"),
        expected=3,
        retractions=[],
        registry=registry,
    )
    assert "holdout-only run" in hold.reasons
    retired = pol.eligibility(
        row("old", median=1), expected=3, retractions=[], registry=registry
    )
    assert "retired tool" in retired.reasons
    r = pol.Retraction(
        id_run="run-a-0", reason="harness bug", retracted_at=T0, by="arthur"
    )
    gone = pol.eligibility(
        row("a", median=1), expected=3, retractions=[r], registry=registry
    )
    assert "retracted: harness bug" in gone.reasons


def test_headline_takes_latest_eligible_run_per_tool_not_the_best(registry) -> None:
    rows = [
        row("a", median=95, days=0),  # older, better
        row("a", median=80, days=5),  # latest: this one is shown
        row("b", median=90, days=1, affiliated=True),
    ]
    t = _select(rows, registry)["script_redlines"]
    assert [(r.row.tool_id, r.row.itt_median, r.rank) for r in t.rows] == [
        ("b", 90, 1),
        ("a", 80, 2),
    ]


def test_headline_current_group_is_the_one_with_the_newest_eligible_row(
    registry,
) -> None:
    rows = [
        row("a", median=99, days=0, docset="d0"),
        row("a", median=70, days=9, docset="d1"),
        row("b", median=60, days=8, docset="d1"),
    ]
    t = _select(rows, registry, docsets={"d0": {"n": 3}, "d1": {"n": 3}})[
        "script_redlines"
    ]
    assert t.group is not None and t.group.docset == "d1"
    assert [r.row.tool_id for r in t.rows] == ["a", "b"]
    assert [h.docset for h in t.history_groups] == ["d0"]


def test_retracted_run_falls_back_to_previous_run(registry) -> None:
    rows = [row("a", median=95, days=0), row("a", median=10, days=5)]
    r = pol.Retraction(
        id_run="run-a-5", reason="broken harness", retracted_at=T0, by="arthur"
    )
    t = _select(rows, registry, retractions=[r])["script_redlines"]
    assert [(x.row.id_run, x.row.itt_median) for x in t.rows] == [("run-a-0", 95)]
    assert [(e.row.id_run, e.verdict.reasons) for e in t.excluded] == [
        ("run-a-5", ("retracted: broken harness",))
    ]


def test_ties_share_a_rank(registry) -> None:
    rows = [row("a", median=91.4, days=1), row("b", median=91.1, days=1)]
    t = _select(rows, registry, tie=True)["script_redlines"]
    assert [(r.rank, r.tied_with_previous) for r in t.rows] == [(1, False), (1, True)]


def test_calibration_and_not_applicable_are_listed_not_ranked(registry) -> None:
    rows = [row("a", median=80), row("cal", median=100)]
    t = _select(rows, registry)["script_redlines"]
    assert [r.row.tool_id for r in t.rows] == ["a"]
    assert [c.tool_id for c in t.calibration] == ["cal"]
    assert [e.id for e in t.not_applicable] == ["na"]
    assert t.excluded == []


def test_no_eligible_rows_gives_an_empty_table_with_reasons(registry) -> None:
    t = _select([row("a", median=80, n=1)], registry)["script_redlines"]
    assert t.group is None and t.rows == []
    assert [e.verdict.reasons for e in t.excluded] == [
        ("incomplete: 1 of 3 documents",)
    ]


def test_load_retractions_round_trip(tmp_path: Path) -> None:
    p = tmp_path / "retractions.jsonl"
    r = pol.Retraction(
        id_run="x", benchmark="roundtrip", reason="r", retracted_at=T0, by="me"
    )
    pol.append_retraction(p, r)
    assert pol.load_retractions(p) == [r]
    assert pol.load_retractions(tmp_path / "missing.jsonl") == []


def test_speed_headline_requires_pin_and_canonical_fixture_count(
    registry, tmp_path: Path
) -> None:
    doc = yaml.safe_load((tmp_path / "reg.yaml").read_text())
    doc["tools"][0]["speed_tools"] = ["a"]
    doc["tools"][1]["speed_tools"] = ["b"]
    (tmp_path / "reg2.yaml").write_text(yaml.safe_dump(doc))
    reg2 = load_registry(tmp_path / "reg2.yaml")

    rows = [
        srow("a", median=6.0),
        srow("a", median=9.0, inproc=True),
        srow("b", median=7.0, fixtures=50, days=1),
        srow("b", median=5.0, pinned=False, days=2),
        srow("a", median=1.0, kind="micro", fixtures=None),
    ]
    t = pol.select_speed_headline(rows, registry=reg2)
    assert [(r.row.tool_id, r.row.inproc, r.rank) for r in t.large] == [
        ("a", False, 1),
        ("a", True, 2),
    ]
    assert [(r.row.tool_id, r.rank) for r in t.micro] == [("a", 1)]
    # Only the latest excluded row per (kind, tool, mode) is reported.
    assert [(e.row.tool_id, e.verdict.reasons) for e in t.excluded] == [
        ("b", ("unpinned speed row",))
    ]
    only_short = pol.select_speed_headline(
        [srow("b", median=7.0, fixtures=50)], registry=reg2
    )
    assert [e.verdict.reasons for e in only_short.excluded] == [
        ("incomplete: 50 of 1000 fixtures",)
    ]
    # A tool with an eligible row in a mode is not also listed as excluded in that mode.
    both = pol.select_speed_headline(
        [srow("a", median=6.0, days=1), srow("a", median=6.0, pinned=False)],
        registry=reg2,
    )
    assert both.excluded == [] and len(both.large) == 1


def test_speed_eligibility_reasons_for_retired_micro_and_unsized_rows(
    registry,
) -> None:
    assert pol.speed_eligibility(srow("old", median=1.0), registry).reasons == (
        "retired tool",
    )
    micro = srow("a", median=1.0, kind="micro", fixtures=None, n=10)
    assert pol.speed_eligibility(micro, registry).reasons == (
        "too few samples: 10 of 30",
    )
    assert pol.speed_eligibility(
        srow("a", median=1.0, kind="micro", fixtures=None, n=30), registry
    ).eligible
    unsized = srow("a", median=1.0, fixtures=None)
    assert pol.speed_eligibility(unsized, registry).reasons == (
        "incomplete: 0 of 1000 fixtures",
    )


def test_rank_rows_orders_equal_medians_by_mean_then_display() -> None:
    a = row("a", median=80, mean=70)
    b = row("b", median=80, mean=75)
    c = row("c", median=80, mean=75)
    ranked = pol.rank_rows([a, c, b], lambda _x, _y: False)
    assert [r.row.tool_id for r in ranked] == ["b", "c", "a"]
    assert [r.rank for r in ranked] == [1, 2, 3]


def test_retraction_scoped_to_one_benchmark_leaves_the_others_alone() -> None:
    scoped = pol.Retraction(
        id_run="run-a-0",
        benchmark="accepted_changes",
        reason="r",
        retracted_at=T0,
        by="me",
    )
    assert pol.find_retraction(row("a", median=1), [scoped]) is None
    assert (
        pol.find_retraction(row("a", median=1, benchmark="accepted_changes"), [scoped])
        is scoped
    )
    unscoped = scoped.model_copy(update={"benchmark": None})
    assert pol.find_retraction(row("a", median=1), [unscoped]) is unscoped


def test_group_key_falls_back_to_the_legacy_render_name() -> None:
    legacy = row("a", median=1, renderer=None).model_copy(update={"render": "word"})
    assert pol.group_key(legacy).renderer == "legacy-word"


def test_history_groups_are_sorted_by_docset_and_exclude_the_current_group(
    registry,
) -> None:
    rows = [
        row("a", median=80, docset="d3", days=0),
        row("b", median=80, docset="d1", days=1),
        row("a", median=80, docset="d2", days=2),
    ]
    docsets = {"d1": {"n": 3}, "d2": {"n": 3}, "d3": {"n": 3}}
    t = _select(rows, registry, docsets=docsets)["script_redlines"]
    assert t.group is not None and t.group.docset == "d2"
    assert [g.docset for g in t.history_groups] == ["d1", "d3"]

    none = _select(
        [row("a", median=80, n=1, docset="d3"), row("b", median=80, n=1, docset="d1")],
        registry,
        docsets=docsets,
    )["script_redlines"]
    assert none.expected_n == 0
    assert [g.docset for g in none.history_groups] == ["d1", "d3"]


def test_a_benchmark_without_eligible_rows_does_not_stop_the_others(
    registry,
) -> None:
    rows = [
        row("a", median=80, n=1, benchmark="accepted_changes"),
        row("a", median=80, benchmark="script_redlines"),
    ]
    tables = _select(rows, registry)
    assert sorted(tables) == ["accepted_changes", "script_redlines"]
    assert tables["accepted_changes"].rows == []
    assert [r.row.tool_id for r in tables["script_redlines"].rows] == ["a"]


def test_load_docsets_json_reads_the_mapping_and_tolerates_absence(
    tmp_path: Path,
) -> None:
    p = tmp_path / "docsets.json"
    p.write_text(
        '{"abc": {"n": 3, "benchmark": "script_redlines", "keys": ["x", "y", "z"]}}',
        encoding="utf-8",
    )
    loaded = pol.load_docsets_json(p)
    assert loaded == {
        "abc": {"n": 3, "benchmark": "script_redlines", "keys": ["x", "y", "z"]}
    }
    assert pol.load_docsets_json(tmp_path / "missing.json") == {}
    (tmp_path / "list.json").write_text("[1, 2]", encoding="utf-8")
    assert pol.load_docsets_json(tmp_path / "list.json") == {}


def test_group_key_carries_the_bench_series_and_labels_unstamped_rows() -> None:
    new = row("a", median=1).model_copy(update={"bench_version": "0.7.2"})
    old = row("a", median=1)
    assert pol.group_key(new).bench == "0.7"
    assert pol.group_key(old).bench == "0.6"
    assert pol.group_key(new) != pol.group_key(old)
