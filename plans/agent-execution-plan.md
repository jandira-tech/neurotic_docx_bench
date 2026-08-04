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

### 4.2 Baselines

#### Superseded: 403-pair corpus (kept for the arithmetic below)

| engine | mean | median | <70 | <90 | =100 | failures |
|---|---|---|---|---|---|---|
| jubarte-rust | 85.02 | 93.37 | 99 | 163 | 126 | 0 |
| jubarte (lossless) | 82.27 | 86.05 | 110 | 213 | 109 | 0 |
| jubarte-ast | 75.00 | 77.14 | 147 | 282 | 40 | 9 (ITT 73.43) |

#### Current: 803-pair corpus (M4 measured 2026-08-04)

`corpus_revision b7f467074a51`, holdout-excluded, **n = 763**, ITT (`itt_n_docs`
763 for all three — failures zero-filled, nothing hidden):

| engine | ITT mean | ITT median | ≥90 | =100 | <50 | failures |
|---|---|---|---|---|---|---|
| jubarte (lossless) | **77.02** | 78.53 | 277 | 142 | 80 | 0 |
| jubarte-rust | 76.21 | 77.95 | **307** | **158** | 108 | 0 |
| jubarte-ast (native) | 69.83 | 68.30 | 178 | 84 | 142 | **9** |

Two things this table says that a single ranking column would hide:

- **rust is bimodal.** It wins outright on perfect scores (158 vs 142) and on
  ≥90 (307 vs 277), yet loses the mean — because it also fails hardest (108
  below 50 vs 80). Ranking these engines on the mean alone picks the wrong
  winner for a "how often is it exactly right" question, and on the median for
  a "how bad is the tail" question. Report both.
- **The ast engine's 8 render failures are Word-validity failures**, not scoring
  failures: LibreOffice cannot open the DOCX at all ("source file could not be
  loaded"). Its raw pixel mean over the 755 openable docs is 70.57; ITT
  zero-fills the 8 and gives 69.83. Reporting 70.57 would pay the tool for
  output nobody can open.

Subcorpus split (jubarte-rust): word_based n=383 mean 85.02 median 93.37;
superdoc n=380 mean 67.32 median 62.42. **The new pool is much harder** — 23%
of its pairs reach 90 against 57% on word_based. The word_based figure is
identical to the pre-rebuild run, which is the control proving the rebuild
perturbed nothing that already existed.

Arithmetic of the gap (rust, on the current corpus): the miner puts the total
at **+15.29 mean points** if every one of the 328 sub-70 documents reached 90.
**The campaign is won or lost entirely in the sub-70 tail**; polishing 93→96
docs is noise. The same holds harder for the other two engines.

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
2. **Pareto mining:** DONE — `scripts/mine_failure_clusters.py` (tested), joining
   scores with `corpus/word_based/coverage_tags.json` +
   `corpus/word_redlines_superdoc/coverage_tags.json`.

   Two corrections this step forced, both worth carrying:

   - The SuperDoc subcorpus had **no coverage tags at all**, so 380 of 763
     documents were unjoined and 229 failing documents were invisible to the
     ranking. Generating them (`bench coverage-matrix` over the SuperDoc
     mapping, 400/400 tagged, 0 errors) took the join to 763/763. A new
     subcorpus is not minable until its tags exist — check the "unjoined"
     count before trusting any ranking.
   - **Recoverable mean-points alone ranks by ubiquity, not by signal.**
     `rev_ins` sits on 740 of 763 pairs and led every ranking while saying
     nothing more than "documents fail". The miner now also reports
     `lift` = tag failure rate ÷ corpus base rate; `rev_ins`/`rev_del` come in
     at **1.02** (noise), and a universal tag is pinned at 1.0 by construction.
     `rev_rPrChange` is **0.94** — run-property changes are *easier* than
     average, which is a useful negative result for the format-changes corpus.

   Attack order for jubarte-rust (base failure rate 43%), reading mass and
   lift together:

   | tag | tagged | failing | lift | recoverable |
   |---|---|---|---|---|
   | field | 186 | 72.6% | 1.69 | +6.35 |
   | footer | 157 | 74.5% | 1.73 | +5.59 |
   | numbering | 182 | 64.8% | 1.51 | +5.50 |
   | image | 166 | 68.1% | 1.58 | +5.27 |
   | content_control | 81 | 77.8% | 1.81 | +2.89 |
   | rev_tblChange / tblGridChange / tcPrChange | 51 | 76.5% | 1.78 | +1.94 |

   Highest lift overall sits in small clusters — textbox 1.96, rtl 1.90,
   math 1.82 — worth a look only once the rows above are closed, since none
   moves the mean by even half a point.
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
   - M4: **DONE (2026-08-04)** — Chapter-2 corpus landed, first 803-pair full
     runs recorded in §4.2. The dip was real and large: rust 85.02 → 76.21,
     lossless 82.27 → 77.02, ast 75.00 → 69.83. Recorded as the new baseline,
     not explained away.
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

---

## Chapter 6 — Pure juice of reality (validity + fairness before any publication)

Added 2026-08-04 after the Chapter 1.4 competitor sweep. The sweep did not
merely find broken vendors — it found that **the comparison itself was not
valid**, and that the invalidity ran in our favour. Nothing in RESULTS.md that
compares jubarte to another vendor may be published until 6.1–6.4 land.

### 6.1 The three defects (measured, not suspected)

**D1 — Corpus asymmetry. Two thirds of the runs are scored on a quarter of the
corpus, and they share a table with the ones that are not.**

Corpus coverage is copy-pasted per run, so it drifted. Of the 12 runs
declaring `script_redlines` (measured by parsing bench.yaml, 2026-08-04):

| coverage | runs |
|---|---|
| all three manifests — 803 pairs | `jubarte-rust`, `jubarte-final-native`, `jubarte-final-lossless`, **`docxodus`** |
| single default manifest — 207 pairs | `docx-redline-js`, `folio`, `superdoc`, `redlines`, `superdoc-redlines`, **`jubarte-wasm`**, `superdoc-ts`, `superdoc-native` |

A run that omits `--manifest` silently inherits the argparse default
`corpus/word_based/centralized_mapping.csv`. Observed n from the 1.4 sweep:
`jubarte-wasm` **n=195**, `superdoc` **n=171**, against `jubarte-rust`
**n=763**. Rows with different n are published in the same comparison table,
so they are not the same measurement.

**Correction (2026-08-04):** an earlier draft of this section claimed *only
jubarte-rust* had full coverage and that the asymmetry therefore ran in our
favour. That was wrong, and the error is worth keeping visible: a competitor
(`docxodus`) already had full coverage, and one of our own runs
(`jubarte-wasm`) is among the partial ones. The split does not follow vendor
lines at all — it follows which `generate:` line someone last copy-pasted.
That makes the defect *more* worth fixing structurally, not less: a footgun
that has already misfired in both directions will misfire again.

Note on direction: the SuperDoc pool is much harder (rust 67.32 there vs
85.02 on word_based), so full coverage *lowers* a tool's score. A comparison
whose validity depends on which way the bias happens to point is not a
measurement either way.

**D2 — Version staleness. Competitors are frozen; jubarte is at HEAD.**
Checked against the registries on 2026-08-04:

| pin | bench.yaml | latest | gap |
|---|---|---|---|
| `docxodus` | 7.0.0 | **9.0.0** | 2 majors |
| `@stll/folio-core` | 0.3.1 | **0.15.13** | 12 minors |
| `superdoc` (editor) | 1.44.1 | **2.3.0** | 1 major |
| `superdoc-sdk` (Python) | 1.19.2 | **2.0.0** | 1 major |
| `@superdoc-dev/sdk` | 1.19.2 | 1.21.3 | 2 minors |
| `@stll/folio-react` | 0.5.0 | 0.13.2 | 8 minors |
| `redlines` | 0.6.1 | 0.6.1 | current |

Worse than passive staleness: the pin is *enforced downward*. The repo's
`package.json` carried `docxodus ^7.1.0`; the 1.4 sweep's tool_updater
**downgraded it to ^7.0.0** to honour the pin. We were actively installing an
older competitor than the one already present.

The pin comment ("Do NOT bump to @latest without re-review — the pin keeps CI
reproducible") is a good rule that produced a bad outcome: reproducibility was
preserved and fairness was silently spent. Both are obtainable — see 6.3.

**D3 — Our missing infrastructure recorded as vendor failure.**
`superdoc-native` and `superdoc-redlines` both failed with `tool build dir not
found` — the gitignored clones (`superdoc/`, `superdoc-redlines/`) are simply
absent. `superdoc-ts` failed `ERR_MODULE_NOT_FOUND` resolving
`@superdoc-dev/sdk` from `utils/superdoc/node_modules/` while the updater
installs it at the repo root. The `docxodus-playwright-*` runs point at
`utils/docxodus/Docxodus/npm`, which does not exist either.

None of these are the vendor's code. **ITT zero-fills a tool that ran and
produced bad output; it must never zero-fill a tool we failed to install.**
The distinction is load-bearing and is now a rule (6.5).

**D4 — A fixed generate timeout that did not scale with the corpus.**
`src/neurotic_docx_bench/cli.py:788` runs each run's `generate:` command with a
hard-coded `subprocess.run(..., timeout=1800)`. That 1800 s budget was chosen
when a run meant 207 pairs. The corpus is now 803 pairs — roughly 4× the work
against an unchanged budget.

Measured 2026-08-04: `docxodus` (which does have full corpus coverage) was
killed at exactly 1800 s having generated **622 of ~763** documents, and the
run was recorded as `1 run(s) failed: docxodus`. Nothing in that line says the
tool was cut off by our clock rather than by its own defect.

This is the D3 disease in a subtler form: **our budget, attributed to their
code**. A tool that is merely *slow* must be reported as slow — with its
throughput — not as failed. Two things follow:

1. The timeout must scale with the number of pairs the generate step covers
   (or be per-run configurable), and a timeout kill must be recorded as
   `TIMEOUT` with the completed/total count, never silently as a failure.
2. **Benchmark runs used for publication must not share the machine with other
   heavy work.** The docxodus timeout above is confounded: five coding agents
   and a LibreOffice fleet were running concurrently. That measurement is
   therefore not clean vendor data and is not publishable as a docxodus
   result — it is only evidence that the harness has defect D4.

**D5 — Version split-brain: the version we record need not be the code we ran.**
Found 2026-08-04 while bumping docxodus. A run's `package:` pin is installed
into, and read back from, the **repo-root** `node_modules` (`cli.py` calls
`resolve_tool_version` with `cwd=` the repo root), but the adapter
`loadEngine("docxodus")` imports the **vendored**
`src/neurotic_docx_bench/utils/docxodus/node_modules` tree. Nothing tied the
two together.

The checkout demonstrated the failure concretely: root held **7.1.0** against a
**7.0.0** pin, so a run could stamp `tool_version` from one tree while
measuring code from another. Every published docxodus number is only as
trustworthy as that coupling, and the coupling did not exist.

This generalises beyond docxodus — any vendor with both a root install and a
vendored tree can drift the same way. Fixes required:

1. Resolve `tool_version` from **the tree the adapter actually imports**, or
   assert at run start that the two agree and abort loudly if they do not.
2. Pin **exactly** (`name@x.y.z`), never a `^range`: a caret lets
   `bun install` drift the installed version off the recorded pin, which
   silently recreates the split.
3. A test asserting the agreement, so this cannot regress.

Related, same commit: the docxodus adapter called `compareDocuments(base, next)`
with no options, so the **comparison engine was whatever the installed version
happened to default to**. A vendor changing its default engine between releases
would silently change what we measure while the version string moves as
expected. Engine selection must be named explicitly.

**D6 — The JS runtime is part of the measurement, and it is not neutral.**
This machine runs **Node v25.9.0**, a bleeding-edge non-LTS release. Discovered
2026-08-04 when the freshly-installed `superdoc-redlines` CLI crashed inside a
transitive dependency:

```
@harbour-enterprises/superdoc/dist/chunks/index-BN3GuVpx.es.js:7087
TypeError: varStorage.getItem is not a function
```

Its `package.json` declares `engines: {"node": ">=18.0.0"}`, so on a literal
reading Node 25 is supported and this is the vendor's bug. But `>=18.0.0` is
the usual open-ended default written before Node 25 existed, and a benchmark
that leans on that technicality is scoring a footnote rather than the software.

The part that makes this OUR problem rather than theirs:

> **`jubarte-rust` is a native binary and is immune to the Node version.
> `jubarte-wasm`, docxodus, folio, superdoc, superdoc-ts, docx-redline-js and
> superdoc-redlines all run through Node and are not.** Choosing a bleeding-edge
> runtime therefore imposes a risk on every JS competitor that our flagship
> engine does not carry — an asymmetry we introduced by choosing the runtime,
> not one the vendors chose.

Rules adopted:

1. **Publication runs execute on a current Node LTS**, not on whatever the
   workstation happens to have. The Node version is recorded in the result line
   the same way `tool_version` is — a score without its runtime is incomplete.
2. A crash that reproduces on the LTS is the vendor's, and counts. A crash that
   occurs only on a non-LTS runtime is reported as a compatibility note in
   `docs/VENDOR_NOTES.md`, not as a score.
3. Same rule for LibreOffice and the OS: any component shared by candidates but
   *not* by the oracle is part of the method and gets recorded.

### 6.2 Definition — what "pure juice" requires

A cross-vendor number is publishable only when all six hold:

1. **Same document set.** Identical manifests, identical holdout exclusion,
   identical `corpus_revision`. Report per-subcorpus splits alongside the
   aggregate, because the pools differ in difficulty by ~18 mean points.
2. **Same oracle and renderer.** Already true (LibreOffice 26.2.4.2, Word
   redline PDFs); the fingerprint canary guards it.
3. **Latest released version of every competitor**, resolved on the run date
   and recorded in the line, not a pin chosen months earlier.
4. **Honest ITT** — a tool that runs and fails scores its failure. A tool we
   could not install is `UNINSTALLED`, reported as a gap in *our* harness.
5. **Adapter parity.** If jubarte gets a bespoke integration, a competitor
   that needs one gets the same effort. Where we cannot reach parity, the
   deficit is disclosed in the row, not absorbed into the score.
6. **Disclosed thumbs.** Every place we touched a vendor's code, forked it, or
   know of an unfixed bug is written down next to the number.

**D7 — A competitor carried benchmark rows that our own runs structurally could
not receive.** Found 2026-08-04 in the docxodus 9.0.0 full-corpus result.

Every `visual_*` benchmark in this config belongs to a dedicated
`*-playwright-*` run whose entire purpose is rendering — that is how `folio`
and `superdoc` are arranged, each with three separate playwright runs. But the
**`docxodus` generating run** (`render: soffice`) *also* declared
`visual_rendering`, `visual_redlines` and `visual_accepted_changes`. No other
generating run does, including all three of ours, which declare only
`accepted_changes`, `script_redlines`, `roundtrip`.

Measured consequence: docxodus picked up three extra published rows, two of
them **total wipeouts** (`visual_rendering` n_docs=0 of 20,
`visual_accepted_changes` n_docs=0 of 19), while jubarte carried none and could
not have. A competitor-only zero manufactured by our own configuration is not a
measurement.

Fixed by removing `visual_*` from the generating run; the `docxodus-playwright-*`
runs already cover those oracles properly.

The general rule this yields, added to 6.2: **two vendors are only comparable
when they are asked the same questions.** Differing benchmark *sets* between
runs of the same kind is the same defect class as differing corpora (D1) — it
just hides one level up, in which rows exist at all rather than in how many
documents each row covers.

### 6.2b Checked and cleared (negative results worth recording)

Suspicions that were tested and did **not** hold. Recorded so nobody re-opens
them from first principles, and because a validity chapter that only lists
confirmed defects looks like motivated reasoning.

- **Author-name colour bias — REFUTED.** The Word oracle stamps
  `w:author="Comparison"`, while every tool stamps its own
  (`jubarte-native`, `folio`, `superdoc`, `redlines`, `docx-redline-js`).
  Since LibreOffice colours tracked changes per author, this looked like a
  systematic pixel penalty applied to every vendor for a cosmetic reason.
  Tested directly: one oracle redline was copied twice, differing **only** in
  `w:author`, rendered through the same LibreOffice, and scored against
  itself. Result **100.00**. LibreOffice assigns colour by author *index*, not
  by name, so a single-author document renders identically whatever the author
  is called. No bias, no normalisation needed.

### 6.3 Tasks

**6.3.1 — Corpus symmetry. ✅ DONE 2026-08-04.** Hoisted to a top-level
`corpora:` list in bench.yaml; `config.expand_generate_commands` expands each
run's single `generate:` once per pool. Verified: **12 of 12** `script_redlines`
runs now cover all three pools (was 4 of 12), and all four hand-written 3-chains
are gone. Hardcoding `--manifest`/`--source-dir` in a `generate:` is now
rejected at config load, so the footgun cannot be reintroduced. A run that
genuinely wants one pool declares `corpora: [<name>]`; silence means ALL.
18 tests in `tests/test_corpus_symmetry.py`.

**6.3.1-original — Corpus symmetry.** Give every `script_redlines` run the same
three-manifest chain jubarte-rust has. All generators already accept
`--manifest`/`--source-dir` (verified: `superdoc_gen.py:171`,
`redlines_gen.py:240`, `superdoc_redlines_gen.py:248`, and
`generate-native-redlines.ts:991`), so this is configuration, not code. Better
than replicating a 3× line into every run: hoist the corpus list into the
config and let the driver expand it, so a future fourth pool cannot be added
to one vendor and forgotten on the rest. *Acceptance:* every vendor's
`itt_n_docs` equals jubarte's, or the shortfall is an explicit per-doc failure.

**6.3.2 — Version currency.** Replace fixed pins with **resolve-at-run-date +
record**: bench resolves the latest release, writes the exact resolved version
into the line, and CI reproducibility comes from the recorded version and the
lockfile rather than from a stale ceiling. Requires re-review of each adapter
against the new major (see 6.3.3). *Acceptance:* no vendor more than one
release behind on the run date; `package.json` is never downgraded by a run.

**6.3.3 — Adapter re-review per major bump.** docxodus 7→9, folio-core
0.3→0.15, superdoc-sdk 1→2, superdoc editor 1.44→2.3 are all breaking-change
candidates. One agent per vendor family, in its own worktree, red-green: a
failing smoke fixture first, then the adapter fix. A vendor whose API we
cannot drive after honest effort is recorded `ADAPTER_GAP` with the specific
call that broke — never silently zero.

**6.3.3 status.** docxodus 7.0.0 → **9.0.0** done, including the D5
split-brain fix (pin, root `package.json` and `utils/docxodus/package.json` now
move together, with a test enforcing agreement) and an explicitly named
comparison engine. folio → **core 0.15.13 / react 0.13.2** done, and it
uncovered the retraction recorded in `docs/VENDOR_NOTES.md`. superdoc family
in progress.

**6.3.4 — Install the missing tools.** Clone `superdoc/` and
`superdoc-redlines/`, restore the docxodus local build, fix the `superdoc-ts`
module resolution path. *Acceptance:* zero runs failing with `tool build dir
not found` or `ERR_MODULE_NOT_FOUND`.

**6.3.5 — Re-run the full sweep and publish** with per-subcorpus splits and a
disclosure column.

### 6.4 Disclosure ledger (constraint: do not bury secrets)

Maintained in `docs/VENDOR_NOTES.md`, one row per vendor, published beside the
results:

- **docxodus** — a bug we found was fixed locally and the upstream PR was
  **not accepted**. Consequence: the *published* package still has it. The
  headline benchmarks the published upstream release, because that is what a
  user installs; the patched fork is a separate, clearly-labelled row. Both
  numbers are shown. Benchmarking only the fork would flatter them; benchmarking
  only upstream while sitting on a fix and saying nothing would bury the fact
  that the defect is known and fixable.
- **jubarte (all three engines)** — ours, benchmarked at repo HEAD, with a
  bespoke three-manifest generate chain and the deepest adapter work in the
  repo. Stated plainly: the home team has the home-field advantage in
  integration effort, and 6.2(5) is the remedy.
- Any vendor where we wrote the alignment the tool does not provide
  (`superdoc-redlines` — our `superdoc_redlines_gen.py` supplies the block
  alignment its CLI lacks; `folio` — our adapter composes two headless APIs
  because there is no single compare call) is marked **harness-assisted**,
  because part of the score is our code, not theirs.

### 6.5 Honesty clauses (extend 4.6)

- A failure is attributed to the vendor **only** when their code ran and
  produced the failure. Harness/install/build failures are `UNINSTALLED` or
  `ADAPTER_GAP`, are excluded from the vendor's score, and are reported as our
  gaps. Zero-filling our own breakage as their score is the worst available
  outcome: it is both wrong and self-serving.
- No cross-vendor number ships without its `n` and its `corpus_revision` next
  to it. Two different `n` values in one table is a defect, not a footnote.
- If a fix to our harness moves a competitor's score up, it ships with the
  same urgency as one that moves jubarte's up.

### 6.6 Deferred — noted, deliberately not done now

Per Arthur's constraint, per-fixture nitty-gritty stays recorded and unbuilt
until the validity work lands:

- **`accepted_changes` has ground truth for only one pool.**
  `accepted_ground_truth: corpus/word_based/docx_accepted_word` holds 232 docs
  and covers the word_based pool only; the 400-pair SuperDoc pool has no
  accepted oracle at all. So `accepted_changes` can never reach the 803-pair
  coverage `script_redlines` now has. This is currently harmless — on the
  current corpus no vendor emits an `accepted_changes` row, so nobody is
  advantaged — but it becomes a live D1-class hazard the moment that benchmark
  is re-enabled, because the ITT denominator must then be the pool that HAS an
  oracle (232), never the full 763. Zero-filling 531 documents that have
  nothing to compare against would manufacture failures for every vendor.
  Fix before re-enabling: either build the accepted oracle for the SuperDoc
  pool, or scope the benchmark's corpus explicitly with `corpora:
  [word_based]`.
- Per-fixture point-chasing of the kind worth ~5 score points on a single
  document (e.g. individual `field`/`footer` edge cases from the miner's tail).
- `nupunkt` tokenizer for `redlines` (would raise a text-only baseline;
  currently absent, which is honest but not its best showing).
- Warmed/persistent LibreOffice (Chapter 5 drop-in) — wall-clock only.
- Per-vendor adapter optimisation beyond making the current API work.

Rationale: each is a small, real gain, and every one of them changes a number.
Changing numbers while the measurement is still invalid produces motion, not
progress. Validity first, then the tail.
