"""Archiving moves rows out of the ranked store without losing them; retractions are stated."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import yaml
from typer.testing import CliRunner

from neurotic_docx_bench.cli import app
from neurotic_docx_bench.ledger import archive as ar
from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger.registry import load_registry
from neurotic_docx_bench.ledger.rows import load_bench_rows


def _line(
    vendor: str,
    ts: str,
    *,
    crev: str | None = "rev1",
    scores: bool = True,
    holdout: str | None = "excluded",
    id_run: str | None = None,
) -> dict:
    return {
        "id_run": id_run or f"run-{vendor}-{ts}",
        "vendor": vendor,
        "benchmark": "script_redlines",
        "n_docs": 2,
        "overall_mean": 50.0,
        "overall_median": 50.0,
        "exact_100": 0,
        "scores": {"a": 50.0, "b": 50.0} if scores else {},
        "failures": [],
        "tool_version": "1.0",
        "timestamp": ts,
        "corpus_revision": crev,
        "holdout_mode": holdout,
        "environment_config": {"runs": [{"name": vendor, "render": "soffice"}]},
    }


def _registry(tmp_path: Path):
    p = tmp_path / "bench.registry.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "tools": [
                    {
                        "id": "a",
                        "vendor": "a",
                        "display": "a",
                        "role": "generator",
                        "engine": "a",
                        "run_names": ["a"],
                        "bench_vendors": ["a"],
                    },
                ],
            }
        )
    )
    return load_registry(p)


def test_split_store_archives_legacy_holdout_and_retracted(tmp_path: Path) -> None:
    store = tmp_path / "results" / "bench.jsonl"
    store.parent.mkdir()
    lines = [
        _line("a", "2026-07-01T00:00:00+00:00", crev=None),  # legacy
        _line("a", "2026-08-01T00:00:00+00:00", holdout="only"),  # holdout-only
        _line("a", "2026-08-02T00:00:00+00:00", id_run="bad"),  # retracted
        _line("a", "2026-08-03T00:00:00+00:00"),  # kept
    ]
    store.write_text("".join(json.dumps(ln) + "\n" for ln in lines))
    ret = [
        pol.Retraction(
            id_run="bad",
            reason="broken harness",
            retracted_at=datetime(2026, 8, 4, tzinfo=UTC),
            by="me",
        )
    ]
    result = ar.split_store(
        store,
        tmp_path / "results" / "archive",
        registry=_registry(tmp_path),
        retractions=ret,
        now=datetime(2026, 9, 27, tzinfo=UTC),
        dry_run=False,
    )
    assert result.kept == 1 and result.archived == 3
    assert len(store.read_text().splitlines()) == 1
    archived = (
        (tmp_path / "results" / "archive" / "bench-2026-09-27.jsonl")
        .read_text()
        .splitlines()
    )
    assert len(archived) == 3
    manifest = (tmp_path / "results" / "archive" / "MANIFEST.md").read_text()
    assert "legacy provenance" in manifest
    assert "holdout-only run" in manifest
    assert "retracted: broken harness" in manifest
    assert json.loads(archived[0])["id_run"] == "run-a-2026-07-01T00:00:00+00:00"
    # Archived rows load with the archived flag and are ineligible for that reason.
    rows, _ = load_bench_rows(
        tmp_path / "results" / "archive" / "bench-2026-09-27.jsonl",
        _registry(tmp_path),
        archived=True,
    )
    assert all(r.archived for r in rows)
    v = pol.eligibility(
        rows[2], expected=2, retractions=[], registry=_registry(tmp_path)
    )
    assert "archived" in v.reasons


def test_split_store_appends_to_an_existing_archive_and_manifest(
    tmp_path: Path,
) -> None:
    store = tmp_path / "results" / "bench.jsonl"
    store.parent.mkdir()
    store.write_text(
        json.dumps(_line("a", "2026-07-01T00:00:00+00:00", crev=None)) + "\n"
    )
    now = datetime(2026, 9, 27, tzinfo=UTC)
    ar.split_store(
        store,
        tmp_path / "results" / "archive",
        registry=_registry(tmp_path),
        retractions=[],
        now=now,
        dry_run=False,
    )
    store.write_text(
        json.dumps(_line("a", "2026-07-02T00:00:00+00:00", crev=None)) + "\n"
    )
    ar.split_store(
        store,
        tmp_path / "results" / "archive",
        registry=_registry(tmp_path),
        retractions=[],
        now=now,
        dry_run=False,
    )
    assert (
        len(
            (tmp_path / "results" / "archive" / "bench-2026-09-27.jsonl")
            .read_text()
            .splitlines()
        )
        == 2
    )
    manifest = (tmp_path / "results" / "archive" / "MANIFEST.md").read_text()
    assert (
        manifest.count("# Archived rows") == 1 and manifest.count("| 2026-09-27 |") == 2
    )


def test_split_store_dry_run_changes_nothing(tmp_path: Path) -> None:
    store = tmp_path / "results" / "bench.jsonl"
    store.parent.mkdir()
    store.write_text(
        json.dumps(_line("a", "2026-07-01T00:00:00+00:00", crev=None)) + "\n"
    )
    before = store.read_text()
    result = ar.split_store(
        store,
        tmp_path / "results" / "archive",
        registry=_registry(tmp_path),
        retractions=[],
        now=datetime(2026, 9, 27, tzinfo=UTC),
        dry_run=True,
    )
    assert result.archived == 1 and store.read_text() == before
    assert not (tmp_path / "results" / "archive").exists()


def test_retract_command_appends_with_reason(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(
        app,
        [
            "retract",
            "run-x",
            "--reason",
            "harness produced the base document",
            "--by",
            "arthur",
        ],
    )
    assert r.exit_code == 0, r.output
    (rec,) = pol.load_retractions(tmp_path / "results" / "retractions.jsonl")
    assert (
        rec.id_run == "run-x"
        and rec.reason.startswith("harness")
        and rec.by == "arthur"
    )
    r = CliRunner().invoke(
        app, ["retract", "run-y", "--reason", "   ", "--by", "arthur"]
    )
    assert r.exit_code != 0


def test_archive_command_dry_run(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "bench.jsonl").write_text(
        json.dumps(_line("a", "2026-07-01T00:00:00+00:00", crev=None)) + "\n"
    )
    _registry(tmp_path)
    monkeypatch.chdir(tmp_path)
    r = CliRunner().invoke(app, ["archive", "--dry-run"])
    assert r.exit_code == 0, r.output
    assert "would archive 1" in r.output
