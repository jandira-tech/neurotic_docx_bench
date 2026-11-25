"""jubarte's two lanes of the redline_600 Contabo tests.

    .venv/bin/python results/redline600_contabo/jubarte_lanes.py --binary <jubarte> [--version 0.20.0] \
        [--task redline] [--task convert] [--jobs 6] [--timeout 300]

``--binary`` is a jubarte release binary (``jubarte_release.resolve``); its ``--version`` must start
with ``jubarte <version>``. Both tasks run by default.

* ``redline`` (the redline capability): jubarte's compare of each pair of
  ``results/sets/redline_600.csv``, the bench's own jubarte-rust command
  (``scripts/generate-native-redlines.ts``): ``compare <base> <next> -o <out> --force --quiet -d
  1970-01-01T00:00:00Z``. Inputs are read from the set's paths and checked against its sha256.
  Output ``jubarte-<v>/docx/<key>_jubarte-<v>.docx``, which ``contabo_word.py convert-lane --lane
  jubarte-<v>`` sends to Word. Log ``jubarte_redlines.jsonl``.
* ``convert`` (the PDF conversion capability): jubarte's PDF of Word's own redline
  ``word/docx/<key>.docx``, the bench's own jubarte DOCX->PDF command
  (``docx_to_pdf.convert_command('jubarte', ...)``: ``convert --force --revisions word --compress``).
  Output ``jubarte-<v>-pdf/pdf/<key>.pdf``; its reference is ``word/pdf/<key>.pdf``. jubarte has no
  switch between inline revisions and balloons, so unlike ``docxodus_pdf.py`` nothing is added per
  document. Log ``jubarte_pdf.jsonl``.

Each document runs in its own process under ``--timeout`` seconds. One JSON line per document (key,
ok, exit code, seconds, input and output sha256, stderr tail). An output already on disk is skipped;
a document that failed before is not tried again.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from neurotic_docx_bench.docx_to_pdf import convert_command

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SET_CSV = ROOT / 'results/sets/redline_600.csv'
DOCX_MAGIC, PDF_MAGIC = b'PK\x03\x04', b'%PDF'


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


def _done(p: Path, magic: bytes) -> bool:
    return p.is_file() and p.stat().st_size > 64 and p.read_bytes()[:4] == magic


def _run(argv: list[str], timeout: int) -> tuple[int | None, str, float]:
    t0 = time.monotonic()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        rc, err = proc.returncode, (proc.stderr or proc.stdout)[-800:]
    except subprocess.TimeoutExpired:
        rc, err = None, f'killed after {timeout} s'
    return rc, err.strip(), round(time.monotonic() - t0, 3)


class Lanes:
    def __init__(self, binary: Path, version: str, timeout: int):
        self.binary, self.version, self.timeout = binary, version, timeout
        self.tool = f'jubarte {version}'
        self.redline_lane = f'jubarte-{version}'
        self.pdf_lane = f'jubarte-{version}-pdf'

    def redline_out(self, key: str) -> Path:
        return HERE / self.redline_lane / 'docx' / f'{key}_{self.redline_lane}.docx'

    def pdf_out(self, key: str) -> Path:
        return HERE / self.pdf_lane / 'pdf' / f'{key}.pdf'

    def redline(self, row: dict) -> dict:
        key, dest = row['key'], self.redline_out(row['key'])
        rec = {'key': key, 'ts': _now(), 'tool': self.tool, 'task': 'redline'}
        base, nxt = ROOT / row['base'], ROOT / row['next']
        for path, want in ((base, row['base_sha256']), (nxt, row['next_sha256'])):
            if _sha(path) != want:
                return rec | {'ok': False, 'error': f"{path.relative_to(ROOT)} does not match the set's sha256"}
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.stem + '.part.docx')
        tmp.unlink(missing_ok=True)
        argv = [str(self.binary), 'compare', str(base), str(nxt), '-o', str(tmp), '--force', '--quiet',
                '-d', '1970-01-01T00:00:00Z']
        rc, err, secs = _run(argv, self.timeout)
        rec |= {'rc': rc, 'seconds': secs, 'argv': ['jubarte', *argv[1:2], '<base>', '<next>', *argv[4:5],
                                                     '<out>', *argv[6:]],
                'inputs': [str(base.relative_to(ROOT)), str(nxt.relative_to(ROOT))]}
        return self._finish(rec, rc, err, tmp, dest, DOCX_MAGIC)

    def convert(self, key: str) -> dict:
        src, dest = HERE / 'word/docx' / f'{key}.docx', self.pdf_out(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.stem + '.part.pdf')
        tmp.unlink(missing_ok=True)
        argv = convert_command('jubarte', src, tmp, binary=self.binary)
        rc, err, secs = _run(argv, self.timeout)
        rec = {'key': key, 'ts': _now(), 'tool': self.tool, 'task': 'convert', 'rc': rc, 'seconds': secs,
               'input': str(src.relative_to(ROOT)), 'input_sha256': _sha(src),
               'argv': ['jubarte', *[a for a in argv[1:] if a not in (str(src), str(tmp))]]}
        return self._finish(rec, rc, err, tmp, dest, PDF_MAGIC)

    @staticmethod
    def _finish(rec: dict, rc: int | None, err: str, tmp: Path, dest: Path, magic: bytes) -> dict:
        if rc == 0 and _done(tmp, magic):
            tmp.replace(dest)
            return rec | {'ok': True, 'out': str(dest.relative_to(ROOT)), 'out_sha256': _sha(dest),
                          'out_bytes': dest.stat().st_size, **({'stderr': err[-300:]} if err else {})}
        tmp.unlink(missing_ok=True)
        return rec | {'ok': False, 'error': err or f'exit {rc}, no output'}


def _failed(log: Path) -> set[str]:
    if not log.is_file():
        return set()
    return {r['key'] for r in map(json.loads, open(log)) if not r['ok']}


def _drive(name: str, log: Path, items: list, fn, out_of, magic: bytes, jobs: int) -> None:
    failed = _failed(log)
    todo = [it for it in items if (it['key'] if isinstance(it, dict) else it) not in failed
            and not _done(out_of(it['key'] if isinstance(it, dict) else it), magic)]
    print(f'{_now()} {name}: {len(items)} items, {len(todo)} to run, {len(failed)} failed before', flush=True)
    ok = bad = 0
    started = time.monotonic()
    with ThreadPoolExecutor(jobs) as pool:
        for rec in pool.map(fn, todo):
            with open(log, 'a') as fh:
                fh.write(json.dumps(rec, sort_keys=True) + '\n')
            ok, bad = ok + rec['ok'], bad + (not rec['ok'])
            state = 'ok' if rec['ok'] else f'FAILED rc={rec.get("rc")} {rec["error"][-160:]!r}'
            print(f'[{(time.monotonic() - started) / 60:6.1f} min] {name} {state} {rec.get("seconds", 0):6.1f}s '
                  f'{rec["key"][:60]} | ok {ok}, failed {bad}', flush=True)
    done = sum(_done(out_of(it['key'] if isinstance(it, dict) else it), magic) for it in items)
    print(f'{_now()} {name}: {done} of {len(items)} on disk, {bad} failed this pass', flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--binary', type=Path, required=True)
    ap.add_argument('--version', default='0.20.0')
    ap.add_argument('--task', action='append', choices=['redline', 'convert'])
    ap.add_argument('--jobs', type=int, default=6)
    ap.add_argument('--timeout', type=int, default=300)
    a = ap.parse_args()
    binary = a.binary.expanduser().resolve()
    reported = subprocess.run([str(binary), '--version'], capture_output=True, text=True).stdout.strip()
    if not reported.startswith(f'jubarte {a.version}'):
        raise SystemExit(f'{binary} reports {reported!r}, not jubarte {a.version}')
    print(f'{_now()} {binary} reports {reported!r}, sha256 {_sha(binary)}', flush=True)
    rows = list(csv.DictReader(open(SET_CSV)))
    if len(rows) != 600:
        raise SystemExit(f'{SET_CSV} has {len(rows)} rows, not 600')
    lanes = Lanes(binary, a.version, a.timeout)
    tasks = a.task or ['redline', 'convert']
    if 'redline' in tasks:
        _drive(lanes.redline_lane, HERE / 'jubarte_redlines.jsonl', rows, lanes.redline, lanes.redline_out,
               DOCX_MAGIC, a.jobs)
    if 'convert' in tasks:
        keys = [r['key'] for r in rows if _done(HERE / 'word/docx' / f'{r["key"]}.docx', DOCX_MAGIC)]
        _drive(lanes.pdf_lane, HERE / 'jubarte_pdf.jsonl', keys, lanes.convert, lanes.pdf_out, PDF_MAGIC, a.jobs)


if __name__ == '__main__':
    main()
