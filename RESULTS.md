# Benchmark results

This is the medium-detail results view: current rankings by benchmark, with compact
columns and the benchmark methodology kept in the detailed report.

- [Detailed results](RESULTS_DETAILED.md)
- [Historical/docs report](docs/RESULTS.md)
- Raw trend data: `results/bench.jsonl` and `results/speed.jsonl`

<!-- RANKING-START -->
### script_redlines — redline markup vs Word

Sorted by ITT median (failed documents score 0). Mean and Median are completed-only. `~` marks approximate ITT. Jubarte families list best and worst pin; other vendors list each pin. Jubarte rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 763 | 763 | 84.47 | 92.66 | 84.47 | 92.66 | 197 | 0 |
| 2 | jubarte (lossless) | 0.2.0@1286be69c690+git.65014685f960a5c1b9a19250e23fccaa4df5e5ef (best) | 763 | 763 | 82.08 | 91.41 | 82.08 | 91.41 | 186 | 0 |
| 3 | docxodus | 9.8.0 | 760 | 763 | 80.24 | 91.11 | 80.55 | 91.19 | 186 | 4 |
| 4 | jubarte (lossless) | jubarte-final@e7bcd29bb5a9+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a (worst) | 763 | 763 | 81.57 | 89.11 | 81.57 | 89.11 | 182 | 0 |
| 5 | jubarte-ast | 0.2.0@1286be69c690+git.65014685f960a5c1b9a19250e23fccaa4df5e5ef | 763 | 763 | 74.20 | 76.15 | 74.20 | 76.15 | 96 | 0 |
| 6 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 614 | 763 | 50.63 | 56.62 | 62.91 | 61.83 | 9 | 149 |
| 7 | folio | 0.17.1 | 744 | 763 | 50.83 | 50.29 | 52.13 | 50.43 | 0 | 19 |
| 8 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 688 | 763 | 48.38 | 49.69 | 53.65 | 51.31 | 6 | 75 |
| 9 | redlines | 0.6.1 | 745 | 763 | 44.86 | 47.05 | 45.94 | 47.14 | 0 | 18 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs):

ITT Docs differs across rows (763, 232, 230, 207, 196, 195, 168, 9). Those rows are not the same measurement. Compare rows with matching ITT Docs.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.0.0 | 760 | 763 | 80.24 | 91.11 | 80.55 | 91.19 | 186 | 4 |
| 2 | jubarte-wasm | 0.1.0@4b36f4db1d2f+git.ebf1a7996df49f99fb40f4f67713e61cfd19c731 | 763 | 763 | 79.57 | 84.89 | 79.57 | 84.89 | 182 | 0 |
| 3 | jubarte (lossless) | jubarte-final@d43557e042c1 | 763 | 763 | 77.02 | 78.53 | 77.02 | 78.53 | 142 | 0 |
| 4 | jubarte-wasm | 0.1.0 | 763 | 763 | 76.21 | 77.95 | 76.21 | 77.95 | 158 | 0 |
| 5 | jubarte-ast | jubarte-final@a58157a9cd2d | 763 | 763 | 74.20 | 76.15 | 74.20 | 76.15 | 96 | 0 |
| 6 | jubarte-rust | jubarte-rust@9457b6549b5d+git.ebf1a79 | 763 | 763 | 76.40 | 76.04 | 76.40 | 76.04 | 144 | 0 |
| 7 | sanity-word | — | 230 | 230 | 68.17 | 70.48 | 68.17 | 70.48 | 0 | 0 |
| 8 | jubarte-ast | jubarte-final@d43557e042c1 | 755 | 763 | 69.83 | 68.30 | 70.57 | 68.67 | 84 | 9 |
| 9 | ooxmlsdk | — | 232 | 232 | 55.19 | 55.24 | 55.19 | 55.24 | 0 | 0 |
| 10 | docxodus | 6.4.0 | 205 | 207 | 58.17 | 55.00 | 58.74 | 55.03 | 3 | 2 |
| 11 | folio | 0.3.1 | 205 | 207 | 54.77 | 53.52 | 55.31 | 53.75 | 0 | 2 |
| 12 | superdoc | 1.19.2 | 171 | 195 | 49.39 | 52.95 | 56.32 | 54.81 | 2 | 33 |
| 13 | folio | 0.15.13 | 744 | 763 | 50.83 | 50.29 | 52.13 | 50.43 | 0 | 19 |
| 14 | superdoc | 1.21.3 | 665 | 763 | 46.30 | 50.16 | 53.13 | 51.56 | 3 | 115 |
| 15 | docx-redline-js | 0.3.0-ts-migration | 161 | 168 | 48.43 | 50.09 | 50.53 | 50.26 | 0 | 7 |
| 16 | docxodus | 7.0.0 | 196 | 196 | 50.49 | 49.64 | 50.49 | 49.64 | 0 | 0 |
| 17 | superdoc-redlines | 0.2.0 | 703 | 763 | 47.37 | 49.16 | 51.41 | 50.11 | 0 | 68 |
| 18 | docx-redline-js | 0.3.0 | 746 | 763 | 45.16 | 47.22 | 46.19 | 47.42 | 0 | 17 |
| 19 | superdoc | 2.0.0 | 331 | 763 | 19.61 | 0.00 | 45.19 | 46.72 | 1 | 432 |
| 20 | docx-redline-js | — | 2 | 9 | 12.25 | 0.00 | 55.12 | 55.12 | 0 | 7 |

### accepted_changes — accept all changes, match final doc

Sorted by ITT median (failed documents score 0). Mean and Median are completed-only. `~` marks approximate ITT. Jubarte families list best and worst pin; other vendors list each pin. Jubarte rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

ITT Docs differs across rows (198, 178, 144). Those rows are not the same measurement. Compare rows with matching ITT Docs.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 195 | 198 | 88.82 | 100.00 | 90.19 | 100.00 | 119 | 4 |
| 2 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 141 | 144 | 77.46 | 80.63 | 79.10 | 80.77 | 19 | 3 |
| 3 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 177 | 178 | 63.73 | 59.71 | 64.09 | 60.22 | 9 | 1 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs):

ITT Docs differs across rows (174, 166, 164). Those rows are not the same measurement. Compare rows with matching ITT Docs.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 164 | 164 | 69.00 | 77.19 | 69.00 | 77.19 | 14 | 0 |
| 2 | docxodus | 7.0.0 | 164 | 164 | 70.20 | 74.92 | 70.20 | 74.92 | 17 | 0 |
| 3 | superdoc | 1.19.2 | 150 | 166 | 57.67 | 55.82 | 63.82 | 61.12 | 2 | 16 |
| 4 | folio | 0.3.1 | 164 | 174 | 54.58 | 53.96 | 57.91 | 55.61 | 3 | 10 |

### roundtrip — self-diff must not invent noise

Sorted by ITT median (failed documents score 0). Mean and Median are completed-only. `~` marks approximate ITT. Jubarte families list best and worst pin; other vendors list each pin. Jubarte rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 166 | 166 | 100.00 | 100.00 | 100.00 | 100.00 | 166 | 0 |
| 2 | docxodus | 9.8.0 | 166 | 166 | 99.99 | 100.00 | 99.99 | 100.00 | 163 | 0 |
| 3 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 166 | 166 | 99.95 | 100.00 | 99.95 | 100.00 | 161 | 0 |
| 4 | folio | 0.17.1 | 163 | 166 | 97.96 | 100.00 | 99.76 | 100.00 | 159 | 3 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs):

ITT Docs differs across rows (198, 197, 166). Those rows are not the same measurement. Compare rows with matching ITT Docs.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | folio | 0.3.1 | 198 | 198 | 98.07 | 100.00 | 98.07 | 100.00 | 185 | 0 |
| 2 | docxodus | 7.0.0 | 166 | 166 | 97.43 | 100.00 | 97.43 | 100.00 | 148 | 0 |
| 3 | docxodus | 6.4.0 | 198 | 198 | 92.24 | 100.00 | 92.24 | 100.00 | 144 | 0 |
| 4 | superdoc | 1.19.2 | 194 | 197 | 91.59 | 100.00 | 93.00 | 100.00 | 144 | 3 |

### visual_rendering — editor render of plain DOCX

Sorted by ITT median (failed documents score 0). Mean and Median are completed-only. `~` marks approximate ITT. Jubarte families list best and worst pin; other vendors list each pin. Jubarte rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 199 | 199 | 65.27 | 67.88 | 65.27 | 67.88 | 1 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs):

ITT Docs differs across rows (199, 198). Those rows are not the same measurement. Compare rows with matching ITT Docs.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | superdoc | 1.44.1 | 199 | 199 | 58.78 | 61.25 | 58.78 | 61.25 | 0 | 0 |
| 2 | folio | 0.5.0 | 198 | 198 | 59.65 | 55.10 | 59.65 | 55.10 | 0 | 0 |
| 3 | docxodus | 6.4.0-local.1 | 190 | 199 | 53.95 | 49.24 | 56.50 | 49.72 | 0 | 9 |
| 4 | docxodus | 7.0.0 | 190 | 199 | 53.95 | 49.24 | 56.50 | 49.72 | 0 | 9 |

### visual_redlines — editor render of redline DOCX

Sorted by ITT median (failed documents score 0). Mean and Median are completed-only. `~` marks approximate ITT. Jubarte families list best and worst pin; other vendors list each pin. Jubarte rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 155 | 155 | 61.10 | 62.44 | 61.10 | 62.44 | 0 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs):

ITT Docs differs across rows (197, 182, 166, 165). Those rows are not the same measurement. Compare rows with matching ITT Docs.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 145 | 182 | 48.54 | 58.92 | 60.92 | 61.22 | 0 | 37 |
| 2 | superdoc | 1.44.1 | 164 | 165 | 55.00 | 56.34 | 55.33 | 56.42 | 0 | 1 |
| 3 | docxodus | 9.0.0 | 178 | 197 | 54.35 | 55.39 | 60.15 | 57.56 | 1 | 19 |
| 4 | folio | 0.5.0 | 164 | 166 | 50.93 | 51.48 | 51.55 | 51.65 | 0 | 2 |
| 5 | docxodus | 7.0.0 | 164 | 166 | 47.65 | 48.03 | 48.23 | 48.08 | 0 | 2 |

### visual_accepted_changes — editor render of accepted DOCX

Sorted by ITT median (failed documents score 0). Mean and Median are completed-only. `~` marks approximate ITT. Jubarte families list best and worst pin; other vendors list each pin. Jubarte rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 9.8.0 | 155 | 155 | 64.63 | 65.79 | 64.63 | 65.79 | 0 | 0 |

**Legacy corpus** (older `corpus_revision` stamps and unstamped runs):

ITT Docs differs across rows (165, 164, 152). Those rows are not the same measurement. Compare rows with matching ITT Docs.

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 152 | 152 | 62.32 | 62.76 | 62.32 | 62.76 | 0 | 0 |
| 2 | superdoc | 1.44.1 | 165 | 165 | 59.34 | 60.97 | 59.34 | 60.97 | 0 | 0 |
| 3 | folio | 0.5.0 | 164 | 164 | 59.67 | 54.95 | 59.67 | 54.95 | 0 | 0 |

### speed_redlines — generation time (ms per redline)

Sorted by median ms per redline (lower is faster). `*-inproc` rows are in-process; CLI rows include process spawn. [Speed methodology](#speed-methodology). Log: `results/speed.jsonl`.

**Large-N** (`kind: speed_redlines` — often 1000 fixtures → 5000 pairs):

| Rank | Tool | Runtime | Fixtures | Pairs | Median ms | Mean ms | p95 | /s | n | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte-rust-inproc | rust | 1000 | 5000 | 6.20 | 25.34 | 110.76 | 39.5 | 5000 | 0 |
| 2 | docxodus-csharp-inproc | dotnet | 1000 | 5000 | 7.89 | 25.83 | 101.85 | 38.7 | 4880 | 120 |
| 3 | jubarte-final-native | node | 1000 | 5000 | 8.69 | 35.36 | 103.87 | 28.3 | 5000 | 0 |
| 4 | jubarte-rust | rust | 1000 | 5000 | 9.66 | 31.02 | 123.39 | 32.2 | 5000 | 0 |
| 5 | jubarte-wasm | rust-wasm | 1000 | 5000 | 9.67 | 41.49 | 174.03 | 24.1 | 5000 | 0 |
| 6 | jubarte-native | node | 1000 | 5000 | 14.43 | 57.15 | 175.71 | 17.5 | 5000 | 0 |
| 7 | jubarte-final-lossless | node | 1000 | 5000 | 48.76 | 146.81 | 530.20 | 6.8 | 5000 | 0 |
| 8 | jubarte-lossless | node | 1000 | 5000 | 54.64 | 168.18 | 592.49 | 5.9 | 4997 | 3 |
| 9 | docxodus | dotnet-wasm | 1000 | 5000 | 74.59 | 428.23 | 922.48 | 2.3 | 5000 | 0 |
| 10 | docxodus-csharp | dotnet | 50 | 50 | 208.39 | 441.65 | 911.87 | 2.3 | 50 | 0 |

**Microbench** (`kind: speed` — typically ~30–40 pairs × 3 reps):

| Rank | Tool | Runtime | Median ms | Mean ms | p95 | /s | n | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | docx-redline-js | node | 1.45 | 2.79 | 6.91 | 358.4 | 90 | 0 |
| 2 | jubarte-third-docxodus | node | 2.36 | 6.03 | 33.76 | 165.8 | 90 | 0 |
| 3 | jubarte-second-docxodus | node | 2.39 | 5.89 | 31.35 | 169.8 | 90 | 0 |
| 4 | jubarte-lossless | node | 2.46 | 6.60 | 37.58 | 151.6 | 90 | 0 |
| 5 | jubarte-second-native | node | 4.46 | 7.49 | 31.96 | 133.6 | 90 | 0 |
| 6 | jubarte-third-native | node | 4.47 | 7.55 | 33.21 | 132.4 | 90 | 0 |
| 7 | jubarte-native | node | 4.50 | 7.67 | 33.27 | 130.4 | 90 | 0 |
| 8 | jubarte-final-native | node | 6.76 | 18.89 | 115.97 | 52.9 | 90 | 0 |
| 9 | jubarte-final-lossless | node | 18.13 | 52.76 | 311.11 | 19.0 | 90 | 0 |
| 10 | superdoc | python | 40.89 | 94.19 | 619.93 | 10.6 | 90 | 0 |
| 11 | docxodus | node | 75.27 | 236.57 | 1499.68 | 4.2 | 90 | 0 |
<!-- RANKING-END -->

<!-- DOCX-TO-PDF-START -->
### docx_to_pdf — DOCX to PDF vs Word export

428 unique stems. Oracle: pinned Word-export PDFs (`pdf_accepted_word`, `pdf_redlines_randomized`). Failed converts score 0 (ITT). Mean and median are ITT.

| Rank | Tool | Version | n scored | ITT n | ITT Mean | ITT Median | Perfect (100) | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte | jubarte 0.7.0 | 428 | 428 | 60.70 | 62.54 | 0 | 0 |
| 2 | office2pdf | office2pdf 0.6.7 | 413 | 428 | 60.26 | 57.01 | 0 | 15 |
| 3 | pdfitdown | pdfitdown 4.0.0 | 413 | 428 | 60.26 | 57.01 | 0 | 15 |
| 4 | rdocx | rdocx 0.7.0 | 428 | 428 | 50.30 | 48.79 | 0 | 0 |
| 5 | doxx | doxx 0.1.4 | 0 | 428 | 0.00 | 0.00 | 0 | 428 |
<!-- DOCX-TO-PDF-END -->

<!-- DOCX-TO-PDF-NO-REDLINE-START -->
### docx_to_pdf_no_redline_docs — source DOCX to PDF vs Word export

398 unique stems. Oracle: pinned Word-export PDFs (`pdf_source`, `pdf_source_randomized`). Failed converts score 0 (ITT). Mean and median are ITT.

| Rank | Tool | Version | n scored | ITT n | ITT Mean | ITT Median | Perfect (100) | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | office2pdf | office2pdf 0.6.7 | 390 | 398 | 73.82 | 84.34 | 3 | 8 |
| 2 | pdfitdown | pdfitdown 4.0.0 | 390 | 398 | 73.82 | 84.34 | 3 | 8 |
| 3 | libreoffice_convert_rust | LibreOffice Convert Rust v0.1.0 | 398 | 398 | 73.98 | 75.26 | 0 | 0 |
| 4 | jubarte | jubarte 0.7.0 | 398 | 398 | 66.25 | 67.39 | 0 | 0 |
| 5 | docxide-pdf | docxide-pdf v0.17.0 | 398 | 398 | 65.65 | 63.97 | 2 | 0 |
| 6 | rdocx | rdocx 0.7.0 | 398 | 398 | 59.11 | 54.49 | 0 | 0 |
| 7 | dxpdf | dxpdf 0.5.1 | 381 | 398 | 56.73 | 52.52 | 2 | 17 |
| 8 | doxx | doxx 0.1.4 | 0 | 398 | 0.00 | 0.00 | 0 | 398 |
<!-- DOCX-TO-PDF-NO-REDLINE-END -->

<!-- DOCXIDE-METRICS-START -->
### docxide_metrics — DOCX to PDF under docxide-pdf's own metrics

The same 398 `docx_to_pdf_no_redline_docs` fixtures and the same pinned Word-export
oracles as the table above, scored instead with the three metrics
[sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) uses to judge itself
against Word, at its own 150 DPI. **Jaccard** is ink-pixel intersection over union
(a pixel is ink when luma < 200) — placement is everything, a one-line shift sends it
toward zero. **SSIM** uses 8×8 windows with a ±8px vertical search, skipping white
windows. **Text boundary** is the share of lines that begin and end on the same words
as Word, ignoring where the ink landed. Ranked by Jaccard median, docxide-pdf's
headline number. Failed converts score 0 on all three (ITT), as does a document that
produced no scorable page. `≥20%` / `≥75%` are docxide-pdf's own per-case pass
thresholds for Jaccard and SSIM.

| Rank | Tool | Version | n scored | ITT n | Jaccard Mean | Jaccard Median | SSIM Mean | SSIM Median | Text-bnd Mean | Text-bnd Median | Jaccard ≥20% | SSIM ≥75% | Failures |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | jubarte | jubarte 0.8.0 | 398 | 398 | 53.10 | 43.50 | 72.79 | 88.96 | 87.55 | 100.00 | 278 | 225 | 0 |
| 2 | docxide-pdf | docxide-pdf v0.17.0 | 398 | 398 | 24.61 | 14.34 | 43.80 | 35.35 | 80.81 | 100.00 | 100 | 55 | 0 |
<!-- DOCXIDE-METRICS-END -->
