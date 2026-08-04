"""Lens-disagreement bench-health metric (PR8).

Three lenses can judge a script_redlines doc: pixel (pagefair overall), functional
(PR7 accept/reject invariant), and WV-1 (PR9 word-validate --json records). When
they disagree — pixel says near-perfect but the redline is functionally inert, or
pixel says broken but the redline functions — the BENCH is measuring the wrong
thing on that doc. The rate is a bench-health alarm, not a tool ranking input.
"""

from __future__ import annotations

import json
from pathlib import Path

from neurotic_docx_bench import lens_health

# ── per-doc decision ─────────────────────────────────────────────────────────


def _doc(pixel: float | None = None, accept: bool | None = None, reject: bool | None = None,
         blind: bool = False, wv1: str | None = None) -> dict[str, object]:
    d: dict[str, object] = {}
    if pixel is not None:
        d["overall_score_pagefair"] = pixel
    d["functional_accept_ok"] = accept
    d["functional_reject_ok"] = reject
    if blind:
        d["functional_blind"] = True
    if wv1 is not None:
        d["wv1_outcome"] = wv1
    return d


def test_agreeing_lenses_no_disagreement() -> None:
    assert lens_health.doc_disagreement(_doc(pixel=95.0, accept=True, reject=True)) is False
    assert lens_health.doc_disagreement(_doc(pixel=40.0, accept=False, reject=False)) is False


def test_pixel_high_functional_fail_is_disagreement() -> None:
    # The painted-redline signature: renders near-perfect, functionally inert.
    assert lens_health.doc_disagreement(_doc(pixel=95.0, accept=True, reject=False)) is True


def test_pixel_low_functional_pass_is_disagreement() -> None:
    # The inverse alarm: the redline works but the pixel lens says broken.
    assert lens_health.doc_disagreement(_doc(pixel=40.0, accept=True, reject=True)) is True


def test_middle_band_is_not_disagreement() -> None:
    # 50–90 is genuine partial quality — no lens conflict to report.
    assert lens_health.doc_disagreement(_doc(pixel=70.0, accept=False, reject=False)) is False


def test_blind_doc_not_computable() -> None:
    assert lens_health.doc_disagreement(_doc(pixel=95.0, accept=True, reject=False, blind=True)) is None


def test_absent_lenses_not_computable() -> None:
    assert lens_health.doc_disagreement(_doc(pixel=95.0)) is None  # no functional, no wv1
    assert lens_health.doc_disagreement(_doc(accept=True, reject=True)) is None  # no pixel
    assert lens_health.doc_disagreement({}) is None


def test_wv1_invalid_with_high_pixel_is_disagreement() -> None:
    # Word cannot even open it, but pixels say near-perfect (LibreOffice was
    # more forgiving) — that's a bench blind spot, with or without functional.
    assert lens_health.doc_disagreement(_doc(pixel=95.0, wv1="invalid")) is True
    assert lens_health.doc_disagreement(_doc(pixel=95.0, accept=True, reject=True, wv1="invalid")) is True


def test_wv1_valid_only_not_computable() -> None:
    # No rule can ever flag a valid-only doc (Word opening a file says nothing
    # about redline correctness) — counting it would mechanically dilute the
    # rate as WV-1 coverage grows. Excluded from the denominator.
    assert lens_health.doc_disagreement(_doc(pixel=95.0, wv1="valid")) is None
    assert lens_health.doc_disagreement(_doc(pixel=95.0, wv1="unjudgeable")) is None
    # With a functional verdict alongside, the doc IS computable and agrees.
    assert lens_health.doc_disagreement(_doc(pixel=95.0, accept=True, reject=True, wv1="valid")) is False


def test_functional_wv1_contradiction_flags_in_any_band() -> None:
    # Two judging lenses in flat contradiction — the invariant holds but Word
    # cannot even open the file — must flag regardless of the pixel band.
    assert lens_health.doc_disagreement(_doc(pixel=70.0, accept=True, reject=True, wv1="invalid")) is True
    assert lens_health.doc_disagreement(_doc(pixel=40.0, accept=False, reject=False, wv1="invalid")) is False


def test_partial_functional_verdict_not_computable() -> None:
    # FunctionalVerdict contract: None fields mean the check could not run —
    # a partial verdict must never read as a fail (and so never as a conflict).
    d = {"overall_score_pagefair": 95.0, "functional_accept_ok": None, "functional_reject_ok": True}
    assert lens_health.doc_disagreement(d) is None


def test_raw_overall_score_fallback() -> None:
    # Docs scored before pagefair (or raw-score benchmarks) still compute.
    d = {"overall_score": 95.0, "functional_accept_ok": True, "functional_reject_ok": False}
    assert lens_health.doc_disagreement(d) is True


# ── aggregation ──────────────────────────────────────────────────────────────


def test_summarize_rate_math() -> None:
    per_doc = {
        "a": _doc(pixel=95.0, accept=True, reject=True),  # computable, agrees
        "b": _doc(pixel=95.0, accept=True, reject=False),  # computable, disagrees
        "c": _doc(pixel=95.0),  # not computable — excluded from denominator
        "d": _doc(pixel=40.0, accept=True, reject=True),  # computable, disagrees
        "e": _doc(pixel=95.0, accept=True, reject=False, blind=True),  # blind — excluded
    }
    n, rate = lens_health.summarize(per_doc)
    assert n == 2
    assert rate == round(2 / 3, 4)


def test_summarize_none_when_nothing_computable() -> None:
    assert lens_health.summarize({"a": _doc(pixel=95.0)}) == (None, None)
    assert lens_health.summarize({}) == (None, None)
    assert lens_health.summarize(None) == (None, None)


# ── WV-1 record loading (PR9 --json output) ─────────────────────────────────


def test_load_wv1_outcomes(tmp_path: Path) -> None:
    path = tmp_path / "vendor.json"
    path.write_text(json.dumps({
        "results": {
            "Pair_A_jubarte_redline": {"outcome": "valid", "error": None, "duration_s": 1.0},
            "pair_b_jubarte_redline": {"outcome": "invalid", "error": "dialog", "duration_s": 2.0},
        },
    }))
    outcomes = lens_health.load_wv1_outcomes(path)
    assert outcomes == {"pair_a_jubarte_redline": "valid", "pair_b_jubarte_redline": "invalid"}


def test_load_wv1_outcomes_absent_or_corrupt(tmp_path: Path) -> None:
    assert lens_health.load_wv1_outcomes(tmp_path / "nope.json") == {}
    bad = tmp_path / "bad.json"
    bad.write_text("not json")
    assert lens_health.load_wv1_outcomes(bad) == {}


# ── Results line fields ──────────────────────────────────────────────────────


def test_build_results_carries_lens_fields() -> None:
    import uuid
    from datetime import UTC, datetime

    from neurotic_docx_bench.config import BenchConfig
    from neurotic_docx_bench.results_schema import build_results

    per_doc = {
        "a": _doc(pixel=95.0, accept=True, reject=True),
        "b": _doc(pixel=95.0, accept=True, reject=False),
    }
    results = build_results(
        id_run=uuid.uuid7(),
        vendor="t",
        benchmark="script_redlines",
        scores={"a": 95.0, "b": 95.0},
        per_doc=per_doc,  # type: ignore[arg-type]
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("oracle")),
        timestamp=datetime.now(UTC),
    )
    assert results.n_lens_disagree == 1
    assert results.lens_disagree_rate == 0.5


def test_build_results_lens_fields_none_without_lenses() -> None:
    import uuid
    from datetime import UTC, datetime

    from neurotic_docx_bench.config import BenchConfig
    from neurotic_docx_bench.results_schema import build_results

    results = build_results(
        id_run=uuid.uuid7(),
        vendor="t",
        benchmark="script_redlines",
        scores={"a": 95.0},
        per_doc={"a": {"overall_score": 95.0}},
        speed_samples_ms=[],
        environment_config=BenchConfig(source_of_truth=Path("oracle")),
        timestamp=datetime.now(UTC),
    )
    assert results.n_lens_disagree is None
    assert results.lens_disagree_rate is None
