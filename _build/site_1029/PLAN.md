# Phase 3a, issue #99

- Scope: 1,276 phase-1 DOCX→PDF jubarte jobs only; no Word, uploads, commits or live viewer writes.
- Pin current main including #98, record scorer fingerprint and source/input hashes.
- Score full references/candidates: pipeline.score_pdf_pair at bench 144 DPI, pipeline.overall_from_result as docx_to_pdf._overall_map; separate upstream a72d91bc page-metrics at 150 DPI.
- Retain current shown pages; infer first 3 only for cases without shown. Encode exactly as site_1028, jubarte assets only, under renew1028/d2p/. Delete temporary PNGs per case/stage.
- Replace only jubarte data in a copy of current index.html; remove Wordcraft versioned jubarte lanes and add them to dropped. Preserve all other bytes/data and case order.
- Validate all assets, score accounting, preservation and cleanup; report group means with metric denominators.
- Preview through Vite + console-pipe and Playwright; inspect old, fixture and Wordcraft cases, metrics, images/PDFs and sorting.

## Verified setup

- Main snapshot 3121c498 including #98, fingerprint 5e481477e2196f6b; numpy, 144 DPI; upstream a72d91bc binary SHA256 matches site_1028.
- All 1,276 reference/candidate pairs match phase-1 manifest; zero generation failures.
- Current source DATA round-trips byte-identically with a no-op patch. Shown selections line up with Word assets and are ordered.
- 14 tests passed: pure data/patch helper and real-file API/upstream identity smoke. Coverage: 100% lines, 100% branches for common.py.
- Full build running; do not treat partial checkpoints as completed output.

## Native tool recovery

- mbx evicted the supplied tools/target cache directory during scoring; seven jobs (28 reference pages) hit missing-executable errors. They are build retries, not jubarte failures.
- Suspended main PID 86853 and its six workers, rebuilt unchanged a72d91bc with cargo --release --locked, restored exactly the original native SHA256 2213ff317059873a15e9605825387a6f41e1514a21a1c9c7e4b7187a7f37925c, copied it to bin/page-metrics, then resumed. No upload, no metric-source change.
- protect_metrics.py holds a shared lease for the first run's already-imported target path. New process.py/test/prepare/report invocations use/verify the local byte-identical copy.
- Original full process session 49663 remains running. It will exit nonzero for the seven prior infrastructure errors even if all remaining jobs succeed. Then archive process.log and errors.json as initial/transient records; rerun process.py (cached successes) to recover the seven cases. Do not invent ITT failures.
- After successful cases_d2p_jubarte.json exists: patch_site.py, report.py, run_tests.py, start dev_server.mjs on 8179, run browser_smoke.mjs, inspect JPEGs/console and final hashes/sizes.

## Complete

All 1,276 rows built; seven infrastructure retries recovered; final pass zero errors. Patch, all-asset/data preservation audit, 14 tests (100% helper line/branch coverage), five-case Playwright smoke plus original-v1 corroboration, visual inspection, manifests and final group/size reports passed. Source viewers unchanged; no temporary PNGs. Local preview server session 7697 remains at 8179. No Word/upload/commit/external posting.
