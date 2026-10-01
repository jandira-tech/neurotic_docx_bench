"""``docxide_metrics`` track: docxide-pdf's own fidelity metrics, run here.

A second, independent opinion on the same DOCX to PDF question the
``docx_to_pdf_no_redline_docs`` track already asks. That track scores with the
superdoc-visual-benchmarks core (SSIM + ink-F1 + edge-IoU + colour dE + blobs,
fused to one 0-100 number at 144 DPI). This one scores with the metrics
[sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) uses to judge
itself against Word, at its own 150 DPI:

* **Jaccard**: ink-pixel intersection over union. A pixel is ink when its luma
  is under 200. Placement is everything: a one-line vertical shift drives it
  toward zero.
* **Text boundary**: share of lines that begin and end on the same words as
  Word. Ignores where the ink landed; asks only whether the text broke in the
  same places.

docxide's SSIM is not carried: pagefair-v2 already scores SSIM (at 40% weight)
on the same rasters, and a second SSIM at a different DPI answered nothing the
first did not.

Same fixtures, same pinned Word oracles, same intent-to-treat rule as the
existing track; only the scorer differs. Two scorers that disagree about a
converter are telling you something a single number cannot.

The metrics are ``page_metrics.py``, a Python port of docxide-pdf's
``tests/common`` (Apache-2.0, credited in the README), held to upstream's frozen
numbers by ``tests/test_page_metrics.py``. Since 0.7.0 the same columns also ride
on every ``pipeline.score_pdf_pair`` row, so a redline run carries them without a
second pass; this track is the converter-only view over the 398 fixtures.
"""

from __future__ import annotations

import asyncio
import json
import statistics
import time
from collections.abc import Sequence
from concurrent.futures import ProcessPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from neurotic_docx_bench import docx_to_pdf as d2p
from neurotic_docx_bench import page_metrics as pm

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The fixture set this track measures: the 398 source-DOCX pins with Word-export oracles.
FIXTURE_TRACK = "docx_to_pdf_no_redline_docs"

#: docxide-pdf rasterizes at 150 DPI; the track's numbers are only comparable at that DPI.
DPI = pm.UPSTREAM_DPI

#: Metric keys in report order. `jaccard` is docxide-pdf's headline number and ranks the table.
METRICS = ("jaccard", "text_boundary")
METRIC_LABELS = {
    "jaccard": "Jaccard",
    "text_boundary": "Text boundary",
}

#: docxide-pdf's own per-case Jaccard pass threshold (tests/visual_comparison.rs).
JACCARD_THRESHOLD = 20.0

#: Converters this track runs by default.
DEFAULT_TOOLS = ("docxide-pdf", "jubarte")

README_START = "<!-- DOCXIDE-METRICS-START -->"
README_END = "<!-- DOCXIDE-METRICS-END -->"


def _score_job(job: tuple[str, str, str]) -> dict:
    stem, oracle, candidate = job
    row = pm.score_pair(Path(oracle), Path(candidate), dpi=DPI).as_row()
    return {"stem": stem, **row}


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _signature(job: tuple[str, str, str]) -> str:
    """Identity of one scoring job: the two PDFs' sizes and the scorer's DPI."""
    _stem, oracle, candidate = job
    size = lambda p: Path(p).stat().st_size if Path(p).is_file() else -1  # noqa: E731 (a missing PDF scores as failed)
    return f"{size(oracle)}:{size(candidate)}:{DPI}"


async def _load_checkpoint(path: Path) -> dict[str, dict]:
    held: dict[str, dict] = {}
    if not path.is_file():
        return held
    async with aiofiles.open(path, encoding="utf-8") as fh:
        async for line in fh:
            try:
                held_row = json.loads(line)
            except json.JSONDecodeError:
                continue  # a line cut short by a kill
            held[held_row["stem"]] = held_row
    return held


async def _score_async(jobs: list[tuple[str, str, str]], workers: int, checkpoint: Path) -> list[dict]:
    total = len(jobs)
    started = time.monotonic()
    held = await _load_checkpoint(checkpoint)
    sigs = {job[0]: _signature(job) for job in jobs}
    rows: dict[str, dict] = {
        stem: held[stem]["row"] for stem in sigs if stem in held and held[stem]["sig"] == sigs[stem]
    }
    todo = [job for job in jobs if job[0] not in rows]
    print(f"{_now()} docxide metrics started, {total} documents ({len(rows)} from checkpoint, {len(todo)} to score)", flush=True)
    done = len(rows)

    async def record(sink, row: dict) -> None:
        nonlocal done
        done += 1
        rows[row["stem"]] = row
        await sink.write(json.dumps({"stem": row["stem"], "sig": sigs[row["stem"]], "scored_at": _now(), "row": row}) + "\n")
        await sink.flush()
        elapsed = time.monotonic() - started
        jac = row.get("jaccard")
        shown = "  n/a" if jac is None else f"{jac * 100:5.1f}"
        print(
            f"{_now()} [{done}/{total}] {done / total:6.1%} jaccard {shown}  {row['stem']}  "
            f"(elapsed {elapsed:.0f}s, eta {elapsed / done * (total - done):.0f}s)",
            flush=True,
        )

    if todo:
        checkpoint.parent.mkdir(parents=True, exist_ok=True)
        loop = asyncio.get_running_loop()
        async with aiofiles.open(checkpoint, "a", encoding="utf-8") as sink:
            if workers <= 1:
                for job in todo:
                    await record(sink, _score_job(job))
            else:
                with ProcessPoolExecutor(max_workers=workers) as pool:
                    for fut in asyncio.as_completed([loop.run_in_executor(pool, _score_job, job) for job in todo]):
                        await record(sink, await fut)
    return [rows[job[0]] for job in jobs]  # input order


def score_candidates(
    fixtures: Sequence[d2p.Fixture],
    candidate_dir: Path,
    out_json: Path,
    *,
    workers: int = 4,
) -> dict[str, dict]:
    """Score one converter's PDFs against the Word oracles. Returns per-stem rows.

    Each worker rasterizes one document in memory and drops the rasters before the
    next, so peak memory is one document's pages per worker. Every scored document is
    appended to ``<out_json stem>.docxide.checkpoint.jsonl`` as it finishes (aiofiles) and a
    rerun scores only the documents that file does not hold; one progress line per
    document carries a UTC stamp.
    """
    jobs = [
        (item.stem, str(item.oracle), str(candidate_dir / f"{item.stem}.pdf"))
        for item in fixtures
    ]
    rows = asyncio.run(_score_async(jobs, workers, out_json.with_name(f"{out_json.stem}.docxide.checkpoint.jsonl")))
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return {row["stem"]: row for row in rows}


def _pct(value: float | None) -> float:
    """Metrics are 0-1; the bench reports 0-100, as docxide-pdf's own viewer does."""
    return 0.0 if value is None else round(value * 100.0, 4)


def _tool_report(
    tool: str,
    binary: Path | None,
    stems: list[str],
    rows: dict[str, dict],
    failures: list[dict[str, object]],
    *,
    version: str | None = None,
) -> dict:
    """ITT report for one converter.

    A document that failed to convert scores 0 on both metrics. So does a
    document that converted but produced no scorable page or no comparable line:
    a PDF that shares nothing with Word's has zero fidelity, and keeping every
    metric's denominator at the full fixture count is what makes the columns
    comparable across tools. ``n_scored`` counts documents that produced a real
    number, so the gap between it and ``itt_n`` is always visible.
    """
    failed = {str(item["doc"]) for item in failures}
    per_doc: dict[str, dict[str, float]] = {}
    scored = 0
    mismatched_pages = 0
    for stem in stems:
        row = rows.get(stem) or {}
        if row.get("converted") and row.get("jaccard") is not None:
            scored += 1
            if row.get("ref_pages") != row.get("pages"):
                mismatched_pages += 1
        per_doc[stem] = {key: _pct(row.get(key)) for key in METRICS}

    metrics: dict[str, dict[str, float | int]] = {}
    for key in METRICS:
        vals = [per_doc[stem][key] for stem in stems]
        metrics[key] = {
            "mean": round(statistics.mean(vals), 4) if vals else 0.0,
            "median": round(statistics.median(vals), 4) if vals else 0.0,
            "min": round(min(vals), 4) if vals else 0.0,
            "max": round(max(vals), 4) if vals else 0.0,
        }
    jaccard_vals = [per_doc[stem]["jaccard"] for stem in stems]
    return {
        "tool": tool,
        "binary": None if binary is None else str(binary),
        "version": version,
        "n_scored": scored,
        "itt_n": len(stems),
        "failures": len(failed),
        "page_count_mismatch": mismatched_pages,
        "metrics": metrics,
        "pass_jaccard_20": sum(1 for v in jaccard_vals if v >= JACCARD_THRESHOLD),
        "per_doc": per_doc,
        # Converted, but no number (no scorable page): 0 in per_doc like a failure.
        "unscored_docs": [
            stem for stem in stems
            if stem not in failed
            and not ((rows.get(stem) or {}).get("converted") and (rows.get(stem) or {}).get("jaccard") is not None)
        ],
        "generate_failures": failures,
    }


def run_eval(
    json_out: Path,
    *,
    tools: Sequence[str] = DEFAULT_TOOLS,
    converter: Path | None = None,
    work_dir: Path | None = None,
    limit: int | None = None,
    resume: bool = True,
    convert_workers: int = 8,
    score_workers: int = 4,
    fixtures: Sequence[d2p.Fixture] | None = None,
    check_pins: bool = True,
    score_only: bool = False,
    candidates: dict[str, Path] | None = None,
    warnings: Sequence[str] | None = None,
    fixture_track: str | None = None,
) -> dict:
    """Convert the pinned fixtures with each tool and score them docxide-style.

    Corpus selections pass ``fixtures`` and ``check_pins=False``. ``score_only``
    skips every converter and scores ``candidates`` (fixture stem to PDF).
    """
    if fixtures is None:
        spec = d2p.resolve_track(FIXTURE_TRACK)
        items = d2p.load_fixtures(track=spec)
    else:
        spec = d2p.resolve_track(FIXTURE_TRACK) if check_pins else None
        items = list(fixtures)
    if limit is not None:
        items = items[:limit]
    if not items:
        raise RuntimeError("no docxide-metrics fixtures to evaluate")
    if check_pins:
        if spec is None:
            spec = d2p.resolve_track(FIXTURE_TRACK)
        d2p.verify_oracle_sha_manifest(track=spec)
        allowed = {d.resolve() for d in d2p.oracle_pdf_dirs(track=spec)}
        for item in items:
            if item.oracle.resolve().parent not in allowed:
                raise RuntimeError(f"oracle {item.oracle} is not in the pinned Word-export folders")

    root = work_dir if work_dir is not None else json_out.parent / "docxide_metrics_work"
    stems = [item.stem for item in items]
    report: dict = {
        "track": "docxide_metrics",
        "fixture_track": spec.name if spec is not None else (fixture_track or "corpus/word"),
        "scorer": "docxide-pdf metrics (Jaccard / text boundary), page_metrics.py port",
        "scorer_upstream": "https://github.com/sverrejb/docxide-pdf",
        "dpi": DPI,
        "oracle": "microsoft_word",
        "generated_at": datetime.now(UTC).isoformat(),
        "n": len(items),
        "stems": stems,
        "warnings": list(warnings or []),
        "tools": {},
    }

    for tool in tools:
        if score_only:
            print(f"scoring {tool} with docxide-pdf metrics ({len(items)} docs)", flush=True)
            cand_dir = root / tool / "candidate"
            failures = d2p.stage_candidates(items, candidates or {}, cand_dir)
            present = [
                item for item in items
                if (cand_dir / f"{item.stem}.pdf").is_file()
            ]
            rows = (
                score_candidates(present, cand_dir, root / tool / "scores.json", workers=score_workers)
                if present
                else {}
            )
            report["tools"][tool] = _tool_report(
                tool, None, stems, rows, failures, version=None,
            )
            continue
        print(f"converting with {tool} ({len(items)} docs)", flush=True)
        try:
            binary: Path | None = d2p.resolve_tool_binary(
                tool, converter if len(list(tools)) == 1 else None,
            )
        except FileNotFoundError as exc:
            report["tools"][tool] = _tool_report(
                tool,
                None,
                stems,
                {},
                [
                    {"doc": item.stem, "stage": "generate", "error": str(exc), "cmd": [tool]}
                    for item in items
                ],
            )
            continue
        cand_dir = root / tool / "candidate"
        failures = d2p.try_convert_fixtures(
            tool, binary, items, cand_dir, resume=resume, workers=convert_workers,
        )
        print(f"scoring {tool} with docxide-pdf metrics ({len(items)} docs)", flush=True)
        rows = score_candidates(
            items,
            cand_dir,
            root / tool / "scores.json",
            workers=score_workers,
        )
        report["tools"][tool] = _tool_report(
            tool, binary, stems, rows, failures, version=d2p.tool_version(binary),
        )

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def render_table(report: dict) -> str:
    """Markdown table for the README, ranked by Jaccard median."""
    tools = report.get("tools") or {}
    rows = sorted(
        tools.items(),
        key=lambda kv: (
            -float(((kv[1].get("metrics") or {}).get("jaccard") or {}).get("median") or 0.0),
            -float(((kv[1].get("metrics") or {}).get("jaccard") or {}).get("mean") or 0.0),
            kv[0],
        ),
    )
    n = report.get("n", "")
    dpi = report.get("dpi", DPI)
    lines = [
        "### docxide_metrics: DOCX to PDF under docxide-pdf's own metrics",
        "",
        f"The same {n} `docx_to_pdf_no_redline_docs` fixtures and the same pinned Word-export",
        "oracles as the table above, scored instead with the metrics",
        "[sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) uses to judge itself",
        f"against Word, at its own {dpi} DPI. **Jaccard** is ink-pixel intersection over union",
        "(a pixel is ink when luma < 200): placement is everything, a one-line shift sends it",
        "toward zero. **Text boundary** is the share of lines that begin and end on the same words",
        "as Word, ignoring where the ink landed. Ranked by Jaccard median, docxide-pdf's",
        "headline number. Failed converts score 0 on both (ITT), as does a document that",
        "produced no scorable page. `>=20%` is docxide-pdf's own per-case Jaccard pass",
        "threshold. docxide's SSIM is not carried; pagefair-v2 scores SSIM on the same rasters.",
        "",
        "| Rank | Tool | Version | n scored | ITT n | Jaccard Mean | Jaccard Median | Text-bnd Mean | Text-bnd Median | Jaccard >=20% | Failures |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, (name, data) in enumerate(rows, 1):
        m = data.get("metrics") or {}

        def cell(key: str, stat: str, m: dict = m) -> str:
            return f"{float((m.get(key) or {}).get(stat) or 0.0):.2f}"

        lines.append(
            f"| {rank} | {name} | {data.get('version') or 'n/a'} | {data.get('n_scored', 0)} | "
            f"{data.get('itt_n', 0)} | {cell('jaccard', 'mean')} | {cell('jaccard', 'median')} | "
            f"{cell('text_boundary', 'mean')} | {cell('text_boundary', 'median')} | "
            f"{data.get('pass_jaccard_20', 0)} | "
            f"{data.get('failures', 0)} |",
        )
    return "\n".join(lines) + "\n"
