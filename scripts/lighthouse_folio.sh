#!/bin/zsh
# Lighthouse pass over both folio harness pages (3 runs each, desktop preset).
# Expects the vite servers already listening on 5175 (baseline) / 5176 (current).
set -e
cd "$(dirname "$0")/.."
OUT=results-compare/lighthouse
mkdir -p "$OUT"
# lighthouse.html = harness.html + a visible heading (same module graph); the
# bare harness paints nothing, which Lighthouse rejects with NO_FCP.
for pair in "folio-base:http://127.0.0.1:5175/lighthouse.html" "folio-current:http://127.0.0.1:5176/lighthouse.html"; do
  tool="${pair%%:*}"
  url="${pair#*:}"
  for i in 1 2 3 4 5; do
    echo "lighthouse $tool run $i"
    bunx lighthouse "$url" \
      --only-categories=performance \
      --preset=desktop \
      --output=json \
      --output-path="$OUT/${tool}_run${i}.json" \
      --chrome-flags="--headless=new" \
      --quiet || echo "lighthouse $tool run $i FAILED (continuing)"
  done
done
echo "lighthouse done → $OUT"
