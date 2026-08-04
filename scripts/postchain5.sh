#!/bin/zsh
# Final measurement chain: lighthouse (fixed NO_FCP) → visual-own-redlines ×3 →
# bundles → stop servers → postchain4 (wasm regen, folio-wasm rerun, reject-compare).
set -e
cd "$(dirname "$0")/.."
RC=results-compare
export BENCH_NO_UPDATE=1

echo "── lighthouse ×5 each (lighthouse.html) $(date +%H:%M:%S)"
./scripts/lighthouse_folio.sh

echo "── visual-own-redlines $(date +%H:%M:%S)"
uv run python scripts/visual_own_redlines.py \
  --docx-dir "$(ls -d runs-compare/folio_2026* | tail -1)/docx" --tool folio \
  --url "http://127.0.0.1:5176/harness.html" --out "$RC/visual_own_redlines.jsonl"
uv run python scripts/visual_own_redlines.py \
  --docx-dir "$(ls -d runs-compare/folio-current_2026* | tail -1)/docx" --tool folio-current \
  --url "http://127.0.0.1:5176/harness.html" --out "$RC/visual_own_redlines.jsonl"
uv run python scripts/visual_own_redlines.py \
  --docx-dir "$(ls -d runs-compare/folio-wasm_2026* | tail -1)/docx" --tool folio-wasm \
  --url "http://127.0.0.1:5176/harness.html" --out "$RC/visual_own_redlines.jsonl"

echo "── production bundle sizes $(date +%H:%M:%S)"
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

./scripts/postchain4.sh
echo "POSTCHAIN5 DONE $(date +%H:%M:%S)"
