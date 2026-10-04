#!/bin/bash
# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# Word truth = Word's own redline (word_redline.py), converted by Word (word_pdf.py).
# Rows, same pairs, all scored against that truth:
#   A redline=jubarte  pdf=Word     -> redlining alone
#   B redline=Word     pdf=jubarte  -> conversion alone
#   C redline=Word     pdf=soffice  -> conversion baseline
#   D redline=jubarte  pdf=jubarte  -> end to end
#   E redline=jubarte  pdf=soffice  -> end to end, the harness's own soffice PDFs (harness pools only)
# No Word truth PDF (Word failed twice): pair skipped. Truth exists but the row has no PDF: scored 0.
set -u
T=cb33ec3; N=/Users/arthrod/temp/T/neurotic_docx_bench; G=$N/grok_run; WR=$G/wr0926; L=/Users/arthrod/temp/T/jubarte-loop
BIN=$L/bin/jubarte-$T; OUT=$N/results/redline_wordpdf; mkdir -p $OUT
SC=$N/src/neurotic_docx_bench/utils/docxide-metrics/target/release/docxide-metrics
RUN=runs/jubarte-rust_2026-09-26_14-41
cd $N
until grep -q "all done" /tmp/word_redlines.log; do sleep 30; done
echo "=== $(date +%T) Word redlines done; converting"

wordpdf(){ mkdir -p $2; uv run --script scripts/word_pdf.py --src $1 --out $2 --no-check-preset -q --log $2.log > /dev/null 2>&1; echo "=== $(date +%T) word_pdf $1 -> $(ls $2 | wc -l) pdf"; }
conv(){ python3 $L/en_conv.py $1 $2 $3 ${4:-8} $BIN > /dev/null 2>&1; echo "=== $(date +%T) $1 $2 -> $(ls $3 | wc -l) pdf"; }

# Harness pools: one folder of Word's redline docx across the three pools.
WD=$WR/word_docx_all; rm -rf $WD; mkdir -p $WD
for p in word_based word_based_randomized word_redlines_superdoc; do ln -sf $WR/$p/docx/*.docx $WD/; done
wordpdf $N/$RUN/docx $WR/A_jubredline_wordpdf
conv jubarte $WD $WR/B_wordredline_jubpdf 10
conv soffice $WD $WR/C_wordredline_soffice 6
conv jubarte $N/$RUN/docx $WR/D_jubredline_jubpdf 10
# English: Word's redlines are 500_extra_docx_redlines; jubarte's are en_jubarte_redlines_$T.
wordpdf $G/en_jubarte_redlines_$T $G/en_A_jubredline_wordpdf_$T
conv jubarte $G/500_extra_docx_redlines $G/en_B_wordredline_jubpdf_$T 10
conv soffice $G/500_extra_docx_redlines $G/en_C_wordredline_soffice_$T 6
conv jubarte $G/en_jubarte_redlines_$T $G/en_D_jubredline_jubpdf_$T 10

score(){ # NAME TRUTH_DIR(<stem>_redline.pdf) CAND_DIR CAND_SUFFIX (candidate file = <stem><suffix>)
  local name=$1 orc=$2 src=$3 suf=$4 cand=/tmp/rlw_cand_$1
  rm -rf $cand; mkdir -p $cand
  python3 - $orc $src $suf $cand $OUT/${name}_jobs.json $OUT/${name}_missing.json <<'PY'
import json, pathlib, sys
orc, src = map(pathlib.Path, sys.argv[1:3]); suf = sys.argv[3]
cand, jobs, missing = map(pathlib.Path, sys.argv[4:7]); out = []; miss = []
for o in sorted(orc.glob('*_redline.pdf')):
    stem = o.name.removesuffix('_redline.pdf')
    c = src / f'{stem}{suf}'
    if not c.exists():
        miss.append(stem)
        continue
    (cand / f'{stem}_jubarte-rust_redline.pdf').symlink_to(c.resolve())
    out.append({'stem': stem, 'oracle': str(o.resolve()), 'candidate': str(c.resolve())})
jobs.write_text(json.dumps(out)); missing.write_text(json.dumps(miss))
PY
  uv run -q bench compare $cand $orc --tool jubarte-rust --json $OUT/${name}_harness.json > /dev/null 2>&1
  $SC --jobs $OUT/${name}_jobs.json --scratch /tmp/rlw_raster --out $OUT/${name}_docxide.json --workers 12 > /dev/null 2>&1; rm -rf /tmp/rlw_raster $cand
  python3 - $OUT/${name}_harness.json $OUT/${name}_docxide.json $OUT/${name}_missing.json $name <<'PY'
import json, statistics as st, sys
h, d, m, name = sys.argv[1:5]; miss = json.load(open(m))
hs = json.load(open(h)); hs.update({s: 0.0 for s in miss}); json.dump(hs, open(h, 'w'), indent=2, sort_keys=True)
ds = json.load(open(d)); ds += [{'stem': s, 'jaccard': 0.0} for s in miss]; json.dump(ds, open(d, 'w'))
hv = list(hs.values()); j = [r.get('jaccard') or 0.0 for r in ds]
print(f'{name}: harness n={len(hv)} mean={st.mean(hv):.2f} median={st.median(hv):.2f} | docxide-metrics mean={st.mean(j):.4f} median={st.median(j):.4f} | zeros {len(miss)}')
PY
}
# Truth: fresh Word redlines, Word PDFs.
O=/tmp/rlw_truth; rm -rf $O; mkdir -p $O
for p in word_based word_based_randomized word_redlines_superdoc; do ln -sf $WR/$p/pdf/*.pdf $O/; done
score A_redline-$T  $O $WR/A_jubredline_wordpdf _jubarte-rust_redline.pdf
score B_convert-$T  $O $WR/B_wordredline_jubpdf _redline.pdf
score C_soffice-$T  $O $WR/C_wordredline_soffice _redline.pdf
score D_e2e-$T      $O $WR/D_jubredline_jubpdf _jubarte-rust_redline.pdf
score E_e2e_soffice-$T $O $N/$RUN/pdf _jubarte-rust_redline.pdf
# English truth: 500_extra_pdf_redlines/<a>__vs__<b>.pdf, exposed as <stem>_redline.pdf.
O3=/tmp/rlw_en_truth; rm -rf $O3; mkdir -p $O3
for f in $G/500_extra_pdf_redlines/*.pdf; do s=$(basename $f .pdf); ln -sf $f $O3/${s}_redline.pdf; done
score en_A_redline-$T $O3 $G/en_A_jubredline_wordpdf_$T .pdf
score en_B_convert-$T $O3 $G/en_B_wordredline_jubpdf_$T .pdf
score en_C_soffice-$T $O3 $G/en_C_wordredline_soffice_$T .pdf
score en_D_e2e-$T     $O3 $G/en_D_jubredline_jubpdf_$T .pdf
rm -rf $O $O3
echo "=== $(date +%T) done"
