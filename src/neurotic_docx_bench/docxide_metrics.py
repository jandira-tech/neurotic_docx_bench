"""``docxide_metrics`` track: docxide-pdf's own fidelity metrics, run here.

A second, independent opinion on the same DOCX→PDF question the
``docx_to_pdf_no_redline_docs`` track already asks. That track scores with the
superdoc-visual-benchmarks core (SSIM + ink-F1 + edge-IoU + colour ΔE + blobs,
fused to one 0–100 number at 144 DPI). This one scores with the three metrics
[sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) uses to judge
itself against Word, at its own 150 DPI:

* **Jaccard** — ink-pixel intersection over union. A pixel is ink when its luma
  is under 200. Placement is everything: a one-line vertical shift drives it
  toward zero.
* **SSIM** — 8×8 windows, ±8px vertical search so small baseline drift is
  forgiven, white windows skipped.
* **Text boundary** — share of lines that begin and end on the same words as
  Word. Ignores where the ink landed; asks only whether the text broke in the
  same places.

Same fixtures, same pinned Word oracles, same intent-to-treat rule as the
existing track — only the scorer differs. Two scorers that disagree about a
converter are telling you something a single number cannot.

The metric code itself is a **verbatim lift** of docxide-pdf's, vendored under
``utils/docxide-metrics/`` (Apache-2.0, credited in the README) and guarded by
``tests/test_docxide_metrics_parity.py``, which requires the same numbers as
upstream's own ``page-metrics`` binary. Nothing here reimplements a metric.
"""

from __future__ import annotations

import json
import shutil
import statistics
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Sequence

from neurotic_docx_bench import docx_to_pdf as d2p

REPO_ROOT = Path(__file__).resolve().parents[2]
SCORER_DIR = REPO_ROOT / "src" / "neurotic_docx_bench" / "utils" / "docxide-metrics"
SCORER_BIN = SCORER_DIR / "target" / "release" / "docxide-metrics"

#: The fixture set this track measures: the 398 source-DOCX pins with Word-export oracles.
FIXTURE_TRACK = "docx_to_pdf_no_redline_docs"

#: Metric keys in report order. `jaccard` is docxide-pdf's headline number and ranks the table.
METRICS = ("jaccard", "ssim", "text_boundary")
METRIC_LABELS = {
    "jaccard": "Jaccard",
    "ssim": "SSIM",
    "text_boundary": "Text boundary",
}

#: docxide-pdf's own per-case pass thresholds (tests/visual_comparison.rs).
JACCARD_THRESHOLD = 20.0
SSIM_THRESHOLD = 75.0

#: Converters this track runs by default.
DEFAULT_TOOLS = ("docxide-pdf", "jubarte")

README_START = "<!-- DOCXIDE-METRICS-START -->"
README_END = "<!-- DOCXIDE-METRICS-END -->"


def ensure_scorer(*, rebuild: bool = False) -> Path:
    """Build the vendored scorer if it is missing or older than its sources."""
    sources = sorted((SCORER_DIR / "src").glob("*.rs")) + [SCORER_DIR / "Cargo.toml"]
    newest = max((p.stat().st_mtime for p in sources if p.is_file()), default=0.0)
    if not rebuild and SCORER_BIN.is_file() and SCORER_BIN.stat().st_mtime >= newest:
        return SCORER_BIN
    print(f"building {SCORER_DIR.name} (cargo build --release)", flush=True)
    subprocess.run(
        ["cargo", "build", "--release"],
        cwd=SCORER_DIR,
        check=True,
    )
    if not SCORER_BIN.is_file():
        raise RuntimeError(f"scorer did not appear at {SCORER_BIN}")
    return SCORER_BIN


def score_candidates(
    fixtures: Sequence[d2p.Fixture],
    candidate_dir: Path,
    scratch: Path,
    out_json: Path,
    *,
    workers: int = 4,
) -> dict[str, dict]:
    """Score one converter's PDFs against the Word oracles. Returns per-stem rows.

    Rasters are written under ``scratch`` and deleted per document by the scorer,
    so peak disk is one document's pages per worker rather than the whole corpus.
    """
    binary = ensure_scorer()
    jobs = [
        {
            "stem": item.stem,
            "oracle": str(item.oracle),
            "candidate": str(candidate_dir / f"{item.stem}.pdf"),
        }
        for item in fixtures
    ]
    out_json.parent.mkdir(parents=True, exist_ok=True)
    jobs_path = out_json.with_suffix(".jobs.json")
    jobs_path.write_text(json.dumps(jobs), encoding="utf-8")
    subprocess.run(
        [
            str(binary),
            "--jobs", str(jobs_path),
            "--scratch", str(scratch),
            "--out", str(out_json),
            "--workers", str(max(1, workers)),
        ],
        check=True,
    )
    rows = json.loads(out_json.read_text(encoding="utf-8"))
    jobs_path.unlink(missing_ok=True)
    shutil.rmtree(scratch, ignore_errors=True)
    return {row["stem"]: row for row in rows}


def _pct(value: float | None) -> float:
    """Scorer emits 0–1; the bench reports 0–100, as docxide-pdf's own viewer does."""
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

    A document that failed to convert scores 0 on all three metrics. So does a
    document that converted but produced no scorable page or no comparable line —
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
    ssim_vals = [per_doc[stem]["ssim"] for stem in stems]
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
        "pass_ssim_75": sum(1 for v in ssim_vals if v >= SSIM_THRESHOLD),
        "per_doc": per_doc,
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
) -> dict:
    """Convert the 398 pinned fixtures with each tool and score them docxide-style."""
    spec = d2p.resolve_track(FIXTURE_TRACK)
    items = d2p.load_fixtures(track=spec)
    if limit is not None:
        items = items[:limit]
    if not items:
        raise RuntimeError("no docxide-metrics fixtures to evaluate")
    d2p.verify_oracle_sha_manifest(track=spec)
    allowed = {d.resolve() for d in d2p.oracle_pdf_dirs(track=spec)}
    for item in items:
        if item.oracle.resolve().parent not in allowed:
            raise RuntimeError(f"oracle {item.oracle} is not in the pinned Word-export folders")

    root = work_dir if work_dir is not None else json_out.parent / "docxide_metrics_work"
    stems = [item.stem for item in items]
    report: dict = {
        "track": "docxide_metrics",
        "fixture_track": spec.name,
        "scorer": "docxide-pdf metrics (Jaccard / SSIM / text boundary)",
        "scorer_upstream": "https://github.com/sverrejb/docxide-pdf",
        "dpi": int(d2p_dpi()),
        "oracle": "microsoft_word",
        "generated_at": datetime.now(UTC).isoformat(),
        "n": len(items),
        "stems": stems,
        "tools": {},
    }

    for tool in tools:
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
            root / tool / "raster",
            root / tool / "scores.json",
            workers=score_workers,
        )
        report["tools"][tool] = _tool_report(
            tool, binary, stems, rows, failures, version=d2p.tool_version(binary),
        )

    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def d2p_dpi() -> str:
    """The DPI baked into the vendored scorer, read from the lifted source."""
    text = (SCORER_DIR / "src" / "metrics.rs").read_text(encoding="utf-8")
    for line in text.splitlines():
        if "MUTOOL_DPI" in line and "=" in line:
            return line.split('"')[1]
    return "150"


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
    dpi = report.get("dpi", 150)
    lines = [
        "### docxide_metrics — DOCX to PDF under docxide-pdf's own metrics",
        "",
        f"The same {n} `docx_to_pdf_no_redline_docs` fixtures and the same pinned Word-export",
        "oracles as the table above, scored instead with the three metrics",
        "[sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) uses to judge itself",
        f"against Word, at its own {dpi} DPI. **Jaccard** is ink-pixel intersection over union",
        "(a pixel is ink when luma < 200) — placement is everything, a one-line shift sends it",
        "toward zero. **SSIM** uses 8×8 windows with a ±8px vertical search, skipping white",
        "windows. **Text boundary** is the share of lines that begin and end on the same words",
        "as Word, ignoring where the ink landed. Ranked by Jaccard median, docxide-pdf's",
        "headline number. Failed converts score 0 on all three (ITT), as does a document that",
        "produced no scorable page. `≥20%` / `≥75%` are docxide-pdf's own per-case pass",
        "thresholds for Jaccard and SSIM.",
        "",
        "| Rank | Tool | Version | n scored | ITT n | Jaccard Mean | Jaccard Median | SSIM Mean | SSIM Median | Text-bnd Mean | Text-bnd Median | Jaccard ≥20% | SSIM ≥75% | Failures |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, (name, data) in enumerate(rows, 1):
        m = data.get("metrics") or {}
        cell = lambda key, stat: f"{float((m.get(key) or {}).get(stat) or 0.0):.2f}"  # noqa: E731
        lines.append(
            f"| {rank} | {name} | {data.get('version') or '—'} | {data.get('n_scored', 0)} | "
            f"{data.get('itt_n', 0)} | {cell('jaccard', 'mean')} | {cell('jaccard', 'median')} | "
            f"{cell('ssim', 'mean')} | {cell('ssim', 'median')} | "
            f"{cell('text_boundary', 'mean')} | {cell('text_boundary', 'median')} | "
            f"{data.get('pass_jaccard_20', 0)} | {data.get('pass_ssim_75', 0)} | "
            f"{data.get('failures', 0)} |",
        )
    return "\n".join(lines) + "\n"


def update_readme(readme: Path, report: dict) -> None:
    """Replace or append the README docxide-metrics block."""
    block = f"{README_START}\n{render_table(report)}{README_END}"
    text = readme.read_text(encoding="utf-8")
    if README_START in text and README_END in text:
        start = text.index(README_START)
        end = text.index(README_END) + len(README_END)
        text = text[:start] + block + text[end:]
    elif d2p.NO_REDLINE_TRACK.readme_end in text:
        anchor = d2p.NO_REDLINE_TRACK.readme_end
        text = text.replace(anchor, anchor + "\n\n" + block, 1)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    readme.write_text(text, encoding="utf-8")
