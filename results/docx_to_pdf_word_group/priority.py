"""Priority fixtures: documents where the better of docxide / soffice lands in a higher
text-boundary band than jubarte, in the cells Arthur picked, delivered with all four metrics.

    uv run python results/docx_to_pdf_word_group/priority.py [OUT]

OUT defaults to ``~/temp/T/jubarte-redlines/_to_improve_docx_to_pdf_priority``.

Selection, from ``~/temp/T/docxide_compare/corpus_scores.json`` (jubarte 0.9.3, docxide 0.17.1,
soffice 26.8.0.3, each against Word's PDF, docxide-pdf ``page-metrics`` at 150 DPI): the files
where all three have a text boundary (2480), banded 0-25 / 25-50 / 50-75 / 75-100 for jubarte
("us") and for the higher of docxide and soffice ("them"). Kept: us 0-25 with them 50-75 (17)
or 75-100 (24), us 25-50 with them 50-75 (34) or 75-100 (37), us 50-75 with them 75-100 (87).

Each fixture is re-measured here with every metric ``page-metrics`` prints (``jaccard``,
``ssim``, ``text_boundary``, ``max_break_drift``); ``score_corpus.py`` kept the first three.
Pages are drawn with mutool at 150 DPI into a temporary folder that is deleted per document.

Writes into OUT: ``_original_docx/<key>.docx`` (corpus/word), ``_word_pdf/<key>.pdf`` (Word's
PDF), ``_winner_pdf/<key>__<engine>.pdf`` for each engine ahead of jubarte on text boundary
(by more than 0.5), ``docs.csv``, and ``scripts/`` (this file, ``build.py``, ``score_corpus.py``).
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
BENCH = HERE.parents[1]
CORPUS = BENCH / 'corpus' / 'word'
DC = Path.home() / 'temp/T/docxide_compare'
SCORES = DC / 'corpus_scores.json'
METRICS_BIN = DC / 'docxide-pdf/tools/target/release/page-metrics'
CANDIDATES = {
    'jubarte': BENCH / 'results/jubarte_0.9.3_docx_to_pdf_work/jubarte/candidate',
    'docxide': BENCH / 'results/docxide_0.17.1_work/candidate',
    'soffice': BENCH / 'results/soffice_26.8.0.3_work/candidate',
}
STORED = {'jubarte': 'jubarte', 'docxide': 'generated', 'soffice': 'libreoffice'}  # corpus_scores.json keys
METRICS = ['jaccard', 'ssim', 'text_boundary', 'max_break_drift']
BANDS = ['0-25', '25-50', '50-75', '75-100']
CELLS = {('0-25', '50-75'), ('0-25', '75-100'), ('25-50', '50-75'), ('25-50', '75-100'), ('50-75', '75-100')}
TIE = 0.5


def band(x: float) -> str:
    return BANDS[min(int(x // 25), 3)]


def select() -> list[dict]:
    out = []
    for r in json.loads(SCORES.read_text()):
        tb = {e: r['scores'].get(k, {}).get('text_boundary') for e, k in STORED.items()}
        if any(v is None for v in tb.values()):
            continue
        best = max(('docxide', 'soffice'), key=lambda e: tb[e])
        cell = (band(tb['jubarte']), band(tb[best]))
        if cell in CELLS:
            out.append({'key': r['stem'], 'cell': cell, 'best': best, 'stored_tb': tb, 'pages': r['pages']})
    return out


def draw(pdf: Path, out: Path) -> None:
    out.mkdir(parents=True)
    subprocess.run(['mutool', 'draw', '-q', '-F', 'png', '-r', '150', '-o', str(out / 'page_%03d.png'), str(pdf)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


def measure(key: str) -> dict[str, dict]:
    """All four page-metrics values of each engine's PDF against Word's, 0-100 except drift."""
    state, stem = key.split('__', 1)
    ref = CORPUS / state / 'pdf' / f'{stem}.pdf'
    res = {}
    with tempfile.TemporaryDirectory(prefix='priority_') as tmp:
        tmp = Path(tmp)
        draw(ref, tmp / 'reference')
        for e, folder in CANDIDATES.items():
            pdf = folder / f'{key}.pdf'
            if not pdf.is_file():
                continue
            draw(pdf, tmp / e)
            r = subprocess.run([str(METRICS_BIN), str(ref), str(pdf), str(tmp / 'reference'), str(tmp / e)],
                               capture_output=True, text=True)
            try:
                m = json.loads(r.stdout)
            except ValueError:
                continue
            res[e] = {k: (None if m.get(k) is None else round(m[k] * 100, 1) if k != 'max_break_drift' else m[k])
                      for k in METRICS}
            shutil.rmtree(tmp / e)
    return res


def main(out: Path) -> None:
    fx = select()
    for d in ('_original_docx', '_word_pdf', '_winner_pdf', 'scripts'):
        (out / d).mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        measured = dict(zip((f['key'] for f in fx), pool.map(measure, (f['key'] for f in fx))))
    rows = []
    for f in fx:
        key = f['key']
        state, stem = key.split('__', 1)
        docx = CORPUS / state / 'docx' / f'{stem}.docx'
        shutil.copy2(docx, out / '_original_docx' / f'{key}.docx')
        shutil.copy2(CORPUS / state / 'pdf' / f'{stem}.pdf', out / '_word_pdf' / f'{key}.pdf')
        tb = f['stored_tb']
        ahead = [e for e in ('docxide', 'soffice') if tb[e] - tb['jubarte'] > TIE]
        for e in ahead:
            shutil.copy2(CANDIDATES[e] / f'{key}.pdf', out / '_winner_pdf' / f'{key}__{e}.pdf')
        m = measured[key]
        row = {'key': key, 'state': state, 'us_band': f['cell'][0], 'them_band': f['cell'][1],
               'best': f['best'], 'winner_pdfs': ' '.join(ahead),
               'tb_gap': round(tb[f['best']] - tb['jubarte'], 1),
               'word_pages': f['pages'].get('reference')}
        for e in CANDIDATES:
            row[f'{e}_pages'] = f['pages'].get(STORED[e])
            for k in METRICS:
                row[f'{e}_{k}'] = m.get(e, {}).get(k)
        row['source_docx'] = str(docx)
        row['source_sha256'] = hashlib.sha256(docx.read_bytes()).hexdigest()
        rows.append(row)
    order = {c: i for i, c in enumerate([('0-25', '75-100'), ('0-25', '50-75'), ('25-50', '75-100'),
                                         ('25-50', '50-75'), ('50-75', '75-100')])}
    rows.sort(key=lambda r: (order[(r['us_band'], r['them_band'])], -r['tb_gap']))
    with open(out / 'docs.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for s in (Path(__file__), HERE / 'build.py', DC / 'score_corpus.py'):
        shutil.copy2(s, out / 'scripts' / s.name)
    # the re-measured text boundary should match corpus_scores.json
    drift = [abs(r[f'{e}_text_boundary'] - f['stored_tb'][e]) for r, f in zip(rows, sorted(fx, key=lambda f: [x['key'] for x in rows].index(f['key'])))
             for e in CANDIDATES if r[f'{e}_text_boundary'] is not None]
    print(f'{len(rows)} fixtures -> {out}; re-measured text boundary vs stored: max |diff| {max(drift):.1f}, '
          f'{sum(d > 0.5 for d in drift)} of {len(drift)} differ by > 0.5')


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'temp/T/jubarte-redlines/_to_improve_docx_to_pdf_priority')
