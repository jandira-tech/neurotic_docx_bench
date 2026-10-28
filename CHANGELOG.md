# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 1.0.0 - 2026-10-28

### Added
- Packaged for PyPI as `neurotic-docx-bench` (#84; the upload is still to come). Fixture set **v1**: every file on the hub
  dataset whose oracle Microsoft Word made, for every test (2,925 `docx_to_pdf`, 3,502 `redline`,
  400 `accept_all`, 400 `reject_all` cases, plus the corpus tables), pinned to dataset commit
  `984e64d8`. The wheel ships the manifest only; `bench fixtures list|get` and
  `neurotic_docx_bench.fixture_sets` fetch and sha256-check the files. `bench fixtures build-set`
  rebuilds a manifest from the tables and the hub listing. `hub_get.remote_files`/`get` take
  `exact=` paths, compared as strings rather than globbed.
- `bench itt-complete-reports`: a listed score-only report that dropped crashed conversions is
  completed with them scored 0; the six affected soffice sample rows are appended corrected (#69).
- `py.typed`, project URLs and classifiers; the sdist holds the package only.

### Fixed
- A listed score-only `docx-to-pdf` run keeps a listed document with no PDF as a failure scored 0
  instead of dropping it (#69).
- History renders a measurement persisted several times as one row with its run count (#75).
- `fetch_compare_regen` writes compare ids to `regen_list.csv`, not `<id>__vs__<id>` stems (#81).
- `bench jubarte-release` and `release-info` check the compare_regen inputs before any Word step (#82).
- `bench.generated` is the day the samples were drawn (#60).
- The `_Progress` batch-log test waits for the state it asserts (#83).

## 1.0.0 (continued): the changes since 0.8.0

### Changed
- `scripts/word_pdf.py` recovery: a pass that ends on `Connection is invalid`, or a Word that stops
  answering, is recovered by `close every document saving no` on the running Word, and the run
  carries on with that Word as soon as it answers (0.2 to 1.2 s measured). Quit, SIGTERM, SIGKILL
  and a background relaunch happen only when the close-all errors or Word stays silent for
  `answer_grace` seconds, and the log says which ("because unresponsive for 15 s after the
  close-all"). The "restart only a Word this run launched" distinction is gone: the default policy
  closes every document whoever opened it; `--do-not-close` keeps the named close and refuses to
  restart. `recover_after_failure` follows the same policy. Word open with no document is normal.
  A pass that ended because Word answered and returned nothing three times in a row is the one
  case that restarts without a close-all, after one look at Word's front for a hidden modal;
  `preflight` runs the close-all as a health check and logs Word's pid.
- The Microsoft Error Reporting dialog is treated as the crash signal (`--crash-signal`, default
  on): the watchdog ends that pass's osascript at once and marks the item Word was on, instead of
  waiting 4 to 5 s for the AppleEvent to fail. A/B on 20 Word-crashing corpus documents: 251 s
  against 382 s, nothing lost; with `--crash-limit 1`, 111 s. The default crash limit stays 2.
- Every file Word writes is named `<stem>_byword.<ext>` (`by_tool`; `_bysoffice`, `_bydocxide`,
  `_bywordcraft`, `_byjubarte` for the other engines). `render/word.py`, `word_actions.py` and the
  new `word_outputs.find_output` resolve outputs through the manifest, then the suffixed name, then
  the pre-suffix name, so folders rendered earlier still resolve; the drivers skip an output that
  exists under the old spelling instead of redoing it.
- Input file names longer than 80 characters (`word_pdf.py`) or 35 (`word_redline.py`) are renamed
  on disk before Word sees them, to `<cut>_<8 hex of sha1(original)><ext>`, logged and recorded in
  the manifest as `renamed`.
- The on-screen log prints lines verbatim and in colour: loguru's level colours plus rich's
  highlighting, with markup and emoji parsing off (`make_console_sink`). Rich had been eating
  `[word]`, `[batch]`, `[ok]` and turning `:recycle:` into ♻ on screen.
- `open produced 0 new documents` and "doesn't understand" errors from Word count toward the
  three-in-a-row empty-load rule in both batch scripts instead of being final failures: a Word in
  that state failed a 70-document batch in 5 s on 2026-10-14.

### Fixed
- `bench report`: the headline group of a benchmark no longer follows the newest eligible row onto
  a subset of another measured document set (`ledger/policy.py::subset_docsets`, read from the
  rows' own per-document scores). The PyMuPDF Pro row (unlicensed, first 3 pages, 253 of the
  cohort's 400 documents) had turned the `docx_to_pdf` headline into a one-row table; the 400-document
  group with ten converters is the headline again and the subset is named in the History pointer.
- `bench report` was refusing to run on `results/converters.jsonl`: the LibreOffice rows that
  `scripts/convert_candidates.py` writes under the tool name `candidates` had no registry mapping;
  they map to `soffice` now, and the fresh cohort's lanes (`wordcraft-cli-0.7.0`, `docxodus-13.0.0`,
  `folio-0.60.0`, `stemma-0.6.0`, `superdoc-2.20.0`, `docxide-pdf-0.18.4`, `rdocx-0.16.0`,
  `office2pdf-0.8.1`, `pdfitdown-4.2.0`, `libreoffice_convert_rust-0.1.0`, `pymupdf-pro-1.28.2`)
  have entries in `bench.registry.yaml`.
- `scripts/word_pdf.py` (and `word_redline.py` through it): Word's repair prompt is now
  recognised from the alert's text in the same osascript that reads its buttons, answered No,
  and followed to the "Word experienced an error trying to open the file" OK with Word brought
  forward; focus is handed straight back. The previous text-matched handler never compiled, so
  the generic fallback pressed No after ~6 s and the OK was never pressed while Word sat in the
  background, costing a 240 s AppleEvent timeout and a batch pass per broken file. Verified
  live 2026-10-14 on `really_broken` fixtures: 5 prompts answered, no timeout.

- A declined repair prompt no longer ends the batch pass, restarts Word, or earns the file a
  second try: the watchdog records `[declined]` in the batch log and the batch scripts fail that
  file outright when its open comes up empty. Three broken plus two good files: 3 m 41 s and one
  restart before, 18 s and none after.
- The export scripts (`_EXPORT_PDF`, `_EXPORT_BATCH`) bind the document `open` produced, found
  by exclusion as `_COMPARE` already did, never `document 1`: a leftover document was saved under
  a broken file's name once that file's open produced nothing.
- A stall report whose probes outlived the item ("item 1/1329 open for more than 30 s" pasted over
  a log showing 30 items done) is dropped: `_Progress._report` re-reads the batch log after probing
  and logs one line saying the item finished while it was looking.
- A nameless alert button is logged as "a button with no name (AppleScript 'missing value')"
  instead of `button 'missing value'`.

### Added
- The fresh cohort's canonical lines are in the stores: `results/bench.jsonl` (+9 `script_redlines`
  rows on docset `62d32b1f2954df42`), `results/converters.jsonl` (+11 `docx_to_pdf` rows, docset
  `c28442e9bb5a5deb`, PyMuPDF Pro on its 253-document subset `c1d39073ba89a2c3`) and
  `results/speed.jsonl` (+20). `RESULTS.md` carries the 400-document `docx_to_pdf` table (jubarte
  0.12.0 82.45 ITT median, 0.11.0 79.75, Wordcraft CLI 0.7.0 53.82, 0.6.1 52.82, docxide-pdf 0.18.4
  52.37, libreoffice_convert_rust 0.1.0 and LibreOffice 47.87, rdocx 0.16.0 45.90, office2pdf 0.8.1
  44.45, pdfitdown 4.2.0 41.95) and the fresh speed rows; the comparison rows have no gate set or
  null-baseline run for their docset, so they stand in `RESULTS_DETAILED.md` (Not ranked, History)
  until one is recorded (AGENTS.md, "Publishing results"). `RESULTS_v0.7.0.md` freezes the page
  as it was before the bench moved to 0.8.0.
- Wordcraft 400+400 cohort extended (`results/wordcraft_20261014_fresh/REPORT.md`): on the same frozen
  fixtures, fresh Word 16.115 oracles, Word renderer and scorer, the newest release of the top three
  non-jubarte tools of every past results table plus two releases that landed during the run.
  Comparisons (pagefair mean over 400, failures as zero): jubarte 0.11.0 76.75, 0.12.0 76.18, docxodus
  13.0.0 67.49 (12.6.5: 66.99), Wordcraft 0.7.0 46.05 (0.6.1: 46.01), folio-core 0.60.0 32.74 (133
  generate refusals), stemma 0.6.0 18.93 (292 `UnsupportedEdit` refusals), superdoc-sdk 2.20.0 5.33
  (364 refusals). Conversions: jubarte 0.12.0 79.89, 0.11.0 76.19, Wordcraft 0.7.0 56.42 (0.6.1:
  55.18, +1.24, 95% [+0.81, +1.69]), docxide-pdf 0.18.4 54.90, LibreOffice and libreoffice_convert_rust
  0.1.0 (same LibreOffice.app) 54.70, rdocx 0.16.0 47.80, office2pdf 0.8.1 45.89, pdfitdown 4.2.0 39.41;
  PyMuPDF Pro 1.28.2 (unlicensed, first 3 pages) 56.24 on the 253 conversions of at most 3 pages,
  with every converter's score on that subset beside it. Latency table in `docs/SPEED.md`.
  `lanes.py`, `finish_new.py`, `one_redline.ts`, `superdoc_one.py`, `add_tools.py` drive the added
  lanes; `folio_cli_probe/` shows folio-cli 0.5.1 `compare -o` is folio-core's call, output identical.
- `manifest.jsonl` in every output folder, appended per run: one JSON line per file produced
  (`original_filename`, `path_origin`, `converted_filename`, `path_out`, `status`, `kind`, `tool`,
  `error`, `seconds`, `run_at`; redline lines add `revision_filename`, `path_revision`,
  `revisions`, `unmatched`).
- Every recovery command is logged as it would be typed (`running: osascript -e '…'`,
  `pkill -x 'Microsoft Word'`, `open -g -a …`) with its result on the very next line
  (`returned rc=0 in 0.2 s, no value came back (AppleScript 'missing value')` / `got: …` /
  `error: …`).
- `scripts/word_ab.py`: the A/B harness AGENTS.md now requires when a batch turns up Word-crashing
  fixtures: stages 20 broken + 50 good, replays them under pinned driver variants, times detect /
  recover / resume per crash, writes `out/ab/results.jsonl` and `out/ab/AB_REPORT.md`
  (`report --drop STARTED_AT=reason` keeps an excluded run on the record).
- `word_redline.py` defers every pair that shares a file with a crashed pair to the back of the
  next pass (`[defer]`), not only the crashed pair.
- `tests/test_word_pdf_manifest.py`, `tests/test_word_outputs.py`, `tests/test_word_ab.py`.
- `--focus/--no-focus` and `--crash-limit` on `word_pdf.py` and `word_redline.py`; every Word
  alert is logged with its words and kept on `Watchdogs.events`; the batch progress tailer checks
  on an item not finished after 10 s (`_Progress.nudge_after`); `tests/test_word_pdf_alerts.py`.
- `results/wordcraft_20261014_fresh/`: Wordcraft CLI 0.6.1 against jubarte 0.11.0 / 0.12.0 and
  docxodus 12.6.5 (comparisons) and LibreOffice 26.8.1.1 (conversions) on a frozen 400 + 400
  sample with fresh Word 16.115 oracles (`REPORT.md`). Pagefair means, failures as zero:
  comparisons wordcraft 46.01, jubarte 0.11.0 76.75, jubarte 0.12.0 76.18, docxodus 66.99;
  conversions wordcraft 55.18, jubarte 0.11.0 76.19, jubarte 0.12.0 79.89, soffice 54.70.
  The run scripts (`build400.py`, `run_word400.py`, `generate_fresh.py`, `score_run.py`,
  `finish400.py`, `finish_rest.py`, `report.py`, `speed_table.py`) and committed driver copies
  (`drivers_ee49054d/`) are included. Registry entries for the four tools; a latency section
  in `docs/SPEED.md`.

### Deprecated
- `scripts/word_pdf_focus.py`: superseded by the above; kept as the record of the 2026-09-30 trial.

## [0.8.0] - 2026-10-02

### Added
- `CITATION.cff`
- `scripts/release_jubarte.py <x.y.z>`: scores a jubarte release from its GitHub asset
  (sha256 checked, never a local build): DOCX to PDF and docxide metrics on all of
  `corpus/word`, a `jubarte-<x.y.z>` redline lane in `redlines_0929_full` (generate, Word
  export under the watchdog, measure, Hub upload), `bench report`, then a results branch and
  pull request; `--plan`, `--only`, `--skip`, `--no-hub`
- DOCX to PDF on the full 6427-document `corpus/word:all` set for jubarte 0.10.1
  (`--revisions word --compress`), docxide-pdf 0.17.1 and LibreOffice 26.8.0.3, scored by
  pixels and by docxide-pdf's metrics; `scripts/{convert_candidates,score_candidate_dirs,
  docxide_metrics_dirs,build_converter_reports}.py` regenerate and score a candidate folder
- Scorers default to the mps device with every core; scoring and docxide-metrics write a
  resumable per-document JSONL checkpoint (aiofiles) and print a UTC-stamped progress line
- GitHub Pages DOCX to PDF comparison on jubarte 0.10.1 with 800 sampled corpus fixtures and
  their docxide-pdf and LibreOffice PDFs
- Generating runs for `stemma` (`stemma-cli` 0.5.0 `stemma compare`) and
  `safe-docx-compare` (UseJunior/safe-docx `compareDocuments` at PR 854 merge
  `7bd35c8`, not published `@usejunior/docx-compare@0.19.1`)
- In-repo tests that drive each shipped compare on a real corpus pair and
  assert native `w:ins`/`w:del`; pin tests refuse the pre-854 npm tarball
- `nupunkt==0.6.0` as a first-class pin; `redlines_gen` now requires
  `NupunktProcessor` (no silent WholeDocumentProcessor fallback)

### Changed
- README states the method as run, its limitations, who maintains the bench and how to
  dispute a result; `docs/VENDOR_NOTES.md` records the houfu/redlines correction; `LICENSE` is the
  canonical AGPL-3.0 text, so GitHub detects the licence
- `redlines_0929_full/{to_scores_jsonl,hub_upload}.py` take their tools from
  `versions.json` (to_scores_jsonl.py no longer rewrites it); the scores are unchanged
- Full-corpus `script_redlines` (plus accepted/roundtrip where declared) for
  stemma, safe-docx, and redlines-with-nupunkt; 803-pair generate universe
- Large-N `speed_redlines` pack (2026-08-15): 1000 fixtures → 5000 pairs
  including jubarte inproc/CLI/WASM and docxodus WASM / csharp-inproc

### Fixed
- `scripts/docx_to_pdf_speed.py`: version probes time out after 30 s and a
  silent probe still names the tool; an empty corpus (directory or `@LIST`)
  stops the run before any probe, worker or output; a tool with no successful
  conversion keeps its rows (n 0, failures, null `total_s`/mean/median/p95);
  p95 is the nearest-rank sample, as in `speed_stats` (it was the maximum at
  n = 20)
- `scripts/speed-bench.ts`: a missing jubarte-rust/jubarte-wasm build exits
  1 instead of writing a table without jubarte, and so does an init failure
  of a jubarte method or of any method named in `--methods`;
  `JUBARTE_WASM_DIST` overrides the WASM path

## [0.7.0] - 2026-09-27

### Added
- `bench_version` stamped on every store line; the report groups by bench series
  (major.minor), unstamped lines read as `0.6`
- Hugging Face datasets: `bench fixtures download|upload`
  (`arthrod/neurotic_docx_bench-fixtures`, sha256 manifest verified on download)
  and `bench results upload [--with-outputs] [--prune-local]`
  (`arthrod/neurotic_docx_bench`: per-version stores, pages, registry, the
  oracle files each docset used, optional run outputs; local outputs pruned only
  after every uploaded hash is read back and matches)
- `scripts/release.py`: refuses to release unless Microsoft Word on the machine
  answers, renders, and rendered the store's Word rows; pages current; tree
  clean; tag free; changelog entry present. Then tag, `uv build`, `uv publish`,
  GitHub release

### Changed
- Wheel no longer ships the vendored competitor tools (`utils/`); competitor SDKs
  moved to the `competitors` extra, torch to the `gpu` extra

## [0.6.0] - 2026-09-27

### Changed
- Packaging only: the last pre-consolidation tree (`bench/latest-competitors-0926`)
  published as a wheel without the vendored competitor tools; competitor SDKs
  under the `competitors` extra

## [0.50] - 2026-07-08

### Added
- FOLIO viewer harness and folio-playwright run for visual_* benchmarks
- Visual_* benchmark dispatch infrastructure with benchmark→oracle mapping
- PDF source oracle (205 base DOCX rendered to PDF)
- FOLIO roundtrip route and wiring for roundtrip benchmark
- Schema v4 standardized vendor×benchmark results
- Rich CLI with centralized benchmark header and six-tier score gradient
- Michigan Blue (#00274C) and Michigan Yellow (#FFCB05) color theming

### Changed
- Split folio-playwright into 3 runs (one per visual_* benchmark corpus)
- FOLIO vendor defaults now cover 5/6 benchmarks
- Accept/roundtrip stages now emit BenchmarkOutcome (per-doc + timings)
- Parallel accept-changes processing
- Longer soffice timeout for better reliability

### Fixed
- Playwright renderer now accepts timeout kwarg (was crashing folio-playwright run)
- Critical correctness fixes in benchmark pipeline
- Duplicate "benchmark" word in CLI output
- Cleaned up mkdtempSync dirs in generate-native-redlines tests

### Technical
- Pinned benchmarked tool packages to exact versions for reproducibility
- FOLIO capability honesty and adapter pinning
- Dead code removal and refactoring

## [0.40] - 2026-07-07

### Added
- SuperDoc TypeScript SDK as a tested engine and tool
- Speed benchmark with CI integration and documentation
- Auto-generated ranking tables in README
- AGPL-3.0 license attribution
- Word ground-truth corpus regeneration

### Changed
- Jubarte lossless WmlComparer via full Node OOXML adapter
- Full benchmark run for jubarte-fourth (both routes)
- Docxodus port restored to build-1 quality

### Fixed
- Prosemirror script REPO_ROOT bug
- SuperDoc-native wiring as a real bench.yaml run

### Technical
- Dropped 5 `prebaked` test-artifact lines from trend log
- Full 4-build results with distribution analysis

## [0.30] - 2026-07-06

### Added
- Jubarte fourth build with both CriticMarkup and lossless routes
- Docxodus port integration
- Comprehensive results documentation

### Changed
- Jubarte lossless route restored to build-1 quality
- Benchmark results aggregation improvements

### Technical
- Corpus expansion with additional document pairs
- Improved error handling in redline generation

## [0.20] - 2026-07-05

### Added
- Initial SuperDoc SDK integration
- Docx-redline-js engine support
- Roundtrip benchmark infrastructure
- Accepted changes benchmark

### Changed
- Benchmark pipeline refactoring for better modularity
- Improved corpus mapping and organization

### Fixed
- Rendering issues with specific document types
- Timeout handling in long-running benchmarks

### Technical
- Better error reporting and failure tracking
- Improved test coverage for benchmark tools

## [0.10] - 2026-07-04

### Added
- Initial benchmark framework
- Jubarte redline generation (CriticMarkup)
- Docxodus WASM compareDocuments integration
- Pixel-wise scoring against Word oracle
- LibreOffice rendering pipeline
- JSONL append-only results format
- Score snapshot gating for CI
- Visual rendering benchmarks with Playwright
- Speed benchmark infrastructure
- Comprehensive test suite (68 Python tests, 7 TS tests)

### Technical
- Scoring core lifted from superdoc-visual-benchmarks
- Corpus with Word-based redline ground truth
- Multi-tool benchmark architecture
- Vendor×benchmark results schema
- AGENTS.md documentation for contributors
