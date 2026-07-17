# Redline generation speed benchmark

How fast each engine turns a `base → next` pair into a redline DOCX. Regenerate with
`scripts/speed-bench.ts` (Node) + `python -m neurotic_docx_bench.superdoc_speed`; raw data
in `results/speed.jsonl`. Render speed (Playwright viewer → PDF) is measured separately by
`python -m neurotic_docx_bench.playwright_speed` (see [Render speed](#render-speed)) and is
also captured per-run in `results/bench.jsonl` under each `visual_*` line's speed stats.

## Canonical Jubarte source

Read `../../reconciliation_plan/GET_JUBARTE_RUST.md` before rebuilding either
Jubarte runtime. The source of truth is `../../jubarte-redlines`
(`~/T/jubarte-redlines`), not an older `ooxmlsdk` checkout. The native binary and
WASM package in this repository are generated consumers of that source.

## Large-N native CLI bench (`speed_redlines`)

Heavy compare of redline engines including **native C# Docxodus**, **WASM Docxodus**,
and **jubarte-rust**:

| tool | binary / path | notes |
|---|---|---|
| `jubarte-rust-inproc` | `jubarte-inproc` long-lived worker | same `compare_documents` as CLI, **warm** |
| `docxodus-csharp-inproc` | `docxodus-inproc` long-lived worker | same `DocxDiffOps.Compare`, **warm** |
| `jubarte-rust` | `utils/jubarte/jubarte-rust/redline` | Rust CLI (spawn per redline) |
| `jubarte-wasm` | `utils/jubarte/jubarte-wasm/pkg` | Rust/wasm-bindgen in V8 after one-time init |
| `docxodus-csharp` | Docxodus C# `tools/redline` | C# CLI (spawn + .NET cold-start) |
| `docxodus` | npm WASM `compareDocuments` | Mono/.NET WASM after `initialize()` |

### Thesis-defense command (warm-vs-warm is the load-bearing row)

For “jubarte is faster *and* more precise” you need:

1. **Speed (algorithm, fair):** warm-process both engines, same 1000 fixtures → 5000 pairs  
2. **Speed (shipping CLI):** optional CLI rows (spawn included)  
3. **Precision:** `script_redlines` / `accepted_changes` means from `results/bench.jsonl` (Word oracle)

```bash
# 0) one-time: build warm workers
dotnet build -c Release src/neurotic_docx_bench/utils/docxodus/docxodus-csharp-inproc
( cd src/neurotic_docx_bench/utils/jubarte/jubarte-rust-inproc && cargo build --release )
cp -f src/neurotic_docx_bench/utils/jubarte/jubarte-rust-inproc/target/release/jubarte-inproc \
      src/neurotic_docx_bench/utils/jubarte/jubarte-rust/jubarte-inproc

# 1) WARM ONLY — the fair algorithm race (recommended for thesis speed claims)
bun run redline-speed-bench:warm
# equivalent:
node --import tsx scripts/redline_speed_bench.ts \
  --methods jubarte-rust-inproc,docxodus-csharp-inproc \
  --fixture-count 1000 --min-pairs 5000 --warmup 50 --reps 1 \
  --no-profile \
  --out results/redline_speed_bench/warm_vs_warm

# 2) FULL thesis pack — warm + CLI + WASM (slower; CLI csharp alone is ~1h+)
bun run redline-speed-bench:thesis
# equivalent:
node --import tsx scripts/redline_speed_bench.ts \
  --methods jubarte-rust-inproc,docxodus-csharp-inproc,jubarte-rust,docxodus-csharp,docxodus \
  --fixture-count 1000 --min-pairs 5000 --warmup 50 --reps 1 \
  --out results/redline_speed_bench/thesis_evidence

# 3) Precision (already measured against Word oracle):
uv run bench run --only jubarte-rust
uv run bench run --only docxodus
# then rank from docs/RESULTS.md / results/bench.jsonl
```

**How to cite the table:** lead with the **inproc** medians (warm-vs-warm). Mention CLI only as “end-to-end CLI cost” — never as algorithm cost. Fidelity numbers come from the visual/script redline benches, not this speed harness.

Methodology:

- **1000 unique fixtures** (content SHA-1) pooled from corpus source/accepted/redline dirs
- **5000 deterministic pairs** (every fixture is base ≥ once per round; Mulberry32 seed=42)
- Warmup untimed; each of the 5000 timed with `performance.now()` → full distribution
- **Profiler: [samply](https://github.com/mstange/samply)** (1000 Hz) for CLI engines so
  child `redline` processes appear in the Firefox Profiler capture; V8 inspector for
  in-process engines when profiling is on
- Appends `kind: "speed_redlines"` rows to `results/speed.jsonl` and writes
  `results/redline_speed_bench/{report.md,summary.json,cpu/*}`

```bash
# Requires: samply on PATH, C# redline at ../ooxmlsdk/Docxodus/tools/redline/bin/Release/net8.0,
#           docxodus-inproc built under utils/docxodus/docxodus-csharp-inproc,
#           jubarte-rust binary under utils/jubarte/jubarte-rust/
bun run redline-speed-bench:native

samply load results/redline_speed_bench/cpu/docxodus-csharp.profile.json.gz
samply load results/redline_speed_bench/cpu/jubarte-rust.profile.json.gz
```

### Verified native/WASM 5k snapshot (2026-07-16)

Both engines were built from Jubarte commit `c7c7fbf`, exercised over the same
1,000 fixtures and 5,000 deterministic pairs (seed 42, warmup 50), and completed
with zero failures. The full immutable report is
[`results/redline_speed_bench/jubarte-wasm-native-c7c7fbf/report.md`](../results/redline_speed_bench/jubarte-wasm-native-c7c7fbf/report.md).
The paired fidelity evidence is recorded separately in
[`fidelity-summary.json`](../results/redline_speed_bench/jubarte-wasm-native-c7c7fbf/fidelity-summary.json).

| tool | mode | median ms | mean ms | p95 | p99 | throughput/s | failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `jubarte-rust` | CLI spawn + I/O | 10.428 | 32.914 | 129.333 | 202.766 | 30.4 | 0 |
| `jubarte-wasm` | warm V8 WASM | 10.967 | 44.596 | 191.773 | 292.953 | 22.4 | 0 |

Reproduce the paired run after rebuilding both consumers:

```bash
node --import tsx scripts/redline_speed_bench.ts \
  --methods jubarte-wasm,jubarte-rust \
  --fixture-count 1000 --min-pairs 5000 --warmup 50 --reps 1 \
  --no-profile \
  --out results/redline_speed_bench/<source-commit>
```

This snapshot compares shipping modes, not pure algorithm cost: the native row
pays one process spawn and file I/O per pair, while WASM runs in-process after
initialization. Use `jubarte-rust-inproc` for native algorithm comparisons.

The preceding `script_redlines` fidelity gate produced identical per-document
scores for native run `019f6e12-e2a5-72fa-b94e-e0da5e78e3e2` and WASM run
`019f6e1d-3c41-7604-86d8-20dea470572f`: 207 documents generated, 164 scored,
mean 91.9831, median 99.9040, 79 exact scores, 121 scores at least 90, three
below 50, and zero generation failures. The built WASM payload SHA-256 was
`73d76228310e39ba4c065df819be59c27418db32b7c316e5f83966008a7ec446`.

After relocating the source checkout, the adapter was rebuilt from the same
commit through the canonical path. The checked-in payload is 1,987,754 bytes
with SHA-256
`f01b4c6e532dacf59a3b9ec212dc225eb9dbcf1ee70a81f38149e0dc497b0545`.
Partial run `019f6e39-e5e4-7535-abc0-9866be9f8f1b` exercised the official
`bench.yaml` entry: 207 outputs generated, three limited documents scored, and
zero failures. The full-corpus scores above remain the quality gate for the same
Rust source commit.

### Why C# CLI looks “that slow” (it isn’t the algorithm)

Same 50 fixtures / 50 pairs / seed=42 / warmup=5 (`results/redline_speed_bench/why_slow/`):

| rank | tool | median ms | mean ms | p95 | /s | wall s |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | **jubarte-rust** | **6.6** | 44.7 | 131 | 22.4 | 2.2 |
| 2 | **docxodus-csharp-inproc** | **9.0** | 69.2 | 237 | 14.5 | 3.5 |
| 3 | docxodus (WASM) | 120.5 | **1011** | 2744 | 1.0 | 50.5 |
| 4 | docxodus-csharp (CLI) | **208** | 442 | 912 | 2.3 | 22.1 |

**Takeaway:**

1. **Docxodus C# algorithm ≈ jubarte-rust** once you keep the process warm
   (`inproc` median 9 ms vs rust 6.6 ms — same order of magnitude).
2. **`docxodus-csharp` CLI is ~23× slower than inproc** because every sample is
   `spawn → load .NET runtime → JIT/touch Docxodus → compare → exit`. A one-shot
   microbench of `DocxDiffOps.Compare` in-process was **~4 ms median** on a tiny
   pair; the same pair via the CLI was **~200–800 ms**.
3. **WASM is not a free win** — median ~120 ms but a **fat tail** (mean ~1 s, p99 ~4 s)
   from Mono WASM. Still better *median* than cold-start CLI, worse *mean* than both
   native engines.
4. Fairness: rust CLI *also* pays spawn+temp-file I/O; it just starts in a few ms.
   Compare CLI-to-CLI (`csharp` vs `rust`) for “how you ship the binary”; compare
   `csharp-inproc` vs in-memory Node engines for “how fast is the comparer”.

Micro-diagnosis (tiny pair, `/usr/bin/time`):

| mode | wall |
|---|---:|
| C# CLI `--version` only (startup tax) | ~20–90 ms |
| C# CLI full small compare | ~200–880 ms |
| C# `DocxDiffOps.Compare` in-process (after warmup) | **~4 ms** |
| Rust CLI small compare | ~0–10 ms |
| WASM small compare (after init) | ~130–900 ms |

Smoke (tiny, no full profile):

```bash
node --import tsx scripts/redline_speed_bench.ts \
  --methods docxodus-csharp,docxodus-csharp-inproc,docxodus,jubarte-rust \
  --fixture-count 20 --min-pairs 40 --warmup 2 --no-profile \
  --out /tmp/redline_speed_smoke
```

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
