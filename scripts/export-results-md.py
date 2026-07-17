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

When the same key appears more than once, keeps the best re-run (see rankers).
"""

from __future__ import annotations

import argparse
import json
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
    visual_*, soffice for script/accepted/roundtrip), then higher n_docs, mean,
    and newer timestamp. Avoids a soffice main-run line "winning" over a real
    Playwright visual_* line just because it has more docs.
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

    n = row.get("n_docs")
    mean = row.get("mean")
    ts = row.get("datetime") or ""
    n_v = int(n) if isinstance(n, (int, float)) else -1
    m_v = float(mean) if isinstance(mean, (int, float)) else float("-inf")
    return (render_fit, n_v, m_v, str(ts))


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
            }
            key = (vendor, benchmark, version)
            cur = best.get(key)
            if cur is None or _rank(row) > _rank(cur):
                best[key] = row

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


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


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
        items = sorted(
            by_bench[bench],
            key=lambda r: (
                -(
                    float(r["mean"])
                    if isinstance(r["mean"], (int, float))
                    else float("-inf")
                ),
                -(int(r["n_docs"]) if isinstance(r["n_docs"], (int, float)) else -1),
                str(r["vendor"]),
                str(r["tool_version"]),
            ),
        )
        label = BENCHMARK_LABELS.get(bench, bench)
        lines.append(f"### `{bench}`")
        lines.append("")
        lines.append(label if label != bench else f"`{bench}`")
        lines.append("")
        table_rows: list[list[str]] = []
        for rank, r in enumerate(items, start=1):
            table_rows.append(
                [
                    str(rank),
                    _escape_cell(r["vendor"]),
                    _escape_cell(r.get("tool_version") or "—"),
                    _escape_cell(_format_num(r["mean"])),
                    _escape_cell(_format_num(r["median"])),
                    _escape_cell(_format_num(r["n_docs"])),
                    _escape_cell(_format_num(r.get("exact_100"))),
                    _escape_cell(_format_num(r.get("at_least_90"))),
                    _escape_cell(_format_num(r.get("below_50"))),
                ]
            )
        lines.extend(
            _table(
                [
                    "#",
                    "vendor",
                    "version",
                    "mean",
                    "median",
                    "n_docs",
                    "exact_100",
                    "≥90",
                    "<50",
                ],
                table_rows,
            )
        )
        lines.append("")

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
            float(r["throughput_per_s"]) if isinstance(r["throughput_per_s"], (int, float)) else 1e18,
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
        "`(render_fit, n_docs, overall_mean, timestamp)` — prefer playwright for "
        "`visual_*` and soffice for script/accepted/roundtrip, then higher n / mean.",
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
) -> str:
    lines = [to_fidelity_markdown(rows, source).rstrip(), ""]
    if speed_rows:
        lines.extend(speed_to_markdown(speed_rows, speed_source=speed_source))
    lines.extend(fidelity_methodology_and_legal())
    return "\n".join(lines) + "\n"


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
    )

    outputs: list[Path]
    if args.output is not None:
        outputs = [args.output]
    else:
        outputs = [root / "RESULTS.md", root / "docs" / "RESULTS.md"]

    for out in outputs:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(
            f"Wrote {len(rows)} fidelity + {len(speed_rows)} speed row(s) → {out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
