"""bench report: every view from the stores, idempotent, refuses unmapped lines."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.ledger import build as bd

README = (
    "# repo\n\nintro\n\n<!-- VENDORS-START -->\nold\n<!-- VENDORS-END -->\n\ntail\n"
)


def _line(
    vendor: str,
    median: float,
    ts: str,
    *,
    n: int = 25,
    version: str = "1.0",
    benchmark: str = "script_redlines",
) -> dict:
    scores = {f"doc{i}": median for i in range(n)}
    return {
        "id_run": f"run-{vendor}-{ts}",
        "vendor": vendor,
        "benchmark": benchmark,
        "n_docs": n,
        "overall_mean": median,
        "overall_median": median,
        "exact_100": 0,
        "scores": scores,
        "failures": [],
        "n_failures": 0,
        "itt_n_docs": n,
        "itt_mean": median,
        "itt_median": median,
        "tool_version": version,
        "timestamp": ts,
        "corpus_revision": "rev1",
        "scorer": "pagefair-v2",
        "holdout_mode": "excluded",
        "docset_id": "dset1",
        "renderer_id": "soffice-26.2.4.2",
        "environment_config": {"runs": [{"name": vendor, "render": "soffice"}]},
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    (tmp_path / "results").mkdir()
    (tmp_path / "bench.registry.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "tools": [
                    {
                        "id": "a",
                        "vendor": "a",
                        "display": "acme",
                        "role": "generator",
                        "engine": "a",
                        "run_names": ["a"],
                        "bench_vendors": ["a"],
                        "speed_tools": ["a"],
                        "url": "https://example.com/a",
                    },
                    {
                        "id": "b",
                        "vendor": "b",
                        "display": "bravo",
                        "role": "generator",
                        "engine": "b",
                        "run_names": ["b"],
                        "bench_vendors": ["b"],
                        "affiliated": True,
                    },
                ],
            }
        )
    )
    (tmp_path / "results" / "bench.jsonl").write_text(
        json.dumps(_line("a", 80.0, "2026-09-01T00:00:00+00:00"))
        + "\n"
        + json.dumps(_line("b", 90.0, "2026-09-02T00:00:00+00:00"))
        + "\n"
    )
    (tmp_path / "results" / "docsets.json").write_text(
        json.dumps({"dset1": {"benchmark": "script_redlines", "n": 25}})
    )
    (tmp_path / "results" / "speed.jsonl").write_text(
        json.dumps(
            {
                "kind": "speed_redlines",
                "tool": "a",
                "runtime": "rust",
                "run_ts": "2026-09-01T00:00:00Z",
                "fixture_count": 1000,
                "pair_count": 5000,
                "n": 5000,
                "failures": 0,
                "unit": "ms_per_redline",
                "mean": 20.0,
                "median": 6.0,
                "p95": 100.0,
                "tool_version": "1.0",
                "hardware": {"cpu": "x", "cores": 8},
            }
        )
        + "\n"
    )
    (tmp_path / "README.md").write_text(README)
    (tmp_path / "RESULTS.md").write_text("stale\n")
    return tmp_path


def test_build_produces_all_views(repo: Path) -> None:
    bundle = bd.build(repo, now=datetime(2026, 9, 27, tzinfo=UTC))
    assert "### script_redlines" in bundle.results_md
    assert "| 1 | bravo †" in bundle.results_md and "| 2 | acme |" in bundle.results_md
    assert "### speed_redlines" in bundle.results_md
    assert (
        "## History" in bundle.detailed_md
        and "## Paired comparisons" in bundle.detailed_md
    )
    assert "## Methodology" in bundle.detailed_md
    assert "| [acme](https://example.com/a) |" in bundle.readme_vendor_table
    assert "Generated 2026-09-27" in bundle.results_md


def test_write_replaces_readme_block_and_is_idempotent(repo: Path) -> None:
    now = datetime(2026, 9, 27, tzinfo=UTC)
    written = bd.write(repo, bd.build(repo, now=now))
    assert {p.name for p in written} == {
        "RESULTS.md",
        "RESULTS_DETAILED.md",
        "README.md",
    }
    readme = (repo / "README.md").read_text()
    assert (
        "old" not in readme
        and readme.startswith("# repo\n\nintro")
        and readme.endswith("tail\n")
    )
    first = (repo / "RESULTS.md").read_text()
    bd.write(repo, bd.build(repo, now=now))
    assert (repo / "RESULTS.md").read_text() == first
    assert (
        bd.changed_files(repo, bd.build(repo, now=datetime(2026, 9, 28, tzinfo=UTC)))
        == []
    )


def test_unmapped_line_is_an_error(repo: Path) -> None:
    with (repo / "results" / "bench.jsonl").open("a") as fh:
        fh.write(json.dumps(_line("ghost", 50.0, "2026-09-03T00:00:00+00:00")) + "\n")
    with pytest.raises(ValueError, match="ghost"):
        bd.build(repo)


def test_readme_without_markers_is_an_error(repo: Path) -> None:
    (repo / "README.md").write_text("no markers\n")
    with pytest.raises(ValueError, match="VENDORS-START"):
        bd.write(repo, bd.build(repo))


def test_cli_report_and_check(repo: Path, monkeypatch) -> None:
    monkeypatch.chdir(repo)
    r = CliRunner().invoke(app, ["report"])
    assert r.exit_code == 0, r.output
    assert "RESULTS.md" in r.output
    r = CliRunner().invoke(app, ["report", "--check"])
    assert r.exit_code == 0, r.output
    (repo / "RESULTS.md").write_text("drift\n")
    r = CliRunner().invoke(app, ["report", "--check"])
    assert r.exit_code == 1
    assert "RESULTS.md" in r.output
