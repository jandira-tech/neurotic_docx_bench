# Execution plan, 2026-09-27 (after consolidate/10-scorer)

State at the time of writing: base `bench/latest-competitors-0926` = 962fb8e0; branches
08-release, 09-policy, 10-scorer are built and committed (HEAD 0c30f964, item 9c). This
plan covers what is left of `docs/plans/2026-09-27-bench-0.7.0.md`, the three patches
Arthur left in the repository root, and the new `bench try` helper. Order of work is
stated in section 6. Rules that apply to every step: red-green (a failing test first),
`ruff` and `ty` clean, coverage stated in the working notes and never reduced, nothing
under `results/` or `corpus/` deleted, commits made in the VM, pushes made by Arthur.

## 1. The three patches (`pipeline.patch`, `score.patch`, `score_v2.patch`)

All three carry wrong hunk line counts; `git apply --recount` is needed. Findings from
the review already delivered stand. Disposition, pending Arthur's word:

- `score.patch`: apply on 10-scorer. It refactors `_score_page` into
  `_compute_metrics(word_rgb, sd_rgb, config, *, word_gray, sd_gray, ink_word, ink_sd)`
  and was parity-verified identical on four documents (overall 99.9925, 100.0, 99.7542,
  99.9430) with about a 10% gain on the score stage. Failing test first: a parity test
  that scores two fixed page pairs through `_score_page` and through `_compute_metrics`
  with precomputed grays and masks, asserting equal `PageMetrics` to 1e-9.
- `pipeline.patch`: not applied as is. Its `_run_tasks` hunk is against the pre-9c file
  and would drop `initializer=kernels.worker_init, initargs=(jobs,)`. Rebase by hand:
  keep `worker_init`; move the OMP/VECLIB/OPENBLAS `setdefault` calls into
  `kernels.worker_init` (they belong to worker start, not module import); wire
  `cache=cache` at the `_add_v2` call site (pipeline.py:330) with a test that asserts the
  base PDF is rasterized through the cache; drop the inline pairing that duplicates
  `match_by_stem`; the `jobs = min(..., 8)` clamp is measured on the Mac before it is
  kept (on the VM it was noise: 23.19 s vs 22.69 s); `chunksize=1` is kept.
- `score_v2.patch`: held. It changes the metric (PIL uint8 per-channel `>20` mask, a
  `>0.85` whole-page heuristic, a bbox crop) and moved one document 99.7925 to 99.7866.
  A metric change needs a v2 version bump, a regression fixture and a decision; it is
  not applied in this stack.

## 2. PR 16: `bench try` (the helper for the Hugging Face Space)

Interpretation of the request, stated for confirmation: the helper works over a fixed
"tryout" set of exactly 100 fixtures we already have with Word oracles. It does not
touch the 736K-row `superdoc-dev/docx-corpus` web dataset. The comparison tool is
jubarte, whose outputs for those 100 are precomputed once with
`/Users/arthrod/T/jubarte-redlines/target/release/jubarte` and shipped with the set, so
the Space never needs the binary or Word.

### 2.1 The tryout set

Pool: `corpus/no_comments_pdf_was_generated_by_word`. It is the corpus whose PDFs were
exported by Word itself (producer `macOS ... Quartz PDFContext`); every PDF under
`corpus/word_based` and `corpus/word_redlines_superdoc` carries the producer
`LibreOffice 26.2.4.2 / Writer`, so a comparison against those measures a renderer
against LibreOffice, not against Word. The pool gives every task a Word oracle from
the same pair: `pdf_source/<base>.pdf` and `pdf_source/<next>.pdf` (the convert
oracle), `pdf_redlines_word/<pair>_word_redline.pdf` or `<pair>_redline.pdf` (the
redline oracle; the `_word_redline` variant is preferred when both exist, as
`pipeline._index_redlines` does) and `pdf_accepted_word/<pair>_redline.pdf` (the
accept oracle), plus the comment-stripped `docx_source`, `docx_redlines_word` and
`docx_accepted_word` inputs. The corpus's `centralized_mapping.csv` supplies only
`pair_stem`, `base` and `next`; its accepted-file columns are stale, so every file is
located on the filesystem. Counting today: 207 rows, 193 eligible (2 lack a Word
redline PDF, 12 are on a holdout).

Selection: the eligible pairs sorted by `pair_stem`, sampled with
`random.Random(20260927).sample(..., 100)`, sorted again. Holdouts are the union of
`corpus/holdout_combined.txt` and `corpus/word_based/holdout.txt` (40 keys). The set
is recorded once in `corpus/tryout/tryout_100.csv` with columns `pair_stem, base,
next, docx_base, docx_next, pdf_base_word, pdf_next_word, docx_redline_word,
pdf_redline_word, docx_accepted_word, pdf_accepted_word` and a `sha256_<column>` for
each of the eight files. The CSV is the contract; a test asserts it has 100 rows, no
holdout stems, every referenced file present with its sha256. The selection script
(`scripts/tryout_jubarte.py`, later `bench try build-set`) is idempotent, refuses to
rewrite an existing CSV without `--force-set`, and refuses a CSV drawn from another
corpus or lacking the docx columns unless `--force-set` is passed.

### 2.2 jubarte outputs for the set

Redline: `jubarte <base.docx> <next.docx> -o <out.docx> --force --quiet` for each of
the 100 pairs, then `jubarte convert <out.docx> -o <out.pdf> --force` so the redline
PDF is jubarte's own render. No soffice: the point of the comparison is jubarte's PDF
against Word's PDF, renderer included. Convert: `jubarte convert <base.docx> -o
<out.pdf> --force` for the 100 base documents. Both go to
`corpus/tryout/jubarte/{redline,convert}/` with `corpus/tryout/jubarte/MANIFEST.json`
(binary path, `jubarte --version`, ENGINE_COMMIT and SOURCE_COMMIT from the vendored
copy, sha256 of every output, `set_sha256` of the CSV the outputs were made from, and
`corpus`). A manifest whose `set_sha256` differs from the current CSV marks the
outputs stale and the script refuses to resume over them without `--force`.

The binary is macOS arm64 and the VM is Linux without cargo, so this step runs on the
Mac: `uv run scripts/tryout_jubarte.py --jubarte-bin
/Users/arthrod/T/jubarte-redlines/target/release/jubarte`. Arthur runs it.
`docx_to_pdf.DEFAULT_CONVERTER` currently resolves to `<repo parent>/jubarte-redlines/...`,
which on the Mac is `/Users/arthrod/temp/T/...`, not the path given; PR 16 adds
`JUBARTE_BIN` (env) and `--jubarte-bin` (option), consulted first by
`resolve_tool_binary`.

The user's tool in `bench try` gets the same treatment: `--renderer passthrough` is
the default (the tool writes the PDF that is scored), `soffice` and `word` are
explicit opt-ins for tools that only write DOCX.

Until the Mac step has run, the VM tests use a fake tool (a Python script that copies
its input) and a fake manifest.

### 2.3 Publication

`corpus/tryout/` (fixtures, oracles, jubarte outputs, both manifests, ODC-By-1.0
attribution) is uploaded under `tryout/` in `arthrod/neurotic_docx_bench-fixtures`
(created if missing) by `bench fixtures upload --only tryout`, reusing `hub.py`
(`upload_folder`, then `verify_uploaded`). Size estimate before upload; the 100-pair
set with oracles and jubarte outputs is in the low hundreds of MB. Download is per
file with `hf_hub_download` (one fixture at a time; a Space never pulls the whole set)
plus `MANIFEST.sha256.json` verification.

### 2.4 Command shape

```
bench try (--random [--seed N] | --fixture PAIR_STEM | --list)
          --task redline|convert
          --tool "<command template>"          # {base} {next} {out} for redline,
                                               # {input} {out} for convert
          [--against jubarte|"<template>"]     # default jubarte (precomputed)
          [--renderer passthrough|soffice|word]  # default passthrough (the tool writes
                                               # the PDF); soffice/word for DOCX tools
          [--set-dir DIR | --repo ID --revision R]  # local set or Hub download
          [--out DIR] [--json OUT] [--dpi 144]
```

Output: for the chosen fixture, the user's tool score against the Word oracle
(pagefair-v2 overall, plus change-region v2 for redline), jubarte's score against the
same oracle, the difference, timings, renderer id, scorer fingerprint, sha256 of every
input and output, and the paths of the rendered pages so a Space can show them side
by side. Nothing is written under `results/`. `--random` with no `--seed` uses
`SystemRandom` and prints the seed; the same seed always picks the same fixture.

Importable API in `neurotic_docx_bench/tryout.py`, all pure functions over paths so the
Space calls them without the CLI: `load_set(dir) -> TryoutSet`, `pick(set, seed=None,
stem=None) -> Fixture`, `run_tool(template, fixture, task, out) -> Path`,
`render(path, renderer) -> Path`, `score_against(oracle_pdf, candidate_pdf, dpi) ->
dict`, `compare(fixture, task, candidate_pdf) -> TryReport`, `fetch(repo, revision,
stem, dest, api=)` (network only through the injected `api`, as in `hub.py`).

### 2.5 Tests (written first, each failing before its implementation)

`tests/test_tryout.py`: set builder picks exactly 100, excludes holdouts, is
deterministic across two calls and records matching sha256; `pick` with a seed is
stable and with a stem is exact, unknown stem names the closest stem; `run_tool`
substitutes the placeholders, refuses a template missing `{out}`, reports a non-zero
exit with stderr and a missing output file; `compare` scores a passthrough copy of the
oracle at 100 and a blank page below it; `fetch` with a fake `api` verifies the
manifest and refuses a mismatched sha256; CLI: `--list`, `--fixture`, `--random
--seed`, `--json` shape, no writes under `results/`, `JUBARTE_BIN` honoured. Target
90% line / 85% branch on `tryout.py`.

## 3. PR 11 to PR 15 (unchanged from the 0.7.0 plan)

- 11-families (item 5): families `redline`, `accept`, `render` with an input-kind column
  (plain, redline, accepted); `roundtrip` detailed-only; legacy names mapped for history.
  Tests on the mapping table, the report's family sections and the frozen page.
- 12-corpus (item 7): grok_run imports (`fixtures_500`, parts a/b with Word PDFs to
  `render`; A-vs-B compares and the 500 extra redlines with `wordpdf_redline_oracles` to
  `redline`), provenance from `MANIFEST.json` and `500_en_sources.jsonl`, ODC-By-1.0
  attribution, sha256 manifest, docset ids. Tests on the manifest builder and the
  `CorpusEntry` registration; no corpus file is moved or deleted.
- 13-word-control (item 11): one canary document open for the session, phrase never in
  any output, paragraph count re-checked after every item, exempt from
  `close every document saving no`; `--allow-open-docs` removed; preflight refuses
  foreign open documents; README states the operator rule. Tests with the fake Word
  driver; the real Word path is exercised by Arthur on the Mac.
- 14-score-cli (item 12): `bench score --benchmark redline|accept|render --oracle DIR
  (--files a,b,c | --dir D) [--renderer word|soffice] [--json OUT] [--record --tool ID]`;
  stem matching with closest-stem reporting; `--record` appends to `results/dev.jsonl`
  with `published: false`; `bench run --unpublished`. Shares `tryout.score_against` and
  the closest-stem helper with PR 16.
- 15-bun-ci (item 10 and item 2 CI): `bun test` replaces vitest for the 12 files,
  `bun test --coverage`, verified in the VM with a Linux `node_modules`; CI runs the
  Python tests, `bun test` and `bench report --check` only; the manual soffice smoke
  uploads an artifact only.

## 4. Loose ends carried in this plan

- `scripts/device_ab.py` is untracked; commit it with PR 16 unless Arthur says no.
- The pre-existing failure `tests/test_cli_driver.py::test_generate_then_render`
  (98.86 vs 100) is not touched by this stack and is listed in the hand-off.
- The `$HOME/wt_head` worktree is removed at the end (`git worktree remove` + `prune`).
- VM disk: 2.7 GB free at the time of writing; Arthur is told the moment it fills.

## 5. Open questions (answered by Arthur, defaults apply if unanswered)

1. Pool for the tryout set: `corpus/no_comments_pdf_was_generated_by_word`, 193
   eligible pairs, seed 20260927. Default: yes.
2. Who runs the jubarte step on the Mac: Arthur with the command from 2.2, or me through
   the shell tool on request. Default: Arthur.
3. `score.patch` applied with a parity test; `pipeline.patch` rebased by hand as in
   section 1; `score_v2.patch` held. Default: yes.
4. `--against jubarte` compares against jubarte's own precomputed PDF render (no
   soffice); a Word render of jubarte's redline is not shipped unless Arthur asks.

## 6. Order

PR 16 first (Arthur's newest request, and its `score_against` helper is reused by
PR 14), then 11-families, 12-corpus, 13-word-control, 14-score-cli, 15-bun-ci, then
the full-suite verification and the hand-off.
