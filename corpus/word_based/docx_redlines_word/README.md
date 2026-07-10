# DOCX Redline Batch Comparison — Instructions

## What this does

Generates Word-native redline (track-changes) documents from sequential pairs of `.docx` fixtures. For `N` files sorted alphabetically, it produces `N-1` redlines: file[1] vs file[2], file[2] vs file[3], etc. Each output is named `<base_stem>_<next_stem>_redline.docx`.

## Prerequisites

- **macOS** with **Microsoft Word for Mac** installed (tested on Word 16.112)
- Files must be **normalized**: dots in stems replaced with underscores (e.g. `foo.bar.docx` → `foo_bar.docx`). Only the `.docx` extension keeps its dot.
- Word lock files (`~$*.docx`) must be excluded — the script does this automatically.

## Key learnings (read before modifying)

1. **Use inline `osascript` heredoc, NOT `.scpt` files.** Word's `save as` command fails inside compiled `.scpt` with `-1708` ("active document doesn't understand the 'save as' message"). The identical code works when passed as an inline heredoc to `osascript`.

2. **Files must be inside Word's container** to avoid the "Grant File Access" sandbox dialog:
   ```
   ~/Library/Containers/com.microsoft.Word/Data/tmp/fresh_batch/src/
   ~/Library/Containers/com.microsoft.Word/Data/tmp/fresh_batch/out/
   ```
   Files outside this container trigger Word's per-file sandbox prompt, which cannot be dismissed via AppleScript.

3. **Always pass `ignore all comparison warnings true`** to the `compare` command. Without it, documents containing track-changes markup (`<w:ins>`/`<w:del>`) trigger a confirmation dialog that blocks AppleScript execution and causes cascade failures.

4. **Close all documents between pairs** to prevent stray docs from corrupting Word's state.

## Steps

### 1. Normalize source filenames

Replace dots in filename stems with underscores (keep `.docx` extension):

```bash
cd /path/to/source_fixtures
for f in *.docx; do
  stem="${f%.docx}"
  new_stem="${stem//./_}"
  [ "$f" != "${new_stem}.docx" ] && mv -n "$f" "${new_stem}.docx"
done
```

### 2. Copy files into Word's container

```bash
WORD_TMP="$HOME/Library/Containers/com.microsoft.Word/Data/tmp/fresh_batch"
mkdir -p "$WORD_TMP/src" "$WORD_TMP/out"
cp /path/to/source_fixtures/*.docx "$WORD_TMP/src/"
```

### 3. Set output directory

```bash
FINAL_OUT="/path/to/output_dir"
mkdir -p "$FINAL_OUT"
```

### 4. Run the batch script

```bash
bash scripts/run_batch_retry.sh
```

The script:
- Reads sorted `.docx` files from `$WORD_TMP/src/`
- For each consecutive pair, runs `open → compare (with ignore warnings) → save as front document → close all`
- Saves outputs to `$WORD_TMP/out/` and copies to `$FINAL_OUT/`
- Skips pairs where output already exists (resumable)
- Logs results to `$FINAL_OUT/batch_retry_log.csv`
- Excludes `~$` lock files automatically

### 5. Resume after interruption

The script auto-resumes from the first missing output. Just re-run:

```bash
bash scripts/run_batch_retry.sh
```

## The core AppleScript pattern (per pair)

```applescript
set basePath to (POSIX file "/path/to/base.docx" as text)
set nextPath to (POSIX file "/path/to/next.docx" as text)
set outputPath to (POSIX file "/path/to/output_redline.docx" as text)

tell application "Microsoft Word"
    open basePath
    delay 1
    set baseDocument to active document
    compare baseDocument path nextPath ignore all comparison warnings true
    delay 1
    save as front document file name outputPath
    close every document without saving
end tell
```

## Files

| File | Purpose |
|------|---------|
| `scripts/run_batch_retry.sh` | Main batch runner (resumable, uses container paths) |
| `scripts/run_batch_compare.sh` | Original batch runner (kept for reference) |
| `scripts/compare-documents.scpt` | Original single-pair script (broken `save as` in Word 16.112) |
| `scripts/compare-documents-fixed.scpt` | Attempted fix (still broken via `.scpt` — use inline heredoc instead) |

## Expected output

For 165 source files: 164 redline outputs in `fresh_compared_fixtures/`, named `<base>_<next>_redline.docx`. Each contains Word's track-changes markup showing insertions/deletions between the two source documents.
