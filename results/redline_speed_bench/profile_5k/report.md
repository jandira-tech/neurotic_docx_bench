# redline_speed_bench (speed_redlines)

- **fixtures:** 1000 unique (target 1000) from 7 dirs
- **pairs:** 5000 (every fixture × random partner, seed=42, min=5000)
- **warmup:** 50  **reps:** 1
- **run_ts:** 2026-07-15T20:34:02.566Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-rust-inproc | 9.34 | 40.008 | 152.681 | 401.608 | 25 | 200.05 | 0 | 5000 | samply |
| 2 | docxodus-csharp-inproc | 11.454 | 36.764 | 138.636 | 294.71 | 27.2 | 198.83 | 120 | 4880 | samply |
| 3 | jubarte-rust | 14.368 | 38.769 | 135.64 | 337.122 | 25.8 | 193.86 | 0 | 5000 | samply |
| 4 | jubarte-lossless | 73.478 | 263.83 | 899.38 | 3212.764 | 3.8 | 1318.85 | 3 | 4997 | v8-inspector |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/profile_5k/cpu/docxodus-csharp-inproc.cpuprofile
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/profile_5k/cpu/jubarte-rust.profile.json.gz
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/profile_5k/cpu/jubarte-rust-inproc.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/profile_5k/cpu/jubarte-lossless.cpuprofile
```

## Fairness

- **docxodus-csharp / jubarte-rust:** CLI — **one process per redline** (spawn + I/O + compare). C# pays large .NET cold-start; Rust starts in a few ms.
- **docxodus-csharp-inproc / jubarte-rust-inproc:** **warm process** — same algorithms as the CLIs (`DocxDiffOps.Compare` / `compare_documents`), long-lived stdin worker. **This is the fair algorithm comparison.**
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-native / jubarte-lossless:** in-memory Node Uint8Array compare when included.
