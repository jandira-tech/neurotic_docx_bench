# redline_speed_bench (speed_redlines)

- **fixtures:** 200 unique (target 200) from 7 dirs
- **pairs:** 500 (every fixture × random partner, seed=42, min=500)
- **warmup:** 30  **reps:** 1
- **run_ts:** 2026-07-15T21:08:04.857Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-wasm | 14.439 | 112.746 | 556.769 | 1105.931 | 8.9 | 56.38 | 0 | 500 | — |
| 2 | docxodus | 148.753 | 607.385 | 3212.297 | 7017.889 | 1.6 | 303.73 | 4 | 496 | — |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/wasm_vs_wasm/cpu/jubarte-wasm.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/wasm_vs_wasm/cpu/docxodus.cpuprofile
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** jubarte-rs via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
