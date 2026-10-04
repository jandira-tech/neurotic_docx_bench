#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# After the running denom1 batch: denom1 reruns + identity, then edge1, punct1, short2, edits1.
set -u
cd ~/T/neurotic_docx_bench || exit 1
R=~/temp/T/jubarte-redlines/jubarte-app/_scratch/redline-traversal-flow/probes
WD=~/T/jubarte-loop/word_watchdog.sh
while pgrep -f "word_redline.py" >/dev/null; do sleep 30; done
P=$R/denom1
echo "$(date '+%F %T') denom1 batch finished: $(ls $P/word/*.docx(N) | wc -l)"
pkill -f word_watchdog.sh; nohup $WD $P/word.log > /tmp/watchdog-denom1.log 2>&1 &
uv run scripts/word_redline.py -a $P/A -b $P/B -o $P/word --emit docx --no-one-redline-osascript --log $P/word.log > $P/word2.out 2>&1
uv run scripts/word_redline.py -a $P/A -b $P/B -o $P/word --emit docx --no-one-redline-osascript --log $P/word.log > $P/word3.out 2>&1
echo "$(date '+%F %T') denom1 reruns done: $(ls $P/word/*.docx(N) | wc -l)"
pkill -f word_watchdog.sh
uv run scripts/check_redline_identity.py --a $P/A --b $P/B --redlines $P/word > $P/identity.out 2>&1
echo "$(date '+%F %T') denom1 identity: $(tail -1 $P/identity.out)"
echo "$(date '+%F %T') denom1 DONE"
/tmp/word_wave_one.sh edge1
/tmp/word_wave_one.sh punct1
/tmp/word_wave_one.sh short2
/tmp/word_wave_one.sh edits1
echo "$(date '+%F %T') ALL DONE"