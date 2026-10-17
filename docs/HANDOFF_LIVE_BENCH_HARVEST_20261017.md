# Handoff: live-bench broken-DOCX harvest and the Word screen logger (2026-10-17)

The session that ran the two-hourly harvest of broken DOCX from the D1 `jubarte-live-bench` and
built the Word screen logger ended here. This page lists what changed, what it left half done,
and what to do next.

## What this PR changes

- `scripts/word_screen_log.py`: back to the working logger. The file had been reverted to the
  first version, which polled every 10 s and missed every alert. Someone had added a 2026-10-14
  note to that old version. This copy:
  - polls CoreGraphics every 0.25 s and screenshots each dialog window as soon as it appears;
  - reads a dialog once its size has held for one poll. Alerts zoom in from 40x44 to 260x282.
    A dialog that closes before it settles is read from its newest shot and marked
    `(closed before it settled)`;
  - reads text with Vision accurate, then tesseract on a 3x copy, then Vision fast. Vision
    accurate has been broken on this machine since 2026-10-13 (e5rt error, about 40 s per failed
    call), so the logger tests it once at start and skips it if it fails;
  - keeps screenshots under `$TMPDIR`, never `/tmp`, because tesseract's Leptonica cannot open
    `/tmp` paths;
  - never polls System Events.
  - The docstring records all of this, plus both notes.
  - Verified: it caught Word's repair prompt and the "error trying to open the file" OK on real
    driver runs.
- `live-bench/harvest/harvest.py`: `collect` now understands `scripts/word_pdf.py`'s output.
  - `category()` treats `repair prompt declined` as `repair_prompt`, the same as the old
    `loaded empty`.
  - It treats `Word crashed` and `error reporter appeared` as `crashes_word`.
  - `pdf_stems()` strips the `_byword` suffix from PDF names. Without it, every good file reads
    as having no PDF.

## What is unfinished

1. **Harvest run `live-bench/.work/harvest/20261017_031051` is incomplete.**
   - `prepare` pulled 320 new rows.
   - `scripts/word_pdf.py` ran pass 1 (54 items) and part of pass 2, logging 102 `[ok]` and
     28 `[fail]`. Arthur stopped it at 04:06, during a restart after "Word returned nothing for
     6 document(s) in a row" at item 75 (`00075__harvest__docxodus__01a11a49_2617.docx`).
   - **There is no `$R/word_pdf/`.** `word_pdf.py` exports into a staging folder inside Word's
     sandbox and copies the results to `--out` only at the end of the run. The stop came before
     that copy.
     - The 53 PDFs it finished sit in
       `~/Library/Containers/com.microsoft.Word/Data/tmp/wordpdf.9z3z73_4/out/`, under staged
       names (`NNNNN__<sha256>.pdf`, not the `<stem>_byword.pdf` that `collect` expects).
     - The per-pass logs are beside them (`batch-pdf-{1,2}.{log,tsv}`).
   - **Do not run `collect` on this run as it stands.** With no `$R/word_pdf/`, every file is filed
     as `no_result`.
   - To redo it: rerun the same command from the repo root. Word must be clean (count of documents
     0) and in front, and the run must be in the foreground; let it finish, then run `collect $R`.
     The batch takes longer than the Bash tool's 600 s foreground limit, so run it in a Terminal
     tab rather than through the tool:

     ```bash
     R=live-bench/.work/harvest/20261017_031051
     uv run python scripts/word_pdf.py --src $R/word_in --out $R/word_pdf --no-check-preset --label harvest --log $R/word.log
     ```
2. **The cron prompt still names `scripts/word_pdf_focus.py`.** AGENTS.md says that driver "must
   not be used for new runs". This session used `scripts/word_pdf.py` instead and changed
   `collect` to match. Update the cron prompt (steps 3 and 4) to `scripts/word_pdf.py`, or tell
   the next session which one to use.
3. **Run the logger over all of `really_broken/`.** Arthur asked to "run the logger on all broken
   fixtures and see if u capture".
   - 155 copies were staged in c00–c16, but other Word users kept the run blocked. Job
     `9ca0b775`'s `word_watchdog.sh` `pkill -9`s Word after 60 s idle. `docx-validate`'s
     `probe-word-fixtures.ts`, run with `--force-close-existing-word`, cycles every few minutes.
   - Arthur said to wait 30 minutes and retry rather than kill them. The staging has since been
     deleted.
   - To redo it: re-stage with `live-bench/harvest/stage_chunks.py`, check that no other Word job
     is running (`ps -axo pid,etime,command | grep -i word`), start the logger, then run
     `word_pdf.py` per chunk.
4. **The screen logger is still running**, as pid 30521 (its `uv` parent is pid 30474), and
   writes to `live-bench/.work/word_screen.log`. Leave it running for the next harvest, or stop
   it with `kill 30521 30474`.

## State worth knowing

- `really_broken/manifest.csv` had 167 rows at 2026-10-13 19:17:

  | Folder | Rows |
  |---|---|
  | `fixtures/repair_prompt` | 15 |
  | `tool_redlines/repair_prompt` | 129 |
  | `tool_redlines/crashes_word` | 16 |
  | `tool_redlines/unconfirmed` | 7 |

  Two rows were refiled by hand, each with a NOTE:
  - superdoc-redlines 2367 moved to `unconfirmed`. Its crash came from probe interference.
  - superdoc-redlines 2380 moved to `repair_prompt`. The screen log caught its repair prompt
    twice.
- The harvest state (`seen.csv`, `watermark.txt`) lives in `live-bench/.work/harvest/`.
  `prepare` advanced the watermark past the 320 rows of the unfinished run, so the next
  `prepare` will not pull them again. Redo that run from its own `word_in/`.
- wrangler sometimes fails with an empty stderr. `harvest.py` retries 3 times.
- A "Connection is invalid" crash during a batch can be another job killing Word. Before filing
  a file as `crashes_word`, compare the time with the screen log and `ps`.
