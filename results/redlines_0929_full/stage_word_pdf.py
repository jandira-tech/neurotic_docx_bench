"""Hard-link the PDFs a running ``scripts/word_pdf.py`` export has made into one folder.

    uv run python results/redlines_0929_full/stage_word_pdf.py docxodus

word_pdf delivers its PDFs only when the whole run ends; until then they sit in Word's
container, ``wordpdf.*/out/<NNNNN>__<stem>.pdf``. A staged PDF is taken only when its item
logged ``[ok]`` in that pass's ``batch-pdf-<N>.log`` (the id resolved through the same pass's
``batch-pdf-<N>.tsv``), so a file Word was still writing, or one a timeout cut short, is never
read, and only when ``<tool>/docx/<stem>.docx`` exists. The delivered ``<tool>/pdf_by_word``
PDFs are linked too, so ``<tool>/pdf_staged`` holds every PDF made so far and
``measure.py --cand-dir <tool>/pdf_staged`` scores all of them. Links are hard links (same
volume), so they outlive word_pdf removing its staged copies. Existing links are kept.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

HERE = Path(__file__).parent
STAGING = Path.home() / 'Library/Containers/com.microsoft.Word/Data/tmp'


def staged_ok(root: Path) -> list[Path]:
    """The ``out`` PDFs of every ``[ok]`` item under one ``wordpdf.*`` staging folder."""
    found = []
    for log in sorted(root.glob('batch-pdf-*.log')):
        tsv = log.with_suffix('.tsv')
        if not tsv.is_file():
            continue
        ok = {line.split('\t')[1].strip() for line in log.read_text(errors='replace').splitlines()
              if line.startswith('[ok]\t')}
        for line in tsv.read_text(errors='replace').splitlines():
            fields = line.split('\t')
            if len(fields) >= 3 and fields[0] in ok:
                found.append(Path(fields[2]))
    return found


def stage(tool: str, staging: Path = STAGING) -> tuple[int, int]:
    dst = HERE / tool / 'pdf_staged'
    dst.mkdir(exist_ok=True)
    docx = HERE / tool / 'docx'
    added = 0
    sources = sorted((HERE / tool / 'pdf_by_word').glob('*.pdf'))
    for root in sorted(staging.glob('wordpdf.*')):
        sources += staged_ok(root)
    for src in sources:
        name = re.sub(r'^\d{5}__', '', src.name)
        target = dst / name
        if (target.exists() or not name.endswith(f'_{tool}.pdf') or not src.is_file()
                or src.stat().st_size == 0 or not (docx / f'{Path(name).stem}.docx').is_file()):
            continue
        os.link(src, target)
        added += 1
    return added, sum(1 for _ in dst.glob('*.pdf'))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tool')
    ap.add_argument('--staging', type=Path, default=STAGING, help='folder holding the wordpdf.* staging folders')
    a = ap.parse_args()
    added, total = stage(a.tool, a.staging)
    print(f'{a.tool}: linked {added} new PDF(s); {total} in {a.tool}/pdf_staged', flush=True)


if __name__ == '__main__':
    main()
