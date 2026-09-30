"""Invariants over the committed stores. Skipped when the stores are absent (CI clones
without results/), never skipped locally."""

from __future__ import annotations

from pathlib import Path

import pytest

from neurotic_docx_bench.ledger import rows as rws
from neurotic_docx_bench.ledger.registry import DEFAULT_REGISTRY_PATH, load_registry

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "results" / "bench.jsonl"
REGISTRY = ROOT / DEFAULT_REGISTRY_PATH

needs_store = pytest.mark.skipif(
    not (BENCH.is_file() and REGISTRY.is_file()),
    reason="results/bench.jsonl or registry absent",
)


@needs_store
def test_every_bench_line_maps_to_a_registry_tool() -> None:
    rows, unmapped = rws.load_bench_rows(BENCH, load_registry(REGISTRY))
    assert rows, "no rows loaded"
    assert unmapped == [], (
        f"unmapped lines: {[(u['vendor'], u['run_name']) for u in unmapped]}"
    )


@needs_store
def test_scored_plus_failed_equals_itt_for_every_row() -> None:
    rows, _ = rws.load_bench_rows(BENCH, load_registry(REGISTRY))
    bad = [
        (r.tool_id, r.benchmark, r.n_scored, r.n_failed_docs, r.itt_n)
        for r in rows
        if not r.itt_approx and r.n_scored + r.n_failed_docs != r.itt_n
    ]
    assert bad == []


@needs_store
def test_headline_rows_are_complete_and_one_per_tool() -> None:
    from neurotic_docx_bench.ledger import policy as pol
    from neurotic_docx_bench.ledger import stats as st

    registry = load_registry(REGISTRY)
    rows, _ = rws.load_bench_rows(BENCH, registry)
    docsets = pol.load_docsets_json(ROOT / "results" / "docsets.json")
    tables = pol.select_headline(
        rows,
        registry=registry,
        retractions=pol.load_retractions(ROOT / pol.DEFAULT_RETRACTIONS_PATH),
        docsets=docsets,
        tie_fn=lambda a, b: st.tie_by_paired_bootstrap(a.itt_scores(), b.itt_scores()),
    )
    assert tables, "no headline tables"
    for benchmark, t in tables.items():
        ids = [r.row.tool_id for r in t.rows]
        assert len(ids) == len(set(ids)), benchmark
        for r in t.rows:
            assert r.row.n_scored + r.row.n_failed_docs == t.expected_n, (
                benchmark,
                r.row.tool_id,
            )
            assert r.row.provenance == "stamped"
            assert not r.row.archived


@needs_store
def test_published_views_are_current() -> None:
    from typer.testing import CliRunner

    from neurotic_docx_bench.cli import app

    result = CliRunner().invoke(app, ["report", "--check", "--root", str(ROOT)])
    assert result.exit_code == 0, result.output
