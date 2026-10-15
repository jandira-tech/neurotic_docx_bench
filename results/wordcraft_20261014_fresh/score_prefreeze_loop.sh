#!/bin/zsh
# Score conversion (then comparison) candidates as their fresh Word oracles land, before the freeze.
cd /Users/arthrod/temp/T/neurotic_docx_bench
R=results/wordcraft_20261014_fresh
typeset -A scored
for kind in convert compare; do
  if [[ $kind == convert ]]; then tools=(wordcraft jubarte-0.11.0 jubarte-0.12.0 soffice); else tools=(wordcraft jubarte-0.11.0 jubarte-0.12.0 docxodus-12.6.5); fi
  for i in 01 02 03 04 05; do
    until [[ -f $R/word_400/${kind}_$i/driver.done ]]; do sleep 30; done
    if [[ $kind == compare ]]; then
      # compare candidates need the vendor redline rendered by Word first; that happens after the freeze
      continue
    fi
    for t in $tools; do
      until [[ -f $R/convert/$t/generate_failures.json ]]; do sleep 30; done
      echo "$(date +%T) score $kind $t after chunk $i"
      PREFREEZE=1 SCORE_WORKERS=3 .venv/bin/python $R/score_run.py $kind $t 2>&1 | grep -vE "Warning|swigvarlink" | tail -2
    done
  done
done
