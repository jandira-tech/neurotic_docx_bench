"""Build the 0929 script-redlines corpus: every Word compare PDF whose two originals exist.

    uv run python results/redlines_0929_full/prepare.py

Reads ``corpus/word/comparisons.csv`` and ``corpus/word/documents.csv`` and writes, next to
this file:

- ``pool_pairs.csv``: one row per Word compare (``key`` = its corpus stem) whose PDF and
  both original DOCX files exist. This is the scoring corpus.
- ``gen_pairs.csv``: one row per distinct (base, next) pair, keyed by the first compare of
  that pair (sorted by compare id). Tools redline each pair once; the same pair compared by
  Word more than once is scored against every one of Word's compares.
- ``oracle_pdf/<key>.pdf``: links to Word's compare PDFs.
"""

from __future__ import annotations

import csv
from pathlib import Path

import polars as pl

HERE = Path(__file__).parent
CORPUS = Path('corpus/word')
FIELDS = ['key', 'base', 'next', 'docx', 'pdf', 'state', 'id', 'sets']


def exists(rel: str | None) -> bool:
    return bool(rel) and (CORPUS / rel).is_file()


def main() -> None:
    cmp = pl.read_csv(CORPUS / 'comparisons.csv', infer_schema_length=0)
    docs = pl.read_csv(CORPUS / 'documents.csv', infer_schema_length=0)
    src = {r['id']: r['docx'].removesuffix('.docx') for r in docs.iter_rows(named=True) if exists(r['docx'])}
    rows = []
    for r in cmp.sort('id').iter_rows(named=True):
        if not exists(r['pdf']) or r['base_id'] not in src or r['next_id'] not in src:
            print('skip', r['id'], 'pdf' if not exists(r['pdf']) else 'original')
            continue
        rows.append({'key': r['key'], 'base': src[r['base_id']], 'next': src[r['next_id']], 'docx': r['docx'],
                     'pdf': r['pdf'], 'state': r['state'], 'id': r['id'], 'sets': r['sets']})
    gen, seen = [], set()
    for r in rows:
        if (r['base'], r['next']) not in seen:
            seen.add((r['base'], r['next']))
            gen.append(r)
    for name, data in (('pool_pairs.csv', rows), ('gen_pairs.csv', gen)):
        with open(HERE / name, 'w', newline='') as f:
            w = csv.DictWriter(f, FIELDS)
            w.writeheader()
            w.writerows(data)
    oracle = HERE / 'oracle_pdf'
    oracle.mkdir(exist_ok=True)
    for r in rows:
        link = oracle / f'{r["key"]}.pdf'
        if not link.is_symlink():
            link.symlink_to((CORPUS / r['pdf']).resolve())
    print(f'{len(rows)} Word compares, {len(gen)} distinct pairs -> {HERE}')


if __name__ == '__main__':
    main()
