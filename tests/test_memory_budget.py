"""Peak-memory budget per corpus size class + explicit wasm32-viability (TODO §1/§3).

The wasm32 lane has a hard 4 GiB linear-memory ceiling. A real run-fragmented diff
(the 276k-run dissertation, ~9.8 MiB inputs) peaks ~11.6 GiB native, so wasm32 aborts.
This module classifies a document by input size, attaches a peak-memory budget per
class, and emits an explicit ``wasm32_viable`` verdict.
"""

from __future__ import annotations

from neurotic_docx_bench import memory_budget as mb

_MiB = 1024**2
_GiB = 1024**3


def test_wasm32_ceiling_constant():
    assert mb.WASM32_CEILING_BYTES == 4 * 1024**3


def test_classify_by_input_size():
    assert mb.classify(800 * 1024).name == "small"   # < 1 MiB
    assert mb.classify(3 * _MiB).name == "medium"     # < 5 MiB
    assert mb.classify(9 * _MiB).name == "large"      # < 12 MiB
    assert mb.classify(50 * _MiB).name == "xlarge"    # >= 12 MiB


def test_wasm32_viable_threshold():
    assert mb.wasm32_viable(3 * _GiB) is True
    assert mb.wasm32_viable(4 * _GiB) is False   # equal to the ceiling is NOT viable
    assert mb.wasm32_viable(11 * _GiB) is False


def test_dissertation_class_is_not_wasm32_viable_and_over_budget():
    """The 276k-run dissertation: ~9.8 MiB input, ~11.6 GiB native peak. wasm32
    cannot run it (>4 GiB), and it blows its size-class budget → fail."""
    input_bytes = int(9.8 * _MiB)
    peak = int(11.6 * _GiB)
    sc = mb.classify(input_bytes)
    assert sc.name == "large"
    assert sc.wasm32_viable is False
    assert mb.wasm32_viable(peak) is False
    result = mb.budget_gate(input_bytes, peak)
    assert result.status == "fail"
    assert result.exit_code == 1
    assert "wasm32_viable" in result.reason


def test_small_doc_is_wasm32_viable_and_passes():
    input_bytes = 400 * 1024   # < 1 MiB
    peak = int(1.2 * _GiB)     # sub-4-GiB, within the small-class budget
    sc = mb.classify(input_bytes)
    assert sc.name == "small"
    assert sc.wasm32_viable is True
    assert mb.wasm32_viable(peak) is True
    result = mb.budget_gate(input_bytes, peak)
    assert result.status == "pass"
    assert result.exit_code == 0
    assert "wasm32_viable" in result.reason


def test_budget_gate_returns_gateresult():
    """The advisory gate reuses gate.GateResult (status / reason / exit_code)."""
    from neurotic_docx_bench.gate import GateResult

    assert isinstance(mb.budget_gate(400 * 1024, 100 * _MiB), GateResult)


def test_config_memory_budgets_override(tmp_path):
    """An optional ``memory_budgets:`` block in bench.yaml overrides the defaults."""
    from neurotic_docx_bench.config import load_config

    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "memory_budgets:\n"
        "  - {name: tiny, max_input_bytes: 1024, peak_budget_bytes: 1048576, wasm32_viable: true}\n"
        "  - {name: huge, max_input_bytes: 9999999999, peak_budget_bytes: 8589934592, wasm32_viable: false}\n"
        "runs:\n"
        "  - {name: t, render: passthrough, unversioned: true}\n",
    )
    cfg = load_config(cfg_path)
    assert [sc.name for sc in cfg.memory_budgets] == ["tiny", "huge"]
    # classify honours the overridden table
    assert mb.classify(500, cfg.memory_budgets).name == "tiny"
    assert mb.classify(5000, cfg.memory_budgets).name == "huge"


def test_config_absent_memory_budgets_defaults_to_empty(tmp_path):
    """Absent block → empty tuple; consumers fall back to DEFAULT_SIZE_CLASSES."""
    from neurotic_docx_bench.config import load_config

    cfg_path = tmp_path / "bench.yaml"
    cfg_path.write_text(
        "source_of_truth: oracle\n"
        "runs:\n"
        "  - {name: t, render: passthrough, unversioned: true}\n",
    )
    cfg = load_config(cfg_path)
    assert cfg.memory_budgets == ()
