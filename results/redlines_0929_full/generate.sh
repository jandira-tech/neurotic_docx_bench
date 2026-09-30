#!/bin/zsh
# Redlines of every distinct pair in gen_pairs.csv, jubarte then docxodus, both through
# their long-lived inproc workers (see RUN.md). Run from the bench root. docxodus gets
# 120 s per pair, the speed lanes' limit; jubarte keeps the 15 s default (no pair hit it).
set -u
R=results/redlines_0929_full
JUBARTE_DIST=$HOME/temp/T/speed_bins/jubarte-inproc-86b6b5d3
DOCXODUS_DIST=src/neurotic_docx_bench/utils/docxodus/docxodus-csharp-inproc/bin/Release/net10.0
echo "jubarte-rust start $(date -u +%FT%TZ)"
node --import tsx scripts/generate-native-redlines.ts --method jubarte-rust-inproc --dist $JUBARTE_DIST \
  --tool jubarte-rust --manifest $R/gen_pairs.csv --source-dir corpus/word \
  --out $R/jubarte-rust/docx --run-dir $R/jubarte-rust > $R/jubarte-rust.generate.log 2>&1
echo "jubarte-rust exit $? $(date -u +%FT%TZ): $(ls $R/jubarte-rust/docx | wc -l) docx"
echo "docxodus start $(date -u +%FT%TZ)"
WORKER_REPLY_TIMEOUT_MS=120000 node --import tsx scripts/generate-native-redlines.ts --method docxodus-csharp-inproc --dist $DOCXODUS_DIST \
  --tool docxodus --manifest $R/gen_pairs.csv --source-dir corpus/word \
  --out $R/docxodus/docx --run-dir $R/docxodus > $R/docxodus.generate.log 2>&1
echo "docxodus exit $? $(date -u +%FT%TZ): $(ls $R/docxodus/docx | wc -l) docx"
echo "generate done"
