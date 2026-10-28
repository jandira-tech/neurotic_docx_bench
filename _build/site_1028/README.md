# October 2026 renewal (2026-10-28)

Review build for issues [#94](https://github.com/jandira-tech/neurotic_docx_bench/issues/94),
[#95](https://github.com/jandira-tech/neurotic_docx_bench/issues/95), and
[#96](https://github.com/jandira-tech/neurotic_docx_bench/issues/96).
All writes belong to this directory. The root viewers are inputs only: this renewal does
**not** edit them, upload anything, commit, or push. The owner publishes after review. The local `.gitignore` excludes the large R2 asset trees, checkpoints, and dependency/test caches from staging while retaining case JSON, reports, scripts, and provenance for review.

Built: **2,925 v1 + 400 Wordcraft compare + 400 Wordcraft convert** cases. The 800-case split remains blocked by missing candidate PDFs (details below).

Current counts, failures, per-engine means and their denominators are in
[build/REPORT.md](build/REPORT.md) and [build/REPORT.json](build/REPORT.json).
A preview marked **PARTIAL** is deliberately incomplete; `patch_site.py` refuses to make
an unmarked preview if any required set is absent.

| Step | Script / record | What it does |
|---|---|---|
| sources | `source_hashes.json`, `metadata/`, `wordcraft_MANIFEST.sha256.txt` | hashes of original viewers, score records and upstream scorer; SHA-verified cohort metadata; hub listing pinned at `cfa2c7171a69675cb17766a1efc351652fb3fbd1` |
| prepare | `prepare.py`, `jobs_*.json` | exact jobs from v1's 2,925 stems, the split's 800 pairs, and Wordcraft's two 400-row CSVs; checks pixel means against the original records; never invokes a converter |
| v1 inputs | `bench fixtures get v1 --test docx_to_pdf` | pinned fixture snapshot `984e64d869803abea841e66364f7b82bb30b3a70`, every file SHA-verified; existing candidate PDFs from `ndb-v1/out/dx89/{full_work,soffice_work}`; recorded ITT failures remain failures |
| split inputs | `jobs_redlines.json`, `hub_redlines_listing.json`, `redline_replacements.json` | records the 400 accept + 400 reject split; pairs are matched by base/next/action, not just a compare id; 8 of the existing 13 cases overlap and 5 are distinct |
| cohort inputs | `fetch_wordcraft.py` | metadata and only the PDFs needed by the selected jobs; six concurrent downloads; SHA256 against public manifest and the score records; excludes leftover PDFs outside the 400-row CSVs |
| score + encode | `process.py` | upstream docxide-pdf **a72d91bca065be5c96b659e5daadc3cf3ffc9fb2**, `tools/target/release/page-metrics`; 150-DPI PNGs for every PDF page; J/SSIM/TB as in `site_1011/process.py`; six concurrent cases, one candidate raster directory at a time |
| images + PDFs | `process.py` → `build/{d2p_v1,redlines_0929ar,wordcraft1014}/` | first 3 Word pages, capped at its page count, for Word and each successful engine; 180-DPI raster → 2/3 downscale → 16-colour lossless WebP, method 4; `mutool clean -gggz` shown pages → `pages.pdf`; missing candidate pages stay null gaps |
| cleanup | `finish_set.py <set>` | validates a full set before removing only its downloaded inputs and all temporary raster directories; run after the set process exits |
| checkpoints | `build/records/` | one completed row per case, tied to the prepared-job fingerprint; interrupted cases can rerun; successful cases reuse their checkpoint |
| validate + report | `report.py` | validates counts, identities, recorded pixels, shown pages, every WebP and page-PDF; metric-specific means and n; `build/MANIFEST.sha256.txt` covers assets and completed case files |
| patch copies | `patch_site.py` → `preview/{index.html,redlines/index.html}` | retains historical cases and versions; adds cohort engine keys and colours, per-case versions, Pixel labels/filters/sorting; hides unrelated lanes; R2 URLs as in the 1011 `remote()`; never writes the live viewers |
| verify | `run_tests.py`, `browser_smoke.mjs`, `dev_server.mjs` | deterministic helper tests plus real-file integrations with coverage; headless Chrome checks new-case images, PDFs, versions and Pixel sorting; Vite's `vite-plugin-console-pipe` captures browser output in `browser_console.log` |

Final browser verification passed on all three completed sets plus two historical selections: 77 local assets, valid PDF downloads, numerical Pixel sorting both ways, per-case versions, health HTTP 200, and no page exceptions. Both viewer routes forward console output through the plugin. See `browser_smoke.json` and `browser_console.log`.

Final Python verification: **24 passed; Coverage: 86.19% lines, 76.62% branches** across all renewal Python scripts, including command orchestration. The full build separately validated every generated asset. The metrics API identity smoke returned J/SSIM/TB = 100 on identical real pages. See `tests.log`, `coverage.json`, and `browser_smoke.json`.

## Score provenance

The bench pixel score and upstream page-metrics are separate measurements. No pixel score
is recomputed. Each new `scores[engine]` has `pixel`, plus available `jaccard`, `ssim`, and
`text_boundary`, all displayed on a 0–100 scale. The per-case page metrics are rounded to
one decimal as in the reference implementation; their reported means use those displayed
values. Upstream null metrics stay null, with page-count diagnostics where available.
All pages are rasterized for metrics; upstream's aggregation compares common compatible
pages and may return no J/SSIM when dimensions differ, or no TB when its text-layout filter
compares no lines. First-three-page PDFs are viewing assets, not the scoring inputs.

- **v1:** pixel = `tools[tool].per_doc[stem]`, including the recorded ITT zeroes.
  `generate_failures` excludes the later serial Chromium-cleanup successes. Versions:
  jubarte 0.14.0, LibreOffice 26.8.1.1, docxodus 14.2.0; reference label Word.
  Groups `v1/<state>`. The case id is the corpus document's hash prefix, with full `stem`
  preserved; identities are checked for collisions.
- **0929 split:** pixel follows `measure.py` → `pipeline.overall_from_result`, which selects
  the recorded `overall_score_pagefair` when present. Failure rows count zero. This
  reproduces the six published ITT means. Versions come from the split's `versions.json`:
  jubarte 0.9.3, docxodus 12.6.4, SuperDoc 2.15.0. Groups `accepted/<state>`, `rejected/<state>`.
- **Wordcraft:** pixel = each lane's `scores.json.rows[id].overall_score`, with its recorded
  failures zero; verified against `REPORT.json.summary[phase][lane].v1_mean`. Folder names
  stay engine keys. Versions come from `tools.json` (`wordcraft` → `wordcraft-cli`,
  `docxodus-12.6.5` → `docxodus`). Groups `wordcraft1014/compare` and `wordcraft1014/convert`.
  PyMuPDF Pro has 253 requested cases (250 scored, 3 failed); the remaining 147 are not
  applicable and do not acquire zero scores. The public report explicitly excludes the
  superseded stemma 0.5.0 lane: its folder has DOCX files and generation failures, but no
  PDFs or scores. It remains an unavailable engine column, with no invented pixel score;
  stemma 0.6.0 carries the published measured lane. `oracle_docx` is auxiliary reference
  material, not a tool lane.

## Reproduce

Run from `site/`, using the main checkout's environment (`../.venv/bin/python` has Pillow,
PyMuPDF, pytest and pytest-cov). Requires `mutool` and the pinned upstream binary; its
SHA256 is in `source_hashes.json`. Inputs and all temporary rasters must remain here.
Process one set at a time. After each `process.py <set>` exits, run
`../.venv/bin/python _build/site_1028/finish_set.py <set>` to validate and delete downloads/rasters; existing candidate PDFs outside this renewal are read-only.

```sh
../.venv/bin/bench fixtures get v1 --test docx_to_pdf --workers 6 \
  --dest _build/site_1028/inputs/v1
python3 _build/site_1028/prepare.py v1
../.venv/bin/python _build/site_1028/process.py v1

# Split: see the source gap below before attempting to build it.
python3 _build/site_1028/prepare.py redlines
# Obtain the exact split candidate PDFs under inputs/redlines_split/.
../.venv/bin/bench fixtures get v1 --test accept_all --test reject_all --workers 6 \
  --dest _build/site_1028/inputs/v1_ar
../.venv/bin/python _build/site_1028/process.py redlines

../.venv/bin/python _build/site_1028/fetch_wordcraft.py metadata
python3 _build/site_1028/prepare.py wordcraft_compare
../.venv/bin/python _build/site_1028/fetch_wordcraft.py pdfs compare
../.venv/bin/python _build/site_1028/process.py wordcraft_compare
# Validate, then delete inputs/wordcraft/compare before the conversion phase.
python3 _build/site_1028/prepare.py wordcraft_convert
../.venv/bin/python _build/site_1028/fetch_wordcraft.py pdfs convert
../.venv/bin/python _build/site_1028/process.py wordcraft_convert

../.venv/bin/python _build/site_1028/report.py
python3 _build/site_1028/patch_site.py
# While the split source gap is unresolved, use --allow-partial on both commands.
```

`process.py --help` and `patch_site.py --help` describe their limited CLI. A missing PDF
for a recorded success is a build error, not a new zero. The final `cases_*.json` file is
written only after every requested case succeeds. `errors_*.json` names build errors if
there are any. Never upload `records/`, test files, reports, or case JSON as an image prefix;
the three named asset trees are the future R2 prefix roots.

```sh
../.venv/bin/python _build/site_1028/run_tests.py
npm ci --prefix _build/site_1028
node _build/site_1028/dev_server.mjs > _build/site_1028/browser_console.log 2>&1
# In another terminal:
node _build/site_1028/browser_smoke.mjs
```

The smoke server binds `127.0.0.1:8178` and returns 200 on `/__health`. The development server rewrites only its HTTP responses for the three new R2 prefixes
to local `build/` assets; saved preview HTML retains the final remote URLs. Open
`http://127.0.0.1:8178/` or `/redlines/` for an interactive local review. The smoke browser
also has an equivalent request-interception fallback. New assets therefore remain unavailable on
R2 until the owner uploads them. Historical assets keep their existing remote URLs.
The browser captures its console through `vite-plugin-console-pipe`, not a remote CDP
connection. The server makes the plugin's injected client URL absolute so console capture also works on `/redlines/`. npm's lockfile pins the local verification dependencies. Browser screenshots
are JPEGs so no PNG rasters remain.

## Split source gap

At hub commit `cfa2c7171a69675cb17766a1efc351652fb3fbd1`, preset `redlines-0929` has
the older 100+100 run: 598 candidate PDFs across docxodus, jubarte-rust, jubarte-093 and
superdoc. Its Word oracles are corpus files, not in that preset. The requested local
`results/redlines_0929_split/` has the 800-pair CSV and complete scores but **no PDFs**;
the dataset's recursive listing has no split archive either. The older candidate outputs
cannot substantiate these split-run scores. The exact split candidate PDFs are needed;
`jobs_redlines.json` records each expected filename. Planned split groups are 318 accepted/tracking_without_comments, 82 accepted/with_comments_tracking, 319 rejected/tracking_without_comments, and 81 rejected/with_comments_tracking. Recorded split pixel means (800-case ITT) are docxodus 87.7234, jubarte-rust 86.8886, and superdoc 12.5146; J/SSIM/TB remain unavailable until those PDFs are restored. [source_summary.json](source_summary.json) preserves the source counts, pixel means and failures for every requested set, separately from built asset counts. Until supplied, there is no
`build/cases_redlines.json`, and the previews/report explicitly remain partial.

Once the correct source is supplied, use narrow `bench hub get redlines-0929 --include`
globs only if that preset actually contains it. Do not download the older full run or
substitute its PDFs. The scripts already preserve the 21 docxodus and 693 SuperDoc
recorded split failures, and never require PDFs for those failures.
