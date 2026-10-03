#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
while ! grep -q "PDF8 CHAIN DONE" /tmp/pdf-comments/chain.log 2>/dev/null; do sleep 30; done
/tmp/run_pdf300.sh pdf9 /tmp/jubarte-pdf9
echo "PDF9 CHAIN DONE" >> /tmp/pdf-comments/chain.log