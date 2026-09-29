#!/bin/zsh
# Both mini-bench selections: convert with every tool (latest builds), score both lenses.
# jubarte is v0.10.0 built from the canonical checkout's tag (86b6b5d3).
cd ~/temp/T/neurotic_docx_bench || exit 1
J=~/temp/T/speed_bins/jubarte-86b6b5d3
echo "mini_bench start $(date -u +%FT%TZ) (sequential converts, scoring 4 workers at nice 10)" >> results/speed_10k/redlines/ENV.txt
for s in jubarte093_le3_w200 jubarte093_all_w200; do
  O=results/mini_bench/$s
  uv run python scripts/mini_bench.py convert --out $O --jubarte $J --timeout 120 > $O/convert.log 2>&1
  echo "convert $s exit $?"
  nice -n 10 uv run python scripts/mini_bench.py score --out $O --jobs 4 > $O/score.log 2>&1
  echo "score $s exit $?"
done
echo "mini_bench end $(date -u +%FT%TZ)" >> results/speed_10k/redlines/ENV.txt
echo "mini bench done"
