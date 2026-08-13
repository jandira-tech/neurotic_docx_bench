#!/usr/bin/env python3
"""Export fidelity + speed aggregates into RESULTS.md.

Fidelity: one row per **(vendor, benchmark, tool_version)** from
``results/bench.jsonl`` so different pins of the same engine (e.g. docxodus
6.4.0 vs 7.0.0) appear side-by-side.

Speed: from ``results/speed.jsonl`` (and optional
``results/redline_speed_bench/**/summary.json``):

- ``kind: speed`` — classic microbench (pairs × reps, usually in-memory Node)
- ``kind: speed_redlines`` / ``redline_speed_bench`` — large-N / CLI / warm
  workers (docxodus-csharp[-inproc], jubarte-rust[-inproc], WASM, …)

When the same key appears more than once, keeps the newest full-corpus re-run
(recency wins within the full-corpus bucket; see rankers).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _format_num(value: object, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
        return text if text else "0"
    if isinstance(value, int):
        return str(value)
    return str(value)


def _escape_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _norm_version(value: object) -> str:
    """Stable empty version label so missing versions don't collide with a real pin."""
    if value is None:
        return "—"
    text = str(value).strip()
    return text if text else "—"


def _render_from_line(data: dict) -> str:
    """Best-effort render backend from environment_config.runs[0].render."""
    env = data.get("environment_config")
    if not isinstance(env, dict):
        return ""
    runs = env.get("runs")
    if not isinstance(runs, list) or not runs:
        return ""
    first = runs[0]
    if not isinstance(first, dict):
        return ""
    return str(first.get("render") or "")


def _rank(row: dict[str, object]) -> tuple:
    """Pick the best re-run of the *same* (vendor, benchmark, version).

    Prefer the render path that matches the benchmark family (playwright for
    visual_*, soffice for script/accepted/roundtrip), then holdout-aware lines
    (``holdout_mode`` present) over pre-holdout legacy lines, then the
    full-corpus bucket (n_docs > 100, consistent with the smoke-run filter),
    then the NEWER timestamp. Raw n_docs must not dominate recency: a stale
    403-doc pre-holdout line would otherwise permanently beat every newer
    383-doc post-holdout line for an unchanged tool_version. Quality
    tiebreakers use ITT median/mean when present (tables sort by ITT), falling
    back to completed-only stats for legacy lines.
    """
    benchmark = str(row.get("benchmark") or "")
    render = str(row.get("render") or "")
    if benchmark.startswith("visual"):
        render_fit = 1 if render == "playwright" else 0
    else:
        # script_redlines / accepted_changes / roundtrip come from soffice runs.
        # Playwright-only harness runs sometimes also emit a bogus script_redlines
        # line — deprioritize those.
        render_fit = 0 if render == "playwright" else 1

    # Prefer holdout-stamped main lines over pre-holdout legacy (missing field).
    holdout_aware = 1 if row.get("holdout_mode") not in (None, "") else 0

    n = row.get("n_docs")
    ts = row.get("datetime") or ""
    n_v = int(n) if isinstance(n, (int, float)) else -1
    full_bucket = 1 if n_v > 100 else 0

    # ITT-first quality so rerun selection matches table sort semantics.
    med = row.get("itt_median")
    if not isinstance(med, (int, float)):
        med = row.get("median")
    mean = row.get("itt_mean")
    if not isinstance(mean, (int, float)):
        mean = row.get("mean")
    med_v = float(med) if isinstance(med, (int, float)) else float("-inf")
    m_v = float(mean) if isinstance(mean, (int, float)) else float("-inf")
    return (render_fit, holdout_aware, full_bucket, str(ts), med_v, m_v)


def _itt_stats(
    data: dict[str, object],
) -> tuple[float | None, float | None, int | None, int | None]:
    """(itt_mean, itt_median, itt_n, n_failures) for a JSONL line.

    Prefers the server-emitted ``itt_*`` fields (new lines); otherwise derives them
    from the line's own ``scores`` map + ``failures`` array (one 0.0 per unique failed
    doc that did not also score). Lines without per-doc scores return ``None`` stats —
    the caller falls back to completed-only values for sorting.
    """
    failures = data.get("failures")
    if isinstance(failures, list):
        n_failures: int | None = len(failures)
    else:
        raw = data.get("n_failures")
        n_failures = int(raw) if isinstance(raw, (int, float)) else None
    if isinstance(data.get("itt_median"), (int, float)):
        itt_n = data.get("itt_n_docs")
        return (
            float(data["itt_mean"]) if isinstance(data.get("itt_mean"), (int, float)) else None,
            float(data["itt_median"]),  # type: ignore[arg-type]
            int(itt_n) if isinstance(itt_n, (int, float)) else None,
            n_failures,
        )
    scores = data.get("scores")
    if isinstance(scores, dict) and scores:
        fail_docs: set[str] = set()
        if isinstance(failures, list):
            fail_docs = {str(f.get("doc", "")) for f in failures if isinstance(f, dict)}
        values = [float(v) for v in scores.values()]
        values += [0.0] * len(fail_docs - set(scores))
        return (
            round(statistics.mean(values), 4),
            round(statistics.median(values), 4),
            len(values),
            n_failures,
        )
    return None, None, None, n_failures


def rows_from_jsonl(path: Path) -> list[dict[str, object]]:
    # Key includes tool_version so 6.4.0 and 7.0.0 of the same vendor×benchmark
    # both survive (otherwise only one "docxodus / script_redlines" row would remain).
    best: dict[tuple[str, str, str], dict[str, object]] = {}
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"warning: skip line {line_no}: {exc}", file=sys.stderr)
                continue

            # Sealed-holdout lines never enter the headline tables — they are
            # scored on a 20-doc subset and reported by the "Holdout gap" section.
            if data.get("holdout_mode") == "only":
                continue

            # Schema v4: vendor/benchmark; legacy v2/v3: tool/stage.
            vendor = str(data.get("vendor") or data.get("tool") or "")
            benchmark = str(data.get("benchmark") or data.get("stage") or "")
            version = _norm_version(data.get("tool_version"))
            n_docs = data.get("n_docs")
            render = _render_from_line(data)

            # Drop tiny docxodus smoke / partial runs (e.g. n=2, n=21) so rankings
            # compare real corpus sizes; full 6.4.x and 7.x lines both pass.
            if vendor == "docxodus" and isinstance(n_docs, (int, float)) and int(n_docs) <= 100:
                continue

            itt_mean, itt_median, itt_n, n_failures = _itt_stats(data)
            holdout_mode = data.get("holdout_mode")
            row: dict[str, object] = {
                "vendor": vendor,
                "datetime": data.get("timestamp") or data.get("run_ts") or "",
                "benchmark": benchmark,
                "mean": data.get("overall_mean"),
                "median": data.get("overall_median"),
                "n_docs": n_docs,
                "exact_100": data.get("exact_100"),
                "at_least_90": data.get("at_least_90"),
                "below_50": data.get("below_50"),
                "min": data.get("min"),
                "max": data.get("max"),
                "std": data.get("std"),
                "tool_version": version,
                "render": render,
                "holdout_mode": holdout_mode,
                "itt_mean": itt_mean,
                "itt_median": itt_median,
                "itt_n": itt_n,
                "n_failures": n_failures,
                "skill_median": data.get("skill_median"),
                "n_lens_disagree": data.get("n_lens_disagree"),
                "lens_disagree_rate": data.get("lens_disagree_rate"),
                "scores": data.get("scores") if isinstance(data.get("scores"), dict) else None,
                # Regime marker: lines stamped with corpus_revision ran on the current
                # corpus, older lines on smaller ones. Their means are not comparable,
                # so to_fidelity_markdown ranks them in separate tables (same predicate
                # as buildFidelityTable in scripts/update-readme-ranking.ts).
                "corpus_revision": (
                    None if data.get("corpus_revision") is None else str(data["corpus_revision"])
                ),
            }
            key = (vendor, benchmark, version)
            cur = best.get(key)
            if cur is None:
                best[key] = row
            else:
                winner = row if _rank(row) > _rank(cur) else cur
                loser = cur if winner is row else row
                # The lens-health alarm is max-over-reruns: _rank prefers the
                # higher-mean line, which is exactly the rerun least likely to
                # carry the alarm — a pre-lens (or clean) line must not shadow a
                # rerun that surfaced disagreements.
                wn, ln = winner.get("n_lens_disagree"), loser.get("n_lens_disagree")
                if isinstance(ln, (int, float)) and (
                    not isinstance(wn, (int, float)) or ln > wn
                ):
                    winner["n_lens_disagree"] = ln
                    winner["lens_disagree_rate"] = loser.get("lens_disagree_rate")
                best[key] = winner

    return sorted(
        best.values(),
        key=lambda r: (
            str(r["vendor"]),
            str(r["tool_version"]),
            str(r["benchmark"]),
        ),
    )


BENCHMARK_ORDER = (
    "script_redlines",
    "accepted_changes",
    "roundtrip",
    "visual_rendering",
    "visual_redlines",
    "visual_accepted_changes",
)

BENCHMARK_LABELS = {
    "script_redlines": "script_redlines (LibreOffice render vs Word oracle)",
    "accepted_changes": "accepted_changes",
    "roundtrip": "roundtrip (self-diff → pdf_source)",
    "visual_rendering": "visual_rendering (Playwright viewer)",
    "visual_redlines": "visual_redlines (Playwright)",
    "visual_accepted_changes": "visual_accepted_changes (Playwright)",
}

SPEED_KINDS_GENERATION = frozenset({"speed", "speed_redlines", "redline_speed_bench"})
SPEED_UNIT_GENERATION = "ms_per_redline"
SPEED_UNIT_RENDER = "ms_per_render"


def _num_or(r: dict[str, object], key: str, fallback_key: str) -> float:
    """Sort helper: the row's ITT stat, falling back to the completed-only stat for
    legacy rows without per-doc data (equivalent to assuming zero failures)."""
    v = r.get(key)
    if isinstance(v, (int, float)):
        return float(v)
    fv = r.get(fallback_key)
    return float(fv) if isinstance(fv, (int, float)) else float("-inf")


def _fidelity_sort_key(r: dict[str, object]) -> tuple:
    """Intent-to-treat ranking: itt_median, then itt_mean (legacy rows fall back to
    their completed-only values), then corpus size, then stable name/version order."""
    return (
        -_num_or(r, "itt_median", "median"),
        -_num_or(r, "itt_mean", "mean"),
        -(int(r["n_docs"]) if isinstance(r["n_docs"], (int, float)) else -1),
        str(r["vendor"]),
        str(r["tool_version"]),
    )


def _common_subset_section(rows: list[dict[str, object]]) -> list[str]:
    """Paired ranking on the docs EVERY script_redlines vendor completed.

    Aggregate means over different doc subsets are not comparable (each vendor fails
    on different docs); this table re-ranks vendors on the intersection of their
    per-doc score maps. One row per vendor: its best pin by the ITT sort. Skipped
    when fewer than two vendors carry per-doc scores or the intersection is < 20 docs.
    """
    candidates = [
        r for r in rows
        if str(r["benchmark"]) == "script_redlines" and isinstance(r.get("scores"), dict) and r["scores"]
    ]
    best_per_vendor: dict[str, dict[str, object]] = {}
    for r in candidates:
        vendor = str(r["vendor"])
        cur = best_per_vendor.get(vendor)
        if cur is None or _fidelity_sort_key(r) < _fidelity_sort_key(cur):
            best_per_vendor[vendor] = r
    if len(best_per_vendor) < 2:
        return []
    doc_sets = [set(r["scores"]) for r in best_per_vendor.values()]  # type: ignore[arg-type]
    common = set.intersection(*doc_sets)
    if len(common) < 20:
        return []
    table_rows = []
    ranked = sorted(
        best_per_vendor.values(),
        key=lambda r: -statistics.median(float(r["scores"][d]) for d in common),  # type: ignore[index]
    )
    for rank, r in enumerate(ranked, start=1):
        subset = [float(r["scores"][d]) for d in common]  # type: ignore[index]
        table_rows.append([
            str(rank),
            _escape_cell(r["vendor"]),
            _escape_cell(r.get("tool_version") or "—"),
            _escape_cell(f"{statistics.median(subset):.2f}"),
            _escape_cell(f"{statistics.mean(subset):.2f}"),
        ])
    return [
        "### Common-subset ranking (script_redlines)",
        "",
        f"Paired comparison on the **{len(common)}** documents every vendor below "
        "completed (best pin per vendor). Unlike the aggregate tables, these medians "
        "are computed on the SAME documents for every vendor.",
        "",
        *_table(["#", "vendor", "version", "median", "mean"], table_rows),
        "",
    ]


def _lens_health_section(rows: list[dict[str, object]]) -> list[str]:
    """One alarm line per vendor/version whose script_redlines row reports lens
    disagreements (> 0). No section at all when the lenses agree everywhere."""
    entries: list[str] = []
    for r in rows:
        if r.get("benchmark") != "script_redlines":
            continue
        n = r.get("n_lens_disagree")
        if not isinstance(n, (int, float)) or n <= 0:
            continue
        rate = r.get("lens_disagree_rate")
        pct = (
            f" ({float(rate) * 100:.1f}% of two-lens docs)"
            if isinstance(rate, (int, float))
            else ""
        )
        entries.append(
            f"- **{r['vendor']}** {r.get('tool_version') or ''}: "
            f"{int(n)} doc(s) where the lenses disagree{pct}"
        )
    if not entries:
        return []
    return [
        "### Lens health (script_redlines)",
        "",
        "Docs where the pixel lens and a judging lens (functional accept/reject "
        "invariant, WV-1 word-validate) conflict — the bench is measuring the "
        "wrong thing on those docs. A bench-health alarm, not a ranking signal.",
        "",
        *entries,
        "",
    ]


def _holdout_se(hold_line: dict) -> float | None:
    """Standard error of the holdout line's mean, from its per-doc ``scores``
    (sample stdev / √n); None when fewer than two per-doc scores are present."""
    scores = hold_line.get("scores")
    if not isinstance(scores, dict) or len(scores) < 2:
        return None
    values = [float(v) for v in scores.values() if isinstance(v, (int, float))]
    if len(values) < 2:
        return None
    return statistics.stdev(values) / (len(values) ** 0.5)


def holdout_gap_section(path: Path) -> list[str]:
    """## Holdout gap — per vendor, the sealed-holdout run vs a COMPARABLE
    main run, with ``gap = holdout − main``.

    Comparable means: same ``tool_version`` as the holdout line,
    ``holdout_mode == "excluded"`` (genuinely disjoint from the sealed set —
    pre-holdout lines CONTAIN the sealed docs and never qualify), and
    full-corpus size (n_docs > 100, so ``--limit`` smoke lines never pose as
    main). Without such a line the vendor row says "no comparable main run"
    instead of printing a misleading number. The log is append-only, so
    "latest" is last-in-file. When the holdout line carries per-doc scores the
    gap is rendered as ``gap ± 2·SE`` of the holdout mean. Renders a
    placeholder note while no holdout run has been recorded yet.
    """
    def _n_docs(line: dict) -> int:
        n = line.get("n_docs")
        return int(n) if isinstance(n, (int, float)) else 0

    main_lines: list[dict] = []
    hold_by_vendor: dict[str, dict] = {}
    if path.is_file():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(data.get("benchmark") or "") != "script_redlines":
                    continue
                vendor = str(data.get("vendor") or "")
                if not vendor:
                    continue
                if data.get("holdout_mode") == "only":
                    # Latest wins, but a partial run (--holdout --limit N) must
                    # not displace a fuller holdout line: prefer higher n, and
                    # recency only among equally-full lines.
                    prev = hold_by_vendor.get(vendor)
                    if prev is None or _n_docs(data) >= _n_docs(prev):
                        hold_by_vendor[vendor] = data
                else:
                    main_lines.append(data)
    # Describe the holdout by what the RUNS actually scored, not by a hard-coded size:
    # the sealed set grew from 20 (word_based only) to 40 when the SuperDoc subcorpus
    # landed, and the stale "20-pair" blurb contradicted the n_holdout column beside it.
    hold_sizes = {_n_docs(line) for line in hold_by_vendor.values() if _n_docs(line)}
    # Mid-migration vendors can disagree (20-key lines beside 40-key ones); printing
    # either number would be wrong for half the table, so the claim is dropped.
    sealed = f"Sealed {next(iter(hold_sizes))}-pair holdout" if len(hold_sizes) == 1 else "Sealed holdout"
    header = [
        "## Holdout gap",
        "",
        f"{sealed} (`corpus/holdout_combined.txt`) vs the visible "
        "corpus, per vendor: the latest holdout-only run (`bench run --holdout`) "
        "next to the latest COMPARABLE main run — same tool_version, "
        "`holdout_mode=excluded` (disjoint from the sealed set), full corpus "
        "(n > 100). `gap = holdout − main`; a strongly negative gap flags "
        "overfitting to the visible corpus.",
        "",
    ]
    if not hold_by_vendor:
        return [*header, "_no holdout runs recorded yet (`bench run --holdout`)_", ""]
    table_rows: list[list[str]] = []
    for vendor in sorted(hold_by_vendor):
        hold_line = hold_by_vendor[vendor]
        hold_mean = hold_line.get("overall_mean")
        hold_version = _norm_version(hold_line.get("tool_version"))
        main_line: dict | None = None
        for data in main_lines:  # append-only log: last qualifying line wins
            n = data.get("n_docs")
            if (
                str(data.get("vendor") or "") == vendor
                and _norm_version(data.get("tool_version")) == hold_version
                and data.get("holdout_mode") == "excluded"
                and isinstance(n, (int, float))
                and int(n) > 100
            ):
                main_line = data
        if main_line is None:
            table_rows.append([
                _escape_cell(vendor),
                "no comparable main run",
                "—",
                _escape_cell(_format_num(hold_mean)),
                _escape_cell(_format_num(hold_line.get("n_docs"))),
                "—",
            ])
            continue
        main_mean = main_line.get("overall_mean")
        if isinstance(hold_mean, (int, float)) and isinstance(main_mean, (int, float)):
            gap_value = float(hold_mean) - float(main_mean)
            se = _holdout_se(hold_line)
            gap = (
                f"{gap_value:+.2f} ± {2 * se:.2f}" if se is not None else f"{gap_value:+.2f}"
            )
        else:
            gap = "—"
        table_rows.append([
            _escape_cell(vendor),
            _escape_cell(_format_num(main_mean)),
            _escape_cell(_format_num(main_line.get("n_docs"))),
            _escape_cell(_format_num(hold_mean)),
            _escape_cell(_format_num(hold_line.get("n_docs"))),
            gap,
        ])
    return [
        *header,
        *_table(
            ["vendor", "main mean", "n_main", "holdout mean", "n_holdout", "gap"],
            table_rows,
        ),
        "",
        "`± 2·SE` uses the holdout line's per-doc scores; a |gap| below roughly "
        "2·SE is within sampling noise, not evidence of overfitting.",
        "",
    ]


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _paired_stats_section(rows: list[dict[str, object]]) -> list[str]:
    """Pairwise vendor comparisons on shared docs (script_redlines winners).

    Aggregate deltas between vendors scored on different doc subsets are not
    meaningful; here every comparison is paired per doc: win/loss/tie counts, the
    median paired delta, and a Wilcoxon signed-rank p-value (zsplit). Pairs with
    fewer than 20 shared docs are skipped.
    """
    candidates = [
        r for r in rows
        if str(r["benchmark"]) == "script_redlines" and isinstance(r.get("scores"), dict) and r["scores"]
    ]
    best_per_vendor: dict[str, dict[str, object]] = {}
    for r in candidates:
        vendor = str(r["vendor"])
        cur = best_per_vendor.get(vendor)
        if cur is None or _fidelity_sort_key(r) < _fidelity_sort_key(cur):
            best_per_vendor[vendor] = r
    vendors = sorted(best_per_vendor)
    if len(vendors) < 2:
        return []
    table_rows: list[list[str]] = []
    for i, va in enumerate(vendors):
        for vb in vendors[i + 1:]:
            sa = best_per_vendor[va]["scores"]
            sb = best_per_vendor[vb]["scores"]
            common = sorted(set(sa) & set(sb))  # type: ignore[arg-type]
            if len(common) < 20:
                continue
            deltas = [float(sa[d]) - float(sb[d]) for d in common]  # type: ignore[index]
            wins = sum(1 for d in deltas if d > 1e-9)
            losses = sum(1 for d in deltas if d < -1e-9)
            ties = len(deltas) - wins - losses
            median_delta = statistics.median(deltas)
            try:
                from scipy import stats as scipy_stats

                p_value = float(scipy_stats.wilcoxon(deltas, zero_method="zsplit").pvalue)
                p_cell = f"{p_value:.2e}"
            except (ImportError, ValueError):
                p_cell = "—"
            table_rows.append([
                _escape_cell(va),
                _escape_cell(vb),
                str(len(common)),
                f"{wins}/{losses}/{ties}",
                f"{median_delta:+.2f}",
                p_cell,
            ])
    if not table_rows:
        return []
    return [
        "### Paired comparisons (script_redlines)",
        "",
        "Per-doc paired deltas on shared documents (best pin per vendor); "
        "`win/loss/tie` counts docs where the FIRST vendor scores higher/lower/equal. "
        "Wilcoxon signed-rank p, zsplit zero method.",
        "",
        *_table(["vendor A", "vendor B", "docs", "win/loss/tie", "median Δ", "p"], table_rows),
        "",
    ]


def to_fidelity_markdown(rows: list[dict[str, object]], source: Path) -> str:
    by_bench: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_bench[str(row["benchmark"])].append(row)

    bench_keys = [b for b in BENCHMARK_ORDER if b in by_bench]
    for b in sorted(by_bench):
        if b not in bench_keys:
            bench_keys.append(b)

    n_versions = len({(str(r["vendor"]), str(r["tool_version"])) for r in rows})
    lines: list[str] = [
        "# Benchmark results",
        "",
        f"Source: `{source.as_posix()}` — **{len(rows)}** fidelity row(s) "
        f"(one per vendor×benchmark×**version**; {n_versions} distinct vendor×version "
        f"pin(s). docxodus rows with n_docs ≤ 100 are dropped as smoke/partial).",
        "",
        "Scores are 0–100 (higher = closer to the Microsoft Word oracle). "
        "Cross-renderer comparisons (LibreOffice vs Playwright) are **not** "
        "directly comparable — only compare within the same benchmark. "
        "Different **versions** of the same vendor are kept so you can compare "
        "pins (e.g. docxodus 6.4.0 vs 7.0.0).",
        "",
        "## Rankings by benchmark",
        "",
    ]

    for bench in bench_keys:
        items = sorted(by_bench[bench], key=_fidelity_sort_key)
        label = BENCHMARK_LABELS.get(bench, bench)
        lines.append(f"### `{bench}`")
        lines.append("")
        lines.append(label if label != bench else f"`{bench}`")
        lines.append("")

        # Corpus regimes are NOT comparable — a legacy tool scored on 164 easy docs
        # would otherwise outrank a current tool scored on 763, and the table would
        # read as a real result. Each regime gets its own table and its own rank 1.
        #
        # Presence of a stamp is not enough: 9.0.0 visual_redlines is stamped
        # b7f467074a51 and 9.8.0 is stamped 5ed816028d99. Ranking those as one
        # "current" table is the same lie as mixing stamped with unstamped.
        # Current = the corpus_revision on the newest stamped line; everything
        # else (older hashes, or no stamp) is legacy.
        stamped = [r for r in items if r.get("corpus_revision")]
        latest_rev = None
        if stamped:
            latest_rev = max(stamped, key=lambda r: str(r.get("timestamp") or "")).get(
                "corpus_revision",
            )
        current = [r for r in items if r.get("corpus_revision") == latest_rev]
        legacy = [r for r in items if r.get("corpus_revision") != latest_rev]
        if current and legacy:
            groups = [
                ("**Current corpus** (lines stamped with `corpus_revision`):", current),
                (
                    "**Legacy corpus** (older, smaller corpora — not comparable with "
                    "the rows above; kept for history until each tool re-runs):",
                    legacy,
                ),
            ]
        else:
            groups = [("", current or legacy)]

        for heading, group in groups:
            if heading:
                lines.append(heading)
                lines.append("")
            lines.extend(
                _table(
                    [
                        "#",
                        "vendor",
                        "version",
                        "mean",
                        "median",
                        "itt_mean",
                        "itt_median",
                        "skill_median",
                        "failures",
                        "n_docs",
                        "itt_n",
                        "exact_100",
                        "≥90",
                        "<50",
                    ],
                    [
                        [
                            str(rank),
                            _escape_cell(r["vendor"]),
                            _escape_cell(r.get("tool_version") or "—"),
                            _escape_cell(_format_num(r["mean"])),
                            _escape_cell(_format_num(r["median"])),
                            _escape_cell(_format_num(r.get("itt_mean"))),
                            _escape_cell(_format_num(r.get("itt_median"))),
                            _escape_cell(_format_num(r.get("skill_median"))),
                            _escape_cell(_format_num(r.get("n_failures"))),
                            _escape_cell(_format_num(r["n_docs"])),
                            _escape_cell(_format_num(r.get("itt_n"))),
                            _escape_cell(_format_num(r.get("exact_100"))),
                            _escape_cell(_format_num(r.get("at_least_90"))),
                            _escape_cell(_format_num(r.get("below_50"))),
                        ]
                        # Rank restarts per regime: continuing the numbering across the
                        # split would re-imply the cross-regime ordering it prevents.
                        for rank, r in enumerate(group, start=1)
                    ],
                )
            )
            lines.append("")
        if bench == "script_redlines":
            lines.extend(_common_subset_section(rows))
            lines.extend(_paired_stats_section(rows))
            lines.extend(_lens_health_section(rows))

    lines.extend(["## All fidelity runs (flat)", ""])
    flat_rows: list[list[str]] = [[
                _escape_cell(r["vendor"]),
                _escape_cell(r.get("tool_version") or "—"),
                _escape_cell(r["datetime"]),
                _escape_cell(r["benchmark"]),
                _escape_cell(_format_num(r["mean"])),
                _escape_cell(_format_num(r["median"])),
                _escape_cell(_format_num(r["n_docs"])),
            ] for r in rows]
    lines.extend(
        _table(
            ["vendor", "version", "datetime", "benchmark", "mean", "median", "n_docs"],
            flat_rows,
        )
    )
    lines.append("")
    return "\n".join(lines)


# ── Speed ─────────────────────────────────────────────────────────────────────


def _speed_rank(row: dict[str, object]) -> tuple:
    """Prefer larger sample count, then lower median (faster), then newer ts."""
    n = row.get("n")
    med = row.get("median")
    ts = str(row.get("run_ts") or "")
    throughput_per_s = row.get("throughput_per_s")
    n_v = int(n) if isinstance(n, (int, float)) else -1
    m_v = -float(med) if isinstance(med, (int, float)) else float("-inf")
    return (n_v, throughput_per_s, ts)


def _normalize_speed_row(data: dict, *, source: str = "") -> dict[str, object] | None:
    """Map a speed JSON object into a flat export row, or None if unusable."""
    kind = str(data.get("kind") or "speed")
    if kind == "redline_speed_bench":
        kind = "speed_redlines"
    unit = str(data.get("unit") or SPEED_UNIT_GENERATION)
    tool = str(data.get("tool") or data.get("engine") or "")
    if not tool:
        return None
    if data.get("error") and (data.get("median") or data.get("throughput_per_s"))is None:
        return None
    if data.get("median") is None and data.get("mean") is None:
        return None
    n = data.get("n")
    # Drop tiny smokes so they cannot win a tool slot over a real large-N run.
    if kind == "speed_redlines" and isinstance(n, (int, float)) and int(n) < 10:
        return None
    return {
        "kind": kind,
        "tool": tool,
        "engine": data.get("engine") or tool,
        "runtime": data.get("runtime") or "",
        "unit": unit,
        "n": n,
        "median": data.get("median"),
        "mean": data.get("mean"),
        "p90": data.get("p90"),
        "p95": data.get("p95"),
        "p99": data.get("p99"),
        "min": data.get("min"),
        "max": data.get("max"),
        "std": data.get("std"),
        "throughput_per_s": data.get("throughput_per_s"),
        "failures": data.get("failures"),
        "init_ms": data.get("init_ms"),
        "fixture_count": data.get("fixture_count") or data.get("fixture_target"),
        "pair_count": data.get("pair_count"),
        "warmup": data.get("warmup"),
        "reps": data.get("reps"),
        "profile_tool": data.get("profile_tool"),
        "run_ts": data.get("run_ts") or data.get("timestamp") or "",
        "source": source,
    }


def speed_rows_from_jsonl(path: Path) -> list[dict[str, object]]:
    """Best row per (kind, tool, unit) from a speed.jsonl append-only log."""
    best: dict[tuple[str, str, str], dict[str, object]] = {}
    if not path.is_file():
        return []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"warning: speed skip line {line_no}: {exc}", file=sys.stderr)
                continue
            row = _normalize_speed_row(data, source=str(path))
            if row is None:
                continue
            key = (str(row["kind"]), str(row["tool"]), str(row["unit"]))
            cur = best.get(key)
            if cur is None or _speed_rank(row) > _speed_rank(cur):
                best[key] = row
    return list(best.values())


def speed_rows_from_redline_summaries(root: Path) -> list[dict[str, object]]:
    """Pull completed runs from results/redline_speed_bench/**/summary.json."""
    base = root / "results" / "redline_speed_bench"
    if not base.is_dir():
        return []
    best: dict[tuple[str, str, str], dict[str, object]] = {}
    for summary in sorted(base.rglob("summary.json")):
        try:
            payload = json.loads(summary.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"warning: skip {summary}: {exc}", file=sys.stderr)
            continue
        rows = payload.get("rows")
        if not isinstance(rows, list):
            continue
        for data in rows:
            if not isinstance(data, dict):
                continue
            if "kind" not in data:
                data = {**data, "kind": "speed_redlines"}
            row = _normalize_speed_row(data, source=str(summary))
            if row is None:
                continue
            if row.get("pair_count") is None and payload.get("pairs") is not None:
                row["pair_count"] = payload.get("pairs")
            if row.get("fixture_count") is None and payload.get("fixtures") is not None:
                row["fixture_count"] = payload.get("fixtures")
            key = (str(row["kind"]), str(row["tool"]), str(row["unit"]))
            cur = best.get(key)
            if cur is None or _speed_rank(row) > _speed_rank(cur):
                best[key] = row
    return list(best.values())


def merge_speed_rows(*groups: list[dict[str, object]]) -> list[dict[str, object]]:
    best: dict[tuple[str, str, str], dict[str, object]] = {}
    for group in groups:
        for row in group:
            key = (str(row["kind"]), str(row["tool"]), str(row["unit"]))
            cur = best.get(key)
            if cur is None or _speed_rank(row) > _speed_rank(cur):
                best[key] = row
    return sorted(
        best.values(),
        key=lambda r: (
            str(r["kind"]),
            float(r["throughput_per_s"]) if isinstance(r.get("throughput_per_s"), (int, float)) else 1e18,
            str(r["tool"]),
        ),
    )


def _speed_section_table(rows: list[dict[str, object]], *, large_n: bool) -> list[str]:
    table_rows: list[list[str]] = []
    for rank, r in enumerate(rows, start=1):
        if large_n:
            table_rows.append(
                [
                    str(rank),
                    _escape_cell(r["tool"]),
                    _escape_cell(r.get("runtime") or "—"),
                    _escape_cell(_format_num(r.get("fixture_count"))),
                    _escape_cell(_format_num(r.get("pair_count"))),
                    _escape_cell(_format_num(r.get("median"), 3)),
                    _escape_cell(_format_num(r.get("mean"), 3)),
                    _escape_cell(_format_num(r.get("p95"), 3)),
                    _escape_cell(_format_num(r.get("p99"), 3)),
                    _escape_cell(_format_num(r.get("throughput_per_s"), 1)),
                    _escape_cell(_format_num(r.get("n"))),
                    _escape_cell(_format_num(r.get("failures"))),
                    _escape_cell(r.get("profile_tool") or "—"),
                ]
            )
        else:
            table_rows.append(
                [
                    str(rank),
                    _escape_cell(r["tool"]),
                    _escape_cell(r.get("runtime") or "—"),
                    _escape_cell(_format_num(r.get("median"), 3)),
                    _escape_cell(_format_num(r.get("mean"), 3)),
                    _escape_cell(_format_num(r.get("p95"), 3)),
                    _escape_cell(_format_num(r.get("p99"), 3)),
                    _escape_cell(_format_num(r.get("throughput_per_s"), 1)),
                    _escape_cell(_format_num(r.get("n"))),
                    _escape_cell(_format_num(r.get("failures"))),
                ]
            )
    if large_n:
        headers = [
            "#",
            "tool",
            "runtime",
            "fixtures",
            "pairs",
            "median ms",
            "mean ms",
            "p95",
            "p99",
            "/s",
            "n",
            "fail",
            "profile",
        ]
    else:
        headers = [
            "#",
            "tool",
            "runtime",
            "median ms",
            "mean ms",
            "p95",
            "p99",
            "/s",
            "n",
            "fail",
        ]
    return _table(headers, table_rows)


def speed_to_markdown(
    speed_rows: list[dict[str, object]],
    *,
    speed_source: Path | None,
) -> list[str]:
    """Markdown sections for generation + render speed (empty if no data)."""
    if not speed_rows:
        return []

    gen = [
        r
        for r in speed_rows
        if str(r.get("unit") or SPEED_UNIT_GENERATION) == SPEED_UNIT_GENERATION
        and str(r.get("kind")) in ("speed", "speed_redlines")
    ]
    micro = [r for r in gen if str(r.get("kind")) == "speed"]
    large = [r for r in gen if str(r.get("kind")) == "speed_redlines"]
    render = [
        r for r in speed_rows if str(r.get("unit") or "") == SPEED_UNIT_RENDER
    ]

    src = speed_source.as_posix() if speed_source else "results/speed.jsonl"
    lines: list[str] = [
        "## Redline generation speed",
        "",
        f"Source: `{src}` (+ `results/redline_speed_bench/**/summary.json` when present). "
        f"**{len(gen)}** generation row(s) after dedupe (one per tool×kind; prefer larger "
        f"`n`, then lower median). Unit: **ms per redline** (lower = faster). "
        f"See [`docs/SPEED.md`](docs/SPEED.md) for methodology.",
        "",
        "**Fairness (read before citing):**",
        "",
        "- **`*-inproc` / Node engines** — warm process, algorithm cost (thesis-grade).",
        "- **CLI tools** (`docxodus-csharp`, `jubarte-rust`) — spawn + I/O + compare per sample. "
        "C# cold-start dominates; do **not** cite CLI as algorithm cost.",
        "- **WASM `docxodus`** — Mono/.NET WASM in-process after one-time init; fat tail.",
        "",
    ]

    if micro:
        lines.append("### Microbench (`kind: speed`)")
        lines.append("")
        lines.append(
            "Classic `scripts/speed-bench.ts` / SuperDoc speed harness "
            "(typically ~30–40 pairs × 3 reps, in-memory for Node)."
        )
        lines.append("")
        lines.extend(_speed_section_table(micro, large_n=False))
        lines.append("")

    if large:
        lines.append("### Large-N `speed_redlines` (`scripts/redline_speed_bench.ts`)")
        lines.append("")
        lines.append(
            "Large fixture pools (often **1000 unique** docs → **5000 pairs**), "
            "including native C# Docxodus, jubarte-rust CLI/warm, WASM. "
            "Warm workers: `docxodus-csharp-inproc`, `jubarte-rust-inproc`."
        )
        lines.append("")
        lines.extend(_speed_section_table(large, large_n=True))
        lines.append("")

    if render:
        lines.append("### Render speed (`unit: ms_per_render`)")
        lines.append("")
        lines.append(
            "Playwright viewer → PDF. Not comparable to generation ms/redline."
        )
        lines.append("")
        lines.extend(_speed_section_table(render, large_n=False))
        lines.append("")

    lines.extend(
        [
            "### Speed methodology notes",
            "",
            "- Dedup key: `(kind, tool, unit)`. Best re-run by `(n, −median, run_ts)`.",
            "- `speed_redlines` rows with **n < 10** are dropped as trivial smokes.",
            "- Profiles (when present): samply `.profile.json.gz` for native CLIs/workers; "
            "V8 `.cpuprofile` for in-process Node (e.g. jubarte-lossless).",
            "- Regenerate after a run: `python3 scripts/export-results-md.py`.",
            "",
        ]
    )
    return lines


def fidelity_methodology_and_legal() -> list[str]:
    return [
        "## Methodology notes (fidelity)",
        "",
        "- Deduplication: one line per `(vendor, benchmark, tool_version)`. "
        "Re-runs of the **same** triple keep the best by "
        "`(render_fit, full_corpus_bucket, timestamp, overall_mean)` — prefer "
        "playwright for `visual_*` and soffice for script/accepted/roundtrip, "
        "then full-corpus lines (n > 100) over smokes, then the newest line "
        "(so a 383-doc post-holdout line supersedes a stale 403-doc one).",
        "- **Versions are not collapsed.** docxodus `6.4.0` and `7.0.0` both appear "
        "so pins can be compared directly.",
        "- **docxodus** filter: rows with **`n_docs ≤ 100`** are dropped (smoke / "
        "partial runs such as `visual_rendering` with n=21 or n=2). Full-corpus "
        "pins (typically n ≳ 145) are kept for every version.",
        "- Other vendors keep every version even if n is small (e.g. `prebaked` sanity).",
        "- Scores isolate *redline-markup fidelity vs Word* when candidates and the oracle "
        "share the same renderer (LibreOffice 26.2.4.2 for `script_redlines` / "
        "`accepted_changes` / `roundtrip`). Playwright `visual_*` scores are not "
        "cross-comparable with soffice scores.",
        "",
        "## Licensing & legal considerations",
        "",
        "These numbers are **independent engineering measurements**, not endorsements, "
        "certifications, or claims of compliance with any third-party product.",
        "",
        "- **This repository** (scoring core derived from "
        "[superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks)) "
        "is licensed under **AGPL-3.0-only**. See `LICENSE`.",
        "- **Microsoft Word** is a proprietary product of Microsoft. The Word oracle "
        "redlines are produced by Word for measurement only; Microsoft is not affiliated "
        "with this benchmark and does not endorse these results. Trademarks remain the "
        "property of their owners.",
        "- **Benchmarked engines** remain under their own licenses and copyrights; "
        "publishing a score does not change their terms:",
        "  - jubarte / in-repo ports — see their package licenses",
        "  - [docxodus](https://github.com/JSv4/docxodus) (MIT)",
        "  - [docx-redline-js](https://github.com/AnsonLai/docx-redline-js) (MIT)",
        "  - [folio](https://github.com/stella/folio) (Apache-2.0)",
        "  - [SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) (AGPL-3.0) and "
        "related SuperDoc tooling",
        "- **LibreOffice** is used only as a pinned PDF renderer for fair comparison; "
        "it is not a redline generator in this bench.",
        "- Redistributing or reusing scores, corpus fixtures, or generated redlines "
        "must still respect the licenses of the underlying tools and any corpus rights.",
        "",
        "Regenerate: `python3 scripts/export-results-md.py` "
        "(reads `results/bench.jsonl` + `results/speed.jsonl`).",
        "",
    ]


def to_markdown(
    rows: list[dict[str, object]],
    source: Path,
    *,
    speed_rows: list[dict[str, object]] | None = None,
    speed_source: Path | None = None,
    holdout_lines: list[str] | None = None,
) -> str:
    lines = [to_fidelity_markdown(rows, source).rstrip(), ""]
    if holdout_lines:
        lines.extend(holdout_lines)
    if speed_rows:
        lines.extend(speed_to_markdown(speed_rows, speed_source=speed_source))
    lines.extend(fidelity_methodology_and_legal())
    return "\n".join(lines) + "\n"


_MARKER_BLOCK = re.compile(
    r"<!-- (?P<name>[A-Z0-9_]+):BEGIN -->.*?<!-- (?P=name):END -->",
    re.DOTALL,
)


def _carry_foreign_marker_blocks(out: Path, md: str) -> str:
    """Preserve marker-delimited sections other generators own.

    Sibling generators (e.g. ``scripts/redline_dual_path_report.mjs``) write
    idempotent ``<!-- NAME:BEGIN -->…<!-- NAME:END -->`` blocks into the same
    files this exporter rewrites wholesale. Any such block present in the
    existing file but absent from the freshly generated markdown is appended,
    so a full export never destroys another tool's section.
    """
    if not out.is_file():
        return md
    existing = out.read_text(encoding="utf-8")
    carried = [
        m.group(0)
        for m in _MARKER_BLOCK.finditer(existing)
        if f"<!-- {m.group('name')}:BEGIN -->" not in md
    ]
    if not carried:
        return md
    return md.rstrip("\n") + "\n\n" + "\n\n".join(carried) + "\n"


def main(argv: list[str] | None = None) -> int:
    root = _repo_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=root / "results" / "bench.jsonl",
        help="Path to bench.jsonl (default: results/bench.jsonl)",
    )
    parser.add_argument(
        "--speed-input",
        type=Path,
        default=root / "results" / "speed.jsonl",
        help="Path to speed.jsonl (default: results/speed.jsonl; optional)",
    )
    parser.add_argument(
        "--no-speed",
        action="store_true",
        help="Skip speed sections even if speed.jsonl exists",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Markdown output path (default: RESULTS.md and docs/RESULTS.md)",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 1

    rows = rows_from_jsonl(args.input)
    try:
        source_disp = args.input.resolve().relative_to(root)
    except ValueError:
        source_disp = args.input

    speed_rows: list[dict[str, object]] = []
    speed_source: Path | None = None
    if not args.no_speed:
        from_jsonl = speed_rows_from_jsonl(args.speed_input)
        from_sum = speed_rows_from_redline_summaries(root)
        speed_rows = merge_speed_rows(from_jsonl, from_sum)
        if args.speed_input.is_file():
            try:
                speed_source = args.speed_input.resolve().relative_to(root)
            except ValueError:
                speed_source = args.speed_input

    md = to_markdown(
        rows,
        source_disp,
        speed_rows=speed_rows or None,
        speed_source=speed_source,
        holdout_lines=holdout_gap_section(args.input),
    )

    outputs: list[Path]
    if args.output is not None:
        outputs = [args.output]
    else:
        outputs = [root / "RESULTS.md", root / "docs" / "RESULTS.md"]

    for out in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_carry_foreign_marker_blocks(out, md), encoding="utf-8")
        print(
            f"Wrote {len(rows)} fidelity + {len(speed_rows)} speed row(s) → {out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
