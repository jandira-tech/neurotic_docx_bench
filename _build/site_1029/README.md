# Phase 3a — jubarte 0.14.0 DOCX→PDF renewal

Issue [#99](https://github.com/jandira-tech/neurotic_docx_bench/issues/99). Local review build only: no Word, uploads, commits, external posting, or writes to either live viewer. The inputs are the phase-1 `~/temp/T/renew_1028` artifacts and the **current** `site/index.html`. The 2,925 v1 cases already at jubarte 0.14.0 remain byte-identical.

The requested scope is 1,276 cases: 76 fixtures, 800 older corpus cases, and 400 Wordcraft convert cases. Every selected reference and generated PDF is checked against the phase-1 SHA256 manifest. Full Word oracles are used for scoring, including the exact published full Word render for older corpus cases and the full manifest-verified cohort oracle for Wordcraft. The viewer's partial PDFs and alternate corpus renders are not scoring inputs.

## Scorers and encoding

`scorer-source/` is an unmodified `git archive` snapshot of bench main **3121c4988d72bf5cd93607c18cb50e3d713ce338**, including PR #98. The older results checkout is left untouched. `source_hashes.json` records scorer fingerprint **5e481477e2196f6b**, source hashes, input viewer hashes, upstream binary hash and DPIs. `runtime.json` records renderer/library versions. The source snapshot can be recreated with `git archive <commit> src bench.yaml pyproject.toml uv.lock`.

Pixel is computed now by `pipeline.score_pdf_pair`, using bench.yaml's **144 DPI**, the deterministic numpy backend, and no content/raster cache. The displayed aggregate is `pipeline.overall_from_result`, as used by `docx_to_pdf._overall_map`: `overall_score_pagefair` when present. Each completed row retains the complete pipeline result in `pixel_result`, including raw and pagefair scores and the #98 port's metrics. These ported metrics use the bench rasters; they are provenance only, not the displayed J/SSIM/TB.

Displayed J/SSIM/TB come separately from upstream `~/temp/T/docxide-pdf/tools/target/release/page-metrics`, commit **a72d91bca065be5c96b659e5daadc3cf3ffc9fb2**, SHA256 `2213ff317059873a15e9605825387a6f41e1514a21a1c9c7e4b7187a7f37925c`, with full **150-DPI mutool** rasters. Nulls remain null; upstream compares compatible common pages. Values are multiplied by 100 and rounded to one decimal as in site_1028; group means use those values, with per-metric denominators.

During this run the supplied executable's mbx-managed target directory was evicted. The workers were suspended while `cargo build --release --locked --bin page-metrics --manifest-path tools/Cargo.toml` restored it from the unchanged upstream checkout. The restored executable has **exactly the original SHA256**; no scorer or dependency change entered the measurement. `bin/page-metrics` preserves a byte-identical local copy for reproducibility and retries. `native_recovery.json` and `restore_page_metrics.log` record the recovery (zero bytes uploaded). A temporary shared target lease protects already-imported paths while in-flight work completes; later runs use the local copy. Missing-executable build errors are retried rather than counted as jubarte failures.

`reference_process_1028.py` is an exact copy of site_1028/process.py, supplying the unchanged `draw`, `metrics`, `encode`, and subprocess helpers. Images follow its 180-DPI raster → 2/3 Lanczos resize → 16-colour median-cut → lossless WebP method 4. `mutool clean -gggz` makes the shown-page PDFs. Existing `shown` page numbers are preserved exactly, including older full-document selections; cases without `shown` use first 3. Existing Word assets are preserved. Missing candidate pages remain null gaps. Only jubarte assets are built, under **build/renew1028/d2p/**.

Temporary pixel rasters are deleted before upstream rasters, which are deleted before shown-page encoding; each shown PNG is deleted immediately after encoding. Six process workers isolate PyMuPDF state and bound disk use. Full input PDFs remain read-only.

## Scripts and records

| File | Purpose |
|---|---|
| `prepare.py` | exact phase-1 joins, page selections, source and input hashes |
| `jobs_d2p_jubarte.json` | 1,276 prepared jobs and provenance |
| `process.py` | fresh pixel + upstream scoring, encoding, resumable records keyed by input/scorer fingerprint |
| `build/cases_d2p_jubarte.json` | all completed replacement rows |
| `build/records/` | individual resumable results, including full pipeline evidence |
| `patch_site.py`, `common.py` | patched copy of current live source; never writes live index.html |
| `preview/index.html` | proposed copy with intended R2 URLs |
| `patch_evidence.json` | source/preview digests and counts |
| `report.py` | all-case preservation, all-asset validation, manifest and group means |
| `build/REPORT.md`, `build/REPORT.json` | counts, failures, means/denominators, sizes and scorer provenance |
| `dev_server.mjs` | local asset preview and Vite console-pipe |
| `browser_smoke.mjs`, `browser_smoke.json` | Playwright checks, screenshots and machine-readable evidence |

The patch changes only each selected case's jubarte maps and its associated `dropped` membership. It clears stale scores, pages, PDFs, counts, times, errors, versions and metric diagnostics before inserting the new result. Version label: **jubarte 0.14.0**, key **jubarte**. Wordcraft's `jubarte-0.11.0` and `jubarte-0.12.0` entries are removed from every map and marked `dropped` following site_1011. Global engine declarations and all other viewer code are byte-identical. A failure row stays visible with Pixel 0 ITT and no candidate assets; stale successes are never retained. Phase 1 has no jubarte generation failures; unexpected scoring/build errors stop finalization instead of silently inventing conversion failures.

The patch reads current index.html when invoked; it refuses partial case files, duplicate/missing identities, page-selection drift or a noncanonical DATA representation. The final audit checks the originally recorded input hashes, head/tail bytes, all untouched rows, all non-jubarte data in changed rows, exact case order and unchanged Word columns. Nothing is patched in place.

## Reproduce

From this folder, using the bench's existing environment:

```sh
export BENCH_DEVICE=numpy OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
../../../.venv/bin/python prepare.py
../../../.venv/bin/python process.py --workers 6
../../../.venv/bin/python patch_site.py
../../../.venv/bin/python report.py
../../../.venv/bin/python run_tests.py
node dev_server.mjs > browser_console.log 2>&1
# In another terminal:
node browser_smoke.mjs
```

The Python path above is relative to this folder. Dependencies are the existing bench environment; exact versions are in `runtime.json`. Node verification uses the same lockfile as site_1028. This run reuses its installed `node_modules` via a local symlink; for independent installation remove the symlink and run `npm ci` here.

Open **http://127.0.0.1:8179/** for review. `/__health` returns HTTP 200. Vite rewrites only HTTP responses for `renew1028/` to this build; retained `d2p_v1/` and `wordcraft1014/` assets use site_1028's local build. Older Word reference images retain their existing remote URLs. Saved preview HTML is never rewritten for local asset serving. New R2 paths are not available remotely until a separately authorized upload.

The browser tests use headless Playwright with local Chrome, enable only Word/jubarte for sample views, check aligned images and page PDFs, verify Pixel/J/SSIM/TB and version labels, exercise Pixel sorting both directions, and corroborate an untouched v1 case. Browser console output is captured by `vite-plugin-console-pipe` into `browser_console.log`; console collection uses no DevTools or CDP WebSocket connection. Screenshots are JPEGs.

`run_tests.py` runs deterministic pure-helper unit tests plus a separately marked real-file integration/API identity smoke. Every run emits line and branch coverage for the changed data/patch helper in `coverage.json` and `tests.log`; the complete data/asset audit is integration validation, separate from unit coverage.

## Final verified result

- **1,276 replaced; 0 jubarte failures; 3,917 cases retained byte-identical.** Both old Wordcraft jubarte lanes were removed from all column maps and marked dropped in all 400 cohort cases.
- **7,885 assets:** 6,609 WebP pages and 1,276 shown-page PDFs. All assets, input hashes, checkpoint fingerprints, score bounds, shown-page selections and preservation constraints passed the full audit. No temporary PNGs remain.
- Asset payload **497.22 MiB**; complete `build/` **516.49 MiB**, including records, cases, reports and manifest. Exact bytes: `sizes.json` and `build/REPORT.json`.
- **14 tests passed; Coverage: 100% lines, 100% branches** for `common.py`, the changed renewal data/patch helper. Public API and upstream identity smoke passed.
- **Playwright passed five updated cases** (fixture, three old corpus groups, Wordcraft convert): jubarte 0.14.0 + Pixel/J/SSIM/TB, aligned images, valid page PDFs, and Pixel sorting both directions. It also confirms an untouched v1 case against its original versions/scores/page counts. HTTP health 200; 27 local asset responses; zero page exceptions or failed local assets. The old Wordcraft checkboxes were explicitly enabled to verify `dropped` suppresses those columns.
- JPEGs for the old corpus and Wordcraft were visually inspected. `verification.json`, `browser_smoke.json`, `browser_console.log` and `tests.log` contain the evidence.
- Seven missing-native-executable attempts were recovered using the byte-identical restored binary; they are not jubarte ITT failures. `process.log` ends with 1,276/1,276 and zero build errors; the initial attempts are retained in `process_initial.log` and `transient_build_errors.json`.
- Source `index.html` and `redlines/index.html` hashes unchanged. No Word, upload, commit or external posting. Local server remains at http://127.0.0.1:8179/.
