#!/usr/bin/env zsh

# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
#
# SPDX-License-Identifier: AGPL-3.0-only

# Ask the real Microsoft Word (AppleScript, macOS-only) to open a .docx and
# report the outcome — the corruption oracle for redline outputs:
#   OPENED: <name>   — Word accepted the file (exit 0)
#   FAILED/ERROR …   — Word refused it (corrupt-file dialog ⇒ AppleEvent timeout)
#
# Usage: scripts/word-open-probe.sh <file.docx> [delay-seconds]
# Requires: macOS, Microsoft Word, osascript.

set -euo pipefail

if [ $# -lt 1 ] || [ ! -f "$1" ]; then
  echo "usage: $0 <file.docx> [delay-seconds] — file must exist" >&2
  exit 2
fi
delay="${2:-2}"

# Resolve to an absolute path and escape AppleScript string specials
# (backslash first, then double quote) so paths containing quotes or
# backslashes cannot break out of the string literal.
abs="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
esc="${abs//\\/\\\\}"
esc="${esc//\"/\\\"}"

result=$(osascript << OSA
with timeout of 60 seconds
  tell application "Microsoft Word"
    try
      open POSIX file "$esc"
      delay $delay
      if (count of documents) > 0 then
        set theName to name of active document
        close active document saving no
        return "OPENED: " & theName
      else
        return "FAILED: no document opened (likely corrupt dialog)"
      end if
    on error errMsg number errNum
      return "ERROR " & errNum & ": " & errMsg
    end try
  end tell
end timeout
OSA
)
echo "$result"
case "$result" in
  OPENED:*) exit 0 ;;
  *) exit 1 ;;
esac
