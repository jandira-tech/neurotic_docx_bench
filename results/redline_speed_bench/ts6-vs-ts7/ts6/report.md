# redline_speed_bench

- **fixtures:** 199 in `/Users/arthrod/temp/T/neurotic_docx_bench/corpus/word_based/docx_source`
- **pairs:** 1000 (every fixture × random partner, seed=42, min=1000)
- **warmup:** 10  **reps:** 1
- **run_ts:** 2026-07-15T13:19:06.158Z

| rank | tool | median ms | mean ms | p95 | p99 | /s | wall s | fail | n |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte-native | 7.047 | 22.993 | 66.133 | 237.771 | 43.5 | 22.99 | 0 | 1000 |
| 2 | jubarte-lossless | 26.172 | 167.638 | 685.796 | 1287.268 | 6 | 167.64 | 0 | 1000 |

## Profiles

```bash
# Chrome DevTools → Performance → Load profile, or:
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts6/cpu/jubarte-native.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts6/cpu/jubarte-lossless.cpuprofile
```

## Fairness

- **jubarte-native / jubarte-lossless:** in-memory `Uint8Array` compare (no disk in the timed loop).
- **jubarte-rust:** CLI via `spawnSync` + temp files (I/O + process spawn included) — real end-to-end CLI cost.
