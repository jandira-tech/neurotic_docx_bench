#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
#
# SPDX-License-Identifier: AGPL-3.0-only

"""Score jubarte redlines on a fixed 40-pair sample against Word's redlines.

The quality guard for the 0.10.0 goal (docs/goals/0.10.0.md). It runs the
neurotic_docx_bench `script_redlines` scorer on a seeded sample of the
bench's three pools. Word's redline DOCX and ours are both rendered by the
local LibreOffice, so a LibreOffice upgrade moves both sides together and
the score isolates markup (the committed oracle PDFs were rendered by an
older build).

Run from the repository root, inside the bench's environment:

    uv run --project ../neurotic_docx_bench python tools/redline40/redline40.py pick
    uv run --project ../neurotic_docx_bench python tools/redline40/redline40.py run --label baseline
    uv run --project ../neurotic_docx_bench python tools/redline40/redline40.py run --label after-x --against baseline

`pick` writes sample.tsv once; later runs reuse it. `run` appends one JSON
line per run to runs.jsonl. With `--against`, a pair that drops more than
--max-drop points or a mean that drops more than --max-mean-drop is a
regression (exit 1). A jubarte failure scores 0.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import random
import shutil
import statistics as st
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
BENCH = Path(os.environ.get("BENCH_DIR", REPO.parent / "neurotic_docx_bench"))
SAMPLE = HERE / "sample.tsv"
RUNS = HERE / "runs.jsonl"
ORACLE_CACHE = HERE / ".oracle_pdf"

# (pool, manifest, source dir, Word redline dir)
POOLS = [
    ("word_based", "corpus/word_based/centralized_mapping.csv",
     "corpus/word_based/docx_source", "corpus/word_based/docx_redlines_word"),
    ("word_based_randomized", "corpus/word_based/centralized_mapping_randomized.csv",
     "corpus/word_based/docx_source_randomized", "corpus/word_based/docx_redlines_randomized"),
    ("word_redlines_superdoc", "corpus/word_redlines_superdoc/centralized_mapping.csv",
     "corpus/word_redlines_superdoc/docx_source", "corpus/word_redlines_superdoc/docx_redlines_word"),
]


def candidates() -> list[dict]:
    holdout = {l.strip() for l in (BENCH / "corpus/holdout_combined.txt").read_text().splitlines() if l.strip()}
    blacklist = BENCH / "grok_run/word_blacklist/blacklist.tsv"
    banned = set()
    if blacklist.is_file():
        banned = {l.split("\t")[0].strip() for l in blacklist.read_text().splitlines() if l.strip()}
    rows = []
    for pool, manifest, src, red in POOLS:
        for r in csv.DictReader((BENCH / manifest).open(encoding="utf-8")):
            stem = r["pair_stem"]
            if stem in holdout or stem in banned:
                continue
            word = r.get("redline_docx_word") or r.get("redline_docx") or ""
            paths = {
                "base": BENCH / src / r["docx_source_base"],
                "next": BENCH / src / r["docx_source_next"],
                "word": BENCH / red / word,
            }
            if not word or not all(p.is_file() for p in paths.values()):
                continue
            rows.append({"pool": pool, "stem": stem, **{k: str(v.relative_to(BENCH)) for k, v in paths.items()}})
    return rows


def pick(args) -> int:
    if SAMPLE.exists() and not args.force:
        print(f"{SAMPLE} exists; pass --force to redraw", file=sys.stderr)
        return 2
    pool = candidates()
    chosen = sorted(random.Random(args.seed).sample(pool, args.n), key=lambda r: (r["pool"], r["stem"]))
    with SAMPLE.open("w", encoding="utf-8") as f:
        f.write(f"# seed={args.seed} n={args.n} drawn from {len(pool)} pairs (holdout and Word blacklist excluded)\n")
        f.write("pool\tstem\tbase\tnext\tword\n")
        for r in chosen:
            f.write("\t".join(r[k] for k in ("pool", "stem", "base", "next", "word")) + "\n")
    print(f"wrote {SAMPLE}: {len(chosen)} of {len(pool)}")
    return 0


def load_sample() -> list[dict]:
    lines = [l for l in SAMPLE.read_text(encoding="utf-8").splitlines() if l and not l.startswith("#")]
    head = lines[0].split("\t")
    return [dict(zip(head, l.split("\t"))) for l in lines[1:]]


def soffice_pdf(docxs: list[Path], outdir: Path) -> None:
    """Render a batch of DOCX files to PDF with the local LibreOffice."""
    if not docxs:
        return
    outdir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="r40_lo_"))
    try:
        subprocess.run(
            ["soffice", f"-env:UserInstallation=file://{profile}", "--headless",
             "--convert-to", "pdf", "--outdir", str(outdir), *map(str, docxs)],
            capture_output=True, text=True, timeout=1800, check=False,
        )
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def soffice_version() -> str:
    p = subprocess.run(["soffice", "--version"], capture_output=True, text=True, check=False)
    return p.stdout.strip().split("\n")[0]


def run(args) -> int:
    sys.path.insert(0, str(BENCH / "src"))
    from neurotic_docx_bench.pipeline import score_pdf_pair  # noqa: PLC0415

    jubarte = Path(args.bin).resolve()
    if not jubarte.is_file():
        print(f"missing binary {jubarte}; cargo build --release", file=sys.stderr)
        return 2
    # Pick the baseline before this run is appended, so a run can never be
    # its own baseline (same label, or a later run reusing the label).
    base = None
    if args.against:
        if args.against == args.label:
            print(f"--label and --against are both {args.label!r}", file=sys.stderr)
            return 2
        for l in RUNS.read_text(encoding="utf-8").splitlines() if RUNS.exists() else []:
            rec = json.loads(l)
            if rec["label"] == args.against:
                base = rec
        if base is None:
            print(f"no run labelled {args.against!r}", file=sys.stderr)
            return 2
    rows = load_sample()
    work = Path(tempfile.mkdtemp(prefix="redline40_"))
    try:
        ours_dir, ours_pdf = work / "docx", work / "pdf"
        ours_dir.mkdir()
        failed: dict[str, str] = {}
        for r in rows:
            out = ours_dir / f"{r['stem']}.docx"
            p = subprocess.run([str(jubarte), str(BENCH / r["base"]), str(BENCH / r["next"]),
                                "-o", str(out), "--force", "--quiet"],
                               capture_output=True, text=True, timeout=300, check=False)
            if p.returncode != 0 or not out.is_file():
                failed[r["stem"]] = (p.stderr or p.stdout).strip()[-300:]
        soffice_pdf(sorted(ours_dir.glob("*.docx")), ours_pdf)

        # Word's redline, rendered once per LibreOffice build and cached by stem.
        cache = ORACLE_CACHE / soffice_version().replace(" ", "_")
        todo, staged = [], work / "oracle_docx"
        staged.mkdir()
        for r in rows:
            if not (cache / f"{r['stem']}.pdf").is_file():
                dst = staged / f"{r['stem']}.docx"
                shutil.copyfile(BENCH / r["word"], dst)
                todo.append(dst)
        soffice_pdf(todo, cache)

        per: dict[str, dict] = {}
        for r in rows:
            stem = r["stem"]
            cand, oracle = ours_pdf / f"{stem}.pdf", cache / f"{stem}.pdf"
            if stem in failed or not cand.is_file():
                per[stem] = {"score": 0.0, "error": failed.get(stem, "no PDF from LibreOffice")}
                continue
            if not oracle.is_file():
                per[stem] = {"score": None, "error": "oracle did not render"}
                continue
            res = score_pdf_pair(oracle, cand, work / "score", key=stem)
            per[stem] = {
                "score": round(float(res["overall_score_pagefair"]), 3),
                "raw": round(float(res["overall_score"]), 3),
                "ink_jaccard": round(float(res.get("ink_jaccard") or 0.0), 4),
                "text_boundary": round(float(res.get("text_boundary") or 0.0), 2),
                "pages": [res["page_count_oracle"], res["page_count_candidate"]],
            }
            shutil.rmtree(work / "score" / stem, ignore_errors=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    scored = [v["score"] for v in per.values() if v["score"] is not None]
    commit = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=False).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=no"],
                                capture_output=True, text=True, check=False).stdout.strip())
    line = {
        "label": args.label,
        "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
        "commit": commit + ("+dirty" if dirty else ""),
        "soffice": soffice_version(),
        "n": len(scored),
        "mean": round(st.mean(scored), 3) if scored else None,
        "median": round(st.median(scored), 3) if scored else None,
        "failures": sorted(failed),
        "per_pair": per,
    }
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, sort_keys=True) + "\n")
    print(f"{args.label}: n={line['n']} mean={line['mean']} median={line['median']} failures={len(failed)}")

    if base is None:
        return 0
    bad = []
    for stem, v in per.items():
        b = base["per_pair"].get(stem, {}).get("score")
        if b is None or v["score"] is None:
            continue
        delta = v["score"] - b
        if abs(delta) >= 0.05:
            print(f"  {delta:+7.3f}  {b:7.3f} -> {v['score']:7.3f}  {stem}")
        if delta < -args.max_drop:
            bad.append(stem)
    mean_drop = (base["mean"] or 0) - (line["mean"] or 0)
    print(f"mean {base['mean']} -> {line['mean']} ({-mean_drop:+.3f})")
    if bad or mean_drop > args.max_mean_drop:
        print(f"REGRESSION: {len(bad)} pair(s) dropped > {args.max_drop}: {bad}; mean drop {mean_drop:.3f}")
        return 1
    print("OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pick")
    p.add_argument("--seed", type=int, default=20260928)
    p.add_argument("--n", type=int, default=40)
    p.add_argument("--force", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--label", required=True)
    r.add_argument("--bin", default=str(REPO / "target/release/jubarte"))
    r.add_argument("--against")
    r.add_argument("--max-drop", type=float, default=1.0)
    r.add_argument("--max-mean-drop", type=float, default=0.2)
    args = ap.parse_args()
    return pick(args) if args.cmd == "pick" else run(args)


if __name__ == "__main__":
    sys.exit(main())
