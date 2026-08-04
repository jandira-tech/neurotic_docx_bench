#!/usr/bin/env bash
# Unattended driver for the Word "Compare Documents" batch.
#
# Why the staging dance: Word for Mac is sandboxed. It can read/write anything
# inside its own group container without a permission prompt, but touching a
# repo path raises a "Grant Access" dialog PER FILE — three clicks for one pair,
# ~1200 for the corpus. So we clone the sources into the container, run the
# compare loop entirely in there, and move the results back. Cloning and moving
# are both free: the container and the repo are on the same APFS volume, so
# `cp -c` is a clonefile (O(1), zero bytes copied) and `mv` is a rename.
#
# A dialog watchdog runs alongside: `set displayAlerts to false` does NOT
# suppress Word's hard file-loader failure dialog, which blocks the Apple event
# until a human clicks OK. See scripts/word_dialog_watchdog.applescript.
#
# Usage:
#   scripts/word_compare_driver.sh [--limit N] [--start I] [--reset] [--screen]
#
#   --limit N   process only N pairs (smoke test); default: all
#   --start I   1-based manifest index to start at; default: 1
#   --reset     clear the staged output dir and the log before running
#   --screen    run the source pre-flight screen instead of the compare batch
#
# Resume is automatic and idempotent: pairs whose output already exists are
# skipped, so re-invoking after a crash finishes the tail.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORPUS="$REPO_ROOT/corpus/word_redlines_superdoc"
STAGE="$HOME/Library/Group Containers/UBF8T346G9.Office/bench-word-compare"
LOG="$CORPUS/compare.log"

LIMIT=0
START=1
RESET=0
SCREEN=0
while [[ $# -gt 0 ]]; do
	case "$1" in
		--limit) LIMIT="$2"; shift 2 ;;
		--start) START="$2"; shift 2 ;;
		--reset) RESET=1; shift ;;
		--screen) SCREEN=1; shift ;;
		*) echo "unknown option: $1" >&2; exit 2 ;;
	esac
done

SCREEN_LOG="$CORPUS/source_screen.tsv"
WATCHDOG_LOG="$CORPUS/word_dialogs.log"
WATCHDOG_PID=""

cleanup() {
	[[ -n "$WATCHDOG_PID" ]] && kill "$WATCHDOG_PID" 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------- preconditions
[[ -d "/Applications/Microsoft Word.app" ]] || { echo "Microsoft Word not installed" >&2; exit 1; }
[[ -f "$CORPUS/compare_manifest.tsv" ]] || {
	echo "missing $CORPUS/compare_manifest.tsv — run scripts/build_superdoc_pairs.py first" >&2
	exit 1
}

# One-time automation grant (macOS TCC, per host->target app pair). If this is
# the first osascript to talk to Word from this terminal, macOS shows exactly
# one dialog; approving it persists. Every later run is silent.
if ! osascript -e 'tell application "Microsoft Word" to get name' >/dev/null 2>&1; then
	echo "Apple-events automation grant for Microsoft Word is missing." >&2
	echo "Run this once and click OK on the single dialog macOS shows:" >&2
	echo "  osascript -e 'tell application \"Microsoft Word\" to activate'" >&2
	exit 1
fi

# The batch closes every open document after each pair. Refuse to run over a
# human's open work.
OPEN_DOCS="$(osascript -e 'tell application "Microsoft Word" to get count of documents' 2>/dev/null || echo 0)"
if [[ "$OPEN_DOCS" != "0" ]]; then
	echo "Microsoft Word has $OPEN_DOCS document(s) open; this batch closes documents without saving." >&2
	osascript -e 'tell application "Microsoft Word" to get name of every document' >&2 || true
	echo "Close them (or save them) and re-run." >&2
	exit 1
fi

# ---------------------------------------------------------------- staging
mkdir -p "$STAGE/in" "$STAGE/out"
if [[ "$RESET" == "1" ]]; then
	rm -f "$STAGE/out"/*.docx "$LOG"
fi

echo "==> staging sources into Word's group container (APFS clones)"
staged=0
for src in "$CORPUS/docx_source"/*.docx; do
	dst="$STAGE/in/$(basename "$src")"
	[[ -f "$dst" ]] && continue
	cp -c "$src" "$dst" 2>/dev/null || cp "$src" "$dst"
	staged=$((staged + 1))
done
echo "    $staged newly cloned, $(ls "$STAGE/in" | wc -l | tr -d ' ') total"

# ---------------------------------------------------------------- watchdog
# Must be running before Word opens anything: a poison fixture raises a modal
# dialog that no scripting flag suppresses, and it blocks the batch until
# dismissed. Requires the Accessibility grant (separate from the Word
# Apple-events grant); without it, warn rather than fail — the batch still runs,
# it just needs a human when a bad document turns up.
if osascript -e 'tell application "System Events" to get name of first process whose frontmost is true' >/dev/null 2>&1; then
	osascript "$REPO_ROOT/scripts/word_dialog_watchdog.applescript" "$WATCHDOG_LOG" 2 >/dev/null 2>&1 &
	WATCHDOG_PID=$!
	echo "==> dialog watchdog running (pid $WATCHDOG_PID, log: $WATCHDOG_LOG)"
else
	echo "!! Accessibility grant missing — Word error dialogs will block the batch." >&2
	echo "   Grant it once: System Settings > Privacy & Security > Accessibility > enable your terminal." >&2
fi

# Recycle Word. Mandatory after any document failure: one unreadable document
# leaves Word silently returning empty documents for every later open, which
# would poison the rest of the batch without raising a single error.
restart_word() {
	osascript -e 'tell application "Microsoft Word" to quit saving no' >/dev/null 2>&1 || true
	sleep 3
	pkill -x "Microsoft Word" 2>/dev/null || true
	sleep 2
	open -a "Microsoft Word" >/dev/null 2>&1 || true
	for _ in $(seq 1 30); do
		if osascript -e 'tell application "Microsoft Word" to get count of documents' >/dev/null 2>&1; then
			return 0
		fi
		sleep 1
	done
	echo "!! Word did not come back after restart" >&2
	return 1
}

# ---------------------------------------------------------------- screen mode
if [[ "$SCREEN" == "1" ]]; then
	[[ "$RESET" == "1" ]] && rm -f "$SCREEN_LOG"
	total=$(ls "$STAGE/in" | wc -l | tr -d ' ')
	echo "==> screening $total sources (log: $SCREEN_LOG)"
	touch "$SCREEN_LOG"
	# The screen stops at each poison document; restart Word and resume until it
	# reports done. Bounded by the file count, so it always terminates.
	for _ in $(seq 1 "$total"); do
		result=$(osascript "$REPO_ROOT/scripts/word_screen_sources.applescript" "$STAGE/in" "$SCREEN_LOG" 2>&1 || true)
		done_n=$(grep -vc '__SCREEN_DONE__' "$SCREEN_LOG" || true)
		printf '    %s/%s  %s\n' "$done_n" "$total" "$result"
		[[ "$result" == "SCREEN_DONE" ]] && break
		restart_word || break
	done
	# Healthy is a POSITIVE INTEGER; everything else (0, BAD:missing value,
	# ERROR:...) is a document Word cannot read.
	bad=$(awk -F'\t' '$1 != "__SCREEN_DONE__" && $2 !~ /^[1-9][0-9]*$/' "$SCREEN_LOG" | wc -l | tr -d ' ')
	echo "    unreadable by Word: $bad / $total"
	awk -F'\t' '$1 != "__SCREEN_DONE__" && $2 !~ /^[1-9][0-9]*$/ {print "      " $1 "  [" $2 "]"}' "$SCREEN_LOG"
	awk -F'\t' '$1 != "__SCREEN_DONE__" && $2 !~ /^[1-9][0-9]*$/ {print $1}' "$SCREEN_LOG" > "$CORPUS/word_unreadable.txt"
	echo "    exclusion list -> $CORPUS/word_unreadable.txt"
	exit 0
fi

# Rewrite the manifest's repo paths to staged paths. Field order is
# pair_id, base, next, out — only the three path fields move.
STAGED_MANIFEST="$STAGE/compare_manifest.tsv"
awk -v indir="$STAGE/in" -v outdir="$STAGE/out" '
	BEGIN { FS = OFS = "\t" }
	NF == 4 {
		n = split($2, a, "/"); $2 = indir "/" a[n]
		n = split($3, b, "/"); $3 = indir "/" b[n]
		n = split($4, c, "/"); $4 = outdir "/" c[n]
		print
	}
' "$CORPUS/compare_manifest.tsv" > "$STAGED_MANIFEST"
echo "    manifest: $(wc -l < "$STAGED_MANIFEST" | tr -d ' ') pairs -> $STAGED_MANIFEST"

# ---------------------------------------------------------------- compare loop
# Two independent failure modes, both handled by "restart Word and resume":
#
#  1. A pair fails. The batch stops and returns "POISON <pair>", because a
#     failed open can leave Word silently returning empty documents for every
#     later open — carrying on would corrupt the rest of the run with no error.
#  2. Word stops answering Apple events entirely. The log stops growing, the
#     stall watcher notices and kills it.
#
# Resume (skip pairs whose output already exists) makes both safe, and
# guarantees forward progress: each restart completes at least the pair that
# failed. The run aborts if restarts stop producing progress.
STALL_SECS=420
MAX_RESTARTS=80
restarts=0
stuck=0
touch "$LOG"
RESULT_FILE="$STAGE/.batch_result"

echo "==> comparing (log: $LOG)"
while :; do
	before=$(wc -l < "$LOG" | tr -d ' ')

	osascript "$REPO_ROOT/scripts/word_compare_batch.applescript" \
		"$STAGED_MANIFEST" "$LOG" "$START" "$LIMIT" > "$RESULT_FILE" 2>&1 &
	pid=$!

	last_size="$before"
	last_change=$SECONDS
	wedged=0
	while kill -0 "$pid" 2>/dev/null; do
		sleep 15
		size=$(wc -l < "$LOG" | tr -d ' ')
		if [[ "$size" != "$last_size" ]]; then
			last_size="$size"
			last_change=$SECONDS
			printf '\r    %s logged' "$size"
		elif (( SECONDS - last_change > STALL_SECS )); then
			wedged=1
			break
		fi
	done
	printf '\n'

	if [[ "$wedged" == "1" ]]; then
		kill "$pid" 2>/dev/null || true
		echo "    no progress for ${STALL_SECS}s — recycling Word" >&2
	else
		wait "$pid" 2>/dev/null || true
	fi

	result="$(tr -d '\n' < "$RESULT_FILE" 2>/dev/null || true)"
	after=$(wc -l < "$LOG" | tr -d ' ')

	# Normal completion: the batch ran to the end of the manifest.
	if [[ "$wedged" != "1" && "$result" != POISON* ]]; then
		break
	fi

	restarts=$((restarts + 1))
	if (( after > before )); then
		stuck=0
	else
		stuck=$((stuck + 1))
	fi
	if (( restarts > MAX_RESTARTS )); then
		echo "!! $MAX_RESTARTS restarts reached; stopping. Inspect $LOG" >&2
		break
	fi
	if (( stuck >= 3 )); then
		echo "!! 3 restarts in a row made no progress; stopping. Inspect $LOG" >&2
		break
	fi
	echo "    restart $restarts (${result:-stalled})" >&2
	restart_word || break
	rm -f "$STAGE/in/"~\$*.docx 2>/dev/null || true
done

# ---------------------------------------------------------------- collect
echo "==> collecting redlines back into the repo"
mkdir -p "$CORPUS/docx_redlines_word"
collected=0
shopt -s nullglob
for out in "$STAGE/out"/*.docx; do
	mv -f "$out" "$CORPUS/docx_redlines_word/"
	collected=$((collected + 1))
done
shopt -u nullglob

echo "    $collected redlines -> $CORPUS/docx_redlines_word/"
echo "==> tail of $LOG"
tail -5 "$LOG"
