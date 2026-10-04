#!/usr/bin/env zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# Ring 3 sweep over a directory of .docx, resilient to Word's failure modes.
#
# Four traps a naive loop falls into, each of which silently corrupts the result:
#  1. word-open-probe.sh leaves Word blocked on a modal corrupt-file dialog, so
#     every later probe fails too (34 real opens, then 88 phantom failures).
#  2. Recovering with `pkill -9` makes Word relaunch into Document Recovery —
#     itself a modal dialog that blocks everything after it.
#  3. `*.docx` matches the `~$name.docx` owner/lock files Word drops next to any
#     document it opens; probing one costs a 60s AppleEvent timeout.
#  4. After a kill, Word needs ~30s to cold start. The probe's `with timeout of
#     60 seconds` covers launch *and* open, so under load the next probe times
#     out too and the whole run cascades into all-fail. Word must be pre-warmed.
#
# Usage: word_probe_all.sh <dir-with-docx> <logfile>
set -uo pipefail

DIR="${1:?usage: word_probe_all.sh <dir> <log>}"
LOG="${2:?usage: word_probe_all.sh <dir> <log>}"
PROBE="/Users/arthrod/temp/T/jubarte-redlines/scripts/word-open-probe.sh"
AUTOREC="$HOME/Library/Containers/com.microsoft.Word/Data/Library/Preferences/AutoRecovery"

kill_word() {
  osascript -e 'tell application "Microsoft Word" to quit saving no' >/dev/null 2>&1
  sleep 2
  pkill -9 -f 'Microsoft Word' >/dev/null 2>&1
  sleep 1
  find "$AUTOREC" -mindepth 1 -delete >/dev/null 2>&1
}

# Launch Word and block until it answers AppleEvents, so the next probe's 60s
# budget is spent opening the document rather than starting the app.
warm_word() {
  open -g -a 'Microsoft Word' >/dev/null 2>&1
  local i
  for i in $(seq 1 40); do
    if osascript -e 'with timeout of 5 seconds' \
                 -e 'tell application "Microsoft Word" to count of documents' \
                 -e 'end timeout' >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

kill_word
warm_word || echo "warning: Word did not warm up" >&2
: > "$LOG"
ok=0; fail=0
for f in "$DIR"/*.docx; do
  [ -e "$f" ] || continue
  case "$(basename "$f")" in
    '~$'*) rm -f "$f"; continue ;;   # Word owner/lock file, not a document
  esac
  if out=$("$PROBE" "$f" 1 2>&1); then
    ok=$((ok+1))
    echo "OK   $(basename "$f")" >> "$LOG"
  else
    fail=$((fail+1))
    echo "FAIL $(basename "$f"): $out" >> "$LOG"
    kill_word          # clear the corrupt-file dialog
    warm_word || true  # pay the cold start here, not inside the next probe
  fi
done
kill_word
echo "word-open probe: opened=$ok failed=$fail" | tee -a "$LOG"
[ "$fail" -eq 0 ]
