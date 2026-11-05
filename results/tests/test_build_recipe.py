"""Full build-recipe capture (TODO §2): the engine pin records *which* build
produced a result; ``resolve_build_recipe`` records the build FLAGS that shape
the wasm artifact (rustflags + wasm-opt), threaded onto the ``Results`` line."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench import tool_updater
from neurotic_docx_bench.config import BenchConfig

_RUSTFLAGS = ["-C", "target-feature=+simd128", "-C", "link-arg=-zstack-size=8388608"]
_WASM_OPT = ["-O3", "--enable-bulk-memory", "--enable-simd"]


def _write_wasm_dist(root: Path) -> None:
    """Lay out a wasm dist like the vendored one: ``.cargo/config.toml`` +
    ``Cargo.toml`` next to the ``pkg/`` artifact dir."""
    cargo_dir = root / ".cargo"
    cargo_dir.mkdir(parents=True)
    (cargo_dir / "config.toml").write_text(
        "[target.wasm32-unknown-unknown]\n"
        'rustflags = ["-C", "target-feature=+simd128", '
        '"-C", "link-arg=-zstack-size=8388608"]\n',
    )
    (root / "Cargo.toml").write_text(
        "[package]\n"
        'name = "jubarte-wasm"\n'
        "[package.metadata.wasm-pack.profile.release]\n"
        'wasm-opt = ["-O3", "--enable-bulk-memory", "--enable-simd"]\n',
    )
    (root / "pkg").mkdir()


def test_resolve_build_recipe_parses_both_flag_lists(tmp_path):
    dist = tmp_path / "jubarte-wasm"
    _write_wasm_dist(dist)
    recipe = tool_updater.resolve_build_recipe(dist)
    assert recipe == {"rustflags": _RUSTFLAGS, "wasm_opt": _WASM_OPT}


def test_resolve_build_recipe_from_pkg_subdir(tmp_path):
    """The loaded artifact is ``pkg/``; the TOML files are one level up. Passing
    the ``pkg/`` dir must still find the recipe in its parent."""
    dist = tmp_path / "jubarte-wasm"
    _write_wasm_dist(dist)
    recipe = tool_updater.resolve_build_recipe(dist / "pkg")
    assert recipe == {"rustflags": _RUSTFLAGS, "wasm_opt": _WASM_OPT}


def test_resolve_build_recipe_binary_dist_returns_none(tmp_path):
    """A plain binary dir (no .cargo/config.toml, no Cargo.toml) has no build
    recipe — ``None``, not an error."""
    binary = tmp_path / "jubarte-rust"
    binary.mkdir()
    (binary / "redline").write_bytes(b"\x7fELF-fake-binary")
    assert tool_updater.resolve_build_recipe(binary) is None


def test_resolve_build_recipe_robust_to_missing_subkeys(tmp_path):
    """Missing rustflags / wasm-opt sub-keys degrade to empty lists, not errors."""
    dist = tmp_path / "partial"
    (dist / ".cargo").mkdir(parents=True)
    (dist / ".cargo" / "config.toml").write_text("[build]\njobs = 4\n")
    (dist / "Cargo.toml").write_text('[package]\nname = "x"\n')
    assert tool_updater.resolve_build_recipe(dist) == {"rustflags": [], "wasm_opt": []}


def test_build_recipe_threaded_onto_results_line(tmp_path):
    """When a recipe is supplied it lands on the emitted JSONL line; when omitted
    the line carries ``None`` (mirrors ``tool_version`` optionality)."""
    from neurotic_docx_bench.emit.jsonl import build_results_line

    cfg = BenchConfig(source_of_truth=Path("oracle"))
    recipe = {"rustflags": _RUSTFLAGS, "wasm_opt": _WASM_OPT}
    line = build_results_line(
        id_run=uuid.uuid7(),
        vendor="jubarte",
        benchmark="script_redlines",
        scores={"a": 100.0, "b": 80.0},
        per_doc=None,
        speed_samples_ms=[5.0, 7.0],
        environment_config=cfg,
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
        tool_version="jubarte-wasm@abc123def456",
        build_recipe=recipe,
    )
    assert line["build_recipe"] == recipe

    line_no_recipe = build_results_line(
        id_run=uuid.uuid7(),
        vendor="jubarte",
        benchmark="script_redlines",
        scores={"a": 100.0},
        per_doc=None,
        speed_samples_ms=[5.0],
        environment_config=cfg,
        timestamp=datetime(2026, 7, 7, tzinfo=UTC),
    )
    assert line_no_recipe["build_recipe"] is None
