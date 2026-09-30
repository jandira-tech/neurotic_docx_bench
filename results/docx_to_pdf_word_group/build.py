"""Word's DOCX->PDF group and where docxide / soffice score above jubarte on it.

    uv run python results/docx_to_pdf_word_group/build.py

- ``group.csv``: every docx under ``corpus/word/<state>/docx`` with Word's PDF beside it
  (``<state>/pdf/<stem>.pdf``), and which engines ``corpus_scores.json`` scored on it.
- ``ahead_of_jubarte.csv``: one row per document and metric where docxide 0.17.1 or soffice
  26.8.0.3 scores more than 0.5 above jubarte 0.9.3 (both against Word's PDF, docxide-pdf
  page-metrics at 150 DPI, ``~/temp/T/docxide_compare/score_corpus.py``).
"""

import csv
import json
from pathlib import Path

HERE = Path(__file__).parent
CORPUS = HERE.parents[1] / 'corpus' / 'word'
SCORES = Path.home() / 'temp/T/docxide_compare/corpus_scores.json'
ENGINES = {'jubarte': 'jubarte 0.9.3', 'generated': 'docxide 0.17.1', 'libreoffice': 'soffice 26.8.0.3'}
TIE = 0.5


def main() -> None:
    scored = {r['stem']: r for r in json.loads(SCORES.read_text())}
    with open(HERE / 'group.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['stem', 'state', 'docx', 'pdf', *ENGINES.values()])
        for state in sorted(p for p in CORPUS.iterdir() if (p / 'docx').is_dir()):
            for d in sorted((state / 'docx').glob('*.docx')):
                pdf = state / 'pdf' / f'{d.stem}.pdf'
                if d.name.startswith('~$') or not pdf.is_file():
                    continue
                r = scored.get(f'{state.name}__{d.stem}', {'scores': {}})
                w.writerow([d.stem, state.name, d.relative_to(CORPUS), pdf.relative_to(CORPUS),
                            *(int(r['scores'].get(e, {}).get('jaccard') is not None) for e in ENGINES)])
    with open(HERE / 'ahead_of_jubarte.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['stem', 'metric', 'engine', 'engine_score', 'jubarte_score', 'margin',
                    'word_pages', 'jubarte_pages', 'engine_pages'])
        for stem, r in sorted(scored.items()):
            s, p = r['scores'], r['pages']
            for m in ('jaccard', 'ssim', 'text_boundary'):
                j = s.get('jubarte', {}).get(m)
                for e in ('generated', 'libreoffice'):
                    o = s.get(e, {}).get(m)
                    if j is not None and o is not None and o - j > TIE:
                        w.writerow([stem, m, ENGINES[e], o, j, round(o - j, 1),
                                    p.get('reference'), p.get('jubarte'), p.get(e)])


if __name__ == '__main__':
    main()
