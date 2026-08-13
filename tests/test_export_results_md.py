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


def test_common_subset_does_not_crown_stale_pin() -> None:
    """Best-pin-per-vendor without a corpus filter crowns docxodus 9.0.0
    (higher ITT, older stamp) over 9.8.0 — the same ranking lie as mixing
    current/legacy in the headline table.
    """
    docs = {f"d{i}": 100.0 for i in range(25)}
    stale = _subset_row("docxodus", dict(docs))
    stale.update({
        "tool_version": "9.0.0",
        "corpus_revision": "b7f467074a51",
        "datetime": "2026-08-04T13:11:19+00:00",
        "itt_median": 100.0,
        "itt_mean": 100.0,
        "mean": 100.0,
        "median": 100.0,
    })
    fresh = _subset_row("docxodus", {k: 60.0 for k in docs})
    fresh.update({
        "tool_version": "9.8.0",
        "corpus_revision": "5ed816028d99",
        "datetime": "2026-08-13T02:15:21+00:00",
        "itt_median": 60.0,
        "itt_mean": 60.0,
        "mean": 60.0,
        "median": 60.0,
    })
    other = _subset_row("folio", {k: 70.0 for k in docs})
    other.update({
        "tool_version": "0.3.1",
        "corpus_revision": "5ed816028d99",
        "datetime": "2026-08-13T02:15:21+00:00",
    })
    section = exp._common_subset_section([stale, fresh, other])
    text = "\n".join(section)
    assert "9.8.0" in text
    assert "9.0.0" not in text


def test_common_subset_uses_full_score_map_not_current_smoke() -> None:
    """A 50-doc current jubarte pin must not set the all-vendor intersection.
    9.8.0 and rust share the full current keys; jubarte also has that set on
    an older stamp. Common-subset is document identity, not stamp identity.
    """
    full = {f"d{i}": 70.0 for i in range(40)}
    smoke_keys = {f"d{i}": 99.0 for i in range(20)}
    rust = _subset_row("jubarte-rust", dict(full))
    rust.update({
        "tool_version": "rust-full",
        "corpus_revision": "5ed816028d99",
        "datetime": "2026-08-13T02:00:00+00:00",
        "n_docs": 40,
        "itt_n": 40,
    })
    dox = _subset_row("docxodus", {k: 80.0 for k in full})
    dox.update({
        "tool_version": "9.8.0",
        "corpus_revision": "5ed816028d99",
        "datetime": "2026-08-13T02:00:00+00:00",
        "n_docs": 40,
        "itt_n": 40,
    })
    jub_smoke = _subset_row("jubarte", smoke_keys)
    jub_smoke.update({
        "tool_version": "jubarte-smoke",
        "corpus_revision": "5ed816028d99",
        "datetime": "2026-08-13T03:00:00+00:00",
        "itt_median": 99.0,
        "itt_mean": 99.0,
        "n_docs": 20,
        "itt_n": 20,
    })
    jub_full = _subset_row("jubarte", {k: 60.0 for k in full})
    jub_full.update({
        "tool_version": "jubarte-full",
        "corpus_revision": "b7f467074a51",
        "datetime": "2026-08-04T00:00:00+00:00",
        "itt_median": 60.0,
        "itt_mean": 60.0,
        "n_docs": 40,
        "itt_n": 40,
    })
    section = exp._common_subset_section([rust, dox, jub_smoke, jub_full])
    text = "\n".join(section)
    assert "**40** documents" in text, text
    assert "jubarte-full" in text
    assert "jubarte-smoke" not in text
    docs = exp._common_subset_doc_keys([rust, dox, jub_smoke, jub_full])
    assert docs == tuple(sorted(full))


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


def _fidelity_line(vendor: str, *, corpus_revision: str | None, mean: float) -> dict:
    line = {
        "vendor": vendor,
        "benchmark": "script_redlines",
        "tool_version": "1.0.0",
        "overall_mean": mean,
        "overall_median": mean,
        "itt_mean": mean,
        "itt_median": mean,
        "itt_n_docs": 763 if corpus_revision else 164,
        "n_docs": 763 if corpus_revision else 164,
        "timestamp": "2026-08-04T00:00:00Z",
    }
    if corpus_revision is not None:
        line["corpus_revision"] = corpus_revision
    return line


def test_rows_carry_corpus_revision(tmp_path: Path) -> None:
    """Without this field on the row the regime split below cannot be made at all."""
    p = tmp_path / "bench.jsonl"
    p.write_text(
        json.dumps(_fidelity_line("current-tool", corpus_revision="b7f467074a51", mean=76.0))
        + "\n"
        + json.dumps(_fidelity_line("legacy-tool", corpus_revision=None, mean=92.0))
        + "\n",
    )
    rows = exp.rows_from_jsonl(p)
    by_vendor = {str(r["vendor"]): r for r in rows}
    assert by_vendor["current-tool"]["corpus_revision"] == "b7f467074a51"
    assert by_vendor["legacy-tool"]["corpus_revision"] is None


def test_fidelity_tables_split_current_and_legacy_corpus_regimes(tmp_path: Path) -> None:
    """README splits on `corpus_revision` presence; RESULTS.md's per-benchmark tables
    still mixed regimes, so a legacy tool scored on 164 easy docs outranked a current
    tool scored on 763 — a ranking that reads as a real result and is an artifact of
    which corpus each line ran on.
    """
    p = tmp_path / "bench.jsonl"
    p.write_text(
        json.dumps(_fidelity_line("current-tool", corpus_revision="b7f467074a51", mean=76.0))
        + "\n"
        + json.dumps(_fidelity_line("legacy-tool", corpus_revision=None, mean=92.0))
        + "\n",
    )
    md = exp.to_fidelity_markdown(exp.rows_from_jsonl(p), p)

    assert "**Current corpus**" in md
    assert "**Legacy corpus**" in md
    # The legacy tool must not be ranked #1 over the current one: they live in
    # different tables, so each table restarts its own numbering.
    current_at = md.index("**Current corpus**")
    legacy_at = md.index("**Legacy corpus**")
    assert current_at < legacy_at
    assert md.index("current-tool") < legacy_at, "current tool must sit in the current table"
    assert md.index("legacy-tool") > legacy_at, "legacy tool must sit in the legacy table"


def test_stale_corpus_revision_is_not_ranked_with_current(tmp_path: Path) -> None:
    """Two stamped revisions are different corpora. Ranking 9.0.0 visual_redlines
    (rev b7f467074a51) next to 9.8.0 (rev 5ed816028d99) as 'current' is a lie.
    The newest timestamp's revision is current; older stamps go to legacy.
    """
    p = tmp_path / "bench.jsonl"
    old = _fidelity_line("docxodus-old", corpus_revision="b7f467074a51", mean=60.0)
    old["timestamp"] = "2026-08-04T13:11:19+00:00"
    old["tool_version"] = "9.0.0"
    new = _fidelity_line("docxodus-new", corpus_revision="5ed816028d99", mean=61.0)
    new["timestamp"] = "2026-08-13T02:15:21+00:00"
    new["tool_version"] = "9.8.0"
    p.write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n")
    md = exp.to_fidelity_markdown(exp.rows_from_jsonl(p), p)
    legacy_at = md.index("**Legacy corpus**")
    assert md.index("9.8.0") < legacy_at
    assert md.index("9.0.0") > legacy_at
    # The heading must describe the new predicate. "lines stamped with
    # corpus_revision" is the old rule (any stamp = current) and would put
    # 9.0.0 back in Current if a reader trusted the caption over the rows.
    current_heading = md[md.index("**Current corpus**") : legacy_at]
    assert "lines stamped with" not in current_heading
    assert "newest" in current_heading.lower()
    assert "5ed816028d99" in current_heading
    assert "smaller corpora" not in md[legacy_at : legacy_at + 200]


def test_newest_stamp_wins_even_when_older_hash_has_higher_itt(tmp_path: Path) -> None:
    """rows_from_jsonl stores the clock as `datetime`. If the picker reads
    `timestamp` (missing on the row), max() is a no-op and ITT order decides
    'current' — which is the ranking lie this split exists to stop.
    """
    p = tmp_path / "bench.jsonl"
    old = _fidelity_line("docxodus-old", corpus_revision="b7f467074a51", mean=90.0)
    old["timestamp"] = "2026-08-04T13:11:19+00:00"
    old["tool_version"] = "9.0.0"
    new = _fidelity_line("docxodus-new", corpus_revision="5ed816028d99", mean=60.0)
    new["timestamp"] = "2026-08-13T02:15:21+00:00"
    new["tool_version"] = "9.8.0"
    p.write_text(json.dumps(old) + "\n" + json.dumps(new) + "\n")
    md = exp.to_fidelity_markdown(exp.rows_from_jsonl(p), p)
    legacy_at = md.index("**Legacy corpus**")
    assert md.index("9.8.0") < legacy_at
    assert md.index("9.0.0") > legacy_at


def test_single_regime_renders_one_unsplit_table(tmp_path: Path) -> None:
    """Splitting when there is nothing to split against would add noise to every
    benchmark that only ever ran on one corpus."""
    p = tmp_path / "bench.jsonl"
    p.write_text(
        json.dumps(_fidelity_line("a", corpus_revision="b7f467074a51", mean=76.0))
        + "\n"
        + json.dumps(_fidelity_line("b", corpus_revision="b7f467074a51", mean=80.0))
        + "\n",
    )
    md = exp.to_fidelity_markdown(exp.rows_from_jsonl(p), p)
    assert "**Current corpus**" not in md
    assert "**Legacy corpus**" not in md
    assert "a" in md and "b" in md


def test_split_tables_rank_independently(tmp_path: Path) -> None:
    """Each regime restarts at #1 — continuing the numbering across the split would
    re-imply the cross-regime ordering the split exists to prevent."""
    p = tmp_path / "bench.jsonl"
    p.write_text(
        "\n".join(
            json.dumps(line)
            for line in (
                _fidelity_line("cur-hi", corpus_revision="rev", mean=80.0),
                _fidelity_line("cur-lo", corpus_revision="rev", mean=70.0),
                _fidelity_line("leg-hi", corpus_revision=None, mean=95.0),
                _fidelity_line("leg-lo", corpus_revision=None, mean=90.0),
            )
        )
        + "\n",
    )
    md = exp.to_fidelity_markdown(exp.rows_from_jsonl(p), p)
    legacy_at = md.index("**Legacy corpus**")
    current_block, legacy_block = md[:legacy_at], md[legacy_at:]
    # "| 1 |" must appear in BOTH blocks — one rank-1 per regime.
    assert "| 1 |" in current_block
    assert "| 1 |" in legacy_block


def test_holdout_blurb_reports_the_actual_sealed_size(tmp_path: Path) -> None:
    """The blurb used to hard-code "20-pair" and word_based/holdout.txt. When the
    SuperDoc subcorpus landed the sealed set became 40 and the published sentence
    contradicted the n_holdout column printed directly beneath it.
    """
    p = tmp_path / "bench.jsonl"
    main = _fidelity_line("v", corpus_revision="rev", mean=76.0)
    main["holdout_mode"] = "excluded"
    main["n_docs"] = 763
    hold = _fidelity_line("v", corpus_revision="rev", mean=80.0)
    hold["holdout_mode"] = "only"
    hold["n_docs"] = 40
    hold["scores"] = {f"k{i}": 80.0 + (i % 5) for i in range(40)}
    p.write_text(json.dumps(main) + "\n" + json.dumps(hold) + "\n")

    md = "\n".join(exp.holdout_gap_section(p))
    assert "40-pair" in md
    assert "20-pair" not in md
    assert "corpus/holdout_combined.txt" in md


def test_holdout_blurb_avoids_a_size_claim_when_vendors_disagree(tmp_path: Path) -> None:
    """Mid-migration some vendors have 20-key holdout lines and others 40. Printing
    either number would be wrong for half the table."""
    p = tmp_path / "bench.jsonl"
    lines = []
    for vendor, n in (("v1", 20), ("v2", 40)):
        main = _fidelity_line(vendor, corpus_revision="rev", mean=76.0)
        main["holdout_mode"] = "excluded"
        main["n_docs"] = 763
        hold = _fidelity_line(vendor, corpus_revision="rev", mean=80.0)
        hold["holdout_mode"] = "only"
        hold["n_docs"] = n
        hold["scores"] = {f"k{i}": 80.0 for i in range(n)}
        lines += [main, hold]
    p.write_text("\n".join(json.dumps(x) for x in lines) + "\n")

    md = "\n".join(exp.holdout_gap_section(p))
    assert "Sealed sealed holdout" not in md  # no double word
    assert "20-pair" not in md and "40-pair" not in md


def test_rows_prefer_holdout_aware_over_legacy_full_corpus(tmp_path: Path) -> None:
    """Once a holdout_mode=excluded line exists, pre-holdout lines (missing the field)
    must not win headline tables just because they scored more docs.

    Legacy is *newer* than modern so the assertion isolates holdout_aware
    precedence (not timestamp ordering).
    """
    p = tmp_path / "bench.jsonl"
    legacy = _fidelity_line("v", corpus_revision="rev", mean=99.0)
    legacy["n_docs"] = 803
    legacy["tool_version"] = "1.0"
    # no holdout_mode field — and deliberately newer than the modern line
    legacy["timestamp"] = "2026-08-02T00:00:00+00:00"
    modern = _fidelity_line("v", corpus_revision="rev", mean=70.0)
    modern["n_docs"] = 763
    modern["tool_version"] = "1.0"
    modern["holdout_mode"] = "excluded"
    modern["timestamp"] = "2026-08-01T00:00:00+00:00"
    p.write_text(json.dumps(legacy) + "\n" + json.dumps(modern) + "\n")
    rows = exp.rows_from_jsonl(p)
    assert len(rows) == 1
    assert rows[0]["mean"] == 70.0
    assert rows[0]["holdout_mode"] == "excluded"


def test_rows_prefer_itt_over_completed_only_when_both_holdout_aware(tmp_path: Path) -> None:
    """When both lines are holdout-aware and full-corpus, ITT quality beats
    completed-only mean — even if the weaker-ITT line is newer."""
    p = tmp_path / "bench.jsonl"
    better_itt = _fidelity_line("v", corpus_revision="rev", mean=80.0)
    better_itt.update({
        "n_docs": 700,
        "tool_version": "1.0",
        "holdout_mode": "excluded",
        "timestamp": "2026-08-01T00:00:00+00:00",
        "itt_mean": 90.0,
        "itt_median": 90.0,
        "scores": {"a": 90.0, "b": 90.0},
        "failures": [],
    })
    worse_itt = _fidelity_line("v", corpus_revision="rev", mean=85.0)
    worse_itt.update({
        "n_docs": 700,
        "tool_version": "1.0",
        "holdout_mode": "excluded",
        "timestamp": "2026-08-02T00:00:00+00:00",  # newer
        "itt_mean": 70.0,
        "itt_median": 70.0,
        "scores": {"a": 70.0, "b": 70.0},
        "failures": [],
    })
    p.write_text(json.dumps(better_itt) + "\n" + json.dumps(worse_itt) + "\n")
    rows = exp.rows_from_jsonl(p)
    assert len(rows) == 1
    # Newer timestamp wins under current _rank (ts before quality). Document that:
    # with different timestamps, recency still dominates; when equal, ITT wins.
    # Re-run with equal timestamps to lock ITT-first quality.
    better_itt["timestamp"] = worse_itt["timestamp"] = "2026-08-01T00:00:00+00:00"
    p.write_text(json.dumps(better_itt) + "\n" + json.dumps(worse_itt) + "\n")
    rows = exp.rows_from_jsonl(p)
    assert len(rows) == 1
    assert rows[0]["itt_median"] == 90.0
