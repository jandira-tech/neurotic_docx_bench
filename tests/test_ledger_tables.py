"""Markdown rendering states the policy, the group, and the uncertainty on the table itself."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import tables as tb
from neurotic_docx_bench.ledger.pins import ToolPin
from neurotic_docx_bench.ledger.registry import load_registry
from neurotic_docx_bench.ledger.rows import ResultRow, SpeedRow

T0 = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def registry(tmp_path: Path):
    doc = {
        "schema_version": 1,
        "tools": [
            {
                "id": "a",
                "vendor": "a",
                "display": "acme",
                "role": "generator",
                "engine": "a",
                "bench_vendors": ["a"],
                "speed_tools": ["a"],
            },
            {
                "id": "b",
                "vendor": "b",
                "display": "jubarte-x",
                "role": "generator",
                "engine": "b",
                "bench_vendors": ["b"],
                "affiliated": True,
            },
            {
                "id": "cal",
                "vendor": "bench",
                "display": "oracle DOCX (identity)",
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
                "display": "doxx",
                "role": "converter",
                "engine": "na",
                "not_applicable": ["script_redlines"],
                "note": "no PDF export",
            },
        ],
    }
    p = tmp_path / "reg.yaml"
    p.write_text(yaml.safe_dump(doc))
    return load_registry(p)


def _row(
    tool, display, median, *, affiliated=False, n=30, pin="1.2.3", docset="d1"
) -> ResultRow:
    scores = {f"doc{i}": median + (i % 3) - 1 for i in range(n)}
    return ResultRow(
        source="bench",
        id_run=f"run-{tool}-{pin}",
        tool_id=tool,
        display=display,
        affiliated=affiliated,
        benchmark="script_redlines",
        pin=ToolPin.parse(pin),
        timestamp=T0,
        corpus_revision="rev",
        docset_id=docset,
        renderer_id="word-16.101.1",
        scorer="pagefair-v2",
        n_scored=n,
        n_failed_docs=2,
        n_failure_events=3,
        itt_n=n + 2,
        itt_mean=median - 1,
        itt_median=median,
        mean=median,
        median=median,
        exact_100=1,
        scores=scores,
        holdout_mode="excluded",
    )


GATED = {"d1": {"n": 32}, "g1": {"n": 2, "gate_of": "d1"}}


def _gated(rows):
    """The rows plus a passing gate run per tool and a null-baseline gate row, in each
    row's own group, so tables tests exercise the layout rather than the gate."""
    extra = []
    seen = set()
    for r in rows:
        for tool, median in ((r.tool_id, 90.0), ("null-baseline", 10.0)):
            sig = (tool, r.benchmark, r.lens, r.renderer_id, r.scorer)
            if sig in seen or r.tool_id == "cal":
                continue
            seen.add(sig)
            extra.append(
                r.model_copy(
                    update={
                        "id_run": f"gate-{tool}-{r.benchmark}-{r.lens}",
                        "tool_id": tool,
                        "display": tool,
                        "docset_id": "g1",
                        "timestamp": T0 - timedelta(days=1),
                        "scores": {"doc0": median, "doc1": median},
                        "n_scored": 2,
                        "n_failed_docs": 0,
                        "n_failure_events": 0,
                        "itt_n": 2,
                        "itt_mean": median,
                        "itt_median": median,
                        "mean": median,
                        "median": median,
                        "extra": {},
                    }
                )
            )
    return list(rows) + extra


def _select(rows, registry, tie=False, docsets=GATED):
    return pol.select_headline(
        _gated(rows),
        registry=registry,
        retractions=[],
        docsets=docsets,
        tie_fn=lambda x, y: tie,
    )["script_redlines"]


def test_fidelity_table_layout(registry) -> None:
    rows = [
        _row("a", "acme", 80.0),
        _row("b", "jubarte-x", 90.0, affiliated=True),
        _row("cal", "oracle DOCX (identity)", 100.0),
    ]
    md = tb.fidelity_table(
        _select(rows, registry),
        row_ci={
            "run-a-1.2.3|script_redlines": (78.0, 82.0),
            "run-b-1.2.3|script_redlines": (88.5, 91.0),
        },
    )
    assert md.startswith("### script_redlines")
    assert "Document set `d1` (32 documents)" in md
    assert "renderer `word-16.101.1`" in md and "scorer `pagefair-v2`" in md
    assert "bench `0.6`" in md
    assert "| 1 | jubarte-x †" in md
    assert "| 2 | acme |" in md
    assert "[88.50, 91.00]" in md
    assert "| 30 | 2 |" in md  # Docs, Failed
    assert "oracle DOCX (identity)" in md and "Calibration" in md
    assert "Not applicable" in md and "doxx" in md and "no PDF export" in md
    assert "author-affiliated" in md
    assert "inferred" not in md


def test_caption_says_when_the_document_set_was_inferred(registry) -> None:
    # the gate set is recorded, the full set it points at is not
    t = _select(
        [_row("a", "acme", 80.0)], registry, docsets={"g1": {"n": 2, "gate_of": "d1"}}
    )
    assert t.docset_recorded is False
    assert "inferred from the largest ITT n" in tb.fidelity_table(t, row_ci={})


def test_tied_rank_is_marked(registry) -> None:
    rows = [_row("a", "acme", 90.0), _row("b", "jubarte-x", 90.3, affiliated=True)]
    md = tb.fidelity_table(_select(rows, registry, tie=True), row_ci={})
    assert "| 1 | jubarte-x †" in md and "| 1= | acme |" in md


def test_excluded_rows_listed_with_reasons(registry) -> None:
    rows = [_row("a", "acme", 80.0), _row("b", "jubarte-x", 90.0, n=10)]
    md = tb.fidelity_table(_select(rows, registry), row_ci={})
    assert (
        "Not ranked" in md
        and "jubarte-x" in md
        and "incomplete: 12 of 32 documents" in md
    )


def test_empty_table_says_so(registry) -> None:
    md = tb.fidelity_table(_select([_row("a", "acme", 80.0, n=5)], registry), row_ci={})
    assert "No eligible rows" in md and "incomplete: 7 of 32 documents" in md


def test_extra_metric_columns_appear_when_present(registry) -> None:
    r = _row("a", "acme", 40.0).model_copy(
        update={"extra": {"ssim": {"mean": 70.0, "median": 88.0}}, "lens": "jaccard"}
    )
    md = tb.fidelity_table(_select([r], registry), row_ci={})
    assert "ssim median" in md and "| 88.00 |" in md


def test_speed_table_layout(registry) -> None:
    srow = SpeedRow(
        tool_id="a",
        display="acme",
        affiliated=False,
        kind="large",
        inproc=True,
        runtime="rust",
        pin=ToolPin.parse("x@abcdefabcdef"),
        timestamp=T0,
        fixture_count=1000,
        pair_count=5000,
        n=5000,
        failures=3,
        median_ms=6.2,
        mean_ms=25.3,
        p95_ms=110.8,
        hardware={"cpu": "Apple M3 Max", "cores": 14},
    )
    h = pol.select_speed_headline([srow], registry=registry)
    md = tb.speed_tables(h)
    assert "### speed_redlines" in md
    assert (
        "| 1 | acme | in-process | rust | x@abcdefabcdef | 2026-09-01 | 1000 | 5000 | 6.20 | 25.30 | 110.80 | 5000 | 3 | Apple M3 Max (14 cores) |"
        in md
    )
    assert "No pinned microbench rows yet." in md


def test_history_table_lists_every_row_with_verdicts(registry) -> None:
    rows = [_row("a", "acme", 80.0), _row("a", "acme", 70.0, n=5, pin="1.0.0")]
    md = tb.history_section(
        _gated(rows), registry=registry, retractions=[], docsets=GATED
    )
    assert "## History" in md and "1.0.0" in md
    assert "incomplete: 7 of 32 documents" in md and "eligible" in md
    assert "gate-set run" in md


def test_paired_section_lists_pairs_with_intervals(registry) -> None:
    rows = [_row("a", "acme", 80.0), _row("b", "jubarte-x", 90.0, affiliated=True)]
    md = tb.paired_section({"script_redlines": _select(rows, registry)})
    assert "## Paired comparisons" in md and "| jubarte-x † | acme | 30 |" in md
    assert tb.paired_section({}).count("No benchmark has two ranked rows") == 1


def test_lens_health_section_lists_disagreeing_tools(registry) -> None:
    r = _row("a", "acme", 80.0).model_copy(
        update={"lens_disagree_rate": 0.12, "n_lens_disagree": 9}
    )
    md = tb.lens_health_section([r, _row("b", "jubarte-x", 90.0)])
    assert "## Lens health" in md and "acme" in md and "| 9 |" in md and "0.12" in md
    assert "jubarte-x" not in md
    assert tb.lens_health_section([_row("a", "acme", 80.0)]) == ""


def test_methodology_mentions_weights_and_oracles() -> None:
    md = tb.methodology_section(noise_sigma=1e-14, lo_version="26.2.4.2")
    for needle in (
        "SSIM",
        "0.7",
        "0.3",
        "intent-to-treat",
        "LibreOffice",
        "Word",
        "paired bootstrap",
        "author",
    ):
        assert needle in md, needle
    assert "not recorded" in tb.methodology_section(noise_sigma=None, lo_version=None)


def test_vendor_table_skips_retired_and_calibration(registry) -> None:
    md = tb.vendor_table(registry)
    assert "acme" in md and "doxx" in md and "no PDF export" in md
    assert "oracle DOCX (identity)" not in md
