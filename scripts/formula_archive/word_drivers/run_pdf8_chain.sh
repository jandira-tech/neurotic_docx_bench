#!/bin/zsh
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
while ! grep -q "PDF7 CHAIN DONE" /tmp/pdf-comments/chain.log 2>/dev/null; do sleep 30; done
/tmp/run_pdf300.sh pdf8 /tmp/jubarte-pdf8
echo "PDF8 CHAIN DONE" >> /tmp/pdf-comments/chain.log