#!/usr/bin/env python3
"""Export bench.jsonl aggregates into a markdown table (RESULTS.md).

One row per **(vendor, benchmark, tool_version)** so different pins of the same
engine (e.g. docxodus 6.4.0 vs 7.0.0) appear side-by-side for comparison.

When the same triple appears more than once (re-runs), keeps the best line by
(n_docs, overall_mean, timestamp).
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


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return lines


def to_markdown(rows: list[dict[str, object]], source: Path) -> str:
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
        f"Source: `{source.as_posix()}` — **{len(rows)}** row(s) "
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
                -(float(r["mean"]) if isinstance(r["mean"], (int, float)) else float("-inf")),
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

    lines.extend(
        [
            "## All runs (flat)",
            "",
        ]
    )
    flat_rows: list[list[str]] = []
    for r in rows:
        flat_rows.append(
            [
                _escape_cell(r["vendor"]),
                _escape_cell(r.get("tool_version") or "—"),
                _escape_cell(r["datetime"]),
                _escape_cell(r["benchmark"]),
                _escape_cell(_format_num(r["mean"])),
                _escape_cell(_format_num(r["median"])),
                _escape_cell(_format_num(r["n_docs"])),
            ]
        )
    lines.extend(
        _table(
            ["vendor", "version", "datetime", "benchmark", "mean", "median", "n_docs"],
            flat_rows,
        )
    )
    lines.extend(
        [
            "",
            "## Methodology notes",
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
            "Regenerate: `python3 scripts/export-results-md.py`.",
            "",
        ]
    )
    return "\n".join(lines)


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
        "--output",
        type=Path,
        default=root / "RESULTS.md",
        help="Markdown output path (default: RESULTS.md)",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        print(f"error: input not found: {args.input}", file=sys.stderr)
        return 1

    rows = rows_from_jsonl(args.input)
    # Prefer a short relative path in the markdown source line when under repo root.
    try:
        source_disp = args.input.resolve().relative_to(root)
    except ValueError:
        source_disp = args.input
    md = to_markdown(rows, source_disp)
    args.output.write_text(md, encoding="utf-8")
    print(f"Wrote {len(rows)} row(s) → {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
