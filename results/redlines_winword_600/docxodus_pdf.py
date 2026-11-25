"""The PDF conversion test: docxodus draws Word's own redline of each redline_600 pair.

    .venv/bin/python results/redline600_contabo/docxodus_pdf.py --binary <export>/node_modules/.bin/docxodus [--follow]

Input: ``word/docx/<key>.docx``, the redline Contabo's Word made (``contabo_word.py compare``).
Output: ``docxodus-16.1.0-pdf/pdf/<key>.pdf``. Its reference is ``word/pdf/<key>.pdf``, Word's PDF
of the same file, so the converter is the only thing that differs.

The command is the bench's own docxodus DOCX->PDF command,
``neurotic_docx_bench.docx_to_pdf.convert_command('docxodus', ...)``: All Markup review profile in
Word's presentation, comments in balloons, LibreOffice's metric-compatible faces as the only
font directory, the same 180 s budget. ``--binary`` is the ``docxodus`` CLI of an
``@docxodus/export`` install; its version is checked against ``--version`` before anything runs.

One flag is added, ``--markup-mode inline``, to mirror how the endpoint's Word lays out
revisions since 2026-11-24 (``word-endpoint/word_endpoint/worker.py`` ``export_pdf``, Word for
Mac's view, ``word-endpoint/docs/review-view.md``): ``RevisionsMode = 1`` for every document, all
revisions inline, comments (only) in balloons, no "Formatted:" balloons. docxodus ``inline`` is
that setting ("Show All Revisions Inline, comments only"). Before 2026-11-24 the endpoint used
mixed mode for a redline with comments and this lane followed it. The comment count (distinct
``w:commentReference`` ids in ``word/document.xml``) and the mode are recorded on every line.

Every document appends one JSON line to ``docxodus_pdf.jsonl`` (key, ok, exit code, seconds,
input and output sha256, stderr tail). A PDF already on disk is skipped. ``--follow`` keeps
scanning ``word/docx`` every minute until every key of the set has a PDF or a failure line, or
no new Word redline has appeared for ``--idle`` minutes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import zipfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench.docx_to_pdf import convert_command

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SET_CSV = ROOT / 'results/sets/redline_600.csv'
LANE = 'docxodus-16.1.0-pdf'
LOG = HERE / 'docxodus_pdf.jsonl'


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def _is_pdf(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 64 and p.read_bytes()[:4] == b'%PDF'


def comment_count(docx: Path) -> int:
    """Distinct comments anchored in the main story, as Word's ``Document.Comments.Count`` counts them."""
    with zipfile.ZipFile(docx) as z:
        xml = z.read('word/document.xml').decode('utf-8', 'replace')
    return len(set(re.findall(r'<w:commentReference\b[^>]*\bw:id="([^"]+)"', xml)))


def convert(key: str, binary: Path, version: str) -> dict:
    src = HERE / 'word/docx' / f'{key}.docx'
    dest = HERE / LANE / 'pdf' / f'{key}.pdf'
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.stem + '.part.pdf')
    tmp.unlink(missing_ok=True)
    comments = comment_count(src)
    mode = 'inline'  # the endpoint's Word: RevisionsMode = 1 for every document
    argv = convert_command('docxodus', src, tmp, binary=binary)
    assert '--markup-mode' not in argv
    argv += ['--markup-mode', mode]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=240)
        rc, err = proc.returncode, (proc.stderr or proc.stdout)[-800:]
    except subprocess.TimeoutExpired:
        rc, err = None, 'killed after 240 s'
    secs = round(time.monotonic() - t0, 3)
    rec = {'key': key, 'ts': _now(), 'tool': f'@docxodus/export {version}', 'rc': rc, 'seconds': secs,
           'comments': comments, 'markup_mode': mode,
           'input': str(src.relative_to(ROOT)), 'input_sha256': _sha(src),
           'argv': [Path(a).name if a == str(binary) else a for a in argv[1:]]}
    if rc == 0 and _is_pdf(tmp):
        tmp.replace(dest)
        rec |= {'ok': True, 'out': str(dest.relative_to(ROOT)), 'out_sha256': _sha(dest),
                'out_bytes': dest.stat().st_size}
    else:
        tmp.unlink(missing_ok=True)
        rec |= {'ok': False, 'error': err.strip() or f'exit {rc}, no PDF'}
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--binary', type=Path, required=True, help='the docxodus CLI of an @docxodus/export install')
    ap.add_argument('--version', default='16.1.0', help='the @docxodus/export version the binary must be')
    ap.add_argument('--jobs', type=int, default=4)
    ap.add_argument('--follow', action='store_true')
    ap.add_argument('--idle', type=float, default=15.0, help='minutes without a new Word redline before --follow stops')
    a = ap.parse_args()
    binary = a.binary.resolve()
    pkg = binary.parents[1] / '@docxodus/export/package.json'
    found = json.loads(pkg.read_text())['version'] if pkg.is_file() else None
    if found != a.version:
        raise SystemExit(f'{pkg}: @docxodus/export {found}, expected {a.version}')
    keys = [r['key'] for r in csv.DictReader(open(SET_CSV))]
    failed = set()
    if LOG.is_file():
        failed = {json.loads(line)['key'] for line in open(LOG) if not json.loads(line)['ok']}
    last_new, started = time.monotonic(), time.monotonic()
    with ThreadPoolExecutor(a.jobs) as pool:
        while True:
            todo = [k for k in keys if k not in failed and (HERE / 'word/docx' / f'{k}.docx').is_file()
                    and not _is_pdf(HERE / LANE / 'pdf' / f'{k}.pdf')]
            if todo:
                last_new = time.monotonic()
            for rec in pool.map(lambda k: convert(k, binary, a.version), todo):
                with open(LOG, 'a') as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + '\n')
                if not rec['ok']:
                    failed.add(rec['key'])
                done = sum(_is_pdf(HERE / LANE / 'pdf' / f'{k}.pdf') for k in keys)
                state = 'ok' if rec['ok'] else f'FAILED rc={rec["rc"]} {rec["error"][-160:]!r}'
                print(f'[{(time.monotonic() - started) / 60:6.1f} min] {state} {rec["seconds"]:6.1f}s '
                      f'{rec["key"][:60]} | pdf {done}, failed {len(failed)}', flush=True)
            finished = all(k in failed or _is_pdf(HERE / LANE / 'pdf' / f'{k}.pdf') for k in keys)
            if not a.follow or finished or time.monotonic() - last_new > a.idle * 60:
                break
            time.sleep(60)
    done = sum(_is_pdf(HERE / LANE / 'pdf' / f'{k}.pdf') for k in keys)
    print(f'{_now()} {LANE}: {done} PDFs, {len(failed)} failed, of {len(keys)} keys', flush=True)


if __name__ == '__main__':
    main()
