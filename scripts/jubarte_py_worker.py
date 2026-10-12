# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Long-lived jubarte-redlines (Python binding) worker for redline_speed_bench.ts.

The protocol of ``jubarte-rust-inproc`` (``jubarte-worker``), so the Python lane is
driven and timed exactly like the native warm worker, plus a PDF command:

    READY
    COMPARE <base> <next> <out>   -> OK <bytes> <ms> | ERR <message>
    PDF <src> <dst>               -> OK <bytes> <ms> | ERR <message>
    QUIT                          -> BYE

Paths are tab-separated when they hold spaces. ``<ms>`` times read + call + write
inside this process; the harness records its own round-trip time as the sample.
Run it with the interpreter of the environment the wheel under test is installed in.
"""

from __future__ import annotations

import sys
import time

import jubarte_redlines
from jubarte_redlines import _native


def paths(rest: str, n: int) -> list[str] | None:
    parts = rest.split('\t') if '\t' in rest else rest.split(' ')
    return parts if len(parts) == n else None


def compare(base: str, nxt: str, out: str) -> int:
    with open(base, 'rb') as f:
        a = f.read()
    with open(nxt, 'rb') as f:
        b = f.read()
    redline = jubarte_redlines.compare_documents(a, b)
    with open(out, 'wb') as f:
        f.write(redline)
    return len(redline)


def pdf(src: str, dst: str) -> int:
    with open(src, 'rb') as f:
        docx = f.read()
    # What Document.to_pdf calls; Word revision marks, as the bench's converters use.
    data = _native.docx_to_pdf(docx, compress=False, revisions='word', revision_palette=None)
    with open(dst, 'wb') as f:
        f.write(data)
    return len(data)


def main() -> int:
    out = sys.stdout
    out.write('READY\n')
    out.flush()
    for line in sys.stdin:
        line = line.rstrip('\r\n')
        if not line.strip():
            continue
        if line == 'QUIT':
            out.write('BYE\n')
            out.flush()
            return 0
        cmd, _, rest = line.partition(' ')
        call, want = {'COMPARE': (compare, 3), 'PDF': (pdf, 2)}.get(cmd, (None, 0))
        args = paths(rest, want) if call else None
        if args is None:
            out.write(f'ERR bad command: {line[:80]}\n')
            out.flush()
            continue
        t0 = time.perf_counter()
        try:
            n = call(*args)
            out.write(f'OK {n} {(time.perf_counter() - t0) * 1000:.3f}\n')
        except Exception as e:  # an engine error answers ERR; the worker stays up
            msg = f'{type(e).__name__}: {e}'.replace('\n', ' ').replace('\r', ' ')
            out.write(f'ERR {msg}\n')
        out.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
