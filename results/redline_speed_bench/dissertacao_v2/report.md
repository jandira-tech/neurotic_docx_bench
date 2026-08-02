# redline_speed_bench (speed_redlines)

- **fixtures:** 2 unique (target 2) from 1 dirs
- **pairs:** 2 (every fixture × random partner, seed=42, min=2)
- **warmup:** 0  **reps:** 1
- **run_ts:** 2026-07-18T03:35:34.738Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-rust | 30348.513 | 30376.624 | 30404.734 | 30404.734 | 0 | 60.75 | 0 | 2 | — |
| 2 | jubarte-rust-inproc | 35804.376 | 35887.41 | 35970.444 | 35970.444 | 0 | 71.77 | 0 | 2 | — |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/dissertacao_v2/cpu/jubarte-rust-inproc.cpuprofile
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/dissertacao_v2/cpu/jubarte-rust.profile.json.gz
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/dissertacao_v2/cpu/jubarte-wasm.cpuprofile
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** canonical jubarte-redlines source via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
