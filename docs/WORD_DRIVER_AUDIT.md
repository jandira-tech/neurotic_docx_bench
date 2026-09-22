# Word driver audit

Audit of every script across `neurotic_docx_bench`, `jubarte-first` and `jubarte-redlines`
that drives Microsoft Word for Mac to redline a document or export a PDF.

**Scope:** 21 files. **Read:** 21 Sep 2026, at these revisions: `neurotic_docx_bench`
`a660f32`, `jubarte-first` `e796d8f`, `jubarte-redlines` `ac9d120`. Every cross-repository
citation below (`word-open-check.mjs:324–338` and the like) is a line number **at those
commits**, and two of the three repositories are not the one you are reading this in, so a
line that has since moved should be checked against the pinned revision, not the branch tip.
**Method:** code-path reading, direct measurement of the scripts (open counts, lock-file
entries, set overlaps), and the **committed run artifacts** these pipelines left behind —
`compare.log`, `batch_retry_log.csv`, `source_screen.tsv`, `word_unreadable.txt` and the
output corpora, all tracked in git. No macOS, Word or `osascript` was available here, so
nothing was re-run; where a claim rests on a past run it cites that run's artifact. Every
other claim is traceable to a file and line, to documented Microsoft/Apple behaviour, or is
marked unverified.

---

## 1. Inventory

Not 21 alternative designs. Six generations, and in date order they read as a debugging log.
July is brute force; August names the failure modes; September detects them.

| Family | Date | Files | Job |
|---|---|---|---|
| **A** | 13–15 Jul | Six generated, fully unrolled: `batch_convert.scpt`, `batch_inline.applescript`, `batch_inline2.applescript`, `batch_sanity_pdf.applescript`, `batch_jubarte_lossless_pdf.applescript`, `batch_jubarte_rs_probe_pdf.applescript`. Plus one generic looping script, `batch_word_to_pdf.scpt`, counted separately wherever this document says "family A" or "the six generated batches" | DOCX → PDF |
| **B** | 10 Jul | `run_batch_retry.sh` | Consecutive-pair Word `compare`, per-pair heredoc |
| **C** | 4 Aug | `word_compare_driver.sh`, `word_compare_batch.applescript`, `word_screen_sources.applescript`, `word_dialog_watchdog.applescript` | Manifest-driven compare pipeline |
| **D** | 11 Aug | `render/word.py`, `word_validate_batch.py` | Library renderer + Word-validity gate |
| **E** | 9 Sep | `word-open-check.mjs`, `redline-word-campaign.ts`, `word-convert.sh`, `word-open-probe.sh` | jubarte-first: validity harnesses + converter |
| **F** | 24 Jul / 5 Sep | `word-open-probe.sh`, `word-probe-sweep.sh`, `redline-sweep.sh` | jubarte-redlines: probe + sweeps |

A–D live in `neurotic_docx_bench` (14 files, `render/word.py` under `src/`). E in
`jubarte-first`, F in `jubarte-redlines`.

Excluded as not actually driving Word — they mention it in prose only:
`convert-docx-to-pdf-native.ts`, `measure-redline-parity.ts`, `generate-jubarte-redlines.ts`,
`build-lossless-failure-diagnostic.ts`.

---

## 2. Criteria

Seven scored dimensions. The first three are the original pass; the last four were added
because they are where the corpus actually spends its wall-clock and its credibility.

| | Criterion | Question |
|---|---|---|
| **C1** | Oracle integrity | Does it prove what it saved is what it claims? |
| **C2** | Contamination control | Does one bad file stay one bad file? |
| **C3** | Operational fitness | Can someone else run, resume and audit it? |
| **C4** | Permission-prompt avoidance | Over many files, how many times does a human have to click? |
| **C5** | Malformed-item handling | Is a broken input a logged data point or a wedged run? |
| **C6** | Edge-case preparedness | Lock files, odd filenames, empty dirs, cold Word, slow-but-fine documents |
| **C7** | Concurrency exploitation | Is the parallelism that *is* available actually used? |

Each scored 0–1. Σ is a plain sum out of 7.00 — a ranking device, not a grade.

### Why these three were added to the original three

- **C4** because the whole of family A exists to avoid a permission prompt that, per §5.1,
  was never going to fire.
- **C5** because the corpus's own measured cascades are malformed-item failures: the
  223-file screen where one poison document took 203 others with it
  (`word_screen_sources.applescript`'s header, 16–20; §5.20), and the
  34-real-then-88-phantom probe sweep (§5.8).
- **C6/C7** because 102 of family A's work items are lock files (§5.5) and because the one
  place real parallelism is available — Rust redline generation in `redline-sweep.sh` — runs
  serially.

---

## 3. Scorecard

| File | Repo | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Σ | Tests |
|---|---|---|---|---|---|---|---|---|---|---|
| `word_compare_driver.sh` | ndb | 0.85 | 0.90 | 0.85 | 1.00 | 0.95 | 0.95 | 0.75 | **6.25** | none |
| `word_compare_batch.applescript` | ndb | 0.85 | 0.90 | 0.80 | 0.90 | 0.85 | 0.90 | 0.50 | **5.70** | none |
| `word_screen_sources.applescript` | ndb | 0.95 | 0.90 | 0.80 | 0.85 | 1.00 | 0.75 | 0.40 | **5.65** | none |
| `word-open-check.mjs` | jf | 0.85 | 0.65 | 0.90 | 0.70 | 1.00 | 0.75 | 0.40 | **5.25** | 19 |
| `word_dialog_watchdog.applescript` | ndb | 0.70 | 0.90 | 0.80 | 0.15 | 0.70 | 0.70 | 0.80 | **4.75** | none |
| `word-convert.sh` | jf | 0.35 | 0.70 | 0.80 | 0.95 | 0.90 | 0.65 | 0.30 | **4.65** | none |
| `word_validate_batch.py` | ndb | 0.70 | 0.80 | 0.85 | 0.25 | 0.85 | 0.70 | 0.30 | **4.45** | none |
| `render/word.py` | ndb | 0.75 | 0.65 | 0.90 | 0.25 | 0.80 | 0.80 | 0.25 | **4.40** | 15 |
| `redline-word-campaign.ts` | jf | 0.80 | 0.45 | 0.45 | 0.60 | 0.90 | 0.50 | 0.50 | **4.20** | none |
| `word-probe-sweep.sh` | jr | 0.60 | 0.90 | 0.40 | 0.15 | 0.85 | 0.70 | 0.20 | **3.80** | none |
| `run_batch_retry.sh` | ndb | 0.20 | 0.40 | 0.60 | 0.80 | 0.50 | 0.60 | 0.20 | **3.30** | none |
| `redline-sweep.sh` | jr | 0.80 | 0.30 | 0.80 | 0.10 | 0.35 | 0.70 | 0.20 | **3.25** | none |
| `word-open-probe.sh` | jf | 0.35 | 0.40 | 0.70 | 0.10 | 0.50 | 0.45 | 0.20 | **2.70** | none |
| `word-open-probe.sh` | jr | 0.35 | 0.40 | 0.70 | 0.10 | 0.50 | 0.45 | 0.20 | **2.70** | none |
| `batch_word_to_pdf.scpt` | ndb | 0.20 | 0.25 | 0.30 | 0.15 | 0.35 | 0.25 | 0.10 | **1.60** | none |
| `batch_convert.scpt` | ndb | 0.15 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.10** | none |
| `batch_jubarte_lossless_pdf.applescript` | ndb | 0.15 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.10** | none |
| `batch_jubarte_rs_probe_pdf.applescript` | ndb | 0.15 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.10** | none |
| `batch_sanity_pdf.applescript` | ndb | 0.15 | 0.30 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.05** | none |
| `batch_inline.applescript` | ndb | 0.10 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.05** | none |
| `batch_inline2.applescript` | ndb | 0.10 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.05** | none |

`ndb` = neurotic_docx_bench, `jf` = jubarte-first, `jr` = jubarte-redlines.

Scores marked in §14 and §5.14–§5.15 were revised downward after re-verifying the code paths
against the header comments that assert them. **No script in this corpus holds an unreduced
C1.** `word-open-check.mjs` came closest and lost it to §5.15: it is still the only script
that proves its own detector works before trusting a clean result, but its text probe reads
`active document` rather than the document it just matched — the same defect §14.1 docks
`word_compare_batch.applescript` for.

The leaders are not interchangeable: `word_compare_driver.sh` is the best at surviving Word;
`word_compare_batch.applescript` has the best *idea* of how to know what it produced
(identification by exclusion) and implements it one step short (§14.1);
`word-open-check.mjs` is the only one that proves its detector before trusting a clean sweep,
and Σ understates it for that reason — a unique property scores once, like any other.

---

## 4. Where they genuinely differ

| Axis | Positions taken, and by whom |
|---|---|
| **Script delivery** | Monolithic unrolled (family A, one `osascript` for 200–1,224 files) · per-file heredoc (`run_batch_retry.sh`, `word-convert.sh`) · script file with argv (family C) · `osascript -e` with argv (`render/word.py`, the TS/MJS harnesses) |
| **Sandbox staging** | App container `~/Library/Containers/com.microsoft.Word/Data/tmp` (`run_batch_retry.sh`, `word-convert.sh`) · Group container `~/Library/Group Containers/UBF8T346G9.Office` (`word_compare_driver.sh`) · deliberately outside (`redline-word-campaign.ts`, `word-open-check.mjs`) · none (family A, `render/word.py`, the probes) |
| **Alert strategy** | `displayAlerts false` only (families A and C) · UI detection only (`word-convert.sh`, the TS/MJS harnesses) · both (family C, via the watchdog) · neither (`run_batch_retry.sh`, `render/word.py`, the probes) |
| **Result identification** | `active document` / `front document` (family A, `run_batch_retry.sh`, `word-convert.sh`, `render/word.py`) · indexed by exclusion (`word_compare_batch.applescript`) · document count must rise (`redline-word-campaign.ts`) · window named for this file (`word-open-check.mjs`) |
| **Poison recovery** | None (family A) · close-all between items (`run_batch_retry.sh`) · quit + `pkill -x` + relaunch-poll (`word_compare_driver.sh`) · quit + `pkill -x` then **exit**, leaving the next invocation to cold-start Word (`word-convert.sh`: `reset_word_after_failure` is followed by `record_error` and `exit`, 225–228 and 257–259) · plus AutoRecovery wipe (`word-probe-sweep.sh`, the only one) · kill-after-each-failure (`word_validate_batch.py`) |
| **Focus behaviour** | Bare `activate`, no bouncer (`word-convert.sh`) · bouncer, never activates (`redline-word-campaign.ts`) · `open -g` background launch (`word-probe-sweep.sh`) · unaddressed (everything else) |
| **Compare semantics** | `detect format changes true` (`word_compare_batch.applescript` only, with a written warning never to flip it mid-corpus) · omitted (`run_batch_retry.sh`). Both pass `ignore all comparison warnings true` |
| **Resume** | None (family A) · output exists (`run_batch_retry.sh`, `render/word.py`, `word_compare_batch.applescript`) · log + output cross-check with same-run failure accounting (`word_compare_driver.sh`, the only one that provably terminates) |

---

## 5. Findings

Ordered by cost if left alone.

### 5.1 The permission-prompt premise behind family A does not hold

`CLAUDE.md` rule 1 says to generate one monolithic inline `osascript` for a whole batch,
because *"macOS asks the automation-permission dialog once **per osascript process** → N
files = N prompts."* That is the stated reason six generated scripts totalling ~1.2 MB exist.

It conflates two unrelated prompts:

1. **TCC Apple-events automation.** Granted as a triple of (responsible client app, service,
   target app) and persisted in TCC.db. For `osascript` run from a terminal, the responsible
   client is the terminal, not the `osascript` process. One grant covers every later
   invocation. `word_compare_driver.sh:64–72` states this correctly — *"macOS shows exactly
   one dialog; approving it persists. Every later run is silent"* — and the script's own
   behaviour corroborates it: it spawns a fresh `osascript` per batch chunk, per restart,
   per precondition probe, and never mentions a repeated prompt.
2. **Word's own "Grant File Access" sandbox sheet.** Raised by Word's sandbox when it reads
   or writes outside its container. This one *is* per file (§6.1), and it is the one
   that container staging solves.

Rule 1's arithmetic belongs to prompt 2; its mechanism is attributed to prompt 1. The
consequence is that per-file `osascript` invocation was ruled out on a false basis, and
per-file invocation is what buys per-file timeouts, per-file error attribution and
shardability — exactly the three things family A lacks.

**Action:** correct the rule to *"one TCC consent per (responsible client app, target app)
pair — for `osascript` from a terminal, that is the terminal — which persists until it is
revoked in System Settings, reset with `tccutil reset AppleEvents`, or invalidated by the
client being re-signed; stage inside the container to avoid the sandbox sheet"*, and stop
generating unrolled scripts.

### 5.2 The `-1708` rule is confounded, and only two of its four cells have run evidence

`corpus/word_based/docx_redlines_word/README.md` and `CLAUDE.md` both state the rule as
*inline heredoc works, `.scpt` file fails with `-1708`*. But the broken example they cite
uses `active document`, and `word_compare_batch.applescript` — a **file** run as
`osascript word_compare_batch.applescript …` — calls `save as cmpDoc` on an explicitly
indexed `document i` rather than on `active document` — and that combination is one of the
two with committed run artifacts behind it (`compare.log`, below). The cell the README's
rule actually indicts is never logged anywhere.

Two data points, one confound:

| | `active document` | `document i` |
|---|---|---|
| **inline** | works (`run_batch_retry.sh`, `word-convert.sh`) | — |
| **file** | reported `-1708` (`compare-documents.scpt`) | **works** — 529 `[ok]`, 400 outputs (`word_compare_batch.applescript`) |

The `document i` + file cell rests on committed artifacts.
`corpus/word_redlines_superdoc/compare.log` (tracked, 1,188 lines) records **529 `[ok]`**
entries and five `[done] processed=N ok=N fail=0` summaries against 9 `[fail]`, and
`corpus/word_redlines_superdoc/docx_redlines_word/` holds **400 `.docx`** outputs. Those
artifacts are **consistent with** `save as cmpDoc file name outP file format format document`
succeeding from a script **file**: the `[ok] <pairId>` and `[done] processed=… ok=… fail=…`
lines are exactly the format `word_compare_batch.applescript`'s `logLine` handler emits, and
`word_compare_driver.sh:239` invokes that script as `osascript <file>`. Both halves of that
are read off the current source.

What the artifacts do **not** record is the invocation or the script revision in force at run
time. So this is a chain of inference from code plus output, not a run transcript: it does
not exclude those outputs having come from an inline variant, an earlier revision, or a hand
run. Treat it as strong corroboration of the `document i` + file cell, not as proof of it.
(529 `[ok]` against 400 files is expected: the log is append-only and outlives the manifest, which is exactly why the driver
requires `[ok]` *and* an existing redline before counting a pair done.)

The inline + `active document` cell has its own artifact:
`corpus/word_based/docx_redlines_randomized/batch_retry_log.csv` (tracked) records 200 pairs,
196 `ok`, 4 `fail`, with per-pair durations — and 196 matching `.docx` outputs sit beside it.

Be exact about what each cell rests on, because the three kinds of evidence are not
interchangeable:

- **Two cells have committed run artifacts**, and both of them *work*: inline +
  `active document` (`batch_retry_log.csv`) and file + `document i` (`compare.log`).
- **One cell is a second-hand report**: file + `active document` was *reported* to fail with
  `-1708` in the corpus README. No log records it, and the script said to have failed
  (`compare-documents.scpt`) is not in the tree.
- **One cell is unobserved**: inline + `document i`. Nothing has ever been run there.

So the run logs do not isolate the failure. What they establish is that two combinations
work; the failure's location rests entirely on the README's report. Reading the table with
that caveat carried through:

- Holding **file** constant: `document i` works (logged), `active document` was reported to
  fail. If the report is right, the selector matters when running from a file.
- Holding **`active document`** constant: inline works (logged), file was reported to fail.
  If the report is right, file-vs-inline matters when targeting `active document` — which is
  the README's own rule, in the one row where it could be tested.

Under that same *if*, one thing is ruled out and nothing is ruled in. Neither factor acts
**alone**: a pure `active document` effect would make inline + `active document` fail, and it
works; a pure `file` effect would make file + `document i` fail, and it works. But ruling out
two models does not establish a third. Three cells cannot identify four parameters, so the
matrix cannot distinguish an interaction from anything else — the reported failure is
*consistent with* an interaction, which is not the same as sitting on one.

A larger hole sits outside the matrix. `compare-documents.scpt` is not in the tree — and
not merely untracked now: it appears in **no commit in the repository's history**
(`git log --all -- '*compare-documents*'` returns nothing, and no tree in the history
contains a blob by that name). The corpus README lists it and `compare-documents-fixed.scpt`
in a file table as though they sit in `scripts/`; neither was ever committed. The README also
ties the failure to a specific build, **Word 16.112**.

So there is no way to confirm the failing script differed from the working ones *only* along
these two axes — a third difference, in its content or in the Word build, would put the cause
outside this 2×2 entirely.

So the classification stays open. An earlier draft claimed the evidence identified
`active document` as the cause, and a later one claimed the failure sat on the interaction;
both overreached and both are withdrawn. Nothing here licenses rewriting
`batch_word_to_pdf.scpt` or deleting family A.

Four runs bound it, as two pairs. From a **file**, the same `save as` against
`active document` and once against `document 1` — that tests the selector. Then the same
pair **inline**, which fills the empty cell and tests file-vs-inline. Only both together
separate the two factors.

Be clear about what that buys, though: it characterises the selector and file-vs-inline **on
the machine and Word build that runs it**. It cannot validate the `-1708` report, because the
script that produced it does not exist to re-run and the report is pinned to Word 16.112. A
clean four-run result would mean the README's rule does not hold *here*; it would not explain
what happened *there*. So if file-vs-inline turns out not to be the variable, what follows
is bounded the same way: `batch_word_to_pdf.scpt` is repairable **on the tested machine and
build**. That is not a finding about family A. The script whose failure prompted the rule
was never committed and the report is pinned to Word 16.112, so four runs here cannot
establish what failed there, and this experiment is not grounds for removing family A.

### 5.3 Two scripts say to stage inside Word's container; two say the opposite, both with reasons

`CLAUDE.md` rule 3 and `word_compare_driver.sh` are emphatic: stage inside the container, a
repo path costs a Grant-File-Access dialog per file (*"three clicks for one pair, ~1200 for
the corpus"*). `redline-word-campaign.ts:110–115` stages **outside** on purpose, recording
that writing many files into Word's sandbox tmp and reopening them rapidly intermittently
yields `"Word experienced an error trying to open the file"` — a file-*access* error, not a
content one. `word-open-check.mjs` inherits that choice by name.

Both claims are plausible; they cannot both be the general rule. It also matters *which*
container: family B and `word-convert.sh` use the app container
(`~/Library/Containers/com.microsoft.Word/Data/tmp`), family C uses the Group container
(`~/Library/Group Containers/UBF8T346G9.Office`), and nothing explains the difference.

**§6.1 resolves this, and it resolves toward staging.** `CLAUDE.md` rule 3's *arithmetic*
was right even though its neighbouring claim about folder grants persisting was not: because
a grant only persists once its panel has been completed — which requires Word frontmost
(§6.1) — an out-of-container batch whose handler does not activate Word pays a prompt **per
file**. That is 232 prompts for `batch_convert.scpt` and 1,224 for
`batch_sanity_pdf.applescript`, none of which have a handler at all. Staging is the only
strategy that makes the prompt not happen rather than answering it, and the only one that
needs neither the Accessibility grant nor a focus interruption.

That does not make the outside-stagers wrong about *their* problem. The file-access error
they recorded under rapid sandbox-tmp reuse is a real report, and staging into one shared
container directory is what provokes it. The two constraints are not actually in conflict,
and one script goes part of the way: `word-convert.sh` stages inside the app container
**and** takes a fresh `mktemp -d` per run, so no two runs reuse a path. That pattern — inside
the container, unique subdirectory per run, cleaned on exit — is what §5.3 should have
recommended from the start.

**It does not, however, clear the reported trigger, and this document should not claim it
does.** `word-convert.sh` converts **one file per invocation**, so its fresh directory holds
exactly one document; what the outside-stagers reported is many files written into one
sandbox-tmp directory and reopened rapidly. That workload never runs under
`word-convert.sh`. It does run under the monolithic default, which stages the whole folder
before the first open — §15's "One osascript for the whole job" puts it at 1,224 copies
live in the container for a
1,224-document run. Unique-per-run removes *cross-run* reuse and nothing more; whether
many-files-in-one-directory provokes the error **within** a run is untested here and needs
the target machine. If it does, the answer is a subdirectory per item, not per run.

What stays open is narrower and much cheaper: **which** container. Family B and
`word-convert.sh` use the app container
(`~/Library/Containers/com.microsoft.Word/Data/tmp`), family C the Group container
(`~/Library/Group Containers/UBF8T346G9.Office`). Both are in Word's entitlements and
neither prompts; nothing in the corpus explains the choice, and nothing so far suggests it
matters.

### 5.4 `run_batch_retry.sh` can save a base document as a redline, silently

It runs `compare` without `detect format changes`, so a pair differing only in font, spacing
or table properties produces no revisions at all — and then `save as front document` saves
whatever is frontmost, which in that case is the base. The output opens cleanly in Word,
carries zero revisions, and scores as ground truth.

`word_compare_batch.applescript` fixes exactly this twice over (lines 88–98 and 100–114) and
its comments say so. `validate_word_redlines.py` catches it downstream by requiring at least
one `w:ins` / `w:del` / `*PrChange` — but only for corpora that run through that validator.

### 5.5 The six generated batches overlap; they are re-generations, not a split

Measured directly from the scripts:

| Script | Opens | `~$*.docx` lock-file entries | Source dirs | Lines |
|---|---|---|---|---|
| `batch_convert.scpt` | 232 | 0 | 1 | 2,325 |
| `batch_inline.applescript` | 241 | **18** | 1 | 2,413 |
| `batch_inline2.applescript` | 244 | **84** | 1 | 2,443 |
| `batch_jubarte_lossless_pdf.applescript` | 207 | 0 | 1 | 2,074 |
| `batch_jubarte_rs_probe_pdf.applescript` | 207 | 0 | 1 | 2,074 |
| `batch_sanity_pdf.applescript` | 1,224 | 0 | 6 | 12,243 |

The first three read the same source directory and write the same output directory. All 232
of `batch_convert`'s files appear in `batch_inline`; `batch_inline` and `batch_inline2` share
211 files. None skips an existing PDF, so running the set re-renders the same ~200 documents three
times.

102 of those work items are `~$*.docx` Word owner/lock files — not documents. Each costs a
full AppleEvent timeout and produces nothing. `word-probe-sweep.sh:9–11` names this exact
trap as one of the four it was written to avoid.

`batch_sanity_pdf.applescript` is a single un-resumable run of 1,224 opens across six
directories. At the ~2–3 s/doc that `CLAUDE.md` records, that is 40–60 minutes with no
checkpoint.

### 5.6 `batch_word_to_pdf.scpt` never closes a document on failure

Its `on error` branch echoes and moves on. All six unrolled scripts do
`close every document saving no` in their error branch; the generic looping version — the one
worth keeping — does not. Word accumulates open failed documents for the rest of the run,
which is precisely the state `word_compare_batch.applescript:120–122` closes after every pair
to avoid. Line 3's `set srcDir to POSIX file (item 1 of argv) as alias` is also dead:
`srcDir` is never read.

### 5.7 `word-probe-sweep.sh` hardcodes a path to one machine's checkout

`PROBE="/Users/arthrod/temp/T/jubarte-redlines/scripts/word-open-probe.sh"` (line 20). The
file next to it, `redline-sweep.sh:42`, derives `SCRIPT_DIR` correctly. Its usage string also
names a script that does not exist (`word_probe_all.sh`). Separately, `pkill -9 -f 'Microsoft
Word'` matches on the full command line where `word_compare_driver.sh` uses the safer
`pkill -x`.

### 5.8 `redline-sweep.sh` has the cascade bug its own sibling documents the fix for

`--probe` loops `word-open-probe.sh` over every artifact with no kill, no warm-up and no
dialog handling. That is exactly the naive loop `word-probe-sweep.sh`'s header describes —
*"34 real opens, then 88 phantom failures"* — sitting in the same `scripts/` directory. One
failing redline mid-sweep turns the rest of the run into noise.

### 5.9 jubarte-first violates its own focus rule, in the directory where it implements it

`CLAUDE.md` requires a concurrent bouncer whenever Word is activated, and prefers `launch` +
`AXPress` with no activation at all. `redline-word-campaign.ts:182–206` implements the
bouncer exactly, cites the rule, and never activates. `word-convert.sh:148` — same repo, same
folder — calls a bare `activate` on every conversion, with no bouncer anywhere.

### 5.10 Path handling ranges from injection-proof to injection-prone

- **Safe by construction (argv):** `word-convert.sh` passes paths as `argv` into a quoted
  heredoc and says so in its header. `render/word.py` does the same —
  `["osascript", "-e", _APPLESCRIPT, str(docx.resolve()), str(pdf.resolve())]` against an
  `on run argv` handler (59, 25–27). In both, the path never appears in AppleScript source.
- **Source-escaped, and not argv:** the two TS/MJS harnesses. An earlier revision of this
  document grouped them with the row above; that was wrong. Both call
  `execFileSync("osascript", ["-e", script])` with nothing after the script
  (`word-open-check.mjs:257`, `redline-word-campaign.ts:51`) and build `script` by embedding
  paths through `JSON.stringify`. The argument array rules out *shell* injection, and JSON
  string syntax does escape safely into an AppleScript literal, so this is sound as written.
  But the safety is the escaper's rather than the interpreter's, which is a weaker guarantee
  than it looked: argv cannot be undone by editing the script text, and this can.
- **Hand-escaped:** `word-open-probe.sh` escapes backslash then quote (correct as far as it
  goes; a newline in a filename still escapes the literal). Its second argument `$delay` is
  interpolated into the script body unvalidated.
- **Interpolated raw:** `run_batch_retry.sh` (`$fname` straight into an AppleScript string
  literal) and all six generated batches.

### 5.11 Three ideas here are better than the state of the art and are used once each

- **The negative control.** `word-open-check.mjs` builds a deliberately corrupt DOCX
  (truncated `word/document.xml`), opens it first, and requires the repair dialog to be
  observed; `computeExitCode` returns 1 rather than 0 on a clean sweep whose detector was
  never proven. A clean result from a blind detector is not a pass. Nothing else in the
  corpus has a negative control.

  **With one opt-out, and it is deliberate.** The guard is
  `if (meta.selftest && !meta.selftest.detectorProven) return 1;` (237), so it only fires
  when a self-test ran at all; under `--no-selftest` (47) `meta.selftest` is absent and a
  clean sweep returns 0 with the detector unproven.

  That is not a hole someone left open — it is written into `computeExitCode`'s own contract,
  which defines exit 0 as *"every probed file OPENED-CLEAN with the detector proven (**or an
  explicit `--skip-word` / `--no-selftest` run that produced no failing verdict**)"*
  (`word-open-check.mjs:226–227`, in the docstring at 216–228 directly above the function).
  An operator who passes the flag has asked for the control to be skipped, and gets what they
  asked for. The one operational consequence worth knowing: the console warning at 1029 is
  guarded by the same `meta.selftest &&`, so a `--no-selftest` run says nothing about the
  detector either way. Its exit 0 means "nothing failed", not "a blind pass was excluded" —
  a distinction that matters if such an invocation is ever wired into CI as a gate.
- **Filename-verified dialogs.** `redline-word-campaign.ts` requires the dialog text to name
  *this* file, killing false positives from stale dialogs, and requires the document count to
  rise before returning CLEAN, killing the false negative the comment records as having
  masked CU003 in the first run.
- **Identification by exclusion.** `word_compare_batch.applescript` walks `document i` and
  takes the one whose name is not the base's. Its own comment (100–102) gives the reason as
  "if compare silently produced nothing, `active document` is still the BASE, and saving that
  as [the result]". **That premise is wrong, corrected from the target machine:** `compare`
  yields its result as a *new* document, and that new document, as created, is the redline.
  Because it is unsaved, Word prompts for a location unless the caller supplies one. The
  technique survives the correction — naming the document you mean beats taking whichever is
  frontmost (§5.18) — but it is good practice rather than a guard against that failure, and
  §15's pair states it that way. It also notes that `repeat with d in documents` makes
  AppleScript send `count` to `every document`, which that Word build rejects outright.

### 5.12 Two of 21 have tests, and both test the right thing

`word-open-check.mjs` exports `REPAIR_DIALOG_RE`, `parseUiLines`, `windowAlertTexts`,
`findDialogs` and `computeExitCode` as pure functions, covered by **19** specs in
`tests/scripts/word-open-check.spec.ts` that run on Linux with no Word present.
`render/word.py` does the same with `_budget`, `_interpret_modal_probe` and
`_interpret_open_exit`, covered by 15 tests including
`test_budget_exhausted_without_modal_is_unjudgeable`.

**That is not the whole verdict-deciding surface, and this document previously said it
was.** `supervisedOpen()` is the function that actually chooses between OPENED-CLEAN,
REPAIR-PROMPT, ERROR and BLOCKED, and it is neither exported nor imported by the spec, which
pulls in only those five helpers. Its orchestration — UI collection, unknown-modal draining,
window matching, late-sheet handling — is unproven off-platform, so a regression that
wrongly returns OPENED-CLEAN would pass every one of these tests. What is testable
off-platform is the *predicate layer* under the verdict, which is still the right layer to
have isolated. The
pattern transfers directly: `word_compare_driver.sh`'s done-accounting and stall arithmetic
are pure text processing and are currently proven only by having been run.

### 5.13 Smaller things

- `render/word.py`'s `WordRenderer.to_pdfs` accepts `jobs: int = 12` and never uses it. The
  signature mirrors `soffice.py`'s `Renderer` protocol, which *does* honour it with a
  `ThreadPoolExecutor`. The comment explaining why Word must be serial is right; the
  signature still advertises throughput that is not there.
- `redline-word-campaign.ts`'s `--word-sample N` takes the first N pairs (`i <= wordSample`),
  not a sample; on an alphabetically ordered corpus that is a biased subset. `PROBE_DIR` is
  `process.cwd()`-relative, so it silently writes elsewhere when invoked from another
  directory.
- **`--word-sample` turns a malformed value into a silent clean pass.**
  `Number.parseInt(args[sampleIdx + 1], 10)` (223) yields `NaN` for a missing or
  non-numeric value and keeps `0` or a negative one. Every downstream test is
  `wordSample > 0` — `willProbeWord` (235) and the per-row `wantWord` (266) — and all of
  them are false for `NaN`, `0` and negatives alike. So `--word-sample` with nothing after
  it marks every row `SKIPPED`, leaves `wordBad` at zero, and exits **0**: an operator who
  explicitly asked for Word validation is told the corpus is clean without a single
  document having been opened. The file already knows the idiom — `wordDocCount` guards
  the identical call with `|| 0` (59) — it is this one argument that does not. A positive
  integer should be required, and anything else refused.
- **The validation scratch path collides between concurrent runs.** Every pair is written
  to `redline-out/_validate/v-${i}.docx` under `process.cwd()` (258–262) with `i` the
  1-based loop index, and `validate()` is awaited *after* the write. Two campaigns started
  from one working directory both begin at `v-1.docx`, so either can overwrite the other's
  file in the window between `writeFileSync` and the read — and the errors then come back
  attributed to the wrong pair. This is the same `process.cwd()` assumption as `PROBE_DIR`
  above, with a worse failure: not output in the wrong place, but a verdict against the
  wrong document. A per-run temporary directory fixes both. Until then the pure-TypeScript
  phase is not safely shardable, which is worth stating because §9 marks it as the one
  genuinely parallelisable step in the corpus.
- `word-open-probe.sh` exists twice, byte-identical apart from an SPDX header and one word,
  in two repos with different licences (GPL-3.0-only and AGPL-3.0-only). No shared source, so
  they will drift.
- **`word-open-check.mjs` has the same unscoped `drainDialogs()` this document docks
  `redline-word-campaign.ts` for.** Lines 324–338 walk every Word window whose subrole is
  `AXDialog` and press `No`, `OK` or `Cancel`, with no filename test, and it runs before
  probes, on unknown modals, after every file and in final cleanup. Closing only `q4woc-*`
  documents does not make it isolated, for the same reason it does not make the campaign
  isolated. An earlier revision of this section criticised one script and credited the other
  for identical code.
- **The campaign's own cleanup may close nothing at all.** It uses
  `repeat with d in (every document)` (`redline-word-campaign.ts:169`) — the exact construct
  `word-open-check.mjs:744–748` records as rejected by this Word build with `-1708`
  ("every document doesn't understand the count message"), recommending descending indexed
  iteration instead. The loop is wrapped in `try` and `osa()` swallows errors, so the failure
  is silent and every probe document stays open to contaminate the next. One repo documents
  the defect and the sibling commits it.
- **An empty worklist is indistinguishable from a clean sweep.** For a valid `pairs.json` of
  `[]` the campaign loop runs zero times and exits 0, because `crashed + valErr + wordBad`
  is `0` (`:314`) and nothing checks `pairs.length`. A worklist that failed to generate
  reports as a fully successful validation.
- **The campaign has no platform preflight.** Run with `--word` on Linux, or on a Mac
  without `osascript`, `osa()` catches the spawn failure and returns `""`, `wordDocCount()`
  reads that as zero, both attempts expire and every valid artifact is recorded UNREADABLE.
  The conservative default corrupts the results instead of reporting that the oracle is
  absent; it needs an early BLOCKED-style exit.
- **`word-open-check.mjs` records a failed UI inspection and then ignores it.** `row.uiError`
  is set at `:582` and read nowhere. If Accessibility is revoked after the initial check and
  the post-settle `collectUi()` fails, a successful `activeDocText()` still yields
  OPENED-CLEAN, certifying a document nobody checked for a late warning sheet. A UI-probe
  failure should propagate as BLOCKED, which is the verdict the taxonomy already has.
- **`word-convert.sh` assumes an external `timeout` exists.** `WORD_CONVERT_TIMEOUT_CMD`
  defaults to a bare `timeout` (`:55`) with no `command -v` check anywhere in the file, and
  neither its header nor the repo setup documents the dependency. macOS does not ship one
  under that name by default. Absent it, the conversion and every recovery invocation fail
  identically with command-not-found.
- `word-open-check.mjs`'s `makeCorruptControl()` runs `rm -rf` unconditionally on
  `<artifacts>/q4woc-00-corrupt-control.docx.unpacked` (530–531) before building the control.
  Nothing establishes that the directory is this run's, so a pre-existing one under that name
  is destroyed. `mkdtemp`, or refusing a path that already exists, costs nothing. Same class
  as §12 step 4: a name is not ownership.
- `redline-word-campaign.ts`'s `drainDialogs()` (63–78) walks **every** Word window whose
  subrole is `AXDialog` and presses `No`, `OK` or `Cancel`, with no filename check, before and
  after each probe. Closing only `campaign-*` documents does not make it isolated: with a
  human's Word session open it can decline their recovery prompt or dismiss their modal. It
  needs the no-open-documents preflight, or filename-scoped matching like the one it already
  applies to its verdicts.
- `redline-word-campaign.ts` writes `${p.label.replace(/[^a-z0-9]+/gi, "-")}.docx` (257), so
  two labels differing only in punctuation (`A/B` and `A-B`) normalise to one filename. The
  later pair silently overwrites the earlier while the report still lists both rows, and
  nothing records which artifact survived. An index prefix, or rejecting duplicate normalised
  names, fixes it.
- `CLAUDE.md` cites `report_one/scripts/compare-docs.sh` and
  `report_one/scripts/redline-word-pdf.py` as the proof for the focus-bouncer recipe. Neither
  file, nor a `report_one/` directory, exists in any of these three checkouts — that claim
  could not be verified here.

---

### 5.14 `word-convert.sh` can report a conversion it never performed

`docx` is a supported output format (40; the usage line offers
`<output.{pdf,html,rtf,docx}>`), and both staged paths are derived from basenames into one
directory:

```sh
word_in_abs="$stage_dir/$(basename "$in_abs")"    # 52
word_out_abs="$stage_dir/$(basename "$out_abs")"  # 53
cp -p "$in_abs" "$word_in_abs"                    # 54
```

So `word-convert.sh in/deal.docx out/deal.docx` resolves both to `$stage_dir/deal.docx`, and
line 54 creates the supposed output before Word has been asked for anything. The poll that
waits for the conversion is `if [ -f "$word_out_abs" ]; then break; fi` (172), true on its
first pass. `wait` then discards the AppleScript's exit status, and the final branch copies
`$word_out_abs` — still the unmodified input — to the destination and prints `saved`
(249–250).

The result is a successful-looking no-op: the caller gets its own input back under the output
name, with exit 0 and no error file. `rm -f "$out_abs"` at 47 clears the *destination* before
starting, which is what C6 credited; the staged output has no equivalent guard, and the
staged one is what both the poll and the copy read. A distinct staged output name, or a
second `mktemp -d`, closes it.

C1 drops to 0.50. A converter that cannot distinguish "finished" from "never started" is not
an oracle, whatever else it does well.

### 5.15 `word-open-check.mjs` reads the text of whichever document is active

`supervisedOpen()` locates the target's window by filename and holds it as `docWin`, then
asks for the text through `activeDocText()` (680–681). All three of that function's probes
are bound to `active document`:

```applescript
content of text object of active document   -- 461–463
content of active document                  -- 464
count of characters of active document      -- 466–468
```

Nothing ties the answer back to `docWin`. If Word is already running with another non-empty
document, or if focus moves between the window match and the text probe, that unrelated
document satisfies the non-empty check and an empty target is recorded OPENED-CLEAN.

This is the defect §14.1 docks `word_compare_batch.applescript` for and §5.11 praises its fix
for: name the document you mean, or find it by exclusion, but never take whichever one is
frontmost. The negative control is not a substitute. It proves the repair dialog *would* be
seen; it says nothing about which document got measured once no dialog appeared.

C1 drops to 0.85 — below `word_screen_sources.applescript` at 0.95, but still above
`redline-word-campaign.ts`, which §5.18 docks to 0.80 for taking a risen count as proof
without a content check.

What survives the cut is the property no score captures and no other script has: it is the
only one here that proves its detector works before it trusts a clean result. That is still
the reason §13 keeps it.

---

### 5.16 `word-open-probe.sh` certifies the wrong document, and condemns the right one

The probe's whole verdict rests on a global count:

```applescript
if (count of documents) > 0 then          -- 31
  set theName to name of active document  -- 32
  close active document saving no         -- 33
  return "OPENED: " & theName             -- 34
```

Nothing checks that the count *rose*, and nothing ties `active document` to the file just
asked for. With a human's document already open, an `open` that silently adds nothing —
the false-clean shape §5.15 and §14.1 both describe — leaves `count of documents` at 1, and
line 32 reports the human's document as the successful probe of ours. Line 33 then closes
it `saving no`, so the same bug that fabricates a pass also destroys the evidence and the
person's unsaved edits.

A count taken before the open and compared after, or matching by name as
`redline-word-campaign.ts` does for its verdicts, settles both halves. That is **one** class
of oracle defect, a false positive, and on its own it takes C1 to 0.45 and C6 to 0.45 in
both copies of the file. The paragraph below adds a second class and moves C1 again.

**The missing grant handler is an oracle defect too, not only a permission cost.** The
script has no handler at all, so on a folder Word has not been granted the `open` sits
behind the Powerbox sheet until the 60-second `with timeout` expires; the `on error` branch
returns `ERROR <n>: <msg>` and the script exits non-zero. `redline-sweep.sh --probe`
consumes that as a failed document. It is not one. `AGENTS.md`'s own definition of Word
valid is explicit that *"when there is a requirement to provide more permissions by Word,
such requirement would not render such file not Word valid"* — so the probe converts a
permission state into a verdict against the file, and a whole ungranted folder reads as a
corpus of broken documents. That is the same class of error as §5.15's and this section's
false *positives*, pointing the other way: a false negative, produced by the absence of a
handler rather than by binding to the wrong document. The fix is either to answer the grant
(with Word frontmost, per §6.1) or to return a distinct `BLOCKED` verdict that the sweep does
not count as invalid. The permission cost stays filed under C4; this half belongs to C1.

**So C1 is recomputed, not stretched.** An earlier revision of this section said the 0.45
above was "already low enough to carry it", which was circular: 0.45 was derived from the
false-positive class alone, before this second class had been identified at all, so it
cannot have accounted for it. The script now carries **two independent oracle defects in
opposite directions** — it certifies a document that is not the one it asked for, and it
condemns a document that is fine. This document already prices that combination: §5.14 and
§5.19 give `word-convert.sh` **C1 0.35** for exactly two such classes. The probe gets the
same, in both copies: **C1 0.45 → 0.35**, Σ 2.80 → 2.70. C6 is untouched at 0.45, because
the edge case it prices — a human's documents already open — is the false-positive half
only; an ungranted folder is not an edge case the probe mishandles, it is one it never
handles.

### 5.17 The campaign's 20-second timeout does not bound anything

`redline-word-campaign.ts`'s `osa()` is `execFileSync("osascript", ["-e", script], {
encoding: "utf-8", timeout: 20000 })` (49–51), and `attempt()` calls it for the open before
any grant or dialog handling can run. `execFileSync` sends `killSignal` on timeout, which
defaults to `SIGTERM` — the one signal §14.2 establishes a blocked `osascript` ignores.

Measured rather than assumed, with a child that ignores `SIGTERM`:

```
$ node -e '…execFileSync("node", ["-e", ignoreSigterm], {timeout: 1000})…'
threw: ETIMEDOUT
elapsed_ms: 10047   (timeout was 1000)
```

The call blocked for the child's full lifetime and only then reported a timeout. So a Grant
File Access sheet or a repair modal hangs the campaign outright: the retry and the 16-second
poll are never reached, because nothing returns. The right rating is not "too short" but
"not a timeout"; `killSignal: "SIGKILL"`, or an asynchronously supervised child, is what
would make the number mean something. C3 drops to 0.45.

**The 45-second budget in `word-open-check.mjs` is not a per-file budget either.** It bounds
the UI poll only (`:577`). Once the window is seen, `activeDocText()` may run three
sequential `osa(..., 30000)` calls (`:472`), after the settle and post-UI probes, so a file
whose text Apple events wedge can consume well over two minutes while the table advertises
45 s. Either account for the post-open probes or put one deadline across `supervisedOpen()`.

**The contrast with `render/word.py` is exact and worth keeping.** Python's
`subprocess.run(timeout=…)` calls `Popen.kill()` — `SIGKILL` — on its own child, which is
why §14.2 credits that shape. Node's synchronous helper does not. Two languages, the same
API shape, opposite guarantees.

---

### 5.18 Four scripts act on whichever document Word happens to have

This is the single most repeated defect in the corpus, and this document found it one script
at a time instead of naming it once. Collected:

| Script | What it binds to | What that costs |
|---|---|---|
| `word-open-check.mjs` | `active document` in `activeDocText()` (§5.15) | an empty target reads as OPENED-CLEAN off another document's text |
| `word-open-probe.sh` | `active document` off `(count of documents) > 0` (§5.16) | certifies a stranger's document as our probe, then closes it unsaved |
| `word-convert.sh` | `active document` on the **normal** conversion path (147–160) | saves the stranger's document into our output, closes it, deletes it with the staging directory, and reports success |
| `redline-word-campaign.ts` | a count that rose, with no content check (145–156) | an openable but empty engine output gets the campaign's strongest verdict |

The `word-convert.sh` row is the one this document had not reached. §5.14 covered the staged
path collision and §11 covered the reset; the ordinary happy path has the same flaw and worse
consequences, because it does not merely mis-report. After `open POSIX file inPath` and a bare
`delay 3`, it runs `save as active document file name outPath` and then
`close active document saving no`. Nothing proves the requested file opened or became active.
If Word was already holding a person's document and the staged open silently added nothing,
theirs is what gets written to the output, closed, and then removed with `$stage_dir` on exit
— with exit 0 and no error log. C1 drops to 0.35.

**The campaign is the least wrong of the four, and deserves the credit.** It is the only one
that takes a count *before* the open and requires it to rise (`:148–156`), with a comment
saying why: "CLEAN only if the document ACTUALLY opens (count rises) — never default to CLEAN
just because no dialog was seen yet". That is exactly the remedy §5.16 recommends for
`word-open-probe.sh`. What it still lacks is a content check, and this repository's own
definition of Word valid requires "at least some content", so C1 drops to 0.80 rather than
further. Binding to the staged filename would close the remaining gap, since a concurrent
unrelated open also raises the count.

**The fix is the same in all four places**, and a fifth script already implements it:
`word_compare_batch.applescript` walks `document i` and takes the one whose name is not
the base's (§5.11). It was listed here in an earlier revision, wrongly: its defect is
§14.1's ordering bug, logging `[ok]` before it evaluates base health, not binding to
whichever document is frontmost. Identify the document by name, or by exclusion, and
never by which one is frontmost.

### 5.19 `word-convert.sh` deletes its input when asked to convert a file to itself

`word-convert.sh deal.docx deal.docx` is accepted by the argument check — the extension
whitelist admits `docx` as an output — and `set -euo pipefail` is on (25). Then:

```sh
out_abs="$(cd "$(dirname "$out")" && pwd)/$(basename "$out")"   # 45, == in_abs
rm -f "$out_abs" "$err_log"                                      # 47, deletes the INPUT
cp -p "$in_abs" "$word_in_abs"                                   # 54, source is gone
```

Line 47 removes the destination before staging, which is right when the two differ. When they
are the same file it removes the input, and line 54 then fails against a path that no longer
exists. Under `set -e` the script aborts there, so it produces no output, no conversion, and
not even the `.error.txt` the rest of the script is careful to write. The user is left with
one fewer file than they started with and nothing explaining why.

This is distinct from §5.14, which is about equal *basenames* in different directories. Here
the paths are canonically identical. Rejecting `in_abs == out_abs` is one comparison, and
staging the input before deleting the destination would make the ordering safe regardless.
C6 drops to 0.65, also carrying §5.13's missing `command -v` check for `timeout`.

### 5.20 The negative control can contaminate the corpus it exists to validate

`word-open-check.mjs`'s self-test deliberately opens a known-corrupt document, confirms the
repair prompt, and then proceeds straight to the real corpus with only
`closeOurDocs(); cancelGrantDialogs(); drainDialogs();` between them (876–878). There is no
recycle, no re-warm, and no health check.

That is the one sequence this document establishes as dangerous.
`word_screen_sources.applescript`'s own header (16–20) is where the failure mode is
recorded: *"a single poison document leaves Word degraded for the REST OF THE SESSION.
Every subsequent open returns an empty document, silently — no error, no dialog. Screening
223 files in one Word session reported 213 as unreadable when only a handful actually are;
the other 203 were collateral damage from file #11."* §5.8's probe sweep is the same
failure measured a second time, and it is the reason §15's replacement pair recycles on a
failure streak at all. (§7 scores the *detector* for this condition — positive integer
healthy; thrown error, `0` and `missing value` all poison — not the cascade itself.)

The committed `source_screen.tsv` does **not** show that cascade, and is not evidence
against it. The script was rewritten to stop at the first failure (`return "POISON " &
fname`, 84) and to skip rows already logged (43–47), so the log is the accumulated output
of many restarted passes, not one session: 223 document rows plus a `__SCREEN_DONE__`
sentinel, 217 healthy, 6 flagged (3 AppleEvent timeouts, 3 `missing value`), and no two
flagged rows adjacent anywhere in the file. A stop-and-restart contract produces that
shape by construction. (`word_unreadable.txt` carries a seventh name,
`super_editor__image_out_of_folder_19763c1d.docx`, that the screen itself logged healthy
at 6 paragraphs — excluded on some basis the artifacts do not record.)

The control is a *deliberate* malformed open, so it is the most predictable instance of the
trigger in the entire corpus, and it runs immediately before the measurements it is supposed
to make trustworthy.

The irony is worth stating plainly, because it cuts against the credit given elsewhere in this
document: the mechanism that makes this the only script proving its detector is also the one
mechanism guaranteed to put Word into the state that invalidates what it proves. A recycle and
warm after the control, or any positive health check before the first real case, closes it.
C2 drops to 0.65, together with §5.13's unscoped `drainDialogs()`.

---

## 6. Permission prompts over many files (C4)

Two mechanisms, routinely conflated (see §5.1).

**P1 — TCC Apple-events automation.** One prompt per (responsible client, target) pair —
for `osascript` from a terminal, that is the terminal — persisting until it is revoked in
System Settings, reset with `tccutil reset AppleEvents`, or invalidated by the client being
re-signed. Not per process, not per file, and not permanent. Only `word_compare_driver.sh:64–72` handles it at all: it
probes with a cheap `get name`, and if it fails, exits with the exact one-liner to run. That
is the correct treatment — this prompt cannot be dismissed programmatically, so the only
options are "already granted" or "stop and tell the human".

**P2 — Word's "Grant File Access" sandbox sheet.** Per file (§6.1), for paths outside
Word's container. **Three strategies, and one absence of one:**

| Strategy | Who | Cost |
|---|---|---|
| Stage inside the container | `run_batch_retry.sh`, `word_compare_driver.sh`, `word-convert.sh` (as shipped) | One copy per file; zero prompts |
| Dismiss via Accessibility AXPress | `word-convert.sh` (only out of container), `redline-word-campaign.ts`, `word-open-check.mjs` | A UI round-trip per file; needs the Accessibility grant |
| Grant the folder once by hand | A human, before the batch | One interaction per folder, per machine — and it persists only once the panel is completed, which needs Word frontmost (§6.1). Viable, but a batch cannot do it for itself |
| *(none)* | family A, `render/word.py`, all three probes/sweeps | Not a strategy. A human at the keyboard, or a hang |

### 6.1 Why some scripts prompt once and some prompt every time

**Reported from the target machine, and not verified here** (no macOS, Word or `osascript`
was available in the authoring environment, and no run artifact in these repositories records
prompt behaviour): the Grant File Access prompt fires **per file close**, varies with where
the script is run from, and some scripts re-prompt on folders they have already been granted
while others ask only once. Everything below explains those three reports from the code; if a
report is wrong, the explanation for it goes with it.

**The grant persists only if the panel flow is completed.** "Grant File Access" is Word's
wrapper over Powerbox. Its `Select…` button opens an `NSOpenPanel`; confirming *that panel*
is what lets Word persist a security-scoped bookmark. Anything that ends the dialog without
completing the panel — Cancel, Escape, a timeout, or no handler at all — grants nothing, so
the next access re-prompts. That is the whole once-versus-every-time split:

| Behaviour | Scripts | Why |
|---|---|---|
| **Never prompts** | `run_batch_retry.sh`, `word_compare_driver.sh`, `word-convert.sh` **as shipped** | Everything is staged inside a container Word already owns, so Powerbox is never invoked |
| **Prompts once, then persists** | `word-convert.sh` **only when staging is bypassed** | Not a second behaviour of the same run: `word-convert.sh:49` stages into `$HOME/Library/Containers/com.microsoft.Word/Data/tmp/…` unless `WORD_CONVERT_STAGE_ROOT` overrides that root to a path outside the container. Only then is Powerbox invoked, and only then does its Grant handler run — `set frontmost to true` (236) before `click button "Select..."` and `key code 36`, so the panel renders and accepts and the grant carries |
| **Prompts every file, and answers nothing** | `redline-word-campaign.ts` | It AXPresses Grant/Open/Select/Allow in a loop *without* activating Word, and its own bouncer takes Word out of frontmost every 0.5 s, so the panel never renders to accept the press. A UI round-trip per file that grants nothing |
| **Prompts every file; whether it answers is undetermined** | `word-open-check.mjs` | Its handler does not activate either, but it has no bouncer and its warm-up *does* activate Word, so Word may still be frontmost when `grantFileAccess()` presses. If it is, the panel renders, the press lands and the grant persists. Reading the handler cannot tell which, and this is not grouped with the campaign for that reason |
| **Prompts every time** | family A, `batch_word_to_pdf.scpt`, `render/word.py`, `word_validate_batch.py`, both `word-open-probe.sh`, `word-probe-sweep.sh`, `redline-sweep.sh` | No handler. The dialog stands until the AppleEvent times out; nothing is ever granted |
| **Prompts every time, and denies** | `word_dialog_watchdog.applescript` | Its button list is `{OK, Ok, Cancel, Close, Don't Save, No}` — no Grant, Select, Open or Allow. On a Grant sheet it presses **Cancel**, so it actively refuses the grant on every appearance |

The watchdog row is the sharpest case: it does not merely fail to persist a grant, it denies
one, forever, on folders it has already seen. Any run that pairs the watchdog with
out-of-container paths will prompt on every single file and never stop.

**"Each time a file is closed"** is the save side. Most of these batches read from one folder
and write to another, so there are *two* folders to grant, and the output folder is first
touched at `save as` — i.e. as the document is finished and closed. Counting distinct folders
each generated batch makes Word touch: `batch_convert.scpt` 2,
`batch_jubarte_lossless_pdf.applescript` 2 (it writes into a `pdf/` subfolder),
`batch_sanity_pdf.applescript` **6**. Those are the folder counts, and they would be the
prompt counts for a script that completes each grant. None of family A has a handler at all,
so for them the prompt count is the *file* count — 1,224 for that one.

**"Depending on where the script is run"** has a concrete cause in at least one script:
`redline-word-campaign.ts` computes `PROBE_DIR` as `process.cwd()`-relative
(§5.13). Invoke it from a different directory and Word is asked for a different folder, so a
previously granted run prompts again. That is invocation location literally determining
whether a prompt appears.

**Persistence is conditional on the panel flow actually completing — and it only completes
when Word is frontmost.** This is the real variable, and exactly one script gets it right.

**Provenance, because the three inputs are not the same kind of claim.** Two are *reported*
and were not verified here: that a completed grant persists at all, which `CLAUDE.md` states
and this audit did not re-test; and the target-machine observation that some scripts ask once
while others ask on every file, which is Arthur's, on the machine these run on — no macOS,
Word or `osascript` was available in the authoring environment. The third, the table below, is
*code-derived* and checkable by line number: which script activates Word before pressing, and
where. The conclusion is the two reports joined by the code. If either report is wrong the
join does not hold, and the table still stands on its own.

`CLAUDE.md` states the mechanism: the Grant File Access sequence *"`Select…` →
`NSOpenPanel` → grant … **will not render/accept `AXPress` unless Word is the active
app**"*. So a handler that presses buttons without activating Word is pressing at a panel
that never rendered; nothing is granted, and the next file prompts again.

| Script | Activates Word for the grant? | Result |
|---|---|---|
| `word-convert.sh` | **Yes** — `set frontmost to true` at line 236, inside the Grant handler, immediately before `click button "Select..."` and `key code 36`. It also `activate`s Word at line 147 on the ordinary open path, so Word is frontmost before a sheet can even appear | Flow completes; **grant persists**. Reached only when `WORD_CONVERT_STAGE_ROOT` moves staging outside the container (49); as shipped it stages inside and never prompts |
| `word-open-check.mjs` | Not in the handler. `grantFileAccess()` (348) AXPresses without activating; its two `activate` calls are elsewhere — forcing the GUI launch during warm-up (827) and a screenshot after a clean verdict (894) | **Undetermined.** The warm-up `activate` precedes the probes and this script runs no bouncer, so Word may well still be frontmost when the handler fires. What the code shows is that the handler does not *itself* ensure it; whether the panel then renders is not decidable from source |
| `redline-word-campaign.ts` | No, and it runs a bouncer that pushes Word *out* of frontmost every 0.5 s | Flow cannot complete; re-prompts |

So "asks only once" is `word-convert.sh`. "Asks every time, even on folders already seen"
fits `redline-word-campaign.ts`, whose bouncer actively prevents the panel rendering.
`word-open-check.mjs` is the one the code cannot settle, because Word's frontmost state
there depends on a warm-up `activate` several hundred lines earlier rather than on the
handler. The grant mechanism is not the
problem; not *ensuring* Word is frontmost at the moment of the press is.

**The irony is worth recording.** `redline-word-campaign.ts` is the only script that
implements `CLAUDE.md`'s focus-bouncer rule properly (§5.9) — and the bouncer is precisely
what stops its grant completing. Two rules in the same `CLAUDE.md` paragraph are in tension,
and that paragraph names the exception: activate *for this flow specifically*, with the
bouncer restoring focus immediately afterwards. `redline-word-campaign.ts` takes the rule and
not the exception.

`word-convert.sh` gets the outcome right while breaking a different clause of the same
paragraph: it finishes with `key code 36` where `CLAUDE.md` says to use `AXPress` and *"never
keystrokes"*. The combination that satisfies everything is activate → `AXPress` the grant →
let the bouncer restore focus, and no script in the corpus does all three.

Three consequences follow, and they are the practical ones:

- **Pressing buttons without activating Word can be a no-op with a delay.** Established for
  one of the three handlers: `redline-word-campaign.ts`'s bouncer removes Word from
  frontmost every 0.5 s, so its panel cannot render to accept the press. Left open for the
  second, `word-open-check.mjs`, whose handler does not activate but which may inherit
  frontmost from its warm-up. So: one handler pays a round-trip per file and grants nothing,
  and a second may be doing the same — the table above does not settle it, and neither does
  this bullet.
- **Container staging remains the first choice**, because it makes the prompt not happen at
  all rather than answering it — and it needs neither the Accessibility grant nor the focus
  interruption that activating requires.
- **Where out-of-container access is unavoidable**, `word-convert.sh`'s activate-then-grant
  is the only pattern here that actually persists, and it should be paired with a bouncer so
  net focus stays with the user.

**On `CLAUDE.md`'s claim.** Its macOS section says *"Granting a folder once persists Word's
access to it, so subsequent opens from that folder need no activation."* That is right about
the grant and misleading about the activation: the grant persists only once it has been
completed, and completing it is exactly what needs Word frontmost. The sentence reads as
though activation stops being necessary in general, when what it means is that a *completed*
grant does not need re-granting. Two of the three handlers do not activate inside the
handler at all, which is what reading it the first way looks like in code. That count is
unaffected by the uncertainty above: whether `word-open-check.mjs`'s panel ends up rendering
is undetermined, but that its handler does not itself activate is plain from line 348.

Unlike the per-process TCC rule (§5.1) and the file-versus-inline `-1708` rule (§5.2), this
one survives. It is not proven, and the distinction matters: reading the handlers shows
whether each calls `activate` before it presses, and that is all local code can show. That
the panel rendered, that the grant persisted, and that frontmost state was the variable
are target-machine reports. So the honest statement is that this explanation is
**consistent with the reported behaviour and with the inspected control flow**, and that
the table's result column inherits that condition. Its cited proof —
`report_one/scripts/compare-docs.sh` and `report_one/scripts/redline-word-pdf.py` — still
does not exist in any of these checkouts (§5.13), so nothing here rests on the attribution.

### 6.2 Scores and why

| File | C4 | Rationale |
|---|---|---|
| `word_compare_driver.sh` | 1.00 | Only script that handles both: staging eliminates P2, an explicit precheck fails fast on P1 with instructions. Documents the arithmetic it is avoiding. |
| `word-convert.sh` | 0.95 | Container staging *and* active Grant-dialog handling (`Select…` then `key code 36`). Belt and braces. No P1 precheck. |
| `word_compare_batch.applescript` | 0.90 | Inherits staging; header forbids pointing it at repo paths. |
| `word_screen_sources.applescript` | 0.85 | Same, via the staged dir passed as argv. |
| `run_batch_retry.sh` | 0.80 | Full app-container staging for both src and out. No P1 precheck, no dialog fallback if staging is bypassed. |
| `word-open-check.mjs` | 0.70 | AXPress dismissal, and it *distinguishes* the permission sheet from a repair dialog rather than draining both — a permission prompt is recorded, never counted as invalid. |
| `redline-word-campaign.ts` | 0.60 | AXPress dismissal (Grant/Open/Select/Allow, up to 8 passes) but stages outside on purpose, so it pays a UI round-trip per file and hard-depends on Accessibility. |
| `word_dialog_watchdog.applescript` | 0.15 | Deliberately clicks only OK/Cancel/Close/Don't Save/No — never Grant/Select/Open/Allow. Sound as a safety policy, but on a Grant sheet it presses **Cancel**: it does not merely fail to help with P2, it denies the grant, every time, on folders already seen (§6.1). |
| `render/word.py`, `word_validate_batch.py` | 0.25 | Docstring is honest — *"Word may prompt for automation permission (grant it) … Run interactively, not from unattended automation"* — but `word_validate_batch.py` is explicitly a large-batch tool, so the gap bites hardest there. |
| `word-probe-sweep.sh` | 0.15 | Nothing for P2; its AutoRecovery wipe addresses a different dialog entirely. |
| family A, `batch_word_to_pdf.scpt` | 0.15 | No staging, no dismissal, arbitrary paths. `displayAlerts false` does **not** suppress the sandbox sheet. `batch_sanity_pdf` spans six directories. |
| `word-open-probe.sh` ×2, `redline-sweep.sh` | 0.10 | Bare open of an arbitrary path, no handling at any layer. |

---

## 7. Malformed-item handling (C5)

| File | C5 | Behaviour on a broken input |
|---|---|---|
| `word_compare_batch.applescript` | 0.85 | Paragraph count is *taken* before comparing but never *gates* it: the compare and `save as` run regardless, and the count is only evaluated after `[ok]` is already logged (§14.1). Otherwise strong — classifies three failure shapes, logs `[fail] <id> :: <errMsg>` verbatim and `[warn]` for zero-paragraph, returns `POISON <id>` so the driver recycles, 300 s inner timeout. |
| `word_screen_sources.applescript` | 1.00 | The dedicated detector. Healthy = a positive integer; a thrown error, `0`, and `missing value` are all poison, each recorded verbatim. Produces `word_unreadable.txt` as a reusable exclusion list. |
| `word-open-check.mjs` | 1.00 | Verdict taxonomy OPENED-CLEAN / REPAIR-PROMPT / ERROR / BLOCKED; dialog text retained verbatim; per-file screenshot as evidence. An unmatched modal is recorded in `row.notes` and drained, then the poll restarts (`drainDialogs(); continue;`, 622–631) rather than falling through to the opened branch — so it is never *silent*. It can still end OPENED-CLEAN if the document opens on a later poll; whether a drained unknown modal ought to poison the verdict is a judgement the code makes deliberately, with the comment to say so. C5 is unaffected by §5.15, but that finding applies here too: what gets measured after a clean open is `active document`, not necessarily the file just probed. |
| `word_compare_driver.sh` | 0.95 | `--screen` pre-flight; stall recovery synthesises a `[fail]` so a wedging file cannot be retried forever; restarts Word on poison. |
| `word-convert.sh` | 0.90 | Detects "Word found unreadable content" / "recover the contents", presses **No** — declining recovery is correct for an oracle, since recovering produces a *different* document — writes a dedicated `.error.txt` with input, output, timestamp and osascript output, exits 3, resets Word. |
| `redline-word-campaign.ts` | 0.90 | Filename-verified UNREADABLE/ERROR; conservative default to UNREADABLE when neither open nor dialog is observed; drains before and after; JSON report. |
| `word_validate_batch.py` | 0.85 | Per-file JSONL row with error, flushed immediately; force-quits Word after each failure so the next file is judged on a clean instance. |
| `word-probe-sweep.sh` | 0.85 | Logs `FAIL <name>: <probe output>`, then kills and warms — the recovery the probe itself lacks. |
| `render/word.py` | 0.80 | Validate path is the corpus's best: three-valued outcome, modal probe, `ModalProbeError` when the probe itself cannot be trusted. PDF path is weaker: timeout → `"Word timed out (dialog?)"`, honest about its uncertainty but with no recovery. |
| `word_dialog_watchdog.applescript` | 0.70 | Dismisses the hard file-loader dialog that `displayAlerts` cannot touch — the missing half — and logs every dismissal. Cannot attribute a dialog to a file. |
| `run_batch_retry.sh` | 0.50 | Per-pair CSV row with status, duration and first line of stderr; closes all documents before and after. No `displayAlerts false` and no timeout, so a repair modal hangs indefinitely. |
| `word-open-probe.sh` ×2 | 0.50 | Returns `ERROR <n>: <msg>` or `FAILED`, with distinct exit codes — but leaves the dialog standing for the next caller. |
| `batch_word_to_pdf.scpt` | 0.35 | Logs the error with an index — better than the unrolled family — but does not close the document, which is worse. |
| `redline-sweep.sh` | 0.35 | Logs `PROBEFAIL`, no recovery, cascade follows. |
| family A (6 files) | 0.30 | `try` / `on error` / `close every document saving no`, then continue. `batch_convert` binds `errMsg` and discards it; `batch_inline`/`2` do not bind it at all. The only record of which file failed is a missing PDF. |

---

## 8. Edge-case preparedness (C6)

Edges that actually occur here: `~$` lock files; filenames with quotes, backslashes,
newlines or dots; empty directory; missing output directory; Word already holding a human's
documents; Word not installed; Accessibility not granted; stale output; a document that opens
but is empty; a large document that is slow but fine; an interrupted run.

| File | C6 | Notable coverage / notable gaps |
|---|---|---|
| `word_compare_driver.sh` | 0.95 | Refuses to run over open documents; Word-installed, manifest and TCC prechecks; Accessibility degrades to a warning rather than a failure; `shopt -s nullglob`; `\|\| true` on greps so an empty log cannot abort under `set -e` (documented); cleans `~$` after each restart; `MAX_RESTARTS` and stall bounds; a written termination argument. |
| `word-open-check.mjs` | 0.75 | Docked for `row.uiError` being recorded and never read (§5.13), and for `makeCorruptControl()`'s unconditional `rm -rf` on an `--artifacts` path it does not own (§5.13). Otherwise: BLOCKED verdict when Accessibility is revoked mid-run; `SIGKILL` because a blocked `osascript` ignores SIGTERM; `rm -f` before `zip` because zip *updates* archives; quits Word only if it launched it; records the strict-packages corpus gap rather than silently skipping it. |
| `word_compare_batch.applescript` | 0.90 | Skips existing output; tolerates blank rows and wrong field counts; start/count slicing; avoids `repeat with d in documents` because that Word build rejects `count of every document`. |
| `word-convert.sh` | 0.65 | Docked hardest for §5.19: `in_abs == out_abs` deletes the input at 47 and aborts at 54 under `set -e`, leaving no file and no error log. Also §5.13's missing `command -v` for `timeout`. Otherwise: arg count, file existence and extension whitelist; `mkdir -p`; per-run `mktemp -d` with `trap cleanup EXIT`; argv-safe paths; records that `format Unicode text` is rejected by this build; removes stale output before starting — the *destination* (47), not the staged output, which is the one the completion poll reads (§5.14). Score cut from 0.85 for that gap, and for inner `timeout 10` wrappers with no `-k` (§10). |
| `render/word.py` | 0.80 | Platform gate; skip-existing with `force`; reference calibration so a slow machine does not read as a broken document; reaps killed processes; `_close_active_document` with an Escape fallback. Globs `*.docx` including `~$`; no staging. |
| `word_screen_sources.applescript` | 0.75 | `\|\| true` so an empty dir does not error; skips already-logged entries; three failure shapes. No `~$` filter. |
| `word-probe-sweep.sh` | 0.70 | `[ -e ]` guard for an empty glob; deletes `~$`; pays the cold start explicitly; wipes AutoRecovery (unscoped — §12 step 4); `set -uo pipefail` without `-e` deliberately. Hardcoded `PROBE` path. |
| `redline-sweep.sh` | 0.70 | Rejects unknown flags; three preconditions; per-sweep manifest; missing-baseline hard fail. `IFS=,` breaks on quoted commas; `BASH_SOURCE` under a `zsh` shebang. |
| `word_dialog_watchdog.applescript` | 0.70 | `try`-wrapped throughout; handles sheets and standalone dialogs. No self-exit if orphaned by a killed parent. |
| `word_validate_batch.py` | 0.70 | `--limit`; empty-dir guard; `mkdir(parents=True)`; flush per row. Globs `~$` files. |
| `redline-word-campaign.ts` | 0.50 | `pairs.json` existence check; bouncer in a `finally`. "Closes only `campaign-*` documents" was credited here until §5.13 established the loop uses `every document` and so may close nothing at all. `process.cwd()`-relative staging; first-N "sample"; an empty worklist exits 0; no platform preflight; unscoped `drainDialogs()`; sanitised-label collisions. |
| `run_batch_retry.sh` | 0.60 | Excludes `~$` in three places; numeric sort with a documented reason; `PAIRS < 1` guard; `mkdir -p`; resume. Requires the `file_N.docx` convention; mutates `SOURCE_DIR` in place when stamping. |
| `word-open-probe.sh` ×2 | 0.45 | File-existence check; escapes backslash and quote; `count of documents > 0` guard. Cut from 0.55 by §5.16, in the same rescore as C1: “Word already holding a human's documents” is on this section's own edge list, and the probe closes whichever document is active `saving no`. Newline in a filename still breaks out; `$delay` interpolated unvalidated. |
| `batch_word_to_pdf.scpt` | 0.25 | `ls \| grep '\.docx$'` — no `~$` filter, breaks on a newline in a filename. No output-dir creation, no zero-file guard. |
| family A (6 files) | 0.05 | Two of six carry 102 lock files *as work items*. Absolute single-machine paths, no directory creation, no stale-output handling, no Word-state check. |

---

## 9. Concurrency (C7)

**The ceiling is low, and that is not a defect.** Word for Mac is a single-instance,
user-session-bound application. There is no equivalent of LibreOffice's
`-env:UserInstallation=file://…`, which is exactly what lets `render/soffice.py` run a
`ThreadPoolExecutor(max_workers=12)` safely in the same package. Real Word parallelism needs
N macOS user sessions or N VMs. So for the Word-touching step, serial is correct and a score
of 0 there is not a criticism.

What *is* scoreable: whether the parallelism that is available gets used — concurrent
supervision, shardability, and doing non-Word work off the critical path.

| File | C7 | Rationale |
|---|---|---|
| `word_dialog_watchdog.applescript` | 0.80 | It *is* the concurrent component: a second process watching Word's UI while the batch holds the Apple-event channel, and the only one whose concurrent work does something the batch needs. Not the only concurrent process in the corpus, though — `redline-word-campaign.ts` spawns a detached `osascript` focus bouncer (`:193`, `detached: true`) that polls every 0.5 s alongside the probe. That one exists to protect the user's focus rather than to advance the run, which is why it scores lower here, not because it is not concurrent. |
| `word_compare_driver.sh` | 0.75 | Runs the watchdog concurrently, and supervises the batch from the shell while it runs (the stall watcher polls the log every 15 s). `--start` / `--limit` allow manual sharding. Word work correctly serial. |
| `word_compare_batch.applescript` | 0.50 | Serial by necessity, but argv `start`/`count` make it shardable, which is what the driver exploits. |
| `redline-word-campaign.ts` | 0.50 | Two-tier screening is the right instinct — `docx-validate` on all pairs, Word on a subset. The bouncer runs concurrently. But the jubarte compare itself is pure TS with no Word involvement and runs sequentially. |
| `word-open-check.mjs` | 0.40 | Phase-separated generate-then-probe; generation is pure TS and sequential. Word phase correctly serial. |
| `word_screen_sources.applescript` | 0.40 | Serial, but resumable-by-log so the driver can loop it — that is what makes the restart cycle cheap. |
| `word_validate_batch.py` | 0.30 | `--limit` allows crude sharding; JSONL append means shards merge cleanly. Nothing coordinates them. |
| `word-convert.sh` | 0.30 | One file per invocation looks trivially shardable, and per-run `mktemp -d` avoids staging collisions — but two invocations would still collide on Word itself (`close active document`), and nothing says so. |
| `render/word.py` | 0.25 | Accepts `jobs=12` and ignores it. The reason is right and documented; the signature is not. |
| `run_batch_retry.sh` | 0.20 | Serial; the per-pair process model would allow index-range sharding but there is no flag for it. |
| `word-probe-sweep.sh` | 0.20 | Serial with kill-and-warm; the ~30 s warm after each failure is pure serial cost that nothing amortises. |
| `redline-sweep.sh` | 0.20 | **The biggest missed parallelism in the corpus.** The generation loop invokes the Rust `jubarte` binary once per pair, sequentially. That step never touches Word and is embarrassingly parallel. |
| `word-open-probe.sh` ×2 | 0.20 | Single file, single process — the ideal shard unit, with no coordination around it. |
| `batch_word_to_pdf.scpt` | 0.10 | Serial single stream; shardable only by pointing at different directories. |
| family A (6 files) | 0.05 | Single serial stream, no chunking, no resume. `batch_inline` / `batch_inline2` look like a manual two-way shard but overlap on 211 files, so the sharding is broken as well as unused. |

---

## 10. Timeouts: which are wrong, and why

| Script | Value | Verdict |
|---|---|---|
| `render/word.py` `validate_one` | 60 s, budget = `max(timeout, 4 × reference_open)` | **The best timeout design in the corpus.** It is the only one that solves *slow ≠ broken*: it measures a known-good document on this machine and scales the budget from that, so a 1,000-page document does not read as a repair prompt. |
| `word-open-check.mjs` | `osa` 30 s, doc-count probe 8 s, 45 s per-file deadline, 0.7 s poll | Well layered. 45 s for one attempt is generous; a 0.7 s poll is responsive without hammering System Events. |
| `word_screen_sources.applescript` | 60 s per open | Right order of magnitude. Screening is open-and-count only, so 60 s is generous for a healthy document and bounded for a bad one — and it sits behind a pre-warmed, driver-recycled Word, so cold start never eats the budget. |
| `word_compare_driver.sh` | `STALL_SECS=420`, polled every 15 s | Correctly larger than the batch's 300 s inner timeout — it must be, or it would kill a legitimately slow pair. But the margin is only 120 s, which is tight for a machine under load. Widen to ~600 s, or derive it as `inner + 50%`. |
| `word_compare_batch.applescript` | 300 s per pair | Justifiably large: `compare` on a big document is genuinely slow. See the margin note above. |
| `word-convert.sh` | outer `timeout 90`, inner `with timeout of 240`, poll loop 120 × 2 s = 240 s | **Incoherent — the only clearly wrong set.** 90 < 240, so the inner budget and the loop's tail are unreachable and the effective budget is 90 s, which is too short for a large DOCX→PDF. **And 90 s is not even a reliable cap:** `word-convert.sh:55` sets `timeout_cmd="${WORD_CONVERT_TIMEOUT_CMD:-timeout}"` — plain `timeout`, with no `-k`/`--kill-after` anywhere in that file (`grep -c -- '-k\|--kill-after' scripts/word-convert.sh` → 0), and `timeout(1)` sends SIGTERM, which is precisely the signal a blocked `osascript` ignores (§14.2). The `kill -0` poll can therefore stay true for its whole run and the following `wait` can block indefinitely. Fix: set the outer to inner + slack *and* give it `-k`, or drop a layer; raising or removing a timeout layer alone does not buy a hard stop. **The same gap sits on the recovery path**, which is worse: `reset_word_after_failure` closes and quits Word through two `$timeout_cmd 10 osascript` calls (131–132), so a Word wedged behind an unanswered Apple event ignores both SIGTERMs and the `pkill` that follows never gets its turn. Every `timeout` wrapper around Word in this file needs `-k`, not just the outer one. |
| `word-convert.sh` UI probes | `timeout 8` / `10` / `12` | Fine. These are sub-second queries with a generous kill switch. |
| `render/word.py` `convert_one` | 180 s flat | Reasonable for docx→PDF, but it is a flat constant in the same module where the validate path got the calibrated treatment. Inconsistent; the calibration belongs here too. |
| `word_validate_batch.py` | `--timeout 25` default | **Too little, and it silently disables the calibration.** It overrides the module's 60 s *downward* and passes no `reference`, so `_budget` degenerates to a flat 25 s. Large documents come back UNJUDGEABLE — and the CLI then counts them as **invalid**, which is the opposite of what the module promises. `ValidationResult.ok` is `outcome == "valid"` (`render/word.py:126-127`), so UNJUDGEABLE is falsy; `word_validate_batch.py` writes it out as `"word_valid": res.ok` (60), reports it in `len(docs) - n_ok` "invalid" (76), and fails the whole batch on it (`return 0 if n_ok == len(docs) else 1`, 78). `render/word.py:118-119` states the intended contract in its own docstring — *"the budget ran out with NO modal observed — Word was merely slow on this machine; recorded, never treated as invalid"* — and the CLI contradicts it. So a too-short budget does not quietly shrink the denominator; it marks slow-but-valid documents invalid and turns a clean corpus red. |
| `word-open-probe.sh` ×2 | `with timeout of 60` covering launch **and** open | **Too little when Word is cold, too much when the file is fine.** `word-probe-sweep.sh`'s own header says Word needs ~30 s to cold start, so half the budget can go to launching. Meanwhile a healthy open is 1–3 s, so a bad file burns the full 60 s. Fix: pre-warm (the sweep does), then 20 s is ample. |
| `redline-word-campaign.ts` | 20 s per `osascript`, 16 × 1 s poll per attempt | **16 s is too little for a first open against a cold Word.** The retry masks it, at the cost of always wasting the first attempt when Word was not already running. Pre-warm instead. |
| `word-probe-sweep.sh` `warm_word` | 40 × 2 s = 80 s, 5 s per responsiveness probe | Correct. Generous for cold start, and it is the only script that pays that cost explicitly rather than charging it to the next file's budget. |
| `word_compare_driver.sh` `restart_word` | quit → 3 s → `pkill` → 2 s → `open` → 30 × 1 s | The 30 s relaunch poll sits right at the documented ~30 s cold start. Raise to 60 to stop a slow relaunch counting as a failed one. |

**The pattern:** every timeout that covers *launch plus work* in one budget is wrong, in both
directions at once. Separate them. Warm Word once, then size the per-document budget to the
work alone — and where the document size varies by orders of magnitude, calibrate it the way
`validate_one` does instead of picking a constant.

---

## 11. Attempts and backoff

| Script | Attempts | Verdict |
|---|---|---|
| `word_compare_driver.sh` | `MAX_RESTARTS=80`, no backoff | Sound. 80 is high but bounded, and the work list shrinks monotonically (documented at lines 182–198), so termination is guaranteed rather than hoped for. No backoff is correct: each restart follows a *specific* event, not a repeat of the same attempt. |
| `word-probe-sweep.sh` | 1 attempt per file; kill + warm after each failure | Correct shape. No retry at all — recovery instead. |
| `word-convert.sh` | 1 attempt, then reset Word and exit 3 | Correct **as a retry policy**: it does not retry into a degraded Word, it hands the decision to the caller. The reset it runs first is a separate question, and §12's residue table answers it: `reset_word_after_failure` (129–135) closes whichever document is active `saving no` and quits everything `saving no`, with no precondition that Word held nothing else. Right escalation, wrong precondition. |
| `render/word.py` | 1 attempt. `_close_active_document` tries close → Escape → close | Correct — those three are cleanup steps, not retries of the work. |
| `render/soffice.py` (contrast) | `retries=1`, each attempt in a **fresh isolated profile** | The right model, and the one Word cannot copy cheaply: Word's equivalent of a fresh profile is a full relaunch. |
| `redline-word-campaign.ts` | 2 attempts, no backoff, **no Word recycle between them** | **The weakest retry in the corpus.** Retrying the same open against the same possibly-degraded Word is the one thing the rest of these repos proves does not work (§5.8's cascade, `word_screen_sources`' 203-file contamination). Either kill and warm between attempts, or drop the second attempt and report. |
| `run_batch_retry.sh` | Named "retry", retries nothing within a run; resume-on-rerun only | The name is misleading; the behaviour is fine. |
| family A | 0 retries, 0 recovery | A failed file is simply lost, discovered later as a missing PDF — which `CLAUDE.md` then repurposes as the broken-fixture worklist. That works, but it is a side effect, not a design. |

**On backoff, specifically: no script here uses exponential backoff, and none should.**
Backoff is for contention — a resource that will free up if you wait. These are *state*
failures: Word is wedged, or degraded, or holding a modal. Waiting longer does not help;
resetting state does. The one place a wait genuinely earns its keep is cold-start polling,
and the right shape there is a short fixed poll under a generous ceiling — which
`warm_word`'s `40 × 2 s` already is.

The rule worth writing down: **retry only across a state reset.** An attempt that follows a
kill-and-warm is a new experiment. An attempt that does not is the same experiment run twice.

---

## 12. The error Word throws when we force-quit it

**A `pkill -9` does not produce an Apple crash report — and Word still asks to send an
error report on the next launch.** Both are true, because they are different mechanisms. An
earlier draft of this section got the second one badly wrong by reasoning from the first.

- **Apple's ReportCrash** fires on uncaught exceptions — SIGSEGV, SIGABRT, SIGILL, SIGBUS. A
  signal you send yourself is a termination, not a crash, so `pkill -9` leaves no crash log
  and raises no "X quit unexpectedly" panel from the OS. (`EXC_CRASH (SIGKILL)` *does* appear
  in crash reports when the **system** kills a process — a watchdog termination carries it
  with `EXC_CORPSE_NOTIFY` and a reason such as `0x8badf00d` — but no `pkill` from these
  scripts reaches that path.) So `defaults write com.apple.CrashReporter DialogType none` is
  not the fix for anything here.
- **Microsoft Error Reporting (MERP)** is Office's own reporter, shipped as a separate
  application — `Microsoft Error Reporting.app`, under
  `/Applications/Microsoft Word.app/Contents/SharedSupport/` in current Office and
  `/Library/Application Support/Microsoft/MERP2.0/` historically. It does **not** depend on
  ReportCrash. Word records whether it exited cleanly and, finding on the next launch that it
  did not, MERP raises its own "send a report" dialog.

The earlier draft concluded "there is no crash dialog to suppress". That was a non-sequitur:
it checked one mechanism and generalised to all of them. **Reported from the target machine
and unverified here:** after a force-quit, Word asks to send a report on the next launch
**even with no document open**. That is Arthur's direct observation, not a documented claim,
and the Sources section says so; nothing below it is stronger than that one report. That detail is what separates the two dialogs: with nothing open there is nothing to
recover, so the prompt is MERP, not Document Recovery.

What a killed Word *actually* leaves behind — three things, not two:

1. **AutoRecovery files → the Document Recovery pane on next launch.** Microsoft's own
   documentation is that Document Recovery opens automatically when AutoRecover files exist.
   That pane appears *before* any script command runs, so `set displayAlerts to false`
   cannot reach it. **What that does to the next Apple event is unverified for the target
   build:** Microsoft documents when the pane opens, not that it blocks `open` from being
   answered. The restart-and-clean recommendation below rests on it, so it is worth
   measuring rather than assuming.
2. **`~$*.docx` owner/lock files** in every folder Word had a document open from. A killed
   Word never removes them. The next glob picks them up as work items and each costs a full
   AppleEvent timeout (§5.5: 102 of them are committed into family A).
3. **An unclean-exit flag → Microsoft Error Reporting's "send a report" dialog on next
   launch.** Independent of AutoRecovery: on the single report above it fires with no document
   open, which would mean after *every* kill in a recovery loop rather than only after one
   that had work in progress. That generalisation inherits the report's status — one machine,
   unverified here. **No script
   in any of the three repos handles it.** `word-probe-sweep.sh`'s AutoRecovery wipe does not
   touch it, because it is not AutoRecovery.

   Two things about it are **unverified here** and should be checked on the machine before
   anything is automated: whether MERP's dialog actually blocks Word from answering Apple
   events (if it does not, a kill-and-warm loop may survive it and merely accumulate
   dialogs), and which suppression route the target Office build honours. §12.1 lists the
   candidates, why no script here can currently dismiss it, and what would settle each.

4. Possibly a "Word did not shut down correctly / open in Safe Mode?" prompt, distinct from
   MERP's. **Unverified** — I could not confirm this for the build these repos target, and no
   script here handles it.

### 12.1 Declining the report the way a human would — candidate solutions, none verified

The obvious fix is to do what the person does: click the decline button. There is a
structural reason no script here can, and it is not the button lists.

**No dialog handler in all three repos addresses MERP by name.** That part is measured.
All **13** `tell process` blocks across the 21 scripts target `"Microsoft Word"`; not one
targets the reporter, and no script mentions Microsoft Error Reporting, "Don't Send" or
"Send Report" anywhere:

```
$ grep -rhoE 'tell process "[^"]+"' <all three repos>
  13 tell process "Microsoft Word"
```

**Whether that makes them blind to it is one step further, and that step is not
established here.** It follows only if the dialog is owned by the `Microsoft Error
Reporting` accessibility process rather than by Word: a separate executable existing is
not by itself proof of which process owns a given window. Nothing in this corpus, and
nothing found in the public documentation, settles that. What would: the accessibility
dump below, on the target machine. Read the rest of this section as conditional on it.

If the reporter does own the window, then `word_dialog_watchdog.applescript` could not
dismiss this dialog even if its button list
were right, and `word-convert.sh`'s and `word-open-check.mjs`'s UI scrapes cannot see it
either. Fixing button names would change nothing; the process target is the blocker.

**Prevention first, then two unverified candidates, then a manual one-off, then a
non-recommendation.** Not a ranking of interchangeable options: only 1 and 2 are things a
batch can do for itself, 3 and 4 are settings whose effect on the *dialog* is unestablished,
and 5 is listed to be refused. None of them has been run here.

1. **Do not create the condition.** MERP is reported to fire on unclean exit, so a
   graceful `quit saving no` that actually succeeds should produce no dialog at all.
   **Target-build hypothesis, not a measurement:** the direct evidence is a single
   observation after one force-quit path, which shows the dialog appearing, not the
   clean quit preventing it. Worth testing first because it is the cheapest to test. This is the only option
   that is not suppression, and three of the four killing scripts already try the graceful
   quit first (§12's table): `word-probe-sweep.sh` (24–26), `word_compare_driver.sh` and
   `word-convert.sh` (130–134) all issue `quit saving no` before any signal.
   `word_validate_batch.py` is the exception and goes straight to `pkill -x` (25).

   That count answers "who gives Word a chance to exit cleanly", which is the question
   MERP turns on. It is **not** the same as "who never reaches an unclean kill" — only two
   stop short of SIGKILL (`word_compare_driver.sh` and `word-convert.sh`, both ending at
   `pkill -x`); `word-probe-sweep.sh` escalates to `pkill -9 -f`, so whenever its graceful
   quit fails it lands exactly where this candidate is trying not to be. Uncertainty: none about the mechanism, but a wedged Word is
   precisely the case where the graceful quit fails, which is when the kill — and the dialog
   — happen.
2. **A watchdog that targets the reporter's own process.** The direct analogue of clicking
   the button: `tell process "Microsoft Error Reporting"` and press the decline control.
   Unverified: the exact process name as System Events sees it, and the decline button's
   label on the target build. Both are one `System Events` dump away on the machine and
   neither should be guessed. This also inherits the Accessibility grant requirement.
3. **Office diagnostic-data preference.**
   `defaults write com.microsoft.office DiagnosticDataTypePreference ZeroDiagnosticData` is
   documented by Microsoft for Office 16.28 and later. **Unverified and the main open
   question:** that key governs the diagnostic-data *level*, and it is not established that
   it suppresses the MERP crash-report *dialog*. It may reduce what is sent while leaving the
   prompt intact.
4. **A manual one-off, not a candidate a script can use: MERP's own Preferences checkbox**, reached by launching
   `Microsoft Error Reporting.app` directly. Community-documented rather than
   Microsoft-documented. One-time and manual; no confirmed `defaults` key backs it, and I am
   not inventing one.
5. **Listed only to be refused — do not delete `Microsoft Error Reporting.app`** from the Word bundle's `SharedSupport/`.
   Circulates as a fix; **do not**. It modifies an application bundle, which is unsupported
   and is reason enough on its own. The further claims usually attached to it — that it
   breaks code signing, and that an Office update restores the file — are repeated here
   from circulation and were **not** established by the documentation search; do not rely
   on either as a reason.

**What would settle it**, in order of cost: force-quit Word once by hand, then on the next
launch dump `System Events` for every process and window to get the reporter's real process
name and button labels (settles 2); apply 3 and force-quit again to see whether the prompt
still appears (settles 3); and check whether the prompt blocks Word from answering Apple
events at all, since if it does not, a kill-and-warm loop may simply accumulate dialogs
rather than wedge (§12 residue 3).

**Who handles what today**

| Script | Escalation | AutoRecovery | `~$` cleanup | MERP prompt |
|---|---|---|---|---|
| `word-probe-sweep.sh` | `quit saving no` → 2 s → `pkill -9 -f` → 1 s | **Yes** — `find "$AUTOREC" -mindepth 1 -delete`. The only one in all three repos, and unscoped: that is the whole directory, not this run's entries (step 4 below) | Yes, in the loop | No |
| `word_compare_driver.sh` | `quit saving no` → 3 s → `pkill -x` (SIGTERM) → 2 s → relaunch + poll | No | Yes, after each restart | No |
| `word-convert.sh` | decline dialog → close → `quit saving no` → 1 s → `pkill -x`. **Assumes Word is the batch's alone:** it closes whichever document is active and quits everything `saving no` (130–134), so a human's unsaved work is discarded if any is open — and §8 lists a live human Word session as an edge case this corpus meets. Correct escalation, wrong precondition: it needs a no-open-documents check, or to close only the staged document | No | No | No |
| `word_validate_batch.py` | `pkill -x` only — **no graceful quit first** | No | No | No |
| everything else | no kill at all | — | — | — |

Two of these are half-right in opposite directions. `word_compare_driver.sh` has the correct
*escalation* (graceful quit, then SIGTERM via `pkill -x`, never `-9`) but no AutoRecovery
handling. `word-probe-sweep.sh` is the only one that cleans up at all, but it jumps to `-9`
with a pattern match (`-f`) that can match more than Word, and its wipe takes the
whole AutoRecovery directory rather than its own entries (step 4).

**The complete recipe**

1. `quit saving no` first, under a short `timeout`. A clean quit writes no recovery state and
   removes its own lock files — everything below is only for when that fails.
2. Escalate to `pkill -x "Microsoft Word"` — SIGTERM, exact-name match. `-x`, never `-f`:
   `-f` matches the full command line and can hit an unrelated process whose arguments
   contain the string.
3. Only then `pkill -9 -x`.
4. After any kill: clear the recovery state **this run** produced, so no Document
   Recovery pane appears, and `rm -f <dir>/~\$*.docx` in every folder **the run
   created** — not every folder it read. A driver that stages into Word's container
   never has Word open anything from the user's own folder, so a `~$` file sitting
   there is another Word's owner file, and deleting it tells that Word its document
   is unlocked. Excluding `~$*` from the work list, which the driver must do anyway,
   already covers the only reason to care about them there.
   **Scope the AutoRecovery deletion by mtime; do not wipe the directory.**
   `~/Library/Containers/com.microsoft.Word/Data/Library/Preferences/AutoRecovery/` is
   the user's, not the run's: it holds a recovery copy for every document Word has
   open, a human's unsaved work included, and §8 lists a live human Word session as an
   edge case this corpus meets. Take the run's start time and delete only entries
   modified at or after it — a file Word wrote before the run began is by definition
   not the run's.

   **The timestamp is the filter, not the control. The precondition is the control.**
   Word's AutoRecover interval defaults to 10 minutes
   ([Microsoft Support](https://support.microsoft.com/en-us/office/change-save-frequency-and-where-word-autorecovery-files-are-stored-ddd81816-39ff-48f4-989e-8bf1db78b2d9)),
   so a human's document open across a longer run has its recovery copy rewritten
   *after* the run started, and "newer than the run" sweeps it up exactly as the wipe
   would. Everything written during the run is ours only if nothing else was open when
   the run began. So establish that first: refuse to start while Word holds documents,
   and when an operator overrides that refusal, leave AutoRecovery entirely alone —
   they have just told you a document is open, which is precisely when mtimes stop
   being evidence of ownership. §15's `clean_after_kill()` gates on that precondition
   and falls back to touching nothing, paying the Document Recovery pane rather than a
   stranger's afternoon. The unscoped form (`find "$AUTOREC" -mindepth 1 -delete`) has
   neither guard.
   That clears Document Recovery and the lock files. It does **not** clear MERP's
   "send a report" prompt, which is a separate mechanism (residue 3) and is unhandled by
   every one of the 21 scripts audited here.

   The only route to that prompt this audit establishes is the one above: a graceful
   `quit saving no` that actually succeeds is not an unclean exit, so no dialog is raised
   (§12.1 candidate 1). That is also exactly what a wedged Word denies you, which is when
   the kill — and the prompt — happen. For that case the replacement pair implements
   §12.1 candidate 2, a watchdog on `tell process "Microsoft Error Reporting"` (§15); it is
   written but has never met a live prompt, so it logs every button label it encounters on
   first contact instead of assuming one.

   The two settings-based options — MERP's own Preferences checkbox and the Office-wide
   `DiagnosticDataTypePreference` — are **experimental and unverified** (§12.1 candidates 3
   and 4). Neither is established to suppress the *dialog*: the Microsoft page cited below
   governs the diagnostic-data level, and no `defaults` key is confirmed for the checkbox.
   Do not plan a batch around either, and do not treat either as having settled MERP. A
   kill loop raises the prompt on every recovery until something is confirmed to stop it.
5. **Better than cleaning up: do not generate the state.** Microsoft documents
   `Options.SaveInterval = 0` as AutoRecover's off switch: *"Returns or sets the time
   interval in minutes for saving AutoRecover information… Set the **SaveInterval** property
   to 0 (zero) to turn off saving AutoRecover information."* — [Options.SaveInterval property
   (Word), Microsoft Learn](https://learn.microsoft.com/en-us/office/vba/api/word.options.saveinterval).
   That is the VBA object model member, not the Preferences page cited in the sources below,
   which covers the GUI control (Preferences → Save) only.

   **Applicability is not established, and the page does not establish it.** That reference
   names no Office or Word version and does not distinguish Windows from Mac (verified
   against its source, `MicrosoftDocs/VBA-Docs/api/Word.Options.SaveInterval.md`, whose
   front-matter carries only `ms.date: 06/08/2017` and no applies-to). Nor does VBA
   availability imply an AppleScript equivalent — they are separate surfaces, and these
   scripts drive Word through AppleScript. So read the term off the local dictionary before
   relying on it, rather than guessing or assuming parity:
   `sdef /Applications/Microsoft\ Word.app | grep -i 'save interval'`. If it is absent, this
   step does not apply on that machine and step 4's first half stays necessary.

   Set it once for the batch session and restore it afterwards; a benchmark harness that
   permanently disables a human's autosave is not a good guest.
6. Re-warm before the next document. Do not let the next file's timeout pay for the cold
   start (§10).

For contrast: LibreOffice solves all of this with one launch flag, `--norestore`, which
`render/soffice.py` already passes. Word has no equivalent, which is why steps 4–5 have to be
done by hand.

---

## 13. If you keep four

`word_compare_driver.sh` + `word_compare_batch.applescript` for redlining,
`word-open-check.mjs` for validity (with §5.15 and §5.20 fixed first — bind its text probe
to the document it matched rather than to `active document`, and recycle Word after the
corrupt control before trusting anything measured afterwards), `render/word.py` for
DOCX→PDF. Between them they cover
every job the other seventeen do, and they are the four that record *why* each decision is
what it is.

The merges worth making are small and specific:

1. **Adopt `word-convert.sh`'s staging pattern everywhere** (§5.3): inside a container Word
   owns, a fresh `mktemp -d` per run, cleaned on exit. §6.1 settled the question, but not the way
   an earlier revision of this item said: grants **do** carry, once the panel flow has been
   completed with Word frontmost. What does not carry is a press made while Word is not
   frontmost, which is the state a focus-bouncer batch is deliberately in. So an
   out-of-container batch either pays a prompt per file or gives up the bouncer; staging is
   the only strategy that removes the choice instead of making it.
2. **Characterise §5.2's two axes** with the four runs in that section — the selector pair
   from a file, then the same pair inline to fill the unobserved cell. That settles how this
   machine behaves; it cannot settle the `-1708` report itself, whose script was never
   committed. Until the matrix is complete, family A stays as it is.
3. **Correct `CLAUDE.md` rule 1** per §5.1 — Apple Events consent is scoped to a
   (responsible client, target) pair and persists until revoked, reset with
   `tccutil reset AppleEvents`, or invalidated by re-signing; it is not per process and not
   permanent. The per-file prompt is Word's separate sandbox sheet, and staging is its cure.
4. Give the compare pipeline `word-open-check.mjs`'s **negative control**, so a clean corpus
   is provably clean rather than possibly unmeasured.
5. Give `render/word.py`'s **PDF path** the kill-and-warm that `word_validate_batch.py`
   already wraps around its validate path, and the calibrated budget that `validate_one`
   already has.
6. Add **AutoRecovery cleanup** to `word_compare_driver.sh`'s `restart_word`, in the form
   §12 step 4 actually specifies, and the graceful-quit-first escalation to
   `word-probe-sweep.sh`'s `kill_word` — whose wipe should be narrowed the same way.
   Each already has the half the other is missing. **Read as "mtime-scoped" this is
   unsafe, and §12 says so:** the timestamp is a filter, not the control. The control is
   the preflight condition that Word held no documents when the session started, because
   AutoRecover rewrites a person's open document every ten minutes and an mtime past the
   run's start does not make that copy ours. Where that condition is false or an operator
   has overridden it, the cleanup must leave AutoRecovery untouched and pay the Document
   Recovery pane instead.
7. Fix `word-convert.sh`'s **timeout layering** (§10) — including `-k` on the recovery
   path's own `timeout 10` wrappers — give it a bouncer or drop its `activate` (§5.9),
   give the staged output a name that cannot collide with the staged input (§5.14), bind
   the save to the document the open returned (§5.18), and reject `in_abs == out_abs`
   before the `rm` (§5.19). Until those land, do not use it for `docx` → `docx` at all:
   same name in another directory silently no-ops, and the same path deletes the input.
8. Parallelise `redline-sweep.sh`'s **generation loop** (§9) — it does not touch Word.

---

---

## 14. Code versus comment

This corpus is unusually well commented, which is a trap: several headers assert a property
the code implements one step short of. Every score above was re-derived from the code path,
and five claims did not survive. All of them are in the highest-scoring files — the unrolled
generated scripts have almost no comments and no gap between claim and behaviour.

### 14.1 `word_compare_batch.applescript` records `[ok]` before it evaluates base health

The header (lines 80–83) says the paragraph-count check exists so that an unreadable base
cannot be compared against. The code checks it — and then orders the outcomes wrongly:

```applescript
if failMsg is "" then
    set okCount to okCount + 1
    my logLine(logPath, "[ok] " & pairId)        -- logged FIRST
else
    ...
    return "POISON " & pairId
end if

if not baseHealthy then                          -- evaluated AFTER
    my logLine(logPath, "[warn] " & pairId & " :: base reported no paragraphs")
    return "POISON " & pairId
end if
```

A pair whose base Word could not read, but whose `compare` did not throw, is logged as
**both `[ok]` and `[warn]`**. `save as cmpDoc` has already written the output. And
`word_compare_driver.sh:213` greps only `^\[ok\] `, never `[warn]`:

```bash
{ grep -E '^\[ok\] ' "$LOG" || true; } | awk '{print $2}' | sort -u | while IFS= read -r id; do
    if [[ -s "$CORPUS/docx_redlines_word/${id}_redline.docx" || ... ]]; then
```

Both conditions are satisfied, so the pair is permanently marked done. The warning is
written to a log nothing reads. **C1: 1.00 → 0.85.** Fix: move the health evaluation above
the `failMsg` branch, or make the driver treat `[warn]` as `[fail]` **and delete the output
it already wrote**, so the pair is not left on disk looking complete. **C5: 1.00 → 0.85** for
the same defect — an unreadable base is a malformed item, and this records one as a success.

One qualification, from the artifact: `compare.log` contains **zero `[warn]` lines** across
its 1,188 entries. The defect is real in the code and would mis-record a pair if it fired,
but on this corpus it never has. Latent, not observed — which is why both scores are reduced
rather than collapsed.

### 14.2 `word_compare_driver.sh` kills a wedged `osascript` with SIGTERM

Line 261, in the stall-recovery branch:

```bash
kill "$pid" 2>/dev/null || true
```

Plain SIGTERM — on exactly the condition `word-open-check.mjs:248–251` documents as the one
where SIGTERM does not land: *"osascript blocked on an unanswered Apple event … IGNORES the
default SIGTERM, so a plain `timeout` never fires."* The driver recovers anyway, but by side
effect: `restart_word`'s `pkill -x "Microsoft Word"` unblocks the Apple event and the orphan
then exits. Until it does, a process the driver believes it killed can still write
`$RESULT_FILE`. **C2: 1.00 → 0.90.** Fix: `kill -9 "$pid"`.

One repo already knew this and the other did not — the finding is dated 9 Sep, the driver
4 Aug.

### 14.3 The watchdog clicks `Cancel` on a Grant File Access sheet

`word_dialog_watchdog.applescript:31` — the actual button list, in priority order:

```applescript
repeat with wanted in {"OK", "Ok", "Cancel", "Close", "Don't Save", "No"}
```

No `Grant`, no `Select`, no `Allow`. The header calls this "the most conservative dismiss
button available… never one that could confirm a destructive or format-changing action",
which is true and is a good policy — but a Grant File Access sheet's buttons are `Select…`
and `Cancel`, so the watchdog will click **Cancel** and actively deny Word the access it
asked for.

This is a constraint on §5.3, not just a score change: **the watchdog and out-of-container
staging are mutually incompatible** — and the consequence is observable, not theoretical:
the prompt recurs on every file, on folders already granted (§6.1). Family C is safe only
because it stages everything
inside the Group container, so the sheet never appears. Anyone resolving the staging
contradiction in favour of `redline-word-campaign.ts`'s outside-staging cannot also run this
watchdog without first teaching it to distinguish a permission sheet from an error dialog —
which `word-open-check.mjs` already does and this does not. **C4: 0.30 → 0.15.**

### 14.4 `redline-word-campaign.ts`'s bouncer outlives the process that starts it

```ts
const proc = spawn("osascript", ["-e", script], { detached: true, stdio: "ignore" });
```

The script is an unbounded `repeat … delay 0.5 … end repeat`. Cleanup exists only in
`main()`'s `finally`. The file contains **zero** `process.on("SIGINT" | "SIGTERM" | "exit")`
handlers.

So Ctrl-C during a campaign — the most likely way a long Word run ends — leaves a detached
`osascript` spinning at 2 Hz forever, forcibly yanking focus back to whatever app was
frontmost when the run started. That is the exact opposite of the bouncer's purpose, and it
survives the terminal session. **C3: 0.70 → 0.55.** Fix: register the stop function on
`SIGINT`/`SIGTERM`, or have the bouncer script poll for its parent's PID and self-exit.

### 14.5 `pkill -9 -f 'Microsoft Word'` matches the script's own helpers

`word-probe-sweep.sh:23–28`:

```bash
kill_word() {
  osascript -e 'tell application "Microsoft Word" to quit saving no' >/dev/null 2>&1
  sleep 2
  pkill -9 -f 'Microsoft Word' >/dev/null 2>&1
```

`-f` matches the full command line. The `osascript` on line 24 — and `warm_word`'s probe on
line 38 — both carry the literal string `Microsoft Word` in their arguments. The `sleep 2`
serialises them today, so this is latent rather than active, but the pattern also matches any
unrelated process whose command line mentions Word: another script, an editor with the file
open, a concurrent sweep. `word_compare_driver.sh:121` uses `pkill -x "Microsoft Word"`,
which matches the process *name* and cannot do this.

### 14.6 What did survive verification

Worth recording, because the rest of the audit leans on them:

- **`word-open-check.mjs`'s detector gate is real — on the path that runs it.**
  `detectorProven` is computed from the control file's actual verdict
  (`ctl.verdict === "REPAIR-PROMPT"`, line 871), consumed by `computeExitCode` (line 237),
  reported in the summary (line 1029), and covered by a unit test named *"returns 1 for a
  clean sweep when the detector was NOT proven"*. It is the only claim in the corpus that is
  asserted in a comment, implemented in code, **and** pinned by a test.

  **The `--no-selftest` opt-out (§5.11) costs C1 nothing** — the question was raised and is
  worth answering rather than leaving to the reader. (C1 is 0.85 rather than 1.00, but for
  §5.15's unrelated reason: `activeDocText()` reads `active document`, not the file just
  probed. The opt-out is not what moved it.) C1 is oracle
  integrity: whether a verdict can be trusted to mean what it says. On the default path the
  detector is proven or the run fails. On the opt-out path the exit-code contract states in
  its own docstring that skipping the control is a valid route to 0, so the verdict still
  means what the tool says it means; an operator who disables a control has not been misled
  by one. A score would be owed if the flag silently weakened the default, or if the contract
  claimed proof it did not have. Neither holds.
- **`redline-word-campaign.ts` genuinely never activates Word.** The only occurrence of the
  string `activate` in the file is the comment saying it never does.
- **`word-convert.sh`'s `activate` is genuinely unconditional** — inside the per-conversion
  `tell` block, before `open`, on every single call.
- **`render/word.py` really verifies its output** (`proc.returncode == 0 and pdf.exists()`),
  and `jobs` really is unused — `results = [convert_one(...) for docx in docs]`, a plain list
  comprehension.
- **`word_compare_driver.sh`'s hardcoded `${id}_redline.docx`** matches what
  `build_superdoc_pairs.py:383` writes. It reconstructs the output name instead of reading
  field 4 of the manifest it was given, which is unnecessary coupling, but it is not
  currently wrong.
- **`displayAlerts to false` is executed in nine files** — the six unrolled batches,
  `batch_word_to_pdf.scpt`, `word_screen_sources.applescript`,
  `word_compare_batch.applescript`. The two further matches, in `word_compare_driver.sh:12`
  and `word_dialog_watchdog.applescript:6`, are comments explaining what it does *not*
  suppress.

### 14.7 The pattern

Comment quality predicts code quality here, but it inverts at the top: the three files with
the most carefully reasoned headers are the three where a header describes an intent the code
implements one step short of — a check evaluated after the record it should gate, a kill that
cannot land on the process it targets, a cleanup path that only runs on the happy exit. Each
is a single line to fix. None would be found by reading the comments, which is what makes
them worth writing down.

---

## 15. The replacement pair

The audit's conclusions are implemented, and they are implemented in **one** of the three
repositories this document spans (§1): the `neurotic_docx_bench` repo, at
`scripts/word_pdf.py` and `scripts/word_redline.py`, with their specs at
`tests/test_word_pdf.py` and `tests/test_word_redline.py`.

**This file is copied verbatim into all three repos**, so in a `jubarte-first` or
`jubarte-redlines` checkout there is no `scripts/word_pdf.py` and no
`neurotic_docx_bench/` directory — nothing at that path to run or inspect. Read this section
there as a cross-reference to the sibling repository, not as a description of the checkout
you are in. Everything below is committed code in `neurotic_docx_bench`, not a proposal.

They are a pair on purpose: the redline script imports the PDF script rather than restating
it, so the process lifecycle, the container staging, the watchdogs and the PDF export exist
once.

| | `word_pdf.py` | `word_redline.py` |
|---|---|---|
| Input | one folder of `.docx` | folder A and folder B |
| Work | export each to PDF | compare each A against its B (Word's own Compare Documents) |
| Output | `.pdf` beside the source, or into `--out` | `--emit pdf` (default), `docx`, or `both` |
| Pairing | n/a | filename match, or `--cross` for every A against every B; `--swap` reverses which side is the base |
| Owns | `WordSession`, `Stage`, `Watchdogs`, `export_pdf`, `iter_docx` | `compare_pair`, pairing, emit rules — everything else is imported |

### What each finding turned into

| Finding | In the code |
|---|---|
| §5.10 paths interpolated into AppleScript | `osa()` runs `osascript -e SCRIPT arg1 arg2` with `on run argv`; no path is ever concatenated into source |
| §5.5 `~$*.docx` treated as documents | `is_word_temp()` / `iter_docx()` exclude them at every entry point |
| §6.1 the sandbox prompt | Inputs **and** outputs staged inside `~/Library/Containers/com.microsoft.Word/Data/tmp`, where no grant is asked for at all; a fresh `mktemp` directory per run (§5.3) |
| §6.1 grant handlers that press without activating | `_PRESS_ACTIVATED` activates Word, `AXPress`es the grant, then hands focus straight back — the pattern no script in the corpus had in full |
| §14.3 watchdog clicking `Cancel` on a Grant sheet | Grant labels are tried first and accepted; `Cancel` is only reachable once no grant button matched |
| §12.1 Microsoft Error Reporting | A **second** watchdog on `tell process "Microsoft Error Reporting"`. Every button label it meets is logged the first time, so the real control names come from a live run instead of a guess |
| §14.1 success recorded before health | Paragraph count is checked before the compare runs; the comparison result is found by exclusion, never by whichever document is frontmost |
| §14.2 `SIGTERM` on a wedged `osascript` | The timeout SIGKILLs **its own child**, which is what `subprocess.run` already does (`Popen.kill()`, never `terminate()`) — and SIGKILL is the part that matters against a blocked `osascript`, which ignores SIGTERM. Deliberately **no `pkill osascript`**: it would match the watchdogs' own polls, every one of which is an `osascript`, plus anything the user is running |
| §14.5 `pkill -9 -f` matching helpers | `pkill -x` only, by exact process name, and escalated: `quit saving no` → `-x` → `-9 -x` |
| §12 Document Recovery after a kill | `clean_after_kill()` removes AutoRecovery entries and `~$` files **modified at or after this session started**, then re-warms. Never the whole directory. And the timestamp only proves ownership because `preflight` established that Word held **zero** documents at startup: under `--allow-open-docs` that premise is gone, so AutoRecovery is skipped entirely rather than filtered, and the Document Recovery pane is the price. The `~$` sweep runs only over the staging directories this run made: Word opens the staged copy, never the user's original, so a lock file in their folder is someone else's (§12 step 4) |
| §10 timeouts that must cover a cold start | Word is pre-warmed once with `open -g`; per-document budgets cover work only |
| §5.8, §5.20 one poison file costing the batch | Any failure recycles Word before the next item |
| §9 concurrency | Neither script takes `--jobs`. Word is single-instance and user-session-bound; a second worker would drive the same instance |

### Malformed documents: decline, close, skip

A file Word cannot read is an ordinary outcome in this corpus, not an incident. The contract
is the same in both scripts and both modes:

1. **Answer the repair prompt "No."** Matched on *window text* —
   `Word found unreadable content`, `Do you want to recover the contents of this document` —
   not on a button name, so it cannot fire on an unrelated alert. "Yes" would make Word
   rewrite the document, and the benchmark would then be measuring Word's repair rather than
   the file it was handed. If the button is unreachable, Escape. This is
   `word-convert.sh`'s `decline_unreadable_dialog`, which is the one handler in the audited
   corpus that gets this right; it now runs *before* the generic dismiss handlers, which
   would otherwise press "OK" on a repair sheet.
2. **Close whatever is open** — `close every document saving no`.
3. **Record it and move to the next item.** No restart. A malformed document costs one
   failed open, not a ~30s Word relaunch.

A restart, when one does happen, cleans **only this run's** residue: AutoRecovery entries
and `~$` lock files modified at or after the session started, never the whole AutoRecovery
directory, which holds the recovery copy of every document Word has open including a human's
unsaved work (§12 step 4). The cutoff carries that guarantee only under the precondition
`preflight` enforces — no document open when the run began — because Word autosaves every
10 minutes and would stamp a human's copy mid-run. When the operator overrides the
precondition with `--allow-open-docs`, AutoRecovery is left untouched and the run says so.

**The override protects the documents, not just the residue**, which an earlier revision of
this pair got wrong in the direction that matters. `--allow-open-docs` exists so the batch
can coexist with a person's Word session, and every cleanup path was closing their documents
anyway: `_EXPORT_PDF` ran `close every document saving no` after a *successful* save, so no
failure was needed to lose their work. Now the export closes only the document it opened;
`recover_after_failure` closes everything only when `preflight` established there was
nothing else to close, and otherwise closes the staged document by name; and `recycle`,
which quits Word `saving no`, refuses outright when the run did not start clean. The cost is
stated up front rather than discovered: the preflight message says the override disables
Word restarts, so a wedged Word ends the run instead of being recovered.

**The redline script declines the override entirely** (`redline_preflight`). Its correctness
rests on the precondition, not merely its tidiness: `_COMPARE` identifies the result by
exclusion, walking `document i` for the one whose name is not the base's, because `compare`
returns its result as a new document and that is how a script names the one it means (§5.11
records the mistaken premise this replaced). That walk is sound exactly while every open
document is ours. With a person's document open it
can select theirs and save it as the redline, which is a wrong artifact rather than a
missing one, and wrong artifacts are what this pair exists to prevent.

**Word is restarted only on evidence that Word itself is the problem**, which is two
conditions, not one:

- `close every document saving no` leaves documents still open, i.e. Word did not come back
  clean; or
- **three failures in a row** (`--poison-streak`). This is the §5.20 finding: after a bad
  document Word keeps answering Apple events while returning EMPTY documents for every later
  open, with no error at all — one poison file cost 203 others
  (`word_screen_sources.applescript`'s header, 16–20). The paragraph-count check on
  every open is what catches that, and a run of failures is what it looks like from outside.

In one-osascript mode the same three steps are the batch script's `try … on error … close
every document saving no … end try`, which sits **inside** the `repeat` over manifest rows —
so it is per item by construction, even though the whole folder is one script: an error on
one row is caught, logged and stepped over without leaving the loop.

The repair prompt is answered by the watchdogs, and they are genuinely concurrent because
they are **not** part of that script. `Watchdogs` runs Python threads, and each poll shells
out to its own `osascript` process. So while the batch script's single `osascript` sits
blocked on `open`, a second and third `osascript` are free to inspect Word's windows and
press a button. One monolithic script for the *work* does not mean one process on the
machine.

### One osascript for the whole job

This is the **default** in both scripts; `--no-one-osascript` and
`--no-one-redline-osascript` are the opt-outs. `word_pdf.py` runs the folder inside a single
monolithic AppleScript. `word_redline.py` runs **two**: every comparison, then every PDF.
Two, not one, because Word yields a comparison only as an open document — every redline
`.docx` has to exist on disk before anything can be rendered from it, so the second script's
input list is the first script's output list, and one wedge would otherwise lose both halves
of the work. The second script is `word_pdf`'s own batch script unchanged: a redline `.docx`
is a `.docx`.

What this actually **saves** is a process spawn and an Apple-event connection *per item* —
one of each for the whole folder instead of one of each per document. It is
**not** the per-osascript permission prompt that `CLAUDE.md` rule 1 claims, which §5.1 found
unsupported — TCC automation grants are keyed on the responsible client app and persist.
The mode is offered because the folder-sized batch is the shape the old corpus used.

What it costs:

- **Every input is staged before the run starts**, because the manifest references all of
  them at once. For a 1,224-document folder that is 1,224 copies live in Word's container
  until the run ends.
- **Nothing can act between items.** No per-item recycle, no per-item budget — only the
  batch script's own `try` block.

Neither is a reason to avoid it, and both are what `--no-one-osascript` and
`--no-one-redline-osascript` buy back when a run needs per-item recycling or per-item
budgets. The monolithic run remains the default.

**Wedges are resumed, not retried wholesale.** The batch script writes `[ok]` or `[fail]`
per item and `[done]` at the end. Three outcomes, and they are not interchangeable: `[ok]`
and `[fail]` are final, because a malformed document will be malformed next pass too; an item
with **no line at all** was never reached, which is the only case worth another pass. Those
items alone go into the next manifest, after Word is recycled — so a wedge costs the
remainder of one pass, not the batch. Three passes by default, then the item is reported as
never reached.

Two details that exist because a batch is not a loop. Paths reach the script through a **TSV
manifest** named by one of exactly two argv arguments, never on argv itself — a thousand
absolute paths would be tens of thousands of characters against `ARG_MAX`, and staged names
are sanitised (`safe_stage_name`) because a tab in a filename would split one manifest row
into two and silently misalign every field after it. And the summary labels batch timings
**"seconds per document (batch avg)"** rather than "median seconds", because a batch pass
times the whole run and cannot say what any single document cost.

### What they deliberately do not do

- **No parallelism.** See §9 — it needs separate macOS user sessions or VMs, not threads.
  One-osascript mode is not parallelism: it is still one document at a time, in one Word.
- **No PDF preset control.** `save as … file format format PDF` inherits the last
  "Optimize for" choice from Word's own Save As dialog; nothing in AppleScript sets it.
  `--check-preset` (on by default) prints the reminder to pick the second option,
  "Best for printing", once by hand.
- **No markup-display control.** A redline PDF renders tracked changes the way Word is
  currently set to show them. Confirm one redline by hand before committing a batch to it.
- **No repair of a document Word refuses.** A missing output after a full run is the
  worklist, not a bug in the driver.

`--emit pdf` is the default and it discards the tracked-changes `.docx` once the PDF is
rendered. `--emit both` keeps it. Both come from the same saved file, so the PDF always
matches the `.docx` that `--emit both` would have written.

## Sources for the external claims

- SIGKILL produces no **Apple** crash report, and watchdog terminations do: [Apple, EXC_CRASH (SIGKILL)](https://developer.apple.com/documentation/xcode/sigkill) · [Addressing watchdog terminations, Apple](https://developer.apple.com/documentation/xcode/addressing-watchdog-terminations) · [How macOS reports crashes, The Eclectic Light Company](https://eclecticlight.co/2021/12/10/how-macos-reports-crashes/)
- Office for Mac diagnostic-data preference `DiagnosticDataTypePreference` (`ZeroDiagnosticData`, Office 16.28+): [Use preferences to manage privacy controls for Office for Mac, Microsoft Learn](https://learn.microsoft.com/en-us/microsoft-365-apps/privacy/mac-privacy-preferences). Whether it suppresses the MERP crash-report dialog is **not** established by that page — see §12.1.
- UI scripting addresses one process at a time via `tell process "<name>"`, which is why a handler aimed at Word cannot see a dialog owned by another process: [Automating the User Interface, Apple](https://developer.apple.com/library/archive/documentation/LanguagesUtilities/Conceptual/MacAutomationScriptingGuide/AutomatetheUserInterface.html) · [AppleScript Essentials: User Interface Scripting, MacTech](http://preserve.mactech.com/articles/mactech/Vol.21/21.06/UserInterfaceScripting/index.html). Apple's page carries the claim on its own; the MacTech link is corroboration and returned **HTTP 403** when checked from this environment, which is as likely to be a crawler restriction as a dead page — unconfirmed either way, because archive.org was also unreachable from here.
- Microsoft Error Reporting is a separate Office application with its own Preferences, independent of ReportCrash: [Get rid of Microsoft Error Reporting 2.2 on Mac, Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5650864/get-rid-of-microsoft-error-reporting-2-2-on-mac) · [Microsoft Office error reporting popups on Mac, The Mac Observer](https://www.macobserver.com/tips/microsoft-office-error-reporting-popups-on-mac/) (this second link did not resolve at all from this environment; the Microsoft Q&A carries the claim). **Note what this does and does not support:** that MERP is a separate application is documented. That the crash dialog a person sees is *owned by* that process, rather than by Word, is the step §12.1 marks as unestablished. That Word raises it after a `pkill -9` **with no document open** is Arthur's direct observation on the target machine, not a documented claim.
- Document Recovery opens when AutoRecover files exist: [Recover files in Office for Mac, Microsoft Support](https://support.microsoft.com/en-us/office/recover-files-in-office-for-mac-6c6425b1-6559-4bbf-8f80-4f038402ff02)
- AutoRecover's off switch in the object model, quoted in §12: *"Set the **SaveInterval** property to 0 (zero) to turn off saving AutoRecover information."* — [Options.SaveInterval property (Word), Microsoft Learn](https://learn.microsoft.com/en-us/office/vba/api/word.options.saveinterval). That page names **no** Office or Word version and does not distinguish Windows from Mac (checked against its source, `MicrosoftDocs/VBA-Docs/api/Word.Options.SaveInterval.md`, whose front-matter carries only `ms.date: 06/08/2017`), and VBA availability does not imply an AppleScript equivalent — §12 says what to check locally instead.
- AutoRecover interval and storage location, the GUI control only: [Change save frequency and where Word AutoRecovery files are stored, Microsoft Support](https://support.microsoft.com/en-us/office/change-save-frequency-and-where-word-autorecovery-files-are-stored-ddd81816-39ff-48f4-989e-8bf1db78b2d9)
- TCC automation grants are keyed on the responsible client app, not the process: [Avoiding AppleScript Security and Privacy Requests, Scripting OS X](https://scriptingosx.com/2020/09/avoiding-applescript-security-and-privacy-requests/) · [AppleScript Permissions on macOS, MAMP Documentation](https://documentation.mamp.info/en/MAMP-PRO-Mac/FAQ/General/AppleScript-Permissions-on-macOS/)
