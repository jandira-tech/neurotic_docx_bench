<!--
SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
SPDX-License-Identifier: AGPL-3.0-only
-->

# Word scripts: review notes from the English redline run (2026-09-25)

These are notes for Arthur to review. No script in this folder was changed.

The run was 500 pairs: `grok_run/500_docx_part_a_original[i]` against
`500_docx_part_b_original[i]`. Each pair was staged under one filename in
`$T/a` and `$T/b`. The chain was `word_redline.py --emit docx`, then
`check_redline_identity.py`, then `word_pdf.py`. The drivers live in
`jubarte-loop`:

- `en_redline.sh`
- `en_redline_pp.sh`
- `en_redline_loop.sh`
- `word_watchdog.sh`

## 1. `word_redline.py`: the default batch mode loses almost half the pairs

In the default mode (`--one-redline-osascript`), 234 of 500 pairs failed with:

    open produced 2 new documents; refusing to guess

- **Deterministic.** A second batch pass on a freshly quit Word recovered 1 of
  the 234.
- **Not the files.** The failing and succeeding pairs have the same feature
  profile: no template content type, no macros, no mail merge, no subDocs,
  no linkStyles.
- **Clustered by pair index.** The failures come in runs of consecutive pairs
  (034–048, 149–161, 311–330, …).
- **Workaround:** `--no-one-redline-osascript`, which runs one osascript per
  pair. See §2.

The rest of pass 1:

| Failures | Error |
|---|---|
| 22 | `Microsoft Word got an error: document "NNNNN__base__…" doesn't …`. The message is truncated in the log, so the verb is unknown. |
| 1 | `dec6d5bf…: redline is missing base 82% of that file`. This is the script's own content check, and it is working as intended. |

## 2. `word_redline.py`, per-pair mode: the same guard still fires, about every other pair

In per-pair mode the error comes in a pattern: `ok`, `FAIL`, `ok`, `FAIL`, …
The failure lands right after a successful compare. Excerpt from
`grok_run/500_extra_redline.log`, 21:05:

    [11/500] ok (2.5s, 64 revisions)
    [12/500] FAIL … open produced 2 new documents; refusing to guess (-2700)
    [word] did not come back clean after a failure; recycling
    [13/500] ok (3.0s, 35 revisions)
    [14/500] FAIL … open produced 2 new documents …

The per-pair script opens with `close every document saving no`. The next
`open` still sees two documents that are not in `seenBeforeOpen`. So something
from the previous compare survives `close every document`, or reappears after
it. Candidates:

- the revision document that `compare … path revP` opens internally;
- the compare result window;
- AutoRecover or a recovered document.

It is also possible that the name-diffing logic miscounts, for example when a
document has two windows or a name is reused.

- **The guard is correct.** Refusing to guess is right; the leak it catches
  is the bug.
- **Proposed diagnosis** (not implemented): when `baseCount is not 1`, append
  every document's `name` and `full name` to the error before closing. Then
  one failing pair shows what the extra document is.
- **Current cost:** each hit is one lost pair for that pass, plus a Word
  recycle. The pair is not replayed, because the replay requires a failure
  streak and the next pair succeeds.
- **Workaround in use:** `en_redline_loop.sh` re-runs the chain. Existing
  outputs are skipped, and each pass recovers most of what is left.

## 3. `word_pdf.py` / `word_redline.py`: timeouts cannot fire through a modal dialog

When Word shows a modal (a repair prompt or a hidden dialog), the batch
osascript blocks. The script's own per-item timeout (`--pdf-timeout 180`) then
never fires. Observed: `[batch pdf 1] 84/265` stayed unchanged for more than
11 minutes, and item 84 was a redline, `9d3fc364…__vs__105134a0…`.

- Only killing Word recovers it. After a kill, the scripts recycle and
  resume, correctly.
- **Workaround:** `jubarte-loop/word_watchdog.sh PATH...` kills Word when none
  of the given logs or output folders has changed for `WD_SECS`, 60 seconds
  per Arthur.
- **Pass the output folder.** In per-pair mode `-q` logs nothing while a pair
  runs, so a log-only watchdog kills healthy runs.
- **Proposed:** fold a no-progress watchdog into `run_batch_with_resume` and
  `_redline_serial`.
- **Linked-file prompt.** Arthur saw a prompt naming `Loch.docx` that stalled
  twice. The only "Loch" in the sources is a mailto hyperlink in part_b
  `44ed9426…` (pair 279), so the prompt's origin is unconfirmed.

## 4. What works well (keep)

- **Close documents instead of restarting Word.** Every pair starts with
  `close every document saving no` and Word stays up. A restart costs about
  30 seconds and does not help a malformed document.
- **Recycle only when Word is broken.** Word is recycled only after an unclean
  recovery, or after a failure streak (§5.20: a degraded Word loads empty
  documents). Throughput is about 2–20 seconds per pair.
- **Re-runs skip existing outputs.** Re-runs are cheap and safe.
- **`check_redline_identity.py`** reported 266 checked, 0 bad, on pass 2.

## 5. Small log issue

The batch-mode ERROR lines wrap and truncate AppleScript messages at
"doesn't". Logging the full `errMsg` on one line would make the 22 failures in
§1 diagnosable.
