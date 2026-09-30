"""Take grok_run/ out of the repository: delete what corpus/ already holds, move the rest out.

    uv run python results/grok_run_removal/remove.py [--apply]

A grok_run file whose sha256 is the sha256 of a file under corpus/ is deleted; a symlink left
pointing at nothing by that is deleted too. Every deletion is a row of ``deleted_duplicates.csv``
(path, kind, sha256, bytes, corpus path) next to this file. What is left, grok_run/ and
grok_run_attic/, is moved (a rename, same volume) to ``~/temp/T/grok_run_archive``. Without
``--apply`` it only writes the ledger of what it would delete and prints the totals.
"""

import argparse
import csv
import hashlib
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
GROK, ATTIC = ROOT / 'grok_run', ROOT / 'grok_run_attic'
ARCHIVE = Path.home() / 'temp/T/grok_run_archive'


def walk(top: Path) -> tuple[list[Path], list[Path]]:
    """Regular files and symlinks under top, symlinks not followed."""
    files, links = [], []
    for d, dirs, names in os.walk(top):
        for n in names + [x for x in dirs if (Path(d) / x).is_symlink()]:
            p = Path(d) / n
            (links if p.is_symlink() else files).append(p)
    return files, links


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    apply = ap.parse_args().apply
    corpus, _ = walk(ROOT / 'corpus')
    grok, links = walk(GROK)
    with ThreadPoolExecutor(16) as pool:
        have = dict(zip(pool.map(sha, corpus), corpus))
        shas = list(pool.map(sha, grok))
    rows, freed = [], 0
    for p, h in zip(grok, shas):
        if h in have:
            size = p.stat().st_size
            rows.append([p, 'file', h, size, have[h].relative_to(ROOT)])
            freed += size
    gone = {r[0].resolve() for r in rows}
    rows += [[p, 'symlink', '', 0, ''] for p in links if not p.exists() or p.resolve() in gone]
    if apply:
        for r in rows:
            r[0].unlink()
    for r in rows:
        r[0] = r[0].relative_to(ROOT)
    with open(HERE / 'deleted_duplicates.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['path', 'kind', 'sha256', 'bytes', 'corpus_path'])
        w.writerows(rows)
    n_files = sum(r[1] == 'file' for r in rows)
    print(f'{"deleted" if apply else "would delete"} {n_files} files ({freed / 1e9:.2f} GB) '
          f'and {len(rows) - n_files} dangling symlinks; {len(grok) - n_files} files remain')
    if not apply:
        return
    for d, dirs, names in os.walk(GROK, topdown=False):
        if not os.listdir(d):
            os.rmdir(d)
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    if GROK.exists():
        shutil.move(GROK, ARCHIVE / 'grok_run')
    if ATTIC.exists():
        shutil.move(ATTIC, ARCHIVE / 'grok_run_attic')
    print(f'moved the rest to {ARCHIVE}')


if __name__ == '__main__':
    main()
