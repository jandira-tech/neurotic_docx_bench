"""Stage a tool's redlines of the accept / reject selections for Word's accept-all / reject-all.

    uv run python results/redlines_0929_full/stage_tracks.py jubarte-093

For each row of ``accept_selection.csv`` / ``reject_selection.csv``, the tool's redline of the
row's pair (``gen_pairs.csv`` keys a pair by its first compare) is copied to
``<tool>/{accepted,rejected}/src/<compare id>.docx``. A pair the tool has no redline for is
listed and skipped.
"""

import csv
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent


def main(tool: str) -> None:
    gen = {(r['base'], r['next']): r['key'] for r in csv.DictReader(open(HERE / 'gen_pairs.csv'))}
    for track, sel in (('accepted', 'accept_selection.csv'), ('rejected', 'reject_selection.csv')):
        dst = HERE / tool / track / 'src'
        dst.mkdir(parents=True, exist_ok=True)
        staged, missing = 0, []
        for r in csv.DictReader(open(HERE / sel)):
            src = HERE / tool / 'docx' / f"{gen[(r['base'], r['next'])]}_{tool}.docx"
            if src.is_file():
                shutil.copy2(src, dst / f"{r['id']}.docx")
                staged += 1
            else:
                missing.append(r['id'])
        print(f'{tool} {track}: staged {staged}, missing {len(missing)} {missing[:10]}')


if __name__ == '__main__':
    main(sys.argv[1])
