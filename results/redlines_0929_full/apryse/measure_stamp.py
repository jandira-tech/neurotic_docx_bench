"""Stamp-matched score of Apryse's Word-rendered redlines (#100). The raw score is the record.

    BENCH_DEVICE=mps .venv/bin/python results/redlines_0929_full/apryse/measure_stamp.py apryse
    BENCH_DEVICE=mps .venv/bin/python results/redlines_0929_full/apryse/measure_stamp.py jubarte-0.17.0 --sample 300

For every compare ``scores_<tool>.json`` scored, the oracle gets the demo stamp of the
*Apryse* redline of that pair (``apryse_stamp.apply_word_stamp``: the header picture Word
rendered, under its own matrix, Multiply blend). ``apryse``: Apryse's candidate against the
stamped oracle, so the stamp is on both sides. Any other tool is the control: its candidate
is stamped the same way too, so the score should not move (the normalisation's own error).
Writes ``scores_<tool>_stamp_matched.json`` beside measure.py. Rasters live in a temporary
folder, deleted per chunk.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import measure  # noqa: E402

from neurotic_docx_bench import kernels, pipeline  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    'apryse_stamp', Path.home() / 'temp/T/ndb-apryse/src/neurotic_docx_bench/apryse_stamp.py')
apryse_stamp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apryse_stamp)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('tool')
    ap.add_argument('--fresh', type=Path, default=Path('results/compare_regen/out'))
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--chunk', type=int, default=250)
    a = ap.parse_args()

    raw = json.loads((HERE / f'scores_{a.tool}.json').read_text())
    pool = list(measure.csv.DictReader(open(HERE / 'pool_pairs.csv')))
    gen = list(measure.csv.DictReader(open(HERE / 'gen_pairs.csv')))
    first = {(r['base'], r['next']): r['key'] for r in reversed(gen)}
    oracle = measure.oracles(pool, a.fresh)
    by_key = {r['key']: r for r in pool}
    apryse_dir = HERE / 'apryse' / 'pdf_by_word'
    tool_dir = HERE / a.tool / 'pdf_by_word'
    stamp_src = {k: measure.candidate_pdf(apryse_dir, first[r['base'], r['next']], 'apryse') for k, r in by_key.items()}
    cand = {k: measure.candidate_pdf(tool_dir, first[r['base'], r['next']], a.tool) for k, r in by_key.items()}
    keys = sorted(k for k in raw['rows'] if stamp_src[k].is_file() and cand[k].is_file())
    if a.sample:
        keys = sorted(random.Random(a.seed).sample(keys, min(a.sample, len(keys))))
    print(f'{a.tool}: {len(keys)} compares with an Apryse stamp source; backend {kernels.backend_id()}', flush=True)

    rows: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for i in range(0, len(keys), a.chunk):
        part = keys[i:i + a.chunk]
        with tempfile.TemporaryDirectory(prefix=f'stamp-{a.tool}.') as tmp:
            orc, cd, work = Path(tmp) / 'oracle', Path(tmp) / 'candidate', Path(tmp) / 'work'
            for d in (orc, cd, work):
                d.mkdir()
            for k in part:
                try:
                    apryse_stamp.apply_word_stamp(oracle[k][0], stamp_src[k], orc / f'{k}.pdf')
                    dst = cd / f'{k}_{a.tool}.pdf'
                    if a.tool == 'apryse':
                        dst.symlink_to(cand[k].resolve())
                    else:
                        apryse_stamp.apply_word_stamp(cand[k], stamp_src[k], dst)
                except Exception as exc:  # a PDF without the stamp, a broken PDF
                    errors[k] = f'{type(exc).__name__}: {exc}'
                    (orc / f'{k}.pdf').unlink(missing_ok=True)
                    (cd / f'{k}_{a.tool}.pdf').unlink(missing_ok=True)
            got = pipeline.score_folders_full(orc, cd, work, candidate_tool=a.tool, jobs=a.jobs)
        for k, v in got.items():
            r = measure._scalars(v)
            r['raw_overall_score'] = raw['rows'][k]['overall_score']
            r['oracle'] = oracle[k][1]
            rows[k] = r
        print(f'{a.tool}: {len(rows)} scored, {len(errors)} not stamped, {len(keys) - i - len(part)} to go', flush=True)

    summary = measure._stats(list(rows.values()), len(keys))
    deltas = [r['overall_score'] - r['raw_overall_score'] for r in rows.values()]
    summary['delta_vs_raw'] = {
        'mean': sum(deltas) / len(deltas) if deltas else None,
        'abs_gt_5': sum(abs(d) > 5 for d in deltas),
        'min': min(deltas, default=None), 'max': max(deltas, default=None),
    }
    summary['scorer_backend'] = kernels.backend_id()
    summary['fresh_dir'] = str(a.fresh)
    summary['sample'] = {'n': a.sample, 'seed': a.seed} if a.sample else None
    summary['label'] = ('stamp-matched normalisation (Apryse demo watermark on the oracle too); '
                        'NOT the record: scores_apryse.json is')
    suffix = f'_sample{a.sample}_seed{a.seed}' if a.sample else ''
    out = HERE / f'scores_{a.tool}_stamp_matched{suffix}.json'
    out.write_text(json.dumps({'summary': summary, 'errors': errors, 'rows': rows}, indent=1, sort_keys=True))
    o = summary['overall']
    print(f'{a.tool} stamp-matched: {summary["scored"]} scored, mean {o.get("mean", 0):.2f}, median '
          f'{o.get("median", 0):.2f}; delta vs raw mean {summary["delta_vs_raw"]["mean"]:+.3f}, '
          f'|delta|>5: {summary["delta_vs_raw"]["abs_gt_5"]} -> {out}', flush=True)


if __name__ == '__main__':
    os.environ.setdefault('BENCH_DEVICE', 'mps')
    kernels.reset()
    main()
