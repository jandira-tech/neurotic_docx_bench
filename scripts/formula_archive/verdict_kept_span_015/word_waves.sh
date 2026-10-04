#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# Word waves prose1 then edits1: batch pass, two pair-by-pair passes, identity check.
# Detached from the agent harness (setsid) so no task timeout kills Word mid-batch.
set -u
cd ~/T/neurotic_docx_bench || exit 1
R=~/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes
WD=~/T/jubarte-loop/word_watchdog.sh
for W in prose1 edits1; do
  P=$R/$W
  mkdir -p $P/word
  echo "$(date '+%F %T') $W start"
  pkill -f word_watchdog.sh
  nohup $WD $P/word.log > /tmp/watchdog-$W.log 2>&1 &
  uv run scripts/word_redline.py -a $P/A -b $P/B -o $P/word --emit docx --log $P/word.log > $P/word.out 2>&1
  echo "$(date '+%F %T') $W batch done: $(ls $P/word/*.docx(N) | wc -l)"
  uv run scripts/word_redline.py -a $P/A -b $P/B -o $P/word --emit docx --no-one-redline-osascript --log $P/word.log > $P/word2.out 2>&1
  echo "$(date '+%F %T') $W rerun1 done: $(ls $P/word/*.docx(N) | wc -l)"
  uv run scripts/word_redline.py -a $P/A -b $P/B -o $P/word --emit docx --no-one-redline-osascript --log $P/word.log > $P/word3.out 2>&1
  echo "$(date '+%F %T') $W rerun2 done: $(ls $P/word/*.docx(N) | wc -l)"
  pkill -f word_watchdog.sh
  uv run scripts/check_redline_identity.py --a $P/A --b $P/B --redlines $P/word > $P/identity.out 2>&1
  echo "$(date '+%F %T') $W identity: $(tail -1 $P/identity.out)"
done
echo "$(date '+%F %T') ALL DONE"
