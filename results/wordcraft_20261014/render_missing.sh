#!/bin/bash
cd /Users/arthrod/temp/T/neurotic_docx_bench || exit 1
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
R=results/wordcraft_20261014
.venv/bin/python scripts/word_pdf.py --src $R/compare/jubarte-0.11.0/docx --out $R/compare/jubarte-0.11.0/pdf --no-check-preset --crash-limit 1 --log $R/jubarte_word_pdf_retry3.log > $R/jubarte_word_pdf_retry3.out 2>&1
.venv/bin/python scripts/word_pdf.py --src $R/compare/wordcraft/docx --out $R/compare/wordcraft/pdf --no-check-preset --crash-limit 1 --log $R/wordcraft_word_pdf_retry3.log > $R/wordcraft_word_pdf_retry3.out 2>&1
