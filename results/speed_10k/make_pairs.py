"""Build the 10,000-pair variation list for the redline speed run (seed 20260929).

    uv run python results/speed_10k/make_pairs.py        # writes results/speed_10k/pairs_10k.csv

Every path is a corpus/word document (2,600 documents, 2,739 Word compares). Categories:

- ``word_compare``: every base -> next pair Word compared for the corpus (real edits).
- ``reverse``: 1,000 of those pairs the other way round (next -> base).
- ``identity``: 300 documents against themselves (nothing changed).
- ``grid``: the rest, drawn evenly over a 4 x 4 grid of base size quartile x next size
  quartile, each cell split evenly across the input kinds (clean, tracked, with comments,
  with comments and tracked) of the base, so small-to-large, large-to-small, and inputs
  that already carry tracked changes or comments are all covered.

Columns: key, base, next, category, base_bytes, next_bytes, base_state, next_state.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CORPUS = Path('corpus/word')
SEED = 20260929
TOTAL = 10_000
REVERSE = 1_000
IDENTITY = 300


def main() -> None:
    rng = random.Random(SEED)
    docs = {r['id']: r for r in csv.DictReader(open(CORPUS / 'documents.csv'))}
    for d in docs.values():
        d['bytes'] = (CORPUS / d['docx']).stat().st_size
    sizes = sorted(d['bytes'] for d in docs.values())
    cuts = [sizes[len(sizes) * q // 4] for q in (1, 2, 3)]

    def quartile(d: dict) -> int:
        return sum(d['bytes'] >= c for c in cuts)

    rows: list[tuple[str, dict, dict]] = []
    compares = [r for r in csv.DictReader(open(CORPUS / 'comparisons.csv'))]
    real = [
        (docs[c['base_id']], docs[c['next_id']]) for c in compares if c['base_id'] in docs and c['next_id'] in docs
    ]
    rows += [('word_compare', b, n) for b, n in real]
    rows += [('reverse', n, b) for b, n in rng.sample(real, min(REVERSE, len(real)))]
    rows += [('identity', d, d) for d in rng.sample(sorted(docs.values(), key=lambda d: d['id']), IDENTITY)]

    cells: dict[tuple[int, str], list[dict]] = defaultdict(list)
    by_q: dict[int, list[dict]] = defaultdict(list)
    for d in sorted(docs.values(), key=lambda d: d['id']):
        cells[quartile(d), d['state']].append(d)
        by_q[quartile(d)].append(d)
    states = sorted({d['state'] for d in docs.values()})
    left = TOTAL - len(rows)
    grid = [(qb, qn, st) for qb in range(4) for qn in range(4) for st in states if cells[qb, st]]
    seen = {(b['id'], n['id']) for _, b, n in rows}
    i = 0
    while left > 0:
        qb, qn, st = grid[i % len(grid)]
        i += 1
        b = rng.choice(cells[qb, st])
        n = rng.choice(by_q[qn])
        if b['id'] == n['id'] or (b['id'], n['id']) in seen:
            continue
        seen.add((b['id'], n['id']))
        rows.append(('grid', b, n))
        left -= 1

    out = HERE / 'pairs_10k.csv'
    with out.open('w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'base', 'next', 'category', 'base_bytes', 'next_bytes', 'base_state', 'next_state'])
        for k, (cat, b, n) in enumerate(rows):
            w.writerow([
                f'p{k:05d}_{cat}',
                CORPUS / b['docx'],
                CORPUS / n['docx'],
                cat,
                b['bytes'],
                n['bytes'],
                b['state'],
                n['state'],
            ])
    counts: dict[str, int] = defaultdict(int)
    for cat, _, _ in rows:
        counts[cat] += 1
    print(f'{len(rows)} pairs -> {out}: {dict(counts)}; size quartile cuts {cuts} bytes')


if __name__ == '__main__':
    main()
