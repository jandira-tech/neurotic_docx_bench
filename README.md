# neurotic-docx-bench

How close can DOCX redline tools get to **Microsoft Word**?

This benchmark takes real `base → next` document pairs, asks each tool to produce a
tracked-change redline, renders the result to PDF, and scores every page **pixel-wise**
against a committed **Word oracle** for that pair. Higher scores mean the tool’s redline
looks more like Word’s.

| | |
| --- | --- |
| **Scores** | 0–100 per document (higher is better) |
| **Oracle** | Word’s tracked-change markup, rendered by LibreOffice 26.2.4.2 |
| **Trend log** | `results/bench.jsonl` (append-only) |
| **Full tables** | [`RESULTS.md`](RESULTS.md) · [`docs/RESULTS.md`](docs/RESULTS.md) |
| **Speed** | [`docs/SPEED.md`](docs/SPEED.md) |

Refresh the ranking block below after a run:

```bash
python3 scripts/export-results-md.py          # RESULTS.md + docs/RESULTS.md
python3 scripts/export-results-md.py --output docs/RESULTS.md
bun run update-readme-ranking                 # tables between RANKING markers
```

> **The oracle in one sentence.** Markup comes from real Microsoft Word; PDFs are rendered
> with **LibreOffice 26.2.4.2** for both oracle and candidates so scores measure
> *redline-markup fidelity vs Word*, not renderer drift. Feeding the oracle’s own source
> DOCX back through that pipeline scores **100** (sanity check).

<!-- RANKING-START -->
### script_redlines — redline markup vs Word

Sorted by median score (0–100, higher is closer to the oracle). Multiple **versions** of the same vendor are listed separately.

| Rank | Vendor | Version | Docs | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@cdfef70a7156 | 207 | 81.04 | 84.72 | 42 | 0 |
| 2 | jubarte | jubarte-final@dd16ad8fbcf3 | 207 | 79.44 | 79.95 | 54 | 0 |
| 3 | jubarte | jubarte-final@6481c2fdbfc0 | 207 | 79.25 | 78.82 | 45 | 0 |
| 4 | jubarte | jubarte-final@4f56a39e78ef | 207 | 79.22 | 78.82 | 45 | 0 |
| 5 | jubarte | jubarte-final@755ee30d148c | 207 | 79.22 | 78.82 | 45 | 0 |
| 6 | jubarte | jubarte-final@a764898a424c | 207 | 79.16 | 78.78 | 46 | 0 |
| 7 | jubarte | jubarte-final@a56814ce307c | 207 | 79.12 | 78.78 | 46 | 0 |
| 8 | jubarte | jubarte-final@04dabff1cfaf | 207 | 77.82 | 78.62 | 34 | 0 |
| 9 | jubarte | jubarte-final@ac1fcea44646 | 207 | 77.82 | 78.62 | 34 | 0 |
| 10 | jubarte | jubarte-final@717311c03d4f | 207 | 73.48 | 73.13 | 25 | 0 |
| 11 | jubarte-rust | jubarte-rust@6233a48e4ac8 | 196 | 66.31 | 64.17 | 0 | 0 |
| 12 | jubarte | jubarte-final@b4f90acaa85e | 196 | 64.69 | 63.48 | 0 | 0 |
| 13 | jubarte-rust | jubarte-rust@b834d6e49fdb | 172 | 61.78 | 59.28 | 2 | 35 |
| 14 | superdoc-redlines | 0.2.0 | 192 | 57.63 | 55.90 | 0 | 15 |
| 15 | superdoc | 1.19.2 | 182 | 57.19 | 55.60 | 2 | 25 |
| 16 | docxodus | 7.0.0 | 205 | 58.75 | 55.03 | 3 | 2 |
| 17 | docxodus | 6.4.0 | 205 | 58.74 | 55.03 | 3 | 2 |
| 18 | folio | 0.3.1 | 205 | 55.31 | 53.75 | 0 | 2 |
| 19 | redlines | 0.6.1 | 200 | 51.28 | 51.77 | 0 | 7 |

### accepted_changes — accept all changes, match final doc

Sorted by median score (0–100, higher is closer to the oracle). Multiple **versions** of the same vendor are listed separately.

| Rank | Vendor | Version | Docs | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte | jubarte-final@dd16ad8fbcf3 | 164 | 86.53 | 94.42 | 63 | 0 |
| 2 | jubarte-rust | jubarte-rust@cdfef70a7156 | 164 | 84.27 | 88.74 | 54 | 0 |
| 3 | jubarte | jubarte-final@717311c03d4f | 166 | 78.15 | 80.64 | 26 | 0 |
| 4 | docxodus | 6.4.0 | 164 | 69.00 | 77.19 | 14 | 0 |
| 5 | docxodus | 7.0.0 | 164 | 70.20 | 74.92 | 17 | 0 |
| 6 | superdoc | 1.19.2 | 150 | 63.82 | 61.12 | 2 | 16 |
| 7 | folio | 0.3.1 | 164 | 57.91 | 55.61 | 3 | 10 |
| 8 | jubarte-rust | jubarte-rust@b834d6e49fdb | 147 | 63.50 | 54.45 | 13 | 27 |

### roundtrip — self-diff must not invent noise

Sorted by median score (0–100, higher is closer to the oracle). Multiple **versions** of the same vendor are listed separately.

| Rank | Vendor | Version | Docs | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | jubarte-rust | jubarte-rust@cdfef70a7156 | 166 | 99.17 | 100.00 | 157 | 0 |
| 2 | folio | 0.3.1 | 198 | 98.07 | 100.00 | 185 | 0 |
| 3 | jubarte | jubarte-final@dd16ad8fbcf3 | 166 | 97.63 | 100.00 | 152 | 0 |
| 4 | docxodus | 7.0.0 | 166 | 97.43 | 100.00 | 148 | 0 |
| 5 | jubarte | jubarte-final@717311c03d4f | 199 | 94.49 | 100.00 | 149 | 0 |
| 6 | jubarte-rust | jubarte-rust@b834d6e49fdb | 171 | 93.12 | 100.00 | 120 | 23 |
| 7 | superdoc | 1.19.2 | 194 | 93.00 | 100.00 | 144 | 3 |
| 8 | docxodus | 6.4.0 | 198 | 92.24 | 100.00 | 144 | 0 |

### visual_rendering — editor render of plain DOCX

Sorted by median score (0–100, higher is closer to the oracle). Multiple **versions** of the same vendor are listed separately.

| Rank | Vendor | Version | Docs | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | superdoc | 1.44.1 | 199 | 58.78 | 61.25 | 0 | 0 |
| 2 | folio | 0.5.0 | 198 | 59.65 | 55.10 | 0 | 0 |
| 3 | docxodus | 6.4.0-local.1 | 190 | 56.50 | 49.72 | 0 | 9 |
| 4 | docxodus | 7.0.0 | 190 | 56.50 | 49.72 | 0 | 9 |

### visual_redlines — editor render of redline DOCX

Sorted by median score (0–100, higher is closer to the oracle). Multiple **versions** of the same vendor are listed separately.

| Rank | Vendor | Version | Docs | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 145 | 60.92 | 61.22 | 0 | 37 |
| 2 | superdoc | 1.44.1 | 164 | 55.33 | 56.42 | 0 | 1 |
| 3 | folio | 0.5.0 | 164 | 51.55 | 51.65 | 0 | 2 |
| 4 | docxodus | 7.0.0 | 164 | 48.23 | 48.08 | 0 | 2 |

### visual_accepted_changes — editor render of accepted DOCX

Sorted by median score (0–100, higher is closer to the oracle). Multiple **versions** of the same vendor are listed separately.

| Rank | Vendor | Version | Docs | Mean | Median | Perfect (100) | Failures |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | docxodus | 6.4.0 | 152 | 62.32 | 62.76 | 0 | 0 |
| 2 | superdoc | 1.44.1 | 165 | 59.34 | 60.97 | 0 | 0 |
| 3 | folio | 0.5.0 | 164 | 59.67 | 54.95 | 0 | 0 |
<!-- RANKING-END -->

---

## What each benchmark measures

There are **six** benchmarks. The first three score **generator** quality through
LibreOffice. The last three score **web-editor** rendering through Playwright. **Do not
compare LibreOffice scores to Playwright scores** — only compare vendors within the same
benchmark.

### Generator fidelity (LibreOffice render)

| Benchmark | In plain English | What we feed the tool | What we score against |
| --- | --- | --- | --- |
| **`script_redlines`** | “Does your redline look like Word’s redline?” | `base.docx` + `next.docx` → tool produces a redline DOCX | Word’s redline PDF for that pair |
| **`accepted_changes`** | “If someone accepts all your tracked changes, is the final document right?” | Accept every `w:ins`/`w:del` on the tool’s redline | Word’s redline with all changes accepted |
| **`roundtrip`** | “Does a no-op self-diff invent junk?” | Tool diffs a document against itself (or re-serializes via its roundtrip path) | The original source PDF — perfect identity is **100** |

**`script_redlines`** is the headline metric: pixel match of the tool’s redline markup
against Word’s redline for the same pair.

**`accepted_changes`** catches tools that paint a pretty redline but put the wrong text in
the “final” document once changes are accepted (common when inserts/deletes are misplaced).

**`roundtrip`** is an identity / cleanliness test. Diffing a document with itself (or
running the tool’s roundtrip pipeline) should not invent spurious markup. High medians near
100 are expected; large drops mean the engine is noisy.

### Editor fidelity (Playwright viewer)

These open DOCX in each vendor’s **web editor** (not LibreOffice), screenshot pages to PDF,
and score against the matching Word-oracle PDF corpus.

| Benchmark | Document shown in the editor | Oracle PDF corpus |
| --- | --- | --- |
| **`visual_rendering`** | Plain source DOCX (`docx_source`) | `pdf_source` |
| **`visual_redlines`** | Word’s redline DOCX (`docx_redlines_word`) | `pdf_redlines_word` |
| **`visual_accepted_changes`** | Accepted Word redlines (`docx_accepted_word`) | `pdf_accepted_word` |

Notes that matter when reading scores:

- **SuperDoc generator ≠ SuperDoc editor.** Generator runs use the Python SDK
  (`superdoc-sdk` **1.19.2**). Visual runs use the browser editor (`superdoc` **1.44.1**).
  Different packages, different version numbers — both are intentional.
- **Folio generator ≠ Folio viewer.** Generator uses `@stll/folio-core` **0.3.1**; visual
  runs use `@stll/folio-react` **0.5.0**.
- Visual runs isolate **viewer** fidelity (they load Word’s DOCX, not the tool’s own
  redlines), so a strong visual score does not prove a strong generator.

---

## Tools

| Vendor | What runs | Version pin | Role |
| --- | --- | --- | --- |
| **jubarte** | In-repo `dist/jubarte-final` (`compareDocx` / CriticMarkup paths) | content-hash under `dist/` | Generator |
| **jubarte-rust** | Rust port under `utils/jubarte` | content-hash | Generator |
| **docxodus** | npm `docxodus` WASM `compareDocuments` | **6.4.0** | Generator + viewer |
| **folio** | `@stll/folio-core` compare + applyOperations | **0.3.1** | Generator |
| **folio** (viewer) | `@stll/folio-react` Playwright harness | **0.5.0** | Editor |
| **superdoc** | Python `superdoc-sdk` Document Engine | **1.19.2** | Generator |
| **superdoc** (editor) | npm `superdoc` Playwright harness | **1.44.1** | Editor |
| **docx-redline-js** | `@ansonlai/docx-redline-js` OOXML reconciliation | **0.2.0** | Generator |
| **redlines** | [houfu/redlines](https://github.com/houfu/redlines) text differ (`redlines_gen.py` wraps it with DOCX extract/rebuild) | **0.6.1** | Generator (text-level baseline) |
| **superdoc-redlines** | [yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines) SuperDoc-headless CLI (`superdoc_redlines_gen.py` aligns blocks, the CLI applies word-diffed track changes) | **0.2.0** | Generator |

Pins live in [`bench.yaml`](bench.yaml). Do not bump to `@latest` without re-review — the
pin is what keeps CI and published rankings reproducible.

---

## Quick start

**Requirements:** Python 3.14 (`uv`), Bun (or Node), **LibreOffice 26.2.4.2** on `PATH`.

```bash
uv sync
bun install --frozen-lockfile

# Per-tool node deps (generators + viewers)
cd src/neurotic_docx_bench/utils/docxodus && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/docx-redline-js && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/folio && bun install --frozen-lockfile && cd -
cd src/neurotic_docx_bench/utils/superdoc && bun install --frozen-lockfile && cd -
cd harness/folio-viewer && bun install --frozen-lockfile && cd -

# Smoke one tool on a few docs
uv run bench run --only jubarte-final-lossless --limit 5

# Full suite (all runs in bench.yaml)
uv run bench run
```

Each run: resolve `tool_version` → generate redlines → render → score vs oracle → append
one JSONL line to `results/bench.jsonl` → gate against the accepted snapshot.

Work folders land in `runs/{run}_{datetime}`. Use `--clean-runs` in CI to delete them after
a successful emit (kept on failure for debugging).

### Useful commands

```bash
uv run bench run --only docxodus --limit 5 --no-emit   # quick smoke, no JSONL write
uv run bench run --only-on-change                      # append JSONL only when scores change
uv run bench run-all --really-all                      # every run + generate_scripts
uv run bench accept-scores jubarte                     # promote latest line to gate baseline

uv run bench render <docx-dir> <work-dir> -b soffice   # DOCX → PDF
uv run bench compare <candidate-pdfs> <oracle-pdfs> --tool name
uv run bench accept <redline-docx-dir> --out <folder>  # accept all tracked changes
uv run bench reject <redline-docx-dir> --out <folder>
```

Common flags: `--config`, `--limit`, `--dpi`, `--no-update`, `--emit/--no-emit`,
`--gate/--no-gate`, `--generate/--no-generate`, `--results-dir`, `--runs-dir`.

---

## How scoring works

1. **Match** candidate PDF ↔ oracle PDF by `<base>_<next>` key (redlines) or plain stem
   (roundtrip / some visual runs).
2. **Raster** every page at the configured DPI (default 144).
3. **Score** each page with a weighted blend of SSIM, ink-F1, edge-IoU, colour ΔE, and blob
   metrics → 0–100, then aggregate per document and per run.

The scoring core (`score.py`, `diff.py`, `raster.py`, …) is lifted **verbatim** from
[superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks);
`tests/test_parity.py` guards byte-identical behaviour against a committed reference.

**Page-count mismatches** are recorded (`page_count_mismatch`) but not penalised — only
`min(pages)` is compared.

### Gate (CI)

- Score **100** always passes.
- A **per-document** drop vs the accepted snapshot → warning.
- An **aggregate** drop (mean or median) → **fail** (non-zero exit).

Promote a good run: `uv run bench accept-scores <tool>`.

---

## Speed

Generation and render speed are measured separately into `results/speed.jsonl`. See
[`docs/SPEED.md`](docs/SPEED.md).

```bash
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --out results/speed.jsonl
uv run python -m neurotic_docx_bench.superdoc_speed --pairs 30 --reps 3 --out results/speed.jsonl
```

---

## Project map

```
bench.yaml                 # runs, pins, oracles, generate_scripts
corpus/word_based/         # source / redline / accepted DOCX + PDF oracles
results/bench.jsonl        # append-only trend log (schema v4)
results/score-snapshots/   # gate baselines
src/neurotic_docx_bench/   # CLI, pipeline, scoring, generators
scripts/                   # Node generators, ranking export, speed bench
runs/                      # per-run work dirs (local; often gitignored artifacts)
```

Agent-oriented invariants: [`AGENTS.md`](AGENTS.md). Contributor notes: [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## Provenance & thanks

- **[balalofernandez/docx-revisions](https://github.com/balalofernandez/docx-revisions)** —
  accept/reject tracked changes (`bench accept` / `reject`).
- **[superdoc-dev/superdoc-visual-benchmarks](https://github.com/superdoc-dev/superdoc-visual-benchmarks)** —
  visual scoring core.
- **[JSv4/docxodus](https://github.com/JSv4/docxodus)** &
  **[react-docxodus-viewer](https://github.com/JSv4/react-docxodus-viewer)** (MIT).
- **[AnsonLai/docx-redline-js](https://github.com/AnsonLai/docx-redline-js)** (MIT).
- **[houfu/redlines](https://github.com/houfu/redlines)** (MIT) — Ang Hou Fu's text-level
  redliner; the `redlines` runs wrap it as a pure-text baseline generator.
- **[yuch85/superdoc-redlines](https://github.com/yuch85/superdoc-redlines)** (Apache-2.0) —
  SuperDoc-headless CLI for block-ID tracked-change edits; the `superdoc-redlines` run
  drives its extract→apply pipeline with a deterministic block alignment.
- **[stella/folio](https://github.com/stella/folio)** (Apache-2.0).
- **[SuperDoc](https://github.com/Harbour-Enterprises/SuperDoc)** (AGPL-3.0) and related
  SuperDoc tooling.

## License

Scoring core derived from
[`superdoc-visual-benchmarks`](https://github.com/superdoc-dev/superdoc-visual-benchmarks).
This repository is licensed under **AGPL-3.0-only**. See [`LICENSE`](LICENSE).

Published scores are independent engineering measurements — not endorsements of any
third-party product. Microsoft Word is a trademark of Microsoft; the Word oracle is used
for measurement only.
