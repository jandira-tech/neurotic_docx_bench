"""The published views have exactly one generator."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_legacy_generator_files_are_gone() -> None:
    for rel in (
        "scripts/update-readme-ranking.ts",
        "scripts/update-readme-ranking.test.ts",
        "scripts/export-results-md.py",
        "docs/RESULTS.md",
    ):
        assert not (ROOT / rel).exists(), rel


def test_package_json_has_no_readme_ranking_script() -> None:
    scripts = json.loads((ROOT / "package.json").read_text())["scripts"]
    assert "update-readme-ranking" not in scripts


def test_readme_points_at_bench_report_only() -> None:
    text = (ROOT / "README.md").read_text()
    for stale in ("export-results-md", "update-readme-ranking", "--update-readme", "docs/RESULTS.md"):
        assert stale not in text, stale
    assert "uv run bench report" in text


def test_ci_checks_the_published_views() -> None:
    text = (ROOT / ".github" / "workflows" / "bench.yml").read_text()
    assert "bench report --check" in text
