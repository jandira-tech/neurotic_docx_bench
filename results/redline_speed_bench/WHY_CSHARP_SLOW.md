# redline_speed_bench (speed_redlines)

- **fixtures:** 50 unique (target 50) from 7 dirs
- **pairs:** 50 (every fixture × random partner, seed=42, min=50)
- **warmup:** 5  **reps:** 1
- **run_ts:** 2026-07-15T17:35:53.260Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n | profile |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | jubarte-rust | 6.643 | 44.737 | 131.242 | 167.517 | 22.4 | 2.24 | 0 | 50 | — |
| 2 | docxodus-csharp-inproc | 8.978 | 69.178 | 236.802 | 248.109 | 14.5 | 3.46 | 0 | 50 | — |
| 3 | docxodus | 120.503 | 1010.66 | 2744.111 | 4212.309 | 1 | 50.53 | 0 | 50 | — |
| 4 | docxodus-csharp | 208.388 | 441.646 | 911.873 | 1154.008 | 2.3 | 22.08 | 0 | 50 | — |

## Profiles

Native engines use **samply** (open in Firefox Profiler / samply load):

```bash
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/why_slow/cpu/docxodus-csharp.profile.json.gz
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/why_slow/cpu/docxodus-csharp-inproc.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/why_slow/cpu/docxodus.cpuprofile
samply load /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/why_slow/cpu/jubarte-rust.profile.json.gz
```

## Fairness

- **docxodus-csharp:** native .NET CLI — **one process per redline** (cold-start tax dominates; typically 200–800ms).
- **docxodus-csharp-inproc:** same Docxodus.dll, **one long-lived process** (algorithm cost only; ~few ms after warmup).
- **docxodus:** npm WASM package (`compareDocuments`) — Mono/.NET WASM in-process after one-time `initialize()`.
- **jubarte-rust:** Rust CLI via spawnSync + temp files (I/O + process spawn included).
- **jubarte-native / jubarte-lossless:** in-memory Uint8Array compare when included.
