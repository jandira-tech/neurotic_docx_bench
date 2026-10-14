# Wordcraft CLI benchmark — partial

Updated: 2026-10-14 01:38:26 EDT.

Fixed seed 20261014. 200 unique base→next comparisons from 11 pools; 200 distinct conversion DOCX, 50 per document state. The sample was frozen before running Wordcraft.

Comparison redlines are rendered by Word 16.115. All tools in each task use identical per-fixture Word PDF oracles, 144 DPI and the unchanged NumPy scorer. Full-cohort means include tool failures as zero. Partial means include only completed scores and can be biased toward faster documents.

## Comparisons

| Tool | Scored / 200 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft | 190 | 10 | 0 | 44.96 | 43.69 | 44.65 | 21.11 | 60 |
| jubarte-0.11.0 (partial) | 76 | 16 | 108 | 76.01 | 75.79 | 84.16 | 79.48 | 7 |
| docxodus-12.6.5 (partial) | 0 | 2 | 198 | — | — | — | 6693.45 | 0 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization and was measured amid concurrent scoring, so its latency is observational. A blank median means it was not measured for that exact build and cohort.

jubarte-0.11.0 minus Wordcraft, pagefair: **+29.57 points**, paired bootstrap 95% interval [+25.54, +33.62], n=74. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By state

| State | N | wordcraft | jubarte-0.11.0 | docxodus-12.6.5 |
|---|---:|---:|---:|---:|
| tracking_without_comments | 98 | 47.15 | 75.85 | — |
| with_comments_tracking | 97 | 40.42 | 75.70 | — |
| with_comments_clean | 3 | 40.54 | — | — |
| clean | 2 | 37.06 | — | — |

## Conversions

| Tool | Scored / 200 | Failed | Pending | Mean v1 | Mean pagefair | Median v1 | Median CLI latency (ms) | Page mismatches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| wordcraft | 200 | 0 | 0 | 54.24 | 54.00 | 51.93 | 41.75 | 40 |
| jubarte-0.12.0-c551 | 200 | 0 | 0 | 79.06 | 79.00 | 81.32 | — | 6 |
| soffice (partial) | 119 | 0 | 81 | 55.05 | 54.93 | 47.63 | — | 8 |

CLI latency includes startup, file loading and saving; Word export is excluded from comparison latency. Docxodus includes WASM initialization and was measured amid concurrent scoring, so its latency is observational. A blank median means it was not measured for that exact build and cohort.

jubarte-0.12.0-c551 minus Wordcraft, pagefair: **+25.00 points**, paired bootstrap 95% interval [+23.04, +26.92], n=200. This interval describes the selected benchmark cohort, not a population-wide guarantee.
soffice minus Wordcraft, pagefair: **-0.35 points**, paired bootstrap 95% interval [-2.30, +1.70], n=119. This interval describes the selected benchmark cohort, not a population-wide guarantee.

### By state

| State | N | wordcraft | jubarte-0.12.0-c551 | soffice |
|---|---:|---:|---:|---:|
| tracking_without_comments | 50 | 57.37 | 77.90 | 63.96 |
| with_comments_clean | 50 | 47.42 | 77.61 | 43.48 |
| with_comments_tracking | 50 | 48.24 | 76.15 | 42.92 |
| clean | 50 | 62.97 | 84.34 | 69.15 |

## Timing and limits

Observed Wordcraft CLI medians: comparison 21.11 ms, conversion 41.75 ms. Each invocation includes process startup, file loading and saving. Three warmups per lane were excluded. Timing is a single-pass observation; other work was active on the machine, and the Docxodus wrapper includes WASM initialization. Do not treat these numbers as a rigorous throughput ranking.

The primary conversion command uses `--markup`, matching Word oracle PDFs that display comments and tracked changes. Wordcraft comparison uses word granularity with formatting/case/whitespace differences enabled. Unsupported Wordcraft compare options are documented in its own CLI command catalog.

Jubarte 0.12.0 c551 conversion fidelity reuses historical rows only after verifying fixture and oracle SHA256 and the same scorer fingerprint. No fresh speed measurement is claimed for that build. LibreOffice conversions and jubarte 0.11.0/Docxodus 12.6.5 comparison baselines are freshly generated for this sample.

Wordcraft redline export: 190 readable, 10 rejected as unreadable after two Word attempts. Existing Word oracles were reused; scripts/word_redline.py refreshed 4 of 8 audited comparisons, while 4 produced Word scripting errors and retained their verified saved oracle. No fixture was substituted after a failure.

Both raw v1 and pagefair are reported. The raw scorer compares shared pages; pagefair additionally accounts for extra or missing pages. Failure-aware means and common-success paired comparisons distinguish tool failure from fidelity among readable outputs.

This is a balanced stress sample, not a frequency-weighted estimate of the full corpus. All 200 comparison input pairs and all 200 conversion content hashes are distinct.

Rasters are discarded after each scored document. DOCX, PDF, manifests, logs and score checkpoints are retained. Scorer parity validation: 5 passed; focused coverage 58.6% lines and 71.2% branches.

## Evidence

- `comparisons.csv`, `conversions.csv`, `sample_provenance.json`: frozen selection, seed, hub revision and hashes.
- `tools.json`, `oracle_provenance.json`, `pdf_preset.txt`: exact binaries, Word version and oracle sources.
- `operations.jsonl`: invocation, timing, exit status, revision XML and output hashes.
- Per-tool `scores.json` and `scores.checkpoint.jsonl`: full metrics and resumable progress.
- `wordcraft_word_pdf.out`, `jubarte_word_pdf.out`, `word_audit/word_redline.out`, `word_screen.log`: Word outputs and exact alerts.
- `feature_distribution.json`, `actual_page_distribution.json`: corpus complexity and reference page counts.
