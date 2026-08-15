# redline_speed_bench (speed_redlines)

- **fixtures:** 1000 unique (target 1000) from 7 dirs
- **pairs:** 5000 (every fixture × random partner, seed=42, min=5000)
- **warmup:** 50  **reps:** 1
- **run_ts:** 2026-08-15T16:10:03.661Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-rust-inproc | 6.353 | 25.985 | 103.676 | 161.464 | 38.5 | 129.93 | 0 | 5000 | samply |
| 2 | docxodus-csharp-inproc | 8.664 | 27.392 | 108.668 | 194.521 | 36.5 | 148.6 | 120 | 4880 | samply |
| 3 | jubarte-wasm | 9.667 | 41.493 | 174.035 | 265.818 | 24.1 | 207.47 | 0 | 5000 | v8-inspector |
| 4 | jubarte-rust | 12.834 | 34.977 | 120.622 | 200.812 | 28.6 | 174.89 | 0 | 5000 | samply |
| 5 | docxodus | 74.595 | 428.227 | 922.477 | 3970.72 | 2.3 | 2141.14 | 0 | 5000 | v8-inspector |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/2026-08-15/cpu/jubarte-rust-inproc.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/2026-08-15/cpu/docxodus-csharp-inproc.cpuprofile
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/2026-08-15/cpu/jubarte-rust.profile.json.gz
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/2026-08-15/cpu/docxodus-csharp.profile.json.gz
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/2026-08-15/cpu/docxodus.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/2026-08-15/cpu/jubarte-wasm.cpuprofile
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** canonical jubarte-redlines source via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
