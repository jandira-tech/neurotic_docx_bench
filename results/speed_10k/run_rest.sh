#!/bin/zsh
# The rest of the 10k speed runs after the 2026-09-29 morning stop (see redlines/NOTES.md),
# one after another, every call capped at 120 s, each stage summarised and published to
# /speed/ as soon as it ends. Nothing measured before is measured again:
#   1. SuperDoc, all 10,000 pairs (superdoc-sdk 2.15.0; a timed-out host is killed and restarted)
#   2. DOCX -> PDF, 10,000 documents: jubarte, jubarte --compress, docxide-pdf, soffice
#   3. docxodus from p01335 on (the first 1,335 pairs were salvaged), npm docxodus 12.6.4
cd ~/temp/T/neurotic_docx_bench || exit 1

env_snapshot() {
  echo "$1 $(date -u +%FT%TZ)"
  uptime
  echo "busiest processes:"
  ps -Ao pcpu,etime,command -r | head -8 | cut -c1-140
}

# 1. SuperDoc
env_snapshot "superdoc start" >> results/speed_10k/redlines/ENV.txt
uv run python -m neurotic_docx_bench.superdoc_speed --pairs-csv results/speed_10k/pairs_10k.csv \
  --reps 1 --warmup 20 --timeout 120 \
  --per-pair-out results/speed_10k/redlines/per_pair/superdoc.jsonl \
  --out results/speed_10k/redlines/speed.jsonl \
  > results/speed_10k/redlines/superdoc_run.log 2>&1
echo "superdoc exit $?"
env_snapshot "superdoc end" >> results/speed_10k/redlines/ENV.txt
uv run python results/speed_10k/summarize.py redlines > /dev/null
zsh ~/temp/T/docxide_compare/publish_speed.sh "SuperDoc redline speed, 10,000 pairs"
echo "stage superdoc done"

# 2. DOCX -> PDF
zsh results/speed_10k/run_pdf_speed.sh
uv run python results/speed_10k/summarize.py pdf > /dev/null
zsh ~/temp/T/docxide_compare/publish_speed.sh "DOCX to PDF speed, 10,000 documents"
echo "stage pdf done"

# 3. docxodus, the pairs not yet measured
env_snapshot "docxodus resume start" >> results/speed_10k/redlines/ENV.txt
node --import tsx scripts/redline_speed_bench.ts --pairs-csv results/speed_10k/pairs_10k.csv \
  --methods docxodus --start-at p01335_word_compare --pair-timeout-ms 120000 \
  --warmup 20 --reps 1 --no-profile --out results/speed_10k/redlines \
  > results/speed_10k/redlines/docxodus_resume.log 2>&1
echo "docxodus exit $?"
rm -rf results/speed_10k/redlines/fixtures_bytes results/speed_10k/redlines/cpu
env_snapshot "docxodus resume end" >> results/speed_10k/redlines/ENV.txt
uv run python results/speed_10k/summarize.py redlines > /dev/null
zsh ~/temp/T/docxide_compare/publish_speed.sh "docxodus redline speed, 10,000 pairs"
echo "stage docxodus done"
echo "speed rest done"
