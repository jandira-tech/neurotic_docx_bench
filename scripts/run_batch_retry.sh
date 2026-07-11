#!/bin/bash
# Word-native consecutive-pair redline batch (macOS + Microsoft Word).
#
# Adapted from ../_fixtures/scripts/run_batch_retry.sh with two additions:
#   1. Stamp each source DOCX with its exact filename at the start of the body
#      (via osascript insert text) before comparing.
#   2. Default paths point at the randomized corpus under this repo.
#
# Flow for N files sorted numerically (file_1, file_2, …):
#   - stamp file_i.docx body with "file_i.docx"
#   - redline file_i vs file_{i+1} → file_i_file_{i+1}_redline.docx
#
# Key learnings (from corpus/word_based/docx_redlines_word/README.md):
#   - inline osascript heredoc, NOT compiled .scpt (save as fails with -1708)
#   - files must live inside Word's container to avoid Grant File Access dialogs
#   - always pass "ignore all comparison warnings true"
#   - close every document between pairs
#
# Usage:
#   bash scripts/run_batch_retry.sh
#   SOURCE_DIR=... FINAL_OUT=... bash scripts/run_batch_retry.sh
#   SKIP_STAMP=1 bash scripts/run_batch_retry.sh   # resume redlines only
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

SOURCE_DIR="${SOURCE_DIR:-$REPO_ROOT/corpus/word_based/docx_source_randomized}"
FINAL_OUT="${FINAL_OUT:-$REPO_ROOT/corpus/word_based/docx_redlines_randomized}"
WORD_TMP="${WORD_TMP:-$HOME/Library/Containers/com.microsoft.Word/Data/tmp/fresh_batch_rand}"
SRC="$WORD_TMP/src"
OUT="$WORD_TMP/out"
LOG="$FINAL_OUT/batch_retry_log.csv"
STAMP_LOG="$FINAL_OUT/stamp_log.csv"
SKIP_STAMP="${SKIP_STAMP:-0}"

mkdir -p "$SRC" "$OUT" "$FINAL_OUT"

echo "=== Word batch redline (randomized) ==="
echo "SOURCE_DIR=$SOURCE_DIR"
echo "FINAL_OUT=$FINAL_OUT"
echo "WORD_TMP=$WORD_TMP"

# ---------------------------------------------------------------------------
# Stage 0: copy sources into Word's sandbox container
# ---------------------------------------------------------------------------
echo "--- copying sources into Word container ---"
# Clear prior sources so we don't mix old stamps / leftover pairs
find "$SRC" -maxdepth 1 -name 'file_*.docx' -delete 2>/dev/null || true
# Numeric order by basename (file_1, file_2, …) — not lex sort, and not
# path-based `sort -t_ -k2` (Word container paths contain underscores).
python3 - <<PY
import shutil
from pathlib import Path
src = Path(r"$SOURCE_DIR")
dst = Path(r"$SRC")
files = sorted(
    [p for p in src.glob("file_*.docx") if not p.name.startswith("~$")],
    key=lambda p: int(p.stem.split("_")[1]),
)
for p in files:
    shutil.copy2(p, dst / p.name)
print(f"copied {len(files)} files into container")
PY

# ---------------------------------------------------------------------------
# Stage 1: stamp each document body with its exact filename (osascript)
# ---------------------------------------------------------------------------
if [ "$SKIP_STAMP" != "1" ]; then
  echo "filename,status,duration_seconds" > "$STAMP_LOG"
  stamp_count=0
  stamp_ok=0
  stamp_fail=0
  while IFS= read -r doc; do
    stamp_count=$((stamp_count + 1))
    fname="$(basename "$doc")"
    start=$(date +%s)
    if osascript <<EOF 2>"$OUT/.stamp_err"
set docPath to (POSIX file "$doc" as text)
tell application "Microsoft Word"
  open docPath
  delay 1
  set theDoc to active document
  set startRange to create range theDoc start 0 end 0
  insert text "$fname" & return at startRange
  delay 0.3
  save theDoc
  close theDoc saving no
end tell
EOF
    then
      end=$(date +%s)
      dur=$((end - start))
      echo "[stamp $stamp_count] OK (${dur}s): $fname"
      echo "$fname,ok,$dur" >> "$STAMP_LOG"
      stamp_ok=$((stamp_ok + 1))
      # Persist stamped copy back into the corpus folder
      cp "$doc" "$SOURCE_DIR/$fname"
    else
      end=$(date +%s)
      dur=$((end - start))
      err=$(head -1 "$OUT/.stamp_err" 2>/dev/null || true)
      echo "[stamp $stamp_count] FAIL (${dur}s): $fname — $err"
      echo "$fname,fail,$dur" >> "$STAMP_LOG"
      stamp_fail=$((stamp_fail + 1))
      osascript -e 'tell application "Microsoft Word" to close every document without saving' 2>/dev/null || true
    fi
    rm -f "$OUT/.stamp_err"
  done < <(find "$SRC" -maxdepth 1 -name 'file_*.docx' ! -name '~$*' | sort -t_ -k2 -n)
  echo "=== STAMP COMPLETE: ok=$stamp_ok fail=$stamp_fail / $stamp_count ==="
else
  echo "--- SKIP_STAMP=1: using already-stamped files in container/source ---"
  # Still ensure container has current corpus copies
  while IFS= read -r f; do
    cp "$f" "$SRC/"
  done < <(find "$SOURCE_DIR" -maxdepth 1 -name 'file_*.docx' ! -name '~$*' | sort -t_ -k2 -n)
fi

# ---------------------------------------------------------------------------
# Stage 2: consecutive-pair Word compare (file_i vs file_{i+1})
# ---------------------------------------------------------------------------
# Build sorted file list (numeric by N in file_N.docx)
FILES=()
while IFS= read -r f; do
  FILES+=("$f")
done < <(find "$SRC" -maxdepth 1 -name 'file_*.docx' ! -name '~$*' | sort -t_ -k2 -n)

PAIRS=$((${#FILES[@]} - 1))
if [ "$PAIRS" -lt 1 ]; then
  echo "ERROR: need at least 2 source files in $SRC" >&2
  exit 1
fi

# Resume: append if log exists and we're continuing; else rewrite header
if [ ! -f "$LOG" ]; then
  echo "pair_index,base,next,output,status,duration_seconds" > "$LOG"
fi

# Find first missing pair (resumable)
START_IDX=0
for i in $(seq 0 $((PAIRS - 1))); do
  base_stem=$(basename "${FILES[$i]}" .docx)
  next_stem=$(basename "${FILES[$((i + 1))]}" .docx)
  outname="${base_stem}_${next_stem}_redline.docx"
  if [ -f "$OUT/$outname" ] || [ -f "$FINAL_OUT/$outname" ]; then
    # Prefer existing FINAL_OUT copy into container out if missing there
    if [ ! -f "$OUT/$outname" ] && [ -f "$FINAL_OUT/$outname" ]; then
      cp "$FINAL_OUT/$outname" "$OUT/$outname"
    fi
    START_IDX=$((i + 1))
  else
    break
  fi
done

echo "Total pairs: $PAIRS | Already done: $START_IDX | Starting from pair $((START_IDX + 1))"

for i in $(seq "$START_IDX" $((PAIRS - 1))); do
  base_file="${FILES[$i]}"
  next_file="${FILES[$((i + 1))]}"
  base_stem=$(basename "$base_file" .docx)
  next_stem=$(basename "$next_file" .docx)
  outname="${base_stem}_${next_stem}_redline.docx"
  outpath="$OUT/$outname"

  if [ -f "$outpath" ]; then
    echo "[$((i + 1))/$PAIRS] SKIP (exists): $outname"
    echo "$((i + 1)),$base_stem,$next_stem,$outname,skip,0" >> "$LOG"
    cp "$outpath" "$FINAL_OUT/" 2>/dev/null || true
    continue
  fi

  osascript -e 'tell application "Microsoft Word" to close every document without saving' 2>/dev/null || true

  start=$(date +%s)
  if osascript <<EOF 2>"$OUT/.err_$i"
set basePath to (POSIX file "$base_file" as text)
set nextPath to (POSIX file "$next_file" as text)
set outputPath to (POSIX file "$outpath" as text)

tell application "Microsoft Word"
  open basePath
  delay 1
  set baseDocument to active document
  compare baseDocument path nextPath ignore all comparison warnings true
  delay 1
  save as front document file name outputPath
  close every document without saving
end tell
EOF
  then
    end=$(date +%s)
    dur=$((end - start))
    size=$(stat -f%z "$outpath" 2>/dev/null || echo "0")
    echo "[$((i + 1))/$PAIRS] OK (${dur}s, ${size}B): $outname"
    echo "$((i + 1)),$base_stem,$next_stem,$outname,ok,$dur" >> "$LOG"
    cp "$outpath" "$FINAL_OUT/"
  else
    end=$(date +%s)
    dur=$((end - start))
    err=$(head -1 "$OUT/.err_$i" 2>/dev/null || true)
    echo "[$((i + 1))/$PAIRS] FAIL (${dur}s): $outname — $err"
    echo "$((i + 1)),$base_stem,$next_stem,$outname,fail,$dur" >> "$LOG"
    osascript -e 'tell application "Microsoft Word" to close every document without saving' 2>/dev/null || true
  fi
  rm -f "$OUT/.err_$i"
done

echo "=== RETRY COMPLETE ==="
echo "Redlines in FINAL_OUT: $(find "$FINAL_OUT" -maxdepth 1 -name '*_redline.docx' | wc -l | tr -d ' ')"
echo "Log: $LOG"
echo "Stamp log: $STAMP_LOG"
