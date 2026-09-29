"""Markdown rendering. Every table states its own policy, group and uncertainty."""

from __future__ import annotations

import json
import statistics
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from neurotic_docx_bench.ledger import docset as ds
from neurotic_docx_bench.ledger import policy as pol
from neurotic_docx_bench.ledger import stats as st
from neurotic_docx_bench.ledger.registry import Registry
from neurotic_docx_bench.ledger.rows import ResultRow
from neurotic_docx_bench.score import ScoreWeights

AFFILIATED_MARK = "†"

TITLES: dict[str, str] = {
    "script_redlines": "script_redlines: redline markup vs Word",
    "accepted_changes": "accepted_changes: accept all changes, match the final document",
    "roundtrip": "roundtrip: self-diff must not invent noise",
    "visual_rendering": "visual_rendering: editor render of the plain DOCX",
    "visual_redlines": "visual_redlines: editor render of the redline DOCX",
    "visual_accepted_changes": "visual_accepted_changes: editor render of the accepted DOCX",
    "docx_to_pdf": "docx_to_pdf: accepted and randomized redline DOCX to PDF vs Word export",
    "docx_to_pdf_no_redline_docs": "docx_to_pdf_no_redline_docs: source DOCX to PDF vs Word export",
    "corpus/word:all": "corpus/word:all: every corpus/word DOCX to PDF vs Word's own PDF",
    "docxide_metrics": "docxide_metrics: DOCX to PDF under docxide-pdf's own metrics",
    "corpus/word:le3pages": "below 3 pages: corpus/word DOCX to PDF vs Word's own PDF",
    "docxide_metrics:le3pages": "below 3 pages: docxide_metrics on the same documents",
}

ORACLE_NOTES: dict[str, str] = {
    "script_redlines": (
        "Oracle: Word's render of Word's tracked-change DOCX; candidates are rendered by the "
        "same Word build, so 100 means pixel-identical to Word's DOCX as Word draws it."
    ),
    "accepted_changes": (
        "Oracle: Word's render of Word's accepted DOCX; the candidate is the tool's own "
        "redline with every change accepted."
    ),
    "roundtrip": (
        "Oracle: Word's render of the unchanged source; the candidate is the tool's roundtrip output."
    ),
    "visual_rendering": (
        "Oracle: Word's own PDF export of the source; the candidate is a Playwright capture of the vendor editor."
    ),
    "visual_redlines": (
        "Oracle: Word's own PDF export of the redline; the candidate is a Playwright capture of the "
        "vendor editor loading Word's DOCX."
    ),
    "visual_accepted_changes": (
        "Oracle: Word's own PDF export of the accepted DOCX; the candidate is a Playwright capture of the vendor editor."
    ),
    "docx_to_pdf": "Oracle: SHA-pinned Word-export PDFs; the candidate is the converter's PDF.",
    "docx_to_pdf_no_redline_docs": (
        "Oracle: SHA-pinned Word-export PDFs of the source; the candidate is the converter's PDF."
    ),
    "corpus/word:all": (
        "Oracle: Word's PDF export of each DOCX in the four corpus/word states; the candidate is "
        "the converter's PDF of the same DOCX."
    ),
    "docxide_metrics": (
        "Word-export PDFs of the document set named below, scored with docxide-pdf's Jaccard "
        "and text-boundary metrics at 150 DPI; ranked on Jaccard, docxide-pdf's headline number."
    ),
    "corpus/word:le3pages": (
        "The corpus/word:all benchmark restricted to the documents Word lays out in 1 to 3 pages, "
        "so a converter that only renders the first 3 pages (unlicensed PyMuPDF Pro) is compared "
        "with every other converter on the same documents."
    ),
    "docxide_metrics:le3pages": (
        "The docxide_metrics benchmark on the same 1 to 3 page documents; ranked on Jaccard."
    ),
}


def fmt(x: float) -> str:
    return f"{x:.2f}"


def fmt_date(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d")


def md_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    sep = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([head, sep, *body])


def _tool_cell(row: ResultRow) -> str:
    return f"{row.display} {AFFILIATED_MARK}" if row.affiliated else row.display


def _rank_cell(r: pol.RankedRow) -> str:
    return f"{r.rank}=" if r.tied_with_previous else str(r.rank)


def _ci_cell(ci: tuple[float, float] | None) -> str:
    return f"[{fmt(ci[0])}, {fmt(ci[1])}]" if ci else "n/a"


def _hardware_cell(hw: Mapping[str, object] | None) -> str:
    if not hw:
        return "unknown"
    cpu = str(hw.get("cpu") or hw.get("machine") or "unknown")
    cores = hw.get("cores")
    return f"{cpu} ({cores} cores)" if cores else cpu


def _extra_metrics(rows: Sequence[ResultRow]) -> list[str]:
    names: list[str] = []
    for r in rows:
        for k in r.extra:
            if k not in names:
                names.append(k)
    return names


def fidelity_table(
    table: pol.HeadlineTable, *, row_ci: Mapping[str, tuple[float, float] | None]
) -> str:
    title = TITLES.get(table.benchmark, table.benchmark)
    out: list[str] = [f"### {title}", "", ORACLE_NOTES.get(table.benchmark, "")]
    if table.group is None or not table.rows:
        out.append("")
        out.append("No eligible rows for this benchmark yet.")
    else:
        g = table.group
        out.append("")
        inferred = (
            " This document set is not recorded in results/docsets.json, so its size is the "
            "largest ITT n in this group."
            if not table.docset_recorded
            else ""
        )
        out.append(
            f"Document set `{g.docset}` ({table.expected_n} documents), renderer `{g.renderer}`, "
            f"scorer `{g.scorer}`, bench `{g.bench}`. One row per tool: its latest eligible run. "
            "Sorted by ITT median, "
            "then ITT mean. Failed documents score 0 (intent-to-treat); Mean and Median are over "
            "scored documents only. 95% CI is a percentile bootstrap of the ITT median (2000 "
            "resamples, seed 42). An equal rank (`n=`) means the paired bootstrap interval of the "
            f"median difference to the row above includes 0. {AFFILIATED_MARK} marks an "
            "author-affiliated tool; the same rules apply to it." + inferred
        )
        out.append("")
        extras = _extra_metrics([r.row for r in table.rows])
        headers = [
            "Rank",
            "Tool",
            "Pin",
            "Run",
            "Docs",
            "Failed",
            "ITT Mean",
            "ITT Median",
            "95% CI",
            "Mean",
            "Median",
            "Perfect (100)",
            *[f"{m} median" for m in extras],
        ]
        body = []
        for r in table.rows:
            cells = [
                _rank_cell(r),
                _tool_cell(r.row),
                r.row.pin.display,
                fmt_date(r.row.timestamp),
                str(r.row.n_scored),
                str(r.row.n_failed_docs),
                fmt(r.row.itt_mean),
                fmt(r.row.itt_median),
                _ci_cell(row_ci.get(r.row.key)),
                fmt(r.row.mean),
                fmt(r.row.median),
                str(r.row.exact_100),
            ]
            for m in extras:
                v = r.row.extra.get(m, {}).get("median")
                cells.append(fmt(v) if v is not None else "n/a")
            body.append(cells)
        out.append(md_table(headers, body))
    if table.calibration:
        out.append("")
        out.append("Calibration rows (never ranked; the pipeline's own anchors):")
        out.append("")
        out.append(
            md_table(
                [
                    "Row",
                    "Pin",
                    "Run",
                    "Docs",
                    "Failed",
                    "ITT Mean",
                    "ITT Median",
                    "Perfect (100)",
                ],
                [
                    [
                        c.display,
                        c.pin.display,
                        fmt_date(c.timestamp),
                        str(c.n_scored),
                        str(c.n_failed_docs),
                        fmt(c.itt_mean),
                        fmt(c.itt_median),
                        str(c.exact_100),
                    ]
                    for c in table.calibration
                ],
            )
        )
    if table.excluded:
        out.append("")
        out.append("Not ranked in this group (latest run per tool, with the reason):")
        out.append("")
        for e in table.excluded:
            out.append(
                f"- {_tool_cell(e.row)} {e.row.pin.display} ({fmt_date(e.row.timestamp)}): "
                f"{'; '.join(e.verdict.reasons)}"
            )
    if table.not_applicable:
        out.append("")
        out.append(
            "Not applicable: "
            + "; ".join(
                f"{t.display} ({t.note})" if t.note else t.display
                for t in table.not_applicable
            )
        )
    if table.history_groups:
        out.append("")
        out.append(
            "Other document sets or renderers measured for this benchmark are listed under History "
            "in RESULTS_DETAILED.md: "
            + ", ".join(f"`{g.docset}`/`{g.renderer}`" for g in table.history_groups)
        )
    return "\n".join(out).rstrip() + "\n"


def _speed_rows(ranked: Sequence[pol.RankedSpeed]) -> list[list[str]]:
    return [
        [
            str(r.rank),
            (
                f"{r.row.display} {AFFILIATED_MARK}"
                if r.row.affiliated
                else r.row.display
            ),
            "in-process" if r.row.inproc else "cli",
            r.row.runtime or "unknown",
            r.row.pin.display,
            fmt_date(r.row.timestamp),
            str(r.row.fixture_count or "n/a"),
            str(r.row.pair_count or "n/a"),
            fmt(r.row.median_ms),
            fmt(r.row.mean_ms),
            fmt(r.row.p95_ms) if r.row.p95_ms is not None else "n/a",
            str(r.row.n),
            str(r.row.failures),
            _hardware_cell(r.row.hardware),
        ]
        for r in ranked
    ]


_SPEED_HEADERS = [
    "Rank",
    "Tool",
    "Mode",
    "Runtime",
    "Pin",
    "Run",
    "Fixtures",
    "Pairs",
    "Median ms",
    "Mean ms",
    "p95 ms",
    "n",
    "Failures",
    "Machine",
]


def speed_tables(h: pol.SpeedHeadline) -> str:
    out = ["### speed_redlines: generation time in ms per redline", ""]
    out.append(
        "Lower is faster. One row per tool and mode: its latest pinned run. Large-N rows rank only "
        f"at the canonical {pol.CANONICAL_SPEED_FIXTURES} fixtures; failures are excluded from the "
        "timing and counted in the Failures column, so read the two together. In-process rows skip "
        "process spawn; cli rows include it. The machine is part of the row because the number "
        "means nothing without it."
    )
    out.append("")
    out.append("Large-N:")
    out.append("")
    out.append(
        md_table(_SPEED_HEADERS, _speed_rows(h.large))
        if h.large
        else "No pinned large-N speed rows yet."
    )
    out.append("")
    out.append("Microbench (30 to 40 pairs, 3 repetitions):")
    out.append("")
    out.append(
        md_table(_SPEED_HEADERS, _speed_rows(h.micro))
        if h.micro
        else "No pinned microbench rows yet."
    )
    if h.excluded:
        out.append("")
        out.append("Not ranked (latest row per tool and mode):")
        out.append("")
        for e in h.excluded:
            mode = "in-process" if e.row.inproc else "cli"
            out.append(
                f"- {e.row.display} ({mode}, {e.row.kind}, {fmt_date(e.row.timestamp)}): "
                f"{'; '.join(e.verdict.reasons)}"
            )
    return "\n".join(out).rstrip() + "\n"


def history_section(
    rows: Sequence[ResultRow],
    *,
    registry: Registry,
    retractions: Sequence[pol.Retraction],
    docsets: Mapping[str, Mapping[str, object]],
) -> str:
    out = [
        "## History",
        "",
        (
            "Every row in the store, grouped by benchmark and comparability group, with the eligibility "
            "verdict the headline applied. Rows in different groups are different measurements."
        ),
        "",
    ]
    by_bench: dict[str, list[ResultRow]] = {}
    for r in rows:
        by_bench.setdefault(r.benchmark, []).append(r)
    for benchmark, bench_rows in sorted(by_bench.items()):
        out.append(f"### {benchmark}")
        groups: dict[pol.GroupKey, list[ResultRow]] = {}
        for r in bench_rows:
            groups.setdefault(pol.group_key(r), []).append(r)
        ordered = sorted(
            groups.items(), key=lambda kv: max(m.timestamp for m in kv[1]), reverse=True
        )
        for g, members in ordered:
            exp = pol.expected_n(members, docsets)
            out.append("")
            out.append(
                f"Group: document set `{g.docset}`, renderer `{g.renderer}`, scorer `{g.scorer}`, "
                f"bench `{g.bench}`, expected {exp} documents."
            )
            out.append("")
            body = []
            for r in sorted(members, key=lambda m: (m.display, m.timestamp)):
                v = pol.eligibility(
                    r,
                    expected=exp,
                    retractions=retractions,
                    registry=registry,
                    docsets=docsets,
                )
                approx = "~" if r.itt_approx else ""
                body.append(
                    [
                        _tool_cell(r),
                        r.pin.display,
                        fmt_date(r.timestamp),
                        str(r.n_scored),
                        str(r.n_failed_docs),
                        str(r.itt_n),
                        fmt(r.itt_median) + approx,
                        fmt(r.itt_mean) + approx,
                        "eligible" if v.eligible else "; ".join(v.reasons),
                        r.id_run,
                    ]
                )
            out.append(
                md_table(
                    [
                        "Tool",
                        "Pin",
                        "Run",
                        "Docs",
                        "Failed",
                        "ITT n",
                        "ITT Median",
                        "ITT Mean",
                        "Verdict",
                        "id_run",
                    ],
                    body,
                )
            )
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def below_gate_section(tables: Mapping[str, pol.HeadlineTable]) -> str:
    """Tools whose latest candidate run did not pass the gate, per benchmark."""
    blocks: list[str] = []
    for benchmark, table in sorted(tables.items()):
        if not table.below_gate:
            continue
        body = []
        for g in table.below_gate:
            body.append(
                [
                    _tool_cell(g.row),
                    g.row.pin.display,
                    fmt_date(g.gate_row.timestamp) if g.gate_row else "n/a",
                    fmt(g.gate_row.itt_median) if g.gate_row else "n/a",
                    fmt(g.null_row.itt_median) if g.null_row else "n/a",
                    _ci_cell(g.ci),
                    f"`{g.gate_docset}`" if g.gate_docset else "n/a",
                    g.reason,
                ]
            )
        blocks.append(f"### {TITLES.get(benchmark, benchmark)}")
        blocks.append("")
        blocks.append(
            md_table(
                [
                    "Tool",
                    "Pin",
                    "Gate run",
                    "Gate median",
                    "Null median",
                    "95% CI",
                    "Gate set",
                    "Reason",
                ],
                body,
            )
        )
        blocks.append("")
    if not blocks:
        return ""
    head = [
        "## Below the gate",
        "",
        (
            f"A tool enters the main page once its latest run on the gate set beats the null "
            f"baseline's ITT median by {pol.GATE_MARGIN:g} points and the 95% bootstrap CI of "
            "its gate median stays above the null median. These tools have a full run that "
            "is otherwise eligible but no passing gate run yet."
        ),
        "",
    ]
    return "\n".join(head + blocks).rstrip() + "\n"


def paired_section(tables: Mapping[str, pol.HeadlineTable]) -> str:
    out = [
        "## Paired comparisons",
        "",
        (
            "Per-document deltas on the documents both tools scored, inside the headline group. "
            "`win/loss/tie` counts documents where the first tool scores higher, lower, or equal. The "
            "interval is a percentile bootstrap of the median delta (2000 resamples, seed 42); it "
            "includes 0 when the two tools are not distinguishable on this corpus."
        ),
        "",
    ]
    any_rows = False
    for benchmark, t in sorted(tables.items()):
        ranked = [r.row for r in t.rows if r.row.scores]
        if len(ranked) < 2:
            continue
        body = []
        for i, a in enumerate(ranked):
            for b in ranked[i + 1 :]:
                d = st.paired_median_diff(a.itt_scores(), b.itt_scores())
                if d is None:
                    continue
                body.append(
                    [
                        _tool_cell(a),
                        _tool_cell(b),
                        str(d.n),
                        f"{d.wins}/{d.losses}/{d.ties}",
                        f"{d.median_delta:+.2f}",
                        f"[{d.ci_low:+.2f}, {d.ci_high:+.2f}]",
                    ]
                )
        if body:
            any_rows = True
            out.append(f"### {benchmark}")
            out.append("")
            out.append(
                md_table(
                    [
                        "Tool A",
                        "Tool B",
                        "Docs",
                        "win/loss/tie",
                        "Median delta",
                        "95% CI",
                    ],
                    body,
                )
            )
            out.append("")
    if not any_rows:
        out.append("No benchmark has two ranked rows with per-document scores yet.")
    return "\n".join(out).rstrip() + "\n"


def lens_health_section(rows: Sequence[ResultRow]) -> str:
    flagged = [r for r in rows if (r.n_lens_disagree or 0) > 0]
    if not flagged:
        return ""
    body = [
        [
            _tool_cell(r),
            r.benchmark,
            r.pin.display,
            fmt_date(r.timestamp),
            str(r.n_lens_disagree),
            f"{r.lens_disagree_rate or 0:.2f}",
        ]
        for r in sorted(flagged, key=lambda r: -(r.lens_disagree_rate or 0))
    ]
    return (
        "\n".join(
            [
                "## Lens health",
                "",
                (
                    "Runs where the pixel lens and the functional lens disagreed on some documents. "
                    "A bench-health alarm, never a ranking input."
                ),
                "",
                md_table(
                    ["Tool", "Benchmark", "Pin", "Run", "Docs disagreeing", "Rate"],
                    body,
                ),
            ]
        )
        + "\n"
    )


def methodology_section(*, noise_sigma: float | None, lo_version: str | None) -> str:
    w = ScoreWeights()
    if noise_sigma is not None and lo_version:
        noise = (
            f"Re-rendering the same DOCX with the same LibreOffice build ({lo_version}) gives a "
            f"score standard deviation of {noise_sigma:.1e} (results/noise_floor.json)."
        )
    else:
        noise = "Noise floor not recorded; run `bench noise-floor`."
    return "\n".join(
        [
            "## Methodology",
            "",
            (
                "Scoring. Each page pair is rasterized at 144 DPI and scored 0 to 100 as a weighted sum "
                "lifted verbatim from superdoc-visual-benchmarks: "
                f"SSIM full {w.ssim_full:g}, SSIM small {w.ssim_small:g}, ink F1 {w.ink_f1:g}, "
                f"edge IoU {w.edge_iou:g}, colour {w.color_sim:g}, blob {w.blob_sim:g}. "
                "A document scores 0.7 times its page mean plus 0.3 times its worst page. For "
                "script_redlines, accepted_changes and roundtrip the ranked score is `pagefair-v2`: "
                "pages present on only one side enter at 0, ink-weighted. The visual_* benchmarks rank "
                "on the raw score because cross-engine repagination is expected there. SuperDoc, whose "
                "benchmark the formula comes from, is itself a ranked vendor; the parity tests keep the "
                "formula byte-identical to upstream."
            ),
            "",
            "Oracles. The redline benchmarks compare Word's render of the candidate DOCX to "
            "Word's render of Word's DOCX; only Word-rendered rows are ranked, and rows rendered "
            "with LibreOffice stay in the History section. The docx_to_pdf and visual_* benchmarks "
            "compare to Word's own PDF export. A tool can score 100 on the first family and well "
            "below 100 on the second, because the second also measures the renderer's distance "
            "from Word. " + noise,
            "",
            (
                f"The gate. A tool enters a main-page table once its latest run on that benchmark's "
                f"gate set ({ds.GATE_N} documents drawn across the corpus strata, recorded in "
                f"`results/docsets.json` with its own docset id) beats the null baseline's ITT median "
                f"by {pol.GATE_MARGIN:g} points and the 95% bootstrap CI of its gate median stays "
                f"above the null median. Tools with an eligible full run and no passing gate run are "
                f"listed under Below the gate."
            ),
            "",
            (
                "Denominators. Every benchmark has a fixed document set (`results/docsets.json`); a "
                "document with no candidate output enters at 0 (intent-to-treat). Documents named by a "
                "non-fatal stage warning but scored keep their score and are not counted as failed."
            ),
            "",
            (
                "Selection. One row per tool: its latest eligible run in the current comparability "
                "group. There is no best-of-N over runs and no best pin. A run that is wrong for a reason "
                "unrelated to the tool is retracted with a stated reason in `results/retractions.jsonl` "
                "and listed as such."
            ),
            "",
            (
                "Uncertainty. Per-row intervals are a percentile bootstrap of the ITT median. Adjacent "
                "rows tie when the paired bootstrap interval of their median difference includes 0."
            ),
            "",
            (
                "Disclosure. The benchmark is maintained by the author of the Jubarte tools. Those rows "
                "are marked and follow the same rules as every other row."
            ),
            "",
        ]
    )


def vendor_table(registry: Registry) -> str:
    rows = []
    for t in registry.tools:
        if t.status != "active" or t.role == "calibration":
            continue
        rows.append(
            [
                f"[{t.display}]({t.url})" if t.url else t.display,
                t.role,
                t.engine,
                "yes" if t.affiliated else "",
                t.note or "",
            ]
        )
    return (
        md_table(["Tool", "Role", "Engine", "Author-affiliated", "Note"], rows) + "\n"
    )


# ---- holdout gap ----------------------------------------------------------------


def _format_num(value: object, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        text = f"{value:.{digits}f}".rstrip("0").rstrip(".")
        return text if text else "0"
    return str(value)


def _escape_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def _norm_version(value: object) -> str:
    if value is None:
        return "n/a"
    text = str(value).strip()
    return text if text else "n/a"


def _holdout_se(hold_line: dict) -> float | None:
    """Standard error of the holdout line's mean from its per-doc scores; None below 2."""
    scores = hold_line.get("scores")
    if not isinstance(scores, dict) or len(scores) < 2:
        return None
    values = [float(v) for v in scores.values() if isinstance(v, int | float)]
    if len(values) < 2:
        return None
    return statistics.stdev(values) / (len(values) ** 0.5)


def holdout_gap_section(path: Path) -> list[str]:
    """Per vendor, the sealed-holdout run vs a comparable main run, gap = holdout - main.

    Comparable means the same tool_version as the holdout line, holdout_mode
    "excluded" (disjoint from the sealed set), and full-corpus size (n_docs > 100). The
    log is append-only, so the latest qualifying line wins. Reads the raw store so a
    holdout-only line (never a ranked row) still counts here.
    """

    def _n_docs(line: dict) -> int:
        n = line.get("n_docs")
        return int(n) if isinstance(n, int | float) else 0

    main_lines: list[dict] = []
    hold_by_vendor: dict[str, dict] = {}
    if Path(path).is_file():
        with Path(path).open(encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if str(data.get("benchmark") or "") != "script_redlines":
                    continue
                vendor = str(data.get("vendor") or "")
                if not vendor:
                    continue
                if data.get("holdout_mode") == "only":
                    prev = hold_by_vendor.get(vendor)
                    if prev is None or _n_docs(data) >= _n_docs(prev):
                        hold_by_vendor[vendor] = data
                else:
                    main_lines.append(data)
    hold_sizes = {_n_docs(line) for line in hold_by_vendor.values() if _n_docs(line)}
    sealed = (
        f"Sealed {next(iter(hold_sizes))}-pair holdout"
        if len(hold_sizes) == 1
        else "Sealed holdout"
    )
    header = [
        "## Holdout gap",
        "",
        (
            f"{sealed} (`corpus/word/pools/holdout.txt`) vs the visible corpus, per vendor: "
            "the latest holdout-only run (`bench run --holdout`) next to the latest "
            "comparable main run (same tool_version, `holdout_mode=excluded`, full corpus "
            "with n > 100). `gap = holdout - main`; a strongly negative gap flags "
            "overfitting to the visible corpus."
        ),
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
        for data in main_lines:
            n = data.get("n_docs")
            if (
                str(data.get("vendor") or "") == vendor
                and _norm_version(data.get("tool_version")) == hold_version
                and data.get("holdout_mode") == "excluded"
                and isinstance(n, int | float)
                and int(n) > 100
            ):
                main_line = data
        if main_line is None:
            table_rows.append(
                [
                    _escape_cell(vendor),
                    "no comparable main run",
                    "n/a",
                    _escape_cell(_format_num(hold_mean)),
                    _escape_cell(_format_num(hold_line.get("n_docs"))),
                    "n/a",
                ]
            )
            continue
        main_mean = main_line.get("overall_mean")
        if isinstance(hold_mean, int | float) and isinstance(main_mean, int | float):
            gap_value = float(hold_mean) - float(main_mean)
            se = _holdout_se(hold_line)
            gap = (
                f"{gap_value:+.2f} ± {2 * se:.2f}"
                if se is not None
                else f"{gap_value:+.2f}"
            )
        else:
            gap = "n/a"
        table_rows.append(
            [
                _escape_cell(vendor),
                _escape_cell(_format_num(main_mean)),
                _escape_cell(_format_num(main_line.get("n_docs"))),
                _escape_cell(_format_num(hold_mean)),
                _escape_cell(_format_num(hold_line.get("n_docs"))),
                gap,
            ]
        )
    return [
        *header,
        md_table(
            ["vendor", "main mean", "n_main", "holdout mean", "n_holdout", "gap"],
            table_rows,
        ),
        "",
        (
            "`± 2·SE` uses the holdout line's per-doc scores; a |gap| below roughly 2·SE "
            "is within sampling noise, not evidence of overfitting."
        ),
        "",
    ]
