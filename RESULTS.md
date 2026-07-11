# Benchmark results

Source: `results/bench.jsonl` — **40** row(s) (one per vendor×benchmark×**version**; 20 distinct vendor×version pin(s). docxodus rows with n_docs ≤ 100 are dropped as smoke/partial).

Scores are 0–100 (higher = closer to the Microsoft Word oracle). Cross-renderer comparisons (LibreOffice vs Playwright) are **not** directly comparable — only compare within the same benchmark. Different **versions** of the same vendor are kept so you can compare pins (e.g. docxodus 6.4.0 vs 7.0.0).

## Rankings by benchmark

### `script_redlines`

script_redlines (LibreOffice render vs Word oracle)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | prebaked | — | 100 | 100 | 1 | 1 | 1 | 0 |
| 2 | jubarte | jubarte-final@6481c2fdbfc0 | 79.2475 | 78.8195 | 207 | 45 | 68 | 9 |
| 3 | jubarte | jubarte-final@4f56a39e78ef | 79.2153 | 78.8195 | 207 | 45 | 68 | 10 |
| 4 | jubarte | jubarte-final@755ee30d148c | 79.2153 | 78.8195 | 207 | 45 | 68 | 10 |
| 5 | jubarte | jubarte-final@a764898a424c | 79.1583 | 78.7802 | 207 | 46 | 69 | 9 |
| 6 | jubarte | jubarte-final@a56814ce307c | 79.1225 | 78.7802 | 207 | 46 | 68 | 9 |
| 7 | jubarte | jubarte-final@04dabff1cfaf | 77.824 | 78.6169 | 207 | 34 | 54 | 10 |
| 8 | jubarte | jubarte-final@ac1fcea44646 | 77.824 | 78.6169 | 207 | 34 | 54 | 10 |
| 9 | jubarte | jubarte-final@717311c03d4f | 73.4761 | 73.1343 | 207 | 25 | 47 | 26 |
| 10 | jubarte-rust | jubarte-rust@6233a48e4ac8 | 66.3055 | 64.1705 | 196 | 0 | 21 | 32 |
| 11 | jubarte | jubarte-final@b4f90acaa85e | 64.6926 | 63.481 | 196 | 0 | 5 | 31 |
| 12 | jubarte-rust | jubarte-rust@b834d6e49fdb | 61.7832 | 59.2784 | 172 | 2 | 6 | 39 |
| 13 | docxodus | 7.0.0 | 58.7507 | 55.0306 | 205 | 3 | 7 | 66 |
| 14 | docxodus | 6.4.0 | 58.7425 | 55.0306 | 205 | 3 | 7 | 66 |
| 15 | superdoc | 1.19.2 | 57.1871 | 55.5996 | 182 | 2 | 4 | 52 |
| 16 | folio | 0.3.1 | 55.3092 | 53.7539 | 205 | 0 | 1 | 75 |
| 17 | redlines | 0.6.1 | 51.284 | 51.7682 | 200 | 0 | 0 | 84 |

### `accepted_changes`

`accepted_changes`

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte | jubarte-final@717311c03d4f | 78.1534 | 80.639 | 166 | 26 | 43 | 14 |
| 2 | docxodus | 7.0.0 | 70.1963 | 74.9182 | 164 | 17 | 44 | 49 |
| 3 | docxodus | 6.4.0 | 68.9994 | 77.1882 | 164 | 14 | 22 | 43 |
| 4 | superdoc | 1.19.2 | 63.818 | 61.1184 | 150 | 2 | 3 | 33 |
| 5 | jubarte-rust | jubarte-rust@b834d6e49fdb | 63.499 | 54.4541 | 147 | 13 | 15 | 72 |
| 6 | folio | 0.3.1 | 57.9094 | 55.608 | 164 | 3 | 4 | 61 |

### `roundtrip`

roundtrip (self-diff → pdf_source)

| # | vendor | version | mean | median | n_docs | exact_100 | ≥90 | <50 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | folio | 0.3.1 | 98.0712 | 100 | 198 | 185 | 190 | 4 |
| 2 | docxodus | 7.0.0 | 97.4281 | 100 | 166 | 148 | 157 | 4 |
| 3 | jubarte | jubarte-final@717311c03d4f | 94.4868 | 100 | 199 | 149 | 165 | 3 |
| 4 | jubarte-rust | jubarte-rust@b834d6e49fdb | 93.1152 | 100 | 171 | 120 | 137 | 6 |
| 5 | superdoc | 1.19.2 | 93.0017 | 100 | 194 | 144 | 158 | 8 |
| 6 | docxodus | 6.4.0 | 92.2445 | 100 | 198 | 144 | 161 | 13 |

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

## All runs (flat)

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
| jubarte | jubarte-final@4f56a39e78ef | 2026-07-11T00:30:15.977616+00:00 | script_redlines | 79.2153 | 78.8195 | 207 |
| jubarte | jubarte-final@6481c2fdbfc0 | 2026-07-11T00:38:01.460324+00:00 | script_redlines | 79.2475 | 78.8195 | 207 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-09T00:19:24.490489+00:00 | accepted_changes | 78.1534 | 80.639 | 166 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-10T00:06:11.537044+00:00 | roundtrip | 94.4868 | 100 | 199 |
| jubarte | jubarte-final@717311c03d4f | 2026-07-09T00:28:15.005270+00:00 | script_redlines | 73.4761 | 73.1343 | 207 |
| jubarte | jubarte-final@755ee30d148c | 2026-07-11T00:22:44.799718+00:00 | script_redlines | 79.2153 | 78.8195 | 207 |
| jubarte | jubarte-final@a56814ce307c | 2026-07-11T01:10:08.212708+00:00 | script_redlines | 79.1225 | 78.7802 | 207 |
| jubarte | jubarte-final@a764898a424c | 2026-07-11T01:22:46.221863+00:00 | script_redlines | 79.1583 | 78.7802 | 207 |
| jubarte | jubarte-final@ac1fcea44646 | 2026-07-10T23:54:03.912780+00:00 | script_redlines | 77.824 | 78.6169 | 207 |
| jubarte | jubarte-final@b4f90acaa85e | 2026-07-11T02:12:18.691781+00:00 | script_redlines | 64.6926 | 63.481 | 196 |
| jubarte-rust | jubarte-rust@6233a48e4ac8 | 2026-07-11T02:17:46.130799+00:00 | script_redlines | 66.3055 | 64.1705 | 196 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-09T17:43:37.147567+00:00 | accepted_changes | 63.499 | 54.4541 | 147 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-10T00:21:53.149640+00:00 | roundtrip | 93.1152 | 100 | 171 |
| jubarte-rust | jubarte-rust@b834d6e49fdb | 2026-07-09T17:36:04.577266+00:00 | script_redlines | 61.7832 | 59.2784 | 172 |
| prebaked | — | 2026-07-08T05:53:47.020343+00:00 | script_redlines | 100 | 100 | 1 |
| redlines | 0.6.1 | 2026-07-10T22:57:16.185376+00:00 | script_redlines | 51.284 | 51.7682 | 200 |
| superdoc | 1.19.2 | 2026-07-09T15:38:31.872437+00:00 | accepted_changes | 63.818 | 61.1184 | 150 |
| superdoc | 1.19.2 | 2026-07-09T18:25:24.395459+00:00 | roundtrip | 93.0017 | 100 | 194 |
| superdoc | 1.19.2 | 2026-07-09T15:34:17.469383+00:00 | script_redlines | 57.1871 | 55.5996 | 182 |
| superdoc | 1.44.1 | 2026-07-09T18:25:37.273372+00:00 | visual_accepted_changes | 59.3354 | 60.971 | 165 |
| superdoc | 1.44.1 | 2026-07-09T18:22:07.033240+00:00 | visual_redlines | 55.3334 | 56.4237 | 164 |
| superdoc | 1.44.1 | 2026-07-09T18:16:46.431642+00:00 | visual_rendering | 58.7798 | 61.2486 | 199 |

## Methodology notes

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

Regenerate: `python3 scripts/export-results-md.py`.
