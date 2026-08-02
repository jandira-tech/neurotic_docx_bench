# redline_speed_bench (speed_redlines)

- **fixtures:** 1000 unique (target 1000) from 7 dirs
- **pairs:** 5000 (every fixture × random partner, seed=42, min=5000)
- **warmup:** 50  **reps:** 1
- **run_ts:** 2026-07-24T15:17:52.613Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-rust-inproc | 9.149 | 38.188 | 164.496 | 266.414 | 26.2 | 190.94 | 0 | 5000 | — |
| 2 | jubarte-rust | 13.372 | 44.952 | 181.835 | 285.275 | 22.2 | 224.77 | 0 | 5000 | — |
| 3 | jubarte-wasm | 14.99 | 63.331 | 278.227 | 419.81 | 15.8 | 316.66 | 0 | 5000 | — |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/jubarte-wasm-inproc-7b21276-20260724T151752Z/cpu/jubarte-wasm.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/jubarte-wasm-inproc-7b21276-20260724T151752Z/cpu/jubarte-rust-inproc.cpuprofile
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/jubarte-wasm-inproc-7b21276-20260724T151752Z/cpu/jubarte-rust.profile.json.gz
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** canonical jubarte-redlines source via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
