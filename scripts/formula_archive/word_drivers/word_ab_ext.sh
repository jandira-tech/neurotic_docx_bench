#!/bin/bash
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
# word_ab_ext.sh SHA [BASE_SHA] : Word-truth A_redline scores for a jubarte build, written ONLY under
# jubarte-loop/wordab (the bench is read-only: sources, Word references, base PDFs, scorers).
# Regenerates every redline, reuses the base build's Word PDF when the redline's parts are identical,
# Word-converts only the changed ones (batch, then one document per call), then scores.
set -u
J=$1; P=${2:-c6307ac}; N=/Users/arthrod/temp/T/neurotic_docx_bench; G=$N/grok_run; WR=$G/wr0926; L=/Users/arthrod/temp/T/jubarte-loop
X=$L/wordab; OUT=$X/results/redline_wordpdf; JB=$L/bin/jubarte-$J
SC=$N/src/neurotic_docx_bench/utils/docxide-metrics/target/release/docxide-metrics
mkdir -p $OUT $X/$J
# base PDFs: a previous external run if there is one, else the bench's
pdfdir(){ if [ -d $X/$2/$1 ]; then echo $X/$2/$1; elif [ $1 = pools_pdf ]; then echo $WR/A_jubredline_wordpdf_$2; else echo $G/en_A_jubredline_wordpdf_$2; fi; }
docxdir(){ if [ -d $X/$2/$1 ]; then echo $X/$2/$1; elif [ $1 = pools_docx ]; then echo $WR/A_jub$2_docx; else echo $G/en_jubarte_redlines_$2; fi; }
cd $N
sed -e "s#$WR/A_jub6fd4043_docx#$X/$J/pools_docx#" -e "s#$G/en_jubarte_redlines_6fd4043#$X/$J/en_docx#" /tmp/jubgen_6fd4043.txt \
  | grep -v -F -f <(cut -f1 $G/word_blacklist/blacklist.tsv) | tr -d '\r' > $X/$J/gen.txt
mkdir -p $X/$J/pools_docx $X/$J/en_docx
xargs -P 8 -L 1 sh -c 'timeout 300 '$JB' "$0" "$1" -o "$2" --force > /dev/null 2>&1' < $X/$J/gen.txt
echo "=== $(date +%T) generated pools $(ls $X/$J/pools_docx | wc -l) en $(ls $X/$J/en_docx | wc -l)"
python3 - $X/$J "$(docxdir pools_docx $P)" "$(pdfdir pools_pdf $P)" "$(docxdir en_docx $P)" "$(pdfdir en_pdf $P)" <<'PY'
import sys, zipfile, pathlib, shutil
X = pathlib.Path(sys.argv[1]); pd, pp, ed, ep = map(pathlib.Path, sys.argv[2:6])
def parts(p):
    try: z = zipfile.ZipFile(p); return {n: z.read(n) for n in z.namelist()}
    except Exception: return None
for new, old, oldpdf, tag in ((X / 'pools_docx', pd, pp, 'pools'), (X / 'en_docx', ed, ep, 'en')):
    newpdf = X / f'{tag}_pdf'; stage = X / f'{tag}_changed'; newpdf.mkdir(exist_ok=True); stage.mkdir(exist_ok=True)
    same = changed = 0
    for d in sorted(new.glob('*.docx')):
        o = old / d.name; pdf = oldpdf / (d.stem + '.pdf')
        if o.exists() and pdf.exists() and parts(o) == parts(d):
            shutil.copy2(pdf, newpdf / pdf.name); same += 1
        else:
            shutil.copy2(d, stage / d.name); changed += 1
    print(tag, 'same', same, 'changed', changed, flush=True)
PY
wordpdf(){ mkdir -p $2; uv run --script scripts/word_pdf.py --src $1 --out $2 --no-check-preset -q --log $2.log > /dev/null 2>&1
  uv run --script scripts/word_pdf.py --src $1 --out $2 --no-check-preset --no-one-osascript -q --log $2.retry.log > /dev/null 2>&1
  echo "=== $(date +%T) word_pdf $1 -> $(ls $2 | wc -l) pdf"; }
pkill -f "[w]ord_watchdog.sh"
(cd $L && nohup ./word_watchdog.sh $X/$J/pools_pdf $X/$J/pools_pdf.log $X/$J/pools_pdf.retry.log $X/$J/en_pdf $X/$J/en_pdf.log $X/$J/en_pdf.retry.log > $X/$J/watchdog.log 2>&1 &)
wordpdf $X/$J/pools_changed $X/$J/pools_pdf
wordpdf $X/$J/en_changed $X/$J/en_pdf
pkill -f "[w]ord_watchdog.sh"
eval "$(sed -n '/^score(){/,/^}/p' /tmp/word_queue.sh)"
O=/tmp/rlwo_truth; rm -rf $O; mkdir -p $O
for p in word_based word_based_randomized word_redlines_superdoc; do ln -sf $WR/$p/pdf/*.pdf $O/; done
O3=/tmp/rlwo_en_truth; rm -rf $O3; mkdir -p $O3
for f in $G/500_extra_pdf_redlines/*.pdf; do s=$(basename $f .pdf); ln -sf $f $O3/${s}_redline.pdf; done
score A_redline-$J $O $X/$J/pools_pdf _jubarte-rust_redline.pdf
score en_A_redline-$J $O3 $X/$J/en_pdf .pdf
echo "=== $(date +%T) word_ab_ext $J done"
