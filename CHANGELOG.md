# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added
- Generating runs for `stemma` (`stemma-cli` 0.5.0 `stemma compare`) and
  `safe-docx-compare` (UseJunior/safe-docx `compareDocuments` at PR 854 merge
  `7bd35c8`, not published `@usejunior/docx-compare@0.19.1`)
- In-repo tests that drive each shipped compare on a real corpus pair and
  assert native `w:ins`/`w:del`; pin tests refuse the pre-854 npm tarball
- `nupunkt==0.6.0` as a first-class pin; `redlines_gen` now requires
  `NupunktProcessor` (no silent WholeDocumentProcessor fallback)

### Changed
- Full-corpus `script_redlines` (plus accepted/roundtrip where declared) for
  stemma, safe-docx, and redlines-with-nupunkt; 803-pair generate universe
- Large-N `speed_redlines` pack (2026-08-15): 1000 fixtures → 5000 pairs
  including jubarte inproc/CLI/WASM and docxodus WASM / csharp-inproc

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
