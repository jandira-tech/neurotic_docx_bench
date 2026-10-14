# Wordcraft CLI benchmark — partial

Updated: 2026-10-14 05:50:50 EDT.

Seed 20261014. 400 unique base→next comparisons and 400 distinct conversion DOCX, in two cohorts: the original 200+200 sample and a seeded, stratified expansion drawn before any vendor ran. Word eligibility is established first: a fixture for which Word could not produce a fresh oracle in this run is excluded and logged (`comparison_exclusions.json`, `conversion_exclusions.json`); Word-session failures were retried, not excluded. Inputs are frozen before vendor generation; vendor failures are never replaced and count as zero.

Comparison redlines are rendered by Word 16.115. All tools in each task use identical per-fixture Word PDF oracles, 144 DPI and the unchanged scorer. Its two kernels (mean CIEDE2000 and SSIM) ran on NumPy for the rows scored early and on the torch port over Apple MPS for the rest (`BENCH_DEVICE=mps`); `tests/test_kernels.py` holds the torch port within 1e-3 of NumPy per document (15 passed on this machine), and every scored row records its `scorer_backend` (counts below). Full-cohort means include tool failures as zero. Partial means include only completed scores and can be biased toward faster documents.

## Comparisons

| Tool | Scored / 400 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft (partial) | 192 | 8 | 200 | 48.38 | 47.07 | 45.26 | 14.48 | 62 |
| jubarte-0.11.0 (partial) | 47 | 1 | 352 | 79.62 | 79.40 | 84.93 | 51.63 | 3 |
| jubarte-0.12.0 (partial) | 0 | 0 | 400 | — | — | — | 37.80 | 0 |
| docxodus-12.6.5 (partial) | 0 | 0 | 400 | — | — | — | 6774.04 | 0 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization. Each tool lane ran serially, one document at a time, but on a shared machine: Word batches, scoring and other sessions were running (load average 35–60 on 12 cores), so latencies are observations, not a throughput ranking. A blank median means it has not yet been measured for this build and cohort.

Scorer backend per tool (scored rows): wordcraft: torch-mps 192; jubarte-0.11.0: torch-mps 47; jubarte-0.12.0: ; docxodus-12.6.5: .

jubarte-0.11.0 minus Wordcraft, pagefair: **+30.19 points**, paired bootstrap 95% interval [+25.89, +34.79], n=47. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By cohort (pagefair mean, failures as zero)

| Cohort | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | docxodus-12.6.5 |
|---|---:|---:|---:|---:|---:|
| cohort 1 | 174 | 46.56 | 79.40 | — | — |
| cohort 2 | 226 | 50.42 | — | — | — |

### By state

| State | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | docxodus-12.6.5 |
|---|---:|---:|---:|---:|---:|
| tracking_without_comments | 245 | 48.69 | 76.69 | — | — |
| with_comments_tracking | 150 | 45.30 | 83.40 | — | — |
| with_comments_clean | 3 | 40.54 | — | — | — |
| clean | 2 | 37.06 | — | — | — |

## Conversions

| Tool | Scored / 400 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft | 400 | 0 | 0 | 55.46 | 55.18 | 52.82 | 41.18 | 72 |
| jubarte-0.11.0 | 400 | 0 | 0 | 76.24 | 76.19 | 79.75 | 27.53 | 12 |
| jubarte-0.12.0 (partial) | 358 | 0 | 42 | 80.15 | 80.10 | 82.83 | 28.28 | 10 |
| soffice (partial) | 0 | 2 | 398 | — | — | — | 1894.46 | 0 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization. Each tool lane ran serially, one document at a time, but on a shared machine: Word batches, scoring and other sessions were running (load average 35–60 on 12 cores), so latencies are observations, not a throughput ranking. A blank median means it has not yet been measured for this build and cohort.

Scorer backend per tool (scored rows): wordcraft: numpy 99, torch-mps 301; jubarte-0.11.0: numpy 144, torch-mps 256; jubarte-0.12.0: torch-mps 358; soffice: .

jubarte-0.11.0 minus Wordcraft, pagefair: **+21.02 points**, paired bootstrap 95% interval [+19.45, +22.58], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
jubarte-0.12.0 minus Wordcraft, pagefair: **+24.59 points**, paired bootstrap 95% interval [+22.97, +26.13], n=358. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By cohort (pagefair mean, failures as zero)

| Cohort | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | soffice |
|---|---:|---:|---:|---:|---:|
| cohort 1 | 197 | 54.19 | 77.14 | 79.69 | — |
| cohort 2 | 203 | 56.14 | 75.28 | 80.61 | — |

### By state

| State | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | soffice |
|---|---:|---:|---:|---:|---:|
| tracking_without_comments | 100 | 57.81 | 76.49 | 77.57 | — |
| with_comments_clean | 100 | 50.34 | 69.76 | 79.22 | — |
| with_comments_tracking | 100 | 49.79 | 73.58 | 77.95 | — |
| clean | 100 | 62.78 | 84.95 | 85.22 | — |

## Timing and limits

Observed Wordcraft CLI medians: comparison 14.54 ms, conversion 41.34 ms. Each invocation includes process startup, file loading and saving. Three warmups per lane were excluded. Timing is a single-pass observation; other work was active on the machine, and the Docxodus wrapper includes WASM initialization. Do not treat these numbers as a rigorous throughput ranking.

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
