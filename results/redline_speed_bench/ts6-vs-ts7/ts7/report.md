# redline_speed_bench

- **fixtures:** 199 in `/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_source`
- **pairs:** 1000 (every fixture × random partner, seed=42, min=1000)
- **warmup:** 10  **reps:** 1
- **run_ts:** 2026-07-15T13:15:35.808Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte-native | 6.333 | 21.535 | 59.876 | 220.005 | 46.4 | 21.54 | 0 | 1000 |
| 2 | jubarte-lossless | 28.49 | 181.731 | 729.909 | 1330.618 | 5.5 | 181.73 | 0 | 1000 |

## Profiles

```bash
# Chrome DevTools → Performance → Load profile, or:
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts7/cpu/jubarte-native.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts7/cpu/jubarte-lossless.cpuprofile
```

## Fairness

- **jubarte-native / jubarte-lossless:** in-memory `Uint8Array` compare (no disk in the timed loop).
- **jubarte-rust:** CLI via `spawnSync` + temp files (I/O + process spawn included) — real end-to-end CLI cost.
