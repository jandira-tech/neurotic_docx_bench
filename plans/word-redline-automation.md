# Teaching doc — generating redlines with Microsoft Word, unattended

Audience: an implementing agent on this machine (macOS, Darwin 25.5.0, `Microsoft
Word.app` and `LibreOffice.app` both present in `/Applications`, `osascript`
verified working). Goal: produce ~400 Word-native redline DOCX files (Word's
own *Compare Documents* output) from the superdoc fixture pool, with **exactly
one** local permission click from the user, and zero clicks after that.

Prior art in this repo — read these before writing anything:

- `scripts/batch_word_to_pdf.scpt` — the proven open→save-as-PDF loop over a
  directory (per-file try/error logging, `display alerts` suppression). Your
  compare loop is this script with `compare` inserted between open and save.
- `scripts/batch_convert.scpt`, `scripts/batch_*_pdf.applescript` — variants
  that already ran over hundreds of corpus files on this machine, which means
  the Word↔Terminal automation grant already exists here (see §1) and Word has
  historically opened files from regular repo paths without per-file dialogs.
- `corpus/word_based/docx_redlines_word/` (233 files) — Word-generated
  redlines already exist for the named corpus; the mapping column
  `redline_docx_word` in `corpus/word_based/centralized_mapping.csv` records
  them. You are extending an established pattern, not inventing one.

## 1. The single permission ask (do this FIRST, interactively)

macOS TCC gates Apple-events automation per (host app → target app) pair. The
first `osascript` that talks to Word from this host triggers one dialog
("…wants access to control Microsoft Word"). Approving it once persists in the
TCC database — every later run is silent. So the entire permission story is:

```bash
# Arm the automation grant. Ask the user to click OK exactly once.
osascript -e 'tell application "Microsoft Word" to activate' \
          -e 'tell application "Microsoft Word" to set d to name of active window' 2>&1 || true
```

Tell the user, in one line, before running it: "macOS will show one permission
dialog for controlling Microsoft Word — click OK; that is the only click this
whole pipeline needs." If the dialog never appears, the grant already exists
(likely, given the prior-art scripts ran here) — verify with:

```bash
osascript -e 'tell application "Microsoft Word" to get name' && echo GRANTED
```

Do NOT ask again. Do not add per-file confirmations of any kind.

## 2. Killing the other thousand clicks

Three other click sources exist; each has a scripted kill:

1. **Word alert dialogs** (conversion prompts, compatibility warnings,
   comparison warnings). Suppress for the whole session:

   ```applescript
   tell application "Microsoft Word"
     set display alerts to alerts none
   end tell
   ```

   Restore `alerts all` in a cleanup handler. Note: the exact enum spelling
   varies by Word build — verify against the live dictionary first (§3).

2. **Sandbox "grant access" file dialogs.** Word for Mac is sandboxed; the
   belt-and-suspenders fix is to stage inputs and collect outputs inside
   Word's own container, which needs no grants ever:

   ```bash
   STAGE="$HOME/Library/Group Containers/UBF8T346G9.Office/bench-word-compare"
   mkdir -p "$STAGE"/{in,out}
   ```

   Copy pairs in with APFS clones (`cp -c`, instant, no data duplication),
   run the compare loop against `$STAGE`, then move results back into the
   repo. If the prior-art scripts prove Word already opens repo paths cleanly
   on this machine, you may skip staging — but implement it anyway behind a
   `--stage` flag so the pipeline is portable and click-proof by construction.

3. **Password prompts.** The pool's `encryption/` bucket (2 files:
   `encrypted-advanced-text.docx`, `encrypted-hello.docx`) will block forever
   waiting for a password. Exclude the bucket up front; record the exclusion
   in the manifest with `status=excluded_encrypted`.

## 3. Verify the `compare` dictionary before coding

Word's AppleScript `compare` command exists in Word 16.x; parameter names can
drift between builds, so always re-dump the dictionary on the machine you run
on:

```bash
sdef "/Applications/Microsoft Word.app" > /tmp/word.sdef
grep -A 20 '<command name="compare"' /tmp/word.sdef
```

**Verified on THIS machine (2026-08-03)** — the installed Word's dictionary
declares exactly:

```
compare <document>
  path <text>                              -- the revised document to compare with (required)
  author name <text>                       -- optional
  target <WdCompareTarget>                 -- optional; omitted → result opens as a NEW document
  detect format changes <boolean>          -- optional
  ignore all comparison warnings <boolean> -- optional
  add to recent files <boolean>            -- optional
```

Use `ignore all comparison warnings true` (kills a whole dialog class) and
`add to recent files false` (keeps the recents list from ballooning across
400 compares). Omit `target` so the result opens as a new document, which the
loop then saves. Still write one manual smoke test against a single pair and
confirm the saved output's `word/document.xml` contains `<w:ins` / `<w:del`
before building the loop.

## 4. The compare loop (reference implementation)

One Word instance, strictly sequential — Word's Apple-events interface is not
concurrency-safe; parallelism belongs to the surrounding pipeline (§6), never
inside Word. Skeleton (adapt names to the sdef you dumped; keep the structure):

```applescript
#!/usr/bin/env osascript
-- argv: 1=manifest.tsv (pair_id \t base_path \t next_path \t out_path), 2=log dir
on run argv
  set manifestPath to item 1 of argv
  set rows to paragraphs of (do shell script "cat " & quoted form of manifestPath)
  tell application "Microsoft Word" to set display alerts to alerts none
  repeat with r in rows
    set fields to my splitTab(r)
    set {pairId, baseP, nextP, outP} to fields
    -- idempotent resume: skip if output already exists and is non-empty
    if (do shell script "test -s " & quoted form of outP & " && echo yes || echo no") is "yes" then
      log "[skip] " & pairId
    else
      try
        with timeout of 300 seconds
          tell application "Microsoft Word"
            open file name baseP
            set baseDoc to active document
            compare baseDoc path nextP ¬
              ignore all comparison warnings true ¬
              add to recent files false  -- signature verified via sdef, see §3
            set cmpDoc to active document
            save as cmpDoc file name outP file format format document
            close every document saving no
          end tell
        end timeout
        log "[ok] " & pairId
      on error errMsg
        log "[fail] " & pairId & " :: " & errMsg
        try
          tell application "Microsoft Word" to close every document saving no
        end try
      end try
    end if
  end repeat
  tell application "Microsoft Word" to set display alerts to alerts all
end run
```

Hard rules the skeleton encodes — keep them all:

- **Idempotent resume**: skip pairs whose output exists non-empty, so a crash
  mid-run costs nothing; re-invoking the script finishes the tail.
- **`close every document saving no` after every pair** (success AND failure).
  Word degrades linearly with open documents; leaks turn a 25-minute run into
  hours and eventually wedge it.
- **Per-pair timeout + try/error**: one poisonous pair must not kill the run.
- **Wedge recovery** in the *driver* (bash, not AppleScript): if the osascript
  process makes no log progress for >5 minutes, `pkill -x "Microsoft Word"`,
  wait 10 s, and re-invoke the script — the resume rule makes this safe.
  Cap at 3 restarts per run, then report the surviving failures.

Driver invocation (from repo root; long-run rules apply — `set -o pipefail`
before any `| tee`, since tee otherwise masks the exit code):

```bash
set -o pipefail
osascript scripts/word_compare_batch.applescript \
  corpus/word_redlines_superdoc/compare_manifest.tsv \
  /tmp 2>&1 | tee corpus/word_redlines_superdoc/compare.log
```

Throughput expectation: ~2–5 s per compare → 400 pairs ≈ 20–35 minutes.
If a run exceeds ~90 minutes, something is leaking; stop and inspect.

## 5. Validating the outputs (Word-valid, per Arthur's definition)

Every produced redline must be **Word valid**: opens in Word with zero
warnings/repair offers (permission prompts don't count). Automated proxy
checks, all three required per file:

1. `unzip -t` passes (zip integrity).
2. Python (`python-docx` or raw lxml): package opens, and `word/document.xml`
   contains at least one `w:ins` or `w:del` element — an empty compare means
   the pair was content-identical (see same-SHA rule in the pairing spec) or
   the compare silently failed; mark `status=empty_redline`, don't ship it.
3. LibreOffice render smoke: `soffice --headless --convert-to pdf` exits 0.

Then one batch Word-reopen pass (reuse the §4 loop minus compare/save) over a
random 5% sample with `display alerts` left ON, watching the log for errors —
that's the closest scriptable approximation of "no repair prompt". Report the
sample size and result honestly in the PR body.

## 6. Where parallelism lives (and where it must not)

- Inside Word: **none**. One instance, one document at a time.
- Around Word: overlap the serial compare producer with parallel consumers —
  a watcher that picks up each finished `out/*.docx` and immediately runs
  validation (§5) and PDF rendering on the bench's 12-worker pool while Word
  is still comparing the next pair. A 30-line Python poll loop
  (`ProcessPoolExecutor(max_workers=12)`, poll `out/` every 5 s, submit new
  non-empty files, stop on a `compare.done` sentinel written by the driver)
  makes the whole pipeline finish ~when Word finishes, instead of
  compare-time + validate-time + render-time in sequence.

## 7. Definition of done

- `scripts/word_compare_batch.applescript` + bash driver committed, with a
  vitest or pytest smoke test that validates the manifest format parser
  (the AppleScript itself is exercised by the real run, not unit tests).
- 400-row map committed (`corpus/word_redlines_superdoc/manifest.csv`) per the
  pairing spec in the master plan §Chapter 2, including SHA-256 of base, next,
  and produced redline for every row, and an explicit `status` for every row
  (`ok` / `empty_redline` / `excluded_encrypted` / `fail: <reason>`).
- ≥95% of rows `status=ok`; every `ok` redline passes all three §5 checks.
- The one permission click is documented in the PR body as the only manual
  step, with the §1 arm command quoted so it's reproducible on a fresh host.
