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


# ---- frozen pages: RESULTS_v{bench_version}.md, written once when the version moves ----

T1 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
T2 = datetime(2026, 9, 27, 9, 30, tzinfo=UTC)


def test_results_page_states_its_provenance(repo: Path) -> None:
    bundle = bd.build(repo, now=T1, version="0.7.0")
    prov = bd.provenance(bundle.results_md)
    assert prov == bd.Provenance(
        bench_version="0.7.0",
        docsets=("dset1",),
        scorers=("pagefair-v2",),
        renderers=("soffice-26.2.4.2",),
    )
    assert bd.provenance("# Benchmark results\n\nlegacy\n") is None


def test_provenance_round_trips_empty_lists() -> None:
    prov = bd.Provenance(bench_version="0.7.0", docsets=(), scorers=(), renderers=())
    assert bd.provenance(prov.line() + "\n") == prov


def test_freeze_writes_previous_page_once(repo: Path) -> None:
    bd.write(repo, bd.build(repo, now=T1, version="0.6.0"))
    old_page = (repo / "RESULTS.md").read_text()
    new = bd.build(repo, now=T2, version="0.7.0")
    frozen = bd.freeze(repo, new, now=T2)
    assert frozen == repo / "RESULTS_v0.6.0.md"
    text = frozen.read_text()
    assert text.startswith(bd.FROZEN_NOTE)
    assert "# Benchmark results, frozen at bench 0.6.0" in text
    assert "Frozen 2026-09-27 09:30 UTC when the bench moved to 0.7.0." in text
    assert "Docsets: dset1." in text
    assert "Scorers: pagefair-v2." in text
    assert "Renderers: soffice-26.2.4.2." in text
    assert bd.GENERATED_NOTE not in text
    body = old_page[old_page.index("# Benchmark results") :]
    assert body.strip() in text
    # Nothing to freeze once RESULTS.md carries the current version.
    bd.write(repo, new)
    assert bd.freeze(repo, new, now=T2) is None
    # A frozen page is never overwritten.
    (repo / "RESULTS.md").write_text(old_page)
    frozen.write_text("kept\n")
    assert bd.freeze(repo, new, now=T2) is None
    assert frozen.read_text() == "kept\n"


def test_freeze_of_unmarked_page_is_the_pre_stamp_version(repo: Path) -> None:
    (repo / "RESULTS.md").write_text("# Benchmark results\n\n| legacy | table |\n")
    new = bd.build(repo, now=T2, version="0.7.0")
    frozen = bd.freeze(repo, new, now=T2)
    assert frozen is not None and frozen.name == "RESULTS_v0.6.0.md"
    text = frozen.read_text()
    assert "frozen at bench 0.6.0" in text
    assert "| legacy | table |" in text
    # Metadata comes from the stores when the old page did not state it.
    assert "Docsets: dset1." in text
    assert "Renderers: soffice-26.2.4.2." in text


def test_freeze_skips_unknown_versions(repo: Path) -> None:
    from neurotic_docx_bench.version import UNKNOWN

    bd.write(repo, bd.build(repo, now=T1, version="0.6.0"))
    assert bd.freeze(repo, bd.build(repo, now=T2, version=UNKNOWN), now=T2) is None
    bd.write(repo, bd.build(repo, now=T1, version=UNKNOWN))
    assert bd.freeze(repo, bd.build(repo, now=T2, version="0.7.0"), now=T2) is None
    assert not list(repo.glob("RESULTS_v*.md"))


def test_cli_report_freezes_when_the_version_moves(repo: Path, monkeypatch) -> None:
    from neurotic_docx_bench import version as ver

    monkeypatch.chdir(repo)
    monkeypatch.setattr(ver, "bench_version", lambda: "0.6.0")
    r = CliRunner().invoke(app, ["report"])
    assert r.exit_code == 0, r.output
    assert "froze" not in r.output
    monkeypatch.setattr(ver, "bench_version", lambda: "0.7.0")
    r = CliRunner().invoke(app, ["report", "--check"])
    assert r.exit_code == 1, r.output  # the page still says 0.6.0
    assert not (repo / "RESULTS_v0.6.0.md").exists()  # --check never writes
    r = CliRunner().invoke(app, ["report"])
    assert r.exit_code == 0, r.output
    assert "froze RESULTS_v0.6.0.md" in r.output
    assert (repo / "RESULTS_v0.6.0.md").is_file()
    r = CliRunner().invoke(app, ["report", "--check"])
    assert r.exit_code == 0, r.output
