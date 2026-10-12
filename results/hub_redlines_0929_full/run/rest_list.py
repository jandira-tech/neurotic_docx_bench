"""Symlink the redlines a Word export still owes into ``<tool>/docx_rest`` for a relaunch.

    uv run python results/redlines_0929_full/rest_list.py docxodus     # prints: linked owed
    uv run python results/redlines_0929_full/rest_list.py docxodus 15  # link at most 15

A small batch keeps a Word hang or crash from poisoning the opens after it for long: a
redline Word loaded empty in a long batch converted alone in 3 of 5 tries (2026-09-30).

A redline is owed when ``<tool>/docx/<stem>.docx`` has no ``<tool>/pdf_by_word/<stem>.pdf`` and no
``[batch] FAIL: <stem>.docx`` line in any ``<tool>.word_pdf*.log`` (word_pdf already gave it its
passes); a FAIL that says ``never reached`` is still owed, since Word never tried it. Word opens the batch in name order, and a document that hangs Word (an AppleEvent
timeout) ends the pass, so the untried redlines sharing a base id (the first 10 hex characters)
with a timed-out one are held back until nothing else is left: they cannot stall the rest.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
FAIL = re.compile(r'\[batch\] FAIL: (\S+)\.docx — (.*)$')


def owed(tool: str) -> tuple[list[Path], list[Path]]:
    """(ready, held back) docx paths still without a PDF and never failed."""
    failed: dict[str, str] = {}
    for log in sorted(HERE.glob(f'{tool}.word_pdf*.log')):
        for line in log.read_text(errors='replace').splitlines():
            # "never reached" is a pass budget running out, not Word failing on the file: still owed
            if (m := FAIL.search(line)) and not m[2].startswith('never reached'):
                failed[m[1]] = m[2]
    hung = {stem[:10] for stem, why in failed.items() if 'timed out' in why}
    done = {p.stem for p in (HERE / tool / 'pdf_by_word').glob('*.pdf')}
    todo = [p for p in sorted((HERE / tool / 'docx').glob('*.docx')) if p.stem not in done and p.stem not in failed]
    return [p for p in todo if p.stem[:10] not in hung], [p for p in todo if p.stem[:10] in hung]


def main() -> None:
    tool = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    ready, held = owed(tool)
    batch = (ready or held)[:limit or None]
    rest = HERE / tool / 'docx_rest'
    if rest.exists():
        shutil.rmtree(rest)  # symlinks only
    rest.mkdir()
    for p in batch:
        (rest / p.name).symlink_to(p.resolve())
    print(len(batch), len(ready) + len(held))  # linked now, owed in all
    print(f'{tool}: {len(ready)} ready, {len(held)} held back (base hung Word); linked {len(batch)}', file=sys.stderr)


if __name__ == '__main__':
    main()
