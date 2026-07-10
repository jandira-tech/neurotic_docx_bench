# Redline generation speed benchmark

How fast each engine turns a `base → next` pair into a redline DOCX. Regenerate with
`scripts/speed-bench.ts` (Node) + `python -m neurotic_docx_bench.superdoc_speed`; raw data
in `results/speed.jsonl`. Render speed (Playwright viewer → PDF) is measured separately by
`python -m neurotic_docx_bench.playwright_speed` (see [Render speed](#render-speed)) and is
also captured per-run in `results/bench.jsonl` under each `visual_*` line's speed stats.

## Methodology (meticulous by design)

- **30 pairs × 3 reps = 90 timed samples** per engine; the same pair set + order for all.
- **Pairs are pre-loaded into memory** (Uint8Array / bytes) so timings measure the engine's
  compare work, not disk reads — for the Node engines.
- **Engine init** (module import / WASM load / SDK connect) is timed **separately** as a
  one-time cost and never mixed into per-pair samples. _Caveat:_ Node engines sharing a
  `dist/` bundle show ~0 init after the first loads it (module cache) — `init_ms` reflects
  first-load only.
- **Warmup:** the first 3 pairs run untimed (JIT / cache warm-up) before sampling.
- **Every call is timed individually** (`performance.now()` / `perf_counter`); failures
  (engine throws) are counted separately and **excluded** from the stats so a fast-throwing
  failure can't deflate the mean.
- **Fairness caveat:** the Node engines are timed as an **in-memory** `compare(base,next)→bytes`
  call. SuperDoc's SDK is **file-path based**, so its samples are the **full cycle**
  (open → capture → compare → apply → **save to disk**) — genuinely more work per sample.
  Compare Node-to-Node directly; read SuperDoc as "the tool's real per-redline cost".

## Results (ms per redline; lower = faster)

| tool | median | mean | p90 | p95 | p99 | min | max | std | throughput/s | init ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| docx-redline-js | 1.45 | 2.79 | 2.55 | 6.91 | 45.98 | 0.86 | 45.98 | 5.95 | **358.4** | 25 |
| jubarte-third-docxodus | 2.36 | 6.03 | 3.54 | 33.76 | 53.80 | 1.96 | 53.80 | 11.26 | 165.8 | 0 |
| jubarte-second-docxodus | 2.39 | 5.89 | 7.03 | 31.35 | 52.84 | 1.96 | 52.84 | 10.60 | 169.8 | 0 |
| jubarte-lossless | 2.46 | 6.60 | 5.84 | 37.58 | 58.26 | 2.07 | 58.26 | 12.32 | 151.6 | 0 |
| jubarte-second-native | 4.46 | 7.49 | 7.97 | 31.96 | 44.70 | 3.47 | 44.70 | 9.03 | 133.6 | 87 |
| jubarte-third-native | 4.47 | 7.55 | 6.36 | 33.21 | 45.32 | 3.39 | 45.32 | 9.31 | 132.4 | 86 |
| jubarte-native | 4.50 | 7.67 | 7.30 | 33.27 | 47.43 | 3.41 | 47.43 | 9.45 | 130.4 | 312 |
| superdoc¹ | 40.89 | 94.19 | 63.42 | 619.93 | 885.37 | 32.93 | 885.37 | 165.50 | 10.6 | 719 |
| docxodus | 75.27 | 236.57 | 112.41 | 1499.68 | 2262.59 | 61.97 | 2262.59 | 491.59 | 4.2 | 89 |

¹ superdoc = full file-based SDK cycle incl. disk I/O (see caveat).

## Reading it

- **jubarte is the fastest *native-diff* engine** — its docxodus route generates in **~2.4 ms**
  (~160/s), its native route in ~4.5 ms. All three builds are within noise of each other on
  speed (the build-to-build differences were in *accuracy*, not speed).
- **docx-redline-js is fastest overall (~1.45 ms, 358/s)** — but it's the *least accurate*
  (score 54.6). Speed bought by doing a shallow text reconciliation, not a real doc diff.
- **the real docxodus (JSv4 WASM/.NET) is by far the slowest and most erratic** — median
  75 ms but **p99 2.3 s** and **std 492 ms**: occasional multi-second stalls from the .NET
  WASM runtime. ~4/s.
- **superdoc ~41 ms median** (10.6/s) with a long tail (p95 620 ms) — but remember that
  number includes the full open/save disk cycle, unlike the in-memory Node figures.

## Speed × accuracy (with `docs/RESULTS.md`)

| tool | fidelity (mean) | speed (median ms) | verdict |
|---|---:|---:|---|
| jubarte-lossless | **62.9** | 2.46 | best of both — fast **and** most Word-faithful |
| docxodus (real) | 60.1 | 75.3 | accurate but ~30× slower + erratic |
| superdoc | 58.2 | 40.9 | mid on both |
| docx-redline-js | 54.6 | **1.45** | fastest, least faithful |
| jubarte-native | 49.0 | 4.50 | fast, weakest fidelity |

**Takeaway:** jubarte's in-tree docxodus port dominates — it matches the real docxodus
engine's fidelity while generating ~30× faster and without the WASM tail-latency.

## Render speed

Distinct from generation: how long a web viewer takes to *render* a DOCX to a
rasterisable PDF (upload → layout → `page.pdf()`), which is the per-doc cost the
`visual_*` benchmarks pay. Two measurement paths, same walltime methodology:

1. **Per-run, in `results/bench.jsonl`** — every `visual_*` line now carries
   `overall_mean_speed` / `overall_median_speed` / `min_speed` / `max_speed` /
   `std_speed` / `q1_speed` / `q3_speed` plus a per-doc `timings` map with `render_s`,
   derived from the `PlaywrightRenderer`'s `duration_ns` (the same field `soffice` sets).
   This is the render pass the `visual_*` score already uses, so the speed comes for free
   — no extra browser launches. The three `visual_*` benchmarks share one render pass, so
   they share its render-speed distribution.

2. **Standalone, in `results/speed.jsonl`** — a meticulous distribution benchmark
   (`ms_per_render` unit, distinct from the generation `ms_per_redline` rows) for when you
   want reps/warmup/full percentiles isolated from a scoring run:

```bash
uv run python -m neurotic_docx_bench.playwright_speed \
  --docx-dir corpus/word_based/docx_redlines_word \
  --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl \
  --tool folio-playwright --url http://127.0.0.1:5175/harness.html \
  --file-input "#fileInput" --page-selector ".layout-page" \
  --readiness-js "window.__folioReady === true" --timeout-ms 90000 \
  --server "cd harness/folio-viewer && npx vite --port 5175 --host 127.0.0.1"
```

Methodology mirrors the generation benchmarks: init (harness server + Chromium launch)
timed separately and never mixed into per-call samples; warmup untimed; each of the N docs
runs `--reps` times with a **fresh browser context per call** (so a stale readiness flag
from doc N-1 can't short-circuit doc N's wait — mirroring `PlaywrightRenderer.to_pdfs`);
every call timed with `perf_counter`; failures excluded from the timing stats and counted
separately; full distribution (median/mean/p90/p95/p99/min/max/std/throughput).

**Fairness caveat:** render-speed measures the *viewer's* layout + PDF-export work, not
redline generation. A slow viewer is still a slow `visual_*` run even with a fast generator.
Compare `ms_per_render` rows to each other; read `ms_per_redline` rows separately.
