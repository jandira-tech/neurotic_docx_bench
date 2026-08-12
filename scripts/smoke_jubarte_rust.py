#!/usr/bin/env python3
"""50-fixture smoke test for jubarte-rust.

Selection (``--select``): picks a representative 50-fixture set from the latest
full-bench per-doc scores (worst tail, shared-low band, docxodus-wins pool,
near-90 band, regression canaries) and writes ``results/smoke50.json`` with the
baseline scores.

Run (default): for each selected pair, generates a redline with the installed
``utils/jubarte/jubarte-rust/redline`` binary, renders via ``bench render``
(soffice), scores via ``bench compare`` against the staged Word-oracle PDFs and
prints per-pair deltas vs the recorded baseline.

Usage:
  uv run python scripts/smoke_jubarte_rust.py --select   # (re)build the set
  uv run python scripts/smoke_jubarte_rust.py            # run smoke test
  uv run python scripts/smoke_jubarte_rust.py --keep     # keep workdir
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import statistics
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
SMOKE_JSON = BENCH_ROOT / "results" / "smoke50.json"
BIN = BENCH_ROOT / "src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline"

CORPORA = [
    # (manifest, source_dir, oracle_pdf_dir)
    (
        "corpus/word_based/centralized_mapping.csv",
        "corpus/word_based/docx_source",
        "corpus/word_based/pdf_redlines_word",
    ),
    (
        "corpus/word_based/centralized_mapping_randomized.csv",
        "corpus/word_based/docx_source_randomized",
        "corpus/word_based/pdf_redlines_randomized/pdf",
    ),
    (
        "corpus/word_redlines_superdoc/centralized_mapping.csv",
        "corpus/word_redlines_superdoc/docx_source",
        "corpus/word_redlines_superdoc/pdf_redlines_word",
    ),
]


def load_pair_index() -> dict[str, dict]:
    """pair_stem -> {base, next, oracle_pdf} with absolute paths."""
    idx: dict[str, dict] = {}
    for manifest, source_dir, oracle_dir in CORPORA:
        mp = BENCH_ROOT / manifest
        if not mp.exists():
            continue
        src = BENCH_ROOT / source_dir
        odir = BENCH_ROOT / oracle_dir
        with mp.open() as f:
            for row in csv.DictReader(f):
                stem = row["pair_stem"]
                oracle_name = row.get("pdf_redline") or f"{stem}_redline.pdf"
                entry = {
                    "base": src / row["docx_source_base"],
                    "next": src / row["docx_source_next"],
                    "oracle_pdf": odir / oracle_name,
                }
                idx[stem] = entry
    return idx


def latest_lines() -> tuple[dict, dict]:
    """latest full-bench (rust, docxodus) script_redlines lines."""
    rust = None
    dx = None
    with (BENCH_ROOT / "results" / "bench.jsonl").open() as f:
        for line in f:
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("benchmark") != "script_redlines" or d.get("n_docs", 0) < 700:
                continue
            if d.get("vendor") == "jubarte-rust":
                rust = d
            elif d.get("vendor") == "docxodus":
                dx = d
    if rust is None:
        sys.exit("no full jubarte-rust line in bench.jsonl")
    return rust, dx


def select(n: int = 50) -> None:
    rust, dx = latest_lines()
    scores = rust["scores"]
    ds = dx["scores"] if dx else {}
    idx = load_pair_index()
    known = {k: v for k, v in scores.items() if k in idx}
    missing = [k for k in scores if k not in idx]
    if missing:
        print(f"warning: {len(missing)} scored docs not in pair index (skipped)", file=sys.stderr)

    chosen: dict[str, dict] = {}

    def take(keys: list[str], count: int, bucket: str) -> None:
        for k in keys:
            if len([c for c in chosen.values() if c["bucket"] == bucket]) >= count:
                break
            if k not in chosen:
                chosen[k] = {
                    "baseline": scores[k],
                    "docxodus": ds.get(k),
                    "bucket": bucket,
                }

    # 1. docxodus-wins pool: rust < 75, docxodus >= 90 (proven fixable) — 12
    dxwins = sorted(
        (k for k in known if ds.get(k, 0) >= 90 and scores[k] < 75),
        key=lambda k: scores[k],
    )
    take(dxwins, 12, "dxwins")
    # 2. worst tail < 50 — 8
    tail = sorted((k for k in known if scores[k] < 50), key=lambda k: scores[k])
    take(tail, 8, "tail")
    # 3. shared-low 50-70 — 10 (spread)
    sharedlow = sorted(
        (k for k in known if 50 <= scores[k] < 70), key=lambda k: scores[k]
    )
    step = max(1, len(sharedlow) // 10)
    take(sharedlow[::step], 10, "mid")
    # 4. near-90 (80-89.9) — 10 (median lever)
    near90 = sorted((k for k in known if 80 <= scores[k] < 90), key=lambda k: -scores[k])
    take(near90, 10, "near90")
    # 5. regression canaries 90-99.9 — 5
    hi = sorted((k for k in known if 90 <= scores[k] < 100), key=lambda k: -scores[k])
    step = max(1, len(hi) // 5)
    take(hi[::step], 5, "canary90")
    # 6. exact-100 canaries — 5 (spread across pools)
    perfect = sorted(k for k in known if scores[k] == 100)
    step = max(1, len(perfect) // 5)
    take(perfect[::step], 5, "canary100")

    # top up to n from lowest-scoring remaining
    rest = sorted((k for k in known if k not in chosen), key=lambda k: scores[k])
    for k in rest:
        if len(chosen) >= n:
            break
        chosen[k] = {"baseline": scores[k], "docxodus": ds.get(k), "bucket": "fill"}

    SMOKE_JSON.write_text(json.dumps(chosen, indent=2, sort_keys=True))
    print(f"wrote {SMOKE_JSON} with {len(chosen)} fixtures")
    by_bucket: dict[str, int] = {}
    for c in chosen.values():
        by_bucket[c["bucket"]] = by_bucket.get(c["bucket"], 0) + 1
    print("buckets:", by_bucket)


def run(keep: bool = False, jobs: int = 10, subset: list[str] | None = None) -> int:
    if not SMOKE_JSON.exists():
        sys.exit("run --select first")
    if not BIN.exists():
        sys.exit(f"missing binary {BIN}")
    chosen = json.loads(SMOKE_JSON.read_text())
    if subset:
        chosen = {k: v for k, v in chosen.items() if k in subset}
    idx = load_pair_index()

    work = Path(tempfile.mkdtemp(prefix="smoke-jr-"))
    docx_dir = work / "docx"
    pdf_dir = work / "pdf"  # bench render writes into <work_dir>/pdf
    oracle_dir = work / "oracle"
    for d in (docx_dir, oracle_dir):
        d.mkdir(parents=True)

    gen_fail: dict[str, str] = {}

    def gen(stem: str) -> None:
        e = idx[stem]
        out = docx_dir / f"{stem}_jubarte-rust_redline.docx"
        r = subprocess.run(
            [str(BIN), str(e["base"]), str(e["next"]), "-o", str(out), "--force", "--quiet"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not out.exists():
            gen_fail[stem] = (r.stderr or r.stdout or "no output").strip()[:300]

    stems = [s for s in chosen if s in idx]
    absent = [s for s in chosen if s not in idx]
    if absent:
        print(f"warning: {len(absent)} smoke stems not in pair index: {absent}", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        list(ex.map(gen, stems))

    for stem in stems:
        if stem in gen_fail:
            continue
        op = idx[stem]["oracle_pdf"]
        if op.exists():
            shutil.copy2(op, oracle_dir / f"{stem}_redline.pdf")
        else:
            print(f"warning: missing oracle pdf {op}", file=sys.stderr)

    subprocess.run(
        [
            "uv", "run", "bench", "render", str(docx_dir), str(work),
            "--backend", "soffice", "--jobs", str(jobs),
        ],
        cwd=BENCH_ROOT,
        check=True,
    )
    scores_json = work / "scores.json"
    subprocess.run(
        [
            "uv", "run", "bench", "compare", str(pdf_dir), str(oracle_dir),
            "--tool", "jubarte-rust", "--jobs", str(jobs), "--json", str(scores_json),
        ],
        cwd=BENCH_ROOT,
        check=True,
    )
    new = json.loads(scores_json.read_text())

    rows = []
    for stem in stems:
        base = chosen[stem]["baseline"]
        got = new.get(stem)
        if stem in gen_fail:
            rows.append((stem, base, None, "GENFAIL: " + gen_fail[stem]))
        elif got is None:
            rows.append((stem, base, None, "NOSCORE"))
        else:
            rows.append((stem, base, got, ""))

    rows.sort(key=lambda r: (r[2] is None, (r[2] or 0) - r[1]))
    print()
    print(f"{'delta':>8}  {'base':>7}  {'new':>7}  doc")
    n_reg = n_imp = 0
    for stem, base, got, note in rows:
        if got is None:
            print(f"{'—':>8}  {base:7.2f}  {'—':>7}  {stem[:70]}  {note}")
            continue
        d = got - base
        flag = ""
        if d < -0.5:
            n_reg += 1
            flag = " REG"
        elif d > 0.5:
            n_imp += 1
        if abs(d) > 0.05:
            print(f"{d:+8.2f}  {base:7.2f}  {got:7.2f}  {stem[:70]}{flag}")
    ok = [r[2] for r in rows if r[2] is not None]
    basevals = [r[1] for r in rows if r[2] is not None]
    print()
    print(
        f"n={len(ok)}  mean {statistics.mean(basevals):.2f}→{statistics.mean(ok):.2f}"
        f"  median {statistics.median(basevals):.2f}→{statistics.median(ok):.2f}"
        f"  improved {n_imp}  regressed {n_reg}  genfail {len(gen_fail)}"
    )
    if keep:
        print(f"workdir kept: {work}")
    else:
        shutil.rmtree(work, ignore_errors=True)
    return 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--select", action="store_true")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--only", nargs="*", help="run only these pair stems")
    a = ap.parse_args()
    if a.select:
        select()
    else:
        run(keep=a.keep, jobs=a.jobs, subset=a.only)


if __name__ == "__main__":
    main()
