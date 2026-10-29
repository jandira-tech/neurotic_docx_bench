# PHASE 3b, issue #99 / #95 — score Word's exports and build the redlines + accept/reject viewer update (local only)

Work only in /Users/arthrod/temp/T/neurotic_docx_bench/site/_build/site_1030 (this folder). Model everything on the finished
Phase 3a build in ../site_1029 (read its README.md, PLAN.md, process.py, patch_site.py, report.py, common.py, tests) and on
../site_1028 (the build that made the current live redlines viewer). Reuse their scorer snapshot approach, encoding, R2 URL
scheme, audits and tests; do not invent a new style.

Hard rules: no Word, no uploads, no commits, no pushes, no GitHub posts, never write ../../index.html or ../../redlines/index.html
(produce preview/ copies only). Delete every temporary raster as soon as it is used (disk has ~55 GiB; keep peak use low).
Failures are ITT 0: a generation failure (renew_1028 generate_failures.json) or a Word failure (no output in manifest.jsonl)
stays a visible row with Pixel 0 and no candidate assets; never retry, substitute or drop it.

## Inputs (all under /Users/arthrod/temp/T/renew_1028)
- case-keys.json, jobs.json, REPORT.md, PLAN.md, MANIFEST.sha256.txt: phase-1 selection and provenance. Check hashes.
- Word exports (Word for Mac, scripts/word_pdf.py, just finished or finishing): out/redlines/{jubarte,docxodus}/pdf and
  out/ar/{jubarte,docxodus,superdoc}/{accept_all,reject_all}/pdf, each with manifest.jsonl. Resolve outputs ONLY through
  neurotic_docx_bench.word_outputs.find_output (src at /Users/arthrod/temp/T/neurotic_docx_bench/src). Accept/reject runs
  also wrote Word's accepted/rejected DOCX beside each PDF.
- The superdoc batches may still be running: before reading out/ar/superdoc, wait until logs_word_master.txt contains ALLDONE.
- Word failure details: logs/*.console and logs/*.log (driver). Record per-document Word failure reason in the report.
- References: the exact full Word oracles phase 1 recorded (references/), as site_1029 did for d2p.

## Scoring (identical to site_1029)
- Pixel: pipeline.score_pdf_pair at bench.yaml's 144 DPI, numpy backend, no cache; display pipeline.overall_from_result.
  Use a git-archive snapshot of bench main (record the commit and scorer fingerprint; expect 5e481477e2196f6b).
- J/SSIM/TB: upstream page-metrics, ../site_1029/bin/page-metrics (sha256 2213ff317059873a15e9605825387a6f41e1514a21a1c9c7e4b7187a7f37925c),
  150-DPI mutool rasters, x100 rounded to 1 decimal, nulls stay null, means exclude nulls with denominators.

## Viewer work
A. Redlines viewer (../../redlines/index.html): the 1,400 selected compare cases get jubarte 0.14.0 and docxodus 14.2.0 in
   place of their older jubarte/docxodus columns (other engines, Word columns, case order and all HTML outside DATA unchanged,
   proven by audit). Drop stale older-version lanes the way site_1029 dropped Wordcraft's jubarte-0.11/0.12.
B. Set B, issue #95: the 0929 accept/reject cohort, 400 accept_all + 400 reject_all pairs, tools jubarte 0.14.0,
   docxodus 14.2.0, superdoc (bench pin; 693 generation failures as ITT 0). Reference = Word's own accept_all/reject_all PDF.
   Inspect both viewers and decide the smallest faithful way to publish it (new groups in the redlines viewer if its DATA
   schema can carry them cleanly, otherwise a new page accept-reject/index.html cloned from the redlines viewer code with a
   nav link). Write the decision and why into README.md.
- Encode images exactly as site_1029 (180 DPI -> 2/3 Lanczos -> 16-colour -> lossless WebP m4; shown-page PDF via mutool clean -gggz)
  under build/renew1030/..., URLs https://pub-92c80eda1059428394970066c8500eda.r2.dev/renew1030/...
- Tests (pytest, high coverage of helpers), a Playwright smoke over preview with screenshots, build/REPORT.md with per group
  per tool: cases, failures (generation vs Word), Pixel/J/SSIM/TB means with n, and MANIFEST.sha256.txt.
- Make the build resumable (per-case records keyed by input+scorer fingerprint), six workers, progress lines in process.log.

Finish with a short summary: counts, failures, group means, sizes, where the preview is, anything you could not do.
