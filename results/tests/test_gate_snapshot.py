"""gate (PLAN §8) + snapshot round-trip."""

from __future__ import annotations

from neurotic_docx_bench.emit.snapshot import load_snapshot, write_snapshot
from neurotic_docx_bench.gate import gate


# ---- snapshot ----------------------------------------------------------------
def test_snapshot_roundtrip_tab_indented(tmp_path):
    scores = {"b": 80.0, "a": 100.0}
    path = write_snapshot(tmp_path, "jubarte", scores)
    assert path.read_text().startswith("{\n\t"), "snapshot must be tab-indented"
    loaded = load_snapshot(tmp_path, "jubarte")
    assert loaded == {"a": 100.0, "b": 80.0}
    assert load_snapshot(tmp_path, "missing") is None


# ---- gate --------------------------------------------------------------------
def test_no_baseline_passes():
    r = gate({"a": 50.0}, None)
    assert r.status == "pass" and r.exit_code == 0


def test_identical_passes():
    base = {"a": 90.0, "b": 100.0}
    r = gate(dict(base), base)
    assert r.status == "pass"


def test_per_doc_regression_warns_only():
    base = {"a": 90.0, "b": 80.0}
    cur = {"a": 90.0, "b": 70.0}  # b dropped, but mean/median must not drop below base
    r = gate(cur, base)
    # mean 80→80? base mean=85, cur mean=80 -> that's an aggregate drop => fail.
    # Use a case where aggregate holds: raise a to keep mean equal.
    cur2 = {"a": 100.0, "b": 70.0}  # mean 85==85, median 85==85, b regressed
    r2 = gate(cur2, base)
    assert r2.status == "warn"
    assert r2.regressed_docs == ["b"]
    assert r2.exit_code == 0


def test_aggregate_regression_fails():
    base = {"a": 90.0, "b": 80.0}
    cur = {"a": 80.0, "b": 80.0}  # mean 85→80
    r = gate(cur, base)
    assert r.status == "fail" and r.exit_code == 1
    assert "mean" in r.reason


def test_doc_at_100_never_flagged():
    base = {"a": 100.0, "b": 80.0}
    cur = {"a": 100.0, "b": 100.0}  # improvement
    r = gate(cur, base)
    assert r.status == "pass"


def test_regressed_doc_still_100_not_flagged():
    # a doc that is at 100 now is never a regression even if baseline recorded >100 noise
    base = {"a": 100.0}
    cur = {"a": 100.0}
    assert gate(cur, base).status == "pass"
