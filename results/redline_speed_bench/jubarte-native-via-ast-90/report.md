# redline_speed_bench (speed_redlines)

- **fixtures:** 1000 unique (target 1000) from 7 dirs
- **pairs:** 5000 (every fixture × random partner, seed=42, min=5000)
- **warmup:** 50  **reps:** 1
- **run_ts:** 2026-07-31T12:42:56.767Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-native | 14.43 | 57.145 | 175.709 | 578.45 | 17.5 | 285.73 | 0 | 5000 | — |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/jubarte-native-via-ast-90/cpu/jubarte-native.cpuprofile
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** canonical jubarte-redlines source via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
