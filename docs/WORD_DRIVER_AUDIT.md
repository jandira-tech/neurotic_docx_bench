# Word driver audit

Audit of every script across `neurotic_docx_bench`, `jubarte-first` and `jubarte-redlines`
that drives Microsoft Word for Mac to redline a document or export a PDF.

**Scope:** 21 files. **Read:** 21 Sep 2026, at the checked-out revisions.
**Method:** code-path reading plus direct measurement of the scripts (open counts, lock-file
entries, set overlaps). No macOS, Word or `osascript` was available in this environment, so
nothing here is from a run — every claim is traceable to a file and line, to a documented
Microsoft/Apple behaviour, or is marked as unverified.

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
  223-file screen where one poison document took 203 others with it (§6, C2), and the
  34-real-then-88-phantom probe sweep (§5.8).
- **C6/C7** because 102 of family A's work items are lock files (§5.5) and because the one
  place real parallelism is available — Rust redline generation in `redline-sweep.sh` — runs
  serially.

---

## 3. Scorecard

| File | Repo | C1 | C2 | C3 | C4 | C5 | C6 | C7 | Σ | Tests |
|---|---|---|---|---|---|---|---|---|---|---|
| `word_compare_driver.sh` | ndb | 0.85 | 0.90 | 0.85 | 1.00 | 0.95 | 0.95 | 0.75 | **6.25** | none |
| `word-open-check.mjs` | jf | 1.00 | 0.80 | 0.90 | 0.70 | 1.00 | 0.95 | 0.40 | **5.75** | 25 |
| `word_compare_batch.applescript` | ndb | 0.85 | 0.90 | 0.80 | 0.90 | 0.85 | 0.90 | 0.50 | **5.70** | none |
| `word_screen_sources.applescript` | ndb | 0.95 | 0.90 | 0.80 | 0.85 | 1.00 | 0.75 | 0.40 | **5.65** | none |
| `word-convert.sh` | jf | 0.70 | 0.70 | 0.80 | 0.95 | 0.90 | 0.85 | 0.30 | **5.20** | none |
| `redline-word-campaign.ts` | jf | 0.95 | 0.70 | 0.55 | 0.60 | 0.90 | 0.70 | 0.50 | **4.90** | none |
| `word_dialog_watchdog.applescript` | ndb | 0.70 | 0.90 | 0.80 | 0.15 | 0.70 | 0.70 | 0.80 | **4.75** | none |
| `word_validate_batch.py` | ndb | 0.70 | 0.80 | 0.85 | 0.25 | 0.85 | 0.70 | 0.30 | **4.45** | none |
| `render/word.py` | ndb | 0.75 | 0.65 | 0.90 | 0.25 | 0.80 | 0.80 | 0.25 | **4.40** | 15 |
| `word-probe-sweep.sh` | jr | 0.60 | 0.90 | 0.40 | 0.15 | 0.85 | 0.70 | 0.20 | **3.80** | none |
| `run_batch_retry.sh` | ndb | 0.20 | 0.40 | 0.60 | 0.80 | 0.50 | 0.60 | 0.20 | **3.30** | none |
| `redline-sweep.sh` | jr | 0.80 | 0.30 | 0.80 | 0.10 | 0.35 | 0.70 | 0.20 | **3.25** | none |
| `word-open-probe.sh` | jf | 0.60 | 0.40 | 0.70 | 0.10 | 0.50 | 0.55 | 0.20 | **3.05** | none |
| `word-open-probe.sh` | jr | 0.60 | 0.40 | 0.70 | 0.10 | 0.50 | 0.55 | 0.20 | **3.05** | none |
| `batch_word_to_pdf.scpt` | ndb | 0.20 | 0.25 | 0.30 | 0.15 | 0.35 | 0.25 | 0.10 | **1.60** | none |
| `batch_convert.scpt` | ndb | 0.15 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.10** | none |
| `batch_jubarte_lossless_pdf.applescript` | ndb | 0.15 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.10** | none |
| `batch_jubarte_rs_probe_pdf.applescript` | ndb | 0.15 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.10** | none |
| `batch_sanity_pdf.applescript` | ndb | 0.15 | 0.30 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.05** | none |
| `batch_inline.applescript` | ndb | 0.10 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.05** | none |
| `batch_inline2.applescript` | ndb | 0.10 | 0.35 | 0.05 | 0.15 | 0.30 | 0.05 | 0.05 | **1.05** | none |

`ndb` = neurotic_docx_bench, `jf` = jubarte-first, `jr` = jubarte-redlines.

Scores marked in §14 were revised downward after re-verifying the code paths against the
header comments that assert them. The top three are not interchangeable:
`word_compare_driver.sh` is the best at surviving Word; `word-open-check.mjs` holds the only
unreduced C1 in the corpus and is the only script that proves its own detector works before
trusting a clean result; `word_compare_batch.applescript` has the best *idea* of how to know
what it produced (identification by exclusion) and implements it one step short (§14.1).

---

## 4. Where they genuinely differ

| Axis | Positions taken, and by whom |
|---|---|
| **Script delivery** | Monolithic unrolled (family A, one `osascript` for 200–1,224 files) · per-file heredoc (`run_batch_retry.sh`, `word-convert.sh`) · script file with argv (family C) · `osascript -e` with argv (`render/word.py`, the TS/MJS harnesses) |
| **Sandbox staging** | App container `~/Library/Containers/com.microsoft.Word/Data/tmp` (`run_batch_retry.sh`, `word-convert.sh`) · Group container `~/Library/Group Containers/UBF8T346G9.Office` (`word_compare_driver.sh`) · deliberately outside (`redline-word-campaign.ts`, `word-open-check.mjs`) · none (family A, `render/word.py`, the probes) |
| **Alert strategy** | `displayAlerts false` only (families A and C) · UI detection only (`word-convert.sh`, the TS/MJS harnesses) · both (family C, via the watchdog) · neither (`run_batch_retry.sh`, `render/word.py`, the probes) |
| **Result identification** | `active document` / `front document` (family A, `run_batch_retry.sh`, `word-convert.sh`, `render/word.py`) · indexed by exclusion (`word_compare_batch.applescript`) · document count must rise (`redline-word-campaign.ts`) · window named for this file (`word-open-check.mjs`) |
| **Poison recovery** | None (family A) · close-all between items (`run_batch_retry.sh`) · quit + `pkill -x` + relaunch-poll (`word_compare_driver.sh`, `word-convert.sh`) · plus AutoRecovery wipe (`word-probe-sweep.sh`, the only one) · kill-after-each-failure (`word_validate_batch.py`) |
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
   or writes outside its container. This one *is* per file or per folder, and it is the one
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

### 5.2 The `-1708` folklore is confounded, and one script is evidence against it

`corpus/word_based/docx_redlines_word/README.md` and `CLAUDE.md` both state the rule as
*inline heredoc works, `.scpt` file fails with `-1708`*. But the broken example they cite
uses `active document`, and `word_compare_batch.applescript` — a **file** run as
`osascript word_compare_batch.applescript …` — calls `save as cmpDoc` on an explicitly
indexed `document i`, successfully, and the entire August pipeline depends on that.

Two data points, one confound:

| | `active document` | `document i` |
|---|---|---|
| **inline** | works (`run_batch_retry.sh`, `word-convert.sh`) | — |
| **file** | reported `-1708` (`compare-documents.scpt`) | **unverified** — see below (`word_compare_batch.applescript`) |

The `document i` + file cell is **not** established by a run. No Word or `osascript` was
available here, so what the source shows is that `word_compare_driver.sh` invokes
`word_compare_batch.applescript` as `osascript <file>` and that its entire done-accounting
assumes the `save as` produces output — i.e. the August pipeline is *built on* that cell
being true, which is suggestive but is not evidence that it is. Treat it as unverified until
someone runs it.

The disambiguating experiment is four lines: same `save as` from a file, once against
`active document`, once against `document 1`. If file-vs-inline is not the variable,
`batch_word_to_pdf.scpt` is repairable and family A never needed to exist.

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

This is the most expensive unresolved disagreement in the corpus, because it decides whether
an unattended batch runs at all.

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

- **Safe by construction:** `word-convert.sh` passes paths as `argv` into a quoted heredoc
  and says so in its header. `render/word.py` and the TS/MJS harnesses get the same from
  `osascript -e` plus argv.
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
- **Filename-verified dialogs.** `redline-word-campaign.ts` requires the dialog text to name
  *this* file, killing false positives from stale dialogs, and requires the document count to
  rise before returning CLEAN, killing the false negative the comment records as having
  masked CU003 in the first run.
- **Identification by exclusion.** `word_compare_batch.applescript` walks `document i` and
  takes the one whose name is not the base's — because if compare silently produced nothing,
  `active document` is still the base. It also notes that `repeat with d in documents` makes
  AppleScript send `count` to `every document`, which that Word build rejects outright.

### 5.12 Two of 21 have tests, and both test the right thing

`word-open-check.mjs` exports `REPAIR_DIALOG_RE`, `parseUiLines`, `windowAlertTexts`,
`findDialogs` and `computeExitCode` as pure functions, covered by 25 specs that run on Linux
with no Word present. `render/word.py` does the same with `_budget`,
`_interpret_modal_probe` and `_interpret_open_exit`, covered by 15 tests including
`test_budget_exhausted_without_modal_is_unjudgeable`.

That is the entire verdict-deciding surface of both harnesses, testable off-platform. The
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
- `word-open-probe.sh` exists twice, byte-identical apart from an SPDX header and one word,
  in two repos with different licences (GPL-3.0-only and AGPL-3.0-only). No shared source, so
  they will drift.
- `CLAUDE.md` cites `report_one/scripts/compare-docs.sh` and
  `report_one/scripts/redline-word-pdf.py` as the proof for the focus-bouncer recipe. Neither
  file, nor a `report_one/` directory, exists in any of these three checkouts — that claim
  could not be verified here.

---

## 6. Permission prompts over many files (C4)

Two mechanisms, routinely conflated (see §5.1).

**P1 — TCC Apple-events automation.** One prompt per (terminal app → Word), persisted.
Not per process, not per file. Only `word_compare_driver.sh:64–72` handles it at all: it
probes with a cheap `get name`, and if it fails, exits with the exact one-liner to run. That
is the correct treatment — this prompt cannot be dismissed programmatically, so the only
options are "already granted" or "stop and tell the human".

**P2 — Word's "Grant File Access" sandbox sheet.** Per file or per folder, for paths outside
Word's container. Three viable strategies:

| Strategy | Who | Cost |
|---|---|---|
| Stage inside the container | `run_batch_retry.sh`, `word_compare_driver.sh`, `word-convert.sh` | One copy per file; zero prompts |
| Dismiss via Accessibility AXPress | `word-convert.sh`, `redline-word-campaign.ts`, `word-open-check.mjs` | A UI round-trip per file; needs the Accessibility grant |
| Grant the folder once by hand | `CLAUDE.md` notes it persists | One human interaction per folder, per machine |
| Nothing | family A, `render/word.py`, all three probes/sweeps | A human at the keyboard, or a hang |

**Scores and why**

| File | C4 | Rationale |
|---|---|---|
| `word_compare_driver.sh` | 1.00 | Only script that handles both: staging eliminates P2, an explicit precheck fails fast on P1 with instructions. Documents the arithmetic it is avoiding. |
| `word-convert.sh` | 0.95 | Container staging *and* active Grant-dialog handling (`Select…` then `key code 36`). Belt and braces. No P1 precheck. |
| `word_compare_batch.applescript` | 0.90 | Inherits staging; header forbids pointing it at repo paths. |
| `word_screen_sources.applescript` | 0.85 | Same, via the staged dir passed as argv. |
| `run_batch_retry.sh` | 0.80 | Full app-container staging for both src and out. No P1 precheck, no dialog fallback if staging is bypassed. |
| `word-open-check.mjs` | 0.70 | AXPress dismissal, and it *distinguishes* the permission sheet from a repair dialog rather than draining both — a permission prompt is recorded, never counted as invalid. |
| `redline-word-campaign.ts` | 0.60 | AXPress dismissal (Grant/Open/Select/Allow, up to 8 passes) but stages outside on purpose, so it pays a UI round-trip per file and hard-depends on Accessibility. |
| `word_dialog_watchdog.applescript` | 0.30 | Deliberately clicks only OK/Cancel/Close/Don't Save/No — never Grant/Allow. Correct as a safety policy, but it means the watchdog does not help with P2, and a "Cancel" landing on a Grant sheet would actively deny access. |
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
| `word-open-check.mjs` | 1.00 | Verdict taxonomy OPENED-CLEAN / REPAIR-PROMPT / ERROR / BLOCKED; dialog text retained verbatim; per-file screenshot as evidence; an unmatched modal becomes ERROR, never a silent clean. |
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
| `word-open-check.mjs` | 0.95 | BLOCKED verdict when Accessibility is revoked mid-run; `SIGKILL` because a blocked `osascript` ignores SIGTERM; `rm -f` before `zip` because zip *updates* archives; quits Word only if it launched it; records the strict-packages corpus gap rather than silently skipping it. |
| `word_compare_batch.applescript` | 0.90 | Skips existing output; tolerates blank rows and wrong field counts; start/count slicing; avoids `repeat with d in documents` because that Word build rejects `count of every document`. |
| `word-convert.sh` | 0.85 | Arg count, file existence and extension whitelist; `mkdir -p`; per-run `mktemp -d` with `trap cleanup EXIT`; argv-safe paths; records that `format Unicode text` is rejected by this build; removes stale output before starting. |
| `render/word.py` | 0.80 | Platform gate; skip-existing with `force`; reference calibration so a slow machine does not read as a broken document; reaps killed processes; `_close_active_document` with an Escape fallback. Globs `*.docx` including `~$`; no staging. |
| `word_screen_sources.applescript` | 0.75 | `\|\| true` so an empty dir does not error; skips already-logged entries; three failure shapes. No `~$` filter. |
| `word-probe-sweep.sh` | 0.70 | `[ -e ]` guard for an empty glob; deletes `~$`; pays the cold start explicitly; wipes AutoRecovery; `set -uo pipefail` without `-e` deliberately. Hardcoded `PROBE` path. |
| `redline-sweep.sh` | 0.70 | Rejects unknown flags; three preconditions; per-sweep manifest; missing-baseline hard fail. `IFS=,` breaks on quoted commas; `BASH_SOURCE` under a `zsh` shebang. |
| `word_dialog_watchdog.applescript` | 0.70 | `try`-wrapped throughout; handles sheets and standalone dialogs. No self-exit if orphaned by a killed parent. |
| `word_validate_batch.py` | 0.70 | `--limit`; empty-dir guard; `mkdir(parents=True)`; flush per row. Globs `~$` files. |
| `redline-word-campaign.ts` | 0.70 | `pairs.json` existence check; closes only `campaign-*` documents; bouncer in a `finally`. `process.cwd()`-relative staging; first-N "sample". |
| `run_batch_retry.sh` | 0.60 | Excludes `~$` in three places; numeric sort with a documented reason; `PAIRS < 1` guard; `mkdir -p`; resume. Requires the `file_N.docx` convention; mutates `SOURCE_DIR` in place when stamping. |
| `word-open-probe.sh` ×2 | 0.55 | File-existence check; escapes backslash and quote; `count of documents > 0` guard. Newline in a filename still breaks out; `$delay` interpolated unvalidated. |
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
| `word_dialog_watchdog.applescript` | 0.80 | It *is* the concurrent component: a second process watching Word's UI while the batch holds the Apple-event channel. The only true concurrency in the corpus. |
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
| `word-convert.sh` | outer `timeout 90`, inner `with timeout of 240`, poll loop 120 × 2 s = 240 s | **Incoherent — the only clearly wrong set.** 90 < 240, so the inner budget and the loop's tail are unreachable and the effective budget is 90 s, which is too short for a large DOCX→PDF. The loop does check `kill -0` and break, so nothing hangs; it is simply a 90 s cap wearing a 240 s costume. Fix: set the outer to inner + slack, or drop a layer. |
| `word-convert.sh` UI probes | `timeout 8` / `10` / `12` | Fine. These are sub-second queries with a generous kill switch. |
| `render/word.py` `convert_one` | 180 s flat | Reasonable for docx→PDF, but it is a flat constant in the same module where the validate path got the calibrated treatment. Inconsistent; the calibration belongs here too. |
| `word_validate_batch.py` | `--timeout 25` default | **Too little, and it silently disables the calibration.** It overrides the module's 60 s *downward* and passes no `reference`, so `_budget` degenerates to a flat 25 s. Large documents come back UNJUDGEABLE, and the CLI treats UNJUDGEABLE as not-failing — so slow documents quietly leave the denominator rather than showing up as a problem. |
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
| `word-convert.sh` | 1 attempt, then reset Word and exit 3 | Correct. It does not retry into a degraded Word; it hands the decision to the caller. |
| `render/word.py` | 1 attempt. `_close_active_document` tries close → Escape → close | Correct — those three are cleanup steps, not retries of the work. |
| `render/soffice.py` (contrast) | `retries=1`, each attempt in a **fresh isolated profile** | The right model, and the one Word cannot copy cheaply: Word's equivalent of a fresh profile is a full relaunch. |
| `redline-word-campaign.ts` | 2 attempts, no backoff, **no Word recycle between them** | **The weakest retry in the corpus.** Retrying the same open against the same possibly-degraded Word is the one thing the rest of these repos proves does not work (§5.4's cascade, `word_screen_sources`' 203-file contamination). Either kill and warm between attempts, or drop the second attempt and report. |
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

First, a correction that removes a whole class of speculation: **a direct `pkill -9` from
the shell does not produce a macOS crash report or a "quit unexpectedly" dialog.**
ReportCrash fires on uncaught exceptions — SIGSEGV, SIGABRT, SIGILL, SIGBUS — and a signal
you send yourself is a termination, not a crash, so it leaves no crash log.

Be precise about the scope of that claim: `EXC_CRASH (SIGKILL)` *does* appear in crash
reports when the **system** kills a process — a watchdog termination carries
`EXC_CRASH (SIGKILL)` with `EXC_CORPSE_NOTIFY` and a termination reason such as
`0x8badf00d`. That is a different path from the one these scripts take, and none of them can
trigger it by calling `pkill`. The conclusion stands for our case only: nothing here needs
`defaults write com.apple.CrashReporter DialogType none`; that would be a system-wide change
for a problem that does not exist.

What a killed Word *actually* leaves behind:

1. **AutoRecovery files → the Document Recovery pane on next launch.** Microsoft's own
   documentation is that Document Recovery opens automatically when AutoRecover files exist.
   That pane appears *before* any script command runs, so `set displayAlerts to false` cannot
   reach it — the next `open` simply never gets answered.
2. **`~$*.docx` owner/lock files** in every folder Word had a document open from. A killed
   Word never removes them. The next glob picks them up as work items and each costs a full
   AppleEvent timeout (§5.5: 102 of them are committed into family A).
3. Possibly a "Word did not shut down correctly / open in Safe Mode?" prompt. **Unverified** —
   I could not confirm this behaviour for the Word build these repos target, and no script
   here handles it. Worth checking before writing a handler for it.

**Who handles what today**

| Script | Escalation | AutoRecovery | `~$` cleanup |
|---|---|---|---|
| `word-probe-sweep.sh` | `quit saving no` → 2 s → `pkill -9 -f` → 1 s | **Yes** — `find "$AUTOREC" -mindepth 1 -delete`. The only one in all three repos | Yes, in the loop |
| `word_compare_driver.sh` | `quit saving no` → 3 s → `pkill -x` (SIGTERM) → 2 s → relaunch + poll | No | Yes, after each restart |
| `word-convert.sh` | decline dialog → close → `quit saving no` → 1 s → `pkill -x` | No | No |
| `word_validate_batch.py` | `pkill -x` only — **no graceful quit first** | No | No |
| everything else | no kill at all | — | — |

Two of these are half-right in opposite directions. `word_compare_driver.sh` has the correct
*escalation* (graceful quit, then SIGTERM via `pkill -x`, never `-9`) but no AutoRecovery
handling. `word-probe-sweep.sh` has the only correct *cleanup* but jumps to `-9` with a
pattern match (`-f`) that can match more than Word.

**The complete recipe**

1. `quit saving no` first, under a short `timeout`. A clean quit writes no recovery state and
   removes its own lock files — everything below is only for when that fails.
2. Escalate to `pkill -x "Microsoft Word"` — SIGTERM, exact-name match. `-x`, never `-f`:
   `-f` matches the full command line and can hit an unrelated process whose arguments
   contain the string.
3. Only then `pkill -9 -x`.
4. After any kill: delete
   `~/Library/Containers/com.microsoft.Word/Data/Library/Preferences/AutoRecovery/*` so no
   Document Recovery pane appears, and `rm -f <dir>/~\$*.docx` in every folder Word touched.
5. **Better than cleaning up: do not generate the state.** Microsoft documents
   `Options.SaveInterval = 0` as AutoRecover's off switch — that is the VBA object model
   member, documented on Microsoft Learn, not the Preferences page cited in the sources
   below, which covers the GUI control (Preferences → Save) only. Set it
   once for the batch session and step 4's first half becomes unnecessary. The AppleScript
   term for it should be read off the local dictionary rather than guessed —
   `sdef /Applications/Microsoft\ Word.app | grep -i 'save interval'`. Restore it afterwards;
   a benchmark harness that permanently disables a human's autosave is not a good guest.
6. Re-warm before the next document. Do not let the next file's timeout pay for the cold
   start (§10).

For contrast: LibreOffice solves all of this with one launch flag, `--norestore`, which
`render/soffice.py` already passes. Word has no equivalent, which is why steps 4–5 have to be
done by hand.

---

## 13. If you keep four

`word_compare_driver.sh` + `word_compare_batch.applescript` for redlining,
`word-open-check.mjs` for validity, `render/word.py` for DOCX→PDF. Between them they cover
every job the other seventeen do, and they are the four that record *why* each decision is
what it is.

The merges worth making are small and specific:

1. **Settle §5.3** (staging), because until the container question has an answer every one of
   these scripts is guessing about the thing that decides whether it can run unattended.
2. **Settle §5.2** (`-1708`) with the four-line experiment. If file-vs-inline is not the
   variable, family A can be deleted rather than regenerated.
3. **Correct `CLAUDE.md` rule 1** per §5.1 — one TCC grant per terminal, forever; the
   per-file prompt is Word's sandbox sheet and staging is its cure.
4. Give the compare pipeline `word-open-check.mjs`'s **negative control**, so a clean corpus
   is provably clean rather than possibly unmeasured.
5. Give `render/word.py`'s **PDF path** the kill-and-warm that `word_validate_batch.py`
   already wraps around its validate path, and the calibrated budget that `validate_one`
   already has.
6. Add **AutoRecovery cleanup** to `word_compare_driver.sh`'s `restart_word`, and the
   graceful-quit-first escalation to `word-probe-sweep.sh`'s `kill_word`. Each already has
   the half the other is missing.
7. Fix `word-convert.sh`'s **timeout layering** (§10) and give it a bouncer or drop its
   `activate` (§5.9).
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
staging are mutually incompatible.** Family C is safe only because it stages everything
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

Worth recording, because these were the load-bearing claims:

- **`word-open-check.mjs`'s detector gate is real.** `detectorProven` is computed from the
  control file's actual verdict (`ctl.verdict === "REPAIR-PROMPT"`, line 871), consumed by
  `computeExitCode` (line 237), reported in the summary (line 1029), and covered by a unit
  test named *"returns 1 for a clean sweep when the detector was NOT proven"*. It is the only
  claim in the corpus that is asserted in a comment, implemented in code, **and** pinned by a
  test. C1 stays 1.00.
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

## Sources for the external claims

- SIGKILL produces no crash report: [Apple, EXC_CRASH (SIGKILL)](https://developer.apple.com/documentation/xcode/sigkill) · [How macOS reports crashes, The Eclectic Light Company](https://eclecticlight.co/2021/12/10/how-macos-reports-crashes/)
- Document Recovery opens when AutoRecover files exist: [Recover files in Office for Mac, Microsoft Support](https://support.microsoft.com/en-us/office/recover-files-in-office-for-mac-6c6425b1-6559-4bbf-8f80-4f038402ff02)
- AutoRecover interval and its off switch: [Change save frequency and where Word AutoRecovery files are stored, Microsoft Support](https://support.microsoft.com/en-us/office/change-save-frequency-and-where-word-autorecovery-files-are-stored-ddd81816-39ff-48f4-989e-8bf1db78b2d9)
- TCC automation grants are keyed on the responsible client app, not the process: [Avoiding AppleScript Security and Privacy Requests, Scripting OS X](https://scriptingosx.com/2020/09/avoiding-applescript-security-and-privacy-requests/) · [AppleScript Permissions on macOS, MAMP Documentation](https://documentation.mamp.info/en/MAMP-PRO-Mac/FAQ/General/AppleScript-Permissions-on-macOS/)
