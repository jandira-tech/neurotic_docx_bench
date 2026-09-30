# redline_speed_bench (speed_redlines)

- **fixtures:** 2565 unique documents named by the plan
- **pairs:** 8665 planned in results/speed_10k/pairs_10k.csv
- **warmup:** 20  **reps:** 1
- **run_ts:** 2026-09-29T18:02:53.346Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | docxodus | 76.619 | 1639.344 | 6362.051 | 38504.146 | 0.6 | 19820.02 | 46 | 8619 | — |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/speed_10k/redlines/cpu/docxodus.cpuprofile
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** canonical jubarte-redlines source via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
