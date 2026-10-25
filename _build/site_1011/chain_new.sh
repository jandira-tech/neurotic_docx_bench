#!/bin/zsh
# Word renders of the 57 replacement pairs only (docxodus last), then score/encode every page and upload.
R=/Users/arthrod/temp/T/neurotic_docx_bench/results/site_1011
H=/Users/arthrod/temp/T/site_1011
cd /Users/arthrod/temp/T/neurotic_docx_bench
for pass in 1 2; do
  uv run scripts/word_pdf.py -s $R/word_render_new/jubarte-compare -o $R/word_render/jubarte --label jubarte -q --log $R/word_render/jubarte_new$pass.log > /dev/null 2>&1
done
for pass in 1 2; do
  uv run scripts/word_pdf.py -s $R/word_render_new/docxodus -o $R/word_render/docxodus --label docxodus -q --log $R/word_render/docxodus_new$pass.log > /dev/null 2>&1
done
echo "new renders: jubarte $(ls $R/word_render/jubarte | wc -l), docxodus $(ls $R/word_render/docxodus | wc -l)"
cd $H
uv run --quiet --with pillow python process.py redlines
bunx wrangler whoami > /dev/null 2>&1
uv run --quiet --with httpx python upload_r2.py redlines
echo "NEW CHAIN DONE"
