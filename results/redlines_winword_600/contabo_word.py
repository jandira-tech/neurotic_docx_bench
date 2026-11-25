# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28,<1"]
# ///
"""Send the fixed set redline_600 to the Contabo Word endpoint and keep every reply.

    uv run --script results/redline600_contabo/contabo_word.py compare convert-word
    uv run --script results/redline600_contabo/contabo_word.py convert-docxodus
    uv run --script results/redline600_contabo/contabo_word.py compare convert-word --limit 2

Stages (run from the bench root):

* ``compare``: Word compares each pair of ``results/sets/redline_600.csv`` (``base`` as
  ``original``, ``next`` as ``revised``) into ``word/docx/<key>.docx``: the reference redline.
* ``convert-word``: Word exports each of those to ``word/pdf/<key>.pdf``. With ``compare`` in
  the same run, each pair's export is queued as soon as its compare lands.
* ``convert-docxodus``: Word exports each docxodus redline
  ``docxodus-16.1.0/docx/<key>_docxodus-16.1.0.docx`` to
  ``docxodus-16.1.0/pdf_by_word/<key>_docxodus-16.1.0.pdf``.
* ``convert-lane`` with ``--lane NAME`` (repeatable): the same for any tool's lane,
  ``NAME/docx/<key>_NAME.docx`` to ``NAME/pdf_by_word/<key>_NAME.pdf``. Only pairs with a Word
  reference PDF (``word/pdf/<key>.pdf``) are sent, since no other pair is scored.

The endpoint is ``WORD_PUBLIC_URL`` with ``WORD_API_TOKEN`` (environment first, else the bench
root's ``.env``); the token is only ever sent in the Authorization header. Every input's sha256
is checked against the set before it is sent. Multipart file names are short and generic
(``original.docx``), so a long key never reaches a Windows path. Each lane (compare, convert)
keeps ``--inflight`` requests open: one running on that lane's Word, the rest queued behind it.

Every call appends one JSON line to ``endpoint.jsonl``: stage, key, input shas, HTTP status,
seconds, attempt, the endpoint's ``x-request-id``, the output's sha256 and size, or the error
text. A 503/429 waits ``Retry-After`` and tries again; a timeout, a dropped connection or a
5xx other than 503 is tried again up to ``--retries`` times; a 4xx is the endpoint's guard
refusing the file and is never retried. An output already on disk (right magic bytes) is
skipped, so a rerun does only what is missing.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SET_CSV = ROOT / 'results/sets/redline_600.csv'
TOOL = 'docxodus-16.1.0'
LOG = HERE / 'endpoint.jsonl'
DOCX_MAGIC, PDF_MAGIC = b'PK\x03\x04', b'%PDF'
RETRYABLE = {500, 502, 504, 520, 521, 522, 523, 524, 525, 526, 527, 530}


def _env() -> tuple[str, str]:
    vals = {}
    env_file = ROOT / '.env'
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                vals[k.strip()] = v.strip()
    url = os.environ.get('WORD_PUBLIC_URL') or vals.get('WORD_PUBLIC_URL', '')
    token = os.environ.get('WORD_API_TOKEN') or vals.get('WORD_API_TOKEN', '')
    if not url or not token:
        raise SystemExit('WORD_PUBLIC_URL and WORD_API_TOKEN must be set (environment or .env)')
    return url.rstrip('/'), token


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _done(path: Path, magic: bytes) -> bool:
    if not path.is_file() or path.stat().st_size < 64:
        return False
    with open(path, 'rb') as fh:
        return fh.read(len(magic)) == magic


class Runner:
    def __init__(self, url: str, token: str, inflight: int, retries: int, timeout: float) -> None:
        self.url, self.retries = url, retries
        self.client = httpx.AsyncClient(
            headers={'Authorization': f'Bearer {token}'},
            timeout=httpx.Timeout(timeout, connect=30.0),
            limits=httpx.Limits(max_connections=inflight * 2 + 2),
        )
        self.lanes = {'compare': asyncio.Semaphore(inflight), 'convert': asyncio.Semaphore(inflight)}
        self.counts: dict[str, dict[str, int]] = {}
        self.started = time.monotonic()

    def _log(self, rec: dict) -> None:
        with open(LOG, 'a') as fh:
            fh.write(json.dumps(rec, sort_keys=True) + '\n')
        c = self.counts.setdefault(rec['stage'], {'ok': 0, 'failed': 0})
        c['ok' if rec['ok'] else 'failed'] += 1
        took = time.monotonic() - self.started
        tally = ' '.join(f'{s}={v["ok"]}ok/{v["failed"]}fail' for s, v in sorted(self.counts.items()))
        msg = 'ok' if rec['ok'] else f'FAILED {rec.get("status")} {str(rec.get("error", ""))[:160]}'
        print(f'[{took / 60:6.1f} min] {rec["stage"]:16} {msg} {rec["key"][:60]} | {tally}', flush=True)

    async def call(self, stage: str, key: str, route: str, files: dict[str, tuple[Path, str]],
                   out: Path, magic: bytes) -> bool:
        """POST ``files`` ({field: (path, expected sha256 or '')}) to ``route``; write the reply to ``out``."""
        blobs, inputs = {}, []
        for field, (path, want) in files.items():
            data = path.read_bytes()
            got = _sha(data)
            if want and got != want:
                self._log({'stage': stage, 'key': key, 'ok': False, 'status': None, 'ts': _now(),
                           'error': f'{path} sha256 {got} != set {want}; not sent'})
                return False
            blobs[field] = (f'{field}.docx', data,
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
            inputs.append({'field': field, 'path': str(path.relative_to(ROOT)), 'sha256': got, 'bytes': len(data)})
        lane = self.lanes['compare' if route == '/v1/compare' else 'convert']
        attempt, busy = 0, 0
        while True:
            attempt += 1
            t0 = time.monotonic()
            rec = {'stage': stage, 'key': key, 'route': route, 'inputs': inputs, 'attempt': attempt, 'ts': _now()}
            try:
                async with lane:
                    resp = await self.client.post(self.url + route, files=blobs)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                rec |= {'ok': False, 'status': None, 'seconds': round(time.monotonic() - t0, 3),
                        'error': f'{type(exc).__name__}: {exc}'}
                if attempt <= self.retries:
                    print(f'  retry {stage} {key[:50]}: {rec["error"][:120]}', flush=True)
                    await asyncio.sleep(10 * attempt)
                    continue
                self._log(rec)
                return False
            secs = round(time.monotonic() - t0, 3)
            rec |= {'status': resp.status_code, 'seconds': secs, 'request_id': resp.headers.get('x-request-id')}
            if resp.status_code in (429, 503) and busy < 120:
                busy += 1
                attempt -= 1  # admission refusals are not attempts at the document
                await asyncio.sleep(float(resp.headers.get('retry-after') or 5))
                continue
            body = resp.content
            if resp.status_code == 200 and body[:len(magic)] == magic:
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp = out.with_name(out.name + '.part')
                tmp.write_bytes(body)
                os.replace(tmp, out)
                rec |= {'ok': True, 'out': str(out.relative_to(ROOT)), 'out_sha256': _sha(body),
                        'out_bytes': len(body)}
                self._log(rec)
                return True
            err = body[:600].decode('utf-8', 'replace') if body[:len(magic)] != magic else 'unexpected payload'
            rec |= {'ok': False, 'error': err, 'content_type': resp.headers.get('content-type')}
            if resp.status_code in RETRYABLE and attempt <= self.retries:
                print(f'  retry {stage} {key[:50]}: HTTP {resp.status_code} {err[:120]}', flush=True)
                await asyncio.sleep(10 * attempt)
                continue
            self._log(rec)
            return False


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec='seconds')


async def main_async(a: argparse.Namespace) -> None:
    rows = list(csv.DictReader(open(SET_CSV)))
    if len(rows) != 600:
        raise SystemExit(f'{SET_CSV} has {len(rows)} rows, not 600')
    if a.limit:
        rows = rows[:a.limit]
    url, token = _env()
    r = Runner(url, token, a.inflight, a.retries, a.timeout)
    word_docx = lambda k: HERE / 'word/docx' / f'{k}.docx'  # noqa: E731
    word_pdf = lambda k: HERE / 'word/pdf' / f'{k}.pdf'  # noqa: E731
    dx_docx = lambda k: HERE / TOOL / 'docx' / f'{k}_{TOOL}.docx'  # noqa: E731
    dx_pdf = lambda k: HERE / TOOL / 'pdf_by_word' / f'{k}_{TOOL}.pdf'  # noqa: E731

    async def convert_word(row: dict) -> None:
        k = row['key']
        if _done(word_pdf(k), PDF_MAGIC) or not _done(word_docx(k), DOCX_MAGIC):
            return
        await r.call('convert-word', k, '/v1/convert', {'document': (word_docx(k), '')}, word_pdf(k), PDF_MAGIC)

    async def compare(row: dict) -> None:
        k = row['key']
        if not _done(word_docx(k), DOCX_MAGIC):
            files = {'original': (ROOT / row['base'], row['base_sha256']),
                     'revised': (ROOT / row['next'], row['next_sha256'])}
            if not await r.call('compare', k, '/v1/compare', files, word_docx(k), DOCX_MAGIC):
                return
        if 'convert-word' in a.stages:
            await convert_word(row)

    def lane_docx(lane: str, k: str) -> Path:
        return HERE / lane / 'docx' / f'{k}_{lane}.docx'

    def lane_pdf(lane: str, k: str) -> Path:
        return HERE / lane / 'pdf_by_word' / f'{k}_{lane}.pdf'

    async def convert_lane(lane: str, row: dict) -> None:
        k = row['key']
        src, dest = lane_docx(lane, k), lane_pdf(lane, k)
        if _done(dest, PDF_MAGIC) or not _done(src, DOCX_MAGIC) or not _done(word_pdf(k), PDF_MAGIC):
            return
        await r.call(f'convert-{lane}', k, '/v1/convert', {'document': (src, '')}, dest, PDF_MAGIC)

    async def convert_docxodus(row: dict) -> None:
        k = row['key']
        if _done(dx_pdf(k), PDF_MAGIC) or not _done(dx_docx(k), DOCX_MAGIC):
            return
        await r.call('convert-docxodus', k, '/v1/convert', {'document': (dx_docx(k), '')}, dx_pdf(k), PDF_MAGIC)

    tasks = []
    if 'compare' in a.stages:
        tasks += [compare(row) for row in rows]
    elif 'convert-word' in a.stages:
        tasks += [convert_word(row) for row in rows]
    if 'convert-docxodus' in a.stages:
        tasks += [convert_docxodus(row) for row in rows]
    if 'convert-lane' in a.stages:
        if not a.lane:
            raise SystemExit('convert-lane needs at least one --lane NAME')
        tasks += [convert_lane(lane, row) for lane in a.lane for row in rows]
    print(f'{_now()} {url} stages={",".join(a.stages)} pairs={len(rows)} inflight/lane={a.inflight}', flush=True)
    try:
        await asyncio.gather(*tasks)
    finally:
        await r.client.aclose()
    have = {
        'word docx': sum(_done(word_docx(x['key']), DOCX_MAGIC) for x in rows),
        'word pdf': sum(_done(word_pdf(x['key']), PDF_MAGIC) for x in rows),
        f'{TOOL} docx': sum(_done(dx_docx(x['key']), DOCX_MAGIC) for x in rows),
        f'{TOOL} pdf_by_word': sum(_done(dx_pdf(x['key']), PDF_MAGIC) for x in rows),
    }
    for lane in a.lane:
        have[f'{lane} docx'] = sum(_done(lane_docx(lane, x['key']), DOCX_MAGIC) for x in rows)
        have[f'{lane} pdf_by_word'] = sum(_done(lane_pdf(lane, x['key']), PDF_MAGIC) for x in rows)
    print(f'{_now()} done in {(time.monotonic() - r.started) / 60:.1f} min; on disk of {len(rows)}: '
          + ', '.join(f'{k} {v}' for k, v in have.items()), flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stages', nargs='+', choices=['compare', 'convert-word', 'convert-docxodus', 'convert-lane'])
    ap.add_argument('--lane', action='append', default=[], help='a lane folder under the run dir (convert-lane)')
    ap.add_argument('--limit', type=int, default=0, help='first N pairs of the set only')
    ap.add_argument('--inflight', type=int, default=2, help='open requests per lane (default 2)')
    ap.add_argument('--retries', type=int, default=2, help='retries after a timeout, dropped connection or 5xx')
    ap.add_argument('--timeout', type=float, default=900.0, help='seconds to wait for one reply')
    a = ap.parse_args()
    if Path.cwd().resolve() != ROOT:
        sys.exit(f'run from the bench root {ROOT}')
    asyncio.run(main_async(a))


if __name__ == '__main__':
    main()
