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
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


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
    rows_a = json.loads((HERE / f'scores_{tool_a}.json').read_text())['rows']
    rows_b = json.loads((HERE / f'scores_{tool_b}.json').read_text())['rows']
    tally = {'loss font-moved': 0, 'loss same-fonts': 0, 'loss other': 0,
             'gain font-moved': 0, 'gain same-fonts': 0, 'gain other': 0}
    for key in sorted(set(rows_a) & set(rows_b)):
        ja, jb = rows_a[key].get('ink_jaccard'), rows_b[key].get('ink_jaccard')
        if ja is None or jb is None or abs(jb - ja) <= floor:
            continue
        oracle = fonts(HERE / 'oracle_pdf' / f'{key}.pdf')
        fa = fonts(HERE / tool_a / 'pdf_by_word' / f'{key}_{tool_a}.pdf')
        fb = fonts(HERE / tool_b / 'pdf_by_word' / f'{key}_{tool_b}.pdf')
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
