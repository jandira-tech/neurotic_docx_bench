#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
cd /Users/arthrod/temp/T/neurotic_docx_bench
R=results/redlines_0929_full; L=$R/jubarte-0.11.2; WD=/Users/arthrod/temp/T/jubarte-loop/word_watchdog.sh
mkdir -p $L/pdf_by_word
$WD $R/jubarte-0.11.2.word_pdf.log > /tmp/wordlane.wd1.log 2>&1 &
wd=$!
uv run --script scripts/word_pdf.py --src $L/docx --out $L/pdf_by_word --do-not-close --log $R/jubarte-0.11.2.word_pdf.log > $R/jubarte-0.11.2.word_pdf.out 2>&1
echo "BATCH exit $? $(date +%H:%M) pdfs $(ls $L/pdf_by_word | wc -l)" >> /tmp/wordlane.status
pkill -P $wd; kill $wd 2>/dev/null
$WD $R/jubarte-0.11.2.word_pdf.retry.log $L/pdf_by_word > /tmp/wordlane.wd2.log 2>&1 &
wd=$!
uv run --script scripts/word_pdf.py --src $L/docx --out $L/pdf_by_word --do-not-close --no-one-osascript --log $R/jubarte-0.11.2.word_pdf.retry.log > $R/jubarte-0.11.2.word_pdf.retry.out 2>&1
echo "RETRY exit $? $(date +%H:%M) pdfs $(ls $L/pdf_by_word | wc -l)" >> /tmp/wordlane.status
pkill -P $wd; kill $wd 2>/dev/null
echo "WORDLANE DONE $(date +%H:%M)" >> /tmp/wordlane.status