# neurotic-docx-bench

Pixel scores of DOCX tools against Microsoft Word oracles.

| | |
| --- | --- |
| **Scores** | 0–100 per document |
| **Redline oracle** | Word tracked-change markup, rendered by LibreOffice 26.2.4.2 |
| **DOCX→PDF oracle** | SHA-pinned Word-export PDFs in `pdf_accepted_word` and `pdf_redlines_randomized` |
| **Second scorer** | `docxide_metrics` — docxide-pdf's own Jaccard / SSIM / text-boundary suite, same fixtures |
| **Trend log** | `results/bench.jsonl` |
| **Full tables** | [`RESULTS.md`](RESULTS.md) · [`docs/RESULTS.md`](docs/RESULTS.md) |
| **Visual report** | `runs/<run>/report.html` |
| **Speed** | [`docs/SPEED.md`](docs/SPEED.md) |

Jubarte families list best and worst pin per fidelity table. Other vendors list each published pin. Compare rows only within one table and only when `ITT Docs` matches.

```bash
python3 scripts/export-results-md.py          # RESULTS.md + docs/RESULTS.md
bun run update-readme-ranking                 # tables between RANKING markers
uv run bench docx-to-pdf --update-readme      # docx_to_pdf table
uv run bench docxide-metrics --update-readme  # docxide_metrics table (docxide-pdf's scorer)
```

Redline markup is Microsoft Word. Candidate and oracle redline PDFs are both rendered with LibreOffice 26.2.4.2. The oracle DOCX through that pipeline scores 100.

<!-- RANKING-START -->
### script_redlines — redline markup vs Word

Sorted by ITT median (failed documents score 0). Mean and Median are completed-only. `~` marks approximate ITT. Jubarte families list best and worst pin; other vendors list each pin. Jubarte rows with ITT docs < 760 are omitted.

**Current corpus** (newest `corpus_revision` stamp: `5ed816028d99`)

| Rank | Vendor | Version | Docs | ITT Docs | ITT Mean | ITT Median | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@17ea47e9a0d7+git.bf3d07ddd61180e55f327c8e891affd0f6c18d64 | 763 | 763 | 84.47 | 92.66 | 84.47 | 92.66 | 197 | 0 |
| 2 | jubarte (lossless) | jubarte-final@951a6e6b453c+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a (best) | 763 | 763 | 81.99 | 91.31 | 81.99 | 91.31 | 186 | 0 |
| 3 | docxodus | 9.8.0 | 760 | 763 | 80.24 | 91.11 | 80.55 | 91.19 | 186 | 4 |
| 4 | jubarte (lossless) | jubarte-final@e7bcd29bb5a9+git.98e641b1f2ef3fa9b4416b197a4494cd6401fb9a (worst) | 763 | 763 | 81.57 | 89.11 | 81.57 | 89.11 | 182 | 0 |
| 5 | stemma | 0.5.0@2e7bdc832391+git.efaed0c1ecb41142b1465bbb124dd183c385a2b0 | 614 | 763 | 50.63 | 56.62 | 62.91 | 61.83 | 9 | 149 |
| 6 | safe-docx | 0.19.1@e3f092da3639+git.7bd35c876493f2725b095f0190c28d2644962c78 | 688 | 763 | 48.38 | 49.69 | 53.65 | 51.31 | 6 | 75 |
| 7 | redlines | 0.6.1 | 745 | 763 | 44.86 | 47.05 | 45.94 | 47.14 | 0 | 18 |

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
| 3 | jubarte-rust | rust | 1000 | 5000 | 9.66 | 31.02 | 123.39 | 32.2 | 5000 | 0 |
| 4 | jubarte-wasm | rust-wasm | 1000 | 5000 | 9.67 | 41.49 | 174.03 | 24.1 | 5000 | 0 |
| 5 | jubarte-native | node | 1000 | 5000 | 14.43 | 57.15 | 175.71 | 17.5 | 5000 | 0 |
| 6 | jubarte-lossless | node | 1000 | 5000 | 54.64 | 168.18 | 592.49 | 5.9 | 4997 | 3 |
| 7 | docxodus | dotnet-wasm | 1000 | 5000 | 74.59 | 428.23 | 922.48 | 2.3 | 5000 | 0 |
| 8 | docxodus-csharp | dotnet | 50 | 50 | 208.39 | 441.65 | 911.87 | 2.3 | 50 | 0 |

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

**Two scorers, same fixtures.** Both agree on the order, and disagree sharply on the
margin. Under the superdoc-visual-benchmarks core the two converters are almost level
(jubarte 66.25 / 67.39 vs docxide-pdf 65.65 / 63.97); under docxide-pdf's own Jaccard
they are 28.5pp apart on the mean and 29.2pp on the median. Jaccard is a raw ink
intersection-over-union with no spatial tolerance whatsoever, so it collapses the moment
a renderer sets a line a few points off, while the fused score mixes in ink-F1, edge-IoU
and colour ΔE, several of which survive small displacement. It is not only vertical
drift: docxide-pdf's SSIM already searches ±8px vertically and still reads 43.80 against
jubarte's 72.79.

The text-boundary column is the one where the two converters nearly meet — 80.81 vs
87.55 mean, both 100.00 median. Both usually break lines exactly where Word does; what
separates them is where the ink lands afterwards. And docxide-pdf clears its own
published pass bars on 100/398 (Jaccard ≥20%) and 55/398 (SSIM ≥75%) here — those
thresholds were set against its 37 handcrafted fixtures, not against this corpus, so
read them as its stated bar rather than as a verdict from its authors.


### DOCX→PDF no-redline Rust converter deep-dive

These three crates were installed with `cargo install` and benchmarked one-by-one
against the 398 fixture `docx_to_pdf_no_redline_docs` Word-oracle set (144 DPI,
the same oracle and scorer as the main table above).

```bash
cargo install libreoffice_convert_rust dxpdf docxide-pdf
```

**Benchmark command used:**

```bash
uv run bench docx-to-pdf --track docx_to_pdf_no_redline_docs \
  --tool libreoffice_convert_rust --tool dxpdf --tool docxide-pdf \
  --json results/docx_to_pdf_no_redline_new.json \
  --convert-workers 8 --jobs 8
```

| Tool | Version | n scored | ITT Mean | ITT Median | Failures | Perfects |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| libreoffice_convert_rust | LibreOffice Convert Rust v0.1.0 | 398 | 73.98 | 75.26 | 0 | 0 |
| dxpdf | dxpdf 0.5.1 | 381 | 56.73 | 52.52 | 17 | 2 |
| docxide-pdf | docxide-pdf v0.17.0 | 398 | 65.65 | 63.97 | 0 | 2 |

#### libreoffice_convert_rust

- **Crate:** `libreoffice_convert_rust`
- **Installed binary:** `/Users/arthrod/.cargo/bin/libreoffice_convert`
- **Invocation:** `libreoffice_convert <input.docx> <output.pdf> pdf`

| Metric | Value |
| --- | --- |
| n scored | 398 |
| ITT n | 398 |
| ITT Mean | 73.98 |
| ITT Median | 75.26 |
| Mean (scored only) | 73.98 |
| Median (scored only) | 75.26 |
| Min (scored) | 37.21 |
| Max | 98.22 |
| Perfect (>=100) | 0 |
| Failures | 0 |

**Per-feature ITT mean** (documents can carry multiple feature tags):
| Feature | n | Mean | Median |
| --- | ---: | ---: | ---: |
| body_text | 398 | 73.98 | 75.26 |
| table | 88 | 59.20 | 63.20 |
| numbering | 38 | 59.27 | 53.59 |
| image | 40 | 56.46 | 57.82 |
| header_or_footer | 54 | 53.92 | 46.98 |

**Worst 5 scored stems:**
| Stem | Score |
| --- | ---: |
| source__docx_lots_of_comments_addition_removal_redline_removal_v_addition | 37.21 |
| source_randomized__file_27 | 37.26 |
| source__docx_lots_of_comments_addition_redline_addition_v_removal | 39.98 |
| source_randomized__file_16 | 39.98 |
| source__docx_lots_of_comments_addition | 40.33 |

**Best 5 scored stems:**
| Stem | Score |
| --- | ---: |
| source_randomized__file_55 | 98.22 |
| source_randomized__file_64 | 97.76 |
| source__gdocs_comments_export | 97.59 |
| source_randomized__file_40 | 97.14 |
| source_randomized__file_111 | 97.09 |

#### dxpdf

- **Crate:** `dxpdf`
- **Installed binary:** `/Users/arthrod/.cargo/bin/dxpdf`
- **Invocation:** `dxpdf <input.docx> -o <output.pdf>`

| Metric | Value |
| --- | --- |
| n scored | 381 |
| ITT n | 398 |
| ITT Mean | 56.73 |
| ITT Median | 52.52 |
| Mean (scored only) | 59.26 |
| Median (scored only) | 52.67 |
| Min (scored) | 33.15 |
| Max | 100.00 |
| Perfect (>=100) | 2 |
| Failures | 17 |

**Per-feature ITT mean** (documents can carry multiple feature tags):
| Feature | n | Mean | Median |
| --- | ---: | ---: | ---: |
| body_text | 398 | 56.73 | 52.52 |
| table | 88 | 37.42 | 42.32 |
| numbering | 38 | 31.96 | 41.88 |
| image | 40 | 33.11 | 39.05 |
| header_or_footer | 54 | 30.61 | 40.60 |

**Worst 5 scored stems:**
| Stem | Score |
| --- | ---: |
| source_randomized__file_27 | 33.15 |
| source__docx_lots_of_comments_addition_removal_redline_removal_v_addition | 33.16 |
| source__endnotes_sample | 36.89 |
| source__docx_lots_of_comments_addition | 37.74 |
| source__docx_lots_of_comments_addition_redline | 37.74 |

**Best 5 scored stems:**
| Stem | Score |
| --- | ---: |
| source_randomized__file_64 | 100.00 |
| source_randomized__file_55 | 100.00 |
| source_randomized__file_145 | 99.92 |
| source_randomized__file_120 | 99.44 |
| source__gdocs_comments_export | 98.87 |

**Sample generate failures (17 total):**
| Stem | Condensed error |
| --- | --- |
| source__Strict01 | error: Parse error: failed to deserialize XML: expected an integer or decimal measurement |
| source__docx_lots_of_comments_addition_redline_addition_v_removal | error: Parse error: failed to deserialize XML: unknown variant `delInstrText`, expected one of `t`, `delText`, `tab`, `ptab`, `... |
| source__docx_lots_of_comments_addition_removal | error: Parse error: failed to deserialize XML: unknown variant `delInstrText`, expected one of `t`, `delText`, `tab`, `ptab`, `... |
| source__ole_object | error: Parse error: failed to deserialize XML: expected an integer or decimal measurement |
| source__potpourritest | error: Parse error: failed to deserialize XML: unknown variant `delInstrText`, expected one of `t`, `delText`, `tab`, `ptab`, `... |
| source__sample_document_word_repair_of_our_output_iter2_word_repaired_2 | error: Parse error: failed to deserialize XML: unknown variant `delInstrText`, expected one of `t`, `delText`, `tab`, `ptab`, `... |
| source__strict01_sdt_controls | error: Parse error: failed to deserialize XML: expected an integer or decimal measurement |
| source__word_clean_strict01 | error: Parse error: failed to deserialize XML: expected an integer or decimal measurement |

#### docxide-pdf

- **Crate:** `docxide-pdf`
- **Installed binary:** `/Users/arthrod/.cargo/bin/docxide-pdf`
- **Invocation:** `docxide-pdf <input.docx> <output.pdf>`

| Metric | Value |
| --- | --- |
| n scored | 398 |
| ITT n | 398 |
| ITT Mean | 65.65 |
| ITT Median | 63.97 |
| Mean (scored only) | 65.65 |
| Median (scored only) | 63.97 |
| Min (scored) | 36.31 |
| Max | 100.00 |
| Perfect (>=100) | 2 |
| Failures | 0 |

**Per-feature ITT mean** (documents can carry multiple feature tags):
| Feature | n | Mean | Median |
| --- | ---: | ---: | ---: |
| body_text | 398 | 65.65 | 63.97 |
| table | 88 | 52.54 | 50.13 |
| numbering | 38 | 52.20 | 50.07 |
| image | 40 | 49.64 | 50.07 |
| header_or_footer | 54 | 46.72 | 43.36 |

**Worst 5 scored stems:**
| Stem | Score |
| --- | ---: |
| source__docx_lots_of_comments_addition_removal_redline_removal_v_addition | 36.31 |
| source_randomized__file_27 | 36.34 |
| source__I_am_sharing_Microsoft_Word_vs_Google_Docs_Comprehensive_Proof_with_you | 36.44 |
| source__sd_2517_localized_heading_styles | 39.90 |
| source_randomized__file_22 | 39.90 |

**Best 5 scored stems:**
| Stem | Score |
| --- | ---: |
| source_randomized__file_64 | 100.00 |
| source_randomized__file_55 | 100.00 |
| source_randomized__file_145 | 99.92 |
| source_randomized__file_120 | 99.44 |
| source__gdocs_comments_export | 98.87 |

#### Cross-tool observations

- `libreoffice_convert_rust` is a thin Rust wrapper around a local LibreOffice
  installation; it therefore inherits LibreOffice layout. It completed all 398
  fixtures and ties the top of the table with `office2pdf` / `pdfitdown`.
- `docxide-pdf` also converted every fixture and scored between `jubarte` and `rdocx`
  overall, with a lower median than `libreoffice_convert_rust` but two perfect pages.
- `dxpdf` produced the fewest perfectly-matching pages among the three and failed
  on 17 fixtures, mostly with XML parse errors (`delInstrText`, decimal measurements)
  or unsupported relationship types. Its average is dragged down by those 17 ITT zeros.
- When `dxpdf` succeeded, its mean is ~59.3 and median ~52.7, still below the other
  two Rust converters and the LibreOffice-based converters.
- All three are pure Rust at the binary boundary, but only `dxpdf` and `docxide-pdf`
  render without calling an external office suite. `libreoffice_convert_rust` still
  requires `soffice` to be discoverable on `PATH` or via `LIBRE_OFFICE_EXE`.

---

## Benchmarks

Compare vendors only within one table. LibreOffice scores and Playwright scores are separate measurements.

| Benchmark | Input | Oracle |
| --- | --- | --- |
| **`script_redlines`** | `base.docx` + `next.docx` → tool redline DOCX | Word redline PDF |
| **`accepted_changes`** | Accept all `w:ins`/`w:del` on the tool redline | Word redline with changes accepted |
| **`roundtrip`** | Self-diff or the tool’s roundtrip path | Original source PDF (identity = 100) |
| **`visual_rendering`** | Source DOCX in the vendor web editor | `pdf_source` |
| **`visual_redlines`** | Word redline DOCX in the vendor web editor | `pdf_redlines_word` |
| **`visual_accepted_changes`** | Accepted Word redline in the vendor web editor | `pdf_accepted_word` |
| **`docx_to_pdf`** | Accepted Word redline DOCX + randomized redline DOCX | SHA-pinned `pdf_accepted_word` + `pdf_redlines_randomized` |
| **`docx_to_pdf_no_redline_docs`** | Source DOCX + randomized source DOCX | SHA-pinned `pdf_source` + `pdf_source_randomized` |
| **`docxide_metrics`** | The `docx_to_pdf_no_redline_docs` inputs, scored with docxide-pdf's Jaccard / SSIM / text-boundary suite at 150 DPI | Same SHA-pinned `pdf_source` + `pdf_source_randomized` |

`visual_*` loads Word’s DOCX in the editor, not the tool’s own redline. Generator package and editor package are separate pins.

Pins: [`bench.yaml`](bench.yaml).

| Vendor | What runs | Pin | Role |
| --- | --- | --- | --- |
| **jubarte** | `dist/jubarte-final` | content-hash | Generator |
| **jubarte-rust** / **jubarte** (`docx_to_pdf`) | `../jubarte-redlines` CLI | content-hash / 0.7.0 | Generator, converter |
| **jubarte-wasm** | wasm-bindgen over `../jubarte-redlines` | artifact + source commit | Generator |
| **docxodus** | npm `docxodus` `compareDocuments` | 9.8.0 | Generator + viewer |
| **folio** | `@stll/folio-core` `generateRedlineDocx` | 0.17.1 | Generator |
| **folio** (viewer) | `@stll/folio-react` | 0.13.4 | Editor |
| **superdoc** | `superdoc-sdk` | 2.0.0 | Generator |
| **superdoc** (editor) | npm `superdoc` | 2.3.0 | Editor |
| **docx-redline-js** | local TS migration of `@ansonlai/docx-redline-js` | dist pin | Generator |
| **redlines** | [houfu/redlines](https://github.com/houfu/redlines) + `nupunkt==0.6.0` | 0.6.1 | Generator |
| **superdoc-redlines** | [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) | 0.2.0 | Generator |
| **stemma** | [stemma-sh/stemma](https://github.com/stemma-sh/stemma) `stemma compare` | 0.5.0 | Generator |
| **safe-docx** | [UseJunior/safe-docx](https://github.com/UseJunior/safe-docx) at `7bd35c8` | content-hash | Generator |
| **rdocx** | [tensorbee/rdocx](https://github.com/tensorbee/rdocx) `convert --to pdf` | 0.7.0 | Converter |
| **office2pdf** | [developer0hye/office2pdf](https://github.com/developer0hye/office2pdf) | 0.6.7 | Converter |
| **pdfitdown** | [AstraBert/PdfItDown](https://github.com/AstraBert/PdfItDown) (`office2pdf` for Office) | 4.0.0 | Converter |
| **doxx** | [bgreenwell/doxx](https://github.com/bgreenwell/doxx) | 0.1.4 | Converter (no PDF export) |
| **libreoffice_convert_rust** | [dnrops/libreoffice_convert_rust](https://gitcode.com/dnrops/libreoffice_convert_rust) | 0.1.0 | Converter |
| **dxpdf** | [nerdy-pro/dxpdf](https://github.com/nerdy-pro/dxpdf) | 0.5.1 | Converter |
| **docxide-pdf** | [sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) | 0.17.0 | Converter |

---

## Quick start

Python 3.14 (`uv`), Bun or Node, LibreOffice 26.2.4.2 on `PATH`.

```bash
uv sync
bun install --frozen-lockfile
cd src/neurotic_docx_bench/utils/docxodus && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/docx-redline-js && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/folio && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/superdoc && bun install --frozen-lockfile && cd -
cd harness/folio-viewer && bun install --frozen-lockfile && cd -

uv run bench run --only jubarte-final-lossless --limit 5
uv run bench run
uv run bench docx-to-pdf --tool jubarte --tool rdocx --tool office2pdf --tool pdfitdown --tool doxx
```

Each `bench run`: resolve `tool_version` → generate → render → score → append `results/bench.jsonl` → gate vs snapshot.

```bash
uv run bench run --only docxodus --limit 5 --no-emit
uv run bench accept-scores jubarte
uv run bench render <docx-dir> <work-dir> -b soffice
uv run bench compare <candidate-pdfs> <oracle-pdfs> --tool name
```

---

## Scoring

1. Match candidate PDF to oracle PDF by `<base>_<next>` (redlines) or plain stem (`docx_to_pdf`, roundtrip).
2. Raster each page at 144 DPI.
3. Score with SSIM, ink-F1, edge-IoU, colour ΔE, and blob metrics (0–100).

Scoring core is a verbatim lift of [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks). `tests/test_parity.py` checks byte-identical behaviour. Page-count mismatch is recorded; only `min(pages)` is scored.

Gate: 100 always passes. Per-document drop vs snapshot → warning. Aggregate mean or median drop → fail. Promote with `uv run bench accept-scores <tool>`.

---

## Speed methodology

Data: `results/speed.jsonl`, `results/redline_speed_bench/`. Detail: [`docs/SPEED.md`](docs/SPEED.md).

| Mode | Measures |
| --- | --- |
| Warm in-process (`*-inproc`) | Compare work in one long-lived process |
| CLI | Process spawn + init + compare |
| WASM | In-process after load |
| Microbench | Small N × reps |

Large-N (`scripts/redline_speed_bench.ts`): up to 1000 unique `.docx` → 5000 pairs (Mulberry32 seed 42), warmup, `performance.now()`, failures excluded.

```bash
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --out results/speed.jsonl
bun run redline-speed-bench:warm
```

---

## Project map

```
bench.yaml                 # runs, pins, oracles
corpus/word_based/         # redline DOCX + LibreOffice oracle PDFs
corpus/no_comments_pdf_was_generated_by_word/  # Word-exported PDFs (docx_to_pdf)
results/bench.jsonl        # redline trend log
results/docx_to_pdf_500.json
src/neurotic_docx_bench/
src/neurotic_docx_bench/utils/docxide-metrics/  # vendored docxide-pdf scorer (Rust)
results/docxide_metrics.json
scripts/
```

[`AGENTS.md`](AGENTS.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Credits

- [balalofernandez/docx-revisions](https://github.com/balalofernandez/docx-revisions) — accept/reject (`bench accept` / `reject`)
- [superdoc-dev/superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks) — scoring core
- [sverrejb/docxide-pdf](https://github.com/sverrejb/docxide-pdf) (Apache-2.0) — the `docxide_metrics`
  scorer. Its Jaccard / SSIM / text-boundary metrics are lifted verbatim from `tests/common/`
  into `src/neurotic_docx_bench/utils/docxide-metrics/`; `tests/test_docxide_metrics_parity.py`
  requires the same numbers as its own `page-metrics` binary. Also benchmarked as a converter.
- [JSv4/docxodus](https://github.com/JSv4/docxodus), [react-docxodus-viewer](https://github.com/JSv4/react-docxodus-viewer) (MIT)
- [AnsonLai/docx-redline-js](https://github.com/AnsonLai/docx-redline-js) (MIT)
- [houfu/redlines](https://github.com/houfu/redlines) (MIT)
- [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) (Apache-2.0)
- [stella/folio](https://github.com/stella/folio) (Apache-2.0)
- [Harbour-Enterprises/SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc) (AGPL-3.0)
- [stemma-sh/stemma](https://github.com/stemma-sh/stemma)
- [UseJunior/safe-docx](https://github.com/UseJunior/safe-docx)
- [tensorbee/rdocx](https://github.com/tensorbee/rdocx)
- [developer0hye/office2pdf](https://github.com/developer0hye/office2pdf)
- [AstraBert/PdfItDown](https://github.com/AstraBert/PdfItDown)
- [bgreenwell/doxx](https://github.com/bgreenwell/doxx)

## License

Scoring core derived from [superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks). This repository is **AGPL-3.0-only**. See [`LICENSE`](LICENSE).

Published scores are measurements, not endorsements. Microsoft Word is a trademark of Microsoft.
