# redline_speed_bench — TypeScript 6 vs 7 builds + rust

- **pairs:** 1000 (every fixture × random partner, seed=42)
- **warmup:** 10  **reps:** 1
- **TS6:** 6.0.2
- **TS7:** 7.0.2
- **dist JS fingerprints identical:** yes
- **TS6 fingerprints:** `{"node.mjs":"75820a1375722946","node.cjs":"8242a7d57ed74360","lossless.node.mjs":"c37e58ee3192aa72","lossless.node.cjs":"1cd8618e52a0554e"}`
- **TS7 fingerprints:** `{"node.mjs":"75820a1375722946","node.cjs":"8242a7d57ed74360","lossless.node.mjs":"c37e58ee3192aa72","lossless.node.cjs":"1cd8618e52a0554e"}`

| tool | build | median ms | mean ms | p95 | p99 | /s | wall s | fail | n |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| jubarte-native | ts6 | 7.047 | 22.993 | 66.133 | 237.771 | 43.5 | 22.99 | 0 | 1000 |
| jubarte-native | ts7 | 6.333 | 21.535 | 59.876 | 220.005 | 46.4 | 21.54 | 0 | 1000 |
| jubarte-native | **TS7/TS6 median** | **0.899** |  |  |  | TS7 faster **10.1%** |  |  |  |
| jubarte-lossless | ts6 | 26.172 | 167.638 | 685.796 | 1287.268 | 6 | 167.64 | 0 | 1000 |
| jubarte-lossless | ts7 | 28.49 | 181.731 | 729.909 | 1330.618 | 5.5 | 181.73 | 0 | 1000 |
| jubarte-lossless | **TS7/TS6 median** | **1.089** |  |  |  | TS7 faster **-8.9%** |  |  |  |
| jubarte-rust | rust binary | 11.111 | 74.143 | 319.572 | 534.866 | 13.5 | 74.14 | 0 | 1000 |

## Profiles

```bash
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts6/cpu/jubarte-native.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts6/cpu/jubarte-lossless.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts7/cpu/jubarte-native.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/ts7/cpu/jubarte-lossless.cpuprofile
npx speedscope /Users/arthrod/temp/T/neurotic_docx_bench/results/redline_speed_bench/ts6-vs-ts7/rust/cpu/jubarte-rust.cpuprofile
```

> Dist fingerprints match between TS6 and TS7 builds — rolldown emit is independent of the tsc/tsgo version used for `.d.ts`. Any wall-time delta is noise/cache, not different JS.
