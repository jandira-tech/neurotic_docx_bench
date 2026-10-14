# Wordcraft CLI benchmark — complete

Updated: 2026-10-14 11:50:34 EDT.

Seed 20261014. 400 unique base→next comparisons and 400 distinct conversion DOCX, in two cohorts: the original 200+200 sample and a seeded, stratified expansion drawn before any vendor ran. Word eligibility is established first: a fixture for which Word could not produce a fresh oracle in this run is excluded and logged (`comparison_exclusions.json`, `conversion_exclusions.json`); Word-session failures were retried, not excluded. Inputs are frozen before vendor generation; vendor failures are never replaced and count as zero.

Comparison redlines are rendered by Word 16.115. All tools in each task use identical per-fixture Word PDF oracles, 144 DPI and the unchanged scorer. Its two kernels (mean CIEDE2000 and SSIM) ran on NumPy for the rows scored early and on the torch port over Apple MPS for the rest (`BENCH_DEVICE=mps`); `tests/test_kernels.py` holds the torch port within 1e-3 of NumPy per document (15 passed on this machine), and every scored row records its `scorer_backend` (counts below). Full-cohort means include tool failures as zero. Partial means include only completed scores and can be biased toward faster documents.

## Comparisons

| Tool | Scored / 400 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft | 392 | 8 | 0 | 47.32 | 46.01 | 46.01 | 14.48 | 118 |
| jubarte-0.11.0 | 399 | 1 | 0 | 76.90 | 76.75 | 84.41 | 51.63 | 29 |
| jubarte-0.12.0 | 395 | 5 | 0 | 76.34 | 76.18 | 84.44 | 37.80 | 28 |
| docxodus-12.6.5 | 369 | 31 | 0 | 67.19 | 66.99 | 80.40 | 8206.79 | 31 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization. Each tool lane ran serially, one document at a time, but on a shared machine: Word batches, scoring and other sessions were running (load average 35–77 on 12 cores), so latencies are observations, not a throughput ranking.

Scorer backend per tool (scored rows): wordcraft: torch-mps 392; jubarte-0.11.0: torch-mps 399; jubarte-0.12.0: torch-mps 395; docxodus-12.6.5: torch-mps 369.

jubarte-0.11.0 minus Wordcraft, pagefair: **+30.74 points**, paired bootstrap 95% interval [+28.98, +32.57], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
jubarte-0.12.0 minus Wordcraft, pagefair: **+30.17 points**, paired bootstrap 95% interval [+28.26, +32.07], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
docxodus-12.6.5 minus Wordcraft, pagefair: **+20.98 points**, paired bootstrap 95% interval [+18.62, +23.32], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By cohort (pagefair mean, failures as zero)

| Cohort | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | docxodus-12.6.5 |
|---|---:|---:|---:|---:|---:|
| cohort 1 | 174 | 44.92 | 76.62 | 75.89 | 67.04 |
| cohort 2 | 226 | 46.85 | 76.84 | 76.41 | 66.96 |

### jubarte 0.11.0 → 0.12.0

Failure transitions: 395 scored by both, 0 failed in 0.11.0 and scored in 0.12.0, 4 scored in 0.11.0 and failed in 0.12.0, 1 failed in both. On the documents both scored, 0.12.0 minus 0.11.0 pagefair averages 0.00 points (35 improved, 42 regressed by more than 0.5).

### By state

| State | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | docxodus-12.6.5 |
|---|---:|---:|---:|---:|---:|
| tracking_without_comments | 245 | 47.74 | 75.84 | 74.93 | 66.26 |
| with_comments_tracking | 150 | 43.42 | 77.57 | 77.55 | 68.77 |
| with_comments_clean | 3 | 40.54 | 95.61 | 94.98 | 39.97 |
| clean | 2 | 37.06 | 98.35 | 98.34 | 63.79 |

## Conversions

| Tool | Scored / 400 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft | 400 | 0 | 0 | 55.46 | 55.18 | 52.82 | 41.18 | 72 |
| jubarte-0.11.0 | 400 | 0 | 0 | 76.24 | 76.19 | 79.75 | 27.53 | 12 |
| jubarte-0.12.0 | 400 | 0 | 0 | 79.93 | 79.89 | 82.45 | 28.28 | 12 |
| soffice | 398 | 2 | 0 | 54.82 | 54.70 | 47.87 | 1894.46 | 33 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization. Each tool lane ran serially, one document at a time, but on a shared machine: Word batches, scoring and other sessions were running (load average 35–77 on 12 cores), so latencies are observations, not a throughput ranking.

Scorer backend per tool (scored rows): wordcraft: numpy 99, torch-mps 301; jubarte-0.11.0: numpy 144, torch-mps 256; jubarte-0.12.0: torch-mps 400; soffice: torch-mps 398.

jubarte-0.11.0 minus Wordcraft, pagefair: **+21.02 points**, paired bootstrap 95% interval [+19.45, +22.58], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
jubarte-0.12.0 minus Wordcraft, pagefair: **+24.71 points**, paired bootstrap 95% interval [+23.31, +26.15], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.
soffice minus Wordcraft, pagefair: **-0.48 points**, paired bootstrap 95% interval [-1.64, +0.70], n=400. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By cohort (pagefair mean, failures as zero)

| Cohort | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | soffice |
|---|---:|---:|---:|---:|---:|
| cohort 1 | 197 | 54.19 | 77.14 | 79.69 | 54.73 |
| cohort 2 | 203 | 56.14 | 75.28 | 80.08 | 54.67 |

### jubarte 0.11.0 → 0.12.0

Failure transitions: 400 scored by both, 0 failed in 0.11.0 and scored in 0.12.0, 0 scored in 0.11.0 and failed in 0.12.0, 0 failed in both. On the documents both scored, 0.12.0 minus 0.11.0 pagefair averages 3.69 points (136 improved, 10 regressed by more than 0.5).

### By state

| State | N | wordcraft | jubarte-0.11.0 | jubarte-0.12.0 | soffice |
|---|---:|---:|---:|---:|---:|
| tracking_without_comments | 100 | 57.81 | 76.49 | 76.99 | 61.83 |
| with_comments_clean | 100 | 50.34 | 69.76 | 79.67 | 47.11 |
| with_comments_tracking | 100 | 49.79 | 73.58 | 77.67 | 42.91 |
| clean | 100 | 62.78 | 84.95 | 85.22 | 66.93 |

## Timing and limits

Observed Wordcraft CLI medians: comparison 14.48 ms, conversion 41.18 ms. Each invocation includes process startup, file loading and saving. Three warmups per lane were excluded. Timing is a single-pass observation; other work was active on the machine, and the Docxodus wrapper includes WASM initialization. Do not treat these numbers as a rigorous throughput ranking.

Per-lane CLI latency over the frozen rows (last attempt per document; a timeout is the 120 s per-call limit):

| Task | Tool | Docs run | OK | Failed | Timeouts | Median ms | p90 ms | p99 ms | Max ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| compare | jubarte-0.11.0 | 400 | 400 | 0 | 0 | 51.6 | 409.5 | 2,089.6 | 7,927.8 |
| compare | jubarte-0.12.0 | 400 | 400 | 0 | 0 | 37.8 | 169.5 | 860.7 | 4,470.3 |
| compare | wordcraft | 400 | 400 | 0 | 0 | 14.5 | 22.7 | 84.1 | 159.4 |
| compare | docxodus-12.6.5 | 400 | 391 | 9 | 9 | 8,206.8 | 27,580.2 | 53,606.3 | 114,902.6 |
| convert | jubarte-0.11.0 | 400 | 400 | 0 | 0 | 27.5 | 108.7 | 293.9 | 432.8 |
| convert | jubarte-0.12.0 | 400 | 400 | 0 | 0 | 28.3 | 96.9 | 292.1 | 395.3 |
| convert | wordcraft | 400 | 400 | 0 | 0 | 41.2 | 84.6 | 193.6 | 493.2 |
| convert | soffice | 400 | 398 | 2 | 0 | 1,894.5 | 3,818.2 | 6,104.2 | 6,612.1 |

Why vendor redlines failed (counted as zero): wordcraft: 8 (8 loaded empty in Word); jubarte-0.11.0: 1 (1 crashed Word); jubarte-0.12.0: 5 (3 crashed Word, 1 Word AppleEvent timeout, 1 Word export failed without an error text); docxodus-12.6.5: 31 (22 loaded empty in Word, 9 generation timed out). "Loaded empty" means Word refused the vendor DOCX in both fresh sessions with "Word experienced an error trying to open the file" (for some docxodus files after an "unreadable content" repair prompt, answered No); the alert text is in compare/<tool>/word_pdf*.log. "Crashed Word" means Word quit on it in both sessions.

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
