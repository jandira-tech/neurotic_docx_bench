"""S0.4 — the holdout gate (execution contract C6).

C6 says "done" must be decidable: the sealed 40-pair holdout passes when its mean
and median are each within 5 points of the same engine's ITT figures, diverges when
it falls more than 5 points below (the honesty clause), the seal's checksum is
recorded so a silently-changed holdout is detectable, and the holdout is run ONCE
per engine per programme.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from neurotic_docx_bench import oracle_manifest
from neurotic_docx_bench.diagnostics import holdout_gate


# ── holdout_verdict: the pass band ───────────────────────────────────────────


def test_pass_when_both_figures_are_within_tolerance() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=87.0, holdout_median=89.5,
    )
    assert v.verdict == "PASS"
    assert v.passed is True
    assert "consistent" in v.reason


def test_pass_exactly_at_the_tolerance_boundary_below() -> None:
    # `== tolerance` is a PASS: C6 passes when "within 5 points" and diverges only
    # when the holdout falls "more than 5 points below". Exactly 5 is neither.
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=85.0, holdout_median=87.0,
    )
    assert v.verdict == "PASS"
    assert v.mean_delta == pytest.approx(-5.0)
    assert v.median_delta == pytest.approx(-5.0)


def test_pass_exactly_at_the_tolerance_boundary_above() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=95.0, holdout_median=97.0,
    )
    assert v.verdict == "PASS"


def test_boundary_survives_float_representation_error() -> None:
    # 64.01 − 59.01 is 5.000000000000007 in binary floating point. A bare `> 5.0`
    # turns the documented boundary PASS into a spurious DIVERGENT — and a
    # spurious DIVERGENT publishes the honesty clause against a clean result.
    assert 64.01 - 59.01 > 5.0  # the trap this test exists for
    v = holdout_gate.holdout_verdict(
        itt_mean=64.01, itt_median=64.01, holdout_mean=59.01, holdout_median=59.01,
    )
    assert v.verdict == "PASS"


# ── holdout_verdict: divergence (the honesty clause) ─────────────────────────


def test_divergent_on_mean_only() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=80.0, holdout_median=90.0,
    )
    assert v.verdict == "DIVERGENT"
    assert "mean" in v.reason
    assert "median" not in v.reason


def test_divergent_on_median_only() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=89.0, holdout_median=80.0,
    )
    assert v.verdict == "DIVERGENT"
    assert "median" in v.reason


def test_divergent_on_both() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=70.0, holdout_median=71.0,
    )
    assert v.verdict == "DIVERGENT"
    assert "mean" in v.reason and "median" in v.reason


def test_divergent_carries_the_non_negotiable_publication_note() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=70.0, holdout_median=71.0,
    )
    note = v.publication_note
    assert note is not None
    # The clause must state the finding AND carry the numbers, so it cannot be
    # published detached from the figures it qualifies.
    assert "corpus-specific" in note
    assert "did not generalise" in note
    assert "70.00" in note and "90.00" in note


def test_pass_carries_no_publication_note() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=89.0, holdout_median=91.0,
    )
    assert v.publication_note is None


# ── holdout_verdict: the holdout-above-ITT branch ────────────────────────────


def test_holdout_far_above_itt_is_unrepresentative_not_pass() -> None:
    # Not an overfitting failure — but the consistency check failed symmetrically,
    # so it is not a clean PASS either.
    v = holdout_gate.holdout_verdict(
        itt_mean=80.0, itt_median=82.0, holdout_mean=95.0, holdout_median=96.0,
    )
    assert v.verdict == "UNREPRESENTATIVE"
    assert v.passed is False
    assert "above" in v.reason


def test_unrepresentative_carries_its_own_note_not_the_honesty_clause() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=80.0, itt_median=82.0, holdout_mean=95.0, holdout_median=96.0,
    )
    note = v.publication_note
    assert note is not None
    assert "not a representative sample" in note
    assert "corroborat" in note
    # The overfitting clause belongs to DIVERGENT alone; attaching it here would
    # publish a claim the number does not support.
    assert "corpus-specific" not in note


def test_divergent_wins_when_the_two_figures_disagree_in_direction() -> None:
    # Mean 15 below, median 15 above. Evidence of non-generalisation outranks
    # evidence of an unrepresentative sample.
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=80.0, holdout_mean=75.0, holdout_median=95.0,
    )
    assert v.verdict == "DIVERGENT"


# ── holdout_verdict: plumbing ────────────────────────────────────────────────


def test_custom_tolerance_is_respected() -> None:
    kw = dict(itt_mean=90.0, itt_median=90.0, holdout_mean=87.0, holdout_median=90.0)
    assert holdout_gate.holdout_verdict(**kw).verdict == "PASS"
    assert holdout_gate.holdout_verdict(**kw, tolerance=2.0).verdict == "DIVERGENT"


def test_verdict_records_signed_deltas_and_tolerance() -> None:
    v = holdout_gate.holdout_verdict(
        itt_mean=90.0, itt_median=92.0, holdout_mean=80.0, holdout_median=95.0,
    )
    # holdout − ITT: negative means the holdout scored lower.
    assert v.mean_delta == pytest.approx(-10.0)
    assert v.median_delta == pytest.approx(3.0)
    assert v.tolerance == pytest.approx(5.0)


# ── check_seal ───────────────────────────────────────────────────────────────


def _sealed(tmp_path: Path, body: str = "# sealed\na_b\nc_d\n") -> Path:
    p = tmp_path / "holdout_combined.txt"
    p.write_text(body)
    return p


def test_check_seal_intact_for_the_recorded_full_digest(tmp_path: Path) -> None:
    p = _sealed(tmp_path)
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    st = holdout_gate.check_seal(p, digest)
    assert st.state == "intact"
    assert st.intact is True
    assert st.actual == digest


def test_check_seal_reuses_the_oracle_manifest_checksum_idiom(tmp_path: Path) -> None:
    # One checksum implementation in the repo, not two.
    p = _sealed(tmp_path)
    assert holdout_gate.seal_checksum(p) == oracle_manifest._sha256(p)


def test_check_seal_accepts_the_short_recorded_prefix(tmp_path: Path) -> None:
    # `cli._corpus_revision` records sha256(...)[:12]; a result stamped that way
    # must still verify against the full recomputed digest.
    p = _sealed(tmp_path)
    short = hashlib.sha256(p.read_bytes()).hexdigest()[:12]
    assert holdout_gate.check_seal(p, short).state == "intact"


def test_check_seal_rejects_a_prefix_too_short_to_be_evidence(tmp_path: Path) -> None:
    p = _sealed(tmp_path)
    stub = hashlib.sha256(p.read_bytes()).hexdigest()[:4]
    st = holdout_gate.check_seal(p, stub)
    assert st.state == "unverifiable"
    assert st.intact is False


def test_check_seal_detects_a_silently_changed_holdout(tmp_path: Path) -> None:
    p = _sealed(tmp_path)
    recorded = hashlib.sha256(p.read_bytes()).hexdigest()
    p.write_text("# sealed\na_b\nc_d\ne_f\n")  # a key quietly added
    st = holdout_gate.check_seal(p, recorded)
    assert st.state == "mismatch"
    assert st.intact is False
    assert st.expected == recorded
    assert st.actual != recorded
    assert "changed" in st.reason


def test_check_seal_missing_manifest_is_unverifiable_never_intact(tmp_path: Path) -> None:
    st = holdout_gate.check_seal(tmp_path / "gone.txt", "0" * 64)
    assert st.state == "unverifiable"
    assert st.intact is False
    assert st.actual is None
    assert "not found" in st.reason


def test_check_seal_without_a_recorded_checksum_is_unverifiable(tmp_path: Path) -> None:
    # A result predating the gate records nothing. That must not read as a pass.
    p = _sealed(tmp_path)
    for recorded in (None, "", "   "):
        st = holdout_gate.check_seal(p, recorded)
        assert st.state == "unverifiable", recorded
        assert st.intact is False
        assert "recorded no seal checksum" in st.reason


def test_check_seal_is_case_insensitive_about_the_recorded_hex(tmp_path: Path) -> None:
    p = _sealed(tmp_path)
    upper = hashlib.sha256(p.read_bytes()).hexdigest().upper()
    assert holdout_gate.check_seal(p, upper).state == "intact"


# ── assert_single_use ────────────────────────────────────────────────────────


def _run_id() -> str:
    return str(uuid.uuid4())


def _holdout_lines(run_id: str, *, vendor: str = "jubarte") -> list[dict]:
    """One `bench run --holdout` invocation: several benchmark lines sharing the
    run's single ``id_run`` (cli assigns it once per run config)."""
    return [
        {
            "id_run": run_id,
            "vendor": vendor,
            "benchmark": bm,
            "holdout_mode": "only",
        }
        for bm in ("script_redlines", "accepted_changes", "visual_redlines")
    ]


def test_one_holdout_run_across_many_benchmark_lines_is_clean() -> None:
    # The trap: a single --holdout run emits one line per benchmark. Counting
    # LINES would condemn a perfectly legal single use.
    lines = _holdout_lines(_run_id())
    assert len(lines) == 3
    assert holdout_gate.assert_single_use(lines) is None


def test_two_holdout_runs_are_flagged() -> None:
    lines = _holdout_lines(_run_id()) + _holdout_lines(_run_id())
    warning = holdout_gate.assert_single_use(lines)
    assert warning is not None
    assert warning.n_uses == 2
    assert len(warning.run_ids) == 2


def test_three_holdout_runs_are_flagged() -> None:
    lines = [
        line
        for _ in range(3)
        for line in _holdout_lines(_run_id())
    ]
    warning = holdout_gate.assert_single_use(lines)
    assert warning is not None
    assert warning.n_uses == 3


def test_zero_holdout_runs_is_clean() -> None:
    assert holdout_gate.assert_single_use([]) is None
    assert holdout_gate.assert_single_use(
        [{"id_run": _run_id(), "vendor": "v", "holdout_mode": "excluded"}],
    ) is None


def test_non_holdout_lines_never_count_as_uses() -> None:
    rid = _run_id()
    lines = [
        {"id_run": _run_id(), "vendor": "jubarte", "holdout_mode": "excluded"},
        {"id_run": _run_id(), "vendor": "jubarte", "holdout_mode": None},
        {"id_run": _run_id(), "vendor": "jubarte"},  # pre-holdout line
        *_holdout_lines(rid),
    ]
    assert holdout_gate.assert_single_use(lines) is None


def test_repeat_use_message_names_the_engine_and_the_consequence() -> None:
    lines = _holdout_lines(_run_id(), vendor="jubarte-rust") + _holdout_lines(
        _run_id(), vendor="jubarte-rust",
    )
    warning = holdout_gate.assert_single_use(lines)
    assert warning is not None
    assert warning.engine == "jubarte-rust"
    assert "jubarte-rust" in warning.message
    assert "training data" in warning.message
    assert "2" in warning.message


def test_explicit_engine_name_overrides_the_recorded_vendor() -> None:
    lines = _holdout_lines(_run_id()) + _holdout_lines(_run_id())
    warning = holdout_gate.assert_single_use(lines, engine="engine-of-record")
    assert warning is not None
    assert warning.engine == "engine-of-record"


def test_mixed_vendors_are_surfaced_rather_than_silently_merged() -> None:
    lines = _holdout_lines(_run_id(), vendor="a") + _holdout_lines(_run_id(), vendor="b")
    warning = holdout_gate.assert_single_use(lines)
    assert warning is not None
    assert warning.engine == "a+b"


def test_results_objects_work_as_well_as_jsonl_dicts() -> None:
    rid_a, rid_b = _run_id(), _run_id()
    runs = [
        SimpleNamespace(id_run=rid_a, vendor="v", holdout_mode="only"),
        SimpleNamespace(id_run=rid_a, vendor="v", holdout_mode="only"),
        SimpleNamespace(id_run=rid_b, vendor="v", holdout_mode="only"),
    ]
    warning = holdout_gate.assert_single_use(runs)
    assert warning is not None
    assert warning.n_uses == 2


def test_lines_without_a_run_id_fall_back_to_the_timestamp() -> None:
    stamp = "2026-08-04T12:00:00+00:00"
    lines = [
        {"vendor": "v", "holdout_mode": "only", "benchmark": "script_redlines",
         "timestamp": stamp},
        {"vendor": "v", "holdout_mode": "only", "benchmark": "accepted_changes",
         "timestamp": stamp},
    ]
    assert holdout_gate.assert_single_use(lines) is None


def test_lines_with_no_identity_at_all_count_as_distinct_uses() -> None:
    # Unidentifiable records are counted separately: a false alarm is recoverable,
    # a silently-missed second use destroys the overfitting check.
    lines = [
        {"vendor": "v", "holdout_mode": "only"},
        {"vendor": "v", "holdout_mode": "only"},
    ]
    warning = holdout_gate.assert_single_use(lines)
    assert warning is not None
    assert warning.n_uses == 2
