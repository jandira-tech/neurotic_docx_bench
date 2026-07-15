"""export-results-md.py — fidelity + speed sections for RESULTS.md."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_MOD_PATH = ROOT / "scripts" / "export-results-md.py"
_spec = importlib.util.spec_from_file_location("export_results_md", _MOD_PATH)
assert _spec and _spec.loader
exp = importlib.util.module_from_spec(_spec)
sys.modules["export_results_md"] = exp
_spec.loader.exec_module(exp)


def test_speed_rows_prefer_larger_n_over_smoke(tmp_path: Path) -> None:
    p = tmp_path / "speed.jsonl"
    lines = [
        {
            "schema": 1,
            "kind": "speed_redlines",
            "tool": "docxodus-csharp-inproc",
            "unit": "ms_per_redline",
            "n": 30,
            "median": 6.8,
            "mean": 10.0,
            "pair_count": 30,
            "fixture_count": 30,
            "run_ts": "2026-07-15T00:00:00Z",
        },
        {
            "schema": 1,
            "kind": "speed_redlines",
            "tool": "docxodus-csharp-inproc",
            "unit": "ms_per_redline",
            "n": 4880,
            "median": 9.4,
            "mean": 29.9,
            "pair_count": 5000,
            "fixture_count": 1000,
            "run_ts": "2026-07-15T12:00:00Z",
        },
    ]
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    rows = exp.speed_rows_from_jsonl(p)
    assert len(rows) == 1
    assert rows[0]["n"] == 4880
    assert rows[0]["median"] == 9.4


def test_speed_redlines_drops_n_under_10(tmp_path: Path) -> None:
    p = tmp_path / "speed.jsonl"
    p.write_text(
        json.dumps(
            {
                "kind": "speed_redlines",
                "tool": "tiny",
                "unit": "ms_per_redline",
                "n": 5,
                "median": 1.0,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert exp.speed_rows_from_jsonl(p) == []


def test_merge_prefers_summary_with_more_samples(tmp_path: Path) -> None:
    a = [
        {
            "kind": "speed_redlines",
            "tool": "jubarte-rust",
            "unit": "ms_per_redline",
            "n": 50,
            "median": 6.6,
            "run_ts": "a",
        }
    ]
    b = [
        {
            "kind": "speed_redlines",
            "tool": "jubarte-rust",
            "unit": "ms_per_redline",
            "n": 1000,
            "median": 11.1,
            "run_ts": "b",
        }
    ]
    merged = exp.merge_speed_rows(a, b)
    assert len(merged) == 1
    assert merged[0]["n"] == 1000


def test_to_markdown_includes_speed_section(tmp_path: Path) -> None:
    fidelity = [
        {
            "vendor": "jubarte-rust",
            "tool_version": "x",
            "datetime": "t",
            "benchmark": "script_redlines",
            "mean": 80.0,
            "median": 85.0,
            "n_docs": 100,
            "exact_100": 10,
            "at_least_90": 40,
            "below_50": 5,
            "render": "soffice",
        }
    ]
    speed = [
        {
            "kind": "speed_redlines",
            "tool": "jubarte-rust-inproc",
            "runtime": "rust",
            "unit": "ms_per_redline",
            "n": 5000,
            "median": 4.5,
            "mean": 8.0,
            "p95": 20.0,
            "p99": 40.0,
            "throughput_per_s": 200.0,
            "failures": 0,
            "fixture_count": 1000,
            "pair_count": 5000,
            "profile_tool": "samply",
            "run_ts": "t",
        },
        {
            "kind": "speed",
            "tool": "docxodus",
            "runtime": "node",
            "unit": "ms_per_redline",
            "n": 90,
            "median": 75.0,
            "mean": 200.0,
            "p95": 1000.0,
            "p99": 2000.0,
            "throughput_per_s": 4.0,
            "failures": 0,
            "run_ts": "t",
        },
    ]
    md = exp.to_markdown(
        fidelity,
        Path("results/bench.jsonl"),
        speed_rows=speed,
        speed_source=Path("results/speed.jsonl"),
    )
    assert "## Redline generation speed" in md
    assert "### Microbench" in md
    assert "### Large-N `speed_redlines`" in md
    assert "jubarte-rust-inproc" in md
    assert "docxodus" in md
    assert "script_redlines" in md
    assert "Methodology notes (fidelity)" in md


def test_main_writes_speed_when_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bench = tmp_path / "bench.jsonl"
    speed = tmp_path / "speed.jsonl"
    out = tmp_path / "OUT.md"
    bench.write_text(
        json.dumps(
            {
                "vendor": "v",
                "benchmark": "script_redlines",
                "tool_version": "1",
                "overall_mean": 50,
                "overall_median": 50,
                "n_docs": 10,
                "timestamp": "t",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    speed.write_text(
        json.dumps(
            {
                "kind": "speed_redlines",
                "tool": "jubarte-rust-inproc",
                "unit": "ms_per_redline",
                "n": 100,
                "median": 5.0,
                "mean": 6.0,
                "throughput_per_s": 100,
                "failures": 0,
                "fixture_count": 50,
                "pair_count": 100,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    # Point summary scan at empty tree under tmp via chdir.
    monkeypatch.chdir(tmp_path)
    # Patch _repo_root so summary scan is under tmp (no redline_speed_bench dir).
    monkeypatch.setattr(exp, "_repo_root", lambda: tmp_path)
    rc = exp.main(
        [
            "--input",
            str(bench),
            "--speed-input",
            str(speed),
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    text = out.read_text(encoding="utf-8")
    assert "jubarte-rust-inproc" in text
    assert "speed_redlines" in text
