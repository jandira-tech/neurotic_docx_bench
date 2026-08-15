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

### Latest same-run pack — 2026-08-15 (1000 fixtures → 5000 pairs, seed 42)

Full report: [`results/redline_speed_bench/2026-08-15/report.md`](../results/redline_speed_bench/2026-08-15/report.md).

| tool | mode | median ms | mean ms | p95 | p99 | throughput/s | failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **`jubarte-rust-inproc`** | warm native (fair algorithm) | **6.353** | **25.985** | 103.676 | 161.464 | **38.5** | **0** |
| `docxodus-csharp-inproc` | warm .NET | 8.664 | 27.392 | 108.668 | 194.521 | 36.5 | 120 |
| `jubarte-wasm` | warm V8 WASM | 9.667 | 41.493 | 174.035 | 265.818 | 24.1 | 0 |
| `jubarte-rust` | CLI spawn + I/O | 12.834 | 34.977 | 120.622 | 200.812 | 28.6 | 0 |
| `docxodus` | npm WASM + V8 profile | 74.595 | 428.227 | 922.477 | 3970.72 | 2.3 | 0 |
| `docxodus-csharp` | CLI | — | — | — | — | — | INIT FAILED (no `redline` binary in this checkout) |

Matrix: **1000 fixtures → 5000 pairs**, seed **42**, warmup **50**, reps **1**.
`docxodus-csharp` CLI was requested and recorded as init-failed — not silently dropped.

### Current snapshot — native/WASM/inproc @ `7b21276` (2026-07-24)

**This is the publishable same-run pack** after rebuilding all three consumers
from Jubarte source `7b212761c2840f94e52bbe196d6c0e83173c5dc2` (hidden-gem
peels on main). Full immutable report:
[`results/redline_speed_bench/jubarte-wasm-inproc-7b21276-20260724T151752Z/report.md`](../results/redline_speed_bench/jubarte-wasm-inproc-7b21276-20260724T151752Z/report.md).
Paired fidelity: [`fidelity-summary.json`](../results/redline_speed_bench/jubarte-wasm-inproc-7b21276-20260724T151752Z/fidelity-summary.json).

| tool | mode | median ms | mean ms | p95 | p99 | throughput/s | failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **`jubarte-rust-inproc`** | warm native (fair algorithm) | **9.149** | **38.188** | 164.496 | 266.414 | **26.2** | **0** |
| `jubarte-rust` | CLI spawn + I/O | 13.372 | 44.952 | 181.835 | 285.275 | 22.2 | 0 |
| `jubarte-wasm` | warm V8 WASM | 14.990 | 63.331 | 278.227 | 419.810 | 15.8 | 0 |

Matrix: **1000 fixtures → 5000 pairs**, seed **42**, warmup **50**, reps **1**.
Zero failures on all three methods. WASM/inproc median tax ≈ **1.64×**; CLI/inproc
median tax ≈ **1.46×** (spawn + temp I/O).

Reproduce:

```bash
# rebuild consumers from ~/T/jubarte-redlines first (CLI + inproc + wasm-pack)
node --import tsx scripts/redline_speed_bench.ts \
  --methods jubarte-wasm,jubarte-rust-inproc,jubarte-rust \
  --fixture-count 1000 --min-pairs 5000 --warmup 50 --reps 1 \
  --no-profile \
  --out results/redline_speed_bench/jubarte-wasm-inproc-7b21276
```

**Fidelity gate (same commit, Word oracle via LibreOffice):** native CLI
`jubarte-rust@cbbcefb724a7` and `jubarte-wasm` 0.1.0 produced **identical**
per-document `script_redlines` scores (164/164 equal): mean **92.2147**, median
**99.9187**, 80 exact-100, 122 ≥90, 3 below-50. Also on this pin: accepted_changes
mean 89.45 / median 99.75; roundtrip mean 99.17 / median 100.0. Payload
SHA-256 of `jubarte_wasm_bg.wasm`:
`3811d517b46dfeaa24ea582bcd25c484fcbc026f409abd6ac43afa43769b2677`.

### How Jubarte compares to other tools (head-to-head)

**Fidelity** (`script_redlines`, LibreOffice vs Word oracle, best published pin
per vendor, n ≥ 100). Full versioned tables: [`RESULTS.md`](../RESULTS.md).

| vendor | mean | median | n | gap vs jubarte-rust best |
| --- | ---: | ---: | ---: | ---: |
| **jubarte-rust** (best pin) | **92.21** | **99.92** | 164 | — |
| **jubarte-wasm** (same engine) | **92.21** | **99.92** | 164 | 0 (identical scores @ 7b21276) |
| **jubarte final / via-AST** (best) | **90.04** | **91.99** | 163 | −2.2 mean (`jubarte-final@3995702f73ed`, 2026-07-31) |
| jubarte final-lossless (best) | 83.63 | 88.96 | 164 | −8.6 mean |
| docxodus 7.0.0 | 58.75 | 55.03 | 205 | **−33.5 mean** |
| superdoc-redlines 0.2.0 | 57.63 | 55.90 | 192 | −34.6 |
| superdoc 1.19.2 | 57.19 | 55.60 | 182 | −35.0 |
| folio 0.3.1 | 55.31 | 53.75 | 205 | −36.9 |
| redlines 0.6.1 | 51.28 | 51.77 | 200 | −40.9 |
| docx-redline-js (migration) | 50.53 | 50.26 | 161 | −41.7 |

**Takeaway (fidelity):** canonical Rust Jubarte still leads, but the Node
**via-AST** pin (`jubarte-final-native` / `compareDocx`) now clears the **≥90 mean
and median** bar (full-55, LibreOffice dpi 144) and sits only ~2 mean points
behind rust/wasm — well clear of every non-Jubarte redliner (~**+31–40 mean**
over docxodus / superdoc / folio / redlines). Rust native and WASM still match
document-for-document when built from the same source commit.

**Speed** (large-N `speed_redlines`; best historical row kept by the exporter —
see RESULTS.md). Fair algorithm row is **inproc**; CLI and WASM are different
shipping modes. Node via-AST is warm in-process `Uint8Array` compare (same
protocol as rust-inproc).

| tool | mode | best median ms (n≈5k) | notes |
| --- | --- | ---: | --- |
| jubarte-rust-inproc | warm native | **~8.1–9.1** | fair algorithm baseline |
| docxodus-csharp-inproc | warm .NET | ~9.4 | close on median; historical best had 120 fails / 4880 ok |
| jubarte-rust | CLI | ~9.7–13.4 | spawn tax small (Rust) |
| jubarte-wasm | V8 WASM | ~9.7–15.0 | same algorithm; portable lane |
| **jubarte-native (via-AST)** | warm Node | **14.43** | 1000 fixtures → 5000 pairs, fail=0 (2026-07-31 tip) |
| jubarte-lossless | warm Node | ~54.6 | older lossless path |
| docxodus (npm WASM) | Mono WASM | ~149 (500 pairs) | fat tail; not competitive on mean |
| docxodus-csharp CLI | cold .NET | ~208 (50 pairs) | cold-start dominates — not algorithm cost |

**Thesis line:** Jubarte is **both** more Word-faithful *and* as fast or faster
than Docxodus on the fair (warm-process) lane; WASM stays within ~1.6× of warm
native at the median with **zero** fidelity loss vs native.

### Prior verified native/WASM 5k snapshot (2026-07-16, `c7c7fbf`)

Historical pack from Jubarte `c7c7fbf` (pre-`7b21276`). Immutable report:
[`results/redline_speed_bench/jubarte-wasm-native-c7c7fbf/report.md`](../results/redline_speed_bench/jubarte-wasm-native-c7c7fbf/report.md).

| tool | mode | median ms | mean ms | p95 | p99 | throughput/s | failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `jubarte-rust` | CLI spawn + I/O | 10.428 | 32.914 | 129.333 | 202.766 | 30.4 | 0 |
| `jubarte-wasm` | warm V8 WASM | 10.967 | 44.596 | 191.773 | 292.953 | 22.4 | 0 |

Fidelity then: mean 91.9831 / median 99.9040 (164 docs; native≡wasm). Prefer the
`7b21276` snapshot above for current claims.

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
| jubarte-native (older pin) | 4.50 | 7.67 | 7.30 | 33.27 | 47.43 | 3.41 | 47.43 | 9.45 | 130.4 | 312 |
| **jubarte-final-native (via-AST @ 3995702f)** | **6.76** | **18.89** | — | **115.97** | — | — | — | — | **52.9** | 511 |
| jubarte-final-lossless | 18.13 | 52.76 | — | 311.11 | — | — | — | — | 19.0 | 58 |
| superdoc¹ | 40.89 | 94.19 | 63.42 | 619.93 | 885.37 | 32.93 | 885.37 | 165.50 | 10.6 | 719 |
| docxodus | 75.27 | 236.57 | 112.41 | 1499.68 | 2262.59 | 61.97 | 2262.59 | 491.59 | 4.2 | 89 |

¹ superdoc = full file-based SDK cycle incl. disk I/O (see caveat).

### Large-N via-AST native (2026-07-31)

Same matrix as the rust/wasm 5k pack: **1000 fixtures → 5000 pairs**, seed **42**,
warmup **50**, reps **1**, `--no-profile`, dist `dist/jubarte-final` (tip content
hash at run time; fidelity gate pin `jubarte-final@3995702f73ed`). Report:
[`results/redline_speed_bench/jubarte-native-via-ast-90/report.md`](../results/redline_speed_bench/jubarte-native-via-ast-90/report.md).

| tool | mode | median ms | mean ms | p95 | p99 | throughput/s | failures |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| **`jubarte-native`** | warm Node via-AST | **14.43** | **57.15** | 175.71 | 578.45 | **17.5** | **0** |

Reproduce:

```bash
rsync -a --delete ../jubarte-first/dist/ dist/jubarte-final/
node --import tsx scripts/redline_speed_bench.ts \
  --methods jubarte-native \
  --fixture-count 1000 --min-pairs 5000 --warmup 50 --reps 1 \
  --no-profile \
  --jubarte-dist dist/jubarte-final \
  --out results/redline_speed_bench/jubarte-native-via-ast-90
```

## Reading it

- **jubarte-rust-inproc remains the fair algorithm leader** (~8–9 ms median large-N).
- **via-AST Node (`jubarte-native` / `jubarte-final-native`)** is the TypeScript path:
  large-N **14.43 ms** median (17.5/s, 0 fails on 5k) and microbench **6.76 ms** median —
  slower than the older shallow native pin (~4.5 ms) because the via-AST compare does
  real structure-aware redline work, but now **fidelity mean 90.04 / median 91.99**.
- **docx-redline-js is fastest overall (~1.45 ms, 358/s)** — but it's the *least accurate*
  (score ~50–55). Speed bought by doing a shallow text reconciliation, not a real doc diff.
- **the real docxodus (JSv4 WASM/.NET) is by far the slowest and most erratic** — median
  75 ms but **p99 2.3 s** and **std 492 ms**: occasional multi-second stalls from the .NET
  WASM runtime. ~4/s.
- **superdoc ~41 ms median** (10.6/s) with a long tail (p95 620 ms) — but remember that
  number includes the full open/save disk cycle, unlike the in-memory Node figures.

## Speed × accuracy (with `docs/RESULTS.md` / `RESULTS.md`)

Canonical large-N + Word-oracle numbers (2026-07-24 pin `7b21276` / binary
`jubarte-rust@cbbcefb724a7` unless noted). Speed medians from the same-run pack
or the exporter’s best historical 5k row (see RESULTS.md).

| tool | fidelity mean (`script_redlines`) | speed median ms | lane | verdict |
| --- | ---: | ---: | --- | --- |
| **jubarte-rust / wasm** | **92.21** | inproc **9.1** · wasm **15.0** · CLI **13.4** | Word-mode | **best fidelity; top-tier speed** |
| **jubarte final / via-AST** | **90.04** | large-N **14.43** · micro **6.76** | Node `compareDocx` | **≥90 mean & median; #2 fidelity, warm Node** |
| jubarte final-lossless (best pin) | 83.63 | large-N ~54.6 · micro ~2–18 | older port | strong, still below via-AST + rust |
| docxodus-csharp-inproc | (same engine as npm ~58.8) | ~9.4 | warm .NET | competitive *speed*, far behind on fidelity |
| docxodus 7.0.0 (npm WASM) | 58.75 | ~75–150+ (fat tail) | Mono WASM | mid fidelity, slow/erratic |
| superdoc 1.19.2 | 57.19 | ~41 (microbench, disk cycle) | SDK | mid on both |
| folio 0.3.1 | 55.31 | — | — | fidelity only in current tables |
| docx-redline-js | 50.53 | **~1.5** (microbench) | shallow text | fastest micro, least faithful |
| redlines 0.6.1 | 51.28 | — | pure text | not a Word-markup peer |

**Takeaway:** on this harness, **canonical Jubarte (rust/wasm) still wins the
speed×accuracy product** — ~+33 mean points over Docxodus on Word-oracle
fidelity while matching warm-process native speed and shipping a WASM peer with
zero fidelity drift vs native. The **Node via-AST** path is now a close second
on quality (**90.04 / 91.99**) at **14.43 ms** median large-N (about **1.6×**
rust-inproc) — the right default when you need TypeScript `compareDocx` without
the Rust binary.

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

<!-- DUAL_PATH_SPEED:BEGIN -->
## jubarte-first dual-path redline speed (lossless vs via-AST)

_Generated by `scripts/redline_dual_path_report.mjs` from `runs/dual-path-403`. jubarte-first `1d33330` · corpus `64d2f609` · bench `b04b8b5` · Node v26.6.0._

Both TypeScript paths in `jubarte-first` over the same base→next pairs from
`centralized_mapping.csv` + `centralized_mapping_randomized.csv`. Timing covers the
`compare()` call only — accept/reject and judging are excluded, so this is the redline
engine and not the harness. Single process, sequential, no warmup.

| engine | pairs timed | mean ms | median | p90 | p99 | max | total s | pairs/s | MB/s in |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jubarte-first-lossless | 403 | 303.0 | 80.0 | 869.0 | 2528.3 | 16575.4 | 122.1 | 3.30 | 0.23 |
| jubarte-first-via-ast | 403 | 36.6 | 12.2 | 117.2 | 257.3 | 462.8 | 14.7 | 27.33 | 1.93 |
<!-- DUAL_PATH_SPEED:END -->
