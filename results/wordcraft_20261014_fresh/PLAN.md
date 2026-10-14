# Authoritative fresh benchmark and expansion

User steering: all final values must be fresh; benchmark jubarte 0.11 and 0.12 separately; after first cohort completes update all relevant Markdown benchmark documentation and push main without asking; then add 200 different fixtures and aggregate.

1. Keep frozen comparisons.csv (200 unique content pairs) and conversions.csv (200 distinct content hashes). Preserve earlier run in ../wordcraft_20261014 as preliminary; do not publish its reused-score figures as final.
2. Use verified official released jubarte 0.11.0 and 0.12.0 binaries; record release SHA256SUMS, source tags and binary hashes. No dev builds.
3. Fresh Word comparisons via scripts/word_redline.py for all 200 pairs; fresh Word rendering via scripts/word_pdf.py for comparison references, all tools' redlines and all 200 conversion references. Verify Best for printing and Print Markup in Word UI.
4. Fresh Wordcraft 0.6.1 comparisons and conversions, jubarte 0.11.0 and 0.12.0 comparisons and conversions, Docxodus 12.6.5 comparisons, and installed LibreOffice 26.8.1.1 conversions. Exact same source bytes, direction and per-fixture Word references within each task. Separate each version; no historical scores or output-cache hits.
5. Same unchanged scorer at 144 DPI, NumPy, per-document raster deletion. Record all failures without replacement. If fresh Word cannot make a reference, diagnose first and disclose oracle failures separately; never silently replace with old scores or old PDFs.
6. Live PARTIALS.md with timestamp, scored/failed/pending, mean/median fidelity, pagefair and median CLI latency. Timings include startup/open/save, excluded warmups; fresh run no competing benchmark scoring during timed CLI generation. Other host activity disclosed.
7. After cohort 1 completes, update benchmark-related Markdown throughout repository, make reviewable commit in isolated worktree, push main directly as explicitly authorized. Preserve unrelated working-tree changes. No PR/approval detour.
8. Add non-overlapping 200 comparison pairs and 200 conversion documents; preserve stage 1 selection and outcomes. Same eligibility/strata rules, account for scarce comparison states (only 5 clean/comment-clean compares, all in first cohort). Freeze stage 2 before vendor generation.
9. Benchmark cohort 2 freshly with all the same pinned tools and Word; aggregate to 400 comparisons + 400 conversions, retain cohort-specific tables and paired failure-transition analysis for jubarte 0.11 vs 0.12.
10. Update final aggregate documentation and push main again if needed; only mark goal complete after fresh expanded results and requested publication are verified.

Existing preliminary jobs can be retired once their checkpoints/logs are preserved. The only authoritative final scores will be under this fresh directory (and the expansion directory); preliminary historical rows remain clearly labeled.
