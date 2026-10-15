# Wordcraft benchmark, 2026-10-14

Requested: 200 DOCX comparisons using Wordcraft CLI, candidate redlines rendered by Word, plus 200 DOCX-to-PDF conversions, compared fairly with other tools.

## Frozen design
- Wordcraft CLI 0.6.1, installed binary SHA256 and upstream v0.6.1 source commit recorded.
- Reuse the 600 comparisons and 600 conversions sampled for jubarte 0.12.0 release evidence. Do not select using engine scores or successful output availability.
- Comparisons: state quotas 98 tracking_without_comments, 97 with_comments_tracking, 2 clean, 3 with_comments_clean (all scarce states); within each state, cycle source-pool and page-length strata with a fixed seed 20261014.
- Conversions: 50 per state (clean, tracking_without_comments, with_comments_clean, with_comments_tracking), balanced across source pools and page lengths; sample unique DOCX content.
- Inputs and Word corpus PDFs restored from a pinned Hugging Face revision and checked against the local SHA256 manifest. Existing site inputs are reused only if their hashes match.
- Comparison outputs use Wordcraft review.compare, word granularity, formatting/case/whitespace enabled, original layout, author Redline. Generate through the CLI; verify revision XML and output ZIP integrity.
- Redline PDFs through scripts/word_pdf.py in one batch process, preserving already-open documents. Missing Word comparison oracles through scripts/word_redline.py. Use fresh same-pair Word oracle PDFs when an existing verified site oracle is available; provenance records exact hash.
- Conversion primary mode is Print Markup (--markup) so Wordcraft shows tracked changes/comments that Word's oracle prints. CLI startup/open/save are included in generation and conversion timing.
- Fresh comparison baseline jubarte 0.11.0 (installed pinned binary) when an existing pinned-version result cannot be verified. Docxodus uses the repository's reviewed loader or verified existing same-input outputs.
- Scores: unchanged pipeline.score_pdf_pair, 144 DPI numpy, same oracles for every tool. Report overall, pagefair, ink Jaccard, text boundary, page mismatch, failures, per-stratum means, paired bootstrap intervals. Missing tool outputs score zero in the intent-to-treat summary; oracle/infrastructure problems are disclosed separately.
- Timing: serial CLI invocations, warmup excluded, no cache. Reused historical fidelity figures have no fresh speed claim.
- Delete scratch rasters after each scored document and verify no PNGs remain after each tool. Retain manifests, DOCX/PDF, logs, scores, provenance and report.

## Progress
- CLI help and review.compare support verified; desktop fallback unnecessary.
- Scorer fingerprint c0507bbb4029b849 matches historical jubarte 0.12.0 conversion checkpoint.
- Existing working-tree changes to Word scripts/tests and AGENTS.md are user work; preserve them.
- Full corpus download stopped in favor of selected-file restoration to save disk and time.
- Next: freeze sample, restore selected bytes, smoke compare and conversion, generate batches, Word render, score and report.

## Verified progress (during execution)
- Frozen sample: comparisons.csv and conversions.csv, SHA256 in sample_provenance.json. 1,052 selected source/oracle files restored and verified at a pinned hub revision.
- Wordcraft 0.6.1: 200/200 comparison DOCX and 200/200 direct PDF conversions generated. CLI smoke has w:ins and w:del, PDF selectable text.
- Word 16.115 Save As UI verified Best for printing was already selected. No setting changed.
- Wordcraft Word-render batch: 190/200 PDFs; ten generated DOCX rejected as unreadable after two attempts. Exact IDs in compare/wordcraft/render_failures.json and dialogs in word_screen.log. All 200 remain in ITT denominator.
- Wordcraft readable redlines: 1,274 candidate pages vs 1,237 oracle pages; 60 page-count mismatches. Full 200 reference comparisons contain 1,358 pages, conversions 1,402 pages.
- scripts/word_redline.py audit: 8 attempts, 4 fresh oracles made; 4 failed with Word compare AppleEvent errors. Four refreshed PDFs now used consistently by all comparison lanes. Other verified corpus/site oracles retained. oracle_provenance.json records hashes.
- Word launcher: uv run was blocked by an unsolicited broad device-control prompt. Dismissed; direct .venv/bin/python successfully executes the drivers without granting new permissions.
- Scorer parity tests: 5 passed. Coverage: 58.6% lines, 71.2% branches. Python 3.14/coverage duplicate-extension import avoided by pre-importing the scorer before pytest (no source changes).
- Conversion baseline jubarte 0.12.0 c551: all 200 selected score rows reused only after current fingerprint c0507bbb4029b849, input hashes, and Word PDF hashes match. Source checkpoint provenance in convert/jubarte-0.12.0-c551/scores.json.
- Fresh LibreOffice conversion lane: 199/200 generated; one process exited signal 6. Still included as failure, no replacement fixture.
- Fresh jubarte 0.11.0 comparisons: 200 DOCX generated; Word PDF batch running, resumable.
- Docxodus dependencies installed from frozen pnpm lock; current engine 12.6.5. Mixed historical lane is intermediate only. refresh_docxodus.py regenerates the 75 reused historical outputs into compare/docxodus-12.6.5/docx. After original generator finishes, copy its fresh (not reused) outputs into that lane; render that complete version-pinned lane through Word. Do not label mixed historic outputs 12.6.5.
- Scoring processes running: score_run.py convert wordcraft, score_run.py compare wordcraft. Resumable checkpoint after each document. Temporary rasters deleted per completed document.
- Other tasks are using CPU on this machine. Do not present timings collected amid concurrent Word/scorer/Node workloads as rigorous cross-engine speed rankings. Run isolated serial timing checks at the end if possible.

## Remaining
1. Finish all Wordcraft conversion/comparison scoring.
2. Finish jubarte Word batch, score its PDFs against same comparison oracles.
3. Finish Docxodus current generation and historical refresh; assemble only verified fresh 12.6.5 outputs, Word-render and score.
4. Retry the one failed LibreOffice conversion once in isolation; record both attempts. Score full candidate cohort, including any remaining failure.
5. Report ITT (missing outputs zero), successful-only and paired common-success means, pagefair, Jaccard/text boundaries, per-state/source/page-band breakdown, bootstrap intervals.
6. Persist new results through schema-v4 build_results_line/append_line for comparisons and converters.jsonl for conversion. Never rewrite existing trend logs; no gates/snapshot promotion.
7. Save self-contained REPORT.md and results JSON/CSV with exact provenance and timing caveats, open report, verify no retained rasters, mark goal complete only after required work finishes.
