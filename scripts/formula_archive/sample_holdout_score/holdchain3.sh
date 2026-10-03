#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
until grep -q "PDF23 CHAIN DONE" /tmp/pdf-comments/chain.log; do sleep 30; done
for b in pdf22 pdf23; do
  rm -rf /tmp/pdf-hold/work-$b /tmp/pdf-hold/$b.json
  /tmp/run_pdflist.sh /tmp/pdf-hold /tmp/pdf-hold/list.txt $b /tmp/jubarte-$b
  echo "HOLD2 $b DONE" >> /tmp/pdf-hold/chain.log
done