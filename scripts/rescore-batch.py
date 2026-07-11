#!/usr/bin/env python3
"""Re-score a batch_to_fix folder against its Word oracle PDFs.

Expects:
  <batch>/candidates/<pair_stem>_redline.docx   (or already-rendered PDFs)
  <batch>/pairs/NN_<pair_stem>/word_oracle_redline.pdf
  <batch>/bottom50.csv                          (baseline scores for deltas)

Writes:
  <batch>/rescore/scores.tsv
  <batch>/rescore/summary.json

Usage:
  uv run python scripts/rescore-batch.py --batch ../jubarte-first/batch_to_fix
  uv run python scripts/rescore-batch.py --batch ../jubarte-rust/batch_to_fix --jobs 8
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]


def _stage_oracles(batch: Path, oracle_dir: Path) -> int:
    oracle_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for pdf in batch.glob("pairs/*/word_oracle_redline.pdf"):
        # pairs/01_<stem>/word_oracle_redline.pdf
        parent = pdf.parent.name  # 01_<stem>
        stem = parent.split("_", 1)[1] if "_" in parent else parent
        # rank is zero-padded 2 digits then underscore
        if len(parent) > 3 and parent[2] == "_":
            stem = parent[3:]
        dest = oracle_dir / f"{stem}_redline.pdf"
        shutil.copy2(pdf, dest)
        n += 1
    return n


def _render_candidates(cand_docx: Path, work: Path, jobs: int) -> Path:
    """Render DOCX candidates → work/pdf via bench render."""
    work.mkdir(parents=True, exist_ok=True)
    cmd = [
        "uv",
        "run",
        "bench",
        "render",
        str(cand_docx),
        str(work),
        "--backend",
        "soffice",
        "--jobs",
        str(jobs),
        "--force",
    ]
    print("[rescore] ", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(BENCH_ROOT), check=True)
    pdf_dir = work / "pdf"
    if not pdf_dir.is_dir():
        raise SystemExit(f"bench render produced no pdf/ under {work}")
    return pdf_dir


def _normalize_candidate_names(pdf_dir: Path, out_dir: Path) -> int:
    """Copy candidate PDFs as <pair_stem>_redline.pdf for match_by_stem.

    Accepts:
      <stem>_redline.pdf
      <stem>_<tool>_redline.pdf
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    tool_suffixes = (
        "_jubarte-final-lossless",
        "_jubarte-final-native",
        "_jubarte-final",
        "_jubarte-rust",
        "_jubarte",
        "_redlines",
        "_docxodus",
        "_folio",
        "_superdoc",
    )
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        s = pdf.stem
        if not s.endswith("_redline"):
            # still copy with _redline so is_redline() accepts it
            key = s
            dest = out_dir / f"{key}_redline.pdf"
        else:
            key = s[: -len("_redline")]
            for sfx in tool_suffixes:
                if key.endswith(sfx):
                    key = key[: -len(sfx)]
                    break
            dest = out_dir / f"{key}_redline.pdf"
        shutil.copy2(pdf, dest)
        n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--batch", type=Path, required=True, help="batch_to_fix directory")
    p.add_argument("--jobs", type=int, default=8)
    p.add_argument("--dpi", type=int, default=144)
    p.add_argument(
        "--pdf-dir",
        type=Path,
        default=None,
        help="skip DOCX render; score this folder of candidate PDFs directly",
    )
    p.add_argument(
        "--only",
        action="append",
        default=[],
        metavar="STEM",
        help=(
            "rescore only this pair_stem (repeatable). Faster one-pair loop: "
            "drop candidates/<stem>_redline.docx then "
            "./rescore.sh --only <stem>"
        ),
    )
    args = p.parse_args(argv)

    batch = args.batch.resolve()
    if not batch.is_dir():
        raise SystemExit(f"batch dir not found: {batch}")

    only: set[str] = {s.strip().lower() for s in args.only if s and s.strip()}

    rescore = batch / "rescore"
    if rescore.exists():
        shutil.rmtree(rescore)
    rescore.mkdir()
    oracle_dir = rescore / "oracle_pdfs"
    cand_norm = rescore / "candidate_pdfs"
    work = rescore / "work"

    n_oracle = _stage_oracles(batch, oracle_dir)
    # When --only is set, keep just those oracle PDFs so score_folders doesn't
    # try to pair every staged oracle against a missing candidate.
    if only:
        kept = 0
        for pdf in list(oracle_dir.glob("*.pdf")):
            # <stem>_redline.pdf
            stem = pdf.stem
            if stem.endswith("_redline"):
                stem = stem[: -len("_redline")]
            if stem.lower() not in only:
                pdf.unlink(missing_ok=True)
            else:
                kept += 1
        n_oracle = kept
        print(f"[rescore] --only filter: {sorted(only)} → {n_oracle} oracle(s)")
    print(f"[rescore] staged {n_oracle} oracle PDFs → {oracle_dir}")

    if args.pdf_dir is not None:
        raw_pdf = args.pdf_dir.resolve()
    else:
        cand_docx = batch / "candidates"
        docs = list(cand_docx.glob("*.docx")) if cand_docx.is_dir() else []
        if only:
            # Only render the requested stems (case-insensitive stem match).
            filtered: list[Path] = []
            for d in docs:
                s = d.stem
                if s.endswith("_redline"):
                    s = s[: -len("_redline")]
                if s.lower() in only:
                    filtered.append(d)
            docs = filtered
        if not docs:
            raise SystemExit(
                f"no DOCX in {cand_docx} matching filter "
                f"(only={sorted(only) or 'ALL'}) — drop <pair_stem>_redline.docx there, "
                "or pass --pdf-dir with already-rendered PDFs"
            )
        # Stage filtered DOCX into a temp dir so bench render only sees them.
        if only:
            slim = work / "docx_only"
            if slim.exists():
                shutil.rmtree(slim)
            slim.mkdir(parents=True)
            for d in docs:
                shutil.copy2(d, slim / d.name)
            raw_pdf = _render_candidates(slim, work, args.jobs)
        else:
            raw_pdf = _render_candidates(cand_docx, work, args.jobs)

    n_cand = _normalize_candidate_names(raw_pdf, cand_norm)
    if only:
        # Drop any normalized PDFs that slipped through (name variants).
        for pdf in list(cand_norm.glob("*.pdf")):
            stem = pdf.stem
            if stem.endswith("_redline"):
                stem = stem[: -len("_redline")]
            if stem.lower() not in only:
                pdf.unlink(missing_ok=True)
        n_cand = len(list(cand_norm.glob("*.pdf")))
    print(f"[rescore] normalized {n_cand} candidate PDFs → {cand_norm}")

    # Import after path setup so `uv run` from bench root resolves the package.
    sys.path.insert(0, str(BENCH_ROOT / "src"))
    from neurotic_docx_bench.pipeline import score_folders

    scores = score_folders(
        oracle_dir,
        cand_norm,
        rescore / "score_work",
        dpi=args.dpi,
        jobs=args.jobs,
        candidate_tool=None,  # already normalized to <stem>_redline.pdf
    )

    baseline: dict[str, float] = {}
    bp = batch / "bottom50.csv"
    if bp.is_file():
        with bp.open() as fh:
            for row in csv.DictReader(fh):
                baseline[row["pair_stem"]] = float(row["score"])

    ranked = sorted(scores.items(), key=lambda kv: (kv[1], kv[0]))
    lines = ["rank\tscore\tpair_stem\tdelta_vs_baseline\n"]
    deltas: list[float] = []
    for i, (stem, sc) in enumerate(ranked, 1):
        base = baseline.get(stem)
        if base is not None:
            d = sc - base
            deltas.append(d)
            delta_s = f"{d:+.4f}"
        else:
            delta_s = ""
        lines.append(f"{i}\t{round(sc, 4)}\t{stem}\t{delta_s}\n")
    (rescore / "scores.tsv").write_text("".join(lines))

    summary = {
        "n_oracle": n_oracle,
        "n_candidates": n_cand,
        "n_scored": len(scores),
        "mean": round(sum(scores.values()) / len(scores), 4) if scores else None,
        "median": None,
        "baseline_mean_of_scored": None,
        "mean_delta": round(sum(deltas) / len(deltas), 4) if deltas else None,
        "scores": {k: round(v, 4) for k, v in ranked},
    }
    if ranked:
        vals = [v for _, v in ranked]
        mid = len(vals) // 2
        summary["median"] = (
            round(vals[mid], 4)
            if len(vals) % 2
            else round((vals[mid - 1] + vals[mid]) / 2, 4)
        )
        base_vals = [baseline[k] for k, _ in ranked if k in baseline]
        if base_vals:
            summary["baseline_mean_of_scored"] = round(sum(base_vals) / len(base_vals), 4)

    (rescore / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: summary[k]
                for k in (
                    "n_scored",
                    "mean",
                    "median",
                    "baseline_mean_of_scored",
                    "mean_delta",
                )
            },
            indent=2,
        )
    )
    print(f"[rescore] wrote {rescore / 'scores.tsv'}")
    return 0 if scores else 1


if __name__ == "__main__":
    raise SystemExit(main())
