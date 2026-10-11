#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# holdout gate chain: select after the pool baseline, then score each build on the holdout list
until grep -q "PDFLIST pool-main DONE" /tmp/pdf-hold/pool-main.log 2>/dev/null; do sleep 20; done
cd ~/T/neurotic_docx_bench && uv run python /tmp/pdf-hold/select_holdout.py > /tmp/pdf-hold/select.log 2>&1
echo "HOLD SELECT DONE" >> /tmp/pdf-hold/chain.log
/tmp/run_pdflist.sh /tmp/pdf-hold /tmp/pdf-hold/list.txt main /tmp/jubarte-main
echo "HOLD main DONE" >> /tmp/pdf-hold/chain.log
/tmp/run_pdflist.sh /tmp/pdf-hold /tmp/pdf-hold/list.txt pdf18 /tmp/jubarte-pdf18
echo "HOLD pdf18 DONE" >> /tmp/pdf-hold/chain.log
until grep -q "PDF19 CHAIN DONE" /tmp/pdf-comments/chain.log; do sleep 20; done
/tmp/run_pdflist.sh /tmp/pdf-hold /tmp/pdf-hold/list.txt pdf19 /tmp/jubarte-pdf19
echo "HOLD pdf19 DONE" >> /tmp/pdf-hold/chain.log
until grep -q "PDF20 CHAIN DONE" /tmp/pdf-comments/chain.log; do sleep 20; done
/tmp/run_pdflist.sh /tmp/pdf-hold /tmp/pdf-hold/list.txt pdf20 /tmp/jubarte-pdf20
echo "HOLD pdf20 DONE" >> /tmp/pdf-hold/chain.log