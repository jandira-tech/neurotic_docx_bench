#!/bin/zsh
# Build the speed page and publish it to gh-pages of jandira-tech/neurotic_docx_bench as /speed/,
# with the summaries and the builder in _build/speed/.
cd ~/temp/T/docxide_compare || exit 1
python3 build_speed_site.py || exit 1
rm -rf ~/temp/T/ndb-gh-pages/speed
cp -R speed_site ~/temp/T/ndb-gh-pages/speed
mkdir -p ~/temp/T/ndb-gh-pages/_build/speed
cp build_speed_site.py publish_speed.sh ~/temp/T/ndb-gh-pages/_build/speed/
for part in redlines pdf; do
  [ -f ~/temp/T/neurotic_docx_bench/results/speed_10k/$part/SUMMARY.md ] && \
    cp ~/temp/T/neurotic_docx_bench/results/speed_10k/$part/SUMMARY.md ~/temp/T/ndb-gh-pages/_build/speed/SUMMARY_$part.md
done
# One link from the DOCX->PDF page and one from the redlines page, added once.
grep -q 'href="speed/"' ~/temp/T/ndb-gh-pages/index.html || \
  sed -i '' 's|<span><b><a href="redlines/">|<span><b><a href="speed/">Speed on 10,000 inputs \&rarr;</a></b></span> <span><b><a href="redlines/">|' \
    ~/temp/T/ndb-gh-pages/index.html
cd ~/temp/T/ndb-gh-pages || exit 1
git add speed _build/speed index.html
git commit -q -m "Speed: ${1:-update}

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01BVmF9Siv5ZuQPMBmvC9vGo" || { echo "nothing to commit"; exit 0; }
git push -q origin gh-pages && echo "published: $(git log --oneline -1)"
