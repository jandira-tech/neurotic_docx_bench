"""The gate: Word-rendered rows only, and a tool enters the main page once its gate-set
run beats the null baseline by the margin with a CI that excludes the null median."""

from __future__ import annotations

import pytest

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import tables
from tests.test_ledger_policy import T0, row
from tests.test_ledger_policy import registry as policy_registry  # noqa: F401


@pytest.fixture
def registry(policy_registry):  # noqa: F811
    return policy_registry


DOCSETS = {"d1": {"n": 3}, "g1": {"n": 2, "gate_of": "d1"}}


def gate_row(tool: str, median: float, *, days: int = -1, scores=None, **kw):
    r = row(tool, median=median, n=2, days=days, docset="g1", scores=scores, **kw)
    return r.model_copy(update={"id_run": f"gate-{tool}-{days}"})


def _select(rows, registry, *, docsets=DOCSETS, retractions=(), ci_fn=None):
    kwargs = {} if ci_fn is None else {"ci_fn": ci_fn}
    return pol.select_headline(
        rows,
        registry=registry,
        retractions=list(retractions),
        docsets=docsets,
        tie_fn=lambda _x, _y: False,
        **kwargs,
    )["script_redlines"]


def test_word_rendered_means_a_word_renderer_id_or_the_word_oracle() -> None:
    assert pol.is_word_rendered("word-16.101.1")
    assert pol.is_word_rendered("oracle:microsoft_word")
    assert not pol.is_word_rendered("soffice-26.2.4.2")
    assert not pol.is_word_rendered("legacy-word")
    assert not pol.is_word_rendered(None)


def test_eligibility_rejects_non_word_renderers_and_gate_set_runs(registry) -> None:
    def verdict(r, docsets=DOCSETS):
        return pol.eligibility(
            r,
            expected=len(r.scores),
            retractions=[],
            registry=registry,
            docsets=docsets,
        )

    assert verdict(row("a", median=1, renderer="soffice-26")).reasons == (
        "renderer soffice-26 is not Word",
    )
    assert verdict(row("a", median=1, renderer=None)).reasons == (
        "renderer unknown is not Word",
    )
    assert verdict(gate_row("a", 90)).reasons == ("gate-set run",)
    assert verdict(row("a", median=1)).eligible
    # without a docsets mapping the gate-set rule cannot fire
    assert verdict(gate_row("a", 90), docsets=None).eligible


def test_a_tool_that_beats_the_null_baseline_on_the_gate_is_ranked(registry) -> None:
    rows = [row("a", median=80), gate_row("a", 90), gate_row("null-baseline", 10)]
    t = _select(rows, registry)
    assert [(r.row.tool_id, r.rank) for r in t.rows] == [("a", 1)]
    assert t.below_gate == [] and t.excluded == []
    # the gate set is not another measurement of the benchmark
    assert t.history_groups == []


def test_a_tool_below_the_margin_is_listed_below_the_gate_not_ranked(registry) -> None:
    rows = [
        row("a", median=80),
        row("b", median=70, days=1),
        gate_row("a", 19.5),
        gate_row("b", 90),
        gate_row("null-baseline", 10),
    ]
    t = _select(rows, registry)
    assert [r.row.tool_id for r in t.rows] == ["b"]
    assert [(e.row.tool_id, e.verdict.reasons) for e in t.excluded] == [
        ("a", ("below the gate: median 19.50 vs null 10.00, needs +10.00",))
    ]
    assert [(g.row.tool_id, g.passed, g.reason) for g in t.below_gate] == [
        ("a", False, "below the gate: median 19.50 vs null 10.00, needs +10.00")
    ]
    g = t.below_gate[0]
    assert g.gate_docset == "g1"
    assert g.gate_row is not None and g.gate_row.itt_median == 19.5
    assert g.null_row is not None and g.null_row.itt_median == 10
    assert g.ci == (19.5, 19.5)


def test_exactly_the_margin_passes(registry) -> None:
    rows = [row("a", median=80), gate_row("a", 20), gate_row("null-baseline", 10)]
    assert [r.row.tool_id for r in _select(rows, registry).rows] == ["a"]


def test_a_ci_that_reaches_the_null_median_fails_the_gate(registry) -> None:
    rows = [row("a", median=80), gate_row("a", 60), gate_row("null-baseline", 10)]
    t = _select(rows, registry, ci_fn=lambda _v: (10.0, 95.0))
    assert t.rows == []
    assert t.below_gate[0].reason == (
        "below the gate: 95% CI [10.00, 95.00] of the gate median reaches null 10.00"
    )
    assert t.below_gate[0].ci == (10.0, 95.0)
    ok = _select(rows, registry, ci_fn=lambda _v: (10.01, 95.0))
    assert [r.row.tool_id for r in ok.rows] == ["a"]


def test_the_default_ci_is_the_bootstrap_of_the_gate_scores(registry) -> None:
    scores = {f"doc{i}": v for i, v in enumerate([5, 95, 60, 70, 80, 90])}
    docsets = {"d1": {"n": 3}, "g1": {"n": 6, "gate_of": "d1"}}
    rows = [
        row("a", median=80),
        gate_row("a", 75, scores=scores),
        gate_row("null-baseline", 10, scores={f"doc{i}": 10 for i in range(6)}),
    ]
    t = _select(rows, registry, docsets=docsets)
    assert t.rows and t.rows[0].row.tool_id == "a"
    assert t.gates[0].ci == pol.st.bootstrap_median_ci(list(scores.values()))


def test_missing_gate_pieces_each_have_their_own_reason(registry) -> None:
    full = row("a", median=80)
    no_set = _select([full], registry, docsets={"d1": {"n": 3}})
    assert no_set.rows == []
    assert no_set.below_gate[0].reason == "no gate set recorded for `d1`"
    assert no_set.below_gate[0].gate_docset is None

    no_run = _select([full, gate_row("null-baseline", 10)], registry)
    assert no_run.below_gate[0].reason == "no gate run on `g1`"

    no_null = _select([full, gate_row("a", 90)], registry)
    assert no_null.below_gate[0].reason == "gate `g1` has no null-baseline row"

    # a stamped row always carries scores; the branch guards an injected ci_fn
    no_ci = _select(
        [full, gate_row("a", 90), gate_row("null-baseline", 10)],
        registry,
        ci_fn=lambda _v: None,
    )
    assert no_ci.below_gate[0].reason == "gate run on `g1` has no per-document scores"


def test_the_latest_usable_gate_run_decides(registry) -> None:
    rows = [
        row("a", median=80),
        gate_row("a", 15, days=-3),  # old, failing
        gate_row("a", 90, days=-2),  # newer, passing
        gate_row("null-baseline", 10),
    ]
    assert [r.row.tool_id for r in _select(rows, registry).rows] == ["a"]

    retracted = pol.Retraction(
        id_run="gate-a--2", reason="bad", retracted_at=T0, by="me"
    )
    t = _select(rows, registry, retractions=[retracted])
    assert t.rows == [] and t.below_gate[0].gate_row.id_run == "gate-a--3"

    incomplete = [
        row("a", median=80),
        gate_row("a", 90, days=-2).model_copy(update={"itt_n": 1}),
        gate_row("null-baseline", 10),
    ]
    assert _select(incomplete, registry).below_gate[0].reason == "no gate run on `g1`"


def test_the_gate_is_checked_in_the_candidate_row_own_group(registry) -> None:
    # a gate run rendered elsewhere or scored differently does not count
    rows = [
        row("a", median=80),
        gate_row("a", 90, renderer="word-15"),
        gate_row("null-baseline", 10),
    ]
    assert _select(rows, registry).below_gate[0].reason == "no gate run on `g1`"


def test_converter_benchmarks_are_not_gated(registry) -> None:
    """The gate is a `bench run` affair: the converter benchmarks (scored against
    Word's own export) have no gate set and rank as before."""
    assert pol.is_gated_benchmark("script_redlines")
    assert pol.is_gated_benchmark("visual_redlines")
    assert not pol.is_gated_benchmark("docx_to_pdf")
    rows = [
        row("a", median=60, benchmark="docx_to_pdf", renderer="oracle:microsoft_word")
    ]
    t = pol.select_headline(
        rows, registry=registry, retractions=[], docsets={}, tie_fn=lambda _x, _y: False
    )["docx_to_pdf"]
    assert [r.row.tool_id for r in t.rows] == ["a"]
    assert t.gates == [] and t.below_gate == []


def test_below_gate_section_lists_the_tools_and_their_numbers(registry) -> None:
    rows = [
        row("a", median=80),
        gate_row("a", 19.5),
        gate_row("null-baseline", 10),
        row("b", median=70),
    ]
    t = _select(rows, registry)
    text = tables.below_gate_section({"script_redlines": t})
    assert text.startswith("## Below the gate")
    assert "| A | 1.0 | 2026-07-31 | 19.50 | 10.00 | [19.50, 19.50] | `g1` |" in text
    assert "| B | 1.0 | n/a | n/a | 10.00 | n/a | `g1` |" in text
    assert "no gate run on `g1`" in text
    assert tables.below_gate_section({}) == ""
