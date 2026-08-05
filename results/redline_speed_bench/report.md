# redline_speed_bench (speed_redlines)

- **fixtures:** 1000 unique (target 1000) from 7 dirs
- **pairs:** 5000 (every fixture × random partner, seed=42, min=5000)
- **warmup:** 20  **reps:** 1
- **run_ts:** 2026-08-05T20:19:37.750Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-rust-inproc | 6.201 | 25.337 | 110.764 | 182.306 | 39.5 | 126.69 | 0 | 5000 | samply |
| 2 | jubarte-wasm | 9.704 | 41.899 | 182.573 | 317.731 | 23.9 | 209.5 | 0 | 5000 | v8-inspector |
| 3 | jubarte-rust | 11.997 | 33.676 | 129.146 | 219.377 | 29.7 | 168.39 | 0 | 5000 | samply |
| 4 | jubarte-lossless | 56.465 | 168.791 | 609.005 | 1049.093 | 5.9 | 843.83 | 3 | 4997 | v8-inspector |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/cpu/jubarte-rust-inproc.cpuprofile
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/cpu/jubarte-rust.profile.json.gz
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/cpu/jubarte-wasm.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/cpu/jubarte-lossless.cpuprofile
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-wasm:** canonical jubarte-redlines source via **wasm-pack** + **wasm-opt -O3** (`wasm32-unknown-unknown` + wasm-bindgen). Same `compare_documents` as native Rust, hosted in V8 WASM — fair peer of docxodus WASM.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
