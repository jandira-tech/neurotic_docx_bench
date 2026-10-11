"""Split the large paired ink moves between two lanes by whether the fonts moved.

    uv run python results/redlines_0929_full/font_session_split.py jubarte-0.10.1 jubarte-0.11.2-full

Word caches the face it substitutes for a missing font by name for the rest of a
session, so a lane's PDF export can draw the same docx in another face than Word's
compare did (probe b6bcd5d86d_file_198 x file_199: Times New Roman in the 0.11.2 export,
Hiragino Mincho alone in a fresh session, as in Word's compare). For each compare whose
ink_jaccard moved by more than --min (default 0.10) this lists the embedded font
families (subset prefix dropped) of Word's compare and of both candidates, and counts:

- font-moved: the losing side's fonts differ from the reference while the winning side's
  match it (export-session noise until a fresh-session export says otherwise);
- same-fonts: both candidates embed the reference's fonts (a layout or content change).

Each row's PDFs are found the way ``measure.py`` scored them (the fresh oracle when the
lane's scores used one, the pair's first-key candidate) and checked against the sha256
the row recorded; a row whose PDFs moved since is counted ``unverified``, not read.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _measure():
    spec = importlib.util.spec_from_file_location('measure', HERE / 'measure.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scored_pdfs(tool: str, scores: dict, keys: set[str], measure=None) -> dict[str, tuple[Path, Path]]:
    """Each row's (oracle, candidate) PDF as ``measure.py`` resolved them for this lane,
    kept only when both still hash to what the row recorded."""
    m = measure or _measure()
    pool = list(csv.DictReader(open(HERE / 'pool_pairs.csv')))
    first = {(r['base'], r['next']): r['key'] for r in reversed(list(csv.DictReader(open(HERE / 'gen_pairs.csv'))))}
    fresh = scores.get('summary', {}).get('fresh_dir')
    oracle = m.oracles(pool, Path(fresh) if fresh else None)
    out = {}
    for r in pool:
        row = scores['rows'].get(r['key'])
        if row is None or r['key'] not in keys:
            continue
        orc = oracle[r['key']][0]
        cand = HERE / tool / 'pdf_by_word' / f'{first[r["base"], r["next"]]}_{tool}.pdf'
        if all(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == row.get(k)
               for p, k in ((orc, 'oracle_sha256'), (cand, 'candidate_sha256'))):
            out[r['key']] = (orc, cand)
    return out


def fonts(pdf: Path) -> frozenset[str]:
    out = subprocess.run(['pdffonts', str(pdf)], capture_output=True, text=True).stdout
    names = set()
    for line in out.splitlines()[2:]:
        name = line.split()[0] if line.split() else ''
        names.add(name.split('+', 1)[-1])
    return frozenset(names)


def main() -> None:
    tool_a, tool_b = sys.argv[1], sys.argv[2]
    floor = float(sys.argv[3]) if len(sys.argv) > 3 else 0.10
    scores_a = json.loads((HERE / f'scores_{tool_a}.json').read_text())
    scores_b = json.loads((HERE / f'scores_{tool_b}.json').read_text())
    rows_a, rows_b = scores_a['rows'], scores_b['rows']
    moved = {k for k in set(rows_a) & set(rows_b)
             if None not in (ja := rows_a[k].get('ink_jaccard'), jb := rows_b[k].get('ink_jaccard')) and abs(jb - ja) > floor}
    m = _measure()
    pdfs_a, pdfs_b = scored_pdfs(tool_a, scores_a, moved, m), scored_pdfs(tool_b, scores_b, moved, m)
    tally = {'loss font-moved': 0, 'loss same-fonts': 0, 'loss other': 0,
             'gain font-moved': 0, 'gain same-fonts': 0, 'gain other': 0, 'unverified': 0}
    for key in sorted(set(rows_a) & set(rows_b)):
        ja, jb = rows_a[key].get('ink_jaccard'), rows_b[key].get('ink_jaccard')
        if ja is None or jb is None or abs(jb - ja) <= floor:
            continue
        if key not in pdfs_a or key not in pdfs_b or pdfs_a[key][0] != pdfs_b[key][0]:
            tally['unverified'] += 1
            continue
        oracle = fonts(pdfs_a[key][0])
        fa, fb = fonts(pdfs_a[key][1]), fonts(pdfs_b[key][1])
        side = 'loss' if jb < ja else 'gain'
        loser, winner = (fb, fa) if side == 'loss' else (fa, fb)
        if loser != oracle and winner == oracle:
            kind = 'font-moved'
        elif fa == oracle and fb == oracle:
            kind = 'same-fonts'
        else:
            kind = 'other'
        tally[f'{side} {kind}'] += 1
        print(f'{side} {kind:10} {ja:.3f}->{jb:.3f} {key}')
    print(tally)


if __name__ == '__main__':
    main()
