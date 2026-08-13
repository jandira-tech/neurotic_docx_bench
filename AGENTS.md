# AGENTS.md — neurotic-docx-bench

Guidance for AI agents and contributors working on this repo. Read this before changing
anything; the invariants below are load-bearing.

Before changing, rebuilding, or benchmarking the Rust redline engine, also read
`../reconciliation_plan/GET_JUBARTE_RUST.md`. The only canonical local Rust source
checkout is `../jubarte-redlines` (`~/T/jubarte-redlines`). Everything under this
repository's `src/neurotic_docx_bench/utils/jubarte/jubarte-rust` and
`src/neurotic_docx_bench/utils/jubarte/jubarte-wasm/pkg` is a consumer artifact;
never implement an engine fix in those copies.

## What this is

A benchmark that measures how faithfully DOCX tools reproduce **Microsoft Word's**
tracked-change redlines. For each `base → next` document pair, a tool generates a redline
DOCX; the bench renders it to PDF, rasterises every page, and scores it pixel-wise against
a committed **Word oracle** redline for that pair.

## Quickstart

```bash
uv sync                       # Python bench (Python 3.14; needs LibreOffice on PATH)
bun install --frozen-lockfile # Node redline generators (jubarte, docxodus, docx-redline-js)
cd src/neurotic_docx_bench/utils/docxodus && bun install --frozen-lockfile
cd src/neurotic_docx_bench/utils/docx-redline-js && bun install --frozen-lockfile
cd src/neurotic_docx_bench/utils/folio && bun install --frozen-lockfile
cd src/neurotic_docx_bench/utils/superdoc && bun install --frozen-lockfile
uv run bench run              # all tools sequentially → results/bench.jsonl
uv run bench run --only jubarte-final-lossless --limit 5   # one tool, quick
uv run pytest -q              # 68 tests
bunx vitest run               # 7 TS-driver tests (scoped by vitest.config.ts)
```

## Architecture (data flow)

```
bench.yaml → cli.run → per tool:
  resolve tool_version → generate (candidate DOCX) → render (→ PDF) →
  raster (→ PNG per page) → match to oracle by <base>_<next> → score_document →
  append one JSONL line (scores + failures) → gate vs snapshot
```

Key modules (`src/neurotic_docx_bench/`):
- `score.py` `diff.py` `raster.py` `report.py` `html_report.py` `utils.py` — the scoring
  core, **lifted verbatim** from superdoc-visual-benchmarks. **Do not edit their logic** —
  `tests/test_parity.py` guards byte-identical scoring against `tests/reference/`.
- `pipeline.py` — match candidate↔oracle redlines by `<base>_<next>` key, rasterise, score.
- `render/` — `soffice` (LibreOffice, default), `passthrough` (score existing PDFs),
  `playwright` (selector-driven web-editor render), `word` (local-only AppleScript).
- `emit/` — `jsonl` (append-only trend log), `snapshot`, `markdown`, `html`, `gallery`
  (per-run `report.html`: worst-first candidate-vs-oracle page gallery from the
  persisted `score/` rasters; emitted automatically by `bench run`).
- `aggregate.py` `gate.py` `tool_updater.py` `provenance.py` `config.py` `cli.py`.
- `superdoc_gen.py` — the SuperDoc (Python SDK) redline generator.
- `scripts/generate-native-redlines.ts` — jubarte / docxodus / docx-redline-js generators.

## The oracle — READ THIS

- Ground truth: `corpus/word_based/pdf_redlines_word/*.pdf`, named `<base>_<next>_redline.pdf`.
  The tracked-change **markup** is Microsoft Word's; the PDF **rendering** is
  **LibreOffice 26.2.4.2** (`Producer` metadata). Candidates are rendered the same way, so a
  score isolates *redline-markup fidelity vs Word*, not renderer drift.
- Rendering the oracle's own source DOCX via LibreOffice 26.2.4.2 reproduces it
  **pixel-for-pixel → 100** (the `word-redlines-soffice` sanity run). The bench is therefore
  **pinned to LibreOffice 26.2.4.2**; CI regenerates the oracle in-image so any LO version
  works there (see `.github/workflows/bench.yml`).
- `pdf_redlines_word/` also holds ~163 **non-redline base PDFs**; matching excludes them
  (`pipeline.is_redline`) and **raises on any key collision** — never silent last-wins.
- The authoritative pairing is `corpus/word_based/centralized_mapping.csv`
  (`base`, `next`, `pdf_redline = <base>_<next>_redline.pdf`, …).

## Tools benchmarked

| Run | Engine | Version source |
|---|---|---|
| `jubarte-final-native` | jubarte `redlineDocx` (CriticMarkup) | `dist/jubarte-final` content-hash |
| `jubarte-final-lossless` | jubarte `compareDocx` (its in-tree docxodus port) | `dist/jubarte-final` content-hash |
| `docxodus` | real JSv4/docxodus WASM `compareDocuments` | npm `docxodus@9.8.0` |
| `docx-redline-js` | `@ansonlai/docx-redline-js` OOXML reconciliation | npm `@0.2.0` |
| `folio` | `@stll/folio-core` `compareDocxVersions`+`FolioDocxReviewer.applyOperations` | npm `@stll/folio-core@0.3.1` |
| `superdoc` | SuperDoc SDK (Python) Document-Engine diff | pip `superdoc-sdk` |
| `redlines` | houfu/redlines text diff → `w:ins`/`w:del` DOCX rewrite (`redlines_gen.py`) | pip `redlines` |
| `superdoc-redlines` | yuch85/superdoc-redlines SuperDoc-headless CLI, extract→align→apply (`superdoc_redlines_gen.py`) | clone `package.json` version |
| `jubarte-rust` | `jubarte-redlines` native CLI (Rust Word-mode comparer) | binary content-hash |
| `jubarte-wasm` | wasm-bindgen adapter over the canonical `jubarte-redlines` library | generated WASM hash + source commit |
| `word-redlines-soffice` | identity sanity (renders the Word redline DOCX) | — |

**Tool versions are pinned** to the reviewed ones (see `bench.yaml`). Do **not** bump to
`@latest` without re-review — the pin keeps CI reproducible.

### Adding a tool
1. Give it a real **headless** compare API (base+next → redline DOCX). If it only has a
   GUI compare, it can't be a headless generator here (see LibreOffice below).
2. Add an engine to `scripts/generate-native-redlines.ts` (Node) **or** a Python generator
   module (like `superdoc_gen.py`) that writes `<base>_<next>_<tool>_redline.docx`.
3. Generators write `$RUN_DIR/generate_failures.json` (`[{doc, stage, error}]`) and must
   **not** abort on partial failure — exit non-zero only on a total wipeout. They must
   also accept `--manifest` / `--source-dir` (the driver supplies both — see 4).
4. Add a run to `bench.yaml`; set the version source (`dist:` / `package:` / `python_package:`).
   Write **one** `generate:` invocation with **no** `--manifest` / `--source-dir`: the
   driver runs it once per entry in the yaml's top-level `corpora:` list, so every vendor
   is scored on the same 803 pairs. Hardcoding either flag is rejected at config load.
   A run that genuinely applies to one pool names it: `corpora: [word_based]`.
   Adding a fourth pool = one entry in `corpora:`, and every vendor picks it up.
5. Add a test (pytest or vitest) that asserts it emits `w:ins`/`w:del`.

## JSONL line (results/bench.jsonl) — append-only

One line per **vendor×benchmark** run, **always appended** (never rewritten;
`--only-on-change` opts into a delta log). **Schema v4.** Key order is **stable** with
`id_run`, `vendor`, `benchmark` first. Each line is a typed
`Results` (`src/neurotic_docx_bench/results_schema.py`): identity triple
(`id_run` UUIDv7, `vendor`, `benchmark`), aggregate score fields (`n_docs`,
`overall_mean`, `overall_median`, `exact_100`, `at_least_90`, `below_50`, `min`/`max`/
`std`/`q1`/`q3`, `page_mean`/`page_median`), speed stats (`overall_mean_speed`, …,
`q3_speed`), `score_config` (mirrors `ScoreConfig`), `environment_config` (the parsed
`BenchConfig`), `scores` (per-doc), `per_doc`, `failures`
(`[{doc, stage: generate|missing_source|render, error}]`), `timings` (per-step seconds),
`tool_version`, `config_hash`, `timestamp`.

The six `benchmark` names: `script_redlines`, `accepted_changes`, `roundtrip`,
`visual_rendering`, `visual_redlines`, `visual_accepted_changes` (see
`benchmarks.py`). `script_redlines` = vendor redline DOCX rendered by LibreOffice vs the
Word oracle; the `visual_*` benchmarks render through a dependency viewer (Playwright).
Legacy schema-v2/v3 lines (keyed by `tool`/`stage`) still live in the trend log and are
read back by the legacy readers; new runs emit v4 only. Delta-log change detection keys
on `scores`. Skip-already-ran keys on `(vendor, benchmark, tool_version, config_hash)`.
Snapshots live at `results/score-snapshots/{vendor}__{benchmark}.json`.

## Speed benchmark

Separate from the fidelity score, `results/speed.jsonl` (append-only, one row per engine
per run) measures **redline-generation time** (`unit: ms_per_redline`). Run it:

```bash
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl
uv run python -m neurotic_docx_bench.superdoc_speed --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl
# Large-N native CLI (C# Docxodus + jubarte-rust): 1000 fixtures → 5000 pairs, samply profiles
bun run redline-speed-bench:native
```

**Render speed** (`unit: ms_per_render`) — how long a Playwright viewer takes to render a
DOCX to PDF — is measured two ways (see `docs/SPEED.md` § Render speed): (1) per-run in
`results/bench.jsonl`, where every `visual_*` line carries `overall_*_speed` stats + a
per-doc `timings` map with `render_s` derived from the `PlaywrightRenderer`'s `duration_ns`
(the same field `soffice` sets — the three `visual_*` benchmarks share one render pass, so
they share its render-speed distribution); (2) standalone with reps/warmup/full percentiles:

```bash
uv run python -m neurotic_docx_bench.playwright_speed --docx-dir corpus/word_based/docx_redlines_word \
  --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl --tool folio-playwright \
  --url http://127.0.0.1:5175/harness.html --file-input "#fileInput" --page-selector ".layout-page" \
  --readiness-js "window.__folioReady === true" --server "cd harness/folio-viewer && npx vite --port 5175 --host 127.0.0.1"
```

Methodology (see `docs/SPEED.md`): pairs pre-loaded into memory, engine init timed
separately, warmup, per-call high-res sampling, failures excluded, full distribution
(median/mean/p90/p95/p99/min/max/std/throughput). **Fairness caveat:** Node engines are
timed as an in-memory `compare(base,next)→bytes`; SuperDoc's SDK is file-path based so its
samples include the full open/save disk cycle. Render-speed uses a fresh browser context
per call (mirroring `PlaywrightRenderer.to_pdfs`) so a stale readiness flag can't leak
between docs. CI runs a smaller 20×2 sample and appends.

## Regenerating the Word oracle PDFs (macOS + Word, local-only)

The committed oracle PDFs (`corpus/word_based/pdf_redlines_word/*.pdf`) are Word redline
markup rendered to PDF. To regenerate them (or render a new set into a sanity directory),
use the `WordRenderer` (`src/neurotic_docx_bench/render/word.py`) or the batch script.

**Permission-prompt trap — read this first:** macOS shows one AppleScript permission dialog
per `osascript` process. The `WordRenderer.to_pdfs()` calls `osascript` **once per file**,
so 232 DOCX files = 232 permission prompts. Never run it for a full batch. Instead, generate
a **single monolithic AppleScript** that processes all files inside one
`tell application "Microsoft Word"` block and pipe it to **one** `osascript` call — one prompt
for the entire batch.

**"Best for printing" export quality:** Word's AppleScript `save as` does not expose the
"Optimize for: Best for printing / Best for online viewing" radio button. The setting is
**sticky** — Word reuses whatever you last chose in the GUI Export dialog. So before a batch:
open any DOCX in Word → File → Export... → PDF → select **"Best for printing"** → Export.
All subsequent `save as ... file format format PDF` calls inherit that choice.

**Step-by-step batch conversion (one permission prompt):**

```bash
# 1. Clean Word temp/lock files (~$ prefix) from the source dir — they cause failures:
rm -f corpus/word_based/docx_redlines_word/~\$*.docx

# 2. Manually export one PDF in Word GUI choosing "Best for printing" (sets sticky pref).

# 3. Generate a single monolithic AppleScript for all DOCX files:
python3 -c "
from pathlib import Path
src = Path('corpus/word_based/docx_redlines_word').resolve()
out = Path('sanity_word/sanity_pdf_redlines_word').resolve()
out.mkdir(parents=True, exist_ok=True)
docs = sorted(src.glob('*.docx'))
lines = ['tell application \"Microsoft Word\"', '  set displayAlerts to false']
for docx in docs:
    pdf = out / (docx.stem + '.pdf')
    lines += ['  try',
              f'    open POSIX file \"{docx}\"',
              '    set theDoc to active document',
              f'    save as theDoc file name \"{pdf}\" file format format PDF',
              '    close theDoc saving no',
              '  on error',
              '    try',
              '      close every document saving no',
              '    end try',
              '  end try']
lines += ['  set displayAlerts to true', 'end tell']
print(chr(10).join(lines))
" | osascript   # MUST run in foreground so the single permission dialog is visible

# 4. Check for any missing PDFs and retry just those:
python3 -c "
from pathlib import Path
src = Path('corpus/word_based/docx_redlines_word').resolve()
out = Path('sanity_word/sanity_pdf_redlines_word').resolve()
missing = [d for d in sorted(src.glob('*.docx')) if not (out / (d.stem + '.pdf')).exists()]
print(f'Missing: {len(missing)}')
for m in missing: print(f'  {m.name}')
"
```

**Rules to avoid the permission-prompt nightmare:**
1. **One `osascript` call, all files inside.** Never loop `osascript` per-file.
2. **Run in foreground** (`osascript ...` directly, not backgrounded). Background mode
   buries the permission dialog where you can't see/click it.
3. **Use inline/heredoc AppleScript**, not `.scpt` files. Compiled `.scpt` triggers
   `-1708` errors on `save as` (see `corpus/word_based/docx_redlines_word/README.md`).
4. **Delete `~$` temp files first** — Word lock files cause spurious failures.
5. Some files intermittently fail `save as` with `-1708` ("active document doesn't
   understand the 'save as' message"). Retry just those individually with a `delay 2`
   after `open`.

## Gate (CI)

100 always passes. Per-doc decrease vs the accepted snapshot → **warning**; aggregate
decrease (mean or median) → **fail** (non-zero exit). `bench accept-scores <tool>` promotes
the latest line to the baseline.

## Gotchas / hard-won facts

- **`.old/` is git-ignored** and holds the original sources + SuperDoc/docs monorepos.
  Never let `vitest`/`pytest` scan it (that's why `vitest.config.ts` scopes to `scripts/`).
- **LibreOffice cannot generate redlines headless.** Its document-compare
  (`.uno:CompareTo` / `.uno:MergeDocuments`) is GUI-dialog-driven → 0 redlines headless, and
  macOS SIGKILLs the standalone LibreOffice Python. LO is the *renderer*, not a generator.
- **Page-count mismatch** is surfaced + recorded (`page_count_mismatch` in per-doc), not
  penalised — the verbatim scorer only compares `min(pages)`. Changing that is a policy call.
- **Scoring uses a process pool** (PyMuPDF/skimage aren't thread-safe).
- **soffice render** requires exit 0 **and** the output file, and deletes a stale PDF before
  a forced re-render (parity with the original shell script).

## Provenance

Scoring core: superdoc-visual-benchmarks. Tools: jubarte (in-repo), JSv4/docxodus,
JSv4/react-docxodus-viewer, AnsonLai/docx-redline-js, stella/folio, SuperDoc +
yuch85/superdoc-redlines, houfu/redlines, balalofernandez/docx-revisions. See README for
links + licenses.
