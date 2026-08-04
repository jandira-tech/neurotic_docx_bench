"""Noise-floor-aware gate epsilon + paired vendor stats (PR6).

Empirical finding (adversarial spec review): double-rendering the same DOCX with the
same LibreOffice produces byte-identical rasters — the render noise floor is 0, and
the fixed 1e-4 epsilon is already correct. The machinery still earns its keep by
(a) RECORDING that zero per environment (a nonzero sigma is itself an environment
alarm, complementing the canary) and (b) making the gate epsilon explicit and
overridable instead of a buried constant.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from neurotic_docx_bench import noise_floor
from neurotic_docx_bench.gate import gate


def test_gate_accepts_explicit_eps() -> None:
    baseline = {"a": 90.0, "b": 80.0}
    # Drop of 0.005 on mean: fails with default eps, passes with eps=0.01.
    current = {"a": 89.99, "b": 80.0}
    assert gate(current, baseline).status == "fail"
    assert gate(current, baseline, eps=0.01).status == "pass"


def test_gate_default_eps_unchanged() -> None:
    baseline = {"a": 90.0}
    assert gate({"a": 90.0}, baseline).status == "pass"
    assert gate({"a": 89.9998}, baseline).status == "fail"


def test_eps_from_noise_floor_file(tmp_path: Path) -> None:
    p = tmp_path / "noise_floor.json"
    assert noise_floor.eps_from_file(p) == pytest.approx(1e-4)  # missing → default
    p.write_text(json.dumps({"sigma": 0.05, "max_delta": 0.1, "n": 10}))
    assert noise_floor.eps_from_file(p) == pytest.approx(0.15)  # 3*sigma
    p.write_text(json.dumps({"sigma": 0.0, "max_delta": 0.0, "n": 10}))
    assert noise_floor.eps_from_file(p) == pytest.approx(1e-4)  # floor at default
    p.write_text("garbage")
    assert noise_floor.eps_from_file(p) == pytest.approx(1e-4)


def test_measure_noise_floor_stats() -> None:
    stats = noise_floor.stats_from_deltas([0.0, 0.0, 0.2, 0.1])
    assert stats["n"] == 4
    assert stats["max_delta"] == pytest.approx(0.2)
    assert stats["sigma"] == pytest.approx(0.0829156, abs=1e-4)
    assert noise_floor.stats_from_deltas([]) == {"n": 0, "sigma": 0.0, "max_delta": 0.0}
