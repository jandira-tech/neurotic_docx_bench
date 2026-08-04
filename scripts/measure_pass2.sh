#!/bin/zsh
# Continuation of the measurement pass after the readiness-JS fix.
# Assumes both harness servers are ALREADY running (5175 baseline, 5176 current).
# Order: folio-wasm rerun (regenerated 094a10c wasm) → speed lanes (fixed
# readiness) → lighthouse → visual-own-redlines ×3 → bundles → stop servers.
set -e
cd "$(dirname "$0")/.."
RC=results-compare
export BENCH_NO_UPDATE=1

# The bench.yaml readiness contract (with the .layout-page fallback) — the
# `window.__folioReady === true` docstring form alone never fires on this
# harness and burns the full timeout per call.
READY="window.__folioReady === true || document.querySelectorAll('.layout-page').length > 0"

echo "── folio-wasm rerun with regenerated wasm (094a10c)"
uv run bench run --config bench.compare.yaml --only folio-wasm --rerun \
  --results-dir results-compare --runs-dir runs-compare --no-gate --accept-compare

typeset -A URLS
URLS=(folio-base "http://127.0.0.1:5175/harness.html" folio-current "http://127.0.0.1:5176/harness.html")
typeset -A CORPORA
CORPORA=(visual_rendering corpus/word_based/docx_source visual_redlines corpus/word_based/docx_redlines_word visual_accepted_changes corpus/word_based/docx_accepted_word)

echo "── playwright_speed (full corpus, warmup 3, reps 2, fixed readiness)"
for tool in folio-base folio-current; do
  for benchmark in visual_rendering visual_redlines visual_accepted_changes; do
    uv run python -m neurotic_docx_bench.playwright_speed \
      --docx-dir "${CORPORA[$benchmark]}" \
      --pairs 9999 --reps 2 --warmup 3 \
      --out "$RC/speed.jsonl" \
      --tool "${tool}-${benchmark}" --url "${URLS[$tool]}" \
      --file-input "#fileInput" --page-selector ".layout-page" \
      --readiness-js "$READY" --timeout-ms 90000
  done
done

echo "── lighthouse ×5 each"
./scripts/lighthouse_folio.sh

echo "── visual-own-redlines (each lane's generated redlines through the SAME current viewer)"
uv run python scripts/visual_own_redlines.py \
  --docx-dir "$(ls -d runs-compare/folio_2026* | tail -1)/docx" --tool folio \
  --url "http://127.0.0.1:5176/harness.html" --out "$RC/visual_own_redlines.jsonl"
uv run python scripts/visual_own_redlines.py \
  --docx-dir "$(ls -d runs-compare/folio-current_2026* | tail -1)/docx" --tool folio-current \
  --url "http://127.0.0.1:5176/harness.html" --out "$RC/visual_own_redlines.jsonl"
uv run python scripts/visual_own_redlines.py \
  --docx-dir "$(ls -d runs-compare/folio-wasm_2026* | tail -1)/docx" --tool folio-wasm \
  --url "http://127.0.0.1:5176/harness.html" --out "$RC/visual_own_redlines.jsonl"

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
echo "MEASURE PASS 2 DONE"
