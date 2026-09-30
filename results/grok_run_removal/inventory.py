"""Which grok_run docx/pdf bytes are not in corpus/, by top-level grok_run folder.

    uv run python results/grok_run_removal/inventory.py

Writes ``only_in_grok_run.csv`` (path, sha256, bytes, producer for PDFs) and ``by_folder.csv``
(folder, files, only_in_grok_run, of those Word-produced PDFs, bytes) next to this file.
"""

import csv
import hashlib
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
SUFFIXES = {'.docx', '.pdf'}


def files(top: Path) -> list[Path]:
    out = []
    for d, _, names in os.walk(top, followlinks=True):
        out += [Path(d) / n for n in names if Path(n).suffix.lower() in SUFFIXES and not n.startswith('~$')]
    return [p for p in out if p.exists()]  # dangling symlinks point at nothing to keep


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def producer(p: Path) -> str:
    if p.suffix.lower() != '.pdf':
        return ''
    head = p.read_bytes()[:4096] + p.read_bytes()[-8192:]
    for tag in (b'Microsoft', b'Quartz', b'LibreOffice', b'Skia', b'docxide', b'jubarte', b'Chromium'):
        if tag in head:
            return tag.decode()
    return 'other'


def main() -> None:
    corpus, grok = files(ROOT / 'corpus'), files(ROOT / 'grok_run')
    with ThreadPoolExecutor(16) as pool:
        have = set(pool.map(sha, corpus))
        gh = list(pool.map(sha, grok))
    by = defaultdict(lambda: [0, 0, 0, 0])
    with open(HERE / 'only_in_grok_run.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['path', 'sha256', 'bytes', 'pdf_producer'])
        for p, h in zip(grok, gh):
            rel = p.relative_to(ROOT / 'grok_run')
            row = by[rel.parts[0]]
            row[0] += 1
            if h in have:
                continue
            prod = producer(p)
            row[1] += 1
            row[2] += prod in ('Microsoft', 'Quartz')
            row[3] += p.stat().st_size
            w.writerow([rel, h, p.stat().st_size, prod])
    with open(HERE / 'by_folder.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['folder', 'files', 'only_in_grok_run', 'only_word_or_quartz_pdfs', 'only_bytes'])
        for k, v in sorted(by.items(), key=lambda kv: -kv[1][1]):
            w.writerow([k, *v])
    tot = [sum(v[i] for v in by.values()) for i in range(4)]
    print(f'corpus {len(corpus)} files, {len(have)} distinct; grok_run {tot[0]} files, '
          f'{tot[1]} not in corpus ({tot[3] / 1e9:.2f} GB), {tot[2]} of them Word/Quartz PDFs')


if __name__ == '__main__':
    main()
