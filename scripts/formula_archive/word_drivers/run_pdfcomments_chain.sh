#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# wait for the 300 run, then score main and pdf3 on every corpus comment document
while ! grep -q "PDF300 pdf3 DONE" /tmp/pdf-300/pdf3.log 2>/dev/null; do sleep 30; done
/tmp/run_pdfcomments.sh main /tmp/jubarte-main
/tmp/run_pdfcomments.sh pdf3 /tmp/jubarte-pdf3
echo "COMMENTS CHAIN DONE" >> /tmp/pdf-comments/chain.log