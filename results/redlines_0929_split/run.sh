#!/bin/zsh
# Tool side of the 400/400 accept/reject split (corpus/word/pools/accept_reject_split.csv).
# pool_pairs.csv holds the 800 split comparisons with their action. Each tool redlines every
# pair (the same generators and pins as bench.yaml: jubarte-redlines 0.9.3 native CLI,
# npm docxodus 12.6.4, superdoc-sdk), then Word accepts or rejects every change in the tool's
# redline, by the pair's action, and exports the result to PDF (scripts/word_pdf.py, one batch
# per folder). measure.py scores those PDFs against Word's own Accept All / Reject All of its
# compare (corpus/word/accept_all, corpus/word/reject_all).
#
# Runs beside the 10k speed lanes; ENV.txt of the speed run records the overlap.
cd ~/temp/T/neurotic_docx_bench || exit 1
R=results/redlines_0929_split
P=$R/pool_pairs.csv
echo "redlines_0929_split start $(date -u +%FT%TZ) (generation at nice 10, then Word batches)" >> results/speed_10k/redlines/ENV.txt

for t in jubarte-rust docxodus; do
  mkdir -p $R/$t
  if [[ $t == jubarte-rust ]]; then
    nice -n 10 node --import tsx scripts/generate-native-redlines.ts --method=jubarte-rust \
      --dist=src/neurotic_docx_bench/utils/jubarte/jubarte-rust \
      --manifest=$P --source-dir=corpus/word --out=$R/$t/docx --run-dir=$R/$t --tool=$t > $R/$t/generate.log 2>&1
  else
    nice -n 10 node --import tsx scripts/generate-native-redlines.ts --method=docxodus \
      --manifest=$P --source-dir=corpus/word --out=$R/$t/docx --run-dir=$R/$t --tool=$t > $R/$t/generate.log 2>&1
  fi
  echo "generate $t exit $? docx $(ls $R/$t/docx | wc -l)"
done
mkdir -p $R/superdoc
nice -n 10 uv run python -m neurotic_docx_bench.superdoc_gen --manifest $P --source-dir corpus/word \
  --out $R/superdoc/docx --tool superdoc > $R/superdoc/generate.log 2>&1
echo "generate superdoc exit $? docx $(ls $R/superdoc/docx | wc -l)"

# Stage each tool's redlines by action (APFS clones), then one Word batch per folder.
uv run python - <<'EOF'
import csv, subprocess
from pathlib import Path
R = Path("results/redlines_0929_split")
rows = list(csv.DictReader(open(R / "pool_pairs.csv")))
for tool in ("jubarte-rust", "docxodus", "superdoc"):
    for action in ("accept_all", "reject_all"):
        src = R / tool / action / "src"
        src.mkdir(parents=True, exist_ok=True)
        n = 0
        for r in rows:
            f = R / tool / "docx" / f"{r['key']}_{tool}.docx"
            if r["action"] == action and f.is_file() and not (src / f.name).exists():
                subprocess.run(["cp", "-c", str(f), str(src / f.name)], check=True)
            n += (src / f.name).exists()
        print(f"staged {tool} {action}: {n}")
EOF

echo "redlines_0929_split Word batches start $(date -u +%FT%TZ)" >> results/speed_10k/redlines/ENV.txt
for t in jubarte-rust docxodus superdoc; do
  for a in accept_all reject_all; do
    flag=--accept-all; [[ $a == reject_all ]] && flag=--reject-all
    mkdir -p $R/$t/$a/by_word
    uv run python scripts/word_pdf.py --src $R/$t/$a/src --out $R/$t/$a/by_word --no-check-preset $flag \
      --log $R/$t/$a/word.log > $R/$t/$a/word.out 2>&1
    echo "word $t $a exit $? pdf $(ls $R/$t/$a/by_word | grep -c '\.pdf$')"
  done
done
echo "redlines_0929_split end $(date -u +%FT%TZ)" >> results/speed_10k/redlines/ENV.txt
echo "split run done"
