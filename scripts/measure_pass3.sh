#!/bin/zsh
# Resume of measure_pass2 after external kill: speed lanes 3-6, lighthouse,
# visual-own-redlines ×3, bundles. Assumes servers on 5175/5176 are running and
# speed.jsonl already has the two folio-base rendering/redlines rows.
set -e
cd "$(dirname "$0")/.."
RC=results-compare
export BENCH_NO_UPDATE=1
READY="window.__folioReady === true || document.querySelectorAll('.layout-page').length > 0"

typeset -A URLS
URLS=(folio-base "http://127.0.0.1:5175/harness.html" folio-current "http://127.0.0.1:5176/harness.html")
typeset -A CORPORA
CORPORA=(visual_rendering corpus/word_based/docx_source visual_redlines corpus/word_based/docx_redlines_word visual_accepted_changes corpus/word_based/docx_accepted_word)

run_speed() {
  local tool=$1 benchmark=$2
  uv run python -m neurotic_docx_bench.playwright_speed \
    --docx-dir "${CORPORA[$benchmark]}" \
    --pairs 9999 --reps 2 --warmup 3 \
    --out "$RC/speed.jsonl" \
    --tool "${tool}-${benchmark}" --url "${URLS[$tool]}" \
    --file-input "#fileInput" --page-selector ".layout-page" \
    --readiness-js "$READY" --timeout-ms 90000
}

echo "── speed lanes (remaining 4)"
run_speed folio-base visual_accepted_changes
run_speed folio-current visual_rendering
run_speed folio-current visual_redlines
run_speed folio-current visual_accepted_changes

echo "── lighthouse ×5 each"
./scripts/lighthouse_folio.sh

echo "── visual-own-redlines (same current viewer for all three lanes)"
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
echo "MEASURE PASS 3 DONE"
