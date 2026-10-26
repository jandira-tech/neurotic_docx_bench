# AGENTS.md — neurotic-docx-bench

Guidance for AI agents and contributors working on this repo. Read this before changing
anything; the invariants below are load-bearing.

Before changing, rebuilding, or benchmarking the Rust redline engine, also read
`docs/GET_JUBARTE_RUST.md`. The only canonical local Rust source
checkout is `~/T/jubarte-redlines`, reached from this repo through the link
`src/neurotic_docx_bench/utils/jubarte/jubarte-redlines` (`scripts/link_engines.sh`). Everything under this
repository's `src/neurotic_docx_bench/utils/jubarte/jubarte-rust` and
`src/neurotic_docx_bench/utils/jubarte/jubarte-wasm/pkg` is a consumer artifact;
never implement an engine fix in those copies.

EXCEPT IF REQUESTED BY THE PERSON OR REQUIRED BY A SPECIFIC BENCHMARK OR TO DEVELOP A TOOL, YOU MUST RECORD THE RESULTS WITH RASTERS DELETED AFTER EACH TOOL SO SCORING DOESN'T FILL THE DISK.

## Publishing fixtures and results (wrangler, R2, D1, gh-pages)

`docs/PUBLISHING.md` is the manual for everything that leaves this machine: review
fixtures to the public R2 bucket `neurotic-docx-bench-pages`
(`scripts/publish/upload_r2.py`, bulk path through the `ndb-r2-upload` Worker), the
live bench's D1 `jubarte-live-bench` and its dashboard deploy (`live-bench/frontend`),
the D1 harvest loop (`live-bench/harvest/`, state in `live-bench/.work/`), the HF-hub
corpus, and the review website — this repo's `gh-pages` branch, checked out at `site/`
(a git-ignored linked worktree; `git worktree add site gh-pages` recreates it). After a
publish verifies, the local uploaded bytes are deleted; the tracked records under
`results/` are the copy of record. The 2026-10-14 wordcraft 400+400 cohort lives on R2
under `wordcraft-20261014/` (12,034 objects, `MANIFEST.sha256.txt` included).

## What this is

A benchmark that measures how faithfully DOCX tools reproduce **Microsoft Word's**
tracked-change redlines. For each `base → next` document pair, a tool generates a redline
DOCX; the bench renders it to PDF, rasterises every page, and scores it pixel-wise against
a committed **Word oracle** redline for that pair.

## Quickstart

```bash
uv sync                       # Python bench (Python 3.14; needs LibreOffice on PATH)
pnpm install --frozen-lockfile # Node 26 + pnpm workspace: root pin tree + utils/ engine fallbacks + live-bench frontend
uv run bench run              # all tools sequentially → results/bench.jsonl
uv run bench run --only jubarte-final-lossless --limit 5   # one tool, quick
uv run pytest -q              # 68 tests
pnpm exec vitest run          # 7 TS-driver tests (scoped by vitest.config.ts)
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
  `score.py` carries exactly two recorded deviations (0de6361bf, 2026-10-03): the ink
  threshold comes from the reference page for both sides, capped at 0.9 below Word's
  0.949 markup pane, and the alignment never lowers a score. The parity test applies
  those two to the frozen reference and fails on any other drift.
- `page_metrics.py` + `docxide_metrics.py`: the **second scorer**, Jaccard and text-boundary
  at 150 DPI, a Python port of sverrejb/docxide-pdf `tests/common/` (Apache-2.0) driven
  through PyMuPDF. Same rule: **do not edit the metric logic**; upstream is the authority
  and `tests/test_page_metrics.py` holds the port to the values frozen in
  `tests/reference/docxide_page_metrics.json` (recorded by upstream's own `page-metrics`
  binary, re-frozen on the MuPDF build named in that file's `_engine` block; the test
  refuses to run on another build). Since 0.7.0 `pipeline.score_pdf_pair` carries the
  same columns (`ink_jaccard`, `text_boundary`, `max_break_drift`) on every scored row.
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

- Everything Word produced lives in **`corpus/word/<state>/{docx,pdf}`** (states: `clean`,
  `tracking_without_comments`, `with_comments_tracking`, `with_comments_clean`,
  `accept_all`, `reject_all`), one naming scheme (`<idA>_<a>__vs__<idB>_<b>_redline_<idC>`
  for comparisons), built by `bench corpus build --origins <Word's working folders>`. Lists live in
  `corpus/word/pools/` (`<set>_pairs.csv`: key, base, next, docx, pdf, state; base/next are
  paths under `corpus/word` without the suffix). `corpus/` is the one source of truth; its
  docx and PDFs live on the Hugging Face hub (below) and may be absent locally. Code finds files through
  `neurotic_docx_bench.corpus_paths` (`pairs(set)`, `documents(set)`, `comparisons(set)`).
- The oracle's **markup** is Word's; its **rendering** must match the candidates' renderer.
  `bench.yaml` has `renderer: auto` and `oracle_roots: {word: corpus/word, soffice:
  corpus/libreoffice}`: with Word on the machine (`render/auto.py`, `BENCH_RENDERER=word|soffice`
  pins it) candidates render through `scripts/word_pdf.py` and score against Word's PDFs;
  otherwise through LibreOffice against `corpus/libreoffice/<state>/pdf`, the LibreOffice
  26.2.4.2 renders filed under the same Word stems (`word_map.csv` maps each to its Word PDF).
  A docx run whose renderer differs from the oracle's is refused at config load.
- Candidates are `<key>_<tool>`; matching (`pipeline.redline_key`) **raises on any key
  collision** — never silent last-wins. `corpus/word_based` and the old working folders are
  gone: code and research scripts read `corpus/word` and its pools. A pair's `stem` in
  `corpus_paths` is its pre-corpus `<base>_<next>` name (from `notices/RENAMED.csv`), so older
  results keyed by it still line up.

## Getting the corpus files back (they live on the hub)

On 2026-10-11 the 16,768 DOCX/PDF files under `corpus/` were uploaded to the public dataset
[`arthrod/neurotic_docx_bench-fixtures`](https://huggingface.co/datasets/arthrod/neurotic_docx_bench-fixtures)
(16,853 files, 2.72 GB, every one verified against the hub by sha256) and deleted locally: `corpus/` went
from 2.6 GB to 25 MB. The tables (`documents.csv`, `comparisons.csv`, `pools/`, `word_map.csv`,
`sources.tsv`), READMEs, `PROVENANCE.json` and manifests stayed. **Before anything that opens a docx or
PDF under `corpus/`** (a bench run, `bench corpus check`, `scripts/word_*.py` on corpus paths, a site
rebuild that reads Word's PDFs), bring them back:

```bash
uv run bench fixtures download                     # into corpus/; refuses any file not matching MANIFEST.sha256.json
uv run bench fixtures download --revision <sha>    # a pinned snapshot
uv run bench corpus check                          # re-checks corpus/word against corpus/word/MANIFEST.sha256.json
```

- The hub repo mirrors `corpus/` path for path (`word/`, `libreoffice/`, `word_unindexed/`, plus
  `mutation_probes/`, `canary_expected.json`, `holdout_combined.txt`, which the canary, holdout and
  mutation-probe tests read from `corpus/`). Its `data/*.parquet` and `README.md` (the dataset card) are
  derived; `*.log` files are not uploaded.
- One file without the whole tree: the `documents` / `comparisons` configs carry `*_repo_path` columns
  for `hf_hub_download("arthrod/neurotic_docx_bench-fixtures", path, repo_type="dataset")`.
- The repo's older by-origin layout (`word_based/`, `no_comments_pdf_was_generated_by_word/`, …) is
  the tag `layout-2026-10-10`.
- Re-publishing after a corpus change: `uv run --with polars --with huggingface_hub python scripts/hf_fixtures/hf_fixtures.py build|upload|verify`
  (rebuilds the card, the parquet configs and the root manifest; `upload` replaces the hub tree in
  one commit and refuses while any manifest file is missing locally, so download first; `verify` re-hashes every local file against the hub). `bench fixtures upload` writes the
  manifest but not this card and leaves stale remote files in place.

## Tools benchmarked

| Run | Engine | Version source |
|---|---|---|
| `jubarte-final-native` | jubarte `redlineDocx` (CriticMarkup) | `dist/jubarte-final` content-hash |
| `jubarte-final-lossless` | jubarte `compareDocx` (its in-tree docxodus port) | `dist/jubarte-final` content-hash |
| `docxodus` | real JSv4/docxodus WASM `compareDocuments` | npm `docxodus@9.8.0` |
| `docx-redline-js` | `@ansonlai/docx-redline-js` OOXML reconciliation | npm `@0.2.0` |
| `folio` | `@stll/folio-core` `compareDocxVersions`+`FolioDocxReviewer.applyOperations` | npm `@stll/folio-core@0.3.1` |
| `superdoc` | SuperDoc SDK (Python) Document-Engine diff | pip `superdoc-sdk` |
| `redlines` | houfu/redlines text diff → `w:ins`/`w:del` DOCX rewrite (`redlines_gen.py`, required `nupunkt==0.6.0`) | pip `redlines==0.6.1` + `nupunkt==0.6.0` |
| `superdoc-redlines` | yuch85/superdoc-redlines SuperDoc-headless CLI, extract→align→apply (`superdoc_redlines_gen.py`) | clone `package.json` version |
| `jubarte-rust` | `jubarte-redlines` native CLI (Rust Word-mode comparer) | binary content-hash |
| `jubarte-wasm` | wasm-bindgen adapter over the canonical `jubarte-redlines` library | generated WASM hash + source commit |
| `stemma` | stemma-cli 0.5.0 `stemma compare` | binary content-hash + git tag v0.5.0 |
| `safe-docx-compare` | UseJunior/safe-docx `compareDocuments` at PR 854 merge `7bd35c8` (not npm `@usejunior/docx-compare@0.19.1`) | dist content-hash + `ENGINE_COMMIT.txt` |
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

## Publishing results (`uv run bench report`)

`RESULTS.md`, `RESULTS_DETAILED.md`, the vendor table in `README.md` and the frozen
`RESULTS_v<old>.md` are generated from `results/bench.jsonl`, `results/converters.jsonl`,
`results/speed.jsonl`, `results/redlines_*/scores.jsonl` and `bench.registry.yaml` by
`src/neurotic_docx_bench/ledger/` (`build.py` loads, `policy.py` decides, `tables.py` renders).
Never edit them by hand; `uv run bench report --check` says whether they are current.

A cohort run that lives under `results/<run>/` (the 2026-10-14 Wordcraft cohort is the model)
reaches the pages in four steps, each of which bit someone on 2026-10-14:

1. The run's persist script (`results/wordcraft_20261014_fresh/persist_fresh.py`) emits
   canonical lines into the run directory's **own** `bench.jsonl` / `converters.jsonl` /
   `speed.jsonl`. It does not touch `results/*.jsonl`.
2. Append those lines to `results/bench.jsonl`, `results/converters.jsonl` and
   `results/speed.jsonl`, deduplicated: bench and converter lines by `id_run`, speed lines by
   `(tool, task, run_ts)`. The stores are append-only; never rewrite or reorder them.
3. Every tool spelling in the appended lines needs a `bench.registry.yaml` entry that maps it:
   `run_names` / `bench_vendors` for bench lines, `converter_tools` for converter lines,
   `speed_tools` for speed lines. A versioned lane (`wordcraft-cli-0.7.0`, `docxodus-13.0.0`,
   `pymupdf-pro-1.28.2`) is its own tool id, so it ranks beside the older release instead of
   replacing it. `build()` refuses the whole report on one unmapped name; the one that stopped it
   on 2026-10-14 was `candidates` in `converters.jsonl` (the LibreOffice rows
   `scripts/convert_candidates.py` writes), which maps to `soffice`.
4. `uv run bench report`, then read the headline tables before committing. Commit the stores,
   the registry, the three pages and any `RESULTS_v<old>.md` the run froze (it freezes the page
   on disk when the bench version moved, here 0.7.0 to 0.8.0); leave other sessions' churn
   (`out/`, corpus files) out of the commit.

What the policy does with the rows (full text at the top of `ledger/policy.py`):

- The headline group of a benchmark is the one holding its **newest eligible row**, skipping
  rows on a **subset set**: a document set whose documents (read from the rows' own per-document
  scores) are a strict subset of another set measured for that benchmark. Added 2026-10-15 after
  the PyMuPDF Pro row (unlicensed, first 3 pages, 253 of the cohort's 400 documents, emitted
  0.8 s after the others) made the whole `docx_to_pdf` headline a one-row table on its subset.
  Subset rows stay in History, with the set they are part of named in the "Other document sets"
  pointer. No `docsets.json` entry is needed for this.
- The six `bench run` benchmarks are gated: a tool enters the main page only when its run on the
  docset's **gate set** (`results/docsets.json`, `gate_of`) beats the null baseline. A cohort
  scored outside `bench run` has no gate set and no null-baseline run for its docset, so its
  `script_redlines` rows are listed in `RESULTS_DETAILED.md` under "Not ranked" with
  "no gate set recorded for `<docset>`" and in History, not on the main page. That is where the
  fresh cohort's comparison rows (docset `62d32b1f2954df42`) stand today; the cohort's own
  `REPORT.md` is their publication of record. Putting them on the main page means recording the
  gate set (`bench docset --write`) and running the null baseline on it, under the same Word
  renderer and scorer; it is a benchmark run, not a report fix, and it needs Word.
- The converter benchmarks (`docx_to_pdf` and kin) are not gated; they appear as soon as a
  complete Word-oracle run exists in the current group.

## Speed benchmark

Separate from the fidelity score, `results/speed.jsonl` (append-only, one row per engine
per run) measures **redline-generation time** (`unit: ms_per_redline`). Run it:

```bash
node --import tsx scripts/speed-bench.ts --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl
uv run python -m neurotic_docx_bench.superdoc_speed --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl
# Large-N native CLI (C# Docxodus + jubarte-rust): 1000 fixtures → 5000 pairs, samply profiles
pnpm run redline-speed-bench:native
```

**Render speed** (`unit: ms_per_render`) — how long a Playwright viewer takes to render a
DOCX to PDF — is measured two ways (see `docs/SPEED.md` § Render speed): (1) per-run in
`results/bench.jsonl`, where every `visual_*` line carries `overall_*_speed` stats + a
per-doc `timings` map with `render_s` derived from the `PlaywrightRenderer`'s `duration_ns`
(the same field `soffice` sets — the three `visual_*` benchmarks share one render pass, so
they share its render-speed distribution); (2) standalone with reps/warmup/full percentiles:

```bash
uv run python -m neurotic_docx_bench.playwright_speed --docx-dir corpus/word/tracking_without_comments/docx \
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

The content cache (below) changes what these per-run numbers cover: a render or scored
row restored from `.bench-cache/` carries `cached: true` and no `duration_ns` /
`raster_ns` / `score_ns`, so `render_s`, `raster_s`, `score_s` and the `overall_*_speed`
stats describe only the documents actually rendered and scored in that run. A run meant
to measure speed passes `--no-cache`.

## Content cache (`src/neurotic_docx_bench/content_cache.py`)

`bench run` reuses renders, page rasters and scored rows by content hash from
`.bench-cache/` next to `results/` (git-ignored; `BENCH_CACHE_DIR` moves it,
`BENCH_NO_CACHE=1` or `--no-cache` disables it; `bench cache [--clear]` inspects it).
Keys: candidate sha256, oracle sha256, base sha256 when present, DPI, renderer id
(`hardware.renderer_id`, e.g. `soffice-26.2.4.2`, `word-16.x`) and the scorer fingerprint,
16 hex chars over `score.py`, `score_v2.py`, `page_metrics.py`, `pipeline.py`, `raster.py`,
the MuPDF build (`mupdf-<version>`) and `content_cache.SCHEMA`. Touching any of those
sources changes the fingerprint, so a scorer edit never reads stale rows; bump `SCHEMA`
when the on-disk layout changes. `score_pdf_pair` takes `cache=` and `renderer_id=`; the
run path passes the active cache (`content_cache.active()`) to every `score_folders_*`
call and wraps the renderer in `CachedRenderer`, which restores PDFs by source sha256 and
only invokes the inner renderer for misses. Process-pool workers receive the cache through
the task tuple. A hit still writes the page PNGs under the run's work dir, so galleries and
the residual-ink diagnostics read the same paths as an uncached run. `bench compare` does
not use the cache.

## Profiling (`src/neurotic_docx_bench/profile.py`, `bench profile`)

`bench profile [--run NAME]... [--sample N] [--seed S] [--dpi D] [--json OUT]
[--roundtrip] [--accept-compare]` drives `_drive_runs` with `emit=False`,
`do_gate=False`, `rerun=True`, `no_update=True`, `oracle_check=False`, `canary_check=False`
and the content cache configured off, so
a profile is always one fresh pass and never lands in `results/`. `limit=N` with
`sample_seed=S` makes `_limited_source` take `profile.sample_files` (a
`random.Random(seed)` sample of the sorted file list, returned sorted) instead of the
first N files; the roundtrip stage samples the same way. `_execute_run` fills a
`timings_sink` with each benchmark's per-document stage seconds (the same
`_collect_timings` / `BenchmarkOutcome.timings` dicts that feed the emitted speed
stats), and `_drive_runs` wraps them with the run's wall time and `hardware.renderer_id`.
`profile.summarize` aggregates a benchmark's timings into per-stage `n`, `total_s`,
`mean_s`, `median_s`, `p95_s` (nearest rank), `max_s` and `share` (stage total over the
sum of stage totals); `build_report` adds `sample`, `seed`, `dpi`, the scorer fingerprint
and raster engine; `render_tables` prints one 80-column table per run. Passthrough runs
time raster and score only (no render duration), generated runs add `generate`.

## Scorer kernels (`src/neurotic_docx_bench/kernels.py`, `--device`)

`score.py` calls `kernels.delta_e_mean` (mean CIEDE2000 over the ink mask) and
`kernels.ssim` instead of skimage directly. Each has two implementations: the
skimage/scipy path (`*_numpy`, the parity-locked default, byte-identical to the old
scorer) and a torch port (`rgb2lab_torch`, `ciede2000_torch`, `delta_e_mean_torch`,
`ssim_torch`; skimage's constants, float32, `avg_pool2d` for SSIM's 7x7 uniform window
with sample covariance over the valid interior). Dispatch reads `BENCH_DEVICE`:
`resolve_device` maps `auto` to cuda, then mps, else `None` (silent), and `cpu|mps|cuda`
to that device or `None` with one `RuntimeWarning` when torch or the device is missing;
the result is cached per spec (`kernels.reset()` clears it). `kernels.device_env(spec)`
is the CLI wrapper: it validates the spec, exports `BENCH_DEVICE` around `_drive_runs`
(or `score_folders_full` for `compare`) so pool workers inherit it, and restores the
previous value; `pipeline._run_tasks` installs `kernels.worker_init(jobs)` as the pool
initializer, which on a torch device gives each worker `cpu_count // jobs` intra-op
threads so `jobs` workers do not oversubscribe the cores (torch's default is one thread
pool per process; `BENCH_TORCH_THREADS` overrides the count). The device is deliberately
not part of `ScoreConfig` or
`result["config"]`; `kernels.backend_id()` (`numpy`, `torch-<device>`) goes into the
content-cache score key, `hardware_info()["scorer_backend"]` and the profile report's
`scorer_backend`. `kernels.py` is in the scorer fingerprint. `tests/test_kernels.py`
checks the torch port against skimage (elementwise Lab and deltaE at 2e-3, page deltaE at
1e-3, SSIM at 1e-4, `score_document` at 1e-3 on synthetic pages and 1e-2 overall on
two real oracle pages) and skips when torch is not installed.

## Regenerating the Word oracle PDFs (macOS + Word, local-only)

Word's PDFs of the corpus live beside their docx in `corpus/word/<state>/pdf`. To render a set
again (or a sanity copy of it), stage the docx a pool names into a working folder and drive Word
with `scripts/word_pdf.py`, which runs the whole folder in one AppleScript (one permission prompt),
skips `~$` lock files and resumes a wedged pass:

```bash
# 1. Manually export one PDF in Word GUI choosing "Best for printing" (sets the sticky pref).
# 2. Stage the documents and render them (foreground, so the permission dialog is visible):
uv run bench corpus stage corpus/word/pools/word_based_renders.csv work/word_based
uv run scripts/word_pdf.py --src work/word_based/docx --out work/word_based/pdf_again
```

**Permission-prompt trap:** macOS shows one AppleScript permission dialog per `osascript`
process. `WordRenderer.to_pdfs()` (`src/neurotic_docx_bench/render/word.py`) calls `osascript`
**once per file**, so 232 DOCX files = 232 prompts. Never use it for a full batch.

**Which driver (2026-10-14):** `scripts/word_pdf.py` is the one to run, and `scripts/word_redline.py`
imports its machinery (and `scripts/word_ab.py` A/Bs it; see the Gotchas for the recovery policy,
`_byword` names, `manifest.jsonl`, the 80/35-character trims and the one-driver rule). Its watchdog reads every Word alert's buttons *and text* in one osascript
per poll, recognises the repair prompt from the text (or its Yes/No pair), and answers it with a
second script that brings Word forward, presses No, waits for the "Word experienced an error
trying to open the file" OK, presses it and hands focus back. Every alert Word shows is logged
with its words (`[watchdog] ... Word said: "..."`), and the batch progress tailer brings Word
forward to check on an item not finished after 10 s. `--no-focus` turns the focus-taking off
(background-only presses, the pre-2026-10-14 behaviour, where the OK after a No never appears
and each broken file costs the 240 s AppleEvent timeout plus a batch pass). Verified live on
2026-10-14 against `really_broken/tool_redlines/repair_prompt` fixtures: no timeouts, right
verdicts (`out/smoke1014/driver.log` has the run). `scripts/word_pdf_focus.py` is superseded by
this and must not be used for new runs; it stays only as the record of the 2026-09-30 trial.
The spec is `tests/test_word_pdf_alerts.py` (plus `tests/test_word_pdf.py`).

**Seeing what Word says, independently:** run `scripts/word_screen_log.py <log>` beside a batch.
It reads CoreGraphics' window list every 0.25 s and logs each Word alert's text, which macOS
Vision reads from a screenshot. It never polls System Events, because the driver's watchdog
depends on it. Since 2026-10-14 the driver logs the alert text itself, so this is the second,
independent record (it also sees alerts the driver missed, and macOS permission prompts).
See the note in the script.

**"Best for printing" export quality:** Word's AppleScript `save as` does not expose the
"Optimize for: Best for printing / Best for online viewing" radio button. The setting is
**sticky**: Word reuses whatever you last chose in the GUI Export dialog, so set it once by hand
(File → Export... → PDF → **"Best for printing"**) before a batch.

**Rules to avoid the permission-prompt nightmare:**
1. **One `osascript` call, all files inside.** Never loop `osascript` per-file.
2. **Run in foreground** (`osascript ...` directly, not backgrounded). Background mode
   buries the permission dialog where you can't see/click it.
3. **Use inline/heredoc AppleScript**, not `.scpt` files. Compiled `.scpt` triggers
   `-1708` errors on `save as`.
4. **Delete `~$` temp files first** — Word lock files cause spurious failures.
5. Some files intermittently fail `save as` with `-1708` ("active document doesn't
   understand the 'save as' message"). Retry just those individually with a `delay 2`
   after `open`.

## Everything else on the hub: `bench hub list|get` (2026-10-26, #79)

The corpus is one of fifteen download presets. The 0929 run's tool outputs, Word's fresh compares,
the 0.13.0 release evidence, the R2 cohort mirrors, the website's R2 objects, the results
dataset's parquet tables and the private git-history archive also live only on the hub. Each has
a named preset:

```bash
uv run bench hub list --sizes                            # every preset: hub path → local destination, files, bytes
uv run bench hub get corpus-word                         # corpus/word (docx, Word PDFs, compares, tables)
uv run bench hub get redlines-0929 --include 'jubarte-0.14.0/docx/*' --dry-run
uv run bench hub get wordcraft-20261014                  # → hub-downloads/r2-mirror/wordcraft-20261014
uv run bench hub get git-archive --include '*.txt'       # private; needs HF_TOKEN or `hf auth login`
uv run bench hub get --repo arthrod/neurotic_docx_bench --path outputs/release_0.13.0_evidence --dest x
```

- **Pinned.** `--revision` (default `main`) is resolved to a commit once, and every listing and
  download reads that commit (a branch read can serve a stale cache, as #76 found with
  `hf_hub_download`).
- **Verified.** Every file is hashed against the hub's own record at that commit: LFS `sha256`, or
  the git blob sha1 for inline files. One mismatch refuses the run, and nothing moves into the
  destination.
- **No clobbering.** A local file with the same bytes is skipped. One with different bytes stops
  the run before anything downloads, unless you pass `--overwrite` or `--keep-local`.
  `--overwrite` replaces only regular files: a local symlink whose bytes differ refuses the run (one
  with the hub's bytes is skipped like any matching file, and nothing is written through it).
  `redlines-0929` lands in `results/redlines_0929_full`, whose scripts and CSVs are tracked, so this
  rule is what protects them. A symlinked folder below the destination refuses the run too, since it
  would put files, or move replaced ones, outside the destination (the destination itself may be a
  symlink), and so does a folder below it on another disk (a mount), where a rollback could not take
  files back; the folders are looked at again before each file moves. So does a destination that is
  or holds the staging folder.
- Files stage in `files/` of `.<dest>.hub-<sha12>/` beside the destination, or of
  `<dest>/.hub-<sha12>/` when the destination is a mount or a link to another disk; the lock, the
  `.replaced/` backups and `.scratch/` sit beside `files/`, where no hub path can land. The folder is
  locked for the run, and a symlink in it refuses the run; a staged file with a second name (a hard link) is
  fetched again, never written into. Files move in all or nothing: each is placed as a hard link to
  its staged copy (on a disk without hard links, a copy made in the staging folder's `.scratch/` that
  takes its name with a rename refusing an existing file, `renamex_np(RENAME_EXCL)` on macOS and
  `renameat2(RENAME_NOREPLACE)` on Linux, so a kill never leaves a part-written or empty file; a disk
  with neither refuses before any download), so a file written meanwhile is never overwritten, and
  the staged copies go only after the last file is in place. A
  failed or interrupted (Ctrl-C) move withdraws every file already placed and restores every file
  `--overwrite` replaced (a rename or link the disk reports failed is checked by identity first, since NFS
  may report one it made as failed), except a file someone else changed after the run placed it, which stays;
  the error names it and where the file it replaced is kept, and a later run refuses to overwrite
  that kept file. On success the run removes only what it staged; on failure the folder is kept for
  a resumable rerun. A rerun names what an earlier run left in the staging folder (replaced files in
  `.replaced/`, files it took back in `.withdrawn-*/`; a run with nothing to download too), and
  takes the second name off staged files a killed move left linked into the destination. Ctrl-C
  never splits a step: during the moves it is held until the step in hand is recorded (a second
  press waits too); one during the rollback lets it finish, a second stops it before its next step
  and names the files not put back. Ctrl-C during the download drops the queued downloads and keeps
  the staging folder. The CLI prints what was left where and exits 130. Ctrl-C is held only under Python's own handler, so a caller that ignores or
  handles it keeps that. Presets with no home in the checkout land in `hub-downloads/`. All three
  are git-ignored.
- `--include` globs are fnmatch patterns relative to the preset's folder: `*` also crosses `/`, so
  `--include '*.docx'` takes the `.docx` files of every subfolder too.
- `bench fixtures download` (whole fixtures repo, checked against `MANIFEST.sha256.json`) and
  `scripts/fetch_corpus.py` still work. The `compare-regen` preset downloads Word's fresh compares but
  not `results/compare_regen/regen_list.csv`, which `bench jubarte-release` reads at its measure step,
  after the Word export: set that lane up with `scripts/fetch_corpus.py`, which writes both.
- Adding a preset is one entry in `hub_get.PRESETS` (`src/neurotic_docx_bench/hub_get.py`).

## Remote tryout (`bench try remote`, `tryout_remote.py`, `jubarte_release.py`)

Scores one tool on random documents from the Hugging Face dataset `superdoc-dev/docx-corpus`
(one parquet index; every row a `url` to the docx). The docx-corpus bytes are the bytes
`corpus/word` holds, so the SOT is looked up by sha256: Word's PDF (`documents.csv`) for
`convert`, Word's compare (`comparisons.csv`) for `redline`. Without it the fallback SOT is
docxodus (redline), soffice (DOCX->PDF) and pdftoppm (PDF->PNG, of the `convert` SOT PDF).
`--with-sot` picks only documents or pairs we hold Word SOT for (about 1.5k documents,
1.4k pairs); a plain random pick almost never has it.

```bash
uv run bench try remote --tool jubarte --version 0.10.0 --seed 5 --with-sot --jsonl runs/try_remote.jsonl
uv run bench try remote --tool pymupdf                     # png only: a tool runs the tasks it can
uv run bench try remote --tool "mytool {input} {out}"      # a template; its placeholders name its task
```

- `--tool` is a known name (`KNOWN_TASKS`: jubarte, docxodus, soffice, pdftoppm, mutool,
  pymupdf) or a template: `{base} {next} {out}` redline, `{input} {out}` convert,
  `{pdf}`/`{input}` + `{outdir}` (+ `{dpi}`) png. `--task` narrows; asking for a task the
  tool cannot run is refused. A tool that is a task's fallback SOT is skipped, not scored
  against itself (a skip exits 0, an error exits 1).
- `--version` is jubarte only: local first (`BENCH_JUBARTE`, `PATH`, `~/.cargo/bin`, the
  cache, the vendored copy, `../speed_bins/jubarte-*`; never a `target/` dev build), else
  the GitHub release asset of `jandira-tech/jubarte-redlines` checked against its
  `SHA256SUMS.txt`, else `cargo install jubarte-redlines --version X`, else it fails. No
  version = the latest GitHub release. Downloads go to `BENCH_JUBARTE_CACHE`
  (`~/.cache/neurotic-docx-bench/jubarte`).
- Both redlines go through `--renderer` (soffice by default). A stored `corpus/libreoffice`
  render of Word's compare stands in only when `word_map.csv` says the installed soffice
  build made it; otherwise Word's compare is rendered again.
- Nothing is written under `results/` unless `--jsonl`/`--json` says so; rasters and
  downloads live in temporary folders deleted on return.

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
- EXCEPT IF REQUESTED BY THE PERSON OR REQUIRED BY A SPECIFIC BENCHMARK OR TO DEVELOP A TOOL, YOU MUST RECORD THE RESULTS WITH RASTERS DELETED AFTER EACH TOOL SO SCORING DOESN'T FILL THE DISK.
- **The agent shell is zsh: it does not word-split unquoted variables.** `M="--manifest x --source-dir y"; node gen.ts $M`
  passes ONE argument; `generate-native-redlines.ts` then ignores it and runs its default manifest (207
  word_based pairs) with exit 0, while `superdoc_gen` rejects it. Write the flags out, use an array
  (`M=(--manifest x --source-dir y)`) or `${=M}`, and check the output count against the manifest.
- **Every retried file goes to the back of the next batch pass** in `scripts/word_pdf.py`: one
  that crashes Word ("Connection is invalid"), one that loads empty (a declined repair prompt), and
  the one a wedged pass stopped on. A `[retry]` file fails for good after two such passes, and a
  pass that logged a `[retry]` does not spend the 3-pass stall budget. Before this, one bad file (or
  three Word-invalid files in a row) led every pass and the rest of the folder was reported "never
  reached". Word's AppleEvent timeout is `APPLE_EVENT_TIMEOUT` = 240 s (was 600).
- **The repair prompt is answered No, then its OK, with Word brought forward** (`word_pdf.py`,
  2026-10-14). Before that the text-matched handler never compiled (its `UI elements` sat outside a
  `tell` block), the generic fallback pressed No after ~6 s and three osascripts, and the OK Word
  raises after the No does not exist for System Events while Word is in the background, so every
  broken file ran out the 240 s timeout and spent a pass. Every AppleScript term must sit inside a
  `tell application "System Events"` block, handlers included, and `st` is a reserved word; compile
  a new script with `osacompile` before trusting it.
- **A declined repair prompt is the file's fault, not Word's** (2026-10-14, later the same day). The
  watchdog appends `[declined]<tab><staged file>` to the batch log when it answers the prompt; the
  batch script reads that back when the open comes up empty and logs a final `[fail]` instead of
  `[retry]`, so a declined file no longer ends the pass, costs a Word restart, or gets a second try.
  Empty loads *without* a decline still count toward the three-in-a-row poison rule. `--crash-limit`
  (default 2) is how many passes a file that crashes Word gets; pass 1 for a corpus you already know
  crashes it. Since the afternoon of 2026-10-14 a pass costs a crash and a close-all, not a restart. Measured: 3 broken + 2 good files went from 3 m 41 s and
  one restart to 18 s and none.
- **The export scripts find the opened document by exclusion, like the compare script**, never
  `document 1`. Seen live 2026-10-14: a document that survived `close every document saving no`
  (a base left open by an aborted `word_redline.py --do-not-close` run) was saved as a broken file's
  PDF once that file's own open produced nothing. Now that case is `[fail] open produced 0 new
  documents; refusing to guess`. The corollary: **start a batch on a Word with zero documents open.**
  `preflight` logs `open_documents=N started_clean=False` and proceeds (the default closes them),
  but a document Word will not close, or one restored from AutoRecovery after a crash, poisons every
  later open by name collision. Since the afternoon of 2026-10-14 the driver closes everything
  itself and restarts a Word that returns nothing (next bullets); quitting Word by hand is no longer
  a precondition.
- **Recovery is close-all first, and nothing is "ours" or "theirs"** (2026-10-14, afternoon). When a
  pass ends on `Connection is invalid` or Word stops answering, `WordSession.recycle` tells the
  running Word `close every document saving no` and carries on with the same Word the moment it
  answers (measured: 0.2 to 1.2 s). Only when that close-all returns an error, or Word stays silent
  for `answer_grace` seconds after it, does it escalate: `quit saving no`, then `pkill -x`, then
  `pkill -9`, then a background relaunch; the log says which and why ("because unresponsive for
  15 s after the close-all"). Whoever launched Word and whatever it held at startup makes no
  difference under the default policy; `--do-not-close` is the one mode that closes by name, and
  it refuses to restart a Word holding documents. Word open with no document, or with a blank
  `Document1`, is normal and never a reason to refuse or restart. A crashed Word relaunches itself
  within seconds; the driver finds it running and goes straight to the close-all. The one case that
  restarts without a close-all: a pass that ended because Word **answered and returned nothing**
  three times in a row (`open produced 0 new documents`, `loaded empty`, "doesn't understand").
  A close-all on an empty Word succeeds and fixes nothing, so the driver brings Word forward once
  to look for a modal System Events cannot see from the background, then quits and relaunches it
  (`recycle(restart=True)`, logged "because Word returned nothing for N document(s) in a row").
  `preflight` runs the close-all as a health check and recycles a Word that errors on it.
- **Every command the driver runs is in the log, and its result is the next line**: `running:
  osascript -e '…'` / `pkill -x 'Microsoft Word'` / `open -g -a …`, then `returned rc=0 in 0.2 s,
  no value came back (AppleScript 'missing value')` (that is what osascript prints when a `close`
  has nothing to return; it is not an error), `got: …`, or `error: …`. `preflight` logs
  `word_pid=`; a pid that changes between runs means something else restarted Word. The on-screen
  log prints these lines verbatim and in colour (`make_console_sink`): the previous sink let rich
  read `[word]`, `[batch]`, `[ok]` as markup and `:recycle:` as an emoji, so the screen said
  `recovery 1:` while the file log said `[word] recovery 1:`.
- **One driver at a time, and that includes frozen copies.** `WordLock` (an flock on
  `~/Library/Containers/com.microsoft.Word/Data/word_driver.lock`) serialises `word_pdf.py` and
  `word_redline.py`; a second driver waits `--lock-wait` seconds and then reports `WordBusy`. The
  copies under `results/*/drivers_<sha>/` predate the lock and take it from nobody: on 2026-10-14
  from 22:21 UTC one of them (`drivers_ee49054d/word_pdf.py`, rendering docxodus 13.0.0 for
  `finish_new.py`) ran beside an A/B batch. Its pending repair prompt, invisible to System Events
  while Word sat in the background, made every `open` of the other driver return nothing: 70
  documents "failed" in 5 s, twice, and Word's pid changed under the other run. A pipeline that
  needs Word must call `scripts/word_pdf.py` (or import it), never a frozen copy, and never while
  another batch is running.
- **Everything Word writes is named `<stem>_byword.<ext>`** (`by_tool`; `_bysoffice`,
  `_bydocxide`, `_bywordcraft`, `_byjubarte` for the others), and **every run appends
  `manifest.jsonl`** in the output folder: one JSON line per file produced (`original_filename`,
  `path_origin`, `converted_filename`, `path_out`, `status` ok|failed|skipped|renamed, `kind`
  pdf|accept_all|reject_all|redline|rename, `tool`, `error`, `seconds`, `run_at`; redline lines add
  `revision_filename`, `path_revision`, `revisions`, `unmatched`). A failure is a line with empty
  `converted_filename`/`path_out`. Outputs that exist under the pre-suffix spelling (`<stem>.pdf`)
  are skipped, not redone, and the manifest records the file that was found
  (`existing_output`). Consumers read `neurotic_docx_bench.word_outputs.find_output` (manifest
  first, then `_byword`, then the old name).
- **Input file names are trimmed on disk before Word sees them**: over 80 characters for
  `word_pdf.py`, over 35 for `word_redline.py` (a redline is named after both sides, so
  `<a>__vs__<b>_byword.docx` stays under 80). `trim_name` keeps the extension and appends 8 hex of
  sha1(original) so two long names never collide; the rename is logged and recorded in the manifest
  as `status: renamed`. A long-named docx that was already rendered under its long name is rendered
  again under the trimmed one (the 2026-10-14 corpus run redid 332 of 1329 for this reason, once).
- **A stall report is dropped when the item finished while the probes ran.** The System Events
  probes take up to 10 s each while Word is busy exporting; by the time they returned on
  2026-10-14 the "stuck" item and 29 more were done. `_Progress._report` re-reads the batch log
  after probing and logs one line (`item 1/1329 finished while I was looking (30 done now …);
  nothing is stuck, report dropped`) instead of a stale diagnosis. A nameless alert button is logged
  as exactly that (`shows a button with no name (AppleScript 'missing value')`), never skipped.
- **Redlining moves every pair that shares a file with a crashed pair to the back** of the next
  pass (`[defer]`), not only the crashed pair, so one broken document does not re-crash Word once
  per pair it appears in.
- **The next batch with a bunch of Word-crashing fixtures is an A/B, not a rerun.** Stop, take 20
  of them, and run `scripts/word_ab.py` (`stage`, `run --set broken`, `report`): it replays the same
  20 under the driver variants it defines (every one pinned to the pre-A/B driver except for the
  knob it tests; `current` is the driver as it ships) and times each on detect / recover / resume
  per crash plus wall time and lost outputs. Pick the fastest variant that loses no more documents
  than any other, then run it against `baseline` on the 50 random good fixtures (`--set good`,
  `mixed` for all 70) before making it the default. `report --drop STARTED_AT=reason` leaves a run
  out on the record. Results: `out/ab/results.jsonl`, `out/ab/AB_REPORT.md`.
- **What the 2026-10-14 A/B found** (20 corpus documents that crash Word, 18 variants, two
  `baseline` controls at 346 s and 382 s): recovery is not the cost. Close-all-first recovers in
  0.4 to 0.7 s and the next pass starts 0.05 s later; `quit_first` took 2.8 s per crash. The cost
  is detection: Microsoft Error Reporting shows up a median 4 to 5 s before the batch osascript
  gets `Connection is invalid`. So the watchdog now treats the reporter as the crash signal
  (`--crash-signal`, default on): on seeing it, it ends that pass's osascript (found by its
  manifest path, never a blanket `pkill osascript`) and marks the item Word was on `[retry]`
  (`merp_kill`: 251 s, detect median 2.4 s). A true crasher crashed Word again on every retry (of
  21 in the 14:13 corpus run, 20 twice and the last failed anyway), so `--crash-limit 1` is right
  for a corpus you know crashes Word (`merp_kill_crash1`: **111 s** against 382 s on the 20).
  The default stays 2, because the retry is what rescues a document the signal attributed wrongly
  or a Word that was returning nothing: before the signal's two races were fixed (the script's own
  `[retry]` already written, so the "first item without a line" was the next, good, document; and
  the reporter of the previous crash surfacing after the next pass began, now detected by its
  process age), `merp_kill_crash1` on the mixed 70 lost 3 good documents more than the control
  (45 ok against 48, 241 s against 336 s). On the 50 good fixtures it rendered all 50 in 57 s
  against 65 s. The mixed-set number for the fixed signal with crash limit 2 is still to be
  measured when Word is free (`word_ab.py run --set mixed --variant current`). Dead ends, measured:
  `defaults write com.microsoft.errorreporting SendReportAutomatically/QuitAfterGeneratingReport`
  (keys from the 16.115 binary) do not suppress the reporter dialog, 35 of 39 crashes still showed
  it; `open … repair false`, read-only open, 1 s polling, 5 s grace, 0.25 s watchdog poll and
  60 s AppleEvent timeout changed nothing beyond the noise band (267 to 463 s for 39 crashes);
  serial mode (one osascript per document) was the slowest at 488 s. The control's own two
  good-document losses on the mixed set were the intermittent `-1708 save as` error.
- **soffice render** requires exit 0 **and** the output file, and deletes a stale PDF before
  a forced re-render (parity with the original shell script).

## Provenance

Scoring core: superdoc-visual-benchmarks. Tools: jubarte (in-repo), JSv4/docxodus,
JSv4/react-docxodus-viewer, AnsonLai/docx-redline-js, stella/folio, SuperDoc +
yuch85/superdoc-redlines, houfu/redlines, balalofernandez/docx-revisions. See README for
links + licenses.
