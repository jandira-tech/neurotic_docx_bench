#!/bin/zsh
# Build the redlines section and publish it to gh-pages of jandira-tech/neurotic_docx_bench as
# /redlines/, with the bench scores and the scripts behind it in _build/redlines/.
# Refuses to publish when the section would push the whole site past 500 MiB.
cd ~/temp/T/docxide_compare || exit 1
uv run --with pillow --with huggingface_hub python build_redlines_site.py || exit 1

size=$(du -sk redlines_site | cut -f1)
rest=$(du -sk -I redlines ~/temp/T/ndb-gh-pages | cut -f1)
if [ $((size + rest)) -gt 512000 ]; then
  echo "refusing: site would be $(((size + rest) / 1024)) MiB (> 500)"; exit 1
fi

rm -rf ~/temp/T/ndb-gh-pages/redlines
cp -R redlines_site ~/temp/T/ndb-gh-pages/redlines
mkdir -p ~/temp/T/ndb-gh-pages/_build/redlines
RUN=~/temp/T/neurotic_docx_bench/results/${REDLINES_RUN:-redlines_0929_full}
OLD=~/temp/T/neurotic_docx_bench/results/redlines_0928
rm -f ~/temp/T/ndb-gh-pages/_build/redlines/*.json ~/temp/T/ndb-gh-pages/_build/redlines/*.csv ~/temp/T/ndb-gh-pages/_build/redlines/*.py
cp $RUN/scores_*.json $RUN/*.py $RUN/*.csv $OLD/select_accept.py $OLD/select_reject.py \
   build_redlines_site.py publish_redlines.sh \
   ~/temp/T/ndb-gh-pages/_build/redlines/
[ -f $RUN/measure_tracks.py ] && cp $OLD/measure.py ~/temp/T/ndb-gh-pages/_build/redlines/measure_0928.py

# One link from the DOCX->PDF page to the redlines section, added once.
grep -q 'href="redlines/"' ~/temp/T/ndb-gh-pages/index.html || \
  sed -i '' 's|<span><b>What this is</b>: every DOCX to PDF engine|<span><b><a href="redlines/">Redlines vs Microsoft Word (jubarte, docxodus, SuperDoc) \&rarr;</a></b></span> <span><b>What this is</b>: every DOCX to PDF engine|' \
    ~/temp/T/ndb-gh-pages/index.html

cd ~/temp/T/ndb-gh-pages || exit 1
git add redlines _build/redlines index.html
git commit -q -m "Redlines vs Word: ${1:-update}

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BVmF9Siv5ZuQPMBmvC9vGo" || { echo "nothing to commit"; exit 0; }
git push -q origin gh-pages && echo "published: $(git log --oneline -1)"
