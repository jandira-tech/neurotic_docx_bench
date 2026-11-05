"""Write a jubarte release's six release_info/ evidence files.

    uv run python -m neurotic_docx_bench.jubarte_release_info 0.11.3 --plan
    uv run python -m neurotic_docx_bench.jubarte_release_info 0.11.3 \
        --engine-dir src/neurotic_docx_bench/utils/jubarte/jubarte-redlines --binary target/release/jubarte
    uv run python -m neurotic_docx_bench.jubarte_release_info 0.11.3 \
        --engine-dir src/neurotic_docx_bench/utils/jubarte/jubarte-redlines            # the GitHub release binary
    scripts/jubarte_release_info.py 0.11.3 --plan   # the same app

The owner's flow, one scoring job at a time (``--only`` / ``--skip`` pick
among the stages, the order never changes). Everything the run makes goes to
``results/release_<version>_evidence/`` (the evidence folder), under names
that carry the version. Stage by owner step:

1. ``sets`` — the fixed evaluation sets (#130, plan 7.3): ``--convert-set``
   (default ``results/sets/convert_860.csv``) and ``--redline-set`` (default
   ``results/sets/redline_600.csv``) are validated against ``sets.json``
   (row counts by state, totals, ``set_version`` pinned to
   ``fixed_sets.SET_VERSION``, every input file hashed against the sha256 the
   set records) and refused on drift, then adopted into the release's own
   evidence lists (``sample_redline_<v>.csv`` in the pool spelling, one
   manifest row per pair under its first key, ``sample_conversion_<v>.csv``)
   with ``set_version`` in ``sample_meta.json``. The old 600/600 draw lives on
   behind ``--draw-sample`` only, for regenerating archived evidence: it
   draws (or adopts) the two ``--n``-item samples of the pre-#130 flow.
2. ``generate`` — redline the set's pairs with the jubarte binary
   (``--binary``, a release candidate built from the release commit: the
   engine's release.sh requires these results before the version bump, so
   the candidate may still report the previous version; the GitHub release
   binary is the default afterwards). Only jubarte: every other vendor's
   lane is read, never run (the vendor refresh, #129).
3. ``export`` — the new redlines to PDF with Word: ``scripts/word_pdf.py``
   batch (``--do-not-close``), then one osascript per document
   (``--no-one-osascript``), ``--timeout 300``, the watchdog on each pass.
   An adopted lane needs neither stage: ``--skip export,generate``.
4. ``measure`` — ``measure.py --sample-csv`` scores the redline set for
   jubarte only (intent-to-treat: a pair without a scored PDF is 0).
5. ``convert`` — ``bench docx-to-pdf --converter … --origin list`` (one
   ``--files-list`` per fixture) converts — and thereby scores — the
   conversion set with jubarte, intent-to-treat.
6. ``write`` — the six files into ``--engine-dir/release_info/``
   (``sample_redline_<v>_<mm-dd-yy_hh-mm>.csv``, ``sample_conversion_…csv``,
   ``results_redline_…json``, ``results_conversion_…json``,
   ``website_data_…jsonl``, ``app_data_…jsonl``), one stamp for all six,
   that version's older stamps deleted; the same six files, same names, same
   bytes, are also filed into the bench's evidence folder
   ``results/release_<v>_evidence/release_info/`` — the copy ``bench report``
   reads for scores.json's sample tables, so ndb and the sites hold one source.
   jubarte's numbers are this run's own; every comparator's are READ from the
   vendor refresh (#129), the newest version per tool present —
   conversions ``results/docx_to_pdf_<tool>_<version>_set-<set>.json``, redlines
   ``results/redlines_0929_full/scores_<tool>-<version>_set-<set>.json`` — and
   a tool the refresh never ran shows as not run, never 0. The two results
   documents record ``set_version``; the sample tables title themselves after
   the fixed sets ("the 860-document set", "the 600-pair set").
7. ``publish`` — the fixed-set flow's own outputs to the results dataset, under
   the layout the vendor lanes use: ``outputs/convert_860/jubarte_<v>/pdf/…``
   (the candidate PDFs), the conversion report and a ``MANIFEST.sha256.json``,
   plus ``outputs/redlines_0929_full/jubarte-<v>/{docx,pdf_by_word,meta}``. The
   upload is verified with ``hub.verify_uploaded`` and the commit it landed on
   is recorded in the release evidence
   (``results/release_<v>_evidence/release_info/hub_outputs.json``), so the
   release shards' file links resolve against that revision and never against a
   moving branch. The stage runs the shared upload path
   (``neurotic_docx_bench.hub_outputs``) — the one the two vendor uploaders use.

The ``install`` stage resolves the binary first: ``--binary PATH`` must run
(whatever version it reports is recorded as ``candidate_reports``); without
it the GitHub release's own binary is downloaded, sha256-checked
(``jubarte_release.github_download``) and must report the release version.

Under ``--draw-sample`` the flow is the pre-#130 one, kept only for
regenerating archived evidence: the ``sample`` stage draws the two samples
(or adopts them, ``--adopt-redline`` / ``--adopt-conversion``), Docxodus
redlines the pairs still missing a Word PDF (fetched from the results dataset
first), Word exports both lanes, ``measure`` scores jubarte then Docxodus,
LibreOffice converts only the fixtures that lack a render and the ``score``
stage scores them — and the write stage builds both comparators from this
run's own artifacts, titled after the drawn samples.

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
import tempfile
import time
import uuid
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from neurotic_docx_bench import hub_outputs, jubarte_release, pipeline, release, word_outputs
from neurotic_docx_bench.jubarte_bench_release import (
    COMPARE_REGEN,
    RUN_DIR,
    Release,
    Step,
    check_compare_regen,
    execute,
)

STAGES = ('install', 'sample', 'sets', 'generate', 'export', 'measure', 'convert', 'score', 'write', 'publish')
# the fixed sets a release runs on (#130, plan 7.3); --draw-sample runs the old draw instead
DEFAULT_CONVERT_SET = Path('results/sets/convert_860.csv')
DEFAULT_REDLINE_SET = Path('results/sets/redline_600.csv')
# the vendor lanes a release READS instead of running them (the vendor refresh, #129):
# redlines scores_<tool>-<version>_set-<set>.json in RUN_DIR, conversions
# docx_to_pdf_<tool>_<version>_set-<set>.json in results/ — the newest version per tool
REDLINE_VENDORS = ('docxodus', 'superdoc', 'apryse')
CONVERT_VENDORS = ('soffice', 'docxide', 'docxodus', 'apryse')
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
SCORE_ONLY_TOOL = 'candidates'  # reports written before the soffice step passed --tool soffice
SOFFICE_VERSION = 'LibreOffice ' + SOFFICE_WORK.name.removeprefix('soffice_').removesuffix('_work')
# generate-native-redlines.ts finds bin/Release/net8.0/docxodus-inproc under it
DOCXODUS_DIST = Path('src/neurotic_docx_bench/utils/docxodus/docxodus-csharp-inproc')
HUB_REPO = 'arthrod/neurotic_docx_bench'
HUB_DOCXODUS = f'outputs/{RUN_DIR.name}/docxodus/pdf_by_word'
# generate-native-redlines.ts errors that are the bench's, not the document's: its worker
# crashed or timed out ("worker exited before reply", "timeout waiting for worker reply"), or a
# process could not start
HARNESS_FAILURE = re.compile(r'worker exited|timeout waiting for worker|ENOENT|EPIPE|ECONNRESET|spawn', re.I)

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


# ------------------------------------------------------------------ the fixed sets

#: which path column of each set CSV pins which sha256 column (fixed_sets._SHA_COLUMNS'
#: spelling; the redline set's oracle fills the two oracle columns, one of which the
#: release_info CSV header spells oracle_pdf_sha256)
SET_SHA_COLUMNS = {
    'convert': {'docx': 'docx_sha256', 'word_pdf': 'word_pdf_sha256'},
    'redline': {'base': 'base_sha256', 'next': 'next_sha256', 'docx': 'docx_sha256',
                'pdf': 'pdf_sha256', 'oracle_pdf': 'oracle_pdf_sha256'},
}


@dataclass(frozen=True)
class SetFacts:
    """A validated fixed set pair (plan 7.1): what a release runs and records."""

    set_version: str
    convert_name: str  # the CSV stem, the sets.json key
    redline_name: str
    convert: list[dict]
    redline: list[dict]


def _pinned_set_version() -> str:
    """The set version the bench pins (fixed_sets.SET_VERSION; imported lazily —
    fixed_sets imports this module)."""
    from neurotic_docx_bench import fixed_sets

    return fixed_sets.SET_VERSION


def validate_sets(root: Path, *, convert_csv: Path, redline_csv: Path, sets_json: Path,
                  want_version: str | None = None) -> SetFacts:
    """Validate the fixed sets against sets.json and refuse on drift (#130).

    Checked: the three files exist; ``set_version`` is the bench's pin (a
    changed set is a new set version, never an edit); every set's row count,
    totals and counts by state match sets.json; and every input file a row
    names is on disk and hashes to the sha256 the set records (the corpus
    drifted, or the corpus is not downloaded). Returns the sets' facts for
    the adopt step and the write stage.
    """
    for path in (convert_csv, redline_csv, sets_json):
        if not path.is_file():
            raise RuntimeError(f'no {rel_path(path, root) if path.is_absolute() else path}: '
                               'the fixed sets a release runs on (results/sets/, plan 7.1)')
    try:
        sets = json.loads(sets_json.read_text())
    except ValueError as exc:
        raise RuntimeError(f'{sets_json} is not JSON: {exc}') from exc
    version = sets.get('set_version')
    if not version:
        raise RuntimeError(f'{sets_json}: no set_version')
    want = _pinned_set_version() if want_version is None else want_version
    if version != want:
        raise RuntimeError(f'{sets_json}: set_version is {version}, the bench pins {want} '
                           '(fixed_sets.SET_VERSION) — a changed set is a new set version, never an edit')
    facts = {}
    for kind, csv_path in (('convert', convert_csv), ('redline', redline_csv)):
        name = csv_path.stem
        rows = read_csv(csv_path)
        counts = state_counts(rows)
        want_counts = (sets.get('counts') or {}).get(name)
        if want_counts is None:
            raise RuntimeError(f'{sets_json}: no counts for {name}')
        if counts != want_counts:
            raise RuntimeError(f'{csv_path}: counts by state drifted from sets.json — {name} holds {counts}, '
                               f'sets.json records {want_counts}')
        total = (sets.get('totals') or {}).get(name)
        if total != len(rows):
            raise RuntimeError(f'{sets_json}: {name} totals {total}, {csv_path.name} holds {len(rows)} rows')
        shas: dict[Path, str] = {}
        for row in rows:
            who = row.get('key') or row.get('stem') or '?'
            for col, sha_col in SET_SHA_COLUMNS[kind].items():
                rel, recorded = (row.get(col) or ''), (row.get(sha_col) or '')
                if not rel or not recorded:
                    raise RuntimeError(f'{csv_path}: row {who}: {col}/{sha_col} is empty — the set pins every input')
                path = root / rel
                if not path.is_file():
                    raise RuntimeError(f'{csv_path}: {rel} (row {who}) is missing — bring the corpus back '
                                       '(uv run bench fixtures download / bench hub get) before a release')
                if path not in shas:
                    shas[path] = _sha(path)
                if shas[path] != recorded:
                    raise RuntimeError(f'{csv_path}: {rel} (row {who}) hashes to {shas[path][:12]}… '
                                       f'but {sha_col} records {recorded[:12]}… — the inputs drifted')
        facts[kind] = rows
    return SetFacts(set_version=version, convert_name=convert_csv.stem, redline_name=redline_csv.stem,
                    convert=facts['convert'], redline=facts['redline'])


def _pool_side(rel: str) -> str:
    """A set CSV path in the pool spelling: relative to corpus/word. A document
    column (base/next) also loses its .docx (fixed_sets._side's rule); the
    docx/pdf columns keep theirs."""
    stripped = rel.removeprefix('corpus/word/')
    return stripped[:-5] if stripped.endswith('.docx') else stripped


def adopt_sets(root: Path, ev: Path, version: str, facts: SetFacts, gen_pairs: Sequence[dict],
               redline_set: Path, convert_set: Path, today: str) -> str:
    """File the fixed sets as this release's evidence lists (#130).

    ``sample_redline_<v>.csv`` carries the set's rows in the pool spelling
    measure.py and the generator expect (shas kept — just validated);
    ``gen_pairs_sample.csv`` redlines each pair once under its FIRST key
    (measure.py's rule); ``sample_conversion_<v>.csv`` is the conversion set
    as drawn. ``sample_meta.json`` records set_version for both. Returns the
    detail line, with the vendor refresh lanes found for the comparators.
    """
    red = [{**r, 'base': _pool_side(r['base']), 'next': _pool_side(r['next']),
            'docx': r['docx'].removeprefix('corpus/word/'),
            'pdf': r['pdf'].removeprefix('corpus/word/')} for r in facts.redline]
    write_csv(root / redline_list(version), GEN_SHA_FIELDS, red)
    by_key = {r['key']: r for r in gen_pairs}
    try:
        keys = sample_first_keys(red, gen_pairs)
    except KeyError as exc:
        raise RuntimeError(f'{redline_set}: the pair {exc.args[0]} is not in {RUN_DIR}/gen_pairs.csv — '
                           'the set and the run directory disagree') from exc
    write_csv(root / ev / 'gen_pairs_sample.csv', GEN_SHA_FIELDS, [by_key[k] for k in keys])
    conv = [{k: r[k] for k in CONVERSION_SHA_FIELDS} for r in facts.convert]
    write_csv(root / conversion_list(version), CONVERSION_SHA_FIELDS, conv)
    pairs = len(keys)
    write_meta(root / ev, 'redline',
               {'set_version': facts.set_version, 'date': today,
                'rule': f'the fixed set {rel_path(redline_set, root)} (set version {facts.set_version}), not drawn',
                'n': len(red), 'pairs': pairs, 'by_state': state_counts(facts.redline)})
    write_meta(root / ev, 'conversion',
               {'set_version': facts.set_version, 'date': today,
                'rule': f'the fixed set {rel_path(convert_set, root)} (set version {facts.set_version}), not drawn',
                'n': len(conv), 'by_state': state_counts(facts.convert)})
    ran_r = _lanes_said(refresh_redline_lanes(root, facts.redline_name), REDLINE_VENDORS)
    ran_c = _lanes_said(refresh_convert_lanes(root, facts.convert_name), CONVERT_VENDORS)
    return (f'{redline_list(version)}: {len(red)} compares of {pairs} pairs '
            f'(the fixed set {facts.redline_name}, set version {facts.set_version}); '
            f'{conversion_list(version)}: {len(conv)} fixtures (the fixed set {facts.convert_name}); '
            f'vendor refresh lanes read at write: redlines {ran_r}, conversions {ran_c}')


# ------------------------------------------------------------------ the vendor refresh lanes

_VERSION = re.compile(r'^\d+(?:\.\d+)*$')
_LANE = re.compile(r'^(?P<tool>.+?)(?P<sep>[-_])(?P<version>\d+(?:\.\d+)*)$')


def _version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split('.'))


def newest_vendor_lanes(folder: Path, *, prefix: str, sep: str, set_name: str) -> dict[str, tuple[str, Path]]:
    """The newest vendor refresh lane per tool: ``{tool: (version, lane file)}`` (#129).

    A release never runs another vendor (#130): the comparator lanes are
    read from the refresh's files, ``<prefix><tool><sep><version>_set-<set_name>.json``
    in ``folder``. The newest version per tool wins (numeric, dot-separated);
    anything that does not name a ``tool<sep><version>`` is not a lane, and a
    tool with no lane is simply absent — not run, never 0.
    """
    suffix = f'_set-{set_name}.json'
    best: dict[str, tuple[tuple[int, ...], str, Path]] = {}
    for path in sorted(folder.glob(f'{prefix}*{suffix}')):
        found = _LANE.match(path.name[len(prefix):-len(suffix)]) if len(path.name) > len(prefix) + len(suffix) else None
        if found is None or found.group('sep') != sep:
            continue
        tool, version = found.group('tool'), found.group('version')
        if tool == 'jubarte' or not _VERSION.fullmatch(version):
            continue
        key = _version_key(version)
        if tool not in best or key > best[tool][0]:
            best[tool] = (key, version, path)
    return {tool: (version, path) for tool, (_, version, path) in best.items()}


def refresh_redline_lanes(root: Path, redline_name: str) -> dict[str, tuple[str, Path]]:
    """The redline refresh lanes: ``RUN_DIR/scores_<tool>-<version>_set-<set>.json``."""
    return newest_vendor_lanes(root / RUN_DIR, prefix='scores_', sep='-', set_name=redline_name)


def refresh_convert_lanes(root: Path, convert_name: str) -> dict[str, tuple[str, Path]]:
    """The conversion refresh lanes: ``results/docx_to_pdf_<tool>_<version>_set-<set>.json``."""
    return newest_vendor_lanes(root / 'results', prefix='docx_to_pdf_', sep='_', set_name=convert_name)


def _lanes_said(lanes: dict[str, tuple[str, Path]], vendors: Sequence[str] = ()) -> str:
    """The refresh lanes as a detail line, one entry per expected ``vendor``:
    an absent one says not run (#130). Without vendors, every lane found."""
    if not vendors:
        return ', '.join(f'{tool} {version}' for tool, (version, _) in sorted(lanes.items())) or 'none'
    return ', '.join(f'{tool} {lanes[tool][0]}' if tool in lanes else f'{tool} not run' for tool in vendors)


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


def snapshot_redlines(docx_dir: Path, ledger: Path) -> str:
    """Record each redline's sha256 before the generator rewrites them."""
    shas = {p.name: _sha(p) for p in sorted(docx_dir.glob('*.docx'))}
    ledger.parent.mkdir(parents=True, exist_ok=True)
    ledger.write_text(json.dumps(shas, indent=1, sort_keys=True) + '\n')
    return f'{len(shas)} redlines on record before generating'


def fresh_failures(failures: Path, since: Path | int) -> list[dict] | None:
    """The generator's ``generate_failures.json`` when this run wrote it, else None.

    ``since`` is the run's start (ns) or a file the run wrote first; an
    older failures file belongs to an earlier run and proves nothing.
    """
    start = since.stat().st_mtime_ns if isinstance(since, Path) else since
    if not failures.is_file() or failures.stat().st_mtime_ns < start:
        return None
    return json.loads(failures.read_text())


def set_aside_stale_pdfs(docx_dir: Path, pdf_dir: Path, ledger: Path,
                         failed: Collection[str] = ()) -> str:
    """Move the Word PDF of every redline whose bytes changed to ``<pdf_dir>_stale/<stamp>/``.

    ``word_pdf.py`` keeps a PDF that already exists, so a redline the new
    candidate rewrote would otherwise be scored on the previous binary's
    export. A PDF with no recorded source bytes counts as changed. The
    redlines named in ``failed`` (docx file names the candidate failed to
    write) still hold the previous binary's bytes: they move to
    ``<docx_dir>_failed/<stamp>/`` with their PDFs, so they score 0. Word
    outputs and redlines are moved aside, never deleted or overwritten.
    """
    before = json.loads(ledger.read_text()) if ledger.is_file() else {}
    stamp = datetime.fromtimestamp(ledger.stat().st_mtime, UTC).strftime('%Y%m%dT%H%M%S') \
        if ledger.is_file() else 'unrecorded'
    aside_root = pdf_dir.with_name(f'{pdf_dir.name}_stale')
    gone = [docx for name in sorted(failed) if (docx := docx_dir / name).is_file()]
    if gone:
        dead = docx_dir.with_name(f'{docx_dir.name}_failed') / stamp
        dead.mkdir(parents=True, exist_ok=True)
        for docx in gone:
            docx.replace(dead / docx.name)
    stale = [pdf for docx in [*gone, *sorted(docx_dir.glob('*.docx'))]
             if (pdf := pdf_dir / f'{docx.stem}.pdf').is_file()
             and (docx in gone or before.get(docx.name) != _sha(docx))]
    aside = aside_root / stamp
    if stale:
        aside.mkdir(parents=True, exist_ok=True)
        for pdf in stale:
            pdf.replace(aside / pdf.name)
    waiting = sum(1 for docx in docx_dir.glob('*.docx') if not (pdf_dir / f'{docx.stem}.pdf').is_file())
    parts = [f'{len(stale)} Word PDFs of changed redlines moved to {aside_root.name}/{stamp}/'
             if stale else 'every exported redline is byte-identical to the one Word exported']
    if gone:
        parts.append(f'{len(gone)} redlines the candidate failed moved to {docx_dir.name}_failed/{stamp}/ '
                     '(they score 0)')
    if waiting:
        parts.append(f'{waiting} redlines await a Word export')
    return '; '.join(parts)


def fresh_conversions(work: Path, binary_sha: str) -> str:
    """Move ``work`` to ``<work's parent>_stale/<stamp>/`` unless ``binary_sha`` filled it.

    ``bench docx-to-pdf`` resumes: it keeps every candidate PDF in its work
    folder and every score its checkpoint holds, so a rebuilt candidate would
    be scored on the previous binary's renders. ``binary.sha256`` records who
    rendered the folder; a crashed run of the same binary still resumes.
    """
    record = work / 'binary.sha256'
    held = record.read_text().strip() if record.is_file() else None
    if held == binary_sha:
        return f'resuming the renders of this binary ({binary_sha[:12]})'
    detail = 'no earlier renders'
    if work.is_dir() and any(work.iterdir()):
        stale_root = work.parent.with_name(f'{work.parent.name}_stale')
        now = datetime.now(UTC).strftime('%Y%m%dT%H%M%S')
        # a set-aside copy is never overwritten: a second move within the second gets a suffix
        stamp = next(s for s in (now, *(f'{now}-{i}' for i in range(2, 1000)))
                     if not (stale_root / s).exists())
        aside = stale_root / stamp / work.name
        aside.parent.mkdir(parents=True)
        work.replace(aside)
        detail = f'renders of binary {(held or "unrecorded")[:12]} moved to {stale_root.name}/{stamp}/'
    work.mkdir(parents=True, exist_ok=True)
    record.write_text(binary_sha + '\n')
    return detail


def read_meta(ev: Path) -> dict:
    path = ev / 'sample_meta.json'
    if not path.is_file():
        raise RuntimeError(f'no {path}: the sets stage writes it (--draw-sample: the sample stage)')
    return json.loads(path.read_text())


def conversion_files(sample_csv: Path) -> list[str]:
    """The ``--files-list`` entries: one corpus docx per sampled fixture."""
    return [r['docx'] for r in read_csv(sample_csv)]


def _is_pdf(path: Path) -> bool:
    """A file that starts like a PDF: an empty or crashed render is not one."""
    with path.open('rb') as fh:
        return fh.read(5) == b'%PDF-'


def _renders(folder: Path) -> dict[str, Path]:
    """The folder's PDFs by lower-cased name, broken renders left out."""
    return {name: path for name, path in _by_lower(folder).items() if _is_pdf(path)}


def soffice_missing(sample_csv: Path, root: Path) -> list[str]:
    """Sampled fixtures with no LibreOffice render (or a broken one) in the soffice work folder."""
    have = _renders(root / SOFFICE_WORK / 'candidate')
    return [r['docx'] for r in read_csv(sample_csv) if f'{r["stem"]}.pdf'.lower() not in have]


def soffice_version(run: release.Runner) -> str | None:
    """``LibreOffice x.y.z.w`` of the soffice ``convert_candidates.py`` renders with."""
    from neurotic_docx_bench.render import soffice as so

    try:
        exe = so.find_soffice()
    except RuntimeError:
        return None
    proc = run([str(exe), '--version'])
    words = (proc.stdout or '').split() if proc.returncode == 0 else []
    return ' '.join(words[:2]) if len(words) >= 2 else None


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
    have = _renders(root / SOFFICE_WORK / 'candidate')  # a broken render scores 0, never as a PDF
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


WORD_FAILED = re.compile(r'(?:FAIL|still failing, so it is the file): (.+?\.docx) — ')


def word_failures(*logs: Path) -> Counter[str]:
    """How often ``word_pdf.py`` logged each document as failed: a pass's own
    FAIL line and its replay's "still failing" line each count once."""
    seen: Counter[str] = Counter()
    for log in logs:
        if log.is_file():
            seen.update(WORD_FAILED.findall(log.read_text(errors='replace')))
    return seen


def record_refusals(root: Path, today: str, logs: Sequence[Path] = ()) -> str:
    """A Docxodus redline Word failed twice by the export ``logs`` (and still
    without a Word PDF) is one Word refused. It is written to the ledger and
    moved out of the export folder, so no later run redlines the pair or opens
    the file again. One without two recorded failures (a pass that died before
    opening it) stays for the next export."""
    lane = root / RUN_DIR / 'docxodus'
    ledger = refused_ledger(root)
    rows = read_csv(ledger) if ledger.is_file() else []
    version = docxodus_version(root)
    failed = word_failures(*logs)
    new = waiting = 0
    for docx in sorted((lane / 'docx').glob('*_docxodus.docx')):
        key = docx.stem.removesuffix('_docxodus')
        if docxodus_pdf(root, key).is_file():
            continue
        if failed[docx.name] < 2:
            waiting += 1
            continue
        rows.append({'key': key, 'tool_version': version, 'docx_sha256': _sha(docx), 'recorded': today})
        dest = lane / 'docx_refused' / docx.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        docx.replace(dest)
        new += 1
    if new:
        write_csv(ledger, REFUSED_FIELDS, rows)
    known = len({r['key'] for r in rows if r['tool_version'] == version})
    said = (f'{new} Docxodus redlines Word refused twice, moved to {RUN_DIR}/docxodus/docx_refused; '
            f'{known} on record for {version or "this Docxodus"} (they score 0 and are not opened again)')
    return said + (f'; {waiting} without a Word PDF and no failure on record stay for the next export'
                   if waiting else '')


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

def _word_pdf_of(folder: Path, original: str) -> Path | None:
    """The PDF Word exported in ``folder`` for the docx named ``original``, following
    the driver's manifest through a trimmed name (#172; ``word_outputs.find_output``)."""
    if not folder.is_dir():
        return None
    return word_outputs.find_output(folder, original, kind='pdf', ext='.pdf')


def _renamed_docx(docx_dir: Path, manifest_dir: Path, original: str) -> Path:
    """The docx named ``original`` under the name Word's driver gave it on disk: a long
    name is trimmed in place, and the rename is a ``renamed`` line in the manifest of
    the folder the PDFs went to (#172)."""
    return docx_dir / word_outputs.current_name(word_outputs.read_manifest(manifest_dir), original)


def redline_rows(sample: Sequence[dict], root: Path, lane: str, gen_pairs: Sequence[dict],
                 fresh: Path, *, with_docxodus: bool = True,
                 docxodus_dir: Path | None = None) -> list[list[str]]:
    """The release_info redline CSV's data rows, from the files on disk now.

    One row per sampled pool key with its own oracle and compare docx/pdf;
    the docxodus and jubarte columns name the pair's first-key files, under
    the names Word's driver gave them (trimmed, ``_byword``; #172).
    ``docxodus_dir`` (the fixed-set flow: the docxodus refresh lane's
    ``pdf_by_word``) names the docxodus PDFs; without it, ``with_docxodus``
    reads the drawn flow's ``docxodus/pdf_by_word`` and ``False`` leaves the
    docxodus columns empty.
    """
    first = first_keys(gen_pairs)
    word = root / 'corpus/word'
    lane_dir = root / RUN_DIR / lane
    if docxodus_dir is not None:
        dx, dx_tool = docxodus_dir, docxodus_dir.parent.name
    else:
        dx, dx_tool = (root / RUN_DIR / 'docxodus' / 'pdf_by_word') if with_docxodus else None, 'docxodus'
    cell = _Cells(root)
    rows = []
    for r in sample:
        kind, oracle = oracle_for(r, fresh, root)
        key = first[r['base'], r['next']]
        original = f'{key}_{lane}.docx'
        rows.append([
            r['key'], *cell(word / f'{r["base"]}.docx'), *cell(word / f'{r["next"]}.docx'),
            *cell(word / r['docx']), *cell(word / r['pdf']),
            r['state'], r['id'], r['sets'], kind,
            *cell(oracle), *cell(_word_pdf_of(dx, f'{key}_{dx_tool}.docx') if dx else None),
            *cell(_renamed_docx(lane_dir / 'docx', lane_dir / 'pdf_by_word', original)),
            *cell(_word_pdf_of(lane_dir / 'pdf_by_word', original)),
        ])
    return rows


def conversion_rows(sample: Sequence[dict], root: Path, jubarte_dir: Path,
                    *, with_soffice: bool = True, soffice_dir: Path | None = None) -> list[list[str]]:
    """The release_info conversion CSV's data rows, from the files on disk now.
    ``soffice_dir`` (the fixed-set flow: the soffice refresh lane's ``candidate``
    folder, #172) names LibreOffice's PDFs; without it ``with_soffice`` reads
    ``SOFFICE_WORK`` and ``False`` leaves the soffice column empty."""
    cell = _Cells(root)
    jubarte = _by_lower(jubarte_dir)
    if soffice_dir is not None:
        soffice = _by_lower(soffice_dir)
    else:
        soffice = _by_lower(root / SOFFICE_WORK / 'candidate') if with_soffice else {}
    return [[r['state'], r['stem'], *cell(root / r['docx']), *cell(root / r['word_pdf']),
             *cell(jubarte.get(f'{r["stem"]}.pdf'.lower())), *cell(soffice.get(f'{r["stem"]}.pdf'.lower()))]
            for r in sample]


# ------------------------------------------------------------------ aggregates

def itt_scores(rows: dict[str, dict], keys: Sequence[str]) -> dict[str, float]:
    """Per-key overall scores (pipeline.overall_from_result, measure.py's rule)
    with 0.0 for every key that scored nothing (intent-to-treat)."""
    return {k: pipeline.overall_from_result(rows[k]) if k in rows else 0.0 for k in keys}


def refresh_scores(rows: dict[str, dict], keys: Sequence[str]) -> dict[str, float]:
    """A vendor refresh lane's own redline scores, only the keys it scored (#130).

    A key the lane never scored stays out of its aggregates — not run, never
    0 (the plan's rule: a release reads its comparators, it does not rerun
    them, and a pair a tool lacks is that tool's absence, not its failure).
    jubarte keeps the intent-to-treat rule above: its own failures are 0s.
    """
    return {k: pipeline.overall_from_result(rows[k]) for k in keys if k in rows}


def report_scores(report: dict, tool: str, stems: Sequence[str]) -> dict[str, float]:
    """A docx_to_pdf report's scores for the sampled fixtures, intent-to-treat: a
    fixture the report leaves out scores 0. Stems are matched whatever their case."""
    per_doc = {str(k).lower(): float(v) for k, v in (_report_tool(report, tool).get('per_doc') or {}).items()}
    return {stem: per_doc.get(stem.lower(), 0.0) for stem in stems}


#: The keys a vendor's docx_to_pdf report may file its scores under: `bench
#: docx-to-pdf` names docxide's lane after its binary, `docxide-pdf` (#169).
REPORT_TOOL_KEYS = {'docxide': ('docxide', 'docxide-pdf')}


def _report_tool(report: dict, tool: str) -> dict:
    """The report's block for ``tool``, under whichever of its known keys the report
    uses (``REPORT_TOOL_KEYS``); refuses a report with none of them, or with two."""
    tools = report.get('tools') or {}
    found = [key for key in REPORT_TOOL_KEYS.get(tool, (tool,)) if key in tools]
    if not found:
        raise RuntimeError(f'the report scores {sorted(tools)}, not {tool}')
    if len(found) > 1:
        raise RuntimeError(f'the report scores {tool} twice, as {found}; keep one')
    return tools[found[0]]


def _score_only_tool(report: dict) -> str:
    """The key a ``--score-only`` report files its PDFs under: ``soffice`` (the step
    passes ``--tool soffice``) or ``candidates`` (reports written before it did)."""
    return 'soffice' if 'soffice' in (report.get('tools') or {}) else SCORE_ONLY_TOOL


def refresh_report_scores(report: dict, tool: str, stems: Sequence[str]) -> dict[str, float]:
    """A conversion refresh lane's scores, only the stems it scored (#130):
    absent means not run (never 0), unlike the intent-to-treat ``report_scores``
    a run's own report gets. Stems are matched whatever their case."""
    per_doc = {str(k).lower(): float(v) for k, v in (_report_tool(report, tool).get('per_doc') or {}).items()}
    return {stem: per_doc[stem.lower()] for stem in stems if stem.lower() in per_doc}


def not_run_block(keys: Sequence[str]) -> dict:
    """A comparator the vendor refresh never ran on the set: not run, never 0 (#130).

    Same shape as ``tool_block``'s, with the aggregates a tool that scored
    nothing cannot have set to None and ``status: not run`` said outright."""
    return {'version': None, 'status': 'not run', 'n': 0, 'not_run': len(keys), 'failures': 0,
            'mean': None, 'median': None, 'exact_100': 0, 'at_least_90': 0, 'median_ci95': None,
            'by_state': {}, 'per_document': {}}


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


def _document_scores(block: dict) -> dict[str, float]:
    """A tool block's per-document scores as floats: the redline results file each as
    ``{'overall': x}``, the conversion results as a bare number."""
    out: dict[str, float] = {}
    for key, value in (block.get('per_document') or {}).items():
        score = value.get('overall') if isinstance(value, dict) else value
        if isinstance(score, (int, float)) and not isinstance(score, bool):
            out[key] = float(score)
    return out


def _ranked(result: dict, rows: list[dict]) -> list[dict]:
    """``rows`` sorted by ITT median and ranked.

    The method note's rule, applied pair by pair (#172): two tools next to each
    other in the order share a rank (``k=``) when the paired bootstrap interval of
    their median difference, over the documents both scored, includes 0; ties chain
    down the order. A pair sharing fewer than ``stats.MIN_PAIRED_DOCS`` documents has
    no interval and never ties. Rows without per-document scores (the drawn-sample
    flow's two rows) fall back to the result's own ``comparison`` interval. A tool
    that was not run (``median`` None, #130) sorts last and carries ``—``.
    """
    rows = sorted(rows, key=lambda row: (row['median'] is None, -(row['median'] or 0.0)))
    scores = [row.pop('_scores', None) or {} for row in rows]
    ci = (result.get('comparison') or {}).get('ci95')
    fallback = bool(ci and ci[0] <= 0 <= ci[1])

    def tied(i: int) -> bool:
        """Whether row ``i`` ties the row ranked just above it."""
        if not scores[i - 1] and not scores[i]:
            return fallback and sum(row['median'] is not None for row in rows) == 2
        pair = paired_interval(scores[i - 1], scores[i])
        return bool(pair and pair['ci95'][0] <= 0 <= pair['ci95'][1])

    ranked = sum(row['median'] is not None for row in rows)
    groups: list[int] = []  # each ranked row's group start
    for i in range(ranked):
        groups.append(groups[i - 1] if i and tied(i) else i)
    sizes = {start: groups.count(start) for start in groups}
    labels = [f'{start + 1}=' if sizes[start] > 1 else str(start + 1) for start in groups]
    return [{'rank': labels[i] if i < ranked else '—'} | row for i, row in enumerate(rows)]


def website_records(version: str, generated: str, redline: dict, conversion: dict,
                    redline_stem: str, conversion_stem: str,
                    set_version: str | None = None) -> list[dict]:
    """facts.jsonl-shaped records for every key the release moves.

    The bench.* values are this run's own numbers; the values the bench
    cannot know before the release exists are placeholders for the site step
    (sync-release.ts) to fill, each marked ``"pending": true`` — the file is
    the checklist, facts.py the writer of data/facts.jsonl itself.
    ``set_version`` names the fixed sets (#130): the tables title themselves
    after the sets ("the N-document set", "the N-pair set") and the
    comparator rows come from the vendor refresh lanes, a tool the refresh
    never ran shown as not run. Without it (the ``--draw-sample`` flow) the
    wording stays the drawn samples'.
    """
    def rec(key: str, value: object, pending: bool = False) -> dict:
        u = uuid.uuid7()
        return {'id': str(u), 'ts': facts_stamp(u), 'key': key, 'value': value,
                'source': f'release_info evidence of jubarte {version} ({generated})'} \
            | ({'pending': True} if pending else {})

    jub_r, jub_c = redline['tools']['jubarte'], conversion['tools']['jubarte']
    doc_r, sof_c = redline['tools'].get('docxodus') or {}, conversion['tools'].get('soffice') or {}
    ran_doc, ran_sof = doc_r.get('status') != 'not run', sof_c.get('status') != 'not run'
    docs, compares = jub_c['n'], jub_r['n']
    pairs = redline['sample'].get('pairs', compares)
    balance = '/'.join(str(block['n']) for block in jub_c['by_state'].values())
    scorer = conversion['versions']['scorer']
    r_ci = _span((redline.get('comparison') or {}).get('ci95'))
    fixed = set_version is not None
    set_bit = f'set {set_version} · ' if fixed else ''

    def row(tool: str, block: dict, *, ours: bool = False, ci_note: bool = False) -> dict:
        """One table row from a tool block; a not-run comparator has no numbers (#130)."""
        if block.get('status') == 'not run':
            return {'tool': tool, 'pin': None, 'median': None, 'mean': None, 'docs': 0,
                    'failed': None, 'note': 'not run on this set (no vendor refresh lane)', 'ours': ours}
        note = (_span(block.get('median_ci95')) if ci_note
                else f"= 100: {block['exact_100']} · ≥ 90: {block['at_least_90']}")
        if block.get('not_run'):
            note += f" · not run: {block['not_run']}"
        return {'tool': tool, 'pin': block['version'], 'median': block['median'], 'mean': block['mean'],
                'docs': block['n'], 'failed': block['failures'], 'note': note, 'ours': ours,
                '_scores': _document_scores(block)}  # read and dropped by _ranked

    if fixed:
        conv_rows = [row('jubarte †', jub_c, ours=True, ci_note=True)] \
            + [row(t, conversion['tools'][t], ci_note=True) for t in CONVERT_VENDORS]
        red_rows = [row(f'jubarte-{version} †', jub_r, ours=True)] \
            + [row(t, redline['tools'][t]) for t in REDLINE_VENDORS]
    else:
        conv_rows = [row('jubarte †', jub_c, ours=True, ci_note=True),
                     row('soffice', sof_c, ci_note=True)]
        red_rows = [row(f'jubarte-{version} †', jub_r, ours=True),
                    row('docxodus', doc_r)]
    tables = [
        {'id': 'conversion-sample',
         'title': (f"DOCX → PDF vs Word's own PDF — the {docs}-document set" if fixed
                   else f"DOCX → PDF vs Word's own PDF — {docs}-document sample"),
         'meta': f'{docs} docs · {balance} by state · {set_bit}scorer {scorer} · {generated}',
         'desc': (f'The fixed {docs}-document conversion set (every path and sha256 in '
                  f'release_info/{conversion_stem}.csv): each converter turns the same DOCX into PDF, '
                  "scored pixel-wise against Word's own export of the same file. jubarte converts and is "
                  'scored by this run, intent-to-treat — a document it fails scores 0; the comparators are '
                  "the vendor refresh's runs on the same set, the newest version per tool, and a document "
                  'a converter did not run is not run, never 0. Sorted by median; 95% CI is a percentile '
                  'bootstrap of the median (2,000 resamples, seed 42).'
                  if fixed else
                  f'A state-balanced {docs}-document sample of corpus/word (every path and sha256 in release_info/{conversion_stem}.csv), '
                  "each converter's PDF scored against Word's own export of the same file. Sorted by ITT median; a failed document "
                  'scores 0. 95% CI is a percentile bootstrap of the ITT median (2,000 resamples, seed 42).'),
         'rows': _ranked(conversion, conv_rows)},
        {'id': 'redlines-sample',
         'title': (f"Redlines vs Word's compare — the {pairs}-pair set" if fixed
                   else f"Redlines vs Word's compare — {pairs}-pair sample"),
         'meta': f'{pairs} pairs · one Word compare each · pixel scorer · opened in Word · {set_bit}{generated}',
         'desc': (f'The fixed {pairs}-pair redline set (every path and sha256 in '
                  f'release_info/{redline_stem}.csv): every jubarte.pro case pair plus pairs drawn from the '
                  'release sample, state-balanced, one Word compare each. Each tool redlines the pair; Word '
                  "opens that redline and exports it to PDF, scored against Word's own compare. jubarte is "
                  'scored by this run, intent-to-treat — a pair without a scored PDF counts 0; the '
                  "comparators are the vendor refresh's runs on the same set, the newest version per tool, "
                  'and a pair a comparator did not run is not run, never 0.'
                  if fixed else
                  f'A sample of {pairs} document pairs of redlines_0929_full, one Word compare each: every pair of the scarce states, '
                  f'the rest spread over the document families (every path and sha256 in release_info/{redline_stem}.csv). '
                  "Each tool redlines the pair; Word opens that redline and exports it to PDF, scored against Word's own compare. "
                  'A pair with no scored PDF counts 0.'),
         'rows': _ranked(redline, red_rows)},
    ]
    def state_median(block: dict, name: str) -> float | None:
        return (block.get('by_state') or {}).get(name, {}).get('median')

    states = [{'name': name, 'n': str(block['n']),
               'rows': [{'tool': 'jubarte †', 'median': jub_c['by_state'][name]['median'], 'ours': True},
                        {'tool': 'soffice',
                         'median': state_median(sof_c, name) if fixed else sof_c['by_state'][name]['median']}]}
              for name, block in sorted(jub_c['by_state'].items())]
    home = [
        {'title': "DOCX → PDF vs Word's own export",
         'meta': (f'{docs}-doc set · median · {generated}' if fixed else f'{docs}-doc sample · median · {generated}'),
         'rows': ([{'name': f'jubarte {version} †', 'v': jub_c['median'], 'ours': True},
                   {'name': sof_c['version'], 'v': sof_c['median']}] if ran_sof
                  else [{'name': f'jubarte {version} †', 'v': jub_c['median'], 'ours': True}])},
        {'title': "Redlines vs Word's compare, opened in Word",
         'meta': (f'{pairs}-pair set · median · {generated}' if fixed else f'{pairs}-pair sample · median · {generated}'),
         'rows': ([{'name': f'jubarte {version} †', 'v': jub_r['median'], 'ours': True},
                   {'name': doc_r['version'], 'v': doc_r['median']}] if ran_doc
                  else [{'name': f'jubarte {version} †', 'v': jub_r['median'], 'ours': True}]),
         **({} if fixed else {'note': "Both groups are the release's samples, state-balanced; "
                                     "the full-corpus tables live in the bench's RESULTS.md."})},
    ]
    headlines = [
        {'label': (f'DOCX → PDF · median, the {docs}-document set' if fixed
                   else f'DOCX → PDF · median, {docs}-doc sample'),
         'value': f"{jub_c['median']:.2f}",
         'vs': (f"{sof_c['version']} {sof_c['median']:.2f}" if ran_sof else 'not run'),
         'sub': (f"{docs} documents of the fixed conversion set (set {set_version}); "
                 f"{jub_c['failures']} jubarte failures. "
                 f"Set list and shas: release_info/{conversion_stem}.csv."
                 if fixed else
                 f"{docs} documents, state-balanced; {jub_c['failures']} jubarte failures. "
                 f"Sample list and shas: release_info/{conversion_stem}.csv.")},
        {'label': (f'Redline vs Word compare · median, the {pairs}-pair set' if fixed
                   else f'Redline vs Word compare · median, {pairs}-pair sample'),
         'value': f"{jub_r['median']:.2f}",
         'vs': (f"{doc_r['version']} {doc_r['median']:.2f}" if fixed and ran_doc
                else (f"Docxodus {doc_r['median']:.2f}" if ran_doc else 'not run')),
         'sub': (f"{pairs} pairs of the fixed redline set (set {set_version}), one Word compare each; "
                 f'paired 95% CI of the difference {r_ci}. '
                 f'Set list and shas: release_info/{redline_stem}.csv.'
                 if fixed else
                 f'{pairs} document pairs, one Word compare each; paired 95% CI of the difference {r_ci}. '
                 f'Sample list and shas: release_info/{redline_stem}.csv.')},
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
        ({'t': 'Fixed sets',
          'd': f"From {version} the tables on this page are the bench's fixed evaluation sets "
               f'(set version {set_version}), the same documents for every release; every row\'s inputs are '
               "sha256-listed in the engine's release_info/. The comparators are the vendor refresh's runs "
               'on the same sets, newest version per tool — a tool the refresh did not run shows as not '
               "run, never 0. Full-corpus runs remain in the bench's RESULTS.md."}
         if fixed else
         {'t': 'Release samples',
          'd': f"From {version} the tables on this page are the release's two samples — "
               "state-balanced, every file sha256-listed in the engine's release_info/. Full-corpus runs "
               "remain in the bench's RESULTS.md."}),
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


def drawn_date(redline: dict, conversion: dict, now: datetime | None = None) -> str:
    """The website's ``bench.generated``: the day the two samples were drawn
    (release_info/README.md: every table names the date its sample was
    drawn), not the day the six are written — a flow that crosses midnight
    UTC wrote the next day's date and the site step refused it (0.14.0, #60).
    Samples drawn on two days have no one date: redraw them. The site holds
    the date only to the samples that name one (jubarte-site
    scripts/check-bench.ts), so one drawn date is the date; today's is used
    only when neither sample names one: the write time's UTC date (``now``,
    as the stamp takes it, else the clock)."""
    dates = {doc.get('sample', {}).get('drawn', {}).get('date') for doc in (redline, conversion)} - {None}
    if len(dates) > 1:
        raise ValueError(f'the samples were drawn on {" and ".join(sorted(dates))}: the site needs one date; '
                         'redraw them in one run')
    if dates:
        return dates.pop()
    return (now.astimezone(UTC) if now else datetime.now(UTC)).date().isoformat()


def write_six(engine_dir: Path, version: str, *, redline: dict, conversion: dict,
              redline_data: Sequence[Sequence[str]], conversion_data: Sequence[Sequence[str]],
              now: datetime | None = None, bench_root: Path | None = None,
              set_version: str | None = None) -> str:
    """Write the six files for ``version`` into engine_dir/release_info/ under one
    stamp, then delete that version's older stamps. With ``bench_root``, the
    same six files (same names, same bytes) are also filed into
    ``<bench_root>/results/release_<version>_evidence/release_info/`` — the
    bench's own copy of the record, which ``bench report`` reads. Returns the
    detail line.

    ``set_version`` (#130) names the fixed sets the run scored; it reaches the
    website records' titles and method note (None — the ``--draw-sample``
    flow — keeps the drawn samples' wording).

    The six are written to a staging folder first and copied out only when all
    six exist: a write that fails halfway (a full disk, an interrupt) leaves
    the previous complete set untouched.
    """
    stamp = stamp_now(now)
    generated = drawn_date(redline, conversion, now)
    folder = engine_dir / 'release_info'
    targets = [folder]
    if bench_root is not None:
        targets.append(bench_root / evidence_dir(version) / 'release_info')
    folder.mkdir(parents=True, exist_ok=True)
    names = {name: f'{name}_{version}_{stamp}.{ext}' for name, ext in SIX}
    staging = Path(tempfile.mkdtemp(prefix=f'.six_{version}_', dir=folder))
    try:
        for name, header, data in (('sample_redline', REDLINE_HEADER, redline_data),
                                   ('sample_conversion', CONVERSION_HEADER, conversion_data)):
            with (staging / names[name]).open('w', newline='') as fh:
                writer = csv.writer(fh)
                writer.writerow(header)
                writer.writerows(data)
        for name, doc, csv_name in (('results_redline', redline, names['sample_redline']),
                                    ('results_conversion', conversion, names['sample_conversion'])):
            doc = dict(doc)
            doc['stamp'] = stamp
            doc['sample'] = doc['sample'] | {'csv': csv_name, 'sha256': _sha(staging / csv_name)}
            (staging / names[name]).write_text(json.dumps(doc, indent=1, sort_keys=True) + '\n')
        with (staging / names['website_data']).open('w') as fh:
            for record in website_records(version, generated, redline, conversion,
                                          Path(names['sample_redline']).stem, Path(names['sample_conversion']).stem,
                                          set_version=set_version):
                fh.write(json.dumps(record, ensure_ascii=False) + '\n')
        with (staging / names['app_data']).open('w') as fh:
            for record in app_records(version):
                fh.write(json.dumps(record, ensure_ascii=False) + '\n')
        for target in targets:
            target.mkdir(parents=True, exist_ok=True)
            for name in names.values():
                shutil.copyfile(staging / name, target / name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    ours = '|'.join(name for name, _ in SIX)
    pattern = re.compile(rf'({ours})_{re.escape(version)}_\d{{2}}-\d{{2}}-\d{{2}}_\d{{2}}-\d{{2}}\.(csv|json|jsonl)')
    for target in targets:
        for old in target.iterdir():
            if pattern.fullmatch(old.name) and old.name not in names.values():
                old.unlink()
    filed = ' + '.join(str(t) for t in targets)
    return f'{filed}: six files of {version} ({stamp})'


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
    measured = {tool: json.loads((root / scores_json(tool, version)).read_text()) for tool in (lane, 'docxodus')}
    rows = {tool: doc['rows'] for tool, doc in measured.items()}
    a = itt_scores(rows[lane], keys)
    b = itt_scores(rows['docxodus'], keys)
    versions = json.loads((root / RUN_DIR / 'versions.json').read_text()) \
        if (root / RUN_DIR / 'versions.json').is_file() else {}
    # measure.py ran in its own process (under --device): its summary names the backend
    scorer = one_backend({tool: doc.get('summary', {}).get('scorer_backend') for tool, doc in measured.items()})
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
        'versions': {'scorer': one_backend({'jubarte': jub_report.get('scorer_backend'),
                                            'soffice': sof_report.get('scorer_backend')}),
                     'microsoft_word': word_version, 'libreoffice': soffice_version, 'docxodus': None},
        'provenance': {
            'measure': 'bench docx-to-pdf --origin list (one --files-list per fixture); '
                       f'soffice --score-only --tool soffice --location-to-score {ev}/soffice_sample',
            'scores': {'jubarte': str(conversion_report('jubarte', version)),
                       'soffice': str(conversion_report('soffice', version))},
        },
    }
    return redline, conversion


def collect_set_results(root: Path, version: str, lane: str, *, jubarte: dict, facts: SetFacts,
                        word_version: str | None, fresh: Path = COMPARE_REGEN / 'out') -> tuple[dict, dict]:
    """The fixed-set flow's two results documents (#130).

    jubarte's numbers are this run's own (redlines intent-to-treat, its
    conversion report intent-to-treat); every comparator's are READ from the
    vendor refresh lanes (#129), the newest version per tool present, and a
    key the lane never scored stays out of that tool's aggregates — not run,
    never 0 — with ``not_run`` counting them. Both documents record the
    ``set_version`` under ``sample``. Refuses when a whole side has no lane at
    all: the engine gate needs a comparator beside jubarte.
    """
    ev = evidence_dir(version)
    meta = read_meta(root / ev)
    identity = {'version': f'jubarte {version}'} | jubarte
    sample_rows = read_csv(root / redline_list(version))
    keys = [r['key'] for r in sample_rows]
    key_state = {r['key']: r['state'] for r in sample_rows}
    measured = json.loads((root / scores_json(lane, version)).read_text())
    a = itt_scores(measured.get('rows') or {}, keys)
    generated = datetime.now(UTC).isoformat(timespec='seconds')

    red_lanes = refresh_redline_lanes(root, facts.redline_name)
    if not any(vendor in red_lanes for vendor in REDLINE_VENDORS):
        raise RuntimeError(f'no vendor refresh lane for {facts.redline_name} in {RUN_DIR} '
                           f'(scores_<tool>-<version>_set-{facts.redline_name}.json, #129): a release '
                           'reads its comparators and runs jubarte only')
    # the scorer of this run's own artifacts; each refresh lane names its own in its block
    # (the refresh is another campaign — its backend is recorded, never required to match)
    backends = {lane: measured.get('summary', {}).get('scorer_backend')}
    tools = {'jubarte': tool_block(identity, a, key_state, {k: {'overall': v} for k, v in a.items()})}
    scores_by = {}
    provenance = {lane: str(scores_json(lane, version))}
    for vendor in REDLINE_VENDORS:
        if vendor not in red_lanes:
            tools[vendor] = not_run_block(keys)
            continue
        lane_version, lane_path = red_lanes[vendor]
        doc = json.loads((root / lane_path).read_text())
        scores_by[vendor] = refresh_scores(doc.get('rows') or {}, keys)
        state = {k: key_state[k] for k in scores_by[vendor]}
        block = tool_block({'version': f'{vendor} {lane_version}', 'commit': None, 'binary_sha256': None},
                           scores_by[vendor], state, {k: {'overall': v} for k, v in scores_by[vendor].items()})
        if lane_backend := doc.get('summary', {}).get('scorer_backend'):
            block['scorer'] = lane_backend
        if len(scores_by[vendor]) != len(keys):
            block['not_run'] = len(keys) - len(scores_by[vendor])
        tools[vendor] = block
        provenance[vendor] = rel_path(lane_path, root)
    comparison = ({'comparator': 'docxodus', **(paired_interval(a, scores_by['docxodus']) or {})}
                  if 'docxodus' in scores_by else None)
    redline = {
        'schema': 'jubarte-redlines/release_info/results_redline/1',
        'release': version,
        'stamp': None,
        'generated': generated,
        'sample': {'n': len(keys), 'pairs': len({(r['base'], r['next']) for r in sample_rows}),
                   'set': facts.redline_name, 'set_version': facts.set_version, 'drawn': meta['redline']},
        'tools': tools,
        'comparison': comparison,
        'versions': {'scorer': one_backend(backends), 'microsoft_word': word_version, 'libreoffice': None,
                     'docxodus': red_lanes.get('docxodus', (None,))[0]},
        'provenance': {
            'measure': f'{RUN_DIR}/measure.py --fresh {rel_path(fresh, root)} --sample-csv {redline_list(version)} '
                       f'(jubarte only); comparators read from the vendor refresh lanes (#129), '
                       'newest version per tool',
            'scores': provenance,
        },
    }

    conv_rows = read_csv(root / conversion_list(version))
    stems = [r['stem'] for r in conv_rows]
    conv_state = {r['stem']: r['state'] for r in conv_rows}
    jub_report = json.loads((root / conversion_report('jubarte', version)).read_text())
    ja = report_scores(jub_report, 'jubarte', stems)  # its own run: intent-to-treat
    conv_lanes = refresh_convert_lanes(root, facts.convert_name)
    if not any(vendor in conv_lanes for vendor in CONVERT_VENDORS):
        raise RuntimeError(f'no vendor refresh lane for {facts.convert_name} in results/ '
                           f'(docx_to_pdf_<tool>_<version>_set-{facts.convert_name}.json, #129): a release '
                           'reads its comparators and runs jubarte only')
    c_backends = {'jubarte': jub_report.get('scorer_backend')}
    c_tools = {'jubarte': tool_block(identity, ja, conv_state, dict(ja))}
    c_scores_by = {}
    c_provenance = {'jubarte': str(conversion_report('jubarte', version))}
    for vendor in CONVERT_VENDORS:
        if vendor not in conv_lanes:
            c_tools[vendor] = not_run_block(stems)
            continue
        lane_version, lane_path = conv_lanes[vendor]
        report = json.loads((root / lane_path).read_text())
        c_scores_by[vendor] = refresh_report_scores(report, vendor, stems)
        state = {k: conv_state[k] for k in c_scores_by[vendor]}
        # the lane's own version string when it carries one, else its file name's
        said = _report_tool(report, vendor).get('version') or f'{vendor} {lane_version}'
        block = tool_block({'version': said, 'commit': None, 'binary_sha256': None},
                           c_scores_by[vendor], state, dict(c_scores_by[vendor]))
        if lane_backend := report.get('scorer_backend'):
            block['scorer'] = lane_backend
        if len(c_scores_by[vendor]) != len(stems):
            block['not_run'] = len(stems) - len(c_scores_by[vendor])
        c_tools[vendor] = block
        c_provenance[vendor] = rel_path(lane_path, root)
    c_comparison = ({'comparator': 'soffice', **(paired_interval(ja, c_scores_by['soffice']) or {})}
                    if 'soffice' in c_scores_by else None)
    conversion = {
        'schema': 'jubarte-redlines/release_info/results_conversion/1',
        'release': version,
        'stamp': None,
        'generated': generated,
        'sample': {'n': len(stems), 'set': facts.convert_name, 'set_version': facts.set_version,
                   'drawn': meta['conversion']},
        'tools': c_tools,
        'comparison': c_comparison,
        'versions': {'scorer': one_backend(c_backends), 'microsoft_word': word_version,
                     'libreoffice': (c_tools['soffice']['version'] if 'soffice' in c_scores_by else None),
                     'docxodus': conv_lanes.get('docxodus', (None,))[0]},
        'provenance': {
            'measure': 'bench docx-to-pdf --origin list (one --files-list per fixture), jubarte only; '
                       'comparators read from the vendor refresh lanes (#129), newest version per tool',
            'scores': c_provenance,
        },
    }
    return redline, conversion


def engine_commit(engine_dir: Path | None,
                  run: Callable[..., release.ProcLike] | None = None,
                  ref: str | None = None) -> str | None:
    """The commit the scored binary was built from, resolved in --engine-dir.

    ``ref`` (--engine-commit) names it; without one the checkout's HEAD is
    taken, which is right only while the checkout has not moved since the
    candidate was built. A ref that does not resolve is an error.
    """
    if engine_dir is None:
        return None
    proc = (run or release.default_runner())(
        ['git', '-C', str(engine_dir), 'rev-parse', '--verify', f'{ref or "HEAD"}^{{commit}}'])
    if proc.returncode == 0:
        return proc.stdout.strip()
    if ref is not None:
        raise RuntimeError(f'--engine-commit {ref} is not a commit of {engine_dir}')
    return None


def binary_reports(binary: Path, run: Callable[..., release.ProcLike] | None = None) -> str:
    """What ``binary --version`` prints (its first line); raises when it does not run."""
    if not binary.is_file():
        raise RuntimeError(f'no such binary: {binary}')
    proc = (run or release.default_runner())([str(binary), '--version'])
    lines = (proc.stdout or '').strip().splitlines()
    if proc.returncode != 0 or not lines:
        raise RuntimeError(f'{binary} --version does not answer (exit {proc.returncode})')
    return lines[0].strip()


def one_backend(found: dict[str, str | None]) -> str:
    """The scorer backend every score artifact records (``unrecorded`` when none does).

    Each artifact names the backend of the process that scored it; the
    writer's own process never ran a scorer, so its backend proves nothing.
    """
    kinds = {backend or 'unrecorded' for backend in found.values()}
    if len(kinds) != 1:
        raise RuntimeError(f'score artifacts disagree on the scorer backend: {found}')
    return kinds.pop()


# ------------------------------------------------------------------ plan/execute

def plan(rel: Release, *, binary: Path | None = None, seed: int = DEFAULT_SEED,
         n: int = DEFAULT_N, device: str = 'mps', conversion: Sequence[str] | None = None,
         engine_dir: Path | None = None, engine_ref: str | None = None,
         adopt_redline_csv: Path | None = None, adopt_conversion_list: Path | None = None,
         jobs: int = DEFAULT_JOBS, convert_workers: int = DEFAULT_CONVERT_WORKERS,
         hub: Hub | None = None, compare_regen: Path = COMPARE_REGEN,
         run: Callable[..., release.ProcLike] | None = None, draw_sample: bool = False,
         convert_set: Path | None = None, redline_set: Path | None = None,
         api: Any | None = None) -> list[Step]:
    """Every step of every stage, in order.

    The fixed-set flow (#130): a ``sets`` stage validates and adopts the two
    committed sets, only jubarte is generated, exported, measured, converted
    and scored, and the write stage reads every comparator from the vendor
    refresh lanes (#129). ``draw_sample=True`` is the pre-#130 flow — the
    600/600 draw (or adoption), the docxodus generate-missing and soffice
    render-missing paths — kept only for regenerating archived evidence.
    ``convert_set``/``redline_set`` (default ``results/sets/*.csv``) name the
    fixed sets; passing either with ``draw_sample`` is an error, and so is
    adopting lists without it.

    ``conversion`` lists the conversion sample's corpus docx (one
    ``--files-list`` flag each); when None the plan reads the evidence
    folder's ``sample_conversion_<v>.csv``, else the list being adopted, and
    falls back to a placeholder so ``--plan`` still prints before the sets
    (or sample) stage ran. ``hub`` is the results dataset (None: local files
    only; the draw flow's docxodus fetch is its only user). ``api`` is the
    results dataset client the publish stage uploads through (None: the real
    one, created when the stage runs).
    """
    if draw_sample and (convert_set is not None or redline_set is not None):
        raise ValueError('--draw-sample runs the old 600/600 draw; --convert-set/--redline-set name the '
                         'fixed sets of the default flow')
    if not draw_sample and (adopt_redline_csv is not None or adopt_conversion_list is not None):
        raise ValueError('--adopt-redline/--adopt-conversion belong to the --draw-sample flow')
    convert_set = convert_set if convert_set is not None else DEFAULT_CONVERT_SET
    redline_set = redline_set if redline_set is not None else DEFAULT_REDLINE_SET
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
        # no SOFFICE_WORK: it is git-ignored, and the convert stage renders what it lacks
        for need in (RUN_DIR / 'pool_pairs.csv', RUN_DIR / 'gen_pairs.csv', Path('corpus/word')):
            if not (root / need).exists():
                raise RuntimeError(f'missing {need}')
        # the measure stage reads out/ and regen_list.csv after the Word export (#82)
        regen = check_compare_regen(root / compare_regen)
        for adopted in (adopt_r, adopt_c):
            if adopted is not None and not adopted.is_file():
                raise RuntimeError(f'no such list to adopt: {adopted}')
        return f'{RUN_DIR} + corpus/word present; {regen}'

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

    def generate(tool: str, method: str, dist: Path, manifest: Path,
                 run_dir: Path | None = None) -> tuple[str, ...]:
        return ('node', '--import', 'tsx', 'scripts/generate-native-redlines.ts',
                '--method', method,
                '--dist', str(dist),
                '--tool', tool,
                '--manifest', str(manifest),
                '--source-dir', 'corpus/word',
                '--out', str(RUN_DIR / tool / 'docx'),
                '--run-dir', str(run_dir or RUN_DIR / tool))

    def docxodus_fetch() -> str:
        return fetch_docxodus(root / redline_csv, root, gen_rows(), root / ev, hub)

    def docxodus_manifest() -> str:
        rows = docxodus_missing(root / redline_csv, root, gen_rows())
        write_csv(root / ev / 'gen_pairs_docxodus_missing.csv', GEN_SHA_FIELDS, gen_with_shas(rows, root))
        return f'{ev}/gen_pairs_docxodus_missing.csv: {len(rows)} pairs without a docxodus Word PDF'

    # its own run dir: the lane's generate_failures.json is the full corpus run's record
    docxodus_generate = generate('docxodus', 'docxodus-csharp-inproc', DOCXODUS_DIST,
                                 ev / 'gen_pairs_docxodus_missing.csv', ev / 'docxodus_generate')

    def docxodus_redlines() -> str:
        # the generator exits 1 when it writes nothing, so an empty manifest must not reach it
        rows = read_csv(root / ev / 'gen_pairs_docxodus_missing.csv')
        if not rows:
            return 'no pair lacks a docxodus Word PDF: nothing to redline'
        started = time.time_ns()
        proc = (run or release.default_runner())(list(docxodus_generate), cwd=root)
        (root / ev / 'docxodus.generate.log').write_text((proc.stdout or '') + (proc.stderr or ''))
        # it also exits 1 when Docxodus fails every pair: those score 0, like any Docxodus failure,
        # once this run's own failures file names exactly these pairs, each with a document error
        # (a worker crash or timeout is the bench's failure, not Docxodus's)
        failed = fresh_failures(root / ev / 'docxodus_generate' / 'generate_failures.json', started)
        if proc.returncode != 0 and failed is not None:
            docs = {f['doc'] for f in failed}
            own = {f['doc'] for f in failed if f.get('stage') == 'generate' and not HARNESS_FAILURE.search(f['error'])}
            if docs == own == {r['key'] for r in rows}:
                return f'{len(rows)} pairs Docxodus itself fails to redline (they score 0); none redlined'
        if proc.returncode != 0:
            raise RuntimeError(f'{" ".join(docxodus_generate)}: exit {proc.returncode} '
                               f'(see {ev}/docxodus.generate.log)')
        return f'{len(rows)} pairs redlined by Docxodus: {" ".join(docxodus_generate)}'

    def stale_aside() -> str:
        # with --force a pair the candidate failed keeps the previous binary's redline: by the
        # failures file the generator wrote after the snapshot, it scores 0 instead
        ledger = root / ev / 'redlines_before.json'
        failed = fresh_failures(root / jub / 'generate_failures.json', ledger) if ledger.is_file() else None
        names = [f'{f["doc"]}_{lane}.docx' for f in failed or ()]
        return set_aside_stale_pdfs(root / jub / 'docx', root / jub / 'pdf_by_word', ledger, names)

    def soffice_list() -> str:
        missing = soffice_missing(root / conversion_csv, root)
        (root / ev / 'soffice_missing.txt').write_text(''.join(f'{docx}\n' for docx in missing))
        said = f'{ev}/soffice_missing.txt: {len(missing)} fixtures without a LibreOffice render'
        if not missing:
            return said
        # the set is scored as SOFFICE_VERSION: a render of another build must not join it
        found = soffice_version(run or release.default_runner())
        if found != SOFFICE_VERSION:
            raise RuntimeError(f'{len(missing)} fixtures need a render, but soffice is {found or "absent"}, '
                               f'not {SOFFICE_VERSION}')
        return f'{said} ({found} renders them)'

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
                    'commit': engine_commit(engine_dir, run, engine_ref)}
        redline, conversion_doc = collect_results(
            root, v, lane, jubarte=identity, fresh=fresh,
            word_version=release.word_version(run or release.default_runner()))
        detail = write_six(
            engine_dir, v, bench_root=root, redline=redline, conversion=conversion_doc,
            redline_data=redline_rows(read_csv(root / redline_csv), root, lane, gen_rows(), fresh),
            conversion_data=conversion_rows(read_csv(root / conversion_csv), root,
                                            root / ev / 'convert_work' / 'jubarte' / 'candidate'))
        return f'{detail}; binary {identity["binary_sha256"][:12]} reports "{identity["candidate_reports"]}"'

    # ------------------------------------------------- the fixed-set flow's steps (#130)

    cset, rset = given(convert_set), given(redline_set)
    sjson = cset.parent / 'sets.json'

    def facts() -> SetFacts:
        # validated fresh by every step that needs them: drift between two stages of one
        # release is caught at the next one that looks (and each stage is independently runnable)
        return validate_sets(root, convert_csv=cset, redline_csv=rset, sets_json=sjson)

    def validate_action() -> str:
        found = facts()
        ran_r = _lanes_said(refresh_redline_lanes(root, found.redline_name), REDLINE_VENDORS)
        ran_c = _lanes_said(refresh_convert_lanes(root, found.convert_name), CONVERT_VENDORS)
        return (f'{rel_path(rset, root)}: {len(found.redline)} compares, set version {found.set_version} '
                f'(by state {state_counts(found.redline)}); {rel_path(cset, root)}: {len(found.convert)} '
                f'fixtures (by state {state_counts(found.convert)}); vendor refresh lanes: '
                f'redlines {ran_r}; conversions {ran_c}')

    def adopt_action() -> str:
        return adopt_sets(root, ev, v, facts(), gen_rows(), rset, cset, today)

    def write_action_sets() -> str:
        if engine_dir is None:
            raise RuntimeError('the write stage needs --engine-dir (the checkout whose release_info/ it fills)')
        exe = binary_path()
        identity = {'candidate_reports': binary_reports(exe, run), 'binary_sha256': _sha(exe),
                    'commit': engine_commit(engine_dir, run, engine_ref)}
        found = facts()
        redline, conversion_doc = collect_set_results(
            root, v, lane, jubarte=identity, facts=found, fresh=fresh,
            word_version=release.word_version(run or release.default_runner()))
        # the sample CSVs name the comparators' files from their refresh lanes (#172)
        dx_lane = refresh_redline_lanes(root, found.redline_name).get('docxodus')
        sof_lane = refresh_convert_lanes(root, found.convert_name).get('soffice')
        detail = write_six(
            engine_dir, v, bench_root=root, redline=redline, conversion=conversion_doc,
            set_version=found.set_version,
            redline_data=redline_rows(
                read_csv(root / redline_csv), root, lane, gen_rows(), fresh, with_docxodus=False,
                docxodus_dir=(root / RUN_DIR / f'docxodus-{dx_lane[0]}' / 'pdf_by_word') if dx_lane else None),
            conversion_data=conversion_rows(
                read_csv(root / conversion_csv), root, root / ev / 'convert_work' / 'jubarte' / 'candidate',
                with_soffice=False,
                soffice_dir=(root / 'results' / f'soffice_{sof_lane[0]}_work' / 'candidate') if sof_lane else None))
        return f'{detail}; binary {identity["binary_sha256"][:12]} reports "{identity["candidate_reports"]}"'

    def publish_action() -> str:
        """Upload the release's own outputs; record the revision they landed on."""
        evidence = hub_outputs.publish_release(root, v, api=api)
        where = ', '.join(evidence['paths'])
        return (f'{evidence["n_files"]} file(s) uploaded and verified at '
                f'{evidence["revision"]} ({where})')

    adopting = 'adopt' if adopt_r is not None else 'draw', 'adopt' if adopt_c is not None else 'draw'
    draw_steps = [
        Step('install', 'candidate binary' if binary is not None else 'release binary', action=install),
        Step('sample', 'bench inputs', action=check_inputs, preflight=True),
        Step('sample', f'{adopting[0]} redline sample', action=redline_sample),
        Step('sample', f'{adopting[1]} conversion sample', action=conversion_sample),
        Step('generate', 'generator dist', action=generator_dist),
        Step('generate', 'redline snapshot',
             action=lambda: snapshot_redlines(root / jub / 'docx', root / ev / 'redlines_before.json')),
        # --force: a rerun with a new candidate must not keep the previous binary's redlines
        Step('generate', 'jubarte redlines',
             (*generate(lane, 'jubarte-rust', ev / 'dist', ev / 'gen_pairs_sample.csv'), '--force'),
             log=ev / f'{lane}.generate.log'),
        Step('generate', 'stale Word PDFs aside', action=stale_aside),
        Step('generate', 'docxodus PDFs from the hub', action=docxodus_fetch),
        Step('generate', 'docxodus manifest', action=docxodus_manifest),
        Step('generate', 'docxodus redlines (missing only)', docxodus_generate, action=docxodus_redlines),
        Step('export', 'word answers', action=word, preflight=True),
        Step('export', 'word export jubarte (batch)',
             (*word_pdf(jub / 'docx', jub / 'pdf_by_word', 'jubarte'), '--log', str(jub / 'word_pdf.sample.log')),
             log=jub / 'word_pdf.sample.out', watch=(jub / 'word_pdf.sample.log',), may_fail=True,
             refusal_codes=(2,)),
        Step('export', 'word export jubarte (one osascript per document)',
             (*word_pdf(jub / 'docx', jub / 'pdf_by_word', 'jubarte'), '--no-one-osascript',
              '--log', str(jub / 'word_pdf.sample.retry.log')),
             log=jub / 'word_pdf.sample.retry.out', watch=(jub / 'word_pdf.sample.retry.log', jub / 'pdf_by_word'),
             may_fail=True),
        # the docxodus lane is shared by every release: its logs carry this one's version
        Step('export', 'word export docxodus (batch)',
             (*word_pdf(dx / 'docx', dx / 'pdf_by_word', 'docxodus'), '--log', str(dx / f'word_pdf.sample_{v}.log')),
             log=dx / f'word_pdf.sample_{v}.out', watch=(dx / f'word_pdf.sample_{v}.log',), may_fail=True,
             refusal_codes=(2,)),
        Step('export', 'word export docxodus (one osascript per document)',
             (*word_pdf(dx / 'docx', dx / 'pdf_by_word', 'docxodus'), '--no-one-osascript',
              '--log', str(dx / f'word_pdf.sample_{v}.retry.log')),
             log=dx / f'word_pdf.sample_{v}.retry.out',
             watch=(dx / f'word_pdf.sample_{v}.retry.log', dx / 'pdf_by_word'), may_fail=True),
        Step('export', 'word refusals docxodus',
             action=lambda: record_refusals(root, today, (root / dx / f'word_pdf.sample_{v}.log',
                                                          root / dx / f'word_pdf.sample_{v}.retry.log'))),
        # one scoring job at a time: each measure finishes before the next starts
        Step('measure', 'measure jubarte', measure(lane), log=ev / f'measure_{lane}.log'),
        Step('measure', 'measure docxodus', measure('docxodus'), log=ev / 'measure_docxodus.log'),
        Step('convert', 'stale renders aside',
             action=lambda: fresh_conversions(root / ev / 'convert_work' / 'jubarte', _sha(binary_path()))),
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
             (*bench, 'docx-to-pdf', '--score-only', '--tool', 'soffice',
              '--tool-version', SOFFICE_VERSION,
              '--location-to-score', str(ev / 'soffice_sample'),
              '--origin', 'list', *files,
              '--work-dir', str(ev / 'soffice_score_work'),
              '--json', str(conversion_report('soffice', v)),
              '--jobs', str(jobs)),
             log=ev / f'score_soffice_{v}.log'),
        Step('write', 'release_info', action=write_action),
    ]
    if draw_sample:
        return draw_steps
    # the fixed-set flow (#130): the sets stage replaces the draw, only jubarte is run,
    # every comparator is read from the vendor refresh lanes at write
    return [
        Step('install', 'candidate binary' if binary is not None else 'release binary', action=install),
        Step('sets', 'bench inputs', action=check_inputs, preflight=True),
        Step('sets', 'validate the fixed sets', action=validate_action),
        Step('sets', 'adopt the fixed sets', action=adopt_action),
        Step('generate', 'generator dist', action=generator_dist),
        Step('generate', 'redline snapshot',
             action=lambda: snapshot_redlines(root / jub / 'docx', root / ev / 'redlines_before.json')),
        # --force: a rerun with a new candidate must not keep the previous binary's redlines
        Step('generate', 'jubarte redlines',
             (*generate(lane, 'jubarte-rust', ev / 'dist', ev / 'gen_pairs_sample.csv'), '--force'),
             log=ev / f'{lane}.generate.log'),
        Step('generate', 'stale Word PDFs aside', action=stale_aside),
        Step('export', 'word answers', action=word, preflight=True),
        Step('export', 'word export jubarte (batch)',
             (*word_pdf(jub / 'docx', jub / 'pdf_by_word', 'jubarte'), '--log', str(jub / 'word_pdf.sample.log')),
             log=jub / 'word_pdf.sample.out', watch=(jub / 'word_pdf.sample.log',), may_fail=True,
             refusal_codes=(2,)),
        Step('export', 'word export jubarte (one osascript per document)',
             (*word_pdf(jub / 'docx', jub / 'pdf_by_word', 'jubarte'), '--no-one-osascript',
              '--log', str(jub / 'word_pdf.sample.retry.log')),
             log=jub / 'word_pdf.sample.retry.out', watch=(jub / 'word_pdf.sample.retry.log', jub / 'pdf_by_word'),
             may_fail=True),
        # one scoring job at a time, and jubarte is the only one measured: the
        # comparators' lanes are read at write, never run (#129, #130)
        Step('measure', 'measure jubarte', measure(lane), log=ev / f'measure_{lane}.log'),
        Step('convert', 'stale renders aside',
             action=lambda: fresh_conversions(root / ev / 'convert_work' / 'jubarte', _sha(binary_path()))),
        # converting with bench docx-to-pdf scores right after the last fixture — that is the
        # score stage too; LibreOffice's numbers come from the vendor refresh lanes
        Step('convert', 'convert jubarte (converts + scores)',
             (*bench, 'docx-to-pdf', '--converter', str(binary_path()), '--origin', 'list', *files,
              '--work-dir', str(ev / 'convert_work'),
              '--json', str(conversion_report('jubarte', v)),
              '--jobs', str(jobs), '--convert-workers', str(convert_workers)),
             log=ev / f'convert_jubarte_{v}.log'),
        Step('write', 'release_info', action=write_action_sets),
        # the release's own outputs to the results dataset, under the layout the
        # vendor lanes use; the revision they landed on is recorded, so the
        # release shards' file links never point at a moving branch (#143)
        Step('publish', 'upload the jubarte lane to the results dataset', action=publish_action),
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
    engine_ref: str = typer.Option(None, '--engine-commit',
                                   help='the commit --binary was built from (default: the --engine-dir HEAD, '
                                        'wrong once the checkout moves on)'),
    binary: Path = typer.Option(None, '--binary',
                                help='a release candidate built from the release commit; any version it reports '
                                     'is accepted and recorded (default: the GitHub release binary)'),
    seed: int = typer.Option(DEFAULT_SEED, '--seed', help='the sample draw seed (--draw-sample only)'),
    n: int = typer.Option(DEFAULT_N, '--n', help='items in each sample (--draw-sample only)'),
    adopt_redline_csv: Path = typer.Option(None, '--adopt-redline',
                                           help='a CSV with a key column: the redline sample, instead of drawing '
                                                '(--draw-sample only; a relative path is from the bench root)'),
    adopt_conversion_list: Path = typer.Option(None, '--adopt-conversion',
                                               help='a file of corpus/word/<state>/docx/<stem>.docx lines: the '
                                                    'conversion sample, instead of drawing (--draw-sample only)'),
    draw_sample: bool = typer.Option(False, '--draw-sample',
                                      help='the pre-#130 flow: draw the 600/600 samples (or adopt lists), '
                                           'measure docxodus and render what soffice lacks — for regenerating '
                                           'archived evidence only'),
    convert_set: Path = typer.Option(None, '--convert-set',
                                     help=f'the fixed conversion set CSV (default: {DEFAULT_CONVERT_SET})'),
    redline_set: Path = typer.Option(None, '--redline-set',
                                     help=f'the fixed redline set CSV (default: {DEFAULT_REDLINE_SET})'),
    jobs: int = typer.Option(DEFAULT_JOBS, '--jobs', help='scorer jobs of measure.py and docx-to-pdf'),
    convert_workers: int = typer.Option(DEFAULT_CONVERT_WORKERS, '--convert-workers',
                                        help='parallel convert processes'),
    device: str = typer.Option('mps', '--device', help='scorer kernels for measure.py'),
    use_hub: bool = typer.Option(True, '--hub/--no-hub',
                                 help='fetch the Docxodus Word PDFs the sample lacks from the results dataset'),
    only: str = typer.Option('', '--only', help=f'comma list of stages to run ({", ".join(STAGES)})'),
    skip: str = typer.Option('', '--skip', help='comma list of stages to leave out'),
    show_plan: bool = typer.Option(False, '--plan', help='print the steps and run nothing'),
    compare_regen: Path = typer.Option(COMPARE_REGEN, '--compare-regen',
                                       help="the folder of Word's fresh compares (out/) and their regen_list.csv"),
) -> None:
    try:
        rel = Release(version, root.resolve())
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    ev = evidence_dir(version)
    if draw_sample and (convert_set is not None or redline_set is not None):
        raise typer.BadParameter('--draw-sample runs the old 600/600 draw; --convert-set/--redline-set name '
                                 'the fixed sets of the default flow — pass one or the other')
    if not draw_sample and (adopt_redline_csv is not None or adopt_conversion_list is not None):
        raise typer.BadParameter('--adopt-redline/--adopt-conversion belong to the --draw-sample flow')

    def steps_of(conversion: Sequence[str] | None = None) -> list[Step]:
        try:
            return select(plan(rel, binary=binary.expanduser().resolve() if binary else None, seed=seed, n=n,
                               device=device, conversion=conversion,
                               engine_dir=engine_dir.resolve() if engine_dir else None,
                               engine_ref=engine_ref,
                               adopt_redline_csv=adopt_redline_csv, adopt_conversion_list=adopt_conversion_list,
                               jobs=jobs, convert_workers=convert_workers,
                               compare_regen=compare_regen.expanduser().resolve(),
                               hub=default_hub(rel.root / ev / 'hub_tmp') if use_hub else None,
                               run=release.default_runner(), draw_sample=draw_sample,
                               convert_set=convert_set, redline_set=redline_set), _stages(only), _stages(skip))
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc

    # The convert/score file lists come from the sets (or sample) the run is
    # about to adopt: install+sets run first, then the rest is planned again
    # with the list on disk (its own preflights first).
    light = ('install', 'sample') if draw_sample else ('install', 'sets')
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
        # only the convert and score commands carry the fixtures: a redline stage resumes without them
        on_disk = rel.root / conversion_list(version)
        if any(s.stage in ('convert', 'score') for s in rest):
            if not on_disk.is_file():
                typer.echo(f'no {on_disk}: run the {light[1]} stage first (--only install,{light[1]})')
                raise typer.Exit(code=1)
            rest = [s for s in steps_of(conversion_files(on_disk)) if s.stage not in light]
        done = execute(rest, rel.root, echo=typer.echo)
        if len(done) < len(rest) or any(o.stops for o in done):
            typer.echo(f'stopped at {done[-1].step.stage}: {done[-1].step.name}')
            raise typer.Exit(code=1)
    typer.echo(f'jubarte {version}: {", ".join(dict.fromkeys(s.stage for s in steps))} done')


if __name__ == '__main__':
    app()
