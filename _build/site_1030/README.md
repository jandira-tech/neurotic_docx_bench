# Phase 3b — redlines and accept/reject renewal

Local review build for issues #99 and #95. All generated files live in this folder. The two source viewers and the phase-1 inputs are read-only. The scripts do not invoke Word, upload, commit, push or post to GitHub.

## Viewer decision

Append Set B as `ar/accept_all` and `ar/reject_all` in the existing redlines viewer. Its DATA schema already represents independent groups, per-case Word references, versioned tools, failure rows, metrics and shown-page PDFs. The group selector and score table therefore work without new viewer code. This is the smallest faithful implementation: no separate page or navigation change is needed. Every byte outside DATA is preserved, including global engine declarations. The existing `jubarte-rust` key displays jubarte; its per-case version becomes jubarte 0.14.0.

The first 1,429 rows retain their identities and order. Of those, the selected 1,400 compare cases replace only jubarte/docxodus data; 29 historical cases stay byte-identical. Selected older jubarte/docxodus version lanes are removed from every map and marked dropped. Other tools and all existing Word columns remain unchanged. The 800 appended cases are the exact 400 accept + 400 reject phase-1 pairs, with jubarte 0.14.0, docxodus 14.2.0 and bench-pinned superdoc-sdk 2.16.0. Their reference is Word's own accepted/rejected PDF. Set B preserves the full pair identity and shows the first three reference pages.

## Inputs and scoring

`prepare.py` checks phase-1 selection/provenance hashes and selected file hashes against `/Users/arthrod/temp/T/renew_1028/MANIFEST.sha256.txt`. It verifies the master log contains ALLDONE before reading SuperDoc exports. Candidate outputs are resolved exclusively by `neurotic_docx_bench.word_outputs.find_output` and require manifest confirmation. Generation failures remain ITT zero even if an unrelated output exists. Missing Word outputs remain ITT zero with per-document reasons and log evidence. There are no generation or Word retries or substitutions.

`scorer-source/` is a git-archive snapshot of bench main at **3121c4988d72bf5cd93607c18cb50e3d713ce338**, matching Phase 3a. `origin/main` is recorded explicitly because the local `main` branch predates scorer PR #98. Pixel uses `pipeline.score_pdf_pair`, bench.yaml's **144 DPI**, deterministic numpy backend, no cache, and `pipeline.overall_from_result` (pagefair when present). Fingerprint: **5e481477e2196f6b**. Full pipeline evidence is retained in each successful tool row, including raw and pagefair scores.

Displayed J/SSIM/TB use the upstream **a72d91bca065be5c96b659e5daadc3cf3ffc9fb2** page-metrics executable copied byte-identically from Phase 3a into `bin/page-metrics`. SHA256: `2213ff317059873a15e9605825387a6f41e1514a21a1c9c7e4b7187a7f37925c`. Full 150-DPI mutool rasters, x100 rounded to one decimal, nulls preserved; means exclude nulls with metric-specific denominators. Generation/Word failures contribute Pixel 0 and no candidate assets.

Encoding reuses the exact Phase 1028 helpers: 180-DPI mutool PNG → 2/3 Lanczos resize → 16-colour median-cut → lossless WebP method 4; shown-page PDFs via `mutool clean -gggz`. Images and PDFs live under `build/renew1030/{redlines,ar}/...`, with intended URLs `https://pub-92c80eda1059428394970066c8500eda.r2.dev/renew1030/...`. Pixel rasters are deleted before upstream rasters; upstream rasters are deleted before encoding; each shown PNG is deleted immediately after encoding. Six process workers bound concurrent temporary use.

## Reproduce

Use the existing bench environment from this folder:

```sh
/Users/arthrod/temp/T/neurotic_docx_bench/.venv/bin/python prepare.py
/Users/arthrod/temp/T/neurotic_docx_bench/.venv/bin/python process.py --workers 6
/Users/arthrod/temp/T/neurotic_docx_bench/.venv/bin/python patch_site.py
/Users/arthrod/temp/T/neurotic_docx_bench/.venv/bin/python report.py
/Users/arthrod/temp/T/neurotic_docx_bench/.venv/bin/python run_tests.py
node dev_server.mjs > browser_console.log 2>&1
# In another terminal:
node browser_smoke.mjs
```

`jobs_prepared.json` holds 6,000 rows: 2,800 redlines candidates, 2,400 Set B candidates and 800 Set B references. The three `jobs_{redlines,ar,references}.json` files support `process.py --which` for narrower resumptions. `build/records/` checkpoints include a SHA256 of the entire prepared job, input hashes and scorer provenance; missing asset files invalidate a checkpoint. Infrastructure/scoring errors stop finalization rather than becoming conversion failures. `process.log` has timestamped progress. The final `build/cases.json` is written only after the requested complete run succeeds; patching refuses partial results.

`report.py` verifies every input, checkpoint, metric, image and PDF, exact asset inventory, source hashes, all unaffected engine data, Word columns, original row order, untouched row bytes and HTML outside DATA. It writes `build/REPORT.md`, `build/REPORT.json` and `build/MANIFEST.sha256.txt`. The report includes per-group/per-tool cases, generation vs Word failures, means with denominators, exact sizes and per-document failure reasons with evidence.

Open **http://127.0.0.1:8180/redlines/**. `preview/redlines/index.html` is the proposed viewer; `preview/index.html` is an unchanged copy of the current conversion viewer for navigation. The Vite development server maps new asset URLs to this build. It uses predecessor assets locally when present, otherwise retaining their exact existing published URLs. Phase 3a's local asset tree is absent; its published renewal URLs returned HTTP 200 and passed the navigation smoke. New `renew1030` assets always resolve locally, and missing new assets remain errors. Saved preview URLs remain intended R2 URLs; those new assets are available only locally until a separately authorized upload. Node verification reuses Phase 1028's installed dependencies via a local `node_modules` symlink; package and lock files are copied here for reproducibility.

Browser verification uses Playwright with local Chrome, `vite-plugin-console-pipe` for terminal/log console output, health HTTP 200, updated compare and both Set B groups, images/PDFs, versions and metrics, Pixel sorting, visible ITT failures and JPEG screenshots. Python unit tests exercise pure helpers without filesystem/network/clock dependencies; real scorer and local-file checks are explicitly integration tests. Every test run produces coverage.

## Verification status

Completed all **6,000 records**, with zero scoring/build errors: 2,800 redlines tool rows, 2,400 Set B tool rows and 800 Set B reference rows. The preview updates **1,400 cases**, preserves **29 historical cases byte-identically**, and appends **400 accept + 400 reject cases**, for 2,229 viewer cases. All selected old versioned jubarte/docxodus lanes were removed; each of the four Wordcraft aliases had 400 removed entries. Original case order, unaffected tool data, Word columns, source files and every byte outside DATA passed the preservation audit.

Failures remain **693 generation + 139 Word = 832 tool rows**, all visible with Pixel 0 and no candidate assets. Word failures: redlines jubarte 6, redlines docxodus 115, accept docxodus 5, reject docxodus 13. SuperDoc generation failures: accept 342, reject 351. Per-document reasons and evidence, all group/tool means and metric-specific denominators are in [build/REPORT.md](build/REPORT.md) and [build/REPORT.json](build/REPORT.json).

| Cohort | Tool | Pixel | J | SSIM | TB |
|---|---|---:|---:|---:|---:|
| All 1,400 selected compare cases | jubarte | 73.61 | 71.41 | 79.08 | 78.76 |
| All 1,400 selected compare cases | docxodus | 64.77 | 63.08 | 71.47 | 70.24 |
| Accept (400) | jubarte | 91.81 | 86.86 | 91.04 | 97.10 |
| Accept (400) | docxodus | 90.68 | 86.00 | 90.32 | 96.72 |
| Accept (400) | superdoc | 13.96 | 94.86 | 97.32 | 98.17 |
| Reject (400) | jubarte | 89.84 | 84.02 | 89.20 | 94.27 |
| Reject (400) | docxodus | 85.43 | 79.55 | 84.89 | 94.44 |
| Reject (400) | superdoc | 11.08 | 83.04 | 87.63 | 94.63 |

Means are on the 0–100 scale. Pixel includes all ITT-zero failures; J/SSIM/TB exclude nulls. The full report separates the four compare groups and shows every denominator.

**22,706 assets:** 17,538 WebP pages and 5,168 shown-page PDFs. Payload **1,538,121,096 bytes (1,466.87 MiB)**. Complete `build/` **1,611,938,831 bytes (1,537.26 MiB)**, including records/reports/manifest. The manifest has 22,707 entries (assets plus cases.json). All 14,099 unique input files and all 6,000 checkpoints verified; no temporary PNGs remain.

**27 pytest tests passed; Coverage: 100% lines, 100% branches** across the changed pure helpers `common.py` and `prepare_helpers.py`, with the real scorer/upstream identity check marked integration. The raw browser V8 source/functions/ranges are saved separately in `browser_coverage.json`; the Python helper percentage does not claim browser-wide coverage.

**Playwright passed eight cases** (five success, two SuperDoc generation failures and one Word failure), health HTTP 200, images/PDFs, versions/metrics, Pixel sorting both directions and conversion-to-redlines navigation. It validated 40 local asset responses and 15 retained remote responses, with no page exceptions, bad assets or unexpected remote requests. Sixteen JPEG screenshots were saved and visually inspected. `vite-plugin-console-pipe` captured browser output in `browser_console.log`. Final machine-readable evidence: [verification.json](verification.json), [browser_smoke.json](browser_smoke.json), [patch_evidence.json](patch_evidence.json).

The first subagent-owned scoring session ended early; 895 valid records were resumed in the root-owned run and six abandoned temporary raster folders were removed. No generation or Word failure was retried. Browser verification exposed and corrected a navigation-fixture assumption, a Playwright coverage API field mismatch, and retained-asset routing when predecessor local assets were absent. Diagnostic logs are preserved as `browser_smoke_initial.log`, `browser_smoke_coverage_failure.log` and `browser_smoke_missing_retained.log`. The final run passed. No Word invocation, upload, commit, push, GitHub post or live viewer write occurred.
