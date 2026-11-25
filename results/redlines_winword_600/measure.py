"""Score the two redline_600 tests against Contabo Word's PDFs.

    .venv/bin/python results/redline600_contabo/measure.py redline convert [--device mps]

Both tests share one reference: ``word/pdf/<key>.pdf``, Word 2024 on the Contabo endpoint
exporting its own compare of the pair (``contabo_word.py compare convert-word``). There is no
fallback to any other oracle: a pair Word did not compare and export is not in either test, and
is listed under ``no_reference``.

* ``redline`` (the redline capability): docxodus 16.1.0's redline of the pair, exported to PDF
  by the same Word (``docxodus-16.1.0/pdf_by_word/<key>_docxodus-16.1.0.pdf``). Word renders
  both sides, so the redline is the only thing that differs.
* ``redline-folio-emit``: the same test for folio 0.70.0's ``compareDocx`` with
  ``onUnverified: "emit"`` (``folio_redlines.ts``), every redline it returned, exported by Word
  (``folio-0.70.0-emit/pdf_by_word``). Rows and the summary split them by whether strict mode
  returned the same package (``folio_source``: ``strict`` = verified, ``emit-only`` = refused under
  the strict default). ``redline-folio`` scores the strict lane, if it was ever exported.
* ``convert`` (the PDF conversion capability): docxodus's PDF of Word's own redline docx
  (``docxodus-16.1.0-pdf/pdf/<key>.pdf``, ``docxodus_pdf.py``). The docx is the same on both
  sides, so the converter is the only thing that differs.
* ``redline-jubarte`` and ``convert-jubarte``: the same two tests for jubarte 0.20.0
  (``jubarte_lanes.py``): its redline exported by Word (``jubarte-0.20.0/pdf_by_word``), and its
  PDF of Word's redline docx (``jubarte-0.20.0-pdf/pdf``).
* ``redline-superdoc``: the redline test for SuperDoc SDK 2.31.0 (``neurotic_docx_bench.superdoc_gen``),
  exported by Word (``superdoc-2.31.0/pdf_by_word``); a pair it refused counts 0 in the ITT figures.
* ``word-mac``: not a tool. The set's committed oracle, Mac Word's own compare of the pair exported by
  Mac Word (the set's ``pdf`` column, ``corpus/word``), scored against Contabo's: how far the two
  Words' redlines are apart on the page, markup and rendering together.
* ``word-mac-local`` and ``convert-word-mac``: the split of ``word-mac`` into its two halves, run
  on 2026-11-24 with this machine's Word for Mac (``.scratch/macword600/collect.py`` files them
  under ``word-mac-local/``). ``word-mac-local`` is Mac Word's compare of the same pair inputs
  (the set's base and next), exported to PDF by Mac Word: compare and rendering together.
  ``convert-word-mac`` is Mac Word's PDF of Contabo Word's own redline docx (``word/docx``): the
  docx is the same on both sides, so Mac Word's rendering is the only thing that differs.

Scoring is the bench's verbatim scorer through ``pipeline.score_folders_full`` (144 DPI, every
page, no content cache). Rasters live in a temporary folder deleted after each chunk. A pair
with a reference but no candidate scores 0 in the intent-to-treat figures (``overall_itt``).
Writes ``scores_<test>.json``: summary (overall, ITT, by compare state, and for ``convert`` by
the markup mode docxodus was given), the missing keys, and one row per scored pair with both
PDFs' sha256.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import tempfile
from pathlib import Path

from neurotic_docx_bench import content_cache, kernels, pipeline
from neurotic_docx_bench.page_scores import per_page_scores

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SET_CSV = ROOT / 'results/sets/redline_600.csv'
TOOL = 'docxodus-16.1.0'
FOLIO = 'folio-0.70.0'
JUBARTE = 'jubarte-0.20.0'
SUPERDOC = 'superdoc-2.31.0'


def _lane_pdf(lane: str, k: str) -> Path:
    return HERE / lane / 'pdf_by_word' / f'{k}_{lane}.pdf'


def _folio_log() -> dict[str, dict]:
    log = HERE / 'folio_redlines.jsonl'
    return {r['key']: r for r in map(json.loads, open(log))} if log.is_file() else {}


_FOLIO_LOG: dict[str, dict] = {}
_MAC_WORD_PDF = {r['key']: ROOT / r['pdf'] for r in csv.DictReader(open(SET_CSV))}
TESTS = {
    'redline': (TOOL, lambda k: _lane_pdf(TOOL, k)),
    'redline-folio': (FOLIO, lambda k: _lane_pdf(FOLIO, k)),
    'redline-folio-emit': (f'{FOLIO}-emit', lambda k: _lane_pdf(f'{FOLIO}-emit', k)),
    'convert': (f'{TOOL}-pdf', lambda k: HERE / f'{TOOL}-pdf' / 'pdf' / f'{k}.pdf'),
    'redline-jubarte': (JUBARTE, lambda k: _lane_pdf(JUBARTE, k)),
    'redline-superdoc': (SUPERDOC, lambda k: _lane_pdf(SUPERDOC, k)),
    'word-mac': ('word-mac', lambda k: _MAC_WORD_PDF[k]),
    'convert-jubarte': (f'{JUBARTE}-pdf', lambda k: HERE / f'{JUBARTE}-pdf' / 'pdf' / f'{k}.pdf'),
    'word-mac-local': ('word-mac-local', lambda k: HERE / 'word-mac-local' / 'redline_pdf' / f'{k}.pdf'),
    'redline-docxodus-mac': ('docxodus-16.1.0-macword', lambda k: HERE / 'docxodus-16.1.0-macword' / f'{k}.pdf'),
    'convert-word-mac': ('word-mac-local-convert', lambda k: HERE / 'word-mac-local' / 'convert_pdf' / f'{k}.pdf'),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_pdf(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 64 and p.read_bytes()[:4] == b'%PDF'


def _row(result: dict) -> dict:
    scalars = {k: v for k, v in result.items() if isinstance(v, (int, float, str, bool)) or v is None}
    pages = per_page_scores(result)
    return scalars | {'per_page': pages} if pages else scalars


def _stats(rows: list[dict], expected: int) -> dict:
    overall = [pipeline.overall_from_result(r) for r in rows]
    ink = [r['ink_jaccard'] for r in rows if r.get('ink_jaccard') is not None]
    out = {'pairs': expected, 'scored': len(rows), 'missing': expected - len(rows)}
    for name, xs in (('overall', overall), ('ink_jaccard', ink)):
        out[name] = {'n': len(xs)} | ({'mean': statistics.fmean(xs), 'median': statistics.median(xs)} if xs else {})
    if overall:
        out['overall'] |= {'exact_100': sum(x >= 100 for x in overall), 'at_least_90': sum(x >= 90 for x in overall),
                           'below_50': sum(x < 50 for x in overall)}
    itt = overall + [0.0] * out['missing']
    if itt:
        out['overall_itt'] = {'n': len(itt), 'mean': statistics.fmean(itt), 'median': statistics.median(itt),
                              'at_least_90': sum(x >= 90 for x in itt), 'below_50': sum(x < 50 for x in itt)}
    return out


def _modes() -> dict[str, str]:
    """The markup mode docxodus_pdf.py gave each key (its last successful line)."""
    log = HERE / 'docxodus_pdf.jsonl'
    out = {}
    if log.is_file():
        for line in open(log):
            rec = json.loads(line)
            if rec.get('ok'):
                out[rec['key']] = rec.get('markup_mode', '?')
    return out


def measure(test: str, jobs: int, chunk: int) -> None:
    tool, cand_of = TESTS[test]
    if test.startswith('redline-folio'):
        _FOLIO_LOG.update(_folio_log())
    rows_set = list(csv.DictReader(open(SET_CSV)))
    state = {r['key']: r['state'] for r in rows_set}
    ref = {k: HERE / 'word/pdf' / f'{k}.pdf' for k in state}
    no_reference = sorted(k for k, p in ref.items() if not _is_pdf(p))
    keys = [k for k in state if k not in set(no_reference)]
    cand = {k: cand_of(k) for k in keys}
    todo = [k for k in keys if _is_pdf(cand[k])]
    scorer = f'{kernels.backend_id()}:{content_cache.scorer_fingerprint()}'
    print(f'{test}: {len(state)} pairs, {len(no_reference)} without a Word reference, '
          f'{len(keys)} in the test, {len(todo)} candidates to score ({tool})', flush=True)
    rows: dict[str, dict] = {}
    for i in range(0, len(todo), chunk):
        part = todo[i:i + chunk]
        with tempfile.TemporaryDirectory(prefix=f'measure-{test}.') as tmp:
            orc, cnd, work = (Path(tmp) / d for d in ('oracle', 'candidate', 'work'))
            for d in (orc, cnd, work):
                d.mkdir()
            for k in part:
                (orc / f'{k}.pdf').symlink_to(ref[k])
                (cnd / f'{k}_{tool}.pdf').symlink_to(cand[k])
            got = pipeline.score_folders_full(orc, cnd, work, candidate_tool=tool, jobs=jobs)
        for k, v in got.items():
            rows[k] = _row(v) | {'state': state[k], 'oracle_sha256': _sha(ref[k]),
                                 'candidate_sha256': _sha(cand[k]), 'scorer': scorer}
        print(f'{test}: {len(rows)} scored, {len(todo) - i - len(part)} to go', flush=True)
    modes = _modes() if test == 'convert' else {}
    for k in rows:
        if modes:
            rows[k]['markup_mode'] = modes.get(k, '?')
        if test == 'redline-folio-emit':
            rec = _FOLIO_LOG.get(k, {})
            rows[k]['folio_source'] = 'strict' if rec.get('emit_equals_strict') else 'emit-only'
            rows[k]['folio_verification'] = (rec.get('emit') or {}).get('verification')
    summary = _stats(list(rows.values()), len(keys))
    summary['by_state'] = {
        s: _stats([v for k, v in rows.items() if state[k] == s], sum(state[k] == s for k in keys))
        for s in sorted({state[k] for k in keys})
    }
    if modes:
        mode_of = {k: modes.get(k, '?') for k in keys}
        summary['by_markup_mode'] = {
            m: _stats([v for k, v in rows.items() if mode_of[k] == m], sum(x == m for x in mode_of.values()))
            for m in sorted(set(mode_of.values()))
        }
    if test.startswith('redline-folio'):
        mode = 'emit' if test.endswith('-emit') else 'strict'
        status = {k: (_FOLIO_LOG.get(k, {}).get(mode) or {}).get('status', 'not run') for k in keys}
        summary['folio_status'] = {st: sum(v == st for v in status.values()) for st in sorted(set(status.values()))}
    if test == 'redline-folio-emit':
        src = {k: 'strict' if _FOLIO_LOG.get(k, {}).get('emit_equals_strict') else 'emit-only' for k in keys}
        summary['by_folio_source'] = {
            m: _stats([v for k, v in rows.items() if src[k] == m], sum(x == m for x in src.values()))
            for m in sorted(set(src.values()))
        }
    summary |= {'test': test, 'candidate_tool': tool, 'reference': 'Word 2024 (Contabo /v1/convert) of '
                'Word 2024 (Contabo /v1/compare)', 'set': 'redline_600', 'set_pairs': len(state),
                'no_reference': len(no_reference), 'scorer': scorer, 'dpi': 144}
    missing = sorted(set(keys) - set(rows))
    out = HERE / f'scores_{test}.json'
    out.write_text(json.dumps({'summary': summary, 'no_reference': no_reference, 'missing': missing,
                               'rows': rows}, indent=1, sort_keys=True))
    o, itt = summary['overall'], summary.get('overall_itt', {})
    print(f'{test}: {summary["scored"]}/{summary["pairs"]} scored, mean {o.get("mean", 0):.2f}, median '
          f'{o.get("median", 0):.2f}, >=90 {o.get("at_least_90", 0)}; ITT mean {itt.get("mean", 0):.2f}, '
          f'median {itt.get("median", 0):.2f} -> {out.relative_to(ROOT)}', flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tests', nargs='+', choices=sorted(TESTS))
    ap.add_argument('--device', choices=kernels.DEVICE_SPECS, help='scorer kernels (cpu, mps, cuda, auto)')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 12)
    ap.add_argument('--chunk', type=int, default=200)
    a = ap.parse_args()
    with kernels.device_env(a.device):
        for t in a.tests:
            measure(t, a.jobs, a.chunk)


if __name__ == '__main__':
    main()
