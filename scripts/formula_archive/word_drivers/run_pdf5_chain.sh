#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
while ! grep -q "PDF4 CHAIN DONE" /tmp/pdf-comments/chain.log 2>/dev/null; do sleep 30; done
/tmp/run_pdf300.sh pdf5 /tmp/jubarte-pdf5
echo "PDF5 CHAIN DONE" >> /tmp/pdf-comments/chain.log