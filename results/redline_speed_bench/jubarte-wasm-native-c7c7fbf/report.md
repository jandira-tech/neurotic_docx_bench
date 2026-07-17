# redline_speed_bench (speed_redlines)

- **fixtures:** 1000 unique (target 1000) from 7 dirs
- **pairs:** 5000 (every fixture × random partner, seed=42, min=5000)
- **warmup:** 50  **reps:** 1
- **run_ts:** 2026-07-17T03:30:28.477Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-rust | 10.428 | 32.914 | 129.333 | 202.766 | 30.4 | 164.57 | 0 | 5000 | — |
| 2 | jubarte-wasm | 10.967 | 44.596 | 191.773 | 292.953 | 22.4 | 222.98 | 0 | 5000 | — |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/jubarte-wasm-native-c7c7fbf/cpu/jubarte-wasm.cpuprofile
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/jubarte-wasm-native-c7c7fbf/cpu/jubarte-rust.profile.json.gz
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** jubarte-rs via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
