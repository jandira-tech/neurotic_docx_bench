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
