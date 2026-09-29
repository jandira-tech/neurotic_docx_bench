#!/bin/zsh
# 10,000-pair redline speed run (pairs_10k.csv), one engine at a time. Only measurements are
# kept: every redline is held in memory (Node lanes) or deleted right after it is timed
# (SuperDoc), and the fixture byte copies the Node harness writes are removed at the end.
#   jubarte-rust-inproc, jubarte-rust, jubarte-wasm: jubarte-redlines 0.9.3 @673aff74
#   docxodus: npm docxodus 12.6.4 (WASM); superdoc: superdoc-sdk 2.15.0 (file based)
cd ~/temp/T/neurotic_docx_bench || exit 1
mkdir -p results/speed_10k/redlines

{
  echo "start $(date -u +%FT%TZ)"
  uptime
  sysctl -n machdep.cpu.brand_string hw.ncpu hw.memsize
  echo "busiest processes at start:"
  ps -Ao pcpu,etime,command -r | head -6 | cut -c1-140
} > results/speed_10k/redlines/ENV.txt

node --import tsx scripts/redline_speed_bench.ts --pairs-csv results/speed_10k/pairs_10k.csv \
  --methods jubarte-rust-inproc,jubarte-rust,jubarte-wasm,docxodus --warmup 20 --reps 1 --no-profile \
  --out results/speed_10k/redlines \
  --rust-inproc-dist /Users/arthrod/temp/T/speed_bins/jubarte-inproc-673aff74 \
  --wasm-dist /Users/arthrod/temp/T/speed_bins/jubarte-wasm-673aff74 \
  > results/speed_10k/redlines/node_run.log 2>&1
echo "node lanes exit $?"
rm -rf results/speed_10k/redlines/fixtures_bytes results/speed_10k/redlines/cpu

uv run python -m neurotic_docx_bench.superdoc_speed --pairs-csv results/speed_10k/pairs_10k.csv \
  --reps 1 --warmup 20 --timeout 120 \
  --per-pair-out results/speed_10k/redlines/per_pair/superdoc.jsonl \
  --out results/speed_10k/redlines/speed.jsonl \
  > results/speed_10k/redlines/superdoc_run.log 2>&1
echo "superdoc exit $?"

{
  echo "end $(date -u +%FT%TZ)"
  uptime
} >> results/speed_10k/redlines/ENV.txt
echo "redline speed done"
