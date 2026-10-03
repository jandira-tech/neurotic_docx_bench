"""Write a jubarte release's six release_info/ evidence files.

    uv run python -m neurotic_docx_bench.jubarte_release_info 0.11.3 --plan
    uv run python -m neurotic_docx_bench.jubarte_release_info 0.11.3 \
        --engine-dir ../jubarte-redlines --binary target/release/jubarte
    uv run python -m neurotic_docx_bench.jubarte_release_info 0.11.3 \
        --engine-dir ../jubarte-redlines            # the GitHub release binary
    scripts/jubarte_release_info.py 0.11.3 --plan   # the same app

The owner's flow, one scoring job at a time (``--only`` / ``--skip`` pick
among the stages, the order never changes). Everything the run makes goes to
``results/release_<version>_evidence/`` (the evidence folder), under names
that carry the version. Stage by owner step:

1. ``sample`` — the two ``--n``-item samples: drawn seeded and balanced by
   state with every scarce state's compares first, or adopted from lists
   that already exist (``--adopt-redline CSV``, ``--adopt-conversion FILE``).
   ``sample_redline_<v>.csv`` keeps every sampled pool key (pool columns);
   ``gen_pairs_sample.csv`` is the generator manifest, one row per (base,
   next) pair under the pair's first key; ``sample_conversion_<v>.csv`` is
   ``state,stem,docx,word_pdf`` and each file's sha256; ``sample_meta.json`` records how each was
   made. Every sample item must already have its Word PDF: the redline
   oracle the ``measure.py`` rule picks (the fresh compare in
   ``compare_regen`` when its file exists, else the corpus oracle) and the
   conversion DOCX's own ``<state>/pdf/<stem>.pdf``.
2. ``generate`` — redline the sample's pairs with the jubarte binary
   (``--binary``, a release candidate built from the release commit: the
   engine's release.sh requires these results before the version bump, so
   the candidate may still report the previous version; the GitHub release
   binary is the default afterwards). The Docxodus Word PDFs the sample
   lacks locally are fetched from the results dataset; Docxodus redlines
   only the pairs still missing.
3. ``export`` — the new redlines to PDF with Word: ``scripts/word_pdf.py``
   batch (``--do-not-close``), then one osascript per document
   (``--no-one-osascript``), ``--timeout 300``, the watchdog on each pass.
   An adopted lane needs neither stage: ``--skip export,generate``.
4. ``measure`` — ``measure.py --sample-csv`` scores the redline sample for
   jubarte, then for Docxodus (sequentially; one scoring job at a time).
5. ``convert`` — ``bench docx-to-pdf --converter … --origin list`` (one
   ``--files-list`` per fixture) converts — and thereby scores — the
   conversion sample with jubarte; LibreOffice converts only the fixtures
   that lack a render in ``results/soffice_26.8.0.3_work/candidate``
   (``scripts/convert_candidates.py``).
6. ``score`` — the sample's LibreOffice renders are staged as ``<docx
   stem>.pdf`` (the name ``--score-only`` matches a fixture by) and scored
   against the same Word PDFs.
7. ``write`` — the six files into ``--engine-dir/release_info/``
   (``sample_redline_<v>_<mm-dd-yy_hh-mm>.csv``, ``sample_conversion_…csv``,
   ``results_redline_…json``, ``results_conversion_…json``,
   ``website_data_…jsonl``, ``app_data_…jsonl``), one stamp for all six,
   that version's older stamps deleted. The two CSVs are built here, from
   the sample lists and the files then on disk: every path relative to the
   bench root with its sha256 beside it, a file that does not exist an
   empty path with an empty sha. The engine's
   ``scripts/check_release_info.py`` gates the release on them.

The ``install`` stage resolves the binary first: ``--binary PATH`` must run
(whatever version it reports is recorded as ``candidate_reports``); without
it the GitHub release's own binary is downloaded, sha256-checked
(``jubarte_release.github_download``) and must report the release version.

Every subprocess goes through ``run``, the watchdog through ``spawn`` and
the results dataset through ``hub``, so the plan and the executor are tested
without Word, network or git (the Step/plan/execute structure is
``jubarte_bench_release``'s).
"""

from __future__ import annotations

import csv
from collections import Counter
import dataclasses
import filecmp
import hashlib
import json
import os
import random
import re
import shutil
import statistics
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import typer

from neurotic_docx_bench import jubarte_release, pipeline, release
from neurotic_docx_bench.jubarte_bench_release import (
    COMPARE_REGEN,
    RUN_DIR,
    Release,
    Step,
    execute,
)

STAGES = ('install', 'sample', 'generate', 'export', 'measure', 'convert', 'score', 'write')
FILL_STATE = 'tracking_without_comments'  # the plentiful state the redline sample fills with
CONVERSION_QUOTAS = {  # of 600: every with_comments_clean fixture the corpus has, the rest to comments + tracking
    'clean': 150,
    'tracking_without_comments': 150,
    'with_comments_clean': 117,
    'with_comments_tracking': 183,
}
DEFAULT_SEED = 20261003
DEFAULT_N = 600
DEFAULT_JOBS = 4
DEFAULT_CONVERT_WORKERS = 3
SOFFICE_WORK = Path('results/soffice_26.8.0.3_work')
SCORE_ONLY_TOOL = 'candidates'  # bench docx-to-pdf --score-only without --tool
SOFFICE_VERSION = 'LibreOffice ' + SOFFICE_WORK.name.removeprefix('soffice_').removesuffix('_work')
# generate-native-redlines.ts finds bin/Release/net8.0/docxodus-inproc under it
DOCXODUS_DIST = Path('src/neurotic_docx_bench/utils/docxodus/docxodus-csharp-inproc')
HUB_REPO = 'arthrod/neurotic_docx_bench'
HUB_DOCXODUS = f'outputs/{RUN_DIR.name}/docxodus/pdf_by_word'

REDLINE_HEADER = [
    'key', 'base', 'base_sha256', 'next', 'next_sha256',
    'docx', 'docx_sha256', 'pdf', 'pdf_sha256',
    'state', 'id', 'sets', 'oracle',
    'oracle_pdf', 'oracle_pdf_sha256',
    'docxodus_pdf', 'docxodus_pdf_sha256',
    'jubarte_docx', 'jubarte_docx_sha256',
    'jubarte_pdf', 'jubarte_pdf_sha256',
]
CONVERSION_HEADER = [
    'state', 'stem',
    'docx', 'docx_sha256', 'word_pdf', 'word_pdf_sha256',
    'jubarte_pdf', 'jubarte_pdf_sha256',
    'soffice_pdf', 'soffice_pdf_sha256',
]
GEN_FIELDS = ['key', 'base', 'next', 'docx', 'pdf', 'state', 'id', 'sets']
CONVERSION_FIELDS = ['state', 'stem', 'docx', 'word_pdf']
# the evidence lists as written: every file a row names, with its sha256 (appended, so a
# reader of the plain columns is undisturbed)
GEN_SHA_FIELDS = [*GEN_FIELDS, 'base_sha256', 'next_sha256', 'docx_sha256', 'pdf_sha256']
CONVERSION_SHA_FIELDS = [*CONVERSION_FIELDS, 'docx_sha256', 'word_pdf_sha256']
_FIXTURE = re.compile(r'^corpus/word/([^/]+)/docx/([^/]+)\.docx$')


# ------------------------------------------------------------------ names and paths

def evidence_dir(version: str) -> Path:
    """Where the run's own artifacts go (relative to the bench root)."""
    return Path(f'results/release_{version}_evidence')


def redline_list(version: str) -> Path:
    """The redline sample ``measure.py --sample-csv`` reads; its stem names the score files."""
    return evidence_dir(version) / f'sample_redline_{version}.csv'


def conversion_list(version: str) -> Path:
    return evidence_dir(version) / f'sample_conversion_{version}.csv'


def scores_json(tool: str, version: str) -> Path:
    """What ``measure.py --sample-csv <redline_list> <tool>`` writes."""
    return RUN_DIR / f'scores_{tool}_{redline_list(version).stem}.json'


def conversion_report(tool: str, version: str) -> Path:
    return evidence_dir(version) / f'docx_to_pdf_{tool}_{version}_sample.json'


def stamp_now(now: datetime | None = None) -> str:
    """The owner's ``mm-dd-yy_hh-mm`` (10-03-26_16-51) of the write time."""
    return (now or datetime.now()).strftime('%m-%d-%y_%H-%M')


def facts_stamp(u: uuid.UUID) -> str:
    """The UTC time a uuidv7 carries in its first 48 bits, as facts.py writes it."""
    when = datetime.fromtimestamp((u.int >> 80) / 1000, UTC)
    return when.isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def rel_path(path: Path, root: Path) -> str:
    """``path`` as every CSV and JSON names it: relative to the bench root."""
    return Path(os.path.relpath(path, root)).as_posix()


def _sha(path: Path) -> str:
    if not path.is_file():
        return ''
    with path.open('rb') as fh:
        return hashlib.file_digest(fh, 'sha256').hexdigest()


class _Cells:
    """A path cell and its sha256 cell: bench-root-relative, hashed once per file;
    a file that is not on disk is an empty path with an empty sha."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self._shas: dict[Path, str] = {}

    def __call__(self, path: Path | None) -> list[str]:
        if path is None or not path.is_file():
            return ['', '']
        if path not in self._shas:
            self._shas[path] = _sha(path)
        return [rel_path(path, self.root), self._shas[path]]


def _by_lower(folder: Path) -> dict[str, Path]:
    """A folder's files by lower-cased name (report keys and file stems may differ in case)."""
    return {p.name.lower(): p for p in folder.iterdir()} if folder.is_dir() else {}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline='') as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fieldnames: list[str], rows: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def _listed(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


# ------------------------------------------------------------------ the samples

def first_keys(gen_pairs: Sequence[dict]) -> dict[tuple[str, str], str]:
    """(base, next) → the pair's first key in gen_pairs.csv (measure.py's rule)."""
    return {(r['base'], r['next']): r['key'] for r in reversed(list(gen_pairs))}


def oracle_for(row: dict, fresh: Path, root: Path) -> tuple[str, Path]:
    """measure.py ``oracles()``: the fresh compare when its file exists, else the corpus one."""
    new = fresh / f'{row["id"]}__vs__{row["id"]}.pdf'
    if new.is_file():
        return 'fresh', new
    return 'corpus', root / RUN_DIR / 'oracle_pdf' / f'{row["key"]}.pdf'


def without_oracle(rows: Sequence[dict], fresh: Path, root: Path) -> list[str]:
    """Keys of the compares that have no Word PDF at all."""
    return [r['key'] for r in rows if not oracle_for(r, fresh, root)[1].is_file()]


_STEM_ID = re.compile(r'^[0-9a-f]{10}_')
_HASH_NAME = re.compile(r'[0-9a-f]{20,}')
_FAMILY = re.compile(r'[a-z]+(?:_[a-z]+)?')


def family(stem: str) -> str:
    """Where a corpus document comes from: the first two words of its name
    (``super_editor``, ``file``), the hash-named web corpus being one family."""
    name = _STEM_ID.sub('', Path(stem).name.lower())
    if _HASH_NAME.match(name):
        return 'web'
    found = _FAMILY.match(name)
    return found.group(0) if found else name


def extend_by_family(sample: Sequence[dict], pool: Sequence[dict], extra: int, seed: int,
                     covered: set[str] | frozenset[str] = frozenset(),
                     first: dict[tuple[str, str], str] | None = None) -> list[dict]:
    """``sample`` and ``extra`` more compares, spread over where documents come from.

    Only pairs the sample does not hold yet, one compare each. First one
    compare from every family (of the base document, ``family``) the sample
    lacks, the pool's largest family first; then, one at a time, from the
    family furthest below its share of the pool. Within a family a scarce
    state goes before ``FILL_STATE``, then a pair the docxodus lane covers
    before one it does not, then seeded order. The added rows follow the
    sample's, sorted by key.
    """
    rng = random.Random(seed)

    def has(r: dict) -> bool:
        return (first[r['base'], r['next']] if first else r['key']) in covered

    pairs = {(r['base'], r['next']) for r in sample}
    share = Counter(family(r['base']) for r in pool)
    have = Counter(family(r['base']) for r in sample)
    rest = [r for r in pool if (r['base'], r['next']) not in pairs]
    rng.shuffle(rest)
    stock: dict[str, list[dict]] = {}
    for r in sorted(rest, key=lambda r: (r['state'] == FILL_STATE, not has(r))):  # stable: seeded within
        stock.setdefault(family(r['base']), []).append(r)
    total, added = len(sample) + extra, []

    def take(name: str) -> None:
        rows = stock[name]
        while rows:
            r = rows.pop(0)
            if (r['base'], r['next']) not in pairs:
                pairs.add((r['base'], r['next']))
                have[name] += 1
                added.append(r)
                break
        if not rows:
            del stock[name]

    for name in sorted((f for f in stock if not have[f]), key=lambda f: (-share[f], f)):
        if len(added) < extra:
            take(name)
    while len(added) < extra and stock:
        take(max(sorted(stock), key=lambda f: total * share[f] / len(pool) - have[f]))
    return [*sample, *sorted(added, key=lambda r: r['key'])]


def draw_balanced(pool: Sequence[dict], n: int, seed: int, covered: set[str],
                  first: dict[tuple[str, str], str] | None = None) -> list[dict]:
    """``n`` compares of ``n`` distinct pairs, balanced by state and spread by source.

    Scarce states (everything but ``FILL_STATE``) go in whole, one compare per
    pair — the pairs the docxodus lane has a Word PDF for first, then the rest;
    ``n`` is filled with ``FILL_STATE`` compares spread over the document
    families (``extend_by_family``): every family once, then by its share of
    the pool, a pair the docxodus lane covers first within a family (the
    comparator's numbers are then about redlines, not about absence). Seeded
    throughout. ``covered`` holds first keys; ``first`` maps a row's pair to
    its first key (a row is its own first key without it).
    """
    rng = random.Random(seed)

    def has(r: dict) -> bool:
        return (first[r['base'], r['next']] if first else r['key']) in covered

    groups = [
        [r for r in pool if r['state'] != FILL_STATE and has(r)],
        [r for r in pool if r['state'] != FILL_STATE and not has(r)],
    ]
    for group in groups:
        rng.shuffle(group)
    # one compare per pair: a second Word compare of the same two documents would score one
    # tool output twice (the pair's first key when it is among them)
    one: dict[tuple[str, str], dict] = {}
    for r in (r for group in groups for r in group):
        pair = (r['base'], r['next'])
        if pair not in one or (first is not None and r['key'] == first[pair]):
            one[pair] = r
    scarce = list(one.values())[:n]
    fill = [r for r in pool if r['state'] == FILL_STATE]
    chosen = extend_by_family(scarce, [*scarce, *fill], n - len(scarce), seed, covered, first)
    return sorted(chosen, key=lambda r: r['key'])


def adopt_redline(listing: Path, pool: Sequence[dict], n: int) -> list[dict]:
    """The pool rows of an existing sample list's keys, in its order."""
    by_key = {r['key']: r for r in pool}
    keys = [r['key'] for r in read_csv(listing)]
    unknown = [k for k in keys if k not in by_key]
    if unknown:
        raise RuntimeError(f'{listing}: {len(unknown)} keys are not in pool_pairs.csv (first: {unknown[0]})')
    if len(set(keys)) != len(keys):
        raise RuntimeError(f'{listing}: {len(keys) - len(set(keys))} keys are listed twice')
    if len(keys) != n:
        raise RuntimeError(f'{listing}: {len(keys)} keys, want {n} (--n)')
    rows = [by_key[k] for k in keys]
    pairs = Counter((r['base'], r['next']) for r in rows)
    twice = [r['key'] for r in rows if pairs[r['base'], r['next']] > 1]
    if twice:
        raise RuntimeError(f'{listing}: {len(rows) - len(pairs)} compares repeat a pair already listed '
                           f'(first: {twice[0]}) — the sample is one compare per pair')
    return rows


def conversion_quotas(n: int) -> dict[str, int]:
    """``CONVERSION_QUOTAS`` scaled to ``n`` fixtures (largest remainder)."""
    total = sum(CONVERSION_QUOTAS.values())
    exact = {state: n * want / total for state, want in CONVERSION_QUOTAS.items()}
    quotas = {state: int(q) for state, q in exact.items()}
    for state in sorted(exact, key=lambda s: exact[s] - int(exact[s]), reverse=True):
        if sum(quotas.values()) >= n:
            break
        quotas[state] += 1
    return quotas


def _fixture(state: str, docx_stem: str) -> dict:
    return {'state': state, 'stem': f'{state}__{docx_stem}',
            'docx': f'corpus/word/{state}/docx/{docx_stem}.docx',
            'word_pdf': f'corpus/word/{state}/pdf/{docx_stem}.pdf'}


def draw_conversion(root: Path, quotas: dict[str, int], seed: int) -> list[dict]:
    """Fixture rows (state, stem, docx, word_pdf; paths from the bench ``root``) —
    the quotas per state, among DOCX with a Word PDF."""
    rng = random.Random(seed)
    word = root / 'corpus/word'
    rows: list[dict] = []
    for state, want in quotas.items():
        have = [_fixture(state, docx.stem)
                for docx in sorted((word / state / 'docx').glob('*.docx'))
                if not docx.name.startswith('~$') and (word / state / 'pdf' / f'{docx.stem}.pdf').is_file()]
        if len(have) < want:
            raise RuntimeError(f'{state}: {want} fixtures wanted, only {len(have)} have a Word PDF')
        rng.shuffle(have)
        rows += have[:want]
    return sorted(rows, key=lambda r: r['stem'])


def adopt_conversion(listing: Path, root: Path, n: int) -> list[dict]:
    """Fixture rows of an existing list: one ``corpus/word/<state>/docx/<stem>.docx`` per line."""
    rows, seen = [], set()
    for line in _listed(listing):
        entry = rel_path(Path(line), root) if Path(line).is_absolute() else Path(line).as_posix()
        match = _FIXTURE.match(entry)
        if match is None:
            raise RuntimeError(f'{listing}: {line} is not corpus/word/<state>/docx/<stem>.docx')
        row = _fixture(*match.groups())
        for need in (row['docx'], row['word_pdf']):
            if not (root / need).is_file():
                raise RuntimeError(f'{listing}: no {need}')
        if row['stem'] in seen:
            raise RuntimeError(f'{listing}: {entry} is listed twice')
        seen.add(row['stem'])
        rows.append(row)
    if len(rows) != n:
        raise RuntimeError(f'{listing}: {len(rows)} fixtures, want {n} (--n)')
    return rows


def gen_with_shas(rows: Sequence[dict], root: Path, shas: dict[Path, str] | None = None) -> list[dict]:
    """Pool or pair rows with the sha256 of the four corpus files each names."""
    word = root / 'corpus/word'
    shas = {} if shas is None else shas

    def sha(path: Path) -> str:
        if path not in shas:
            shas[path] = _sha(path)
        return shas[path]

    return [dict(r) | {'base_sha256': sha(word / f'{r["base"]}.docx'),
                       'next_sha256': sha(word / f'{r["next"]}.docx'),
                       'docx_sha256': sha(word / r['docx']), 'pdf_sha256': sha(word / r['pdf'])}
            for r in rows]


def conversion_with_shas(rows: Sequence[dict], root: Path) -> list[dict]:
    """Conversion sample rows with the sha256 of the fixture and of Word's PDF."""
    return [dict(r) | {'docx_sha256': _sha(root / r['docx']), 'word_pdf_sha256': _sha(root / r['word_pdf'])}
            for r in rows]


def state_counts(rows: Sequence[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r['state']] = counts.get(r['state'], 0) + 1
    return counts


def write_meta(ev: Path, name: str, block: dict) -> None:
    """Record how the ``name`` sample was made in ``sample_meta.json``."""
    path = ev / 'sample_meta.json'
    meta = json.loads(path.read_text()) if path.is_file() else {}
    meta[name] = block
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=1, sort_keys=True) + '\n')


def read_meta(ev: Path) -> dict:
    path = ev / 'sample_meta.json'
    if not path.is_file():
        raise RuntimeError(f'no {path}: the sample stage writes it')
    return json.loads(path.read_text())


def conversion_files(sample_csv: Path) -> list[str]:
    """The ``--files-list`` entries: one corpus docx per sampled fixture."""
    return [r['docx'] for r in read_csv(sample_csv)]


def soffice_missing(sample_csv: Path, root: Path) -> list[str]:
    """Sampled fixtures with no LibreOffice render in the soffice work folder."""
    have = _by_lower(root / SOFFICE_WORK / 'candidate')
    return [r['docx'] for r in read_csv(sample_csv) if f'{r["stem"]}.pdf'.lower() not in have]


def stage_soffice(sample_csv: Path, root: Path, dest: Path) -> tuple[int, int]:
    """Copy the sample's LibreOffice renders to ``dest`` as ``<docx stem>.pdf``, the name
    ``--score-only`` matches a fixture by. Returns (staged, without a render).

    Safe over a folder a scorer is reading: a copy already there and identical
    is left alone, and the only file removed is the staged copy of a sampled
    fixture whose render is gone (it must score 0, not its stale copy).
    """
    rows = read_csv(sample_csv)
    owner: dict[str, str] = {}
    for r in rows:
        stem = Path(r['docx']).stem.lower()
        if stem in owner:
            raise RuntimeError(f'{owner[stem]} and {r["stem"]} share the docx stem {Path(r["docx"]).stem}: '
                               'score-only could not tell their renders apart')
        owner[stem] = r['stem']
    dest.mkdir(parents=True, exist_ok=True)
    have = _by_lower(root / SOFFICE_WORK / 'candidate')
    staged = 0
    for r in rows:
        src, copy = have.get(f'{r["stem"]}.pdf'.lower()), dest / f'{Path(r["docx"]).stem}.pdf'
        if src is None:
            copy.unlink(missing_ok=True)
            continue
        if not (copy.is_file() and filecmp.cmp(src, copy, shallow=False)):
            shutil.copyfile(src, copy)
        staged += 1
    return staged, len(rows) - staged


# ------------------------------------------------------------------ the results dataset

@dataclass(frozen=True)
class Hub:
    """The two calls on the results dataset, injectable so tests need no network."""

    listing: Callable[[], list[str]]  # the file names under HUB_DOCXODUS
    fetch: Callable[[str, Path], bool]  # one name to a path; False when the Hub has no such file


def default_hub(tmp: Path) -> Hub:
    def listing() -> list[str]:
        from huggingface_hub import HfApi

        tree = HfApi().list_repo_tree(HUB_REPO, path_in_repo=HUB_DOCXODUS, repo_type='dataset')
        return sorted(Path(item.path).name for item in tree if item.path.endswith('.pdf'))

    def fetch(name: str, dest: Path) -> bool:
        from huggingface_hub import hf_hub_download
        from huggingface_hub.errors import EntryNotFoundError

        try:
            got = hf_hub_download(HUB_REPO, f'{HUB_DOCXODUS}/{name}', repo_type='dataset', local_dir=tmp)
        except EntryNotFoundError:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        os.replace(got, dest)
        return True

    return Hub(listing, fetch)


def hub_names(ev: Path, hub: Hub | None) -> tuple[set[str] | None, str]:
    """The Docxodus Word PDFs the Hub holds, cached in the evidence folder, and where
    the answer came from. None when there is no listing to be had."""
    cache = ev / 'hub_docxodus_listing.json'
    if cache.is_file():
        return set(json.loads(cache.read_text())['names']), 'cached Hub listing'
    if hub is None:
        return None, 'Hub not consulted'
    try:
        names = sorted(hub.listing())
    except Exception as exc:  # no network, no such repo, no token: fall back, say so
        return None, f'Hub unreachable ({type(exc).__name__})'
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({'repo': HUB_REPO, 'folder': HUB_DOCXODUS, 'names': names,
                                 'listed': datetime.now(UTC).isoformat(timespec='seconds')}, indent=1) + '\n')
    return set(names), 'Hub listing'


def docxodus_pdf(root: Path, key: str) -> Path:
    return root / RUN_DIR / 'docxodus' / 'pdf_by_word' / f'{key}_docxodus.pdf'


def sample_first_keys(sample: Sequence[dict], gen_pairs: Sequence[dict]) -> list[str]:
    """The sample's pairs, each once, by first key and in sample order."""
    first = first_keys(gen_pairs)
    return list(dict.fromkeys(first[r['base'], r['next']] for r in sample))


def docxodus_missing(sample_csv: Path, root: Path, gen_pairs: Sequence[dict]) -> list[dict]:
    """gen_pairs rows of the sampled pairs that lack a docxodus Word PDF locally,
    less the pairs whose Docxodus redline Word already refused (they score 0)."""
    by_key = {r['key']: r for r in gen_pairs}
    refused = word_refused(root)
    return [by_key[key] for key in sample_first_keys(read_csv(sample_csv), gen_pairs)
            if not docxodus_pdf(root, key).is_file() and key not in refused]


REFUSED_FIELDS = ['key', 'tool_version', 'docx_sha256', 'recorded']


def refused_ledger(root: Path) -> Path:
    return root / RUN_DIR / 'docxodus' / 'word_refused.csv'


def docxodus_version(root: Path) -> str:
    versions = root / RUN_DIR / 'versions.json'
    return json.loads(versions.read_text()).get('docxodus') or '' if versions.is_file() else ''


def word_refused(root: Path) -> set[str]:
    """Pairs whose redline by this Docxodus version Word refused in both export passes."""
    ledger = refused_ledger(root)
    if not ledger.is_file():
        return set()
    version = docxodus_version(root)
    return {r['key'] for r in read_csv(ledger) if r['tool_version'] == version}


def record_refusals(root: Path, today: str) -> str:
    """After both export passes, a Docxodus redline still without a Word PDF is one
    Word refused twice. It is written to the ledger and moved out of the export
    folder, so no later run redlines the pair or opens the file again."""
    lane = root / RUN_DIR / 'docxodus'
    ledger = refused_ledger(root)
    rows = read_csv(ledger) if ledger.is_file() else []
    version = docxodus_version(root)
    new = 0
    for docx in sorted((lane / 'docx').glob('*_docxodus.docx')):
        key = docx.stem.removesuffix('_docxodus')
        if docxodus_pdf(root, key).is_file():
            continue
        rows.append({'key': key, 'tool_version': version, 'docx_sha256': _sha(docx), 'recorded': today})
        dest = lane / 'docx_refused' / docx.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        docx.replace(dest)
        new += 1
    if new:
        write_csv(ledger, REFUSED_FIELDS, rows)
    known = len({r['key'] for r in rows if r['tool_version'] == version})
    return (f'{new} Docxodus redlines Word refused twice, moved to {RUN_DIR}/docxodus/docx_refused; '
            f'{known} on record for {version or "this Docxodus"} (they score 0 and are not opened again)')


def fetch_docxodus(sample_csv: Path, root: Path, gen_pairs: Sequence[dict], ev: Path, hub: Hub | None) -> str:
    """Fetch the Docxodus Word PDFs the sample's pairs lack locally. A PDF the Hub
    does not hold is counted, not an error: Docxodus redlines that pair next."""
    wanted = [r['key'] for r in docxodus_missing(sample_csv, root, gen_pairs)]
    if not wanted:
        return 'every sampled pair has its docxodus Word PDF locally'
    if hub is None:
        return f'Hub not consulted: {len(wanted)} pairs left to Docxodus'
    names, source = hub_names(ev, hub)
    if names is None:
        return f'{source}: nothing fetched, {len(wanted)} pairs left to Docxodus'
    fetched = absent = failed = 0
    for key in wanted:
        name = f'{key}_docxodus.pdf'
        if name not in names:
            absent += 1
            continue
        try:
            got = hub.fetch(name, docxodus_pdf(root, key))
        except Exception:  # one download failing leaves the pair to Docxodus
            failed += 1
            continue
        fetched += got
        absent += not got
    return (f'{fetched} docxodus Word PDFs fetched ({source}), {absent} not on the Hub'
            + (f', {failed} downloads failed' if failed else ''))


# ------------------------------------------------------------------ release_info rows

def redline_rows(sample: Sequence[dict], root: Path, lane: str, gen_pairs: Sequence[dict],
                 fresh: Path) -> list[list[str]]:
    """The release_info redline CSV's data rows, from the files on disk now.

    One row per sampled pool key with its own oracle and compare docx/pdf;
    the docxodus and jubarte columns name the pair's first-key files.
    """
    first = first_keys(gen_pairs)
    word = root / 'corpus/word'
    lane_dir = root / RUN_DIR / lane
    cell = _Cells(root)
    rows = []
    for r in sample:
        kind, oracle = oracle_for(r, fresh, root)
        key = first[r['base'], r['next']]
        rows.append([
            r['key'], *cell(word / f'{r["base"]}.docx'), *cell(word / f'{r["next"]}.docx'),
            *cell(word / r['docx']), *cell(word / r['pdf']),
            r['state'], r['id'], r['sets'], kind,
            *cell(oracle), *cell(docxodus_pdf(root, key)),
            *cell(lane_dir / 'docx' / f'{key}_{lane}.docx'),
            *cell(lane_dir / 'pdf_by_word' / f'{key}_{lane}.pdf'),
        ])
    return rows


def conversion_rows(sample: Sequence[dict], root: Path, jubarte_dir: Path) -> list[list[str]]:
    """The release_info conversion CSV's data rows, from the files on disk now."""
    cell = _Cells(root)
    jubarte, soffice = _by_lower(jubarte_dir), _by_lower(root / SOFFICE_WORK / 'candidate')
    return [[r['state'], r['stem'], *cell(root / r['docx']), *cell(root / r['word_pdf']),
             *cell(jubarte.get(f'{r["stem"]}.pdf'.lower())), *cell(soffice.get(f'{r["stem"]}.pdf'.lower()))]
            for r in sample]


# ------------------------------------------------------------------ aggregates

def itt_scores(rows: dict[str, dict], keys: Sequence[str]) -> dict[str, float]:
    """Per-key overall scores (pipeline.overall_from_result, measure.py's rule)
    with 0.0 for every key that scored nothing (intent-to-treat)."""
    return {k: pipeline.overall_from_result(rows[k]) if k in rows else 0.0 for k in keys}


def report_scores(report: dict, tool: str, stems: Sequence[str]) -> dict[str, float]:
    """A docx_to_pdf report's scores for the sampled fixtures, intent-to-treat: a
    fixture the report leaves out scores 0. Stems are matched whatever their case."""
    per_doc = {str(k).lower(): float(v) for k, v in (_report_tool(report, tool).get('per_doc') or {}).items()}
    return {stem: per_doc.get(stem.lower(), 0.0) for stem in stems}


def _report_tool(report: dict, tool: str) -> dict:
    tools = report.get('tools') or {}
    if tool not in tools:
        raise RuntimeError(f'the report scores {sorted(tools)}, not {tool}')
    return tools[tool]


def _score_only_tool(report: dict) -> str:
    """The key a ``--score-only`` report files its PDFs under: ``candidates``
    (``--tool`` takes converters the bench can run, and LibreOffice is not one)."""
    return SCORE_ONLY_TOOL if SCORE_ONLY_TOOL in (report.get('tools') or {}) else 'soffice'


def _agg(scores: dict[str, float]) -> dict:
    values = list(scores.values())
    return {
        'n': len(values),
        'failures': sum(1 for v in values if v <= 0.0),  # scored 0, intent-to-treat
        'mean': round(statistics.fmean(values), 4) if values else 0.0,
        'median': round(statistics.median(values), 4) if values else 0.0,
        'exact_100': sum(1 for v in values if v >= 100.0 - 1e-6),
        'at_least_90': sum(1 for v in values if v >= 90.0),
    }


def by_state(scores: dict[str, float], key_state: dict[str, str]) -> dict[str, dict]:
    states: dict[str, list[str]] = {}
    for key, state in key_state.items():
        states.setdefault(state, []).append(key)
    return {state: _agg({k: scores[k] for k in keys}) for state, keys in sorted(states.items())}


def median_interval(scores: dict[str, float]) -> list[float] | None:
    """ledger/stats.bootstrap_median_ci of a tool's own ITT scores (2,000 resamples, seed 42)."""
    from neurotic_docx_bench.ledger import stats

    ci = stats.bootstrap_median_ci(list(scores.values()))
    return None if ci is None else list(ci)


def paired_interval(a: dict[str, float], b: dict[str, float]) -> dict | None:
    """ledger/stats.paired_median_diff: percentile bootstrap, 2,000 resamples, seed 42."""
    from neurotic_docx_bench.ledger import stats

    diff = stats.paired_median_diff(a, b)
    if diff is None:
        return None
    return {'median_delta': diff.median_delta, 'ci95': [diff.ci_low, diff.ci_high],
            'wins': diff.wins, 'losses': diff.losses, 'ties': diff.ties,
            'bootstrap': {'reps': stats.DEFAULT_REPS, 'seed': stats.DEFAULT_SEED}}


def tool_block(identity: dict, scores: dict[str, float], key_state: dict[str, str],
               per_document: dict | None = None) -> dict:
    block = dict(identity) | _agg(scores)
    block['median_ci95'] = median_interval(scores)
    block['by_state'] = by_state(scores, key_state)
    if per_document is not None:
        block['per_document'] = per_document
    return block


# ------------------------------------------------------------------ the records

def _span(ci: Sequence[float] | None) -> str:
    return f'[{ci[0]}, {ci[1]}]' if ci else 'not computed'


def website_records(version: str, generated: str, redline: dict, conversion: dict,
                    redline_stem: str, conversion_stem: str) -> list[dict]:
    """facts.jsonl-shaped records for every key the release moves.

    The bench.* values are this run's own numbers; the values the bench
    cannot know before the release exists are placeholders for the site step
    (sync-release.ts) to fill, each marked ``"pending": true`` — the file is
    the checklist, facts.py the writer of data/facts.jsonl itself.
    """
    def rec(key: str, value: object, pending: bool = False) -> dict:
        u = uuid.uuid7()
        return {'id': str(u), 'ts': facts_stamp(u), 'key': key, 'value': value,
                'source': f'release_info evidence of jubarte {version} ({generated})'} \
            | ({'pending': True} if pending else {})

    jub_r, doc_r = redline['tools']['jubarte'], redline['tools']['docxodus']
    jub_c, sof_c = conversion['tools']['jubarte'], conversion['tools']['soffice']
    docs, compares = jub_c['n'], jub_r['n']
    pairs = redline['sample'].get('pairs', compares)
    balance = '/'.join(str(block['n']) for block in jub_c['by_state'].values())
    scorer = conversion['versions']['scorer']
    r_ci = _span((redline.get('comparison') or {}).get('ci95'))
    tables = [
        {'id': 'conversion-sample', 'title': f"DOCX → PDF vs Word's own PDF — {docs}-document sample",
         'meta': f'{docs} docs · {balance} by state · scorer {scorer} · {generated}',
         'desc': f'A state-balanced {docs}-document sample of corpus/word (every path and sha256 in release_info/{conversion_stem}.csv), '
                 "each converter's PDF scored against Word's own export of the same file. Sorted by ITT median; a failed document "
                 'scores 0. 95% CI is a percentile bootstrap of the ITT median (2,000 resamples, seed 42).',
         'rows': [
             {'rank': '1', 'tool': 'jubarte †', 'pin': jub_c['version'], 'median': jub_c['median'],
              'mean': jub_c['mean'], 'docs': jub_c['n'], 'failed': jub_c['failures'],
              'note': _span(jub_c.get('median_ci95')), 'ours': True},
             {'rank': '2', 'tool': 'soffice', 'pin': sof_c['version'], 'median': sof_c['median'],
              'mean': sof_c['mean'], 'docs': sof_c['n'], 'failed': sof_c['failures'],
              'note': _span(sof_c.get('median_ci95')), 'ours': False}]},
        {'id': 'redlines-sample', 'title': f"Redlines vs Word's compare — {pairs}-pair sample",
         'meta': f'{pairs} pairs · one Word compare each · pixel scorer · opened in Word · {generated}',
         'desc': f'A sample of {pairs} document pairs of redlines_0929_full, one Word compare each: every pair of the scarce states, '
                 f'the rest spread over the document families (every path and sha256 in release_info/{redline_stem}.csv). '
                 "Each tool redlines the pair; Word opens that redline and exports it to PDF, scored against Word's own compare. "
                 'A pair with no scored PDF counts 0.',
         'rows': [
             {'rank': '1', 'tool': f'jubarte-{version} †', 'pin': jub_r['version'], 'median': jub_r['median'],
              'mean': jub_r['mean'], 'docs': jub_r['n'], 'failed': jub_r['failures'],
              'note': f"= 100: {jub_r['exact_100']} · ≥ 90: {jub_r['at_least_90']}", 'ours': True},
             {'rank': '2', 'tool': 'docxodus', 'pin': doc_r['version'], 'median': doc_r['median'],
              'mean': doc_r['mean'], 'docs': doc_r['n'], 'failed': doc_r['failures'],
              'note': f"= 100: {doc_r['exact_100']} · ≥ 90: {doc_r['at_least_90']}", 'ours': False}]},
    ]
    states = [{'name': name, 'n': str(block['n']),
               'rows': [{'tool': 'jubarte †', 'median': jub_c['by_state'][name]['median'], 'ours': True},
                        {'tool': 'soffice', 'median': sof_c['by_state'][name]['median']}]}
              for name, block in sorted(jub_c['by_state'].items())]
    home = [
        {'title': "DOCX → PDF vs Word's own export", 'meta': f'{docs}-doc sample · median · {generated}',
         'rows': [{'name': f'jubarte {version} †', 'v': jub_c['median'], 'ours': True},
                  {'name': sof_c['version'], 'v': sof_c['median']}]},
        {'title': "Redlines vs Word's compare, opened in Word", 'meta': f'{pairs}-pair sample · median · {generated}',
         'rows': [{'name': f'jubarte {version} †', 'v': jub_r['median'], 'ours': True},
                  {'name': doc_r['version'], 'v': doc_r['median']}],
         'note': "Both groups are the release's samples, state-balanced; "
                 "the full-corpus tables live in the bench's RESULTS.md."},
    ]
    headlines = [
        {'label': f'DOCX → PDF · median, {docs}-doc sample', 'value': f"{jub_c['median']:.2f}",
         'vs': f"{sof_c['version']} {sof_c['median']}",
         'sub': f"{docs} documents, state-balanced; {jub_c['failures']} jubarte failures. "
                f"Sample list and shas: release_info/{conversion_stem}.csv."},
        {'label': f'Redline vs Word compare · median, {pairs}-pair sample', 'value': f"{jub_r['median']:.2f}",
         'vs': f"Docxodus {doc_r['median']}",
         'sub': f'{pairs} document pairs, one Word compare each; paired 95% CI of the difference {r_ci}. '
                f'Sample list and shas: release_info/{redline_stem}.csv.'},
    ]
    method = [
        {'t': 'Oracle: real Word',
         'd': 'Every reference PDF is exported by Microsoft Word and SHA-pinned. Redlines are opened in Word too: '
              'if Word refuses the file, the tool scores 0 for that pair.'},
        {'t': 'Intent-to-treat',
         'd': 'Failures are not dropped. A crash, a timeout or an unopenable file counts as 0 in ITT mean and '
              'median, so a tool cannot improve its rank by skipping hard documents.'},
        {'t': 'Paired bootstrap',
         'd': 'Ranks tie (n=) when the paired bootstrap interval of the median difference to the row above '
              'includes 0. 2,000 resamples, seed 42.'},
        {'t': 'Release samples',
         'd': f"From {version} the tables on this page are the release's two samples — "
              "state-balanced, every file sha256-listed in the engine's release_info/. Full-corpus runs "
              "remain in the bench's RESULTS.md."},
        {'t': 'Author-affiliated, same rules',
         'd': 'jubarte is marked † everywhere. Pins, run dates and sample lists are published so any row can '
              'be re-run; the harness is public.'},
    ]
    return [
        rec('engine.version', version),
        rec('engine.released', '<the CHANGELOG date of the release, filled by the site step>', pending=True),
        rec('release.archives', '<the GitHub release archives, filled by the site step (sync-release.ts)>', pending=True),
        rec('release.wheels', '<the GitHub release wheels, filled by the site step (sync-release.ts)>', pending=True),
        rec('release.history', '<the release list headed by this version, filled by the site step>', pending=True),
        rec('bench.generated', generated),
        rec('bench.version', '<the bench results version>', pending=True),
        rec('bench.tables', tables),
        rec('bench.headlines', headlines),
        rec('bench.states', states),
        rec('bench.home_groups', home),
        rec('bench.method', method),
    ]


def app_records(version: str) -> list[dict]:
    """The app-frontend items a release moves: id/ts/key/value plus file, where, note.
    A value nobody knows yet is a placeholder marked ``"pending": true``."""
    def rec(key: str, value: object, file: str, where: str, note: str, pending: bool = False) -> dict:
        u = uuid.uuid7()
        return {'id': str(u), 'ts': facts_stamp(u), 'key': key, 'value': value,
                'file': file, 'where': where, 'note': note,
                'source': f'release_info evidence of jubarte {version}'} | ({'pending': True} if pending else {})

    return [
        rec('app.version/package.json', version, 'package.json', 'line 4 ("version")',
            "set by the engine's scripts/release.sh step 1 (npm pkg set)"),
        rec('app.version/tauri.conf.json', version, 'src-tauri/tauri.conf.json', 'line 4 ("version")',
            "set by the engine's scripts/release.sh step 1 (sed)"),
        rec('app.version/Cargo.toml', version, 'src-tauri/Cargo.toml', 'line 17 (^version = )',
            "set by the engine's scripts/release.sh step 1 (sed)"),
        rec('app.version/index.html', f'v{version}', 'src/index.html', 'line 23, selector #appbar-ver',
            "the app-bar label; set by the engine's scripts/release.sh step 1 (sed)"),
        rec('app.engine/about', f'jubarte-redlines {version}', 'src-tauri/build.rs',
            'JUBARTE_ENGINE_VERSION (line 55), read from src-tauri/Cargo.toml',
            'the About window prints it via src/about.js line 41; no edit beyond the version files'),
        rec('app.changelog', f'## [{version}] section naming `jubarte-redlines {version}`', 'CHANGELOG.md',
            'the new ## heading', "the engine's scripts/release.sh step 2 refuses the release without it"),
        rec('facts/engine.version', version, 'data/facts.jsonl', 'latest record keyed engine.version',
            'appended by sync-release.ts through scripts/facts.py; values as in website_data'),
        rec('facts/engine.released', '<the CHANGELOG date>', 'data/facts.jsonl',
            'latest record keyed engine.released', 'as above', pending=True),
        rec('facts/release.history', '<the list headed by this version>', 'data/facts.jsonl',
            'latest record keyed release.history', 'as above', pending=True),
        rec('app_store.version', '<the App Store build version>', 'data/facts.jsonl',
            'latest record keyed app_store.version',
            'moves with the Mac App Store release, not the engine release', pending=True),
        rec('app_store.price', '<$price>', 'data/facts.jsonl', 'latest record keyed app_store.price',
            'only if the listing changed', pending=True),
        rec('app_store.url', 'https://apps.apple.com/us/app/jubarte/id6790926615?mt=12', 'data/facts.jsonl',
            'latest record keyed app_store.url', 'constant; listed so the checklist is complete'),
    ]


# ------------------------------------------------------------------ the six files

SIX = (('sample_redline', 'csv'), ('sample_conversion', 'csv'),
       ('results_redline', 'json'), ('results_conversion', 'json'),
       ('website_data', 'jsonl'), ('app_data', 'jsonl'))


def write_six(engine_dir: Path, version: str, *, redline: dict, conversion: dict,
              redline_data: Sequence[Sequence[str]], conversion_data: Sequence[Sequence[str]],
              now: datetime | None = None) -> str:
    """Write the six files for ``version`` into engine_dir/release_info/ under one
    stamp, deleting that version's older stamps first. Returns the detail line."""
    stamp = stamp_now(now)
    folder = engine_dir / 'release_info'
    folder.mkdir(parents=True, exist_ok=True)
    names = {name: f'{name}_{version}_{stamp}.{ext}' for name, ext in SIX}
    ours = '|'.join(name for name, _ in SIX)
    pattern = re.compile(rf'({ours})_{re.escape(version)}_\d{{2}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}\.(csv|json|jsonl)')
    for old in folder.iterdir():
        if pattern.fullmatch(old.name) and old.name not in names.values():
            old.unlink()
    for name, header, data in (('sample_redline', REDLINE_HEADER, redline_data),
                               ('sample_conversion', CONVERSION_HEADER, conversion_data)):
        with (folder / names[name]).open('w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(header)
            writer.writerows(data)
    for name, doc, csv_name in (('results_redline', redline, names['sample_redline']),
                                ('results_conversion', conversion, names['sample_conversion'])):
        doc = dict(doc)
        doc['stamp'] = stamp
        doc['sample'] = doc['sample'] | {'csv': csv_name, 'sha256': _sha(folder / csv_name)}
        (folder / names[name]).write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
    generated = datetime.now(UTC).date().isoformat()
    with (folder / names['website_data']).open('w') as fh:
        for record in website_records(version, generated, redline, conversion,
                                      Path(names['sample_redline']).stem, Path(names['sample_conversion']).stem):
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')
    with (folder / names['app_data']).open('w') as fh:
        for record in app_records(version):
            fh.write(json.dumps(record, ensure_ascii=False) + '\n')
    return f'{folder}: six files of {version} ({stamp})'


def collect_results(root: Path, version: str, lane: str, *, jubarte: dict,
                    word_version: str | None, fresh: Path = COMPARE_REGEN / 'out') -> tuple[dict, dict]:
    """Read the four score artifacts and build the two results documents.

    ``jubarte`` is the binary's identity (``candidate_reports``,
    ``binary_sha256``, ``commit``); the version both documents record for it
    is the release's. Every path is relative to the bench ``root``.
    """
    ev = evidence_dir(version)
    meta = read_meta(root / ev)
    identity = {'version': f'jubarte {version}'} | jubarte
    sample_rows = read_csv(root / redline_list(version))
    keys = [r['key'] for r in sample_rows]
    key_state = {r['key']: r['state'] for r in sample_rows}
    rows = {tool: json.loads((root / scores_json(tool, version)).read_text())['rows']
            for tool in (lane, 'docxodus')}
    a = itt_scores(rows[lane], keys)
    b = itt_scores(rows['docxodus'], keys)
    versions = json.loads((root / RUN_DIR / 'versions.json').read_text()) \
        if (root / RUN_DIR / 'versions.json').is_file() else {}
    scorer = scorer_backend()
    generated = datetime.now(UTC).isoformat(timespec='seconds')
    redline = {
        'schema': 'jubarte-redlines/release_info/results_redline/1',
        'release': version,
        'stamp': None,
        'generated': generated,
        'sample': {'n': len(keys), 'pairs': len({(r['base'], r['next']) for r in sample_rows}),
                   'drawn': meta['redline']},
        'tools': {
            'jubarte': tool_block(identity, a, key_state, {k: {'overall': v} for k, v in a.items()}),
            'docxodus': tool_block({'version': versions.get('docxodus'), 'commit': None, 'binary_sha256': None},
                                   b, key_state, {k: {'overall': v} for k, v in b.items()}),
        },
        'comparison': {'comparator': 'docxodus', **(paired_interval(a, b) or {})},
        'versions': {'scorer': scorer, 'microsoft_word': word_version, 'libreoffice': None,
                     'docxodus': versions.get('docxodus')},
        'provenance': {
            'measure': f'{RUN_DIR}/measure.py --fresh {rel_path(fresh, root)} --sample-csv {redline_list(version)}',
            'scores': {lane: str(scores_json(lane, version)), 'docxodus': str(scores_json('docxodus', version))},
        },
    }
    conv_rows = read_csv(root / conversion_list(version))
    stems = [r['stem'] for r in conv_rows]
    conv_state = {r['stem']: r['state'] for r in conv_rows}
    jub_report = json.loads((root / conversion_report('jubarte', version)).read_text())
    sof_report = json.loads((root / conversion_report('soffice', version)).read_text())
    ja = report_scores(jub_report, 'jubarte', stems)
    scored = _score_only_tool(sof_report)
    sa = report_scores(sof_report, scored, stems)
    soffice_version = _report_tool(sof_report, scored).get('version') or SOFFICE_VERSION
    conversion = {
        'schema': 'jubarte-redlines/release_info/results_conversion/1',
        'release': version,
        'stamp': None,
        'generated': generated,
        'sample': {'n': len(stems), 'drawn': meta['conversion']},
        'tools': {
            'jubarte': tool_block(identity, ja, conv_state, dict(ja)),
            'soffice': tool_block({'version': soffice_version, 'commit': None, 'binary_sha256': None},
                                  sa, conv_state, dict(sa)),
        },
        'comparison': {'comparator': 'soffice', **(paired_interval(ja, sa) or {})},
        'versions': {'scorer': scorer, 'microsoft_word': word_version,
                     'libreoffice': soffice_version, 'docxodus': None},
        'provenance': {
            'measure': 'bench docx-to-pdf --origin list (one --files-list per fixture); '
                       f'soffice --score-only --location-to-score {ev}/soffice_sample',
            'scores': {'jubarte': str(conversion_report('jubarte', version)),
                       'soffice': str(conversion_report('soffice', version))},
        },
    }
    return redline, conversion


def engine_commit(engine_dir: Path | None,
                  run: Callable[..., release.ProcLike] | None = None) -> str | None:
    """The engine checkout's HEAD, when --engine-dir is a git checkout."""
    if engine_dir is None:
        return None
    proc = (run or release.default_runner())(['git', '-C', str(engine_dir), 'rev-parse', 'HEAD'])
    return proc.stdout.strip() if proc.returncode == 0 else None


def binary_reports(binary: Path, run: Callable[..., release.ProcLike] | None = None) -> str:
    """What ``binary --version`` prints (its first line); raises when it does not run."""
    if not binary.is_file():
        raise RuntimeError(f'no such binary: {binary}')
    proc = (run or release.default_runner())([str(binary), '--version'])
    lines = (proc.stdout or '').strip().splitlines()
    if proc.returncode != 0 or not lines:
        raise RuntimeError(f'{binary} --version does not answer (exit {proc.returncode})')
    return lines[0].strip()


def scorer_backend() -> str:
    from neurotic_docx_bench import kernels

    return kernels.backend_id()


# ------------------------------------------------------------------ plan/execute

def plan(rel: Release, *, binary: Path | None = None, seed: int = DEFAULT_SEED,
         n: int = DEFAULT_N, device: str = 'mps', conversion: Sequence[str] | None = None,
         engine_dir: Path | None = None,
         adopt_redline_csv: Path | None = None, adopt_conversion_list: Path | None = None,
         jobs: int = DEFAULT_JOBS, convert_workers: int = DEFAULT_CONVERT_WORKERS,
         hub: Hub | None = None, compare_regen: Path = COMPARE_REGEN,
         run: Callable[..., release.ProcLike] | None = None) -> list[Step]:
    """Every step of every stage, in order.

    ``conversion`` lists the conversion sample's corpus docx (one
    ``--files-list`` flag each); when None the plan reads the evidence
    folder's ``sample_conversion_<v>.csv``, else the list being adopted, and
    falls back to a placeholder so ``--plan`` still prints before the sample
    exists. ``hub`` is the results dataset (None: local files only).
    """
    lane, v, root = rel.lane, rel.version, rel.root
    ev = evidence_dir(v)
    fresh = compare_regen / 'out'
    bench = ('uv', 'run', 'bench')
    redline_csv, conversion_csv = redline_list(v), conversion_list(v)

    def given(path: Path | None) -> Path | None:
        return None if path is None else path if path.is_absolute() else root / path

    adopt_r, adopt_c = given(adopt_redline_csv), given(adopt_conversion_list)
    if conversion is None:
        if (root / conversion_csv).is_file():
            conversion = conversion_files(root / conversion_csv)
        elif adopt_c is not None and adopt_c.is_file():
            conversion = _listed(adopt_c)
        else:
            conversion = [f'<the {n} fixtures of {conversion_csv}>']
    files: list[str] = []
    for docx in conversion:
        files += ['--files-list', docx]

    def word_pdf(src: Path, out: Path, tool: str) -> tuple[str, ...]:
        # the label goes in front of the staged name: a Word dialog then says whose file it is
        return ('uv', 'run', '--script', 'scripts/word_pdf.py',
                '--src', str(src), '--out', str(out), '--timeout', '300', '--do-not-close', '--label', tool)

    jub = RUN_DIR / lane
    dx = RUN_DIR / 'docxodus'
    today = datetime.now(UTC).date().isoformat()

    def binary_path() -> Path:
        return binary if binary is not None else rel.binary

    def install() -> str:
        if binary is not None:
            said = binary_reports(binary, run)
            return f'{binary} (candidate, reports "{said}", recorded as jubarte {v}; sha256 {_sha(binary)[:12]})'
        exe = jubarte_release.github_download(v, rel.cache, jubarte_release.http_get)
        if exe is None:
            raise RuntimeError(f'release v{v} has no {jubarte_release.asset_name(v)} (or no SHA256SUMS.txt); '
                               'pass --binary for a release candidate')
        got = jubarte_release.parse_version(binary_reports(exe, run))
        if got != v:
            raise RuntimeError(f'{exe} says it is {got}, not {v}')
        return f'{exe} ({got}, sha256 checked)'

    def word() -> str:
        found = release.word_version(run or release.default_runner())
        if not found:
            raise RuntimeError('Microsoft Word does not answer osascript; the export stage needs it')
        return f'Microsoft Word {found}'

    def check_inputs() -> str:
        for need in (RUN_DIR / 'pool_pairs.csv', RUN_DIR / 'gen_pairs.csv', Path('corpus/word'),
                     SOFFICE_WORK / 'candidate'):
            if not (root / need).exists():
                raise RuntimeError(f'missing {need}')
        if not fresh.is_dir():
            raise RuntimeError(f'no {fresh} — the fresh-compare oracle rule reads it')
        for adopted in (adopt_r, adopt_c):
            if adopted is not None and not adopted.is_file():
                raise RuntimeError(f'no such list to adopt: {adopted}')
        return f'{RUN_DIR} + corpus/word + {SOFFICE_WORK} present'

    def gen_rows() -> list[dict]:
        return read_csv(root / RUN_DIR / 'gen_pairs.csv')

    def redline_sample() -> str:
        gen = gen_rows()
        first = first_keys(gen)
        pool = [r for r in read_csv(root / RUN_DIR / 'pool_pairs.csv') if (r['base'], r['next']) in first]
        local = {r['key'] for r in gen if docxodus_pdf(root, r['key']).is_file()}
        if adopt_r is not None:
            sample = adopt_redline(adopt_r, pool, n)
            missing = without_oracle(sample, fresh, root)
            if missing:
                raise RuntimeError(f'{len(missing)} sampled compares have no Word PDF (first: {missing[0]}) '
                                   '— every sample item must already have its oracle')
            covered, source = local, 'local PDFs'
            drawn = {'seed': seed, 'date': today, 'adopted_sha256': _sha(adopt_r),
                     'rule': f'adopted from {rel_path(adopt_r, root)}, not drawn'}
        else:
            names, source = hub_names(root / ev, hub)
            covered = local | {name.removesuffix('_docxodus.pdf') for name in names or ()}
            source = 'local PDFs + ' + source if names is not None else f'local PDFs only: {source}'
            pool = [r for r in pool if oracle_for(r, fresh, root)[1].is_file()]
            sample = draw_balanced(pool, n, seed, covered, first)
            if len(sample) != n:
                raise RuntimeError(f'only {len(sample)} compares have their Word PDF, {n} wanted')
            drawn = {'seed': seed, 'date': today,
                     'rule': 'pool compares that have their oracle, balanced by compare state: every scarce '
                             f'state whole (docxodus-covered pairs first), filled with {FILL_STATE} compares '
                             'of docxodus-covered pairs, then uncovered ones; seeded shuffles'}
        keys = sample_first_keys(sample, gen)
        have = sum(k in covered for k in keys)
        by_key = {r['key']: r for r in gen}
        shas: dict[Path, str] = {}
        write_csv(root / redline_csv, GEN_SHA_FIELDS, gen_with_shas(sample, root, shas))
        write_csv(root / ev / 'gen_pairs_sample.csv', GEN_SHA_FIELDS,
                  gen_with_shas([by_key[k] for k in keys], root, shas))
        write_meta(root / ev, 'redline', drawn | {'n': len(sample), 'pairs': len(keys),
                                                  'by_state': state_counts(sample),
                                                  'docxodus_covered_pairs': have, 'docxodus_coverage': source})
        how = f'adopted from {rel_path(adopt_r, root)}' if adopt_r is not None else f'drawn, seed {seed}'
        return (f'{redline_csv}: {len(sample)} compares of {len(keys)} pairs ({how}); '
                f'{have} pairs with a docxodus Word PDF ({source})')

    def conversion_sample() -> str:
        if adopt_c is not None:
            sample = adopt_conversion(adopt_c, root, n)
            drawn = {'seed': seed, 'date': today, 'adopted_sha256': _sha(adopt_c),
                     'rule': f'adopted from {rel_path(adopt_c, root)}, not drawn'}
            how = f'adopted from {rel_path(adopt_c, root)}'
        else:
            quotas = conversion_quotas(n)
            sample = draw_conversion(root, quotas, seed)
            drawn = {'seed': seed, 'date': today, 'quotas': quotas,
                     'rule': 'per-state quotas among the corpus/word DOCX that have a Word PDF; seeded shuffles'}
            how = f'drawn, seed {seed}, quotas {quotas}'
        write_csv(root / conversion_csv, CONVERSION_SHA_FIELDS, conversion_with_shas(sample, root))
        counts = state_counts(sample)
        write_meta(root / ev, 'conversion', drawn | {'n': len(sample), 'by_state': counts})
        return f'{conversion_csv}: {len(sample)} fixtures ({how}); by state {counts}'

    def generator_dist() -> str:
        # generate-native-redlines.ts runs <dist>/redline, else <dist>/jubarte: a folder
        # holding only this link cannot hand it a neighbour of the binary instead
        target = binary_path().resolve()
        if not target.is_file():
            raise RuntimeError(f'no such binary: {target} (the install stage resolves it)')
        dist = root / ev / 'dist'
        dist.mkdir(parents=True, exist_ok=True)
        link = dist / 'jubarte'
        link.unlink(missing_ok=True)
        link.symlink_to(target)
        return f'{ev}/dist/jubarte -> {target}'

    def generate(tool: str, method: str, dist: Path, manifest: Path) -> tuple[str, ...]:
        return ('node', '--import', 'tsx', 'scripts/generate-native-redlines.ts',
                '--method', method,
                '--dist', str(dist),
                '--tool', tool,
                '--manifest', str(manifest),
                '--source-dir', 'corpus/word',
                '--out', str(RUN_DIR / tool / 'docx'),
                '--run-dir', str(RUN_DIR / tool))

    def docxodus_fetch() -> str:
        return fetch_docxodus(root / redline_csv, root, gen_rows(), root / ev, hub)

    def docxodus_manifest() -> str:
        rows = docxodus_missing(root / redline_csv, root, gen_rows())
        write_csv(root / ev / 'gen_pairs_docxodus_missing.csv', GEN_SHA_FIELDS, gen_with_shas(rows, root))
        return f'{ev}/gen_pairs_docxodus_missing.csv: {len(rows)} pairs without a docxodus Word PDF'

    docxodus_generate = generate('docxodus', 'docxodus-csharp-inproc', DOCXODUS_DIST,
                                 ev / 'gen_pairs_docxodus_missing.csv')

    def docxodus_redlines() -> str:
        # the generator exits 1 when it writes nothing, so an empty manifest must not reach it
        rows = read_csv(root / ev / 'gen_pairs_docxodus_missing.csv')
        if not rows:
            return 'no pair lacks a docxodus Word PDF: nothing to redline'
        proc = (run or release.default_runner())(list(docxodus_generate), cwd=root)
        (root / ev / 'docxodus.generate.log').write_text((proc.stdout or '') + (proc.stderr or ''))
        if proc.returncode != 0:
            raise RuntimeError(f'{" ".join(docxodus_generate)}: exit {proc.returncode} '
                               f'(see {ev}/docxodus.generate.log)')
        return f'{len(rows)} pairs redlined by Docxodus: {" ".join(docxodus_generate)}'

    def soffice_list() -> str:
        missing = soffice_missing(root / conversion_csv, root)
        (root / ev / 'soffice_missing.txt').write_text(''.join(f'{docx}\n' for docx in missing))
        return f'{ev}/soffice_missing.txt: {len(missing)} fixtures without a LibreOffice render'

    def soffice_stage() -> str:
        staged, missing = stage_soffice(root / conversion_csv, root, root / ev / 'soffice_sample')
        return f'{ev}/soffice_sample: {staged} renders staged, {missing} fixtures without one (they score 0)'

    def measure(tool: str) -> tuple[str, ...]:
        return ('uv', 'run', 'python', str(RUN_DIR / 'measure.py'),
                '--fresh', str(fresh), '--regen-list', str(compare_regen / 'regen_list.csv'),
                '--device', device, '--jobs', str(jobs), '--sample-csv', str(redline_csv), tool)

    def write_action() -> str:
        if engine_dir is None:
            raise RuntimeError('the write stage needs --engine-dir (the checkout whose release_info/ it fills)')
        exe = binary_path()
        identity = {'candidate_reports': binary_reports(exe, run), 'binary_sha256': _sha(exe),
                    'commit': engine_commit(engine_dir, run)}
        redline, conversion_doc = collect_results(
            root, v, lane, jubarte=identity, fresh=fresh,
            word_version=release.word_version(run or release.default_runner()))
        detail = write_six(
            engine_dir, v, redline=redline, conversion=conversion_doc,
            redline_data=redline_rows(read_csv(root / redline_csv), root, lane, gen_rows(), fresh),
            conversion_data=conversion_rows(read_csv(root / conversion_csv), root,
                                            root / ev / 'convert_work' / 'jubarte' / 'candidate'))
        return f'{detail}; binary {identity["binary_sha256"][:12]} reports "{identity["candidate_reports"]}"'

    adopting = 'adopt' if adopt_r is not None else 'draw', 'adopt' if adopt_c is not None else 'draw'
    return [
        Step('install', 'candidate binary' if binary is not None else 'release binary', action=install),
        Step('sample', 'bench inputs', action=check_inputs, preflight=True),
        Step('sample', f'{adopting[0]} redline sample', action=redline_sample),
        Step('sample', f'{adopting[1]} conversion sample', action=conversion_sample),
        Step('generate', 'generator dist', action=generator_dist),
        Step('generate', 'jubarte redlines',
             generate(lane, 'jubarte-rust', ev / 'dist', ev / 'gen_pairs_sample.csv'),
             log=ev / f'{lane}.generate.log'),
        Step('generate', 'docxodus PDFs from the hub', action=docxodus_fetch),
        Step('generate', 'docxodus manifest', action=docxodus_manifest),
        Step('generate', 'docxodus redlines (missing only)', docxodus_generate, action=docxodus_redlines),
        Step('export', 'word answers', action=word, preflight=True),
        Step('export', 'word export jubarte (batch)',
             (*word_pdf(jub / 'docx', jub / 'pdf_by_word', 'jubarte'), '--log', str(jub / 'word_pdf.sample.log')),
             log=jub / 'word_pdf.sample.out', watch=(jub / 'word_pdf.sample.log',), may_fail=True),
        Step('export', 'word export jubarte (one osascript per document)',
             (*word_pdf(jub / 'docx', jub / 'pdf_by_word', 'jubarte'), '--no-one-osascript',
              '--log', str(jub / 'word_pdf.sample.retry.log')),
             log=jub / 'word_pdf.sample.retry.out', watch=(jub / 'word_pdf.sample.retry.log', jub / 'pdf_by_word'),
             may_fail=True),
        # the docxodus lane is shared by every release: its logs carry this one's version
        Step('export', 'word export docxodus (batch)',
             (*word_pdf(dx / 'docx', dx / 'pdf_by_word', 'docxodus'), '--log', str(dx / f'word_pdf.sample_{v}.log')),
             log=dx / f'word_pdf.sample_{v}.out', watch=(dx / f'word_pdf.sample_{v}.log',), may_fail=True),
        Step('export', 'word export docxodus (one osascript per document)',
             (*word_pdf(dx / 'docx', dx / 'pdf_by_word', 'docxodus'), '--no-one-osascript',
              '--log', str(dx / f'word_pdf.sample_{v}.retry.log')),
             log=dx / f'word_pdf.sample_{v}.retry.out',
             watch=(dx / f'word_pdf.sample_{v}.retry.log', dx / 'pdf_by_word'), may_fail=True),
        Step('export', 'word refusals docxodus', action=lambda: record_refusals(root, today)),
        # one scoring job at a time: each measure finishes before the next starts
        Step('measure', 'measure jubarte', measure(lane), log=ev / f'measure_{lane}.log'),
        Step('measure', 'measure docxodus', measure('docxodus'), log=ev / 'measure_docxodus.log'),
        # converting with bench docx-to-pdf scores right after the last fixture
        Step('convert', 'convert jubarte (converts + scores)',
             (*bench, 'docx-to-pdf', '--converter', str(binary_path()), '--origin', 'list', *files,
              '--work-dir', str(ev / 'convert_work'),
              '--json', str(conversion_report('jubarte', v)),
              '--jobs', str(jobs), '--convert-workers', str(convert_workers)),
             log=ev / f'convert_jubarte_{v}.log'),
        Step('convert', 'soffice missing list', action=soffice_list),
        Step('convert', 'convert soffice (missing only)',
             ('uv', 'run', 'python', 'scripts/convert_candidates.py', '--engine', 'soffice',
              '--out', str(SOFFICE_WORK), '--files-list', str(ev / 'soffice_missing.txt'),
              '--jobs', str(convert_workers)),
             log=ev / 'convert_soffice.log', may_fail=True),
        Step('score', 'stage soffice renders', action=soffice_stage),
        Step('score', 'score soffice (score-only)',
             (*bench, 'docx-to-pdf', '--score-only',
              '--tool-version', SOFFICE_VERSION,
              '--location-to-score', str(ev / 'soffice_sample'),
              '--origin', 'list', *files,
              '--work-dir', str(ev / 'soffice_score_work'),
              '--json', str(conversion_report('soffice', v)),
              '--jobs', str(jobs)),
             log=ev / f'score_soffice_{v}.log'),
        Step('write', 'release_info', action=write_action),
    ]


def select(steps: Sequence[Step], only: Sequence[str] = (), skip: Sequence[str] = ()) -> list[Step]:
    unknown = sorted((set(only) | set(skip)) - set(STAGES))
    if unknown:
        raise ValueError(f'unknown stage(s) {unknown}; stages are {", ".join(STAGES)}')
    chosen = [s for s in steps if (not only or s.stage in only) and s.stage not in skip]
    return [s for s in chosen if s.preflight] + [s for s in chosen if not s.preflight]


def shown(step: Step) -> str:
    """``Step.shown`` with a long run of ``--files-list`` flags folded to its count, and
    the command an action runs beside its name."""
    if step.action is not None and step.argv:
        return f'({step.name}: {" ".join(step.argv)})'
    count = step.argv.count('--files-list')
    if count <= 3:
        return step.shown()
    at = step.argv.index('--files-list')
    folded = (*step.argv[:at], '--files-list', f'<{count} fixtures, one flag each>', *step.argv[at + 2 * count:])
    return dataclasses.replace(step, argv=folded).shown()


app = typer.Typer(name='release-info', add_completion=False, help=__doc__)


def _stages(value: str) -> list[str]:
    return [s.strip() for s in value.split(',') if s.strip()]


@app.command()
def main(
    version: str = typer.Argument(..., help='the jubarte release, x.y.z'),
    root: Path = typer.Option(Path('.'), '--root', help='bench repository root'),
    engine_dir: Path = typer.Option(None, '--engine-dir',
                                    help='the jubarte-redlines checkout whose release_info/ the six files go to'),
    binary: Path = typer.Option(None, '--binary',
                                help='a release candidate built from the release commit; any version it reports '
                                     'is accepted and recorded (default: the GitHub release binary)'),
    seed: int = typer.Option(DEFAULT_SEED, '--seed', help='the sample draw seed'),
    n: int = typer.Option(DEFAULT_N, '--n', help='items in each sample'),
    adopt_redline_csv: Path = typer.Option(None, '--adopt-redline',
                                           help='a CSV with a key column: the redline sample, instead of drawing '
                                                '(a relative path is from the bench root)'),
    adopt_conversion_list: Path = typer.Option(None, '--adopt-conversion',
                                               help='a file of corpus/word/<state>/docx/<stem>.docx lines: the '
                                                    'conversion sample, instead of drawing'),
    jobs: int = typer.Option(DEFAULT_JOBS, '--jobs', help='scorer jobs of measure.py and docx-to-pdf'),
    convert_workers: int = typer.Option(DEFAULT_CONVERT_WORKERS, '--convert-workers',
                                        help='parallel convert processes'),
    device: str = typer.Option('mps', '--device', help='scorer kernels for measure.py'),
    use_hub: bool = typer.Option(True, '--hub/--no-hub',
                                 help='fetch the Docxodus Word PDFs the sample lacks from the results dataset'),
    only: str = typer.Option('', '--only', help=f'comma list of stages to run ({", ".join(STAGES)})'),
    skip: str = typer.Option('', '--skip', help='comma list of stages to leave out'),
    show_plan: bool = typer.Option(False, '--plan', help='print the steps and run nothing'),
) -> None:
    try:
        rel = Release(version, root.resolve())
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    ev = evidence_dir(version)

    def steps_of(conversion: Sequence[str] | None = None) -> list[Step]:
        try:
            return select(plan(rel, binary=binary.expanduser().resolve() if binary else None, seed=seed, n=n,
                               device=device, conversion=conversion,
                               engine_dir=engine_dir.resolve() if engine_dir else None,
                               adopt_redline_csv=adopt_redline_csv, adopt_conversion_list=adopt_conversion_list,
                               jobs=jobs, convert_workers=convert_workers,
                               hub=default_hub(rel.root / ev / 'hub_tmp') if use_hub else None,
                               run=release.default_runner()), _stages(only), _stages(skip))
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    # The convert/score file lists come from the sample the run is about to
    # make: install+sample run first, then the rest is planned again with
    # the list on disk (its own preflights first).
    light = ('install', 'sample')
    steps = steps_of()
    first = [s for s in steps if s.stage in light]
    rest = [s for s in steps if s.stage not in light]
    if show_plan:
        for s in (*first, *rest):
            typer.echo(f'{s.stage:9} {shown(s)}' + ('   [watchdog]' if s.watch else ''))
        return
    done = execute(first, rel.root, echo=typer.echo) if first else []
    if len(done) < len(first) or not all(o.ok for o in done):
        typer.echo(f'stopped at {done[-1].step.stage}: {done[-1].step.name}')
        raise typer.Exit(code=1)
    if rest:
        on_disk = rel.root / conversion_list(version)
        if not on_disk.is_file():
            typer.echo(f'no {on_disk}: run the sample stage first (--only install,sample)')
            raise typer.Exit(code=1)
        rest = [s for s in steps_of(conversion_files(on_disk)) if s.stage not in light]
        done = execute(rest, rel.root, echo=typer.echo)
        if len(done) < len(rest) or not all(o.ok or o.step.may_fail for o in done):
            typer.echo(f'stopped at {done[-1].step.stage}: {done[-1].step.name}')
            raise typer.Exit(code=1)
    typer.echo(f'jubarte {version}: {", ".join(dict.fromkeys(s.stage for s in steps))} done')


if __name__ == '__main__':
    app()
