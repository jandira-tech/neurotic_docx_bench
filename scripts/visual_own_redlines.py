"""Viewer-render a lane's OWN generated redline DOCX and score vs the Word oracle.

Extension of the visual_* family for the folio comparison: the standard
visual_redlines renders WORD's redline corpus, which never varies by generator.
This lane renders <run>/docx (a generator's actual output) through ONE fixed
folio viewer harness and scores the pages against the same
corpus/word_based/pdf_redlines_word oracle, so the only variable between lanes
is the generated redline itself.

Usage:
  uv run python scripts/visual_own_redlines.py \
    --docx-dir runs-compare/folio-wasm_<ts>/docx --tool folio-wasm \
    --url http://127.0.0.1:5176/harness.html --out results-compare/visual_own_redlines.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.render.playwright import PlaywrightRenderer

ORACLE = Path("corpus/word_based/pdf_redlines_word")

HARNESS = {
    "file_input": "#fileInput",
    "page_selector": ".layout-page",
    "readiness_js": (
        "window.__folioReady === true || "
        "document.querySelectorAll('.layout-page').length > 0"
    ),
    "timeout_ms": 90000,
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx-dir", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--dpi", type=int, default=144)
    args = ap.parse_args()

    src = Path(args.docx_dir)
    docs = sorted(src.glob("*.docx"))
    if not docs:
        print(f"no docx in {src}")
        return 1

    harness = {**HARNESS, "url": args.url}
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="visual-own.") as work:
        work_dir = Path(work)
        report = PlaywrightRenderer(harness).to_pdfs(src, work_dir, jobs=args.jobs)
        render_s = [
            r.duration_ns / 1e9 for r in report.results if r.ok and r.duration_ns
        ]
        per_doc = pipeline.score_folders_full(
            ORACLE,
            report.pdf_dir,
            work_dir / "score",
            dpi=args.dpi,
            jobs=args.jobs,
            candidate_tool=args.tool,
        )
    # Cross-engine visual render: repagination is endemic, so this stays on the RAW
    # overall_score (NOT pagefair) — same policy as the visual_* benchmarks.
    scores = {key: float(v["overall_score"]) for key, v in per_doc.items()}
    vals = list(scores.values())
    row = {
        "schema": 1,
        "kind": "visual_own_redlines",
        "tool": args.tool,
        "viewer_url": args.url,
        "n_docs": len(vals),
        "render_fail": report.fail_count,
        "mean": round(statistics.fmean(vals), 4) if vals else None,
        "median": round(statistics.median(vals), 4) if vals else None,
        "at_least_90": sum(1 for s in vals if s >= 90),
        "exact_100": sum(1 for s in vals if s >= 99.995),
        "below_50": sum(1 for s in vals if s < 50),
        "render_s_median": round(statistics.median(render_s), 3) if render_s else None,
        "wall_s": round(time.perf_counter() - t0, 1),
        "scores": {k: (round(s, 4) if s is not None else None) for k, s in sorted(scores.items())},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(
        f"{args.tool}: n={row['n_docs']} mean={row['mean']} median={row['median']} "
        f"(>=90: {row['at_least_90']}, =100: {row['exact_100']}) render-fail={row['render_fail']} → {out}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
