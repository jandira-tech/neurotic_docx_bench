"""Typer CLI for neurotic-docx-bench.

PR2 commands: ``render`` (DOCX/PDF folder → PDFs), ``compare`` (two PDF folders → scores),
``run`` (drive a single tool from bench.yaml: render its source, score vs the oracle).
Sequential multi-tool runs, JSONL emission and gating arrive in later PRs.
"""

from __future__ import annotations

import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast
from urllib.error import URLError
from urllib.request import urlopen

import typer
from rich import box
from rich.align import Align
from rich.console import Console
from rich.highlighter import RegexHighlighter
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from neurotic_docx_bench import pipeline, provenance, stages, tool_updater
from neurotic_docx_bench.benchmarks import BenchmarkName, BenchmarkOutcome
from neurotic_docx_bench.config import BenchConfig, RunConfig, environment_config_for_run, load_config
from neurotic_docx_bench.emit import jsonl as jsonl_emit
from neurotic_docx_bench.emit import snapshot as snapshot_emit
from neurotic_docx_bench.gate import gate as run_gate
from neurotic_docx_bench.render.base import Renderer, RenderReport
from neurotic_docx_bench.render.passthrough import PassthroughRenderer
from neurotic_docx_bench.render.soffice import SofficeRenderer
from neurotic_docx_bench.visual_oracles import visual_benchmarks_for_run

# Type aliases for complex data structures
HarnessConfig = dict[str, str]
ScoreResult = pipeline.ScoreResult
PerDocScores = dict[str, ScoreResult]
FailureRecord = dict[str, str]
AggregateStats = dict[str, float | int]


class ReportData(TypedDict):
    tool: str
    n_docs: int
    aggregate_redline: AggregateStats
    aggregate_accepted: AggregateStats
    per_doc: dict[str, dict[str, float | None]]
    accept_failures: list[dict[str, str | None]]


# Helper to extract overall_score safely
def _get_overall_score(result: ScoreResult) -> float:
    """Extract overall_score from a ScoreResult."""
    return float(result["overall_score"])


app = typer.Typer(
    name="bench",
    help="neurotic-docx-bench — DOCX tool fidelity benchmark vs a Microsoft Word oracle.",
    no_args_is_help=True,
    add_completion=False,
)


class _BenchmarkHighlighter(RegexHighlighter):
    """Auto-highlight the benchmark keyword and the document count in header lines.

    Mirrors Rich's ``RegexHighlighter`` recipe (the email-highlighter example): feed
    it plain text and the words ``benchmark`` and ``<n> documents`` get styled by the
    themed ``bench.*`` styles below — no handrolled markup.
    """

    base_style = "bench."
    highlights = [
        r"(?P<keyword>benchmark)",
        r"(?P<count>\d+)\s+(?P<unit>documents?)",
    ]


# Named theme styles for the benchmark header highlighter. Additive over Rich's
# defaults, so existing markup like [bold]/[green]/[cyan] is unaffected.
console = Console(
    theme=Theme(
        {
            "bench.keyword": "bold #3B82E0",
            "bench.count": "bold bright_green",
            "bench.unit": "green",
        },
    ),
)


def _renderer(backend: str, harness: HarnessConfig | None = None) -> Renderer:
    """Factory for render backends."""
    if backend == "soffice":
        return SofficeRenderer()
    if backend == "passthrough":
        return PassthroughRenderer()
    if backend == "playwright":
        from neurotic_docx_bench.render.playwright import PlaywrightRenderer

        return PlaywrightRenderer(harness)
    if backend == "word":
        from neurotic_docx_bench.render.word import WordRenderer

        return WordRenderer()
    raise typer.BadParameter(f"unknown render backend: {backend!r}")


def _limited_source(source: Path, pattern: str, limit: int | None) -> tuple[Path, bool]:
    """Return (source_dir, is_temp). If limit is set, copy the first N matching files into
    a temp dir so only a subset is rendered/scored.
    """
    if not limit:
        return source, False
    files = sorted(source.glob(pattern))[:limit]
    tmp = Path(tempfile.mkdtemp(prefix="bench-subset."))
    for f in files:
        _ = shutil.copy(f, tmp / f.name)
    return tmp, True


def _warn_mismatches(per_doc: PerDocScores) -> None:
    bad = [
        f'{k} (oracle {v["page_count_oracle"]} vs candidate {v["page_count_candidate"]})'
        for k, v in per_doc.items()
        if v.get("page_count_mismatch")
    ]
    if bad:
        console.print(
            f'[yellow]page-count mismatch on {len(bad)} doc(s)[/yellow] (scored on the shared pages only): {"; ".join(bad[:5])}{(" …" if len(bad) > 5 else "")}',
        )


def _score_style(score: float) -> str:
    """Rich style for a fidelity score, on a six-tier gradient:

    bright green (100) → green (≥70) → Michigan Blue (≥50) → Michigan Blue (≥30)
    → red (≥15) → bright red (<15). Anything above 70% lands in the green family.
    Blue/yellow tiers use a bright blue (#3B82E0).
    """
    if score >= 100.0 - 1e-6:
        return "bold bright_green"
    if score >= 70.0:
        return "green"
    if score >= 50.0:
        return "#3B82E0"
    if score >= 30.0:
        return "#3B82E0"
    if score >= 15.0:
        return "red"
    return "bright_red"


def _score_table(scores: dict[str, float], *, title: str | None = None) -> Table:
    """An elegant Rich table of ``{document: score}`` with the distribution stats
    in the caption. Scores are colour-coded against the 90/50 fidelity bands.
    """
    values = list(scores.values())
    table = Table(
        title=title,
        title_style="bold",
        caption=(
            f"mean {statistics.mean(values):.2f} · median {statistics.median(values):.2f} · "
            f"min {min(values):.2f} · max {max(values):.2f} · n {len(values)}"
        ),
        caption_style="dim",
        box=box.ROUNDED,
        row_styles=["", "dim"],
    )
    table.add_column("document", overflow="fold", justify="left", style="#3B82E0")
    table.add_column("score", justify="right", header_style="bold")
    for key in sorted(scores):
        s = scores[key]
        table.add_row(key, f"[{_score_style(s)}]{s:.2f}[/]")
    return table


def _print_scores(scores: dict[str, float], *, title: str | None = None) -> None:
    if not scores:
        console.print("[yellow]no matched documents scored[/yellow]")
        return
    console.print(Align.center(_score_table(scores, title=title)))


def _print_benchmark_header(*, vendor: str, benchmark: str, n_docs: int) -> None:
    """A centralized Rich line announcing a benchmark, with the vendor and the
    document count below it.

    A blank line + ``console.rule`` (a Rich horizontal rule — not a handrolled
    divider) separates one benchmark from the previous; a ``RegexHighlighter``
    auto-styles ``benchmark`` and ``<n> documents`` via the themed ``bench.*``
    styles.
    """
    console.print()  # visual breathing room between benchmarks
    console.rule(f"[bold #FFCB05]benchmark: {benchmark}[/bold #FFCB05]", align="center")
    line = Text(f"{vendor}  ·  {n_docs} document{'s' if n_docs != 1 else ''}")
    _BenchmarkHighlighter().highlight(line)
    console.print(Align.center(line))


def _print_benchmark_block(
    scores: dict[str, float], *, vendor: str, benchmark: str,
) -> None:
    """Print one benchmark's results: a centralized header (Rich rule + highlighted
    vendor/doc-count line) followed by the centralized, left-aligned, boxed, captioned
    score table with the six-tier colour gradient. No table title — the header line
    already carries the vendor and doc count, so a title would duplicate it.
    """
    if not scores:
        console.print("[yellow]no matched documents scored[/yellow]")
        return
    _print_benchmark_header(vendor=vendor, benchmark=benchmark, n_docs=len(scores))
    console.print(Align.center(_score_table(scores)))


def _print_accept_compare_table(data: ReportData) -> None:
    """Render the accept-compare report to the console as an elegant Rich table.

    The markdown report is still written to ``accepted_report.md`` for the record;
    this is the live console view (redline vs accepted, with per-doc delta).
    """
    per_doc = data["per_doc"]
    if not per_doc:
        console.print("[yellow]accept-compare: no matched documents scored[/yellow]")
        return
    _print_benchmark_header(vendor=data["tool"], benchmark="accepted_changes", n_docs=data["n_docs"])
    ar = data["aggregate_redline"]
    aa = data["aggregate_accepted"]

    def fmt(v: float | None) -> str:
        return "—" if v is None else f"{v:.2f}"

    def cell(v: float | None) -> str:
        return "[dim]—[/]" if v is None else f"[{_score_style(v)}]{v:.2f}[/]"

    def delta_cell(d: float | None) -> str:
        if d is None:
            return "[dim]—[/]"
        if d >= 1e-6:
            return f"[green]+{d:.2f}[/]"
        if d <= -1e-6:
            return f"[red]{d:.2f}[/]"
        return f"[dim]{d:.2f}[/]"

    table = Table(
        caption=(
            f'redline  mean {fmt(ar.get("mean"))} · median {fmt(ar.get("median"))}    '
            f'accepted  mean {fmt(aa.get("mean"))} · median {fmt(aa.get("median"))}    '
            f'n {data["n_docs"]}'
        ),
        caption_style="dim",
        box=box.ROUNDED,
        row_styles=["", "dim"],
    )
    table.add_column("document", overflow="fold", justify="left", style="#3B82E0")
    table.add_column("redline", justify="right", header_style="bold")
    table.add_column("accepted", justify="right", header_style="bold")
    table.add_column("delta", justify="right", header_style="bold")
    for k in sorted(per_doc):
        d = per_doc[k]
        table.add_row(k, cell(d["redline_score"]), cell(d["accepted_score"]), delta_cell(d["delta"]))
    if data["accept_failures"]:
        table.add_section()
        for f in data["accept_failures"]:
            table.add_row(
                str(f.get("doc", "?")),
                "[red]accept failed[/]",
                "",
                str(f.get("error", "")),
            )
    console.print(Align.center(table))


@app.command()
def render(
    source: Path = typer.Argument(..., help="folder of DOCX (soffice) or PDF (passthrough)"),
    work_dir: Path = typer.Argument(..., help="scratch dir; PDFs land in <work_dir>/pdf"),
    backend: str = typer.Option("soffice", "--backend", "-b"),
    jobs: int = typer.Option(4, "--jobs", "-j"),
    force: bool = typer.Option(False, "--force", "-f"),
) -> None:
    """Render a folder of documents to PDF."""
    report = _renderer(backend).to_pdfs(source, work_dir, force=force, jobs=jobs)
    console.print(
        f"rendered [green]{report.ok_count}[/green] ok, [red]{report.fail_count}[/red] failed → {report.pdf_dir}",
    )
    for r in report.results:
        if not r.ok:
            console.print(f"  [red]FAIL[/red] {r.source.name}: {r.error}")
    raise typer.Exit(1 if report.fail_count else 0)


@app.command()
def compare(
    candidate: Path = typer.Argument(..., help="folder of candidate PDFs"),
    oracle: Path = typer.Argument(..., help="folder of Word oracle PDFs"),
    tool: str | None = typer.Option(None, "--tool", help="tool token in candidate names (…_<tool>_redline)"),
    dpi: int = typer.Option(144, "--dpi"),
    jobs: int = typer.Option(8, "--jobs", "-j"),
    limit: int | None = typer.Option(None, "--limit"),
    json_out: Path | None = typer.Option(None, "--json", help="write scores as JSON"),
) -> None:
    """Score a folder of candidate redline PDFs against the Word oracle redlines."""
    cand_dir, is_temp = _limited_source(candidate, "*.pdf", limit)
    try:
        with tempfile.TemporaryDirectory(prefix="bench-work.") as work:
            per_doc = pipeline.score_folders_full(
                oracle, cand_dir, Path(work), dpi=dpi, jobs=jobs, candidate_tool=tool,
            )
    finally:
        if is_temp:
            shutil.rmtree(cand_dir, ignore_errors=True)
    scores = {k: _get_overall_score(v) for k, v in per_doc.items()}
    _warn_mismatches(per_doc)
    _print_benchmark_block(
        scores,
        vendor=tool or "candidate",
        benchmark="compare",
    )
    if json_out:
        json_out.write_text(json.dumps(scores, indent=2, sort_keys=True))
        console.print(f"wrote {json_out}")


def _agg(values: Iterable[float | None]) -> dict[str, float | int]:
    vals = [v for v in values if v is not None]
    if not vals:
        return {}
    return {
        "mean": round(statistics.mean(vals), 2),
        "median": round(statistics.median(vals), 2),
        "min": round(min(vals), 2),
        "max": round(max(vals), 2),
        "n": len(vals),
    }


def _accepted_report(
    tool: str,
    redline_scores: dict[str, float],
    accepted_scores: dict[str, float],
    accept_failures: list[dict[str, str | None]],
) -> tuple[str, ReportData]:
    """Build the accepted-vs-accepted report (markdown, json-able dict).

    ``redline_scores`` are the run's normal scores (tool redline vs Word-oracle redline);
    ``accepted_scores`` diff the ACCEPTED tool output against the ACCEPTED ground truth.
    """
    keys = sorted(set(redline_scores) | set(accepted_scores))
    per_doc: dict[str, dict[str, float | None]] = {}
    for k in keys:
        r = redline_scores.get(k)
        a = accepted_scores.get(k)
        per_doc[k] = {
            "redline_score": r,
            "accepted_score": a,
            "delta": round(a - r, 2) if (a is not None and r is not None) else None,
        }
    data: ReportData = {
        "tool": tool,
        "n_docs": len(keys),
        "aggregate_redline": _agg(redline_scores.values()),
        "aggregate_accepted": _agg(accepted_scores.values()),
        "per_doc": per_doc,
        "accept_failures": accept_failures,
    }

    def fmt(v: float | None) -> str:
        return "—" if v is None else f"{v:.2f}"

    md = [
        f"# accepted-changes comparison — {tool}",
        "",
        "Scores of the tool's redline with ALL changes accepted, diffed against the",
        "accepted ground truth (Word's redline, all changes accepted), next to the",
        "normal redline-vs-redline score.",
        "",
        "| aggregate | redline | accepted |",
        "| --- | ---: | ---: |",
    ]
    aggregate_redline = data["aggregate_redline"]
    aggregate_accepted = data["aggregate_accepted"]
    for m in ("mean", "median", "min", "max", "n"):
        redline_val = aggregate_redline.get(m, "—")  # type: ignore[arg-type]
        accepted_val = aggregate_accepted.get(m, "—")  # type: ignore[arg-type]
        md.append(f"| {m} | {redline_val} | {accepted_val} |")
    md += ["", "| document | redline | accepted | delta |", "| --- | ---: | ---: | ---: |"]
    for k in keys:
        d = per_doc[k]
        md.append(f'| {k} | {fmt(d["redline_score"])} | {fmt(d["accepted_score"])} | {fmt(d["delta"])} |')
    if accept_failures:
        md += ["", f"## accept failures ({len(accept_failures)})", ""]
        md += [f'- `{f["doc"]}`: {f["error"]}' for f in accept_failures]
    return "\n".join(md) + "\n", data


def _accept_compare_stage(
    rc: RunConfig, run_dir: Path, docx_source: Path, per_doc: PerDocScores, accepted_oracle_pdf: Path, use_dpi: int,
) -> BenchmarkOutcome:
    """Copy the freshly generated redlines, accept ALL tracked changes, render, and score
    the accepted copies against the accepted ground truth; write the diff report.
    Returns a :class:`BenchmarkOutcome` with scores, per_doc, failures, and timings
    for the ``accepted_changes`` benchmark.
    """
    from neurotic_docx_bench import accept_changes

    console.print("[bold]accept-compare:[/bold] accepting tracked changes on the generated redlines")
    accepted_dir = run_dir / "accepted_docx"
    results = accept_changes.process_folder(docx_source, accepted_dir, reject=False, jobs=rc.jobs)
    accept_failures = [{"doc": r.source.name, "stage": "accept", "error": r.error} for r in results if not r.ok]
    if accept_failures:
        console.print(f"[yellow]{len(accept_failures)} accept failure(s)[/yellow]")

    report = SofficeRenderer().to_pdfs(accepted_dir, run_dir / "accepted", jobs=rc.jobs)
    if report.fail_count:
        console.print(f"[yellow]{report.fail_count} accepted-render failure(s)[/yellow]")

    accepted_per_doc = pipeline.score_folders_full(
        accepted_oracle_pdf,
        report.pdf_dir,
        run_dir / "accepted_score",
        dpi=use_dpi,
        jobs=rc.jobs,
        candidate_tool=rc.name,
    )
    accepted_scores = {k: _get_overall_score(v) for k, v in accepted_per_doc.items()}
    redline_scores = {k: _get_overall_score(v) for k, v in per_doc.items()}
    md, data = _accepted_report(rc.name, redline_scores, accepted_scores, accept_failures)
    (run_dir / "accepted_report.md").write_text(md)
    (run_dir / "accepted_report.json").write_text(json.dumps(data, indent=2, sort_keys=True))
    _print_accept_compare_table(data)
    console.print(f'accepted report → {run_dir / "accepted_report.md"}')

    # Collect accept-stage failures (accept + render) and timings for the
    # self-contained Results line.
    stage_failures: list[FailureRecord] = list(accept_failures)
    stage_failures.extend(
        {"doc": pipeline.redline_key(r.source.stem, rc.name), "stage": "render", "error": r.error or "render failed"}
        for r in report.results
        if not r.ok
    )
    stage_timings: dict[str, dict[str, float]] = {}
    for r in report.results:
        if r.duration_ns is not None:
            key = pipeline.redline_key(r.source.stem, rc.name)
            stage_timings.setdefault(key, {})["render_s"] = r.duration_ns / 1e9
    for key, result in accepted_per_doc.items():
        entry = stage_timings.setdefault(key, {})
        raster_ns = result.get("raster_ns")
        if raster_ns is not None:
            entry["raster_s"] = float(raster_ns) / 1e9
        score_ns = result.get("score_ns")
        if score_ns is not None:
            entry["score_s"] = float(score_ns) / 1e9

    return BenchmarkOutcome(
        benchmark="accepted_changes",
        scores=accepted_scores,
        per_doc=cast("dict[str, dict[str, object]] | None", accepted_per_doc),
        failures=stage_failures,
        speed_samples_ms=stages.speed_samples_from_timings(stage_timings, "render_s"),
        timings=stage_timings,
    )


def _roundtrip_stage(
    rc: RunConfig, run_dir: Path, roundtrip_oracle_pdf: Path, use_dpi: int, limit: int | None,
) -> BenchmarkOutcome | None:
    """Score the tool's roundtrip output (``out/roundtrip/<tool>/``) against the original
    corpus rendered to PDF — an identity / re-serialization fidelity test. A perfect
    roundtrip (no visual change) scores 100. Returns a :class:`BenchmarkOutcome` with
    scores, per_doc, failures, and timings for the ``roundtrip`` benchmark, or ``None``
    when skipped.
    """
    rt_dir = Path("out/roundtrip") / rc.name
    if not rt_dir.is_dir():
        console.print(f"[yellow]roundtrip: no output for {rc.name} (expected {rt_dir}), skipping[/yellow]")
        return None

    console.print(f"[bold]roundtrip:[/bold] scoring {rc.name} roundtrip fidelity ({rt_dir})")
    rt_source, is_temp = _limited_source(rt_dir, "*.docx", limit)
    try:
        report = SofficeRenderer().to_pdfs(rt_source, run_dir / "roundtrip", jobs=rc.jobs)
        if report.fail_count:
            console.print(f"[yellow]{report.fail_count} roundtrip-render failure(s)[/yellow]")
        per_doc = pipeline.score_folders_plain(
            roundtrip_oracle_pdf, report.pdf_dir, run_dir / "roundtrip_score", dpi=use_dpi, jobs=rc.jobs,
        )
    finally:
        if is_temp:
            shutil.rmtree(rt_source, ignore_errors=True)

    scores = {k: _get_overall_score(v) for k, v in per_doc.items()}
    if scores:
        _print_benchmark_block(
            scores, vendor=rc.name, benchmark="roundtrip",
        )
    else:
        console.print("[yellow]roundtrip: no matched documents scored[/yellow]")
    data = {"tool": rc.name, "n_docs": len(scores), "scores": scores}
    (run_dir / "roundtrip_report.json").write_text(json.dumps(data, indent=2, sort_keys=True))
    console.print(f'roundtrip report → {run_dir / "roundtrip_report.json"}')

    # Collect roundtrip-stage failures and timings for the self-contained Results line.
    stage_failures: list[FailureRecord] = []
    stage_failures.extend(
        {"doc": pipeline.redline_key(r.source.stem, rc.name), "stage": "render", "error": r.error or "render failed"}
        for r in report.results
        if not r.ok
    )
    stage_timings: dict[str, dict[str, float]] = {}
    for r in report.results:
        if r.duration_ns is not None:
            key = pipeline.redline_key(r.source.stem, rc.name)
            stage_timings.setdefault(key, {})["render_s"] = r.duration_ns / 1e9
    for key, result in per_doc.items():
        entry = stage_timings.setdefault(key, {})
        raster_ns = result.get("raster_ns")
        if raster_ns is not None:
            entry["raster_s"] = float(raster_ns) / 1e9
        score_ns = result.get("score_ns")
        if score_ns is not None:
            entry["score_s"] = float(score_ns) / 1e9

    return BenchmarkOutcome(
        benchmark="roundtrip",
        scores=scores,
        per_doc=cast("dict[str, dict[str, object]] | None", per_doc),
        failures=stage_failures,
        speed_samples_ms=stages.speed_samples_from_timings(stage_timings, "render_s"),
        timings=stage_timings,
    )


def _run_generate(cmd: str, run_dir: Path) -> None:
    """Execute a run's ``generate`` command with ``$RUN_DIR`` set; it writes ``$RUN_DIR/docx``."""
    (run_dir / "docx").mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "RUN_DIR": str(run_dir.resolve())}
    console.print(f"generate: {cmd}")
    subprocess.run(cmd, shell=True, cwd=str(Path.cwd()), env=env, check=True, timeout=1800)


def _collect_timings(
    rc: RunConfig, run_dir: Path, report: RenderReport, per_doc: PerDocScores,
) -> dict[str, dict[str, float]]:
    """Assemble per-doc step durations (seconds) from all pipeline stages.

    Steps tracked: ``generate_s`` (from the generator's ``generate_timings.json``),
    ``render_s`` (soffice per-doc), ``raster_s`` and ``score_s`` (pipeline per-doc).
    All measured with ``perf_counter_ns`` / ``process.hrtime.bigint`` and stored as
    float seconds for readability.
    """
    timings: dict[str, dict[str, float]] = {}

    # Generate timings (generator writes $RUN_DIR/generate_timings.json as
    # { "<output_stem>": <nanoseconds> }).
    gen_timings_path = run_dir / "generate_timings.json"
    if gen_timings_path.is_file():
        try:
            gen_timings = json.loads(gen_timings_path.read_text())
            for stem, ns in gen_timings.items():
                key = pipeline.redline_key(stem, rc.name)
                timings.setdefault(key, {})["generate_s"] = float(ns) / 1e9
        except (json.JSONDecodeError, OSError):
            pass

    # Render timings (per-doc duration_ns from RenderReport.results).
    for r in report.results:
        if r.duration_ns is not None:
            key = pipeline.redline_key(r.source.stem, rc.name)
            timings.setdefault(key, {})["render_s"] = r.duration_ns / 1e9

    # Raster + score timings (per-doc from ScoreResult, populated by score_pdf_pair).
    for key, result in per_doc.items():
        entry = timings.setdefault(key, {})
        raster_ns = result.get("raster_ns")
        if raster_ns is not None:
            entry["raster_s"] = float(raster_ns) / 1e9
        score_ns = result.get("score_ns")
        if score_ns is not None:
            entry["score_s"] = float(score_ns) / 1e9

    return timings


def _emit_and_gate_benchmark(
    *,
    benchmark: BenchmarkName,
    rc: RunConfig,
    cfg: BenchConfig,
    tool_version: str | None,
    scores: dict[str, float],
    per_doc: dict[str, dict[str, float | int | bool | list[dict[str, object]] | dict[str, object]]] | None,
    failures: list[FailureRecord],
    timings: dict[str, dict[str, float]],
    speed_key: str,
    jsonl_path: Path,
    snapshots_dir: Path,
    cfg_hash: str,
    id_run: uuid.UUID,
    timestamp: datetime,
    emit: bool,
    only_on_change: bool,
    do_gate: bool,
) -> int:
    """Emit one schema-v4 ``Results`` JSONL line for ``(vendor, benchmark)`` and gate it
    vs the benchmark's snapshot.

    Returns the gate's exit contribution (1 on FAIL, 0 otherwise). Each benchmark
    (``script_redlines``, ``accepted_changes``, ``roundtrip``, …) is its own
    self-contained ``Results`` line keyed by ``vendor``/``benchmark``.
    """
    if not scores:
        return 0
    # A --no-emit run opts out of recording; do not gate against the snapshot
    # on data the user chose not to write (gating is a property of the emitted
    # line, so it only runs alongside emission).
    if not emit:
        return 0
    vendor = rc.vendor or rc.name
    speed_samples_ms = stages.speed_samples_from_timings(timings, speed_key)
    line = jsonl_emit.build_results_line(
        id_run=id_run,
        vendor=vendor,
        benchmark=benchmark,
        scores=scores,
        per_doc=cast("dict[str, dict[str, object]] | None", per_doc),
        speed_samples_ms=speed_samples_ms,
        environment_config=environment_config_for_run(cfg, rc.name),
        timestamp=timestamp,
        tool_version=tool_version,
        config_hash=cfg_hash,
        failures=failures,
        timings=timings,
    )
    appended = (
        jsonl_emit.append_if_changed(jsonl_path, line)
        if only_on_change
        else jsonl_emit.append_line(jsonl_path, line)
    )
    console.print(
        f'jsonl[{benchmark}]: {"appended" if appended else "no change, skipped"} → {jsonl_path}',
    )
    if do_gate:
        baseline = snapshot_emit.load_snapshot_for_benchmark(snapshots_dir, vendor, benchmark)
        result = run_gate(scores, baseline)
        colour = {"pass": "green", "warn": "yellow", "fail": "red"}[result.status]
        console.print(
            f"gate[{benchmark}]: [{colour}]{result.status.upper()}[/{colour}] — {result.reason}",
        )
        if result.regressed_docs:
            console.print("  regressed: " + ", ".join(result.regressed_docs))
        return result.exit_code
    return 0


def _execute_run(
    rc: RunConfig,
    cfg: BenchConfig,
    run_dir: Path,
    *,
    use_dpi: int,
    limit: int | None,
    emit: bool,
    only_on_change: bool,
    do_gate: bool,
    no_update: bool,
    jsonl_path: Path,
    snapshots_dir: Path,
    cfg_hash: str,
    id_run: uuid.UUID,
    timestamp: datetime,
    accept_compare: bool = False,
    accepted_oracle_pdf: Path | None = None,
    roundtrip: bool = False,
    roundtrip_oracle_pdf: Path | None = None,
    stage_cb: Callable[[str, int | None], None] | None = None,
) -> int:
    """Run one tool: (update/resolve version) → generate/locate source → render → score →
    emit → gate. Returns this run's exit contribution (1 on gate FAIL).
    """
    run_dir.mkdir(parents=True, exist_ok=True)

    def _stage(name: str, total: int | None = None) -> None:
        """Notify the outer progress display that stage ``name`` started.

        ``total`` is set once (on the first stage) so the per-run bar is determinate.
        No-op when no progress display is attached (tests, CI, piped output).
        """
        if stage_cb is not None:
            stage_cb(name, total)

    tool_version = tool_updater.resolve_tool_version(
        dist=rc.dist, package=rc.package, python_package=rc.python_package, cwd=Path.cwd(), no_update=no_update,
    )
    if tool_version:
        console.print(f"tool_version: {tool_version}")

    # Locate/produce the candidate source folder.
    if rc.generate:
        _stage("generate")
        _run_generate(rc.generate, run_dir)
        source: Path | None = run_dir / "docx"
        pattern = "*.docx"
    elif rc.render in ("soffice", "playwright"):
        source, pattern = rc.docx, "*.docx"
    else:  # passthrough
        source, pattern = rc.modified, "*.pdf"
    if source is None or not Path(source).is_dir():
        raise RuntimeError(f"source not found: {source}")

    # Progress: count this run's stages so the per-run bar is determinate.
    _n_stages = 2  # setup + render/score (always run)
    if rc.generate:
        _n_stages += 1
    if accept_compare and accepted_oracle_pdf is not None and pattern == "*.docx":
        _n_stages += 1
    if roundtrip and roundtrip_oracle_pdf is not None:
        _n_stages += 1
    _n_visual = len(visual_benchmarks_for_run(rc, cfg.visual_oracles)) if cfg.visual_oracles else 0
    _n_stages += _n_visual
    if emit:
        _n_stages += 1
    _stage("setup", _n_stages)

    roundtrip_outcome: BenchmarkOutcome | None = None
    accept_outcome: BenchmarkOutcome | None = None
    visual_outcomes: list[BenchmarkOutcome] = []
    src_dir, is_temp = _limited_source(Path(source), pattern, limit)
    try:
        _stage("render + score")
        report = _renderer(rc.render, rc.harness).to_pdfs(src_dir, run_dir, jobs=rc.jobs, timeout=rc.timeout)
        if report.fail_count:
            console.print(f"[yellow]{report.fail_count} render failures[/yellow]")
        per_doc = pipeline.score_folders_full(
            cfg.source_of_truth, report.pdf_dir, run_dir / "score", dpi=use_dpi, jobs=rc.jobs, candidate_tool=rc.name,
        )
        if accept_compare and accepted_oracle_pdf is not None:
            if pattern == "*.docx":
                _stage("accept-compare")
                accept_outcome = _accept_compare_stage(rc, run_dir, src_dir, per_doc, accepted_oracle_pdf, use_dpi)
            else:
                console.print("[yellow]accept-compare skipped (no DOCX source for this run)[/yellow]")
        if roundtrip and roundtrip_oracle_pdf is not None:
            _stage("roundtrip")
            roundtrip_outcome = _roundtrip_stage(rc, run_dir, roundtrip_oracle_pdf, use_dpi, limit)
        # Visual benchmarks: re-score the SAME rendered candidate PDFs (already
        # produced by the renderer above) against each visual_* oracle declared on
        # the run. visual_rendering uses the plain-stem matcher (base PDFs); the
        # redlines/accepted variants use the redline-key matcher. Each emits its
        # own JSONL line. This makes rc.benchmarks load-bearing for visual_*.
        # The three visual_* benchmarks share ONE render pass (the ``report``
        # above), so they share its render-speed distribution: build the per-doc
        # ``render_s`` timings once and attach to each outcome.
        vis_render_timings = stages.render_timings_from_report(report, rc.name)
        # visual_* shares the same render pass — attach the same render failures so
        # JSONL does not silently drop them (previous code always set failures=[]).
        vis_render_failures: list[FailureRecord] = [
            {
                "doc": pipeline.redline_key(r.source.stem, rc.name),
                "stage": "render",
                "error": r.error or "render failed",
            }
            for r in report.results
            if not r.ok
        ]
        for vis_name, vis_oracle in visual_benchmarks_for_run(rc, cfg.visual_oracles):
            if not Path(vis_oracle).is_dir():
                console.print(f"[yellow]{vis_name}: oracle {vis_oracle} missing, skipping[/yellow]")
                continue
            _stage(f"visual: {vis_name}")
            if vis_name == "visual_rendering":
                vis_per_doc = pipeline.score_folders_base(
                    Path(vis_oracle), report.pdf_dir, run_dir / f"score_{vis_name}",
                    dpi=use_dpi, jobs=rc.jobs,
                )
            elif vis_name == "visual_accepted_changes":
                vis_per_doc = pipeline.score_folders_accepted(
                    Path(vis_oracle), report.pdf_dir, run_dir / f"score_{vis_name}",
                    dpi=use_dpi, jobs=rc.jobs,
                )
            else:
                vis_per_doc = pipeline.score_folders_full(
                    Path(vis_oracle), report.pdf_dir, run_dir / f"score_{vis_name}",
                    dpi=use_dpi, jobs=rc.jobs, candidate_tool=rc.name,
                )
            vis_scores = {k: _get_overall_score(v) for k, v in vis_per_doc.items()}
            if vis_scores:
                _print_benchmark_block(
                    vis_scores, vendor=rc.vendor or rc.name, benchmark=vis_name,
                )
            if vis_render_failures:
                console.print(
                    f"[yellow]{len(vis_render_failures)} render failure(s) "
                    f"recorded on {vis_name}[/yellow]"
                )
            visual_outcomes.append(BenchmarkOutcome(
                benchmark=vis_name, scores=vis_scores,
                per_doc=cast("dict[str, dict[str, object]] | None", vis_per_doc),
                failures=list(vis_render_failures), speed_samples_ms=[],
                timings=vis_render_timings,
            ))
    finally:
        if is_temp:
            shutil.rmtree(src_dir, ignore_errors=True)

    scores = {k: _get_overall_score(v) for k, v in per_doc.items()}
    _warn_mismatches(per_doc)
    _print_benchmark_block(
        scores, vendor=rc.vendor or rc.name, benchmark="script_redlines",
    )

    # Record which docs did NOT work: generate failures (a generator writes
    # $RUN_DIR/generate_failures.json) + render failures (from the RenderReport).
    failures: list[FailureRecord] = []
    gen_fail = run_dir / "generate_failures.json"
    if gen_fail.is_file():
        try:
            failures.extend(json.loads(gen_fail.read_text()))
        except (json.JSONDecodeError, OSError):
            pass
    failures.extend(
        {"doc": pipeline.redline_key(r.source.stem, rc.name), "stage": "render", "error": r.error or "render failed"}
        for r in report.results
        if not r.ok
    )
    if failures:
        console.print(f"[yellow]{len(failures)} doc(s) recorded as failed in the JSONL[/yellow]")

    timings = _collect_timings(rc, run_dir, report, per_doc)

    # Schema v4: emit one self-contained Results line per benchmark. The primary
    # redline score is "script_redlines"; accept-compare and roundtrip are their
    # own benchmark lines when those flags are enabled.
    worst = 0
    if emit and scores:
        _stage("emit + gate")
        worst = max(worst, _emit_and_gate_benchmark(
            benchmark="script_redlines", rc=rc, cfg=cfg, tool_version=tool_version, scores=scores,
            per_doc=per_doc, failures=failures, timings=timings, speed_key="generate_s",
            jsonl_path=jsonl_path, snapshots_dir=snapshots_dir,
            cfg_hash=cfg_hash, id_run=id_run, timestamp=timestamp,
            emit=emit, only_on_change=only_on_change, do_gate=do_gate,
        ))

    if accept_outcome is not None:
        worst = max(worst, _emit_and_gate_benchmark(
            benchmark=accept_outcome.benchmark, rc=rc, cfg=cfg, tool_version=tool_version,
            scores=accept_outcome.scores,
            per_doc=accept_outcome.per_doc,
            failures=accept_outcome.failures,
            timings=accept_outcome.timings, speed_key="render_s",
            jsonl_path=jsonl_path, snapshots_dir=snapshots_dir,
            cfg_hash=cfg_hash, id_run=id_run, timestamp=timestamp,
            emit=emit, only_on_change=only_on_change, do_gate=do_gate,
        ))

    if roundtrip_outcome is not None:
        worst = max(worst, _emit_and_gate_benchmark(
            benchmark=roundtrip_outcome.benchmark, rc=rc, cfg=cfg, tool_version=tool_version,
            scores=roundtrip_outcome.scores,
            per_doc=roundtrip_outcome.per_doc,
            failures=roundtrip_outcome.failures,
            timings=roundtrip_outcome.timings, speed_key="render_s",
            jsonl_path=jsonl_path, snapshots_dir=snapshots_dir,
            cfg_hash=cfg_hash, id_run=id_run, timestamp=timestamp,
            emit=emit, only_on_change=only_on_change, do_gate=do_gate,
        ))

    for vis_outcome in visual_outcomes:
        # Emit when we have scores *or* failures so a total wipeout still lands
        # a JSONL line documenting why n_docs is 0 (e.g. 176 viewer ArgumentNulls).
        if vis_outcome.scores or vis_outcome.failures:
            worst = max(worst, _emit_and_gate_benchmark(
                benchmark=vis_outcome.benchmark, rc=rc, cfg=cfg, tool_version=tool_version,
                scores=vis_outcome.scores,
                per_doc=vis_outcome.per_doc,
                failures=vis_outcome.failures,
                timings=vis_outcome.timings, speed_key="render_s",
                jsonl_path=jsonl_path, snapshots_dir=snapshots_dir,
                cfg_hash=cfg_hash, id_run=id_run, timestamp=timestamp,
                emit=emit, only_on_change=only_on_change, do_gate=do_gate,
            ))

    # A run succeeds if ANY of its benchmarks produced scores — not just the
    # primary script_redlines score. A visual-only run (e.g. folio-playwright-*)
    # has an empty `scores` (its candidate DOCX aren't redlines) but still emits
    # valid visual_* lines; treating it as failed would discard that work.
    any_scores = bool(scores) or any(o.scores for o in visual_outcomes) \
        or (accept_outcome is not None and accept_outcome.scores) \
        or (roundtrip_outcome is not None and roundtrip_outcome.scores)
    if not any_scores:
        console.print(f"[red]run {rc.name!r}: no documents scored — treating as failed[/red]")
        return 1
    return worst


def _wait_for_url(url: str, timeout_s: float = 30.0, interval_s: float = 0.5) -> bool:
    """Poll ``url`` until it responds with HTTP 200, or until ``timeout_s`` elapses.
    Returns True if the server became reachable, False on timeout.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:  # noqa: S310 — localhost dev server
                if resp.status == 200:
                    return True
        except (URLError, OSError, TimeoutError):
            pass
        time.sleep(interval_s)
    return False


def _start_harness_server(rc: RunConfig) -> subprocess.Popen[bytes] | None:
    """Start the harness dev server for a playwright run (Phase D).

    ``harness.server`` is a shell command; ``harness.url`` is the URL to poll.
    Returns the Popen handle if a server was started, or None if the run has no
    ``harness.server`` (the user is expected to have started it manually, e.g. via
    ``bench serve``).
    """
    if not rc.harness:
        return None
    server_cmd = rc.harness.get("server")
    url = rc.harness.get("url")
    if not server_cmd or not url:
        return None
    console.print(f"[dim]starting harness server for {rc.name}: {server_cmd}[/dim]")
    proc = subprocess.Popen(
        server_cmd,
        shell=True,
        cwd=str(Path.cwd()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    timeout_s = float(rc.harness.get("server_timeout_s", 30))
    if not _wait_for_url(url, timeout_s=timeout_s):
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise RuntimeError(
            f"harness server for {rc.name} did not become ready at {url} within {timeout_s:.0f}s",
        )
    console.print(f"[green]harness server ready[/green] → {url}")
    return proc


def _stop_harness_server(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    console.print("[dim]harness server stopped[/dim]")


def _drive_runs(
    *,
    config: Path,
    names: list[str] | None,
    limit: int | None,
    dpi: int | None,
    results_dir: Path,
    runs_dir: Path,
    clean_runs: bool,
    emit: bool,
    only_on_change: bool,
    do_gate: bool,
    no_update: bool,
    generate: bool,
    accept_compare: bool,
    accepted_oracle_cache: Path,
    roundtrip: bool,
    roundtrip_oracle_cache: Path,
    rerun: bool = False,
) -> None:
    """Shared driver for ``run`` / ``run-all``: execute the selected bench.yaml runs
    sequentially. ``names=None`` runs everything; otherwise the runs execute in the
    given order (deduplicated).
    """
    cfg = load_config(config)
    use_dpi = dpi if dpi is not None else cfg.scoring.dpi
    if os.environ.get("BENCH_CLEAN_RUNS") == "1":
        clean_runs = True
    if os.environ.get("BENCH_NO_UPDATE") == "1":
        no_update = True
    if names:
        by_name = {r.name: r for r in cfg.runs}
        unknown = [n for n in names if n not in by_name]
        if unknown:
            raise typer.BadParameter(
                f'unknown run name(s): {", ".join(unknown)} (available: {", ".join(sorted(by_name))})',
            )
        runs = [by_name[n] for n in dict.fromkeys(names)]
    else:
        runs = list(cfg.runs)
    if not runs:
        raise typer.BadParameter(f"no runs to execute (names={names!r})")

    rid = provenance.run_id()
    cfg_hash = provenance.config_hash(config)
    jsonl_path = results_dir / "bench.jsonl"
    snapshots_dir = results_dir / "score-snapshots"
    worst_exit = 0
    failures: list[str] = []

    if generate:
        if not cfg.generate_scripts:
            console.print("[yellow]--generate: no generate_scripts in the config[/yellow]")
        # Scope the generate scripts to the selected runs: scripts read $BENCH_TOOLS
        # (comma-separated run names) and skip work for tools that aren't running.
        # Scripts that finish with exit code 100 signal "nothing to do" — the CLI
        # suppresses every trace of that script (no rule, no header, no blank line)
        # so the user doesn't see a banner announcing a no-op script invocation
        # (e.g. roundtrips-superdoc when the BENCH_TOOLS scope excludes superdoc).
        gen_env = {k: v for k, v in os.environ.items() if k != "BENCH_TOOLS"}
        if names:
            gen_env["BENCH_TOOLS"] = ",".join(r.name for r in runs)
        for script in cfg.generate_scripts:
            proc = subprocess.run(script.command, shell=True, cwd=str(Path.cwd()), env=gen_env)
            if proc.returncode == 100:
                # Silent no-op scope — the script decided it had no work; stay quiet.
                continue
            console.rule(script.name, align="left")
            if proc.returncode != 0:
                console.print(f"[red]generate '{script.name}' failed (exit {proc.returncode})[/red]")
                worst_exit = max(worst_exit, 1)

    accepted_oracle_pdf: Path | None = None
    if accept_compare:
        agt = cfg.accepted_ground_truth
        if agt is None or not agt.is_dir():
            raise typer.BadParameter(
                "--accept-compare needs 'accepted_ground_truth' in bench.yaml pointing at an "
                "existing folder (produce it with `bench accept … --out …` or `--generate`)",
            )
        console.rule("[bold]accepted ground truth → PDF (cached)[/bold]")
        rep = SofficeRenderer().to_pdfs(agt, accepted_oracle_cache, jobs=8)
        if rep.fail_count:
            console.print(f"[yellow]{rep.fail_count} accepted-oracle render failure(s)[/yellow]")
        accepted_oracle_pdf = rep.pdf_dir

    roundtrip_oracle_pdf: Path | None = None
    if roundtrip:
        rt_corpus = Path("corpus/word_based/word_working_roundtrip")
        if rt_corpus.is_dir():
            console.rule("[bold]roundtrip oracle → PDF (cached)[/bold]")
            rep = SofficeRenderer().to_pdfs(rt_corpus, roundtrip_oracle_cache, jobs=8)
            if rep.fail_count:
                console.print(f"[yellow]{rep.fail_count} roundtrip-oracle render failure(s)[/yellow]")
            roundtrip_oracle_pdf = rep.pdf_dir
        else:
            console.print(f"[yellow]roundtrip: corpus not found at {rt_corpus}, skipping[/yellow]")

    # Dynamic progress: an overall bar across all runs + a per-run bar that advances
    # through its stages (setup → generate → render+score → accept → roundtrip → emit).
    # Only animate on a real interactive terminal so tests (CliRunner capture), CI logs
    # and piped output stay clean — Rich's Live would otherwise redraw over them.
    interactive = sys.stdout.isatty()
    progress: Progress | None = None
    overall_task: TaskID | None = None
    if interactive:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
            redirect_stdout=False,
            redirect_stderr=False,
            transient=False,
        )
        progress.start()
        overall_task = progress.add_task("[bold]Overall bench[/]", total=len(runs))

    for rc in runs:
        console.rule(f"[bold]{rc.name}[/bold]  (render={rc.render})")
        current_task: TaskID | None = None
        if progress is not None:
            current_task = progress.add_task(f"[bold]{rc.name}[/]", total=None)

        def _stage(name: str, total: int | None = None) -> None:
            if progress is not None and current_task is not None:
                if total is not None:
                    progress.update(current_task, total=total)
                progress.update(current_task, description=f"[bold]{rc.name}[/] · {name}")
                progress.advance(current_task)

        if not rerun and not rc.generate and emit:
            tv = tool_updater.resolve_tool_version(
                dist=rc.dist, package=rc.package, python_package=rc.python_package,
                cwd=Path.cwd(), no_update=no_update,
            )
            vendor = rc.vendor or rc.name
            # Skip only when the run's PRIMARY benchmark (script_redlines) already
            # ran with the same (vendor, tool_version, config_hash) identity.
            # Accept-compare/roundtrip share that identity and depend on the
            # primary stage, so a matching script_redlines line implies they were
            # produced from the same generate pass; re-running them would just
            # re-render the same redlines. Runs with no version pin
            # (generate:-only) intentionally never skip — their output may differ.
            prior = jsonl_emit.has_already_ran_benchmark(
                jsonl_path,
                vendor=vendor,
                benchmark="script_redlines",
                tool_version=tv,
                config_hash=cfg_hash,
            )
            if prior is not None:
                console.print(
                    f'[cyan]skip (already ran[/cyan] '
                    f'tool_version={prior.get("tool_version")}, '
                    f'vendor={prior.get("vendor")}, '
                    f'benchmark={prior.get("benchmark")})',
                )
                if progress is not None and overall_task is not None:
                    progress.advance(overall_task)
                if progress is not None and current_task is not None:
                    progress.remove_task(current_task)
                continue

        run_dir = runs_dir / f"{rc.name}_{rid}"
        # Fresh per-run identity for the schema-v4 Results lines.
        id_run = provenance.run_uuid7()
        timestamp = datetime.now(UTC)
        # Phase D: auto-start the harness dev server for playwright runs that
        # declare ``harness.server``. Runs without it (soffice, passthrough, or a
        # manually-started server via ``bench serve``) are unaffected.
        server_proc: subprocess.Popen[bytes] | None = None
        if rc.render == "playwright" and rc.harness and rc.harness.get("server"):
            try:
                server_proc = _start_harness_server(rc)
            except Exception as exc:
                console.print(f"[red]run '{rc.name}' harness server failed:[/red] {exc}")
                failures.append(rc.name)
                worst_exit = max(worst_exit, 1)
                if progress is not None and overall_task is not None:
                    progress.advance(overall_task)
                if progress is not None and current_task is not None:
                    progress.remove_task(current_task)
                continue
        try:
            worst_exit = max(
                worst_exit,
                _execute_run(
                    rc,
                    cfg,
                    run_dir,
                    use_dpi=use_dpi,
                    limit=limit,
                    emit=emit,
                    only_on_change=only_on_change,
                    do_gate=do_gate,
                    no_update=no_update,
                    jsonl_path=jsonl_path,
                    snapshots_dir=snapshots_dir,
                    cfg_hash=cfg_hash,
                    id_run=id_run,
                    timestamp=timestamp,
                    accept_compare=accept_compare,
                    accepted_oracle_pdf=accepted_oracle_pdf,
                    roundtrip=roundtrip,
                    roundtrip_oracle_pdf=roundtrip_oracle_pdf,
                    stage_cb=_stage,
                ),
            )
        except Exception as exc:  # one run's failure must not stop the rest
            console.print(f"[red]run '{rc.name}' FAILED:[/red] {exc}")
            failures.append(rc.name)
            worst_exit = max(worst_exit, 1)
            if clean_runs and run_dir.exists():
                console.print(f"[yellow]kept {run_dir} (run failed before its scores were obtained)[/yellow]")
        else:
            # Clean ONLY at the end of a successful run, after every compare stage
            # (score + accept-compare) has consumed the run's artifacts. The accepted
            # report is preserved into results/ first so --clean-runs doesn't lose it.
            if clean_runs and run_dir.exists():
                for rpt in ("accepted_report.md", "accepted_report.json", "roundtrip_report.json"):
                    src = run_dir / rpt
                    if src.is_file():
                        dest_dir = results_dir / "accepted-reports"
                        dest_dir.mkdir(parents=True, exist_ok=True)
                        _ = shutil.copy(src, dest_dir / f"{rc.name}_{rid}{src.suffix}")
                shutil.rmtree(run_dir, ignore_errors=True)
                console.print(f"cleaned {run_dir}")
        finally:
            _stop_harness_server(server_proc)
        # one run processed (ok or failed) → advance the overall bar and retire the
        # per-run bar (skips & harness failures do their own cleanup before `continue`).
        if progress is not None and overall_task is not None:
            progress.advance(overall_task)
        if progress is not None and current_task is not None:
            progress.remove_task(current_task)

    if progress is not None:
        progress.stop()
    if failures:
        console.print(f'[red]{len(failures)} run(s) failed:[/red] {", ".join(failures)}')
    if worst_exit:
        raise typer.Exit(worst_exit)


@app.command()
def run(
    config: Path = typer.Option(Path("bench.yaml"), "--config", "-c"),
    only: str | None = typer.Option(None, "--only", help="run only this run name"),
    limit: int | None = typer.Option(None, "--limit", help="cap docs per run (for speed)"),
    dpi: int | None = typer.Option(None, "--dpi"),
    results_dir: Path = typer.Option(Path("results"), "--results-dir"),
    runs_dir: Path = typer.Option(Path("runs"), "--runs-dir", help="per-run work folders"),
    clean_runs: bool = typer.Option(
        False,
        "--clean-runs",
        help="delete a run's work folder only at the END of that run, after its scores and "
        "every compare stage (e.g. accept-compare) finished; kept on failure (CI)",
    ),
    no_update: bool = typer.Option(False, "--no-update", help="don't npm-update packaged tools"),
    emit: bool = typer.Option(True, "--emit/--no-emit", help="append a JSONL line per run"),
    only_on_change: bool = typer.Option(
        False, "--only-on-change", help="append only when scores/aggregate changed (delta log)",
    ),
    do_gate: bool = typer.Option(True, "--gate/--no-gate", help="gate vs accepted snapshot"),
    generate: bool = typer.Option(
        False,
        "--generate",
        help="execute the yaml's generate_scripts (roundtrips, accepted corpus, …) before the runs",
    ),
    accept_compare: bool = typer.Option(
        False,
        "--accept-compare/--no-accept-compare",
        help="after generating each tool's redlines, copy them, accept ALL tracked changes, "
        "and score/report vs the accepted ground truth (yaml: accepted_ground_truth)",
    ),
    accepted_oracle_cache: Path = typer.Option(
        Path("out/accepted_oracle"),
        "--accepted-oracle-cache",
        help="cache dir for the rendered accepted ground-truth PDFs",
    ),
    roundtrip: bool = typer.Option(
        False,
        "--roundtrip/--no-roundtrip",
        help="score the tool's roundtrip output (out/roundtrip/<tool>/) against the original "
        "corpus — an identity / re-serialization fidelity test",
    ),
    roundtrip_oracle_cache: Path = typer.Option(
        Path("out/roundtrip_oracle"),
        "--roundtrip-oracle-cache",
        help="cache dir for the rendered roundtrip oracle (original corpus) PDFs",
    ),
    rerun: bool = typer.Option(
        False,
        "--rerun/--no-rerun",
        "-r",
        help="force re-running even if (tool, tool_version, config_hash) already exists in "
        "results/bench.jsonl (env BENCH_RERUN=1 also enables this)",
    ),
) -> None:
    """Drive bench.yaml runs **sequentially** (one per tool). Each run gets its own
    ``runs/{name}_{datetime}`` work folder (kept locally; ``--clean-runs`` deletes it only
    after the run's scores and compare stages complete); a run's failure is recorded and
    the next still runs. Resolves each tool's version, renders → scores → appends a JSONL
    line on change → gates vs the accepted snapshot.

    By default runs that already exist in ``results/bench.jsonl`` (same tool, tool_version,
    and config_hash) are SKIPPED; use ``--rerun`` (or ``BENCH_RERUN=1``) to force them.
    """
    if os.environ.get("BENCH_RERUN"):
        rerun = True
    _drive_runs(
        config=config,
        names=[only] if only else None,
        limit=limit,
        dpi=dpi,
        results_dir=results_dir,
        runs_dir=runs_dir,
        clean_runs=clean_runs,
        no_update=no_update,
        emit=emit,
        only_on_change=only_on_change,
        do_gate=do_gate,
        generate=generate,
        accept_compare=accept_compare,
        accepted_oracle_cache=accepted_oracle_cache,
        roundtrip=roundtrip,
        roundtrip_oracle_cache=roundtrip_oracle_cache,
        rerun=rerun,
    )


@app.command(name="run-all")
def run_all(
    tools: list[str] | None = typer.Argument(
        None,
        help="one or more bench.yaml run names, executed in the given order "
        "(omit and pass --really-all to run every run in the config)",
    ),
    really_all: bool = typer.Option(
        False,
        "--really-all",
        help="run EVERY run in bench.yaml, in config order (makes the positional run names optional)",
    ),
    config: Path = typer.Option(Path("bench.yaml"), "--config", "-c"),
    limit: int | None = typer.Option(None, "--limit", help="cap docs per run (for speed)"),
    dpi: int | None = typer.Option(None, "--dpi"),
    results_dir: Path = typer.Option(Path("results"), "--results-dir"),
    runs_dir: Path = typer.Option(Path("runs"), "--runs-dir", help="per-run work folders"),
    clean_runs: bool = typer.Option(
        False,
        "--clean-runs",
        help="delete a run's work folder only at the END of that run, after its scores and "
        "every compare stage (e.g. accept-compare) finished; kept on failure (CI)",
    ),
    no_update: bool = typer.Option(False, "--no-update", help="don't npm-update packaged tools"),
    emit: bool = typer.Option(True, "--emit/--no-emit", help="append a JSONL line per run"),
    only_on_change: bool = typer.Option(
        False, "--only-on-change", help="append only when scores/aggregate changed (delta log)",
    ),
    do_gate: bool = typer.Option(True, "--gate/--no-gate", help="gate vs accepted snapshot"),
    generate: bool = typer.Option(
        True,
        "--generate/--no-generate",
        help="execute the yaml's generate_scripts (roundtrips, accepted corpus, …) before the runs (default: on)",
    ),
    accept_compare: bool = typer.Option(
        True,
        "--accept-compare/--no-accept-compare",
        help="accept ALL tracked changes on each tool's redlines and score vs the accepted ground truth (default: on)",
    ),
    accepted_oracle_cache: Path = typer.Option(
        Path("out/accepted_oracle"),
        "--accepted-oracle-cache",
        help="cache dir for the rendered accepted ground-truth PDFs",
    ),
    roundtrip: bool = typer.Option(
        True,
        "--roundtrip/--no-roundtrip",
        help="score each tool's roundtrip output (out/roundtrip/<tool>/) against the original "
        "corpus — an identity / re-serialization fidelity test (default: on)",
    ),
    roundtrip_oracle_cache: Path = typer.Option(
        Path("out/roundtrip_oracle"),
        "--roundtrip-oracle-cache",
        help="cache dir for the rendered roundtrip oracle (original corpus) PDFs",
    ),
    rerun: bool = typer.Option(
        False,
        "--rerun/--no-rerun",
        "-r",
        help="force re-running even if (tool, tool_version, config_hash) already exists in "
        "results/bench.jsonl (env BENCH_RERUN=1 also enables this)",
    ),
) -> None:
    """Run the NAMED bench.yaml runs sequentially, in the given order, e.g.
    ``bench run-all jubarte-final-lossless docxodus superdoc``. With ``--really-all``
    the names are optional and EVERY run in bench.yaml executes, in config order.

    By default this runs ALL three benchmark stages per tool with no extra flags:
    (1) redline fidelity (generate → render → score vs Word oracle),
    (2) accept-compare (accept tracked changes → score vs accepted ground truth),
    (3) roundtrip identity (score roundtripped DOCX vs original corpus).

    Generation scripts (roundtrip files, accepted corpus) also run by default and are
    scoped to the named tools ($BENCH_TOOLS), so e.g. roundtrip files are only
    (re)generated for the runs actually executing.
    Use ``--no-accept-compare``, ``--no-roundtrip``, ``--no-generate`` to skip stages.
    Unknown names fail fast listing the available runs.
    """
    if really_all and tools:
        raise typer.BadParameter("--really-all runs every run in bench.yaml; don't also pass run names")
    if not really_all and not tools:
        raise typer.BadParameter("pass one or more bench.yaml run names, or --really-all to run everything")
    if os.environ.get("BENCH_RERUN"):
        rerun = True
    _drive_runs(
        config=config,
        names=None if really_all else tools,
        limit=limit,
        dpi=dpi,
        results_dir=results_dir,
        runs_dir=runs_dir,
        clean_runs=clean_runs,
        no_update=no_update,
        emit=emit,
        only_on_change=only_on_change,
        do_gate=do_gate,
        generate=generate,
        accept_compare=accept_compare,
        accepted_oracle_cache=accepted_oracle_cache,
        roundtrip=roundtrip,
        roundtrip_oracle_cache=roundtrip_oracle_cache,
        rerun=rerun,
    )


@app.command(name="accept-scores")
def accept_scores(
    tool: str = typer.Argument(..., help="vendor/run name to promote to baseline"),
    render: str | None = typer.Option(None, "--render", help="scope to a render backend (legacy v3 lines)"),
    stage: str = typer.Option(
        jsonl_emit.STAGE_REDLINE,
        "--stage",
        help="legacy benchmark stage (redline | accepted | roundtrip); mapped to the "
        "schema-v4 benchmark name. Prefer --benchmark for new baselines.",
    ),
    benchmark: str | None = typer.Option(
        None,
        "--benchmark",
        help="schema-v4 benchmark name to promote "
        "(script_redlines | accepted_changes | roundtrip | visual_rendering | "
        "visual_redlines | visual_accepted_changes)",
    ),
    results_dir: Path = typer.Option(Path("results"), "--results-dir"),
) -> None:
    """Promote a vendor's latest JSONL line to its accepted score snapshot (PLAN §8).

    Schema v4 snapshots live at ``score-snapshots/{vendor}__{benchmark}.json``. The
    benchmark is resolved from ``--benchmark``; if omitted, ``--stage`` is mapped to its
    benchmark name (``redline → script_redlines``, etc.) for back-compat. Both the new
    vendor/benchmark line and any legacy tool/stage line for this run are considered.
    """
    from neurotic_docx_bench.benchmarks import BENCHMARKS, LEGACY_STAGE_TO_BENCHMARK

    # Runtime validation: --benchmark and --stage are free-form strings on the
    # CLI surface (cast('BenchmarkName', ...) is typing-only). Reject unknown
    # values here so a typo (e.g. --benchmark visual_xyz) can't silently write
    # a snapshot under a misspelled filename.
    if benchmark is not None and benchmark not in BENCHMARKS:
        raise typer.BadParameter(
            f'unknown --benchmark {benchmark!r}; known: {", ".join(BENCHMARKS)}',
        )
    if stage not in LEGACY_STAGE_TO_BENCHMARK:
        raise typer.BadParameter(
            f'unknown --stage {stage!r}; known: {", ".join(LEGACY_STAGE_TO_BENCHMARK)}',
        )
    bm: BenchmarkName = cast(
        "BenchmarkName",
        benchmark or LEGACY_STAGE_TO_BENCHMARK.get(stage, "script_redlines"),
    )
    jsonl_path = results_dir / "bench.jsonl"
    # Prefer the schema-v4 vendor/benchmark line; fall back to legacy tool/stage.
    line = jsonl_emit.last_line_for_benchmark(jsonl_path, tool, bm)
    if line is None:
        line = jsonl_emit.last_line_for_tool(jsonl_path, tool, render=render, stage=stage)
    if line is None:
        raise typer.BadParameter(
            f"no JSONL line for vendor {tool!r} benchmark {bm!r} in {jsonl_path}",
        )
    scores = cast("dict[str, float]", line["scores"])
    path = snapshot_emit.write_snapshot_for_benchmark(
        results_dir / "score-snapshots", tool, bm, scores,
    )
    console.print(
        f"accepted {len(scores)} scores for [bold]{tool}[/bold] benchmark={bm} → {path}",
    )


@app.command()
def accept(
    in_folder: Path = typer.Argument(
        ..., help="folder of tracked-change DOCX", exists=True, file_okay=False, dir_okay=True, readable=True,
    ),
    out: Path = typer.Option(..., "--out", help="output folder for accepted copies"),
) -> None:
    """Accept all tracked changes in every DOCX under IN_FOLDER → OUT (docx-revisions)."""
    from neurotic_docx_bench import accept_changes

    results = accept_changes.process_folder(in_folder, out, reject=False)
    ok = sum(1 for r in results if r.ok)
    console.print(f"accepted [green]{ok}[/green]/{len(results)} → {out}")
    for r in results:
        if not r.ok:
            console.print(f"  [red]FAIL[/red] {r.source.name}: {r.error}")
    raise typer.Exit(1 if ok < len(results) else 0)


@app.command()
def reject(
    in_folder: Path = typer.Argument(
        ..., help="folder of tracked-change DOCX", exists=True, file_okay=False, dir_okay=True, readable=True,
    ),
    out: Path = typer.Option(..., "--out", help="output folder for rejected copies"),
) -> None:
    """Reject all tracked changes in every DOCX under IN_FOLDER → OUT (docx-revisions)."""
    from neurotic_docx_bench import accept_changes

    results = accept_changes.process_folder(in_folder, out, reject=True)
    ok = sum(1 for r in results if r.ok)
    console.print(f"rejected [green]{ok}[/green]/{len(results)} → {out}")
    for r in results:
        if not r.ok:
            console.print(f"  [red]FAIL[/red] {r.source.name}: {r.error}")
    raise typer.Exit(1 if ok < len(results) else 0)


@app.command()
def version() -> None:
    """Print the installed package version."""
    from importlib.metadata import version as _v

    typer.echo(_v("neurotic-docx-bench"))


@app.command()
def serve(
    run_name: str = typer.Argument(..., help="bench.yaml run name whose harness server to start"),
    config: Path = typer.Option(Path("bench.yaml"), "--config", "-c"),
) -> None:
    """Start a run's harness dev server in the foreground (dev use, Phase D).

    Reads ``harness.server`` (shell command) from the named run in bench.yaml and runs
    it in the foreground. Use Ctrl+C to stop. During ``bench run`` / ``run-all``, if a
    playwright run declares ``harness.server``, the server is auto-started in the
    background instead — this command is for manual/dev iteration on the harness itself.
    """
    cfg = load_config(config)
    by_name = {r.name: r for r in cfg.runs}
    if run_name not in by_name:
        raise typer.BadParameter(
            f'unknown run name: {run_name!r} (available: {", ".join(sorted(by_name))})',
        )
    rc = by_name[run_name]
    if not rc.harness or not rc.harness.get("server"):
        raise typer.BadParameter(
            f"run {run_name!r} has no harness.server to start "
            "(add a harness.server shell command to bench.yaml)",
        )
    url = rc.harness.get("url", "?")
    cmd = rc.harness["server"]
    console.print(f"[bold]serving {run_name}[/bold] → {url}")
    console.print(f"[dim]command: {cmd}[/dim]")
    console.print("[dim]Ctrl+C to stop[/dim]")
    try:
        subprocess.run(cmd, shell=True, cwd=str(Path.cwd()))
    except KeyboardInterrupt:
        console.print("\n[yellow]stopped[/yellow]")


if __name__ == "__main__":
    app()
