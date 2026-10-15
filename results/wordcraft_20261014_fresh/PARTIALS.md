# Wordcraft CLI benchmark — partial

Updated: 2026-10-14 20:16:35 EDT.

Seed 20261014. 400 unique base→next comparisons and 400 distinct conversion DOCX, in two cohorts: the original 200+200 sample and a seeded, stratified expansion drawn before any vendor ran. Word eligibility is established first: a fixture for which Word could not produce a fresh oracle in this run is excluded and logged (`comparison_exclusions.json`, `conversion_exclusions.json`); Word-session failures were retried, not excluded. Inputs are frozen before vendor generation; vendor failures are never replaced and count as zero.

Comparison redlines are rendered by Word 16.115. All tools in each task use identical per-fixture Word PDF oracles, 144 DPI and the unchanged scorer. Its two kernels (mean CIEDE2000 and SSIM) ran on NumPy for the rows scored early and on the torch port over Apple MPS for the rest (`BENCH_DEVICE=mps`); `tests/test_kernels.py` holds the torch port within 1e-3 of NumPy per document (15 passed on this machine), and every scored row records its `scorer_backend` (counts below). Full-cohort means include tool failures as zero. Partial means include only completed scores and can be biased toward faster documents.

Lanes. The original run: Wordcraft CLI 0.6.1, jubarte 0.11.0 and 0.12.0, and docxodus 12.6.5 (comparisons) or LibreOffice 26.8.1.1 (conversions). Added the same day, on the same frozen fixtures, oracles, renderer and scorer, at their newest releases: the top three non-jubarte tools of every past results table in RESULTS.md (comparisons: docxodus, stemma, folio, superdoc; conversions: office2pdf, pdfitdown, rdocx, libreoffice_convert_rust, docxide-pdf, PyMuPDF Pro, with LibreOffice already present), plus Wordcraft CLI 0.7.0 and docxodus 13.0.0, released while this run was in progress. Each tool runs through the bench's own adapter for it, one document per process; exact versions and hashes are in `tools.json`. jubarte is author-affiliated.

## Comparisons

| Tool | Scored / 400 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft | 392 | 8 | 0 | 47.32 | 46.01 | 46.01 | 14.48 | 118 |
| wordcraft-0.7.0 | 392 | 8 | 0 | 47.36 | 46.05 | 46.01 | 25.38 | 118 |
| jubarte-0.11.0 | 399 | 1 | 0 | 76.90 | 76.75 | 84.41 | 51.63 | 29 |
| jubarte-0.12.0 | 395 | 5 | 0 | 76.34 | 76.18 | 84.44 | 37.80 | 28 |
| docxodus-12.6.5 | 369 | 31 | 0 | 67.19 | 66.99 | 80.40 | 8206.79 | 31 |
| docxodus-13.0.0 (partial) | 9 | 21 | 370 | 61.43 | 60.94 | 61.89 | 849.89 | 1 |
| folio-0.60.0 (partial) | 0 | 133 | 267 | — | — | — | 863.82 | 0 |
| stemma-0.5.0 (partial) | 0 | 104 | 296 | — | — | — | 228.36 | 0 |
| superdoc-2.20.0 (partial) | 0 | 364 | 36 | — | — | — | 2750.51 | 0 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization. Each tool lane ran serially, one document at a time, but on a shared machine: Word batches, scoring and other sessions were running (load average 35–77 on 12 cores), so latencies are observations, not a throughput ranking. A blank median means it has not yet been measured for this build and cohort.

Scorer backend per tool (scored rows): wordcraft: torch-mps 392; wordcraft-0.7.0: torch-mps 392; jubarte-0.11.0: torch-mps 399; jubarte-0.12.0: torch-mps 395; docxodus-12.6.5: torch-mps 369; docxodus-13.0.0: torch-mps 9; folio-0.60.0: ; stemma-0.5.0: ; superdoc-2.20.0: .

wordcraft-0.7.0 minus Wordcraft, pagefair: **+0.04 points**, paired bootstrap 95% interval [-0.01, +0.12], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
jubarte-0.11.0 minus Wordcraft, pagefair: **+30.74 points**, paired bootstrap 95% interval [+28.98, +32.57], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
jubarte-0.12.0 minus Wordcraft, pagefair: **+30.17 points**, paired bootstrap 95% interval [+28.26, +32.07], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
docxodus-12.6.5 minus Wordcraft, pagefair: **+20.98 points**, paired bootstrap 95% interval [+18.62, +23.32], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
docxodus-13.0.0 minus Wordcraft, pagefair: **+11.30 points**, paired bootstrap 95% interval [-6.63, +26.03], n=9. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By cohort (pagefair mean, failures as zero)

| Cohort | N | wordcraft | wordcraft-0.7.0 | jubarte-0.11.0 | jubarte-0.12.0 | docxodus-12.6.5 | docxodus-13.0.0 | folio-0.60.0 | stemma-0.5.0 | superdoc-2.20.0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cohort 1 | 174 | 44.92 | 45.01 | 76.62 | 75.89 | 67.04 | 60.94 | — | — | — |
| cohort 2 | 226 | 46.85 | 46.84 | 76.84 | 76.41 | 66.96 | — | — | — | — |

### wordcraft → wordcraft-0.7.0

Failure transitions: 392 scored by both, 0 failed in the old version and scored in the new, 0 scored in the old and failed in the new, 8 failed in both. On the documents both scored, new minus old pagefair averages 0.04 points (1 improved, 0 regressed by more than 0.5).

### jubarte-0.11.0 → jubarte-0.12.0

Failure transitions: 395 scored by both, 0 failed in the old version and scored in the new, 4 scored in the old and failed in the new, 1 failed in both. On the documents both scored, new minus old pagefair averages 0.00 points (35 improved, 42 regressed by more than 0.5).

### By state

| State | N | wordcraft | wordcraft-0.7.0 | jubarte-0.11.0 | jubarte-0.12.0 | docxodus-12.6.5 | docxodus-13.0.0 | folio-0.60.0 | stemma-0.5.0 | superdoc-2.20.0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tracking_without_comments | 245 | 47.74 | 47.74 | 75.84 | 74.93 | 66.26 | 61.77 | — | — | — |
| with_comments_tracking | 150 | 43.42 | 43.51 | 77.57 | 77.55 | 68.77 | 60.28 | — | — | — |
| with_comments_clean | 3 | 40.54 | 40.58 | 95.61 | 94.98 | 39.97 | — | — | — | — |
| clean | 2 | 37.06 | 37.12 | 98.35 | 98.34 | 63.79 | — | — | — | — |

## Conversions

| Tool | Scored / 400 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft | 400 | 0 | 0 | 55.46 | 55.18 | 52.82 | 41.18 | 72 |
| wordcraft-0.7.0 | 400 | 0 | 0 | 56.59 | 56.42 | 53.82 | 68.80 | 33 |
| jubarte-0.11.0 | 400 | 0 | 0 | 76.24 | 76.19 | 79.75 | 27.53 | 12 |
| jubarte-0.12.0 | 400 | 0 | 0 | 79.93 | 79.89 | 82.45 | 28.28 | 12 |
| soffice | 398 | 2 | 0 | 54.82 | 54.70 | 47.87 | 1894.46 | 33 |
| office2pdf-0.8.1 | 398 | 2 | 0 | 48.66 | 45.89 | 44.45 | 658.24 | 134 |
| pdfitdown-4.2.0 | 397 | 3 | 0 | 43.48 | 39.41 | 41.95 | 562.64 | 173 |
| rdocx-0.16.0 | 397 | 3 | 0 | 50.69 | 47.80 | 45.90 | 291.96 | 111 |
| docxide-pdf-0.18.4 | 400 | 0 | 0 | 55.90 | 54.90 | 52.37 | 43.59 | 66 |
| libreoffice_convert_rust-0.1.0 (partial) | 9 | 2 | 389 | 52.25 | 51.87 | 47.81 | 1927.04 | 1 |
| pymupdf-pro-1.28.2 (≤3-page subset, n=253) | 250 | 3 | 0 | 56.48 | 56.24 | 48.50 | 770.49 | 12 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization. Each tool lane ran serially, one document at a time, but on a shared machine: Word batches, scoring and other sessions were running (load average 35–77 on 12 cores), so latencies are observations, not a throughput ranking. A blank median means it has not yet been measured for this build and cohort.

Scorer backend per tool (scored rows): wordcraft: numpy 99, torch-mps 301; wordcraft-0.7.0: torch-mps 400; jubarte-0.11.0: numpy 144, torch-mps 256; jubarte-0.12.0: torch-mps 400; soffice: torch-mps 398; office2pdf-0.8.1: torch-mps 398; pdfitdown-4.2.0: torch-mps 397; rdocx-0.16.0: torch-mps 397; docxide-pdf-0.18.4: torch-mps 400; libreoffice_convert_rust-0.1.0: torch-mps 9; pymupdf-pro-1.28.2: torch-mps 250.

wordcraft-0.7.0 minus Wordcraft, pagefair: **+1.24 points**, paired bootstrap 95% interval [+0.81, +1.69], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
jubarte-0.11.0 minus Wordcraft, pagefair: **+21.02 points**, paired bootstrap 95% interval [+19.45, +22.58], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
jubarte-0.12.0 minus Wordcraft, pagefair: **+24.71 points**, paired bootstrap 95% interval [+23.31, +26.15], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
soffice minus Wordcraft, pagefair: **-0.48 points**, paired bootstrap 95% interval [-1.64, +0.70], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
office2pdf-0.8.1 minus Wordcraft, pagefair: **-9.29 points**, paired bootstrap 95% interval [-10.79, -7.85], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
pdfitdown-4.2.0 minus Wordcraft, pagefair: **-15.77 points**, paired bootstrap 95% interval [-17.14, -14.48], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
rdocx-0.16.0 minus Wordcraft, pagefair: **-7.38 points**, paired bootstrap 95% interval [-8.76, -6.03], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
docxide-pdf-0.18.4 minus Wordcraft, pagefair: **-0.28 points**, paired bootstrap 95% interval [-1.54, +1.06], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
libreoffice_convert_rust-0.1.0 minus Wordcraft, pagefair: **-2.70 points**, paired bootstrap 95% interval [-8.41, +4.22], n=9. This interval describes the selected benchmark cohort, not a population-wide guarantee.
pymupdf-pro-1.28.2 minus Wordcraft, pagefair: **-4.08 points**, paired bootstrap 95% interval [-5.76, -2.34], n=253. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By cohort (pagefair mean, failures as zero)

| Cohort | N | wordcraft | wordcraft-0.7.0 | jubarte-0.11.0 | jubarte-0.12.0 | soffice | office2pdf-0.8.1 | pdfitdown-4.2.0 | rdocx-0.16.0 | docxide-pdf-0.18.4 | libreoffice_convert_rust-0.1.0 | pymupdf-pro-1.28.2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cohort 1 | 197 | 54.19 | 55.12 | 77.14 | 79.69 | 54.73 | 45.59 | 38.32 | 47.62 | 53.28 | 51.87 | 58.04 |
| cohort 2 | 203 | 56.14 | 57.69 | 75.28 | 80.08 | 54.67 | 46.18 | 40.48 | 47.98 | 56.47 | — | 54.83 |

### wordcraft → wordcraft-0.7.0

Failure transitions: 400 scored by both, 0 failed in the old version and scored in the new, 0 scored in the old and failed in the new, 0 failed in both. On the documents both scored, new minus old pagefair averages 1.24 points (103 improved, 22 regressed by more than 0.5).

### jubarte-0.11.0 → jubarte-0.12.0

Failure transitions: 400 scored by both, 0 failed in the old version and scored in the new, 0 scored in the old and failed in the new, 0 failed in both. On the documents both scored, new minus old pagefair averages 3.69 points (136 improved, 10 regressed by more than 0.5).

### Conversions whose Word PDF has at most 3 pages (n=253)

Every conversion tool on the same subset, so PyMuPDF Pro (unlicensed: it converts only the first 3 pages) is compared like for like. Pagefair mean, failures as zero.

| Tool | Scored / 253 | Mean pagefair | Median v1 |
|---|---:|---:|---:|
| jubarte-0.12.0 | 253 | 85.08 | 86.04 |
| jubarte-0.11.0 | 253 | 79.54 | 83.47 |
| wordcraft-0.7.0 | 253 | 61.33 | 58.51 |
| docxide-pdf-0.18.4 | 253 | 60.42 | 59.00 |
| soffice | 253 | 60.32 | 58.96 |
| wordcraft | 253 | 60.32 | 58.00 |
| libreoffice_convert_rust-0.1.0 | 6 | 59.77 | 53.71 |
| pymupdf-pro-1.28.2 | 250 | 56.24 | 48.50 |
| rdocx-0.16.0 | 252 | 55.06 | 48.50 |
| office2pdf-0.8.1 | 251 | 52.68 | 47.86 |
| pdfitdown-4.2.0 | 251 | 45.58 | 46.71 |

### By state

| State | N | wordcraft | wordcraft-0.7.0 | jubarte-0.11.0 | jubarte-0.12.0 | soffice | office2pdf-0.8.1 | pdfitdown-4.2.0 | rdocx-0.16.0 | docxide-pdf-0.18.4 | libreoffice_convert_rust-0.1.0 | pymupdf-pro-1.28.2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| tracking_without_comments | 100 | 57.81 | 59.84 | 76.49 | 76.99 | 61.83 | 42.51 | 34.16 | 44.94 | 50.42 | 61.46 | 57.96 |
| with_comments_clean | 100 | 50.34 | 50.83 | 69.76 | 79.67 | 47.11 | 44.19 | 41.33 | 46.56 | 56.03 | 47.69 | 50.49 |
| with_comments_tracking | 100 | 49.79 | 50.73 | 73.58 | 77.67 | 42.91 | 38.03 | 34.52 | 37.37 | 47.13 | 48.08 | 40.81 |
| clean | 100 | 62.78 | 64.29 | 84.95 | 85.22 | 66.93 | 58.82 | 47.64 | 62.33 | 66.02 | 43.19 | 70.80 |

## Timing and limits

Observed Wordcraft CLI medians: comparison 14.48 ms, conversion 41.18 ms. Each invocation includes process startup, file loading and saving. Three warmups per lane were excluded. Timing is a single-pass observation; other work was active on the machine, and the Docxodus wrapper includes WASM initialization. Do not treat these numbers as a rigorous throughput ranking.

The primary conversion command uses `--markup`, matching Word oracle PDFs that display comments and tracked changes. Wordcraft comparison uses word granularity with formatting/case/whitespace differences enabled. Unsupported Wordcraft compare options are documented in its own CLI command catalog.

All reported vendor outputs, Word references and scores are freshly generated in this run. Official jubarte 0.11.0 and 0.12.0 release archives are verified against their SHA256SUMS. No historical scores or candidate/reference PDFs are reused.

Word redlines and all Word oracle PDF exports are made by invoking the repository scripts/word_redline.py and scripts/word_pdf.py directly (hashes in `oracle_provenance.json` and `word_400/driver_invocations.jsonl`); every vendor redline Word could not export gets one retry in a fresh Word session, the same rule for every tool. Word-oracle exclusions and their replacements are recorded before vendor generation; no fixture is substituted after a vendor failure.

Both raw v1 and pagefair are reported. The raw scorer compares shared pages; pagefair additionally accounts for extra or missing pages. Failure-aware means and common-success paired comparisons distinguish tool failure from fidelity among readable outputs.

This is a balanced stress sample, not a frequency-weighted estimate of the full corpus. All 400 comparison input pairs and all 400 conversion content hashes are distinct. The corpus holds only 174 distinct with_comments_tracking, 3 with_comments_clean and 2 clean comparison pairs, so comparisons take every Word-eligible pair of those states and tracking_without_comments fills the rest.

Rasters are discarded after each scored document. DOCX, PDF, manifests, logs and score checkpoints are retained.

## Evidence

- `comparisons.csv`, `conversions.csv`, `sample_provenance.json`: frozen selection, seed, hub revision and hashes.
- `tools.json`, `oracle_provenance.json`, `ORACLES_READY.json`: exact binaries, Word version, the committed driver hashes (`drivers_ee49054d/`) and the source of every oracle.
- `comparison_exclusions.json`, `conversion_exclusions.json`, `word_400/selection.json`, `word_400/candidates_*.csv`: Word-ineligible fixtures with every attempt, and the seeded reserve order.
- `word_400/driver_invocations.jsonl` and `word_400/*/driver.log`: every Word batch (command, driver hash, exclusive-Word flag, PDFs produced) and its alerts; `word_400/contaminated/`: batches aborted because another session touched Word, rerun from scratch.
- `operations.jsonl`: invocation, timing, exit status, revision XML and output hashes.
- `compare/<tool>/word_pdf.log`, `render_retry.json`, `render_failures.json`, `generate_failures.json`: vendor redline export by Word and every failure.
- Per-tool `scores.json` and `scores.checkpoint.jsonl`: full metrics (with `scorer_backend`) and resumable progress.

## Fresh Word oracle preparation

- comparison_references_valid: 174
- comparison_corrected_writable_retry: 44
- comparison_permission_failures_withdrawn: 30
- previous_reserve_selection_withdrawn: True
- conversion_references_valid: 0
- vendor_generation_started: False
- vendor_scores: 0
- comparison_word_exclusions: 26
- updated_at: 2026-10-14 02:54:19
