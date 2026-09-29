#!/bin/zsh
# Word Reject All on the 100 reject_selection pairs: Word's own redline first (corpus set
# rejected_tracking_0928), then each tool's redline of the same pair. One word_pdf.py batch
# per folder, run in sequence (Word is one process).
cd ~/temp/T/neurotic_docx_bench || exit 1

mkdir -p grok_run/wr0928/rejected_tracking/out
./scripts/word_pdf.py --src grok_run/wr0928/rejected_tracking/src_word --out grok_run/wr0928/rejected_tracking/out \
  --no-check-preset --reject-all --log grok_run/wr0928/rejected_tracking/reject_word.log \
  > grok_run/wr0928/rejected_tracking/reject_word.out 2>&1
echo "reject word: $(ls grok_run/wr0928/rejected_tracking/out/*.pdf | wc -l) pdf; $(grep -a -c 'FAIL:' grok_run/wr0928/rejected_tracking/reject_word.log) FAIL"

mkdir -p results/redlines_0928/jubarte-rust/rejected/out
./scripts/word_pdf.py --src results/redlines_0928/jubarte-rust/rejected/src --out results/redlines_0928/jubarte-rust/rejected/out \
  --no-check-preset --reject-all --reject-suffix _rejected_tracking_jubarte-rust \
  --log results/redlines_0928/jubarte-rust/rejected/reject.log > results/redlines_0928/jubarte-rust/rejected/reject.out 2>&1
echo "reject jubarte-rust: $(ls results/redlines_0928/jubarte-rust/rejected/out/*.pdf | wc -l) pdf; $(grep -a -c 'FAIL:' results/redlines_0928/jubarte-rust/rejected/reject.log) FAIL"

mkdir -p results/redlines_0928/docxodus/rejected/out
./scripts/word_pdf.py --src results/redlines_0928/docxodus/rejected/src --out results/redlines_0928/docxodus/rejected/out \
  --no-check-preset --reject-all --reject-suffix _rejected_tracking_docxodus \
  --log results/redlines_0928/docxodus/rejected/reject.log > results/redlines_0928/docxodus/rejected/reject.out 2>&1
echo "reject docxodus: $(ls results/redlines_0928/docxodus/rejected/out/*.pdf | wc -l) pdf; $(grep -a -c 'FAIL:' results/redlines_0928/docxodus/rejected/reject.log) FAIL"

mkdir -p results/redlines_0928/superdoc/rejected/out
./scripts/word_pdf.py --src results/redlines_0928/superdoc/rejected/src --out results/redlines_0928/superdoc/rejected/out \
  --no-check-preset --reject-all --reject-suffix _rejected_tracking_superdoc \
  --log results/redlines_0928/superdoc/rejected/reject.log > results/redlines_0928/superdoc/rejected/reject.out 2>&1
echo "reject superdoc: $(ls results/redlines_0928/superdoc/rejected/out/*.pdf | wc -l) pdf; $(grep -a -c 'FAIL:' results/redlines_0928/superdoc/rejected/reject.log) FAIL"
echo "reject queue done"
