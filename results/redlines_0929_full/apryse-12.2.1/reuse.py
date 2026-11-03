"""Reuse the Apryse 12.2.1 redlines and Word PDFs the 0929 run already made (#129).

    uv run python results/redlines_0929_full/apryse-12.2.1/reuse.py

The 0929 Apryse lane (apryse-sdk 12.2.1, the demo key) already redlined 2599 pairs and
Word exported 1816 of them. The fixed set ``redline_600`` draws 600 pairs; for every one of
them that lane already holds a redline **and** Word's PDF of it, the bytes are the ones
this lane would produce (same engine, same version, same Word) — so they are copied in and
only the pairs the old lane never exported are generated and exported again.

What is copied:

- the redline ``<key>_apryse.docx`` → ``<key>_apryse-12.2.1.docx`` (same bytes, the
  lane's own tool name);
- Word's PDF of it → ``<trimmed stem>_byword.pdf``, the name ``word_pdf.py`` gives the PDF
  of that redline (file names over 80 characters are trimmed on disk, and the trim is a
  function of the name, so the name is computed here with the driver's own ``trim_name``).

The pairs with no PDF are listed in ``missing_pairs.csv`` (the manifest the generator
runs on). ``word_pdf.py`` then skips every pair whose PDF is already there and exports
the rest, so the lane's ``pdf_by_word/manifest.jsonl`` records who was skipped and who
was exported.
"""

from __future__ import annotations

import csv
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'src'))

from neurotic_docx_bench.word_outputs import find_output  # noqa: E402

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location('word_pdf', REPO / 'scripts' / 'word_pdf.py')
word_pdf = importlib.util.module_from_spec(_spec)
sys.modules['word_pdf'] = word_pdf  # dataclasses look their module up in sys.modules
_spec.loader.exec_module(word_pdf)

TOOL = 'apryse-12.2.1'
OLD_TOOL = 'apryse'
ARTHUR = Path.home() / 'temp/T/neurotic_docx_bench/results/redlines_0929_full/apryse'
PAIRS = HERE.parent / 'set-redline_600_pairs.csv'
MISSING = HERE / 'missing_pairs.csv'


def main() -> None:
    docx_dir = HERE / 'docx'
    pdf_dir = HERE / 'pdf_by_word'
    docx_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(PAIRS)))
    reused = missing = 0
    missing_rows = []
    for r in rows:
        key = r['key']
        old_docx = ARTHUR / 'docx' / f'{key}_{OLD_TOOL}.docx'
        old_pdf = find_output(ARTHUR / 'pdf_by_word', f'{key}_{OLD_TOOL}.docx', kind='pdf', ext='.pdf')
        if not old_docx.is_file() or old_pdf is None or not Path(old_pdf).is_file():
            missing_rows.append(r)
            missing += 1
            continue
        new_docx = docx_dir / f'{key}_{TOOL}.docx'
        shutil.copy2(old_docx, new_docx)
        trimmed = word_pdf.trim_name(new_docx.name)
        shutil.copy2(old_pdf, pdf_dir / f'{Path(trimmed).stem}_byword.pdf')
        reused += 1
    with MISSING.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator='\n')
        w.writeheader()
        w.writerows(missing_rows)
    print(f'{reused} pair(s) reused from the 0929 Apryse lane; {missing} to generate '
          f'({MISSING.name})')


if __name__ == '__main__':
    main()
