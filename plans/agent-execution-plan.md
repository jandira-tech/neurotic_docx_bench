# Agent execution plan — house order, Word redlines at scale, full parallelism, 90/90

Drafted 2026-08-03 on branch `feat/holdout` (top of the stacked-PR chain
#12→#13→#14→#15). This plan is written for an implementing agent; every
chapter is self-contained: ground truth, tasks with acceptance criteria, and a
non-obvious **Speed-up drop-in** (Chapter 5 lives inside each chapter — see
its index at the end).

Recommended execution order: **Chapter 3 → Chapter 1 → Chapter 2 → Chapter 4.**
Parallelism first (it makes every later run cheaper), then housekeeping and
decisions, then the corpus expansion, then the accuracy campaign that depends
on the expanded corpus.

## Standing rules (apply to every chapter)

- Conejo discipline: each chapter lands as one or more **stacked PRs** on top
  of the current top of the stack; red-green TDD (failing test first, verified
  failing for the right reason); adversarial review that must REFUTE before
  merge-ready.
- `bench run --only` is a **single-value** option (last flag wins,
  `src/neurotic_docx_bench/cli.py:1733`). One tool per invocation, chained
  with `&&`.
- Always `set -o pipefail` before piping a long run into `tee` — tee otherwise
  masks the exit code (this bit us once already).
- A parallel Claude session shares this checkout. **Never `git add -A`** —
  stage explicit paths only. Never touch the `<!-- DUAL_PATH_*:BEGIN/END -->`
  marker sections in RESULTS.md / docs/RESULTS.md / docs/SPEED.md; the export
  script's `_carry_foreign_marker_blocks` preserves them — keep it that way.
- **Never edit `src/**/*.py` while a bench run or pytest is executing** —
  ProcessPoolExecutor on macOS spawns workers that re-import source. Iterate
  in a worktree under `~/temp/T/wt-*` (NOT the scratchpad, which gets wiped),
  land after runs finish.
- Fresh worktrees need `bun install` before any test that resolves
  tool_version (`test_skip_already_ran` flakes otherwise; also Chapter 1 task
  1.7 makes that failure loud).
- Results are append-only (`results/bench.jsonl`); pair identity comes from
  `corpus/word_based/centralized_mapping.csv` (+ `_randomized`); the sealed
  holdout is `corpus/word_based/holdout.txt` (20 keys) and stays sealed.

---

## Chapter 1 — Putting order in the house

All previously flagged issues, turned into tasks. Ground truth for "flagged":
the wrap-up after commit `114ec13` ("feat(results): full-corpus (403-pair)
runs…", pushed on `feat/holdout`).

### 1.1 Decision gate G1 — ranking semantics (ASK ARTHUR, do not decide)

The README/RESULTS ranking now uses **newest full-corpus run wins** (was:
best-run-wins). This changes published numbers. Present both to Arthur in one
message with the concrete rows that differ; implement whichever he picks; if
he already answered in the conversation driving this plan, implement that.
Do not proceed past writing the ranking code until G1 is answered — everything
else in this chapter is independent and proceeds meanwhile.

### 1.2 Finish the corpus-regime split in RESULTS.md

README got the current/legacy corpus split (keyed on `corpus_revision`
presence); RESULTS.md's per-benchmark all-pins tables still mix regimes.
- Test first: extend `tests/test_export_results_md.py` — a legacy line (no
  `corpus_revision`) and a current line for the same benchmark must land in
  separate sub-tables with the same headers used in README's split.
- Implement in `scripts/export-results-md.py`, reusing the partition logic
  already written in `scripts/update-readme-ranking.ts` (port the predicate,
  keep the SEs/columns as-is).
- Regenerate RESULTS.md + docs/RESULTS.md, confirm DUAL_PATH blocks survive.

### 1.3 Populate the holdout gap section

No `--holdout` runs exist yet, so the gap section renders its placeholder.
Run, one tool per invocation (single-value `--only`):

```bash
set -o pipefail
uv run python -m neurotic_docx_bench.cli run --holdout --only jubarte-rust        2>&1 | tee /tmp/ho-rust.log
uv run python -m neurotic_docx_bench.cli run --holdout --only jubarte-final-lossless 2>&1 | tee /tmp/ho-lossless.log
uv run python -m neurotic_docx_bench.cli run --holdout --only jubarte-final-native   2>&1 | tee /tmp/ho-ast.log
```

(Adjust to the actual CLI entrypoint used for the 403-pair runs — check
`final-run2.log` in `~/temp/T/bench-recovery/` for the exact invocation.)
Then re-export and verify the gap table shows all three engines with n=20 and
the ±2·SE band. Holdout-only lines must NOT enter headline rankings (guarded
since PR15 — the test suite already covers it; don't break it).

### 1.4 Re-run legacy vendors on the current corpus

Every tool in `bench.yaml` with `script_redlines` in `benchmarks` that has no
`corpus_revision`-stamped line yet (enumerate: names at bench.yaml lines
63–280 — docxodus, superdoc, folio, jubarte-wasm, docx-redline-js, etc. —
minus the three jubarte engines already run). One `--only` invocation per
tool, `accept-scores` only for tools that complete without wipeout, then
re-export. Expect some to be slow or broken on the bigger corpus: a tool that
fails wholesale gets its failure recorded honestly (ITT policy scores
failures, doesn't hide them) — do not "fix" a legacy tool's score by
excluding docs.

### 1.5 bench.jsonl diet (design + implement smallest safe step)

`results/bench.jsonl` is large and append-only. Do NOT rewrite history.
Implement: new lines keep per-doc payloads, but add
`scripts/compact-results.py` that moves per-doc payloads of lines older than
the latest line per (vendor, benchmark, tool_version) into
`results/detail/<id_run>.json.gz`, leaving a stub field
`detail: "results/detail/<id_run>.json.gz"`. Gate/accept-scores/export must
read stubs transparently (test first: a compacted file produces byte-identical
RESULTS.md). Run it once; commit both the script and the compaction.

### 1.6 Merge the stack

After 1.1–1.4 land: merge PRs #12 → #13 → #14 → #15 in order (each into its
base, or retarget-and-merge per repo convention — inspect how #2…#11 were
merged and copy that). Delete merged branches. `main` must end up containing
the full chain plus this chapter's PRs.

### 1.7 Small sharp edges

- `tool_version` resolving to `None` when `node_modules` is missing must
  raise with a message naming `bun install` (currently silently breaks skip
  identity). Test first.
- The SuperDoc vendor submodule shows perpetually modified (`m … vendor/SuperDoc`).
  Diagnose (dirty submodule vs. commit drift); fix with a pin or
  `ignore = dirty` in `.gitmodules` so `git status` is clean. Don't hide real
  drift — check what the modification IS first.
- Archive `~/temp/T/bench-recovery/` keepers (final-run logs, holdout_keys.txt)
  into `docs/recovery/2026-08-corpus-400/` (small text files only, no
  patches/worktree leftovers), then delete the directory.

### Speed-up drop-in (Chapter 1) — persistent LibreOffice via unoserver

The legacy re-runs (1.4) are render-dominated: cold `soffice` startup is
~1–2 s per document × ~400 docs × N vendors. Non-obvious fix: run
`unoserver` (pip, wraps a single persistent LibreOffice process) and convert
via `unoconvert` over its socket — startup cost is paid once per worker, not
once per document. Implement as an opt-in render backend
(`render: unoserver` in bench.yaml, default stays `soffice`), with 12 server
instances on ports 2003–2014 pinned one-per-worker and per-instance
`-env:UserInstallation` profiles to avoid the profile lock. Acceptance: pixel
scores byte-identical to the soffice backend on a 20-doc sample (same
LibreOffice binary renders, so they must match); wall-clock per vendor drops
≥40%. If unoserver's LibreOffice version differs from 26.2.4.2, STOP and keep
soffice — oracle comparability outranks speed.

---

## Chapter 2 — Word-generated redlines: teaching doc + the 400-pair map

The full how-to (single osascript permission click, sandbox staging, the
compare loop, validation, wedge recovery) is the dedicated teaching document:
**`plans/word-redline-automation.md`** — the agent MUST read it end-to-end
before writing any code; this chapter only adds the corpus-shape spec.

### 2.1 Source pool (already inventoried — use the committed manifest)

`plans/superdoc-source-pool.sha256.csv` — 227 rows, one per `.docx` under
`/Users/arthrod/temp/T/docx-validate/tests/fixtures/external/superdoc`
(recursive), columns `relative_path,sha256,bytes`. Bucket counts: behavior 36,
cli-legacy 2, doc-api-stories 5, encryption 2, evals 10, layout-engine 2,
super-editor 170. Known facts the pairing algorithm must honor:

- **2 encrypted files** (`encryption/*`) — excluded (they hard-block on a
  password prompt; see teaching doc §2.3).
- **6 duplicate content SHAs** — never pair two files with equal sha256
  (Word compare of identical content yields an empty redline).
- Re-verify the pool before generating: re-hash and diff against the
  committed CSV; if the fixture repo moved/changed, regenerate the CSV first
  and say so in the PR.

### 2.2 Pairing spec — exactly 400 pairs, fully deterministic

- Usable pool: 225 files (227 − 2 encrypted).
- **Chain pairs (~224):** sort usable files by `relative_path`; pair each
  consecutive (i, i+1) within the same top-level bucket (path-sorted
  neighbors are related fixtures → meaningful, realistic diffs). Skip pairs
  with equal sha256.
- **Cross pairs (to reach 400):** seeded PRNG (`random.Random(0x5D0C400)`),
  draw ordered (base, next) uniformly from the usable pool; reject same-file,
  same-sha, and already-emitted ordered pairs; draw until total = 400.
- `pair_id`: `<bucket>__<stem>` per side, joined with `__VS__`; sanitize to
  `[A-Za-z0-9_]`, truncate each side to 60 chars and append the first 8 sha
  hex chars when truncated (macOS 255-byte filename cap, collision-proof).
- Output tree: `corpus/word_redlines_superdoc/` containing `manifest.csv`
  (columns: `pair_id, base_rel, next_rel, base_sha256, next_sha256,
  redline_docx, redline_sha256, status, error`), `docx_redlines_word/`, and
  later `pdf_redlines_word/`. The manifest IS "the map of documents where we
  have 400 redlines, SHA codes included" — every row carries three SHAs.
- Generator is a tested Python script (`scripts/build_superdoc_pairs.py`),
  pure function from (pool CSV, seed) → manifest; unit tests pin: row count
  400, zero same-sha pairs, zero encrypted rows with status ok, determinism
  (two invocations byte-identical).

### 2.3 Produce the redlines and oracles

1. Run the compare loop per the teaching doc → `docx_redlines_word/` +
   statuses in the manifest.
2. Validate every output (teaching doc §5: unzip -t, w:ins/w:del presence,
   soffice render smoke; 5% Word-reopen sample).
3. Produce oracle PDFs **the same way the existing word_based corpus did** —
   inspect `corpus/word_based/build_mapping.py` and the recovery logs to
   confirm whether `pdf_redlines_word` came from Word
   (`scripts/batch_word_to_pdf.scpt`) and replicate exactly; do not invent a
   new oracle path. Extend `oracle_manifest.json`-style fingerprinting to the
   new subcorpus (same hashing recipe → the corpus_revision stamp changes,
   which is correct and expected: new corpus, new regime marker).
4. Wire a new benchmark source into bench.yaml (either extend
   `script_redlines` with the new manifest or add `script_redlines_superdoc`
   — decide by how `generate-native-redlines.ts` consumes `--manifest`;
   it already takes per-manifest invocations, see bench.yaml lines 55, 67,
   238, so a second `&&`-chained invocation per tool is the low-risk shape).
5. Seal a holdout extension: 20 of the 400 new pairs, seeded
   `random.Random(0xD0C5 + 1)`, appended to a NEW file
   `corpus/word_redlines_superdoc/holdout.txt` (do not rewrite the existing
   sealed file — seals don't get edited).

### 2.4 Acceptance

- 400-row manifest committed with all SHAs; ≥380 rows `status=ok`.
- The three jubarte engines run end-to-end on the new subcorpus (scores may
  be ugly — that's Chapter 4's problem, not this chapter's).
- One documented permission click, zero others (teaching doc §7).

### Speed-up drop-in (Chapter 2) — producer/consumer overlap + APFS clones

Word compare is irreducibly serial (~25 min for 400). Don't let validation
and rendering serialize AFTER it: run the watcher-consumer from teaching doc
§6 so validation + PDF rendering of finished redlines proceed on the
12-worker pool while Word is still comparing. Stage files into the Office
group container with `cp -c` (APFS clonefile: O(1), zero bytes copied) rather
than `cp`. Net effect: pipeline wall-clock ≈ Word's own compare time, and
staging is free.

---

## Chapter 3 — Multi-thread / multi-worker everywhere, including the Python assessment

### 3.1 Ground truth (verified today)

Defaults are already 12 across `src/` (`config.py:36`, `cli.py:406,520`,
`pipeline.py` ×5, `accept_changes.py:93`, `functional_lens.py:146`) and
pytest runs `-n 12` (`pyproject.toml` addopts). What is NOT yet parallel or
is parallel-but-wasteful:

- `superdoc_redlines_gen.py:194,232` uses **ThreadPoolExecutor** — fine if
  the work is subprocess-bound; verify, and if any CPU-bound Python (XML
  parsing, zip repacking) runs in those threads, move to processes.
- **Pool-per-call**: `pipeline.py` builds a fresh ProcessPoolExecutor inside
  each of render/score/compare stages. On macOS spawn, each pool pays
  ~1–2 s × 12 workers of interpreter+import startup, several times per run.
- **Per-page pixel scoring** is pure-Python/PIL per page inside a worker —
  parallel across docs but slow within a doc.
- `scripts/export-results-md.py` parses the (large) bench.jsonl with stdlib
  json line-by-line, single process.
- pytest: `-n 12` without `--dist worksteal` — long-tailed test files leave
  workers idle.

### 3.2 Tasks

1. Audit sweep (commit the audit as a doc table in the PR body):
   `rg -n 'ThreadPoolExecutor|ProcessPoolExecutor|max_workers|for .*render|for .*score' src/ scripts/` —
   classify every site: parallel-ok / serial-hot / serial-cold (leave cold
   ones alone; don't parallelize one-shot 100 ms loops).
2. **Shared executor**: create one ProcessPoolExecutor per bench-run
   invocation (in `cli.py`/`config`), pass it down through
   pipeline/accept_changes/functional_lens instead of constructing per stage.
   Keep the `jobs` parameters (they now size the shared pool). Test: a run
   over a 6-doc fixture corpus spawns exactly one pool (assert via a spawn
   counter monkeypatch), results unchanged.
3. **Vectorize pixel compare**: replace per-pixel/PIL arithmetic with numpy
   (`np.asarray(img, dtype=np.int16)`, vectorized abs-diff + threshold
   count). Numpy is already an available dependency of the stack (verify in
   pyproject; add if truly missing). Test first: scorer output must be
   **bit-identical** on the committed canary pages (`corpus/canary_expected.json`
   regime) — a scorer change that shifts any score is a fail, this is a
   pure-speed change.
4. `--dist worksteal` in addopts; verify suite still green and wall-clock
   drops (record before/after in the PR body).
5. Export script: switch to `orjson.loads` per line (or a single
   `readlines` + map) — measure; only keep if >2× on the real file.
6. Sanity: `rg -n 'jobs: int = [1-9]\b|max_workers=[1-9]\b' src/` matches
   nothing but 12s after the change (i.e., no stray small defaults).

### 3.3 Acceptance

Full `bench run` on the 403-pair corpus and full pytest, before/after
wall-clock in the PR body; scores byte-identical (this chapter must not move
a single score); suite green under worksteal.

### Speed-up drop-in (Chapter 3) — forkserver + warmed workers

Non-obvious on macOS: the default spawn context re-imports the whole package
per worker per pool. Switch the shared executor to
`multiprocessing.get_context("forkserver")` with
`ProcessPoolExecutor(mp_context=ctx, initializer=_warm)` where `_warm`
imports PIL/numpy/lxml once; forkserver forks pre-warmed children from a
clean template process, cutting per-worker startup to ~50 ms while avoiding
fork-after-threads unsafety. Guardrail: forkserver still re-executes module
state — the "never edit src during runs" rule stays. If any dependency
misbehaves under forkserver (Objective-C frameworks can), fall back to spawn
+ the shared-pool change alone, which already removes the repeated cost.

---

## Chapter 4 — 90/90 for each jubarte on the 800 fixtures

### 4.1 Definition

Target, per engine (jubarte-rust, jubarte-final-lossless,
jubarte-final-native/ast): **mean ≥ 90 AND median ≥ 90** on the combined
**800-fixture corpus** = 403 existing pairs + ~400 Chapter-2 pairs, scored
with both holdouts excluded from the headline number (n ≈ 760), ITT policy
(failures score, nothing hidden). "90/90" is measured by the standard
pipeline only — no scorer changes ride along with engine changes, ever
(separate PRs, separate runs).

### 4.2 Baselines (403-pair corpus, holdout-excluded, snapshots committed)

| engine | mean | median | <70 | <90 | =100 | failures |
|---|---|---|---|---|---|---|
| jubarte-rust | 85.02 | 93.37 | 99 | 163 | 126 | 0 |
| jubarte (lossless) | 82.27 | 86.05 | 110 | 213 | 109 | 0 |
| jubarte-ast | 75.00 | 77.14 | 147 | 282 | 40 | 9 (ITT 73.43) |

Arithmetic of the gap (rust): +4.98 mean points over n=383 ≈ 1907 doc-points;
the 99 sub-70 docs average ≈ 55, so lifting them to ≈ 75 closes it — i.e.
**the campaign is won or lost entirely in the sub-70 tail**; polishing
93→96 docs is noise. The same holds harder for the other two engines.

### 4.3 Where the tail is (from committed snapshots — verify, then extend)

`results/score-snapshots/{jubarte-rust,jubarte,jubarte-ast}__script_redlines.json`
(flat key→score maps). Known clusters from the worst-10 lists:

- `sample_document_word_repair_*` pairs — 28–37 on ALL three engines →
  malformed-input tolerance/repair path.
- `sd_2517_localized_heading_styles_sectpr_headerref` — 42–44 on all →
  sectPr/headerReference handling.
- `table_bookmark_end_table_vmerge_colspan` (lossless 41) → table
  vMerge/gridSpan revisions.
- `docx_lots_of_comments_addition_removal` (lossless 39) → comment
  add/remove revisions.
- `file_NN_file_NN+1` randomized chains (many, all engines, worst on ast) →
  large whole-document rewrites; likely alignment/anchoring, not features.

### 4.4 Engine source map (do not guess — verified paths)

- **jubarte-rust**: source `~/T/jubarte-redlines` (canonical per
  `~/T/reconciliation_plan/GET_JUBARTE_RUST.md`; GitHub `arthrod/jubarte-rs`).
  Build `cargo build --release`, install as
  `src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline`.
- **jubarte-final (lossless + ast)**: `dist/jubarte-final` is a built JS dist;
  probable source `~/T/jubarte-first` (package name `jubarte` 0.1.0 — same as
  `~/T/jubarte-base`, so **verify before editing**: rebuild the candidate
  repo's dist and diff file hashes against `dist/jubarte-final`; only edit
  the repo whose build reproduces the dist).

### 4.5 The loop (per engine, strict order)

1. **Crash-free first (ast only):** 9 failing docs score ~0 under ITT —
   fixing crashes is worth ~+1.8 mean points before any quality work.
   Reproduce each with the engine CLI directly on the pair's inputs, fix in
   the engine repo with a regression fixture there (red-green in THEIR test
   suite), rebuild, reinstall into the bench.
2. **Pareto mining:** join snapshot scores with
   `corpus/word_based/coverage_tags.json` (`pairs.<key>.features` /
   `.revisions`) → table of (tag, n_docs<70, mean-points recoverable).
   Attack clusters in recoverable-points order. Commit the mining script
   (`scripts/mine_failure_clusters.py`, tested) — it will be rerun dozens of
   times.
3. **Per-cluster fix loop:** failing fixture test in the engine repo → fix →
   rebuild → reinstall → **targeted re-score of only that cluster's keys**
   (see this chapter's speed-up drop-in) → full corpus run only when the
   cluster clears locally.
4. **Anti-overfit guardrails (all hard gates, already in the bench —
   respect them):** holdout gap within ±2·SE (`bench run --holdout` after
   every full run); mutation probes must keep discriminating; functional
   accept/reject lens must stay green; lens-disagreement metric must not
   spike. An engine change that helps the visible set but blows the holdout
   gap gets reverted, not explained away.
5. **Milestones, each = full run + accepted snapshot + commit + push:**
   - M1: ast crash-free (0 failures).
   - M2: no doc < 50 on any engine (kills the repair/sectPr cluster).
   - M3: mean ≥ 88 per engine on the 403-corpus.
   - M4: Chapter-2 corpus lands → first 800-fixture full runs (expect a dip;
     record it honestly — new-corpus baselines).
   - M5: mean ≥ 90 AND median ≥ 90 per engine on the 800, holdout gap ≤2·SE.
6. Every engine-repo change goes to that repo's own branch/PR; the bench
   repo only receives rebuilt artifacts + snapshot/results commits, each
   stamping the engine commit hash in the results line's tool_version (the
   existing `@<hash>` convention — e.g. `jubarte-rust@fcea02da49f4`).

### 4.6 Honesty clauses

90/90 might be unreachable for a given engine architecture (ast's
40-perfect / 282-below-90 profile suggests structural, not incremental,
distance). If two consecutive milestone iterations recover <1 mean point
each, STOP and report the ceiling with the Pareto table as evidence instead
of grinding — Arthur decides whether to accept a lower target or redesign.
Never close the gap by touching the scorer, the oracles, the corpus
composition, or by special-casing benchmark filenames in engine code (that's
gaming; the mutation probes exist to catch exactly this).

### Speed-up drop-in (Chapter 4) — content-keyed render cache for the inner loop

The iteration bottleneck is re-rendering + re-scoring ~800 docs per engine
tweak when <5% of outputs actually changed. Add a render cache keyed by
`sha256(generated_docx_bytes)` → rendered PNG set + per-doc score
(precedent: `results/null_baseline.json` is already a content-keyed cache in
this repo). On each run, docs whose generated bytes are unchanged reuse
cached renders/scores; only changed docs hit LibreOffice. Combined with
`score_folders_full(only_keys=cluster)` (exists since PR15) for mid-loop
smoke checks, the inner loop drops from ~40 min to ~2 min. Cache lives in
`results/render-cache/` (gitignored), is invalidated wholesale by renderer
fingerprint change (the canary from the earlier robustness work is the
trigger), and full milestone runs bypass it (`--no-render-cache`) so accepted
snapshots never depend on cache correctness.

---

## Chapter 5 — Speed-up drop-ins (index)

Per Arthur's spec, each chapter carries one non-obvious drop-in; this chapter
just indexes them and states the shared rules.

| Chapter | Drop-in | Non-obvious core |
|---|---|---|
| 1 | unoserver persistent LibreOffice | pay soffice startup once per worker, not per doc; hard-stop if it changes the oracle renderer version |
| 2 | producer/consumer + APFS clonefile | pipeline finishes when Word finishes; `cp -c` staging is O(1) |
| 3 | forkserver + warmed shared pool | kills macOS spawn re-import tax; one pool per run, not per stage |
| 4 | content-keyed render cache + only_keys smoke loop | 20× faster engine iteration; milestone runs bypass the cache |

Shared rules for all four: (a) every drop-in is opt-in behind a flag with the
old path as default until its byte-identical-scores test passes; (b) a
drop-in may change wall-clock only — any score delta is an automatic revert;
(c) measure and record before/after wall-clock in the PR body, on the real
corpus, not a toy.
