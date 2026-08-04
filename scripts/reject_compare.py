"""Reject-compare: reject-all a lane's generated redlines and score vs the BASE oracle.

Mirror of the bench's accept-compare stage, pointed the other way: rejecting every
tracked change in a redline of ``base -> next`` must reproduce ``base``, so the
rejected DOCX is rendered (soffice) and pixel-scored against the committed
``corpus/word_based/pdf_source/<base>.pdf`` oracle. A perfect reject scores 100.

Two reject backends:
  - ``docx-revisions`` (default): the bench's own tool-neutral accept/reject helper,
    the same one accept-compare uses — apples-to-apples across all lanes.
  - ``folio-wasm``: folio's orchestrator engine reject (createJubarteWasmRedlineEngine
    .rejectAll via a small node shim) — the path REJECT-LOSSLESS-01 changed. Only
    meaningful for the wasm lane.

Usage:
  uv run python scripts/reject_compare.py --redline-dir runs-compare/folio-wasm_<ts>/docx \
    --tool folio-wasm --backend docx-revisions --out results-compare/reject_compare.jsonl
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import tempfile
import time
from pathlib import Path

from neurotic_docx_bench import pipeline
from neurotic_docx_bench.accept_changes import process_folder
from neurotic_docx_bench.render.soffice import SofficeRenderer

ORACLE = Path("corpus/word_based/pdf_source")
MANIFEST = Path("corpus/word_based/centralized_mapping.csv")

NODE_REJECT_SHIM = """
const { readFileSync, writeFileSync, readdirSync } = require("node:fs");
const { join } = require("node:path");
(async () => {
  const [,, wasmDir, folioRoot, inDir, outDir] = process.argv;
  const glueRaw = await import(join(wasmDir, "jubarte_wasm.js"));
  const glue = glueRaw.default && typeof glueRaw.default === "object"
    ? { ...glueRaw.default, ...glueRaw } : glueRaw;
  if (typeof glueRaw.default === "function") {
    await glueRaw.default({ module_or_path: readFileSync(join(wasmDir, "jubarte_wasm_bg.wasm")) });
  }
  glue.initPanicHook?.();
  const { createJubarteWasmRedlineEngine } = await import(
    join(folioRoot, "@stll/folio-core/dist/server.js"));
  const engine = createJubarteWasmRedlineEngine({
    compareDocuments: glue.compareDocuments,
    acceptRevisions: glue.acceptRevisions,
    rejectRevisions: glue.rejectRevisions,
    getRevisions: glue.getRevisions,
  });
  let ok = 0, fail = 0;
  for (const name of readdirSync(inDir).filter((n) => n.endsWith(".docx")).sort()) {
    try {
      const buf = readFileSync(join(inDir, name));
      const ab = buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength);
      const out = await engine.rejectAll(ab);
      writeFileSync(join(outDir, name), Buffer.from(out));
      ok++;
    } catch (e) {
      fail++;
      console.error(`REJECT-FAIL ${name}: ${String(e && e.message || e).slice(0, 200)}`);
    }
  }
  console.log(`rejected ${ok} ok, ${fail} failed`);
})();
"""


def base_of(redline_stem: str, tool: str, bases: set[str]) -> str | None:
    """``<base>_<next>_<tool>_redline`` → ``<base>`` via longest known-base prefix."""
    stem = redline_stem.removesuffix(f"_{tool}_redline")
    candidates = [b for b in bases if stem == b or stem.startswith(b + "_")]
    return max(candidates, key=len) if candidates else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--redline-dir", required=True)
    ap.add_argument("--tool", required=True)
    ap.add_argument("--backend", choices=["docx-revisions", "folio-wasm"], default="docx-revisions")
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--dpi", type=int, default=144)
    args = ap.parse_args()

    redline_dir = Path(args.redline_dir)
    docs = sorted(redline_dir.glob("*.docx"))
    if not docs:
        print(f"no docx in {redline_dir}")
        return 1
    bases = {p.stem for p in Path("corpus/word_based/docx_source").glob("*.docx")}

    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="reject-cmp.") as work:
        work_dir = Path(work)
        rejected = work_dir / "rejected"
        rejected.mkdir()
        reject_failures: list[str] = []
        if args.backend == "docx-revisions":
            results = process_folder(redline_dir, rejected, reject=True)
            reject_failures = [r.source.name for r in results if not r.ok]
        else:
            shim = work_dir / "reject_shim.cjs"
            shim.write_text(NODE_REJECT_SHIM)
            wasm_dir = "src/neurotic_docx_bench/utils/jubarte/jubarte-wasm/pkg"
            folio_root = "src/neurotic_docx_bench/utils/folio-current/node_modules"
            proc = subprocess.run(
                ["node", str(shim), str(Path(wasm_dir).resolve()), str(Path(folio_root).resolve()),
                 str(redline_dir.resolve()), str(rejected.resolve())],
                capture_output=True, text=True, timeout=1800,
            )
            print(proc.stdout.strip())
            reject_failures = [
                line.split(" ", 1)[1].split(":", 1)[0]
                for line in proc.stderr.splitlines()
                if line.startswith("REJECT-FAIL")
            ]

        report = SofficeRenderer().to_pdfs(rejected, work_dir / "render", jobs=args.jobs)

        # Pair each rejected-redline PDF with its BASE oracle PDF by manifest bases.
        scores: dict[str, float] = {}
        missing = 0
        pairs = []
        for r in report.results:
            if not r.ok or r.pdf is None:
                continue
            base = base_of(r.source.stem, args.tool, bases)
            oracle_pdf = ORACLE / f"{base}.pdf" if base else None
            if oracle_pdf is None or not oracle_pdf.exists():
                missing += 1
                continue
            pairs.append((r.source.stem, oracle_pdf, r.pdf))
        # Same process-pool fan-out the pipeline's own scorers use (rasterize+score
        # is CPU-bound and not thread-safe).
        from concurrent.futures import ProcessPoolExecutor

        from neurotic_docx_bench.pipeline import _score_one  # noqa: PLC2701

        score_dir = work_dir / "score"
        score_dir.mkdir(exist_ok=True)
        tasks = [(key, o, c, score_dir, args.dpi) for key, o, c in pairs]
        if args.jobs > 1 and len(tasks) > 1:
            with ProcessPoolExecutor(max_workers=args.jobs) as pool:
                per_doc = dict(pool.map(_score_one, tasks))
        else:
            per_doc = dict(_score_one(t) for t in tasks)
        scores = {k: pipeline.overall_from_result(v) for k, v in per_doc.items()}

    vals = list(scores.values())
    row = {
        "schema": 1,
        "kind": "reject_compare",
        "tool": args.tool,
        "backend": args.backend,
        "n_docs": len(vals),
        "reject_failures": len(reject_failures),
        "render_failures": report.fail_count,
        "oracle_missing": missing,
        "mean": round(statistics.fmean(vals), 4) if vals else None,
        "median": round(statistics.median(vals), 4) if vals else None,
        "exact_100": sum(1 for s in vals if s >= 99.995),
        "at_least_90": sum(1 for s in vals if s >= 90),
        "below_50": sum(1 for s in vals if s < 50),
        "wall_s": round(time.perf_counter() - t0, 1),
        "reject_failure_docs": reject_failures[:20],
        "scores": {k: round(s, 4) for k, s in sorted(scores.items())},
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(
        f"{args.tool}/{args.backend}: n={row['n_docs']} mean={row['mean']} median={row['median']} "
        f"(=100: {row['exact_100']}, <50: {row['below_50']}) reject-fail={row['reject_failures']} → {out}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
