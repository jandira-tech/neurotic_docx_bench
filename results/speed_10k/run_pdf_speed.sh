#!/bin/zsh
# 10,000-document DOCX -> PDF speed run (pdf_docs_10k.txt): jubarte, jubarte --compress,
# docxide-pdf and soffice, round robin per document. Every PDF goes to one temp file per tool,
# overwritten by the next sample and removed at the end; only the timings are kept.
#   jubarte: jubarte-redlines 0.9.3 @673aff74 (the bench's redline binary)
cd ~/temp/T/neurotic_docx_bench || exit 1
mkdir -p results/speed_10k/pdf

{
  echo "start $(date -u +%FT%TZ)"
  uptime
  sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize
  echo "busiest processes at start:"
  ps -Ao pcpu,etime,command -r | head -6 | cut -c1-140
} > results/speed_10k/pdf/ENV.txt

uv run python scripts/docx_to_pdf_speed.py \
  --jubarte src/neurotic_docx_bench/utils/jubarte/jubarte-rust/redline \
  --corpus all10k=@results/speed_10k/pdf_docs_10k.txt \
  --tools jubarte,jubarte-compress,docxide,soffice --timeout 120 \
  --out results/speed_10k/pdf > results/speed_10k/pdf/run.log 2>&1
echo "pdf speed exit $?"

{
  echo "end $(date -u +%FT%TZ)"
  uptime
  echo "soffice processes left behind:"
  ps -Ao pid,etime,command | grep -a '[s]office.*d2p-speed' | cut -c1-160
} >> results/speed_10k/pdf/ENV.txt
echo "pdf speed done"
