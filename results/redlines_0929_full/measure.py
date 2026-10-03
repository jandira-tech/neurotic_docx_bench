"""Score each tool's Word-rendered redlines against Word's own compares.

    uv run python results/redlines_0929_full/measure.py jubarte-rust docxodus [superdoc]
    uv run python results/redlines_0929_full/measure.py --fresh ~/temp/T/compare_regen/out --device mps jubarte-rust

For every row of ``pool_pairs.csv`` the candidate is the tool's redline of that row's pair
(``<tool>/pdf_by_word/<first key of the pair>_<tool>.pdf``), scored against the row's own
Word compare (``oracle_pdf/<key>.pdf``) through ``pipeline.score_folders_full``. Rasters
live in a temporary folder deleted before the next tool starts. Writes
``scores_<tool>.json``: a summary (overall and per compare state) and one row per compare.

``--fresh DIR`` replaces the oracle of every compare Word made again: ``DIR/<id>__vs__<id>.pdf``
(``scripts/word_redline.py`` output over the ``compare_regen`` A/B folders, one file per
compare id) stands in for ``oracle_pdf/<key>.pdf``. Each row records which oracle it used,
and the summary counts both. ``--regen-list`` names the ids meant to be fresh; one without a
fresh PDF keeps its old oracle and is listed under ``fresh_missing``. ``--device`` sets the
scorer kernels (``kernels.device_env``); ``--sample N --seed S`` scores a stratified sample
(``stratified``) into ``scores_<tool>_sampleN_seedS.json`` and lists it in ``sampleN_seedS.csv``;
``--sample-csv FILE`` scores exactly the keys of a saved sample (so every tool is scored on the
same compares) into ``scores_<tool>_<FILE stem>.json`` and lists its PDFs in ``<FILE stem>_<tool>.csv``;
``--jobs`` the scoring processes (every core by default). Scoring runs in ``--chunk`` batches; after
each, the rows so far are saved to ``scores_<tool>[suffix].partial.json``, a rerun of the same
command resumes from it, and it is removed once the final JSON is written. A rerun after a finished
run reuses that JSON's rows and scores only candidate PDFs that are new (``_resume``).
``--cand-dir DIR`` reads the candidates from ``DIR`` instead of ``<tool>/pdf_by_word`` (same file
names), e.g. PDFs a running Word export has made but not delivered yet. Runs writing the same
``scores_<tool>[suffix].json`` hold ``.scores_<tool>[suffix].lock``: a second one waits, then resumes.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import json
import os
import random
import statistics
import tempfile
from pathlib import Path

from neurotic_docx_bench import kernels, pipeline

HERE = Path(__file__).parent


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scalars(row: dict) -> dict:
    return {k: v for k, v in row.items() if isinstance(v, (int, float, str, bool)) or v is None}


def _stats(rows: list[dict], expected: int) -> dict:
    overall = [pipeline.overall_from_result(r) for r in rows]
    ink = [r['ink_jaccard'] for r in rows if r.get('ink_jaccard') is not None]
    out = {'pairs': expected, 'scored': len(rows), 'missing': expected - len(rows)}
    for name, xs in (('overall', overall), ('ink_jaccard', ink)):
        out[name] = {'n': len(xs)} | ({'mean': statistics.fmean(xs), 'median': statistics.median(xs)} if xs else {})
    if overall:
        out['overall'] |= {'exact_100': sum(x >= 100 for x in overall), 'at_least_90': sum(x >= 90 for x in overall),
                           'below_50': sum(x < 50 for x in overall)}
    # intent to treat: a compare with no candidate PDF is a failure and scores zero
    itt = overall + [0.0] * out['missing']
    if itt:
        out['overall_itt'] = {'n': len(itt), 'mean': statistics.fmean(itt), 'median': statistics.median(itt),
                              'at_least_90': sum(x >= 90 for x in itt), 'below_50': sum(x < 50 for x in itt)}
    return out


def _still_current(row: dict, orc_pdf: Path, cand_pdf: Path) -> bool:
    """A resumed row stands only for the two files it was scored from.

    A row from before the hashes were recorded cannot be checked and is kept.
    """
    want = (row.get('oracle_sha256'), row.get('candidate_sha256'))
    if want == (None, None):
        return True
    return cand_pdf.is_file() and want == (_sha(orc_pdf), _sha(cand_pdf))


def oracles(pool: list[dict], fresh: Path | None) -> dict[str, tuple[Path, str]]:
    """Each compare key's oracle PDF and where it came from (``fresh`` or ``corpus``)."""
    out = {}
    for r in pool:
        new = fresh / f'{r["id"]}__vs__{r["id"]}.pdf' if fresh else None
        if new is not None and new.is_file():
            out[r['key']] = (new.resolve(), 'fresh')
        else:
            out[r['key']] = ((HERE / 'oracle_pdf' / f'{r["key"]}.pdf').resolve(), 'corpus')
    return out


def stratified(pool: list[dict], kind: dict[str, str], n: int, seed: int) -> list[dict]:
    """``n`` compares spread over compare state x corpus set x oracle source.

    Each stratum gets its share of ``n`` by largest remainder, and at least one compare
    while ``n`` covers every stratum. Within a stratum the pick is a seeded shuffle that
    takes one compare per (base, next) pair, so a pair Word compared several times is
    not scored twice; a stratum that runs out of pairs leaves its places to the rest.
    """
    rng = random.Random(seed)
    strata: dict[tuple, list[dict]] = {}
    for r in sorted(pool, key=lambda r: r['key']):
        strata.setdefault((r['state'], r['sets'], kind[r['key']]), []).append(r)
    for rows in strata.values():
        rng.shuffle(rows)
    quota = {k: n * len(v) / len(pool) for k, v in strata.items()}
    take = {k: int(q) for k, q in quota.items()}
    if n >= len(strata):
        take = {k: max(1, t) for k, t in take.items()}
    for k in sorted(quota, key=lambda k: quota[k] - int(quota[k]), reverse=True):
        if sum(take.values()) >= n:
            break
        take[k] += 1
    chosen, pairs = [], set()
    rest = []
    for k in sorted(strata):
        got = 0
        for r in strata[k]:
            pair = (r['base'], r['next'])
            if got < take[k] and pair not in pairs:
                chosen.append(r)
                pairs.add(pair)
                got += 1
            else:
                rest.append(r)
    rng.shuffle(rest)
    for r in rest:
        if len(chosen) >= n:
            break
        if (r['base'], r['next']) not in pairs:
            chosen.append(r)
            pairs.add((r['base'], r['next']))
    return sorted(chosen[:n], key=lambda r: r['key'])


def _write_listing(path: Path, pool: list[dict], oracle: dict, cand: dict[str, Path]) -> None:
    """One row per sampled compare: its oracle and candidate PDF with their sha256 (blank when absent)."""
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'id', 'state', 'sets', 'oracle', 'oracle_pdf', 'oracle_sha256', 'candidate_pdf',
                    'candidate_sha256'])
        for r in pool:
            orc_pdf, cand_pdf = oracle[r['key']][0], cand[r['key']]
            w.writerow([r['key'], r['id'], r['state'], r['sets'], oracle[r['key']][1], orc_pdf, _sha(orc_pdf),
                        cand_pdf.resolve() if cand_pdf.is_file() else '', _sha(cand_pdf) if cand_pdf.is_file() else ''])


def _resume(partial: Path, out: Path, fresh: Path | None) -> dict[str, dict]:
    """Rows already scored for this output: a killed run's ``partial``, else the last finished ``out``.

    Either must have been scored against the same oracles (``--fresh``). Rerunning after more
    candidate PDFs arrive therefore scores only the new ones; delete both files to start over.
    """
    for path in (partial, out):
        if not path.is_file():
            continue
        saved = json.loads(path.read_text())
        used = saved.get('fresh_dir', saved.get('summary', {}).get('fresh_dir'))
        if used != (str(fresh) if fresh else None):
            raise SystemExit(f'{path} was scored with --fresh {used}; delete it or match it')
        return saved['rows']
    return {}


def measure(tool: str, fresh: Path | None, regen: set[str], jobs: int, sample: int = 0, seed: int = 0,
            sample_csv: Path | None = None, chunk: int = 250, cand_dir: Path | None = None) -> None:
    pool = list(csv.DictReader(open(HERE / 'pool_pairs.csv')))
    first = {(r['base'], r['next']): r['key'] for r in reversed(list(csv.DictReader(open(HERE / 'gen_pairs.csv'))))}
    oracle = oracles(pool, fresh)
    src = cand_dir or HERE / tool / 'pdf_by_word'
    cands = {r['key']: src / f'{first[(r["base"], r["next"])]}_{tool}.pdf' for r in pool}
    suffix = ''
    if sample_csv:
        keys = {r['key'] for r in csv.DictReader(open(sample_csv))}
        pool = [r for r in pool if r['key'] in keys]
        if len(pool) != len(keys):
            raise SystemExit(f'{sample_csv}: {len(keys) - len(pool)} keys are not in pool_pairs.csv')
        suffix = f'_{sample_csv.stem}'
        _write_listing(HERE / f'{sample_csv.stem}_{tool}.csv', pool, oracle, cands)
    elif sample:
        scoreable = [r for r in pool if cands[r['key']].is_file()]
        pool = stratified(scoreable, {k: v[1] for k, v in oracle.items()}, sample, seed)
        suffix = f'_sample{sample}_seed{seed}'
        _write_listing(HERE / f'sample{sample}_seed{seed}.csv', pool, oracle, cands)
    out = HERE / f'scores_{tool}{suffix}.json'
    partial = out.with_suffix('.partial.json')
    lock = open(HERE / f'.{out.stem}.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f'{tool}: another run holds {out.name}; waiting', flush=True)
        fcntl.flock(lock, fcntl.LOCK_EX)
    rows = {k: v for k, v in _resume(partial, out, fresh).items() if k in {r['key'] for r in pool}}
    stale = sorted(k for k, v in rows.items() if not _still_current(v, oracle[k][0], cands[k]))
    for k in stale:
        del rows[k]
    todo = [r for r in pool if r['key'] not in rows and cands[r['key']].is_file()]
    if rows or stale:
        unhashed = sum('oracle_sha256' not in v for v in rows.values())
        print(f'{tool}: resuming: {len(rows)} already scored ({unhashed} without recorded file hashes), '
              f'{len(stale)} dropped because their oracle or candidate PDF changed, {len(todo)} to go', flush=True)
    for i in range(0, len(todo), chunk):
        part = todo[i:i + chunk]
        with tempfile.TemporaryDirectory(prefix=f'measure-{tool}.') as tmp:
            orc, cand, work = Path(tmp) / 'oracle', Path(tmp) / 'candidate', Path(tmp) / 'work'
            for d in (orc, cand, work):
                d.mkdir()
            for r in part:
                (orc / f'{r["key"]}.pdf').symlink_to(oracle[r['key']][0])
                (cand / f'{r["key"]}_{tool}.pdf').symlink_to(cands[r['key']].resolve())
            got = pipeline.score_folders_full(orc, cand, work, candidate_tool=tool, jobs=jobs)
        rows |= {k: _scalars(v) | {'oracle': oracle[k][1], 'oracle_sha256': _sha(oracle[k][0]),
                                   'candidate_sha256': _sha(cands[k])} for k, v in got.items()}
        partial.write_text(json.dumps({'fresh_dir': str(fresh) if fresh else None, 'rows': rows}, sort_keys=True))
        print(f'{tool}: {len(rows)} scored, {len(todo) - i - len(part)} to go -> {partial.name}', flush=True)
    state = {r['key']: r['state'] for r in pool}
    kind = {r['key']: oracle[r['key']][1] for r in pool}
    summary = _stats(list(rows.values()), len(pool))
    summary['by_state'] = {
        s: _stats([v for k, v in rows.items() if state.get(k) == s], sum(st == s for st in state.values()))
        for s in sorted(set(state.values()))
    }
    summary['by_oracle'] = {
        o: _stats([v for v in rows.values() if v['oracle'] == o], sum(x == o for x in kind.values()))
        for o in ('fresh', 'corpus')
    }
    summary['fresh_dir'] = str(fresh) if fresh else None
    summary['sample'] = ({'csv': sample_csv.name} if sample_csv else {'n': sample, 'seed': seed} if sample else None)
    summary['scorer_backend'] = kernels.backend_id()
    missing = sorted(set(state) - set(rows))
    fresh_missing = sorted(r['id'] for r in pool if r['id'] in regen and oracle[r['key']][1] != 'fresh')
    out.write_text(json.dumps({'summary': summary, 'missing': missing, 'fresh_missing': fresh_missing, 'rows': rows},
                              indent=1, sort_keys=True))
    partial.unlink(missing_ok=True)
    o, itt = summary['overall'], summary.get('overall_itt', {})
    zeros = (f' (with the {summary["missing"]} missing as 0: mean {itt.get("mean", 0):.2f}, '
             f'median {itt.get("median", 0):.2f})' if summary['missing'] else '')
    print(f'{tool}: {summary["scored"]}/{summary["pairs"]} scored, mean {o.get("mean", 0):.2f}, '
          f'median {o.get("median", 0):.2f}, >=90: {o.get("at_least_90", 0)}{zeros}; '
          f'fresh oracles {summary["by_oracle"]["fresh"]["pairs"]}, meant fresh but old {len(fresh_missing)}; '
          f'{summary["scorer_backend"]} -> {out}')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('tools', nargs='+')
    ap.add_argument('--fresh', type=Path, help='folder of <id>__vs__<id>.pdf Word compares made again')
    ap.add_argument('--regen-list', type=Path, help='CSV with an id column: the compares meant to be fresh')
    ap.add_argument('--device', choices=kernels.DEVICE_SPECS, help='scorer kernels (cpu, mps, cuda, auto)')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 12, help='scoring worker processes (default: every core)')
    ap.add_argument('--sample', type=int, default=0, help='score a stratified sample of this many compares')
    ap.add_argument('--seed', type=int, default=0, help='seed of --sample')
    ap.add_argument('--sample-csv', type=Path,
                    help='score exactly the compares listed in this CSV (a key column), e.g. sample500_seed0.csv')
    ap.add_argument('--chunk', type=int, default=250,
                    help='compares scored per batch; scores_<tool>*.partial.json is saved after each, and a rerun resumes from it')
    ap.add_argument('--cand-dir', type=Path, help='read <first key>_<tool>.pdf candidates from here, not <tool>/pdf_by_word')
    ap.add_argument('--dry-run', action='store_true', help='print the oracle counts and stop')
    a = ap.parse_args()
    regen = {r['id'] for r in csv.DictReader(open(a.regen_list))} if a.regen_list else set()
    if a.dry_run:
        pool = list(csv.DictReader(open(HERE / 'pool_pairs.csv')))
        got = oracles(pool, a.fresh)
        fresh = sum(v[1] == 'fresh' for v in got.values())
        print(f'pool {len(pool)}; fresh {fresh}; corpus {len(pool) - fresh}; '
              f'regen ids in pool {sum(r["id"] in regen for r in pool)}; '
              f'regen without fresh {sum(r["id"] in regen and got[r["key"]][1] != "fresh" for r in pool)}; '
              f'corpus oracles missing {sum(not v[0].is_file() for v in got.values())}')
        return
    with kernels.device_env(a.device):
        for t in a.tools:
            measure(t, a.fresh, regen, a.jobs, a.sample, a.seed, a.sample_csv, a.chunk, a.cand_dir)


if __name__ == '__main__':
    main()
