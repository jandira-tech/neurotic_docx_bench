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


# ── Intent-to-treat (PR2) ────────────────────────────────────────────────────


def test_itt_stats_prefers_emitted_fields() -> None:
    mean, median, n, n_fail = exp._itt_stats(
        {
            "itt_mean": 40.0,
            "itt_median": 35.0,
            "itt_n_docs": 5,
            "scores": {"a": 100.0},
            "failures": [{"doc": "b"}],
        }
    )
    assert (mean, median, n, n_fail) == (40.0, 35.0, 5, 1)


def test_itt_stats_derives_from_scores_and_failures() -> None:
    mean, median, n, n_fail = exp._itt_stats(
        {
            "scores": {"a": 100.0, "b": 50.0},
            "failures": [
                {"doc": "c"},
                {"doc": "c"},  # deduped
                {"doc": "a"},  # already scored — keeps its score
            ],
        }
    )
    assert n == 3
    assert median == 50.0
    assert mean == 50.0
    assert n_fail == 3


def test_itt_stats_legacy_line_without_scores() -> None:
    mean, median, n, n_fail = exp._itt_stats({"n_failures": 7})
    assert (mean, median, n) == (None, None, None)
    assert n_fail == 7


def test_fidelity_sort_ranks_itt_below_completed_only() -> None:
    clean = {
        "vendor": "clean", "tool_version": "1", "benchmark": "script_redlines",
        "mean": 80.0, "median": 80.0, "n_docs": 10,
        "itt_mean": 80.0, "itt_median": 80.0, "itt_n": 10, "n_failures": 0,
    }
    crashy = {
        "vendor": "crashy", "tool_version": "1", "benchmark": "script_redlines",
        "mean": 90.0, "median": 90.0, "n_docs": 5,
        "itt_mean": 45.0, "itt_median": 40.0, "itt_n": 10, "n_failures": 5,
    }
    ranked = sorted([crashy, clean], key=exp._fidelity_sort_key)
    assert [r["vendor"] for r in ranked] == ["clean", "crashy"]


def _subset_row(vendor: str, scores: dict[str, float]) -> dict[str, object]:
    return {
        "vendor": vendor, "tool_version": "1", "benchmark": "script_redlines",
        "datetime": "t", "mean": 50.0, "median": 50.0, "n_docs": len(scores),
        "itt_mean": 50.0, "itt_median": 50.0, "itt_n": len(scores),
        "n_failures": 0, "scores": scores, "render": "soffice",
        "exact_100": 0, "at_least_90": 0, "below_50": 0,
    }


def test_common_subset_section_ranks_on_shared_docs() -> None:
    docs = [f"d{i}" for i in range(25)]
    a = _subset_row("alpha", {d: 90.0 for d in docs} | {"only_a": 10.0})
    b = _subset_row("beta", {d: 60.0 for d in docs} | {"only_b": 100.0})
    section = exp._common_subset_section([a, b])
    text = "\n".join(section)
    assert "Common-subset ranking" in text
    assert "**25** documents" in text
    alpha_line = next(line for line in section if "alpha" in line)
    assert alpha_line.startswith("| 1 ")
    assert "90.00" in alpha_line


def test_common_subset_section_skips_small_intersections() -> None:
    a = _subset_row("alpha", {"d1": 90.0})
    b = _subset_row("beta", {"d1": 60.0})
    assert exp._common_subset_section([a, b]) == []


def test_to_markdown_renders_itt_columns() -> None:
    row = _subset_row("alpha", {"d1": 80.0, "d2": 90.0})
    md = exp.to_fidelity_markdown([row], Path("results/bench.jsonl"))
    assert "itt_median" in md
    assert "failures" in md


def test_paired_stats_section_win_loss_and_p() -> None:
    docs = {f"d{i}": 80.0 + i * 0.1 for i in range(30)}
    a = _subset_row("alpha", {k: v + 5.0 for k, v in docs.items()})
    b = _subset_row("beta", dict(docs))
    section = exp._paired_stats_section([a, b])
    text = "\n".join(section)
    assert "Paired comparisons" in text
    row_line = next(line for line in section if "| alpha | beta |" in line)
    assert "| 30 |" in row_line
    assert "30/0/0" in row_line
    assert "+5.00" in row_line


def test_paired_stats_skips_small_overlap() -> None:
    a = _subset_row("alpha", {"d1": 90.0})
    b = _subset_row("beta", {"d1": 60.0})
    assert exp._paired_stats_section([a, b]) == []


def test_lens_health_section_lists_disagreeing_vendors() -> None:
    rows = [
        {
            "vendor": "alpha", "tool_version": "1.0", "benchmark": "script_redlines",
            "n_lens_disagree": 3, "lens_disagree_rate": 0.015,
        },
        {
            "vendor": "beta", "tool_version": "2.0", "benchmark": "script_redlines",
            "n_lens_disagree": 0, "lens_disagree_rate": 0.0,
        },
        {
            "vendor": "gamma", "tool_version": "1.0", "benchmark": "visual_redlines",
            "n_lens_disagree": 9, "lens_disagree_rate": 0.5,
        },
    ]
    section = exp._lens_health_section(rows)
    text = "\n".join(section)
    assert "Lens health" in text
    assert "alpha" in text
    assert "3 doc(s)" in text
    assert "1.5%" in text
    assert "beta" not in text  # zero disagreements → no alarm line
    assert "gamma" not in text  # other benchmarks excluded


def test_lens_health_section_absent_when_clean() -> None:
    rows = [
        {"vendor": "alpha", "tool_version": "1.0", "benchmark": "script_redlines",
         "n_lens_disagree": 0, "lens_disagree_rate": 0.0},
        {"vendor": "old", "tool_version": "0.9", "benchmark": "script_redlines"},
    ]
    assert exp._lens_health_section(rows) == []


def test_dedup_keeps_lens_alarm_from_shadowed_rerun(tmp_path: Path) -> None:
    # _rank prefers the newest line (within the full-corpus bucket) among same
    # (vendor, benchmark, version) reruns — which may be a clean/pre-lens line.
    # The alarm must be max-over-reruns: a losing rerun that surfaced
    # disagreements must not be silenced by the winner.
    import json as _json

    line_common = {
        "vendor": "alpha", "benchmark": "script_redlines", "tool_version": "1.0",
        "n_docs": 10, "exact_100": 0, "at_least_90": 5, "below_50": 0,
        "min": 50.0, "max": 99.0, "std": 1.0,
    }
    with_alarm = {**line_common, "overall_mean": 80.0, "overall_median": 81.0,
                  "timestamp": "2026-08-01T00:00:00+00:00",
                  "n_lens_disagree": 4, "lens_disagree_rate": 0.4}
    shadowing = {**line_common, "overall_mean": 90.0, "overall_median": 91.0,
                 "timestamp": "2026-08-02T00:00:00+00:00"}
    path = tmp_path / "bench.jsonl"
    path.write_text(_json.dumps(with_alarm) + "\n" + _json.dumps(shadowing) + "\n")
    rows = exp.rows_from_jsonl(path)
    assert len(rows) == 1
    assert rows[0]["mean"] == 90.0  # ranking uses the newest line
    assert rows[0]["n_lens_disagree"] == 4  # but the alarm survives
    assert rows[0]["lens_disagree_rate"] == 0.4


def test_carry_foreign_marker_blocks(tmp_path: Path) -> None:
    """A wholesale rewrite must not destroy marker-delimited sections owned by
    sibling generators (e.g. the dual-path report's DUAL_PATH_QUALITY block)."""
    out = tmp_path / "RESULTS.md"
    block = (
        "<!-- DUAL_PATH_QUALITY:BEGIN -->\n"
        "## dual-path table\n"
        "| a | b |\n"
        "<!-- DUAL_PATH_QUALITY:END -->"
    )
    out.write_text(f"# old content\n\n{block}\n", encoding="utf-8")
    merged = exp._carry_foreign_marker_blocks(out, "# new export\n")
    assert block in merged
    assert merged.startswith("# new export")
    # A block the new markdown already contains is not duplicated.
    merged2 = exp._carry_foreign_marker_blocks(out, f"# new export\n\n{block}\n")
    assert merged2.count("DUAL_PATH_QUALITY:BEGIN") == 1
    # No existing file → passthrough.
    assert exp._carry_foreign_marker_blocks(tmp_path / "missing.md", "x") == "x"
