#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# ab.sh BIN TAG : regenerate every jubarte PDF with BIN, score fixtures_500 (+extras), docxide suite, redlines.
set -uo pipefail
BIN=$1; TAG=$2; L=/Users/arthrod/temp/T/jubarte-loop; G=/Users/arthrod/temp/T/neurotic_docx_bench/grok_run
cd "$G"; find fixtures_500_pdf_jubarte -name '*.pdf' -delete
ls fixtures_500 | grep '\.docx$' | sed 's/\.docx$//' | xargs -P 10 -I@ "$BIN" convert fixtures_500/@.docx -o fixtures_500_pdf_jubarte/@.pdf --force --revisions word >/dev/null 2>&1
echo "f500 pdfs: $(ls fixtures_500_pdf_jubarte | wc -l)"
cd "$L"; python3 refbench.py "f5_$TAG" fixtures_500_pdf | head -1; python3 extrabench.py "ex_$TAG" | tail -1
python3 dxs.py "$BIN" "dx_$TAG" | tail -1; python3 redl/rs.py "$BIN" "rl_$TAG" | tail -2
