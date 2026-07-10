#!/usr/bin/env python3
"""Extract the bottom-N script_redlines pairs for a vendor and stage a fix batch.

Copies Word-equivalent fixtures (base, next, Word redline DOCX, Word oracle PDF)
into a target directory with README + manifests for incremental re-scoring.

Usage (from neurotic-docx-bench root):
  uv run python scripts/extract-bottom50-batch.py \\
    --vendor jubarte --out ../jubarte-first/batch_to_fix --n 50
  uv run python scripts/extract-bottom50-batch.py \\
    --vendor jubarte-rust --out ../jubarte-rust/batch_to_fix --n 50
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = BENCH_ROOT / "results" / "bench.jsonl"
DEFAULT_CORPUS = BENCH_ROOT / "corpus" / "word_based"

VENDOR_LABELS = {
    "jubarte": "jubarte-final (vendor=jubarte, tool_version jubarte-final@…)",
    "jubarte-rust": "jubarte-rust (vendor=jubarte-rust)",
}


def latest_script_redlines(jsonl: Path, vendor: str) -> dict:
    best: dict | None = None
    for line in jsonl.read_text().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("vendor") != vendor:
            continue
        if d.get("benchmark") != "script_redlines":
            continue
        if best is None or (d.get("timestamp") or "") > (best.get("timestamp") or ""):
            best = d
    if best is None:
        raise SystemExit(f"no script_redlines line for vendor={vendor!r} in {jsonl}")
    return best


def load_mapping(mapping_csv: Path) -> dict[str, dict]:
    """Index by lowercased pair_stem — bench score keys are case-folded."""
    by_stem: dict[str, dict] = {}
    with mapping_csv.open(newline="") as fh:
        for row in csv.DictReader(fh):
            stem = (row.get("pair_stem") or "").strip()
            if stem:
                by_stem[stem.lower()] = row
    return by_stem


def resolve_word_redline(row: dict, stem: str, word_redlines: Path) -> Path | None:
    for col in ("redline_docx", "redline_docx_word"):
        name = (row.get(col) or "").strip()
        if name and name != "MISSING":
            p = word_redlines / name
            if p.is_file():
                return p
    for name in (f"{stem}_redline.docx", f"{stem}_word_redline.docx"):
        p = word_redlines / name
        if p.is_file():
            return p
    hits = sorted(word_redlines.glob(f"{stem}*redline*.docx"))
    return hits[0] if hits else None


def resolve_pdf(row: dict, stem: str, pdf_redlines: Path) -> Path | None:
    name = (row.get("pdf_redline") or "").strip()
    if name and name != "MISSING":
        p = pdf_redlines / name
        if p.is_file():
            return p
    p = pdf_redlines / f"{stem}_redline.pdf"
    return p if p.is_file() else None


def write_readme(
    out_root: Path,
    *,
    vendor: str,
    run: dict,
    n: int,
    scores_list: list[float],
    bench_root: Path,
) -> None:
    label = VENDOR_LABELS.get(vendor, vendor)
    mean = run.get("overall_mean")
    med = run.get("overall_median")
    tv = run.get("tool_version")
    ts = run.get("timestamp")
    id_run = run.get("id_run")
    out_root_s = str(out_root.resolve())
    bench_s = str(bench_root.resolve())

    readme = f"""# batch_to_fix — bottom {n} `script_redlines` for {label}

Auto-generated from **neurotic-docx-bench** so we can iterate on the worst Word-fidelity
failures without re-scoring the full corpus every time.

## Where the numbers come from

| Field | Value |
|---|---|
| Bench repo | `{bench_s}` |
| Results log | `results/bench.jsonl` |
| Vendor | `{vendor}` |
| Benchmark | `script_redlines` |
| Tool version | `{tv}` |
| Run id | `{id_run}` |
| Run timestamp | `{ts}` |
| Full-corpus mean / median | {mean} / {med} |
| Docs scored in that run | {run.get("n_docs")} |
| This batch | bottom **{n}** by per-doc score (ascending) |
| Bottom-{n} score range | {min(scores_list):.2f} – {max(scores_list):.2f} |
| Extract script | `neurotic-docx-bench/scripts/extract-bottom50-batch.py` |

**Selection rule:** take the **latest** `script_redlines` JSONL line for vendor
`{vendor}`, sort `scores` ascending, keep the first {n} keys.

Score keys are pair stems (`<base>_<next>`). They match
`corpus/word_based/centralized_mapping.csv` → `pair_stem`.

The score is **pixel fidelity** of the tool's redline DOCX (rendered via LibreOffice
**26.2.4.2**) against the committed Word oracle PDF
(`corpus/word_based/pdf_redlines_word/<pair>_redline.pdf`). Higher = closer to Word.
100 = pixel-identical to the oracle (on the shared pages).

### Reproduce the ranking (from neurotic-docx-bench)

```bash
cd {bench_s}
uv run python scripts/extract-bottom50-batch.py --vendor {vendor} --dry-run --n {n}
```

Or raw:

```bash
cd {bench_s}
uv run python - <<'PY'
import json
from pathlib import Path
VENDOR = "{vendor}"
N = {n}
best = None
for line in Path("results/bench.jsonl").read_text().splitlines():
    d = json.loads(line)
    if d.get("vendor") == VENDOR and d.get("benchmark") == "script_redlines":
        if best is None or (d.get("timestamp") or "") > (best.get("timestamp") or ""):
            best = d
assert best, "no run found"
bottom = sorted(best["scores"].items(), key=lambda kv: kv[1])[:N]
for i, (stem, sc) in enumerate(bottom, 1):
    print(f"{{i:2d}}  {{sc:7.4f}}  {{stem}}")
print("mean", best["overall_mean"], "tool", best["tool_version"], "ts", best["timestamp"])
PY
```

## Layout

```
batch_to_fix/
  README.md                 ← this file
  bottom50.json             ← full provenance + per-pair file map
  bottom50.csv              ← spreadsheet-friendly
  scores.tsv                ← rank / score / pair_stem only
  rescore.sh                ← one-shot re-score after you drop candidates/
  pairs/
    01_<pair_stem>/
      base.docx             ← source A (corpus/word_based/docx_source)
      next.docx             ← source B
      word_redline.docx     ← Microsoft Word tracked-change redline (oracle DOCX)
      <original name>.docx  ← same file under the corpus filename
      word_oracle_redline.pdf ← LibreOffice-rendered Word oracle PDF (score target)
    02_...
  candidates/               ← YOU put <pair_stem>_redline.docx here to re-score
```

Missing files (if any) are listed under each pair in `bottom50.json` → `missing`.

## Easy re-score loop (incremental)

### 1. Generate candidates for just these pairs

Each `pairs/NN_<stem>/` has `base.docx` and `next.docx`. Point your tool at them and
write **flat** output names the scorer expects:

```text
candidates/<pair_stem>_redline.docx
```

Example loop (adapt the compare command to your tool):

```bash
BATCH={out_root_s}
mkdir -p "$BATCH/candidates"
for d in "$BATCH"/pairs/*/; do
  stem=$(basename "$d" | sed 's/^[0-9][0-9]_//')
  # jubarte-first example (adjust to your CLI):
  #   jubarte compare "$d/base.docx" "$d/next.docx" -o "$BATCH/candidates/${{stem}}_redline.docx"
  # jubarte-rust example:
  #   jubarte redline "$d/base.docx" "$d/next.docx" "$BATCH/candidates/${{stem}}_redline.docx"
  echo "TODO generate $stem"
done
```

### 2. Re-score with the same LO pin (one script)

```bash
cd {out_root_s}
./rescore.sh
# or from the bench:
cd {bench_s}
uv run bash {out_root_s}/rescore.sh
```

`rescore.sh` will:

1. Render `candidates/*.docx` → PDFs via `bench render` (LibreOffice).
2. Build a flat oracle PDF dir from `pairs/*/word_oracle_redline.pdf`.
3. Pixel-score every candidate vs its oracle (dpi=144, same `ScoreConfig` defaults).
4. Write `rescore/scores.tsv` and `rescore/summary.json` (mean/median/deltas vs baseline).

### 3. Compare before / after on this batch only

```bash
cd {out_root_s}
uv run python - <<'PY'
import csv, json
from pathlib import Path
old = {{r["pair_stem"]: float(r["score"]) for r in csv.DictReader(open("bottom50.csv"))}}
new_path = Path("rescore/scores.tsv")
if not new_path.is_file():
    raise SystemExit("run ./rescore.sh first")
new = {{}}
for line in new_path.read_text().splitlines()[1:]:
    rank, score, stem = line.split("\\t")
    new[stem] = float(score)
deltas = []
for stem, sc in old.items():
    if stem in new:
        deltas.append((new[stem] - sc, stem, sc, new[stem]))
deltas.sort()
print(f"{{'stem':40}}  {{'before':>8}}  {{'after':>8}}  {{'delta':>8}}")
for d, stem, a, b in deltas:
    print(f"{{stem:40}}  {{a:8.2f}}  {{b:8.2f}}  {{d:+8.2f}}")
print("mean delta", sum(d for d, *_ in deltas) / len(deltas) if deltas else 0)
PY
```

### 4. Full-corpus re-bench after a fix lands

```bash
cd {bench_s}
# jubarte-final JS build (lossless compare path used in the extracted run when applicable)
uv run bench run --only jubarte-final-lossless --rerun
# or: uv run bench run --only jubarte-final-native --rerun

# then refresh this batch from the new JSONL line:
uv run python scripts/extract-bottom50-batch.py \\
  --vendor {vendor} --out {out_root_s} --n {n}
```

### 5. Promote a new CI baseline (only when intentional)

```bash
cd {bench_s}
uv run bench accept-scores {vendor} --benchmark script_redlines
```

## Notes / gotchas

1. **Renderer pin:** oracle PDFs were produced with LibreOffice **26.2.4.2**. Re-score
   candidates with the same LO, or scores drift for renderer reasons (not markup).
2. **Word equivalent** = Microsoft Word tracked-change DOCX from
   `corpus/word_based/docx_redlines_word/` plus its LO-rendered PDF oracle.
3. **jubarte-final** in the bench is vendor `jubarte` (this batch may live under
   `jubarte-first/batch_to_fix` because that tree builds `dist/jubarte-final`).
4. This batch is the bottom of *scored* docs only (pairs the tool failed to generate
   never enter `scores`).
5. Do not treat the mean of the bottom-{n} as the corpus mean — full-corpus mean was
   **{mean}**.

## Provenance files

- `bottom50.json` — authoritative (tool_version, id_run, score_config, per-pair paths)
- `bottom50.csv` / `scores.tsv` — convenience views
- `rescore/` — produced by `./rescore.sh` after you drop candidates
"""
    (out_root / "README.md").write_text(readme)


def write_rescore_sh(out_root: Path, *, bench_root: Path) -> None:
    """Thin wrapper: call neurotic-docx-bench scripts/rescore-batch.py."""
    script = f"""#!/usr/bin/env bash
# Re-score candidates/ against Word oracle PDFs in pairs/.
# Drop <pair_stem>_redline.docx into ./candidates/ then run this script.
set -euo pipefail
BATCH="$(cd "$(dirname "$0")" && pwd)"
BENCH="${{NEUROTIC_DOCX_BENCH:-{bench_root.resolve()}}}"
JOBS="${{JOBS:-8}}"
if [[ ! -f "$BENCH/scripts/rescore-batch.py" ]]; then
  echo "bench not found at $BENCH — set NEUROTIC_DOCX_BENCH to neurotic-docx-bench root" >&2
  exit 1
fi
cd "$BENCH"
exec uv run python scripts/rescore-batch.py --batch "$BATCH" --jobs "$JOBS" "$@"
"""
    path = out_root / "rescore.sh"
    path.write_text(script)
    path.chmod(0o755)


def extract_batch(
    *,
    vendor: str,
    out_root: Path,
    n: int,
    jsonl: Path,
    corpus: Path,
    dry_run: bool = False,
) -> list[tuple[str, float]]:
    source = corpus / "docx_source"
    word_redlines = corpus / "docx_redlines_word"
    pdf_redlines = corpus / "pdf_redlines_word"
    mapping = load_mapping(corpus / "centralized_mapping.csv")
    run = latest_script_redlines(jsonl, vendor)
    scores = {k: float(v) for k, v in (run.get("scores") or {}).items()}
    bottom = sorted(scores.items(), key=lambda kv: (kv[1], kv[0]))[:n]

    if dry_run:
        for i, (stem, sc) in enumerate(bottom, 1):
            print(f"{i:2d}  {sc:7.4f}  {stem}")
        print(
            f"mean={run.get('overall_mean')} tool={run.get('tool_version')} "
            f"ts={run.get('timestamp')} n_docs={run.get('n_docs')}"
        )
        return bottom

    if out_root.exists():
        shutil.rmtree(out_root)
    pairs_dir = out_root / "pairs"
    pairs_dir.mkdir(parents=True)
    (out_root / "candidates").mkdir()

    manifest_rows: list[dict] = []
    for rank, (stem, score) in enumerate(bottom, start=1):
        row = mapping.get(stem.lower(), {})
        base = (row.get("base") or "").strip()
        nxt = (row.get("next") or "").strip()
        # Source filenames keep mapping casing; score keys are lowercased.
        base_docx = source / f"{base}.docx" if base else None
        next_docx = source / f"{nxt}.docx" if nxt else None
        # Prefer mapping pair_stem (original case) for Word file name resolution.
        map_stem = (row.get("pair_stem") or stem).strip()
        word_rl = resolve_word_redline(row, map_stem, word_redlines)
        word_pdf = resolve_pdf(row, map_stem, pdf_redlines)
        if word_pdf is None:
            # Oracle PDFs are often lowercased / pair_stem from scores
            word_pdf = resolve_pdf(row, stem, pdf_redlines)
        if word_rl is None:
            word_rl = resolve_word_redline(row, stem, word_redlines)

        pair_dir = pairs_dir / f"{rank:02d}_{stem}"
        pair_dir.mkdir()
        entry: dict = {
            "rank": rank,
            "pair_stem": stem,
            "score": round(score, 4),
            "base": base,
            "next": nxt,
            "files": {},
            "missing": [],
        }

        def copy_as(src: Path | None, dest_name: str, label: str) -> None:
            if src is None or not src.is_file():
                entry["missing"].append(label)
                return
            shutil.copy2(src, pair_dir / dest_name)
            entry["files"][label] = dest_name

        copy_as(base_docx, "base.docx", "base")
        copy_as(next_docx, "next.docx", "next")
        copy_as(word_rl, "word_redline.docx", "word_redline")
        copy_as(word_pdf, "word_oracle_redline.pdf", "word_oracle_pdf")
        if word_rl and word_rl.is_file():
            shutil.copy2(word_rl, pair_dir / word_rl.name)
            entry["files"]["word_redline_original_name"] = word_rl.name

        manifest_rows.append(entry)

    scores_list = [e["score"] for e in manifest_rows]
    payload = {
        "source_bench": str(BENCH_ROOT),
        "vendor": vendor,
        "label": VENDOR_LABELS.get(vendor, vendor),
        "benchmark": "script_redlines",
        "tool_version": run.get("tool_version"),
        "id_run": run.get("id_run"),
        "timestamp": run.get("timestamp"),
        "overall_mean": run.get("overall_mean"),
        "overall_median": run.get("overall_median"),
        "n_docs_scored": run.get("n_docs"),
        "n_bottom": n,
        "config_hash": run.get("config_hash"),
        "score_config": run.get("score_config"),
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "pairs": manifest_rows,
    }
    (out_root / "bottom50.json").write_text(json.dumps(payload, indent=2) + "\n")

    with (out_root / "bottom50.csv").open("w", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "rank",
                "score",
                "pair_stem",
                "base",
                "next",
                "word_redline",
                "has_base",
                "has_next",
                "has_word_redline",
                "has_word_pdf",
            ],
        )
        w.writeheader()
        for e in manifest_rows:
            w.writerow(
                {
                    "rank": e["rank"],
                    "score": e["score"],
                    "pair_stem": e["pair_stem"],
                    "base": e["base"],
                    "next": e["next"],
                    "word_redline": e["files"].get("word_redline_original_name", ""),
                    "has_base": "base" in e["files"],
                    "has_next": "next" in e["files"],
                    "has_word_redline": "word_redline" in e["files"],
                    "has_word_pdf": "word_oracle_pdf" in e["files"],
                }
            )

    with (out_root / "scores.tsv").open("w") as fh:
        fh.write("rank\tscore\tpair_stem\n")
        for e in manifest_rows:
            fh.write(f"{e['rank']}\t{e['score']}\t{e['pair_stem']}\n")

    write_readme(
        out_root,
        vendor=vendor,
        run=run,
        n=n,
        scores_list=scores_list,
        bench_root=BENCH_ROOT,
    )
    write_rescore_sh(out_root, bench_root=BENCH_ROOT)

    n_missing = sum(1 for e in manifest_rows if e["missing"])
    print(f"=== {vendor} → {out_root} ===")
    print(f"  tool_version: {run.get('tool_version')}")
    print(f"  full-corpus mean={run.get('overall_mean')} n_docs={run.get('n_docs')}")
    print(f"  bottom{n} range: {min(scores_list):.2f} .. {max(scores_list):.2f}")
    print(f"  pairs with any missing file: {n_missing}")
    print(f"  docx={len(list(out_root.rglob('*.docx')))} pdf={len(list(out_root.rglob('*.pdf')))}")
    print("  worst 5:")
    for e in manifest_rows[:5]:
        print(f"    {e['rank']:2d}  {e['score']:7.4f}  {e['pair_stem']}")
    return bottom


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--vendor", required=True, help="bench.jsonl vendor field (jubarte | jubarte-rust)")
    p.add_argument("--out", type=Path, required=True, help="destination batch_to_fix directory")
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    p.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    p.add_argument("--dry-run", action="store_true", help="print ranking only, do not copy")
    args = p.parse_args(argv)

    extract_batch(
        vendor=args.vendor,
        out_root=args.out.resolve() if not args.dry_run else args.out,
        n=args.n,
        jsonl=args.jsonl,
        corpus=args.corpus,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
