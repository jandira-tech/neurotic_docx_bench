"""Pin + config gates for the stemma and post-PR-854 safe-docx generating runs.

These tests drive the shipped config and pin files — they do not mock compare,
and they refuse the published ``@usejunior/docx-compare@0.19.1`` tarball (that
release predates PR 854).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from neurotic_docx_bench.config import expand_generate_commands, load_config
from neurotic_docx_bench.tool_updater import resolve_local_version

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCH_YAML = REPO_ROOT / "bench.yaml"
STEMMA_DIST = REPO_ROOT / "src/neurotic_docx_bench/utils/stemma"
SAFE_DIST = REPO_ROOT / "src/neurotic_docx_bench/utils/safe-docx-compare"
STEMMA_COMMIT = "efaed0c1ecb41142b1465bbb124dd183c385a2b0"
SAFE_COMMIT = "7bd35c876493f2725b095f0190c28d2644962c78"
ALLOWED_BENCHMARKS = {"script_redlines", "accepted_changes", "roundtrip"}


def _runs() -> dict[str, dict]:
    doc = yaml.safe_load(BENCH_YAML.read_text())
    return {r["name"]: r for r in doc.get("runs", [])}


def test_stemma_and_safe_docx_runs_are_registered():
    runs = _runs()
    assert "stemma" in runs
    assert "safe-docx-compare" in runs


def test_runs_inherit_all_three_corpora_and_do_not_hardcode_driver_flags():
    cfg = load_config(BENCH_YAML)
    for name in ("stemma", "safe-docx-compare"):
        run = next(r for r in cfg.runs if r.name == name)
        assert run.generate
        assert "--manifest" not in run.generate
        assert "--source-dir" not in run.generate
        assert "--limit" not in run.generate
        expanded = expand_generate_commands(cfg, run)
        assert len(expanded) == 3, f"{name} must expand across all three corpora"
        assert all("--manifest=" in cmd and "--source-dir=" in cmd for cmd in expanded)


def test_declared_benchmarks_are_generating_only():
    runs = _runs()
    for name in ("stemma", "safe-docx-compare"):
        benches = set(runs[name]["benchmarks"])
        assert benches == ALLOWED_BENCHMARKS
        assert not any(b.startswith("visual_") for b in benches)


def test_safe_docx_is_git_pinned_not_published_0191():
    """package: cannot express 7bd35c8; the published 0.19.1 tarball predates PR 854."""
    raw = _runs()["safe-docx-compare"]
    assert "package" not in raw
    assert raw["dist"] == "src/neurotic_docx_bench/utils/safe-docx-compare"
    commit = (SAFE_DIST / "ENGINE_COMMIT.txt").read_text().strip()
    assert commit == SAFE_COMMIT
    assert "0.19.1" not in str(raw.get("package", ""))


def test_stemma_pin_is_cli_050_with_v050_commit():
    raw = _runs()["stemma"]
    assert raw["dist"] == "src/neurotic_docx_bench/utils/stemma"
    commit = (STEMMA_DIST / "ENGINE_COMMIT.txt").read_text().strip()
    assert commit == STEMMA_COMMIT
    version = json.loads((STEMMA_DIST / "package.json").read_text())["version"]
    assert version == "0.5.0"


def test_tool_version_hashes_executed_bytes_and_records_git():
    if not (STEMMA_DIST / "stemma").is_file():
        return
    stemma_ver = resolve_local_version(STEMMA_DIST)
    assert stemma_ver.startswith("0.5.0@")
    assert f"+git.{STEMMA_COMMIT}" in stemma_ver

    if not (SAFE_DIST / "node_modules/@usejunior/docx-compare/dist/index.js").is_file():
        return
    safe_ver = resolve_local_version(SAFE_DIST)
    assert f"+git.{SAFE_COMMIT}" in safe_ver
    # Must not look like a bare published npm 0.19.1 with no git suffix.
    assert "+git." in safe_ver
