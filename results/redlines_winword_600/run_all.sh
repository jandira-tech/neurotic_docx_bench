#!/bin/zsh
# Rebuild the redline_600 Contabo run from an empty folder (only the drivers and pairs.csv), then score it.
#
#     zsh results/redline600_contabo/run_all.sh        # from anywhere; ~3-4 h; progress in run_all.log
#
# Rebuilt on 2026-11-24 after the endpoint switched to Word for Mac's review view
# (word-endpoint/docs/review-view.md): every Contabo PDF made before it used mixed mode for redlines
# with comments. Order, as in the first run:
#   - Contabo: Word compares every pair and exports each redline (word/docx, word/pdf), then a pass for
#     anything missing.
#   - Local, one tool at a time so no generator times out for lack of CPU: jubarte 0.20.0, docxodus
#     16.1.0 (pairs.csv = the set's own keys), folio 0.70.0 (strict and emit), SuperDoc 2.31.0 (4 shards).
#   - Contabo: Word exports each tool's redlines (convert-lane), looping while generators and Word run.
#   - Local, once Word's redlines are all in: docxodus 16.1.0 and jubarte 0.20.0 draw them as PDFs.
#   - Scoring: measure.py on MPS; rasters live in temporary folders deleted after each chunk.
set -u
ROOT=/Users/arthrod/temp/T/neurotic_docx_bench
cd $ROOT || exit 1
R=results/redline600_contabo
S=.scratch/redline600-contabo
F=$S/rerun/flags
J=$HOME/.cache/neurotic-docx-bench/jubarte/0.20.0/jubarte-0.20.0-macos-aarch64/jubarte
DX=$S/docxodus-export/node_modules/.bin/docxodus
LANES=(--lane jubarte-0.20.0 --lane docxodus-16.1.0 --lane folio-0.70.0-emit --lane superdoc-2.31.0)
mkdir -p $F
rm -f "${F:?}"/word.done "${F:?}"/gen.done "${F:?}"/lanes.done "${F:?}"/pdf.done
log() { print -r -- "$(date -u +%FT%TZ) $*" | tee -a $R/run_all.log }
await() { while [[ ! -e $F/$1 ]]; do sleep 30; done }

ready=$(set -a; source .env; set +a; curl -s -m 20 -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $WORD_API_TOKEN" "$WORD_PUBLIC_URL/ready")
[[ $ready == 200 ]] || { log "endpoint /ready says $ready; not starting"; exit 1 }
log "start; endpoint ready; $(wc -l < $R/pairs.csv | tr -d ' ') lines in pairs.csv"

{   # Contabo: Word's own redlines and their PDFs (the reference of both tests)
    uv run --script $R/contabo_word.py compare convert-word > $R/word.contabo.log 2>&1
    log "word: first pass exit $?; $(tail -1 $R/word.contabo.log)"
    uv run --script $R/contabo_word.py compare convert-word --inflight 1 > $R/word.retry.log 2>&1
    log "word: missing-only pass exit $?; $(tail -1 $R/word.retry.log)"
    touch $F/word.done
} &

{   # Contabo: each tool's redlines exported by the same Word, as they land
    while [[ ! -e $F/gen.done || ! -e $F/word.done ]]; do
        uv run --script $R/contabo_word.py convert-lane $LANES --inflight 1 >> $R/lanes.contabo.log 2>&1
        sleep 60
    done
    for pass in 1 2; do
        uv run --script $R/contabo_word.py convert-lane $LANES --inflight 2 >> $R/lanes.contabo.log 2>&1
        log "lanes: final pass $pass exit $?; $(tail -1 $R/lanes.contabo.log)"
    done
    touch $F/lanes.done
} &

# Local generators, one at a time
.venv/bin/python $R/jubarte_lanes.py --binary $J --task redline --jobs 6 > $R/jubarte_redlines.log 2>&1
log "jubarte redlines exit $?; $(tail -1 $R/jubarte_redlines.log)"
node --import tsx scripts/generate-native-redlines.ts --method docxodus --tool docxodus-16.1.0 --manifest $R/pairs.csv \
    --source-dir . --out $R/docxodus-16.1.0/docx --run-dir $R/docxodus-16.1.0 > $R/docxodus-16.1.0.generate.log 2>&1
log "docxodus redlines exit $?; $(ls $R/docxodus-16.1.0/docx | wc -l | tr -d ' ') docx"
node --import tsx $R/folio_redlines.ts --folio-dir $S/folio --jobs 6 --timeout 300 > $R/folio_redlines.log 2>&1
log "folio redlines exit $?; $(tail -1 $R/folio_redlines.log)"
.venv/bin/python - $R/pairs.csv $S/superdoc <<'EOF'
import csv, sys
from pathlib import Path
rows = list(csv.DictReader(open(sys.argv[1])))
for i in range(4):
    with open(Path(sys.argv[2]) / f'shard{i}.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, ['key', 'base', 'next']); w.writeheader(); w.writerows(rows[i::4])
EOF
pids=()
for i in 0 1 2 3; do
    .venv/bin/python -m neurotic_docx_bench.superdoc_gen --manifest $S/superdoc/shard$i.csv --source-dir . \
        --out $S/superdoc/shard$i/docx --tool superdoc-2.31.0 > $S/superdoc/shard$i.log 2>&1 &
    pids+=($!)
done
wait $pids
.venv/bin/python $S/superdoc/link_done.py $S/superdoc $R/superdoc-2.31.0 --final > $R/superdoc.generate.log 2>&1
log "superdoc redlines: $(head -1 $R/superdoc.generate.log)"
touch $F/gen.done

# Local PDF lanes, once Word's redlines are all in
await word.done
.venv/bin/python $R/docxodus_pdf.py --binary $DX --jobs 4 > $R/docxodus_pdf.log 2>&1
log "docxodus pdf exit $?; $(tail -1 $R/docxodus_pdf.log)"
.venv/bin/python $R/jubarte_lanes.py --binary $J --task convert --jobs 6 > $R/jubarte_pdf.log 2>&1
log "jubarte pdf exit $?; $(tail -1 $R/jubarte_pdf.log)"
touch $F/pdf.done

await lanes.done
wait
log "all outputs in; scoring on MPS"
.venv/bin/python $R/measure.py word-mac redline redline-jubarte redline-folio-emit redline-superdoc convert convert-jubarte \
    --device mps > $R/measure.log 2>&1
log "measure exit $?"
grep -E '^[a-z-]+: [0-9]+/[0-9]+ scored' $R/measure.log | tee -a $R/run_all.log
