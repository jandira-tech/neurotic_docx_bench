"""The History pointer names each group well enough to tell two of them apart (#105 review)."""

from __future__ import annotations

from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import tables


def _g(docset: str, bench: str, scorer: str = "v1") -> pol.GroupKey:
    return pol.GroupKey(
        benchmark="docx_to_pdf", lens="all", docset=docset,
        renderer="oracle:microsoft_word", scorer=scorer, bench=bench,
    )


def test_same_docset_and_renderer_are_told_apart_by_bench() -> None:
    text = tables.history_pointer([_g("a89f", "0.8"), _g("a89f", "0.7")], {})
    assert "`a89f`/`oracle:microsoft_word` (bench `0.8`)" in text
    assert "`a89f`/`oracle:microsoft_word` (bench `0.7`)" in text


def test_subset_note_is_kept() -> None:
    text = tables.history_pointer([_g("7a17", "1.0")], {"7a17": "a89f"})
    assert "`7a17`/`oracle:microsoft_word` (bench `1.0`, a subset of `a89f`)" in text
