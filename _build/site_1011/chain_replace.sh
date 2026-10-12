#!/bin/zsh
# After the main Word render chain: Word compare the replacement candidates, pick, run the tools, render.
R=/Users/arthrod/temp/T/neurotic_docx_bench/results/site_1011
H=/Users/arthrod/temp/T/site_1011
cd /Users/arthrod/temp/T/neurotic_docx_bench
until grep -q "docxodus pass 3" $R/word_render/progress.txt 2>/dev/null; do sleep 30; done
mkdir -p $R/word_compare_r/{out,docx}
for pass in 1 2; do
  uv run scripts/word_redline.py -a $R/word_compare_r/A -b $R/word_compare_r/B -o $R/word_compare_r/out --docx-out $R/word_compare_r/docx --emit both -q --log $R/word_compare_r/pass$pass.log > $R/word_compare_r/pass$pass.out 2>&1
  echo "compare_r pass $pass: $(ls $R/word_compare_r/out | wc -l) pdfs" >> $R/word_render/progress.txt
done
python3 -I $H/replace.py pick >> $R/word_render/progress.txt 2>&1
python3 -I $H/run_tools.py jubarte-compare >> $R/word_render/progress.txt 2>&1
python3 -I $H/run_docxodus.py >> $R/word_render/progress.txt 2>&1
for pass in 1 2; do
  uv run scripts/word_pdf.py -s $R/jubarte-compare/docx -o $R/word_render/jubarte --label jubarte -q --log $R/word_render/jubarte_r$pass.log > /dev/null 2>&1
  echo "jubarte_r pass $pass: $(ls $R/word_render/jubarte | wc -l) pdfs" >> $R/word_render/progress.txt
done
for pass in 1 2; do
  uv run scripts/word_pdf.py -s $R/docxodus/docx -o $R/word_render/docxodus --label docxodus -q --log $R/word_render/docxodus_r$pass.log > /dev/null 2>&1
  echo "docxodus_r pass $pass: $(ls $R/word_render/docxodus | wc -l) pdfs" >> $R/word_render/progress.txt
done
echo "REPLACE CHAIN DONE" >> $R/word_render/progress.txt
