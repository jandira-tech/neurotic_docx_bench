"""Pick 10,000 varied DOCX files for the docx -> PDF speed run (seed 20260929).

    uv run python results/speed_10k/make_pdf_docs.py   # writes pdf_docs_10k.txt and pdf_docs_10k.csv

Candidates: every .docx under corpus/, grok_run/ (symlinks followed) and the 0928 tool
redlines (results/redlines_0928/<tool>/docx), one per distinct content (sha256), skipping
Word lock files, folders named *invalid*, *_discarded*, *attic*, and anything that is not
a zip. Each file gets a family (corpus/word, other corpus sets, the grok_run top folder,
or the redline tool) and a size quartile; the 10,000 are drawn round-robin over
family x quartile strata, so small families are taken whole and large ones sampled.

pdf_docs_10k.txt lists the paths (the --corpus NAME=@LIST input of
scripts/docx_to_pdf_speed.py); pdf_docs_10k.csv adds family, quartile, bytes and sha256.
"""

from __future__ import annotations

import csv
import hashlib
import os
import random
import zipfile
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
SEED = 20260929
TOTAL = 10_000
ROOTS = [
    Path('corpus'),
    Path('grok_run'),
    *(Path(f'results/redlines_0928/{t}/docx') for t in ('jubarte-rust', 'docxodus', 'superdoc')),
]
SKIP = ('invalid', '_discarded', 'attic')


def family(p: Path) -> str:
    parts = p.parts
    if parts[0] == 'results':
        return f'redline:{parts[2]}'
    if parts[0] == 'corpus':
        return 'corpus/word' if parts[1] == 'word' else 'corpus/other'
    return f'grok_run/{parts[1]}'


def candidates() -> list[Path]:
    out = []
    for root in ROOTS:
        for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
            dirnames[:] = sorted(d for d in dirnames if not any(s in d for s in SKIP))
            out += [Path(dirpath) / f for f in sorted(filenames) if f.endswith('.docx') and not f.startswith('~$')]
    return out


def main() -> None:
    rng = random.Random(SEED)
    seen: set[str] = set()
    rows = []
    for p in candidates():
        if not p.is_file() or not zipfile.is_zipfile(p):
            continue
        with p.open('rb') as fh:
            sha = hashlib.file_digest(fh, 'sha256').hexdigest()
        if sha in seen:
            continue
        seen.add(sha)
        rows.append({'path': str(p), 'family': family(p), 'bytes': p.stat().st_size, 'sha256': sha})
    sizes = sorted(r['bytes'] for r in rows)
    cuts = [sizes[len(sizes) * q // 4] for q in (1, 2, 3)]
    strata: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for r in rows:
        r['quartile'] = sum(r['bytes'] >= c for c in cuts)
        strata[r['family'], r['quartile']].append(r)
    for bucket in strata.values():
        rng.shuffle(bucket)
    keys = sorted(strata)
    chosen: list[dict] = []
    while len(chosen) < min(TOTAL, len(rows)):
        for k in keys:
            if strata[k] and len(chosen) < TOTAL:
                chosen.append(strata[k].pop())
    (HERE / 'pdf_docs_10k.txt').write_text(''.join(r['path'] + '\n' for r in chosen))
    with (HERE / 'pdf_docs_10k.csv').open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['path', 'family', 'quartile', 'bytes', 'sha256'], extrasaction='ignore')
        w.writeheader()
        w.writerows(chosen)
    fams: dict[str, int] = defaultdict(int)
    for r in chosen:
        fams[r['family']] += 1
    print(f'{len(rows)} distinct docx; chose {len(chosen)}; size cuts {cuts}')
    for f, n in sorted(fams.items(), key=lambda x: -x[1]):
        print(f'  {n:5d} {f}')


if __name__ == '__main__':
    main()
