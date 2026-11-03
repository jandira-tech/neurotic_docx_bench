"""Stamp-matched score of the Apryse 12.2.1 lane on the fixed set (#129). The raw score is the record.

    uv run python results/redlines_0929_full/apryse-12.2.1/measure_stamp.py

The same normalisation as the 0929 Apryse lane (``results/redlines_0929_full/apryse/measure_stamp.py``):
Apryse ran with the demo key, so every page of its redline carries Apryse's watermark, and
the raw score is measured against Word's clean compare. Here Word's compare gets the stamp
of the Apryse redline of the same pair (``apryse_stamp.apply_word_stamp``: the header image
Word rendered, under its own matrix, Multiply blend), so the watermark is on both sides and
it cancels.

It is a separate, labelled figure, never the record: ``scores_apryse-12.2.1_set-redline_600.json``
is the record. Rasters live in a temporary folder, deleted per chunk.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
RUN = HERE.parent
sys.path.insert(0, str(RUN))
sys.path.insert(0, str(RUN.parents[1] / 'src'))
import measure  # noqa: E402

from neurotic_docx_bench import kernels, pipeline  # noqa: E402
from neurotic_docx_bench import apryse_stamp  # noqa: E402

TOOL = 'apryse-12.2.1'
SET = 'redline_600'


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fresh', type=Path, default=Path.home() / 'temp/T/neurotic_docx_bench/results/compare_regen/out')
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--chunk', type=int, default=100)
    a = ap.parse_args()

    raw = json.loads((RUN / f'scores_{TOOL}_set-{SET}.json').read_text())
    pool = list(measure.csv.DictReader(open(RUN / 'pool_pairs.csv')))
    gen = list(measure.csv.DictReader(open(RUN / 'gen_pairs.csv')))
    first = {(r['base'], r['next']): r['key'] for r in reversed(gen)}
    oracle = measure.oracles(pool, a.fresh)
    by_key = {r['key']: r for r in pool}
    set_keys = [r['key'] for r in measure.csv.DictReader(open(RUN / f'set-{SET}.csv'))]
    lane = HERE / 'pdf_by_word'
    cand = {k: measure.candidate_pdf(lane, first[by_key[k]['base'], by_key[k]['next']], TOOL) for k in set_keys}
    keys = sorted(k for k in raw['rows'] if k in cand and cand[k].is_file())
    print(f'{TOOL}: {len(keys)} compares with an Apryse PDF; backend {kernels.backend_id()}', flush=True)

    rows: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for i in range(0, len(keys), a.chunk):
        part = keys[i:i + a.chunk]
        with tempfile.TemporaryDirectory(prefix=f'stamp-{TOOL}.') as tmp:
            orc, cd, work = Path(tmp) / 'oracle', Path(tmp) / 'candidate', Path(tmp) / 'work'
            for d in (orc, cd, work):
                d.mkdir()
            for k in part:
                try:
                    apryse_stamp.apply_word_stamp(oracle[k][0], cand[k], orc / f'{k}.pdf')
                    (cd / f'{k}_{TOOL}.pdf').symlink_to(cand[k].resolve())
                except Exception as exc:  # a PDF without the stamp, a broken PDF
                    errors[k] = f'{type(exc).__name__}: {exc}'
                    (orc / f'{k}.pdf').unlink(missing_ok=True)
                    (cd / f'{k}_{TOOL}.pdf').unlink(missing_ok=True)
            got = pipeline.score_folders_full(orc, cd, work, candidate_tool=TOOL, jobs=a.jobs)
        for k, v in got.items():
            r = measure._scalars(v)
            r['raw_overall_score'] = raw['rows'][k]['overall_score']
            r['oracle'] = oracle[k][1]
            rows[k] = r
        print(f'{TOOL}: {len(rows)} scored, {len(errors)} not stamped, {len(keys) - i - len(part)} to go', flush=True)

    summary = measure._stats(list(rows.values()), len(keys))
    deltas = [r['overall_score'] - r['raw_overall_score'] for r in rows.values()]
    summary['delta_vs_raw'] = {
        'mean': sum(deltas) / len(deltas) if deltas else None,
        'abs_gt_5': sum(abs(d) > 5 for d in deltas),
        'min': min(deltas, default=None), 'max': max(deltas, default=None),
    }
    summary['scorer_backend'] = kernels.backend_id()
    summary['fresh_dir'] = str(a.fresh)
    summary['set'] = SET
    summary['label'] = ('stamp-matched normalisation (Apryse demo watermark on the oracle too); '
                        f'NOT the record: scores_{TOOL}_set-{SET}.json is')
    out = RUN / f'scores_{TOOL}_set-{SET}_stamp_matched.json'
    out.write_text(json.dumps({'summary': summary, 'errors': errors, 'rows': rows}, indent=1, sort_keys=True))
    o = summary['overall']
    print(f'{TOOL} stamp-matched: {summary["scored"]} scored, mean {o.get("mean", 0):.2f}, median '
          f'{o.get("median", 0):.2f}; delta vs raw mean {summary["delta_vs_raw"]["mean"]:+.3f}, '
          f'|delta|>5: {summary["delta_vs_raw"]["abs_gt_5"]} -> {out}', flush=True)


if __name__ == '__main__':
    os.environ.setdefault('BENCH_DEVICE', 'mps')
    kernels.reset()
    main()
