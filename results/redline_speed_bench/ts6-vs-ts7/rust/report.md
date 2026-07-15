# redline_speed_bench

- **fixtures:** 199 in `/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_source`
- **pairs:** 1000 (every fixture × random partner, seed=42, min=1000)
- **warmup:** 10  **reps:** 1
- **run_ts:** 2026-07-15T13:22:18.544Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte-rust | 11.111 | 74.143 | 319.572 | 534.866 | 13.5 | 74.14 | 0 | 1000 |

## Profiles

```bash
# Chrome DevTools → Performance → Load profile, or:
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/rust/cpu/jubarte-rust.cpuprofile
```

## Fairness

- **jubarte-native / jubarte-lossless:** in-memory `Uint8Array` compare (no disk in the timed loop).
- **jubarte-rust:** CLI via `spawnSync` + temp files (I/O + process spawn included) — real end-to-end CLI cost.
