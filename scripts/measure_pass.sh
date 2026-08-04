#!/bin/zsh
# Full-corpus measurement pass over BOTH folio harnesses (apples to apples):
#   1. CDP per-document metrics (render ms, post-GC JS heap, script/layout, DOM)
#   2. playwright_speed ms_per_render rows (full corpus, warmup+reps)
#   3. Lighthouse ×5 per harness
#   4. Production vite build → bundle sizes
# Servers: 5175 = vendored baseline harness, 5176 = current-build harness.
set -e
cd "$(dirname "$0")/.."
RC=results-compare
mkdir -p "$RC"

echo "── starting harness servers"
(cd src/neurotic_docx_bench/utils/folio/harness/folio-viewer && ./node_modules/.bin/vite --port 5175 --host 127.0.0.1 >/tmp/vite5175.log 2>&1 &)
(cd harness/folio-viewer-current && ./node_modules/.bin/vite --port 5176 --host 127.0.0.1 >/tmp/vite5176.log 2>&1 &)
for port in 5175 5176; do
  for i in $(seq 1 60); do
    curl -s -o /dev/null "http://127.0.0.1:$port/harness.html" && break
    sleep 1
  done
  curl -s -o /dev/null -w "port $port: %{http_code}\n" "http://127.0.0.1:$port/harness.html"
done

typeset -A URLS
URLS=(folio-base "http://127.0.0.1:5175/harness.html" folio-current "http://127.0.0.1:5176/harness.html")
typeset -A CORPORA
CORPORA=(visual_rendering corpus/word_based/docx_source visual_redlines corpus/word_based/docx_redlines_word visual_accepted_changes corpus/word_based/docx_accepted_word)

echo "── CDP per-document passes (full corpus)"
for tool in folio-base folio-current; do
  for benchmark in visual_rendering visual_redlines visual_accepted_changes; do
    uv run python scripts/cdp_folio_measure.py \
      --url "${URLS[$tool]}" --docx-dir "${CORPORA[$benchmark]}" \
      --tool "$tool" --benchmark "$benchmark" \
      --out "$RC/cdp_${tool}_${benchmark}.jsonl" --workers 4
  done
done

echo "── playwright_speed (bench ms_per_render, full corpus, warmup 3, reps 2)"
for tool in folio-base folio-current; do
  for benchmark in visual_rendering visual_redlines visual_accepted_changes; do
    uv run python -m neurotic_docx_bench.playwright_speed \
      --docx-dir "${CORPORA[$benchmark]}" \
      --pairs 9999 --reps 2 --warmup 3 \
      --out "$RC/speed.jsonl" \
      --tool "${tool}-${benchmark}" --url "${URLS[$tool]}" \
      --file-input "#fileInput" --page-selector ".layout-page" \
      --readiness-js "window.__folioReady === true" --timeout-ms 90000
  done
done

echo "── lighthouse ×5 each"
./scripts/lighthouse_folio.sh

echo "── production bundle sizes"
(cd src/neurotic_docx_bench/utils/folio/harness/folio-viewer && rm -rf dist && ./node_modules/.bin/vite build >/dev/null 2>&1)
(cd harness/folio-viewer-current && rm -rf dist && ./node_modules/.bin/vite build >/dev/null 2>&1)
python3 - <<'EOF'
import json
from pathlib import Path

def sizes(dist):
    js = sum(f.stat().st_size for f in Path(dist).rglob("*.js"))
    css = sum(f.stat().st_size for f in Path(dist).rglob("*.css"))
    total = sum(f.stat().st_size for f in Path(dist).rglob("*") if f.is_file())
    return {"js": js, "css": css, "total": total}

out = {
    "baseline": sizes("src/neurotic_docx_bench/utils/folio/harness/folio-viewer/dist"),
    "current": sizes("harness/folio-viewer-current/dist"),
}
Path("results-compare/bundle_sizes.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
EOF

echo "── stopping servers"
pkill -f "vite --port 517" || true
echo "MEASURE PASS DONE"
