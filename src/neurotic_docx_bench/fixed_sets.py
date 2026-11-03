"""The fixed evaluation sets convert_860 and redline_600 (plan 7.1, issue #128).

Two document sets that never move again, so every future run — jubarte
releases, the live bench, the sites' comparisons — scores the same fixtures
and the numbers stay comparable across versions:

* ``convert_860`` — every row of ``results/site_fixtures_860.csv`` (the 860
  conversion fixtures the site shows), plus each DOCX's and each Word PDF's
  sha256: the ``sample_conversion`` layout of ``jubarte_release_info``
  (``state, stem, docx, word_pdf`` + shas) with the source CSV's own columns
  (``pages``, ``jubarte_score``) riding along and a ``source`` column.
* ``redline_600`` — ALL jubarte.pro redline cases (``cases-redline.json``,
  the 234, ``origin=jubarte_pro``) plus pairs drawn from the release sample
  CSV (``origin=sample_0.17.0``) with ``draw_balanced``: scarce states (every
  state but tracking_without_comments) go in whole and the plentiful state is
  spread over document families. Sample rows whose pair a jubarte.pro row
  already holds — 42 by compare id, 49 by (base, next) documents — count
  among the 234, never among the drawn. Exactly 600 distinct pairs, seeded
  (20261103): the same inputs give byte-identical CSVs.

Every input a row names is hashed where the builder finds it — the bench
root first (``--bench-root``; the worktree holds no corpus, the canonical
checkout holds all of it), then, for what is missing there, the two hub
datasets through ``HfApi.get_paths_info`` (the LFS sha256): the corpus tree
on ``arthrod/neurotic_docx_bench-fixtures`` (``corpus/word/...`` is the
dataset's ``word/...``) and the 0929 oracle PDFs on
``arthrod/neurotic_docx_bench`` (``results/redlines_0929_full/...`` is its
``outputs/redlines_0929_full/...``). A row that needed the hub says
``source=hf``. A redline pair whose oracle PDF exists nowhere is excluded,
named in ``sets.json`` under ``excluded`` with the reason, and its slot is
redrawn from the sample pool so the total stays 600. Shas the sample CSV
already records are kept and cross-checked: a mismatch (the corpus drifted)
refuses the build.

No comments inside the CSVs — the provenance lives in ``sets.json``:
``set_version``, ``seed``, every input file's path and sha256, the row count
by state of both sets, the origin counts and the excluded pairs.

    uv run bench sets build --bench-root ~/temp/T/neurotic_docx_bench
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from csv import DictWriter
from pathlib import Path

from neurotic_docx_bench import hub
from neurotic_docx_bench.jubarte_release_info import (
    CONVERSION_SHA_FIELDS,
    REDLINE_HEADER,
    draw_balanced,
    read_csv,
)

SET_VERSION = '2026-11-03.1'
SEED = 20261103
REDLINE_TOTAL = 600
CONVERT_NAME = 'convert_860'
REDLINE_NAME = 'redline_600'
CONVERT_CSV = f'{CONVERT_NAME}.csv'
REDLINE_CSV = f'{REDLINE_NAME}.csv'
SETS_JSON = 'sets.json'
ORIGIN_PRO = 'jubarte_pro'
ORIGIN_SAMPLE = 'sample_0.17.0'
ORACLE_DIR = Path('results/redlines_0929_full/oracle_pdf')  # relative to the bench root
CASES_PATH = Path(
    '~/temp/T/1_jubarte-redlines/jubarte-app/jubarte-site/public/data/cases-redline.json'
).expanduser()
SAMPLE_GLOB = 'release_*_evidence/release_info/sample_redline_*.csv'

CONVERT_HEADER = [*CONVERSION_SHA_FIELDS, 'source', 'pages', 'jubarte_score']
REDLINE_SET_HEADER = [*REDLINE_HEADER, 'oracle_sha256', 'origin', 'source']
# row path column -> the sha column(s) it fills (the oracle fills both spellings);
# only the columns a row actually has are filled, so the same table serves both sets
_SHA_COLUMNS = {
    'base': ('base_sha256',),
    'next': ('next_sha256',),
    'docx': ('docx_sha256',),
    'pdf': ('pdf_sha256',),
    'word_pdf': ('word_pdf_sha256',),
    'oracle_pdf': ('oracle_pdf_sha256', 'oracle_sha256'),
}
_CASE_ID = re.compile(r'^r-([0-9a-f]{10})$')
_HF_CHUNK = 200  # paths per get_paths_info call

HubLookup = Callable[[str, list[str]], dict[str, str]]
Sha = tuple[str, str]  # (sha256, 'local' | 'hf')


def _sha_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    with path.open('rb') as fh:
        return hashlib.file_digest(fh, 'sha256').hexdigest()


def _write_csv(path: Path, fieldnames: list[str], rows: Sequence[dict]) -> None:
    """write_csv with LF ends — how this repo's results/ CSVs are stored (their
    working copy matches the committed bytes; the CRLF release samples that need
    their exact bytes are the -text exceptions in .gitattributes)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as fh:
        writer = DictWriter(fh, fieldnames=fieldnames, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def newest_sample_csv(root: Path = Path('.')) -> Path:
    """The newest release evidence sample CSV: ``release_<v>_evidence/release_info/…``."""
    found = sorted(root.glob('results/' + SAMPLE_GLOB))
    if not found:
        raise RuntimeError(f'no results/{SAMPLE_GLOB} — pass --sample-csv')

    def version(path: Path) -> tuple[int, ...]:
        try:
            return tuple(int(part) for part in path.parent.parent.name
                         .removeprefix('release_').removesuffix('_evidence').split('.'))
        except ValueError:
            return ()

    return max(found, key=lambda p: (version(p), p.name))


def load_case_ids(path: Path) -> list[str]:
    """The jubarte.pro case pair ids: ``r-<10hex>`` → the 10 hex (gen_pairs ``id``)."""
    cases = json.loads(path.read_text())['cases']
    ids: list[str] = []
    for case in cases:
        match = _CASE_ID.match(case['id'])
        if match is None:
            raise RuntimeError(f'{path}: case id {case["id"]!r} is not r-<10 hex>')
        if match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def _with_docx(rel: str) -> str:
    return rel if rel.endswith('.docx') else f'{rel}.docx'


def _side(path: str) -> str:
    """One side of a pair in gen_pairs' form: relative to corpus/word, no extension."""
    stripped = path.removeprefix('corpus/word/')
    return stripped[:-5] if stripped.endswith('.docx') else stripped


def pair_of(row: Mapping) -> tuple[str, str]:
    """The pair a row names — its two documents, whichever spelling the row uses."""
    return _side(row['base']), _side(row['next'])


def pro_rows(gen_pairs: Sequence[dict], case_ids: Sequence[str]) -> list[dict]:
    """The jubarte.pro pairs as sample-shaped rows: gen_pairs rows in the sample CSV's paths."""
    by_id = {row['id']: row for row in gen_pairs}
    unknown = [id_ for id_ in case_ids if id_ not in by_id]
    if unknown:
        raise RuntimeError(f'{len(unknown)} case ids are not in gen_pairs.csv (first: {unknown[0]})')
    rows = []
    for id_ in case_ids:
        gen = by_id[id_]
        rows.append({
            'key': gen['key'],
            'base': f'corpus/word/{_with_docx(gen["base"])}',
            'next': f'corpus/word/{_with_docx(gen["next"])}',
            'docx': f'corpus/word/{gen["docx"]}',
            'pdf': f'corpus/word/{gen["pdf"]}',
            'state': gen['state'], 'id': gen['id'], 'sets': gen['sets'],
            'oracle': 'corpus',
            'oracle_pdf': (ORACLE_DIR / f'{gen["key"]}.pdf').as_posix(),
        })
    return rows


def _check_pool(sample: Sequence[dict], pool: Sequence[dict], listing: Path) -> None:
    """Every sample key must be a pool key (the adopt rule of jubarte_release_info)."""
    keys = {row['key'] for row in pool}
    unknown = [row['key'] for row in sample if row['key'] not in keys]
    if unknown:
        raise RuntimeError(f'{listing}: {len(unknown)} sample keys are not in the pool '
                           f'(first: {unknown[0]})')


def hub_shas(api, repo_id: str, paths: list[str]) -> dict[str, str]:
    """The LFS sha256 of every path the hub has (absent paths simply miss)."""
    out: dict[str, str] = {}
    for start in range(0, len(paths), _HF_CHUNK):
        for info in api.get_paths_info(repo_id, paths[start:start + _HF_CHUNK], repo_type=hub.REPO_TYPE):
            sha = getattr(getattr(info, 'lfs', None), 'sha256', None)
            if sha:
                out[getattr(info, 'path', None) or info.rfilename] = sha
    return out


class Resolver:
    """sha256 of every file a row names: the bench root's disk first, the hub second.

    ``hf(repo_id, hub_paths) -> {hub path: sha256}`` is injected so tests need
    no network; ``None`` means offline (a miss is a miss). One hub call per
    dataset per ``resolve_all``, over that call's misses only; answers are
    cached across calls.
    """

    def __init__(self, bench_root: Path, hf: HubLookup | None = None):
        self.bench_root = Path(bench_root)
        self.hf = hf
        self.hf_calls: list[tuple[str, list[str]]] = []
        self._hub: dict[str, Sha | None] = {}

    @staticmethod
    def hub_path(rel: str) -> tuple[str, str] | None:
        """(repo, path in the repo) a bench-root path maps to, or None when no dataset holds it."""
        if rel.startswith('corpus/word/'):
            return hub.FIXTURES_REPO, rel.removeprefix('corpus/')
        if rel.startswith('results/redlines_0929_full/'):
            return hub.RESULTS_REPO, f'outputs/{rel.removeprefix("results/")}'
        return None

    def resolve_all(self, rels: Iterable[str]) -> dict[str, Sha | None]:
        """(sha256, source) of every path: a local hash, the hub's, or None when it is nowhere."""
        out: dict[str, Sha | None] = {}
        ask: dict[str, dict[str, str]] = {}  # repo -> {hub path: bench-root path}
        for rel in sorted(set(rels)):
            digest = _sha_file(self.bench_root / rel)
            if digest:
                out[rel] = (digest, 'local')
            elif rel in self._hub:
                out[rel] = self._hub[rel]
            elif (where := self.hub_path(rel)) is not None and self.hf is not None:
                repo, in_repo = where
                ask.setdefault(repo, {})[in_repo] = rel
            else:
                out[rel] = None
        for repo, mapping in sorted(ask.items()):
            paths = sorted(mapping)
            self.hf_calls.append((repo, paths))
            found = self.hf(repo, paths) if self.hf else {}
            for in_repo, rel in sorted(mapping.items()):
                digest = found.get(in_repo)
                self._hub[rel] = (digest, 'hf') if digest else None
                out[rel] = self._hub[rel]
        return out


def _fill_shas(row: dict, resolved: Mapping[str, Sha | None], *, strict: bool) -> None:
    """Write the sha columns of one shaped row; a recorded sha must agree with the file.

    ``strict`` rows (jubarte_pro pairs, nothing recorded) must find every file
    somewhere; a sample row may keep a sha its CSV records when the file is
    nowhere on disk. The row's ``source`` is ``hf`` when any input needed the
    hub, else ``local``.
    """
    source = 'local'
    for rel_col, sha_cols in _SHA_COLUMNS.items():
        if rel_col not in row:
            continue
        rel = row[rel_col]
        got = resolved.get(rel)
        if got is None:
            if strict or not any(row.get(col) for col in sha_cols):
                raise RuntimeError(f'{row.get("key", row.get("stem", "?"))}: {rel} is neither '
                                   f'in the bench root nor on the hub')
            continue  # nowhere to hash; the sample CSV's recorded sha stands
        digest, where = got
        if where == 'hf':
            source = 'hf'
        for col in sha_cols:
            if row.get(col) and row[col] != digest:
                raise RuntimeError(f'{row.get("key", row.get("stem", "?"))}: {rel} hashes to '
                                   f'{digest[:12]}… but {col} records {row[col][:12]}… — the inputs drifted')
            row[col] = digest
    row['source'] = source


def build_convert(site_rows: Sequence[dict], resolver: Resolver) -> list[dict]:
    """convert_860: every site row with both files' sha256, sorted by (state, stem)."""
    rows = []
    for site in site_rows:
        state, stem = site['state'], site['stem']
        if not stem.startswith(f'{state}__'):
            raise RuntimeError(f'{stem} is not {state}__<docx stem>')
        name = stem.split('__', 1)[1]
        rows.append({'state': state, 'stem': stem,
                     'docx': f'corpus/word/{state}/docx/{name}.docx',
                     'word_pdf': f'corpus/word/{state}/pdf/{name}.pdf',
                     'pages': site.get('pages', ''), 'jubarte_score': site.get('jubarte_score', '')})
    resolved = resolver.resolve_all([rel for row in rows for rel in (row['docx'], row['word_pdf'])])
    for row in rows:
        _fill_shas(row, resolved, strict=True)
    if len({row['stem'] for row in rows}) != len(rows):
        raise RuntimeError('site fixtures list a stem twice')
    return sorted(rows, key=lambda row: (row['state'], row['stem']))


def build_redline(pro: Sequence[dict], sample: Sequence[dict], total: int, seed: int,
                  resolver: Resolver) -> tuple[list[dict], list[dict]]:
    """redline_600's rows (sorted by pair id) and the excluded pairs.

    Every live jubarte.pro pair is in; the rest is drawn from the sample with
    ``draw_balanced`` (scarce states whole, the plentiful state spread over
    document families — no covered/first preference: every sample row's
    oracle is already known). A pair with no oracle anywhere — on either
    side — is excluded with the reason and replaced from the pool.
    """
    candidates = [(ORIGIN_PRO, row) for row in pro] + [(ORIGIN_SAMPLE, row) for row in sample]
    oracle = resolver.resolve_all({row['oracle_pdf'] for _, row in candidates})
    excluded = [{'set': REDLINE_NAME, 'origin': origin, 'key': row['key'], 'id': row['id'],
                 'reason': f'no oracle anywhere: {row["oracle_pdf"]}'}
                for origin, row in candidates if oracle[row['oracle_pdf']] is None]
    live_pro = [row for row in pro if oracle[row['oracle_pdf']] is not None]
    live_pairs = {pair_of(row) for row in live_pro}
    pool = [row for row in sample
            if oracle[row['oracle_pdf']] is not None and pair_of(row) not in live_pairs]
    want = total - len(live_pro)
    if want < 0:
        raise RuntimeError(f'{len(live_pro)} jubarte.pro pairs already exceed the {total} wanted')
    chosen = draw_balanced(pool, want, seed, covered=frozenset()) if want else []
    if len(live_pro) + len(chosen) != total:
        raise RuntimeError(f'only {len(live_pro) + len(chosen)} live pairs for {REDLINE_NAME}, want {total}')

    rows = [*(dict(row, origin=ORIGIN_PRO) for row in live_pro),
            *(dict(row, origin=ORIGIN_SAMPLE) for row in chosen)]
    resolved = resolver.resolve_all({rel for row in rows for rel in
                                     (row['base'], row['next'], row['docx'], row['pdf'], row['oracle_pdf'])})
    for row in rows:
        _fill_shas(row, resolved, strict=row['origin'] == ORIGIN_PRO)
    rows.sort(key=lambda row: row['id'])
    if len({row['id'] for row in rows}) != len(rows) or len({pair_of(row) for row in rows}) != len(rows):
        raise RuntimeError(f'{REDLINE_NAME} holds a pair or an id twice')
    return rows, excluded


def build(*, bench_root: Path = Path('.'), out: Path = Path('results/sets'),
          site_csv: Path = Path('results/site_fixtures_860.csv'),
          sample_csv: Path | None = None,
          gen_pairs_csv: Path = Path('results/redlines_0929_full/gen_pairs.csv'),
          pool_pairs_csv: Path = Path('results/redlines_0929_full/pool_pairs.csv'),
          cases_json: Path = CASES_PATH, total: int = REDLINE_TOTAL, seed: int = SEED,
          resolver: Resolver | None = None) -> dict:
    """Build both sets and sets.json; return the summary the CLI prints.

    The five input files are read from the working tree (they are tracked);
    the files the rows name are hashed under ``bench_root`` (the canonical
    checkout) with the hub as fallback.
    """
    sample_csv = Path(sample_csv) if sample_csv else newest_sample_csv()
    for name, path in (('site fixtures', site_csv), ('sample', sample_csv),
                       ('gen pairs', gen_pairs_csv), ('pool pairs', pool_pairs_csv),
                       ('cases', cases_json)):
        if not Path(path).is_file():
            raise RuntimeError(f'the {name} input is missing: {path}')
    if resolver is None:
        from huggingface_hub import HfApi

        api = HfApi()
        resolver = Resolver(bench_root, lambda repo, paths: hub_shas(api, repo, paths))

    site = read_csv(Path(site_csv))
    sample = read_csv(sample_csv)
    gen_pairs = read_csv(Path(gen_pairs_csv))
    _check_pool(sample, read_csv(Path(pool_pairs_csv)), Path(pool_pairs_csv))
    case_ids = load_case_ids(Path(cases_json))

    convert = build_convert(site, resolver)
    redline, excluded = build_redline(pro_rows(gen_pairs, case_ids), sample, total, seed, resolver)

    _write_csv(Path(out) / CONVERT_CSV, CONVERT_HEADER, convert)
    _write_csv(Path(out) / REDLINE_CSV, REDLINE_SET_HEADER, redline)
    sets = {
        'set_version': SET_VERSION,
        'seed': seed,
        'sources': [{'path': str(path), 'sha256': _sha_file(Path(path))}
                    for path in (site_csv, sample_csv, gen_pairs_csv, pool_pairs_csv, cases_json)],
        'counts': {CONVERT_NAME: dict(Counter(row['state'] for row in convert)),
                   REDLINE_NAME: dict(Counter(row['state'] for row in redline))},
        'totals': {CONVERT_NAME: len(convert), REDLINE_NAME: len(redline)},
        'origins': dict(Counter(row['origin'] for row in redline)),
        'excluded': excluded,
    }
    (Path(out) / SETS_JSON).write_text(json.dumps(sets, indent=2) + '\n')
    return {
        'out': Path(out),
        'convert_rows': len(convert),
        'redline_rows': len(redline),
        'counts': sets['counts'],
        'origins': sets['origins'],
        'excluded': excluded,
        'sample_csv': sample_csv,
        'hf_rows': {name: sum(1 for row in rows if row.get('source') == 'hf')
                    for name, rows in ((CONVERT_NAME, convert), (REDLINE_NAME, redline))},
    }
