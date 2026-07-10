# PLAN — `neurotic-docx-bench`

> **Status: design only. Nothing here is implemented yet.** This document is the
> agreed blueprint for the standalone, run-now-and-then benchmark repo that
> compares DOCX tools against a Microsoft Word ground truth. Approve it (or edit
> it) before any code is written.

## 1. Vision

One repo, one Typer CLI, driven by **`bench.yaml`**. It runs **several tool-runs
sequentially** (jubarte-native, docxodus, SuperDoc, CasualOffice, …), each
optionally **updating its package to latest first**, renders the modified DOCX →
PDF (LibreOffice/`soffice` by default, Playwright for web editors), rasters and
scores every page against a **committed** Word ground truth, and appends **one
comprehensive JSONL line per tool** — but only when the result changed. It ships
with a Dockerfile + docker-compose so the whole thing runs the same on a laptop
and in CI.

The scoring core (`score.py`, `diff.py`, `raster.py`) is lifted verbatim from
`_fixtures/compare` and stays byte-identical so numbers remain comparable across
this repo and the in-tree harness.

## 2. What already exists in this directory

- `pyproject.toml` — `docx_neurotic_bench`, `requires-python >=3.14`, `uv`.
- `docx_neurotic_bench/` — a nested JS/TS redline generator (CasualOffice +
  SuperDoc, native engines, batch from a CSV manifest, `docx-to-pdf.sh`). This
  is a **tool** the Python bench will drive, not the bench itself.

The Python bench described below lives at the repo root alongside `pyproject.toml`.

## 3. Repo layout (target)

```
neurotic-docx-bench/
  pyproject.toml                # uv; typer, pymupdf, numpy, scikit-image,
                                #   playwright, pyyaml, docx_revisions
  bench.yaml                    # (a) sequential runs; per-tool modified sources
  Dockerfile                    # (i) soffice + python + node + playwright/chromium
  docker-compose.yml            # (i) `bench run` service, mounts corpus + results
  src/neurotic_docx_bench/
    cli.py                      # Typer app (run / compare / accept / reject / render)
    config.py                   # parse + validate bench.yaml
    packages.py                 # (h) update tool packages to latest, resolve versions
    render/
      base.py                   # Renderer protocol
      soffice.py                # (3) Python port of docx-to-pdf.sh — DEFAULT
      playwright.py             # (1) web-editor render via harness profiles
      word.py                   # (f) AppleScript; local-only, never in CI
      passthrough.py            # (2) folder-of-PDFs, skip render
    raster.py  score.py  diff.py                 # lifted verbatim from _fixtures/compare
    report.py  html_report.py                    # lifted (relative-import fix only)
    aggregate.py                # medians / averages / distribution
    accept_changes.py           # (c) wraps docx_revisions.RevisionDocument
    gate.py                     # (e) pass / fail / warn logic
    emit/
      jsonl.py                  # (b)(j) one comprehensive line per tool, append-on-change
      snapshot.py               # score-snapshots/{name}.json (tab-indented)
      markdown.py  html.py      # human reports
  corpus/
    word_based/                   # Word ground-truth corpus (2016 files total)
      docx_source/                # (d)(f) committed source DOCX — the raw inputs (201 files)
                                  #   names: {document_name}.docx (normalized: underscores only)
      pdf_redlines_word/          # (d)(f) committed Word redline PDFs — the oracle (329 files)
                                  #   includes both source-PDFs and {a}_{b}_redline.pdf pairs
      docx_redlines_word/         # (d)(f) committed Word DOCX redlines — the oracle (337 files)
                                  #   {a}_{b}_redline.docx (gdocs-style) + {a}_{b}_word_redline.docx (word-style)
      pdf_accepted_word/          # (d)(f) committed "accept all changes" PDFs (166 files)
                                  #   {a}_{b}_word_redline_accepted.pdf
      docx_accepted_word/         # (d)(f) committed "accept all changes" DOCX (166 files)
                                  #   {a}_{b}_word_redline_accepted.docx
    other_tools/                  # (8) input DOCX to run tools against (optional, committed)
  results/
    bench.jsonl                 # (b)(j) append-only trend log, committed
    score-snapshots/            # per-tool accepted baselines, committed
  runs/                         # (NEW) generated per-run work folders — see §4
  .github/workflows/bench.yml   # (8) scheduled CI
```

### 3.1 Corpus naming conventions

All filenames in `corpus/word_based/` follow a single normalized scheme:

- **Stem:** `[a-zA-Z0-9_]` only — every hyphen, dot, space, or symbol in the
  original name was replaced with `_`.  Multiple consecutive separators
  collapse to a single `_`; leading/trailing `_` stripped.
- **Extension:** lowercase, preserved (`.docx`, `.pdf`).
- **Source folder** (`docx_source/`): the former `_docx` / `_pdf` pseudo-extension
  suffix became the real extension, e.g. `foo_bar_docx` → `foo_bar.docx`.
- **Accepted folders** (`pdf_accepted_word/`, `docx_accepted_word/`): every file
  carries an `_accepted` marker before the extension, e.g.
  `foo_bar_word_redline_accepted.docx`.
- **Duplicates:** byte-identical files within a folder were removed (5 dups in
  `docx_source`); no cross-folder PDF duplicates were found.

## 4. Generated-folder policy (NEW requirement)

Every run produces heavy intermediate folders (generated candidate DOCX, its
rendered PDFs, per-page PNGs, per-doc score JSON). These are **work products**,
not deliverables.

- **Naming:** each run's folder is `runs/{modified_name_source}_{datetime_for_humans}`,
  e.g. `runs/jubarte-native_2026-07-05_14-32`, `runs/docxodus_2026-07-05_14-40`.
  `modified_name_source` is the run's `name` from `bench.yaml`;
  `datetime_for_humans` is `YYYY-MM-DD_HH-MM` — same convention as `_fixtures`.
- **Local repo (default): KEEP them.** A developer running the bench by hand
  wants to open the PDFs and diffs afterward. `runs/` is git-ignored so they
  never get committed, but they are **not** deleted.
- **CI/CD: AUTO-CLEAN them.** CI runs with `--clean-runs` (or `BENCH_CLEAN_RUNS=1`),
  which deletes each `runs/{...}` folder after its JSONL line + snapshot are
  emitted. CI only ever commits the durable outputs: `results/bench.jsonl`,
  `results/score-snapshots/*`, and (if regenerated) `corpus/word_based`.
- The committed ground truth and the trend log are the only things that persist
  across CI runs; the pixel intermediates are reproducible and disposable.

## 5. `bench.yaml` — sequential multi-tool config (a)

```yaml
source_of_truth: corpus/word_based/pdf_redlines_word   # committed oracle redline PDFs
scoring: { dpi: 144 }

runs:                                          # executed IN ORDER, one per tool
  - name: jubarte-native
    package: "jubarte@latest"                  # (h) npm i @latest before run
    generate: "node scripts/generate-native-redlines.ts --method=jubarte --out=$RUN_DIR/docx --run-dir=$RUN_DIR"
    render: soffice                            # (3) default
    jobs: 8

  - name: docxodus
    package: "jubarte@latest"
    generate: "node scripts/generate-native-redlines.ts --method=docxodus --out=$RUN_DIR/docx --run-dir=$RUN_DIR"
    render: soffice

  - name: superdoc
    package: "@harbour-enterprises/superdoc@latest"   # (h)
    generate: "node --import tsx prosemirror-fresh-redline-batch.ts --editor superdoc --out-dir $RUN_DIR/docx"
    render: playwright                          # (1) render in the real editor
    harness:
      url: "http://127.0.0.1:5173/harness/"
      file_input: "#fileInput"
      page_selector: ".superdoc-page"
      readiness_js: "window.__superdocReady && window.__superdocLayoutStable && window.__superdocFontsReady"
      hide: [".comments-layer"]

  - name: casualoffice
    generate: "node --import tsx prosemirror-fresh-redline-batch.ts --editor casualoffice --out-dir $RUN_DIR/docx"
    render: soffice

  - name: some-prebaked-tool
    render: passthrough                         # (2) already-rendered PDFs
    modified: /abs/path/to/that/tools/pdf
```

Rules:
- Runs execute sequentially; one run's failure is recorded and the next still runs.
- `$RUN_DIR` = `runs/{name}_{datetime_for_humans}` (see §4), created per run.
- `generate` is optional — omit it (with `render: passthrough`, or `modified:`
  pointing at a DOCX folder) when you just want to score pre-made files (item 8:
  "dump a bunch of docx into folders").
- `render` picks the backend; `passthrough` skips rendering entirely.

## 6. Requirement map (original 1–8 + refinements a–j)

| # | Requirement | Design |
|---|---|---|
| 1 | Unify capabilities; Playwright for other tools | Typer CLI; `Renderer` protocol; Playwright backend is **selector-driven via a `harness` profile** so any web editor is a config block, not new code. |
| 2 | Point to folders with PDFs | `passthrough` backend — raster + score existing PDFs, no render. |
| 3 | Migrate soffice docx→pdf to Python | `render/soffice.py` — Python port of `docx-to-pdf.sh` (per-worker `-env:UserInstallation` profiles, `ThreadPoolExecutor`, skip/force). **Default.** |
| 6 | JSONL by default | `emit/jsonl.py` writes `results/bench.jsonl`. |
| 7 | "Accept all changes" util | `accept_changes.py`, see (c). |
| 8 | Point to DOCX folders; soffice default; CI vs source of truth | `bench.yaml` `docx`/`generate` → render → score vs committed truth; `.github/workflows/bench.yml`. |
| a | `bench.yaml`, sequential runs, different modified sources | §5. |
| b | JSONL = **one comprehensive line per tool** | §7. Not per-doc; the single line embeds the per-doc score map so per-doc warnings + change detection still work. |
| c | Accept tracked changes — **use the provided snippet** | `accept_changes.py` wraps `docx_revisions.RevisionDocument`: `accept_all(path) → rdoc.accept_all()`, plus `reject_all`, `find_and_replace_tracked`, `apply_tracked_changes`, `_enable_markup_view`. CLI: `bench accept <folder> --out <folder>` / `bench reject ...`. **Not** the earlier pure-lxml idea. |
| d | Commit ground truth | `corpus/word_based/` is committed (5 sub-folders, see §3). |
| e | Pass/fail gating | §8. |
| f | Word stays in-script, CI uses pre-generated | `render/word.py` present for local ground-truth regen; CI never calls it, scores against committed PDFs. |
| g | Cross-renderer not comparable, but keep measuring | Every JSONL line records `render`/backend + `baseline_ref`; trend views only compare within the same `(backend, baseline)`. Still measured + stored. |
| h | Always try to update packages to latest | `packages.py` runs before each run that has a `package:` — `npm i <pkg>@latest` (or pull+build local) — and **records the resolved version** into the line. `--no-update` pins. Bench's own Python deps: `uv lock --upgrade` step too. |
| i | Dockerfile + docker-compose | Named deliverable; §3. `Dockerfile` bundles soffice + python(3.14/uv) + node + playwright chromium; `docker-compose.yml` mounts `corpus/` + `results/` and runs `bench run --clean-runs`. |
| j | JSONL appended after each run only if there are changes | §7 change-detection. |
| NEW | Generated folders auto-cleaned in CI, kept locally; `{modified_name_source}_{datetime_for_humans}` naming | §4. |

## 7. JSONL schema — one comprehensive line per tool, append-on-change (b + j)

One line summarizes an entire tool-run over the whole corpus:

```json
{
  "schema": 1,
  "run_id": "2026-07-05_14-32",
  "run_ts": "2026-07-05T14:32:11Z",
  "git_sha": "…",
  "tool": "docxodus",
  "tool_version": "1.6.2",
  "render": "soffice",
  "baseline_ref": "corpus/word_based/pdf_redlines_word@<sha>",
  "n_docs": 164,
  "aggregate": {
    "overall_mean": 76.70, "overall_median": 76.69,
    "page_mean": 78.1, "page_median": 79.0,
    "exact_100": 3, "at_least_90": 41, "below_50": 12,
    "min": 22.4, "max": 100.0, "std": 14.8, "q1": 66.0, "q3": 88.0
  },
  "scores": { "<doc_stem>": 76.69, "…": 0 },
  "config_hash": "…"
}
```

- **(b) one line per tool** — the `scores` map is embedded (not separate rows) so
  the line is self-contained yet supports per-doc gating.
- **(j) append-on-change** — before writing, compare `scores` + `aggregate`
  (rounded) to the **last line for this `tool`** in `bench.jsonl`. Append only if
  changed; otherwise log a "no change, skipped" line to stdout and write nothing.
  This keeps the trend log a record of *deltas*, not of every identical re-run.

## 8. Gate logic (e) — `gate.py`

- **100% is always a pass.** Any doc (or whole tool) at 100 is never flagged.
- **Per-document decrease** vs the last accepted baseline → **WARNING only**
  (names the regressed docs; does **not** fail the build).
- **Aggregate decrease** (overall_mean or overall_median down vs the tool's
  accepted snapshot) → **FAIL** — non-zero exit, CI goes red.
- Baseline = `results/score-snapshots/{tool}.json` (the last accepted run).
  `bench accept-scores <tool>` promotes the latest run to the new baseline.
- Rationale (Arthur's wording): "a 100% is always a pass, and compare decrease is
  also fail (but on the aggregate only, with a warning when specific decrease)."

## 9. Package auto-update (h) — `packages.py`

Before each run that declares `package:`:
1. `npm i <pkg>@latest` in the tool's workspace (or `git pull && build` for a
   local checkout).
2. Resolve the concrete installed version and stamp it into the JSONL line's
   `tool_version`.
3. `--no-update` / `BENCH_NO_UPDATE=1` pins to whatever's installed.

Because CI always updates, a red build can be caused by an **upstream release**,
not by this repo — the `tool_version` field makes that diagnosable at a glance.
The bench's own Python deps get `uv lock --upgrade` on the same schedule.

## 10. Accept-tracked-changes util (c) — `accept_changes.py`

Steals the provided `docx_revisions` / `RevisionDocument` snippet verbatim:
- `accept_all(doc_path) -> RevisionDocument` — opens, calls `rdoc.accept_all()`, returns it.
- `reject_all(doc_path)`, `find_and_replace_tracked(...)`, `apply_tracked_changes(...)`,
  `_enable_markup_view(...)`; dataclasses `TextChange`, `ParagraphEdit`; `WORD_NS`.
- CLI: `bench accept <in_folder> --out <out_folder>` and `bench reject ...`
  (walk the folder, write accepted/rejected copies).

Depends on the `docx_revisions` package (add to `pyproject.toml`).

## 11. Docker (i)

- **`Dockerfile`** — base with LibreOffice (`soffice`), Python 3.14 + `uv`,
  Node, and Playwright's Chromium + system deps. Installs the bench, runs
  `playwright install --with-deps chromium`.
- **`docker-compose.yml`** — a `bench` service mounting `./corpus` and
  `./results` read-write, entrypoint `bench run --clean-runs`. Lets CI and local
  users run the identical image.

## 12. CI/CD (8 + f + NEW clean policy)

`.github/workflows/bench.yml`, scheduled (cron) + manual dispatch:
1. Build/run the Docker image.
2. `bench run --clean-runs` over `bench.yaml` (Word backend never invoked; scores
   vs committed `corpus/word_based`).
3. `gate.py` sets exit status (§8).
4. If `results/bench.jsonl` / snapshots changed, commit them back (§7 ensures
   this only happens on a real delta).
5. `runs/` intermediates are deleted by `--clean-runs`; nothing pixel-heavy is
   committed.

## 13. Build order (phases)

1. Skeleton + lift `score.py`/`diff.py`/`raster.py`/`report.py`; parity-check the
   numbers against `_fixtures/compare` on the existing jubarte/docxodus runs.
2. `render/soffice.py` (3) + `render/passthrough.py` (2); `bench compare` /
   `bench run` over a single tool.
3. `emit/jsonl.py` (b, j) + `emit/snapshot.py` + `aggregate.py`; `gate.py` (e).
4. `packages.py` (h) + sequential `bench.yaml` driver (a) + `runs/` naming &
   `--clean-runs` (NEW).
5. `render/playwright.py` (1) with harness profiles.
6. `accept_changes.py` (c) via `docx_revisions`.
7. `Dockerfile` + `docker-compose.yml` (i) + `.github/workflows/bench.yml` (8).
8. `render/word.py` (f) — local-only.

## 14. Open points to confirm before coding

- Exact `bench.yaml` field names above (esp. `render` vs `backend`, `generate`
  vs `docx`) — lock them now so the schema doesn't churn.
- Whether `results/bench.jsonl` and snapshots live in this repo or a data branch
  (default: same repo, committed).
- SuperDoc / CasualOffice `generate` commands must accept an `--out`/`--out-dir`
  pointing at `$RUN_DIR/docx` (the existing batch script already takes
  `--out-dir`; the jubarte one takes `--out`).

## 16. PLAN 2026-07-07 — fairness / skip-if-ran / per-stage JSONL / editor server

Goal: apples-to-apples, configurable, repeatable; skip already-ran benchmarks by
default (opt-in rerun); pins required; editor-server wired into run-all;
one JSONL line PER STAGE.

### Phase A — bench.yaml REQUIRES a version pin
- [x] `config.py`: every run must declare exactly one version source
      (`dist:` | `package:` | `python_package:`). `package`/`python_package`
      must carry an exact pin (`@x.y.z` / `==x.y.z`); reject `@latest`/bare.
      Escape hatch `unversioned: true` for sanity runs (word-redlines-soffice).
- [x] pytest for the validation.

### Phase B — skip-already-ran by default, `--rerun` to force
- [x] Identity = (tool, stage, tool_version, config_hash). After version
      resolution and before generate, scan `results/bench.jsonl`; if a line with
      the same identity exists → print `skip (already ran …)` and move on.
- [x] `--rerun/--force` on `run` + `run-all` overrides; env `BENCH_RERUN=1`.
- [x] pytest.

### Phase C — JSONL schema v3: one line per stage
- Stages: `redline` (vs Word oracle), `accepted`, `roundtrip`,
  `render-original` / `render-redline` / `render-accepted` (headless web-editor
  renderer benchmarks via playwright).
- [x] `emit/jsonl.py`: add `stage` field (2nd key after `tool`); drop embedded
      `roundtrip_scores`/`accepted_scores` — each stage is its own full line
      (`scores`, `aggregate`, `failures`, `timings`). schema: 3.
- [x] `cli._execute_run`: emit one line per executed stage.
- [x] change-detection + `accept-scores` + gate keyed by (tool, stage);
      snapshots `results/score-snapshots/{tool}__{stage}.json` (legacy
      `{tool}.json` == `{tool}__redline.json` fallback).
- [x] update report/README table generation + tests.

### Phase D — editor server command + playwright wiring into run-all
- [x] `harness.server:` (shell cmd) + `harness.url` in bench.yaml; new
      `bench serve <run-name>` starts it in foreground (dev use).
- [x] `_drive_runs`: for `render: playwright` runs, auto-start `harness.server`
      in background, poll `url` until ready (timeout), stop it after the run.
- [x] Add playwright renderer runs to bench.yaml (superdoc harness) producing
      the `render-*` stages; uncomment/adapt the existing harness blocks.
- [x] pytest/vitest smoke.

Build order A→B→C→D; run `uv run pytest -q`, `bun run typecheck`,
`bunx vitest run` after each phase. Check boxes here as phases land.

## 15. Add provenance

- Add the licenses and provenance, adding thank you at readme.md:
- .old/docx-revisions.py: https://github.com/balalofernandez/docx-revisions
- .old/compare/: https://github.com/superdoc-dev/superdoc-visual-benchmarks
