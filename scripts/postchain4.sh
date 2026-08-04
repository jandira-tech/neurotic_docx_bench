#!/bin/zsh
# Post-measurement chain: regenerate wasm → rerun folio-wasm lane → reject-compare.
set -e
cd "$(dirname "$0")/.."
export PATH="$HOME/.cargo/bin:$PATH"
export BENCH_NO_UPDATE=1
RC=results-compare

echo "── wasm regenerate $(date +%H:%M:%S)"
git -C /Users/arthrod/temp/T/jubarte-redlines log --oneline -1 | cat
(cd src/neurotic_docx_bench/utils/jubarte/jubarte-wasm && wasm-pack build --target nodejs --release > /dev/null 2>&1 && shasum -a 256 pkg/jubarte_wasm_bg.wasm)

echo "── folio-wasm rerun $(date +%H:%M:%S)"
uv run bench run --config bench.compare.yaml --only folio-wasm --rerun \
  --results-dir results-compare --runs-dir runs-compare --no-gate --accept-compare

echo "── reject-compare: docx-revisions backend, all three lanes $(date +%H:%M:%S)"
uv run python scripts/reject_compare.py \
  --redline-dir "$(ls -d runs-compare/folio_2026* | tail -1)/docx" --tool folio \
  --backend docx-revisions --out "$RC/reject_compare.jsonl"
uv run python scripts/reject_compare.py \
  --redline-dir "$(ls -d runs-compare/folio-current_2026* | tail -1)/docx" --tool folio-current \
  --backend docx-revisions --out "$RC/reject_compare.jsonl"
uv run python scripts/reject_compare.py \
  --redline-dir "$(ls -d runs-compare/folio-wasm_2026* | tail -1)/docx" --tool folio-wasm \
  --backend docx-revisions --out "$RC/reject_compare.jsonl"

echo "── reject-compare: folio+wasm engine reject (REJECT-LOSSLESS path) $(date +%H:%M:%S)"
uv run python scripts/reject_compare.py \
  --redline-dir "$(ls -d runs-compare/folio-wasm_2026* | tail -1)/docx" --tool folio-wasm \
  --backend folio-wasm --out "$RC/reject_compare.jsonl"

echo "POSTCHAIN4 DONE $(date +%H:%M:%S)"
