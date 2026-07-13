#!/usr/bin/env python3
"""Score jubarte-rs-probe PDFs against the Word oracle and emit an HTML gallery report.

Standalone: matches by <base>_<next> key (pipeline.redline_key), rasterizes
both sides, scores pixel-wise (pipeline.score_folders_full), then builds a
worst-first candidate-vs-oracle HTML report (html_report.generate_html_report).
"""
from __future__ import annotations

import json
from pathlib import Path

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.html_report import DocumentReportInput, generate_html_report

REPO = Path(__file__).resolve().parent.parent
ORACLE_DIR = REPO / "corpus_sanity" / "word_based" / "pdf_redlines_word"
CANDIDATE_DIR = REPO / "jubarte-rs-probe" / "pdf"
WORK_DIR = REPO / "jubarte-rs-probe" / "score"
REPORT_DIR = REPO / "jubarte-rs-probe" / "report"
TOOL = "jubarte-rust"
JOBS = 8
DPI = 144


def main() -> None:
    ORACLE_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATE_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    pairs = pipeline.match_by_stem(
        ORACLE_DIR,
        CANDIDATE_DIR,
        candidate_tool=TOOL,
    )
    oracle_only, candidate_only = pipeline.coverage(
        ORACLE_DIR,
        CANDIDATE_DIR,
        candidate_tool=TOOL,
    )
    print(f"matched pairs: {len(pairs)}")
    print(f"oracle-only (no candidate): {len(oracle_only)}")
    print(f"candidate-only (no oracle): {len(candidate_only)}")
    if oracle_only:
        for k in sorted(oracle_only)[:10]:
            print(f"  oracle-only: {k}")
    if candidate_only:
        for k in sorted(candidate_only)[:10]:
            print(f"  candidate-only: {k}")

    results = pipeline.score_folders_full(
        ORACLE_DIR,
        CANDIDATE_DIR,
        WORK_DIR,
        dpi=DPI,
        jobs=JOBS,
        candidate_tool=TOOL,
    )

    # Persist raw scores
    scores_path = WORK_DIR / "scores.json"
    scores_path.write_text(
        json.dumps(results, indent=2, default=str, sort_keys=True),
        encoding="utf-8",
    )

    # Summary stats
    scores = sorted(
        (k, v["overall_score"]) for k, v in results.items()
    )
    values = [s for _, s in scores]
    if values:
        import statistics
        print()
        print("=== Score summary ===")
        print(f"  n_docs:   {len(values)}")
        print(f"  mean:     {statistics.mean(values):.2f}")
        print(f"  median:   {statistics.median(values):.2f}")
        print(f"  min:      {min(values):.2f}")
        print(f"  max:      {max(values):.2f}")
        print(f"  stdev:    {statistics.stdev(values):.2f}" if len(values) > 1 else "")
        print(f"  exact_100: {sum(1 for v in values if v >= 99.99)}")
        print(f"  >=90:      {sum(1 for v in values if v >= 90)}")
        print(f"  <50:       {sum(1 for v in values if v < 50)}")
        print()
        print("worst 10:")
        for k, s in scores[:10]:
            print(f"  {s:7.2f}  {k}")

    # Build HTML gallery report (worst-first)
    documents: list[DocumentReportInput] = []
    for key, result in sorted(results.items(), key=lambda kv: kv[1]["overall_score"]):
        oracle_pages_dir = WORK_DIR / key / "oracle"
        cand_pages_dir = WORK_DIR / key / "candidate"
        oracle_pages = sorted(oracle_pages_dir.glob("page_*.png")) if oracle_pages_dir.exists() else []
        cand_pages = sorted(cand_pages_dir.glob("page_*.png")) if cand_pages_dir.exists() else []
        score_file = WORK_DIR / key / "score.json"
        score_file.write_text(
            json.dumps(result, indent=2, default=str),
            encoding="utf-8",
        )
        documents.append(DocumentReportInput(
            name=key,
            word_pages=oracle_pages,
            jubarte_pages=cand_pages,
            assets_dir=REPORT_DIR / key,
            score_path=score_file,
        ))

    if documents:
        report_path = generate_html_report(
            documents=documents,
            version_label=f"{TOOL} (probe)",
            report_dir=REPORT_DIR,
            run_label=f"{TOOL}-probe",
        )
        print(f"\nHTML report: {report_path}")


if __name__ == "__main__":
    main()
