# Benchmark results

Source: `results/bench.jsonl` — **64** fidelity row(s) (one per vendor×benchmark×**version**; 38 distinct vendor×version pin(s). docxodus rows with n_docs ≤ 100 are dropped as smoke/partial).

Scores are 0–100 (higher = closer to the Microsoft Word oracle). Cross-renderer comparisons (LibreOffice vs Playwright) are **not** directly comparable — only compare within the same benchmark. Different **versions** of the same vendor are kept so you can compare pins (e.g. docxodus 6.4.0 vs 7.0.0).

## Rankings by benchmark

### `script_redlines`

script_redlines (LibreOffice render vs Word oracle)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@3838e1a2c0ae | 85.2628 | 89.4719 | 164 | 48 | 79 | 6 |
| 2 | jubarte-rust | jubarte-rust@8a970b82f860 | 85.0487 | 89.3449 | 164 | 48 | 78 | 6 |
| 3 | jubarte-rust | jubarte-rust@aad3e04cebbd | 84.9762 | 89.3449 | 164 | 48 | 78 | 6 |
| 4 | jubarte-rust | jubarte-rust@980adfca2fc6 | 84.8331 | 89.3449 | 164 | 48 | 78 | 6 |
| 5 | jubarte-rust | jubarte-rust@27b57358b1c3 | 84.7354 | 89.3449 | 164 | 47 | 78 | 6 |
| 6 | jubarte-rust | jubarte-rust@267e2e589504 | 84.4755 | 89.4719 | 164 | 47 | 79 | 6 |
| 7 | jubarte-rust | jubarte-rust@8e77f696f091 | 83.7652 | 88.5162 | 164 | 44 | 75 | 8 |
| 8 | jubarte-rust | jubarte-rust@fc29f56fd31d | 83.7652 | 88.5162 | 164 | 44 | 75 | 8 |
| 9 | jubarte | jubarte-final@8b2e9bf2522a | 83.4234 | 88.6547 | 164 | 53 | 77 | 8 |
| 10 | jubarte | jubarte-final@2f41358dbc2c | 83.4039 | 88.6547 | 164 | 53 | 77 | 8 |
| 11 | jubarte | jubarte-final@d7599c91e4d5 | 83.4039 | 88.6547 | 164 | 53 | 77 | 8 |
| 12 | jubarte | jubarte-final@dbc8db9ef551 | 83.4037 | 88.6547 | 164 | 53 | 77 | 8 |
| 13 | jubarte-rust | jubarte-rust@cdfef70a7156 | 81.0444 | 84.7199 | 207 | 42 | 84 | 17 |
| 14 | jubarte-rust | jubarte-rust@51a93adf52ca | 80.2389 | 83.1955 | 207 | 41 | 79 | 17 |
| 15 | jubarte | jubarte-final@dd16ad8fbcf3 | 79.4364 | 79.9471 | 207 | 54 | 77 | 13 |
| 16 | jubarte | jubarte-final@8b23cdc7eca8 | 79.2696 | 79.9471 | 207 | 54 | 77 | 13 |
| 17 | jubarte | jubarte-final@6481c2fdbfc0 | 79.2475 | 78.8195 | 207 | 45 | 68 | 9 |
| 18 | jubarte | jubarte-final@4f56a39e78ef | 79.2153 | 78.8195 | 207 | 45 | 68 | 10 |
| 19 | jubarte | jubarte-final@755ee30d148c | 79.2153 | 78.8195 | 207 | 45 | 68 | 10 |
| 20 | jubarte | jubarte-final@a764898a424c | 79.1583 | 78.7802 | 207 | 46 | 69 | 9 |
| 21 | jubarte | jubarte-final@a56814ce307c | 79.1225 | 78.7802 | 207 | 46 | 68 | 9 |
| 22 | jubarte | jubarte-final@04dabff1cfaf | 77.824 | 78.6169 | 207 | 34 | 54 | 10 |
| 23 | jubarte | jubarte-final@ac1fcea44646 | 77.824 | 78.6169 | 207 | 34 | 54 | 10 |
| 24 | jubarte | jubarte-final@717311c03d4f | 73.4761 | 73.1343 | 207 | 25 | 47 | 26 |
| 25 | sanity-word | — | 68.1679 | 70.4845 | 230 | 0 | 0 | 38 |
| 26 | jubarte-rust | jubarte-rust@6233a48e4ac8 | 66.3055 | 64.1705 | 196 | 0 | 21 | 32 |
| 27 | jubarte | jubarte-final@b4f90acaa85e | 64.6926 | 63.481 | 196 | 0 | 5 | 31 |
| 28 | jubarte-rust | jubarte-rust@b834d6e49fdb | 61.7832 | 59.2784 | 172 | 2 | 6 | 39 |
| 29 | docxodus | 7.0.0 | 58.7507 | 55.0306 | 205 | 3 | 7 | 66 |
| 30 | docxodus | 6.4.0 | 58.7425 | 55.0306 | 205 | 3 | 7 | 66 |
| 31 | superdoc-redlines | 0.2.0 | 57.6297 | 55.8997 | 192 | 0 | 1 | 63 |
| 32 | superdoc | 1.19.2 | 57.1871 | 55.5996 | 182 | 2 | 4 | 52 |
| 33 | folio | 0.3.1 | 55.3092 | 53.7539 | 205 | 0 | 1 | 75 |
| 34 | ooxmlsdk | — | 55.1866 | 55.2398 | 232 | 0 | 0 | 52 |
| 35 | redlines | 0.6.1 | 51.284 | 51.7682 | 200 | 0 | 0 | 84 |

### `accepted_changes`

`accepted_changes`

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte | jubarte-final@dd16ad8fbcf3 | 86.534 | 94.4179 | 164 | 63 | 87 | 7 |
| 2 | jubarte-rust | jubarte-rust@cdfef70a7156 | 84.2733 | 88.7405 | 164 | 54 | 80 | 7 |
| 3 | jubarte-rust | jubarte-rust@8e77f696f091 | 83.7563 | 87.9669 | 164 | 52 | 77 | 7 |
| 4 | jubarte | jubarte-final@717311c03d4f | 78.1534 | 80.639 | 166 | 26 | 43 | 14 |
| 5 | docxodus | 7.0.0 | 70.1963 | 74.9182 | 164 | 17 | 44 | 49 |
| 6 | docxodus | 6.4.0 | 68.9994 | 77.1882 | 164 | 14 | 22 | 43 |
| 7 | superdoc | 1.19.2 | 63.818 | 61.1184 | 150 | 2 | 3 | 33 |
| 8 | jubarte-rust | jubarte-rust@b834d6e49fdb | 63.499 | 54.4541 | 147 | 13 | 15 | 72 |
| 9 | folio | 0.3.1 | 57.9094 | 55.608 | 164 | 3 | 4 | 61 |

### `roundtrip`

roundtrip (self-diff → pdf_source)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@cdfef70a7156 | 99.1699 | 100 | 166 | 157 | 161 | 1 |
| 2 | jubarte-rust | jubarte-rust@fc29f56fd31d | 99.1697 | 100 | 166 | 157 | 161 | 1 |
| 3 | folio | 0.3.1 | 98.0712 | 100 | 198 | 185 | 190 | 4 |
| 4 | jubarte | jubarte-final@dd16ad8fbcf3 | 97.6313 | 100 | 166 | 152 | 156 | 3 |
| 5 | docxodus | 7.0.0 | 97.4281 | 100 | 166 | 148 | 157 | 4 |
| 6 | jubarte | jubarte-final@717311c03d4f | 94.4868 | 100 | 199 | 149 | 165 | 3 |
| 7 | jubarte-rust | jubarte-rust@b834d6e49fdb | 93.1152 | 100 | 171 | 120 | 137 | 6 |
| 8 | superdoc | 1.19.2 | 93.0017 | 100 | 194 | 144 | 158 | 8 |
| 9 | docxodus | 6.4.0 | 92.2445 | 100 | 198 | 144 | 161 | 13 |

### `visual_rendering`

visual_rendering (Playwright viewer)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | folio | 0.5.0 | 59.6494 | 55.0967 | 198 | 0 | 3 | 56 |
| 2 | superdoc | 1.44.1 | 58.7798 | 61.2486 | 199 | 0 | 0 | 38 |
| 3 | docxodus | 6.4.0-local.1 | 56.5017 | 49.7216 | 190 | 0 | 0 | 97 |
| 4 | docxodus | 7.0.0 | 56.5017 | 49.7216 | 190 | 0 | 0 | 97 |

### `visual_redlines`

visual_redlines (Playwright)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 60.9207 | 61.2232 | 145 | 0 | 0 | 13 |
| 2 | superdoc | 1.44.1 | 55.3334 | 56.4237 | 164 | 0 | 0 | 44 |
| 3 | folio | 0.5.0 | 51.5494 | 51.6497 | 164 | 0 | 0 | 68 |
| 4 | docxodus | 7.0.0 | 48.2275 | 48.0758 | 164 | 0 | 0 | 122 |

### `visual_accepted_changes`

visual_accepted_changes (Playwright)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 62.3235 | 62.7622 | 152 | 0 | 1 | 21 |
| 2 | folio | 0.5.0 | 59.671 | 54.9489 | 164 | 0 | 0 | 42 |
| 3 | superdoc | 1.44.1 | 59.3354 | 60.971 | 165 | 0 | 0 | 35 |

## All fidelity runs (flat)

| vendor | version | datetime | benchmark | mean | median | n_docs |
| --- | --- | --- | --- | --- | --- | --- |
| docxodus | 6.4.0 | 2026-07-09T15:58:38.145555+00:00 | accepted_changes | 68.9994 | 77.1882 | 164 |
| docxodus | 6.4.0 | 2026-07-10T00:12:10.214778+00:00 | roundtrip | 92.2445 | 100 | 198 |
| docxodus | 6.4.0 | 2026-07-09T15:48:47.581159+00:00 | script_redlines | 58.7425 | 55.0306 | 205 |
| docxodus | 6.4.0 | 2026-07-09T17:19:51.161639+00:00 | visual_accepted_changes | 62.3235 | 62.7622 | 152 |
| docxodus | 6.4.0 | 2026-07-09T16:57:22.200205+00:00 | visual_redlines | 60.9207 | 61.2232 | 145 |
| docxodus | 6.4.0-local.1 | 2026-07-10T20:58:07.916380+00:00 | visual_rendering | 56.5017 | 49.7216 | 190 |
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | accepted_changes | 70.1963 | 74.9182 | 164 |
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | roundtrip | 97.4281 | 100 | 166 |
| docxodus | 7.0.0 | 2026-07-10T21:37:40.839901+00:00 | script_redlines | 58.7507 | 55.0306 | 205 |
| docxodus | 7.0.0 | 2026-07-10T21:59:48.076126+00:00 | visual_redlines | 48.2275 | 48.0758 | 164 |
| docxodus | 7.0.0 | 2026-07-10T21:55:37.514080+00:00 | visual_rendering | 56.5017 | 49.7216 | 190 |
| folio | 0.3.1 | 2026-07-09T13:48:42.309993+00:00 | accepted_changes | 57.9094 | 55.608 | 164 |
| folio | 0.3.1 | 2026-07-10T00:18:18.365930+00:00 | roundtrip | 98.0712 | 100 | 198 |
| folio | 0.3.1 | 2026-07-09T13:01:34.270204+00:00 | script_redlines | 55.3092 | 53.7539 | 205 |
| folio | 0.5.0 | 2026-07-08T20:35:26.466209+00:00 | visual_accepted_changes | 59.671 | 54.9489 | 164 |
| folio | 0.5.0 | 2026-07-08T20:20:25.117836+00:00 | visual_redlines | 51.5494 | 51.6497 | 164 |
| folio | 0.5.0 | 2026-07-08T20:14:38.167302+00:00 | visual_rendering | 59.6494 | 55.0967 | 198 |
| jubarte | jubarte-final@04dabff1cfaf | 2026-07-11T00:05:44.072714+00:00 | script_redlines | 77.824 | 78.6169 | 207 |
| jubarte | jubarte-final@2f41358dbc2c | 2026-07-15T12:21:54.426896+00:00 | script_redlines | 83.4039 | 88.6547 | 164 |
| jubarte | jubarte-final@4f56a39e78ef | 2026-07-11T00:30:15.977616+00:00 | script_redlines | 79.2153 | 78.8195 | 207 |
| jubarte | jubarte-final@6481c2fdbfc0 | 2026-07-11T00:38:01.460324+00:00 | script_redlines | 79.2475 | 78.8195 | 207 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-09T00:19:24.490489+00:00 | accepted_changes | 78.1534 | 80.639 | 166 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-10T00:06:11.537044+00:00 | roundtrip | 94.4868 | 100 | 199 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-09T00:28:15.005270+00:00 | script_redlines | 73.4761 | 73.1343 | 207 |
| jubarte | jubarte-final@755ee30d148c | 2026-07-11T00:22:44.799718+00:00 | script_redlines | 79.2153 | 78.8195 | 207 |
| jubarte | jubarte-final@8b23cdc7eca8 | 2026-07-13T16:52:37.466270+00:00 | script_redlines | 79.2696 | 79.9471 | 207 |
| jubarte | jubarte-final@8b2e9bf2522a | 2026-07-13T23:45:59.667934+00:00 | script_redlines | 83.4234 | 88.6547 | 164 |
| jubarte | jubarte-final@a56814ce307c | 2026-07-11T01:10:08.212708+00:00 | script_redlines | 79.1225 | 78.7802 | 207 |
| jubarte | jubarte-final@a764898a424c | 2026-07-11T01:22:46.221863+00:00 | script_redlines | 79.1583 | 78.7802 | 207 |
| jubarte | jubarte-final@ac1fcea44646 | 2026-07-10T23:54:03.912780+00:00 | script_redlines | 77.824 | 78.6169 | 207 |
| jubarte | jubarte-final@b4f90acaa85e | 2026-07-11T02:12:18.691781+00:00 | script_redlines | 64.6926 | 63.481 | 196 |
| jubarte | jubarte-final@d7599c91e4d5 | 2026-07-15T12:32:02.889171+00:00 | script_redlines | 83.4039 | 88.6547 | 164 |
| jubarte | jubarte-final@dbc8db9ef551 | 2026-07-15T12:17:34.829279+00:00 | script_redlines | 83.4037 | 88.6547 | 164 |
| jubarte | jubarte-final@dd16ad8fbcf3 | 2026-07-12T07:58:10.784184+00:00 | accepted_changes | 86.534 | 94.4179 | 164 |
| jubarte | jubarte-final@dd16ad8fbcf3 | 2026-07-12T07:58:10.784184+00:00 | roundtrip | 97.6313 | 100 | 166 |
| jubarte | jubarte-final@dd16ad8fbcf3 | 2026-07-12T07:58:10.784184+00:00 | script_redlines | 79.4364 | 79.9471 | 207 |
| jubarte-rust | jubarte-rust@267e2e589504 | 2026-07-15T17:33:08.665862+00:00 | script_redlines | 84.4755 | 89.4719 | 164 |
| jubarte-rust | jubarte-rust@27b57358b1c3 | 2026-07-15T17:38:41.179863+00:00 | script_redlines | 84.7354 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@3838e1a2c0ae | 2026-07-15T18:13:36.622865+00:00 | script_redlines | 85.2628 | 89.4719 | 164 |
| jubarte-rust | jubarte-rust@51a93adf52ca | 2026-07-13T01:57:49.073008+00:00 | script_redlines | 80.2389 | 83.1955 | 207 |
| jubarte-rust | jubarte-rust@6233a48e4ac8 | 2026-07-11T02:17:46.130799+00:00 | script_redlines | 66.3055 | 64.1705 | 196 |
| jubarte-rust | jubarte-rust@8a970b82f860 | 2026-07-15T18:08:21.829429+00:00 | script_redlines | 85.0487 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@8e77f696f091 | 2026-07-15T15:36:32.217189+00:00 | accepted_changes | 83.7563 | 87.9669 | 164 |
| jubarte-rust | jubarte-rust@8e77f696f091 | 2026-07-15T15:36:32.217189+00:00 | script_redlines | 83.7652 | 88.5162 | 164 |
| jubarte-rust | jubarte-rust@980adfca2fc6 | 2026-07-15T17:48:46.133050+00:00 | script_redlines | 84.8331 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@aad3e04cebbd | 2026-07-15T18:02:55.334087+00:00 | script_redlines | 84.9762 | 89.3449 | 164 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-09T17:43:37.147567+00:00 | accepted_changes | 63.499 | 54.4541 | 147 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-10T00:21:53.149640+00:00 | roundtrip | 93.1152 | 100 | 171 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-09T17:36:04.577266+00:00 | script_redlines | 61.7832 | 59.2784 | 172 |
| jubarte-rust | jubarte-rust@cdfef70a7156 | 2026-07-12T08:09:01.073181+00:00 | accepted_changes | 84.2733 | 88.7405 | 164 |
| jubarte-rust | jubarte-rust@cdfef70a7156 | 2026-07-12T08:09:01.073181+00:00 | roundtrip | 99.1699 | 100 | 166 |
| jubarte-rust | jubarte-rust@cdfef70a7156 | 2026-07-12T08:09:01.073181+00:00 | script_redlines | 81.0444 | 84.7199 | 207 |
| jubarte-rust | jubarte-rust@fc29f56fd31d | 2026-07-15T15:50:15.935561+00:00 | roundtrip | 99.1697 | 100 | 166 |
| jubarte-rust | jubarte-rust@fc29f56fd31d | 2026-07-15T15:50:15.935561+00:00 | script_redlines | 83.7652 | 88.5162 | 164 |
| ooxmlsdk | — | 2026-07-13T17:24:50.712941+00:00 | script_redlines | 55.1866 | 55.2398 | 232 |
| redlines | 0.6.1 | 2026-07-12T07:38:29.295760+00:00 | script_redlines | 51.284 | 51.7682 | 200 |
| sanity-word | — | 2026-07-13T18:06:21.529826+00:00 | script_redlines | 68.1679 | 70.4845 | 230 |
| superdoc | 1.19.2 | 2026-07-09T15:38:31.872437+00:00 | accepted_changes | 63.818 | 61.1184 | 150 |
| superdoc | 1.19.2 | 2026-07-09T18:25:24.395459+00:00 | roundtrip | 93.0017 | 100 | 194 |
| superdoc | 1.19.2 | 2026-07-09T15:34:17.469383+00:00 | script_redlines | 57.1871 | 55.5996 | 182 |
| superdoc | 1.44.1 | 2026-07-09T18:25:37.273372+00:00 | visual_accepted_changes | 59.3354 | 60.971 | 165 |
| superdoc | 1.44.1 | 2026-07-09T18:22:07.033240+00:00 | visual_redlines | 55.3334 | 56.4237 | 164 |
| superdoc | 1.44.1 | 2026-07-09T18:16:46.431642+00:00 | visual_rendering | 58.7798 | 61.2486 | 199 |
| superdoc-redlines | 0.2.0 | 2026-07-12T08:32:43.871610+00:00 | script_redlines | 57.6297 | 55.8997 | 192 |

## Redline generation speed

Source: `results/speed.jsonl` (+ `results/redline_speed_bench/**/summary.json` when present). **16** generation row(s) after dedupe (one per tool×kind; prefer larger `n`, then lower median). Unit: **ms per redline** (lower = faster). See [`docs/SPEED.md`](docs/SPEED.md) for methodology.

**Fairness (read before citing):**

- **`*-inproc` / Node engines** — warm process, algorithm cost (thesis-grade).
- **CLI tools** (`docxodus-csharp`, `jubarte-rust`) — spawn + I/O + compare per sample. C# cold-start dominates; do **not** cite CLI as algorithm cost.
- **WASM `docxodus`** — Mono/.NET WASM in-process after one-time init; fat tail.

### Microbench (`kind: speed`)

Classic `scripts/speed-bench.ts` / SuperDoc speed harness (typically ~30–40 pairs × 3 reps, in-memory for Node).

| # | tool | runtime | median ms | mean ms | p95 | p99 | /s | n | fail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docx-redline-js | node | 1.451 | 2.791 | 6.907 | 45.976 | 358.4 | 90 | 0 |
| 2 | jubarte-third-docxodus | node | 2.364 | 6.031 | 33.763 | 53.804 | 165.8 | 90 | 0 |
| 3 | jubarte-second-docxodus | node | 2.39 | 5.891 | 31.351 | 52.839 | 169.8 | 90 | 0 |
| 4 | jubarte-lossless | node | 2.457 | 6.596 | 37.579 | 58.256 | 151.6 | 90 | 0 |
| 5 | jubarte-second-native | node | 4.46 | 7.485 | 31.96 | 44.696 | 133.6 | 90 | 0 |
| 6 | jubarte-third-native | node | 4.469 | 7.55 | 33.212 | 45.323 | 132.4 | 90 | 0 |
| 7 | jubarte-native | node | 4.5 | 7.671 | 33.267 | 47.434 | 130.4 | 90 | 0 |
| 8 | superdoc | python | 40.888 | 94.191 | 619.931 | 885.366 | 10.6 | 90 | 0 |
| 9 | docxodus | node | 75.27 | 236.569 | 1499.68 | 2262.59 | 4.2 | 90 | 0 |

### Large-N `speed_redlines` (`scripts/redline_speed_bench.ts`)

Large fixture pools (often **1000 unique** docs → **5000 pairs**), including native C# Docxodus, jubarte-rust CLI/warm, WASM. Warm workers: `docxodus-csharp-inproc`, `jubarte-rust-inproc`.

| # | tool | runtime | fixtures | pairs | median ms | mean ms | p95 | p99 | /s | n | fail | profile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-native | node | 199 | 1000 | 6.333 | 21.535 | 59.876 | 220.005 | 46.4 | 1000 | 0 | — |
| 2 | docxodus-csharp-inproc | dotnet | 1000 | 5000 | 9.431 | 29.903 | 110.731 | 234.991 | 33.4 | 4880 | 120 | v8-inspector |
| 3 | jubarte-rust-inproc | rust | 1000 | 5000 | 9.688 | 40.764 | 157.506 | 494.063 | 24.5 | 5000 | 0 | samply |
| 4 | jubarte-rust | node | 199 | 1000 | 11.111 | 74.143 | 319.572 | 534.866 | 13.5 | 1000 | 0 | — |
| 5 | jubarte-lossless | node | 199 | 1000 | 26.172 | 167.638 | 685.796 | 1287.268 | 6 | 1000 | 0 | — |
| 6 | docxodus | dotnet-wasm | 50 | 50 | 120.503 | 1010.66 | 2744.111 | 4212.309 | 1 | 50 | 0 | — |
| 7 | docxodus-csharp | dotnet | 50 | 50 | 208.388 | 441.646 | 911.873 | 1154.008 | 2.3 | 50 | 0 | — |

### Speed methodology notes

- Dedup key: `(kind, tool, unit)`. Best re-run by `(n, −median, run_ts)`.
- `speed_redlines` rows with **n < 10** are dropped as trivial smokes.
- Profiles (when present): samply `.profile.json.gz` for native CLIs/workers; V8 `.cpuprofile` for in-process Node (e.g. jubarte-lossless).
- Regenerate after a run: `python3 scripts/export-results-md.py`.

## Methodology notes (fidelity)

- Deduplication: one line per `(vendor, benchmark, tool_version)`. Re-runs of the **same** triple keep the best by `(render_fit, n_docs, overall_mean, timestamp)` — prefer playwright for `visual_*` and soffice for script/accepted/roundtrip, then higher n / mean.
- **Versions are not collapsed.** docxodus `6.4.0` and `7.0.0` both appear so pins can be compared directly.
- **docxodus** filter: rows with **`n_docs ≤ 100`** are dropped (smoke / partial runs such as `visual_rendering` with n=21 or n=2). Full-corpus pins (typically n ≳ 145) are kept for every version.
- Other vendors keep every version even if n is small (e.g. `prebaked` sanity).
- Scores isolate *redline-markup fidelity vs Word* when candidates and the oracle share the same renderer (LibreOffice 26.2.4.2 for `script_redlines` / `accepted_changes` / `roundtrip`). Playwright `visual_*` scores are not cross-comparable with soffice scores.

## Licensing & legal considerations

These numbers are **independent engineering measurements**, not endorsements, certifications, or claims of compliance with any third-party product.

- **This repository** (scoring core derived from [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks)) is licensed under **AGPL-3.0-only**. See `LICENSE`.
- **Microsoft Word** is a proprietary product of Microsoft. The Word oracle redlines are produced by Word for measurement only; Microsoft is not affiliated with this benchmark and does not endorse these results. Trademarks remain the property of their owners.
- **Benchmarked engines** remain under their own licenses and copyrights; publishing a score does not change their terms:
  - jubarte / in-repo ports — see their package licenses
  - [docxodus](https://github.com/JSv4/docxodus) (MIT)
  - [docx-redline-js](https://github.com/AnsonLai/docx-redline-js) (MIT)
  - [folio](https://github.com/stella/folio) (Apache-2.0)
  - [SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) (AGPL-3.0) and related SuperDoc tooling
- **LibreOffice** is used only as a pinned PDF renderer for fair comparison; it is not a redline generator in this bench.
- Redistributing or reusing scores, corpus fixtures, or generated redlines must still respect the licenses of the underlying tools and any corpus rights.

Regenerate: `python3 scripts/export-results-md.py` (reads `results/bench.jsonl` + `results/speed.jsonl`).

