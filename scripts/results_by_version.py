#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC
# SPDX-License-Identifier: AGPL-3.0-only
"""Write RESULTS_BY_VERSION.md: the best result of every tool version, per metric.

Reads every results store we keep and lists, for each metric:

- what it measures (redline markup, redline speed, docx->pdf, pdf->docx);
- the reference PDFs (Microsoft Word exports, or soffice-converted);
- for docx->pdf, whether the documents are clean or redlined (comparison) docs;
- per tool and version, the best run of each 7-day window (newest window
  first), ranked by its mean (lower is better for speed). A run without a
  mean is ranked by the average of its per-document scores.

Sources (in this repository, or $NEUROTIC_DOCX_BENCH): results/bench.jsonl, results/speed.jsonl, results/redline_speed_bench,
results/docx_to_pdf*.json, results/docxide_metrics*.json, results/redline_wordpdf,
results/soffice_vs_word_redlines_randomized, grok_run/docxide_metrics, and the
jubarte loop's English-corpus, redlined-corpus and docxide-suite runs
($JUBARTE_LOOP, by default .scratch/jubarte-loop in a jubarte checkout
beside this one).

Moved here from the jubarte repository at its 0.19.0 cleanup: it reads this
repository's result stores, so it belongs with them.

Usage: uv run python scripts/results_by_version.py [--out RESULTS_BY_VERSION.md]
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import statistics
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = Path(os.environ.get('NEUROTIC_DOCX_BENCH', REPO))
RES = ROOT / 'results'
GROK = ROOT / 'grok_run'
LOOP = Path(os.environ.get('JUBARTE_LOOP', REPO.parent / 'jubarte-redlines' / '.scratch' / 'jubarte-loop'))
# Word-truth A/B runs kept outside the bench (.scratch/jubarte-loop/word_ab_ext.sh); same file names.
WORDAB = LOOP / 'wordab' / 'results' / 'redline_wordpdf'
DXSUITE = Path(os.environ.get('DOCXIDE_SUITE', REPO.parent / 'docxide_suite'))

# Superseded --compress runs, dropped: the writer that embedded whole fonts (23abeb2), and
# 1b72452, whose device-scale glyphs MuPDF hinted differently (fixed in 530f46c).
SUPERSEDED = 'superseded --compress'
SUPERSEDED_FILES = {
    'docxide_metrics_jubarte-23abeb2-compressed.json',
    'docxide_metrics_jubarte-1b72452-compressed.json',
}
# The harness records the binary's own version; 530f46c is the 0.9.2 line (Cargo.toml lags).
FILE_VERSIONS = {'docxide_metrics_jubarte-530f46c-compressed.json': 'jubarte 0.9.2 --compress'}

# The English-corpus full runs record a tag, not the binary: en_full.sh BIN TAG.
EN_TAGS = {
    'full0926b': 'jubarte@1da7e08',
    'full0926c': 'jubarte@020d909',
    'full0926d': 'jubarte@ef2a739',
    'full0926e': 'jubarte@23abeb2',
    'saved23abeb2': 'jubarte@23abeb2',
    'h80d6f94': 'jubarte@80d6f94',
    'd2aa5db': 'jubarte@d2aa5db',
    '6742f5c': 'jubarte@6742f5c',
    '7c8d376_now': 'jubarte@7c8d376',
    'macfix': 'jubarte@macfix',
    # Clean rebuild of 23abeb2 (older binaries deleted first), 2026-09-26.
    'fresh0926f': 'jubarte 0.9.2',
    'fresh0926g': 'jubarte 0.9.2',
    'compressed0926': SUPERSEDED,
    'compressed0926b': SUPERSEDED,
    # Subset fonts, narrowed /W, shared text objects (530f46c), 2026-09-26.
    'compressed0926c': 'jubarte 0.9.2 --compress',
}
# Competitor versions of the English corpus (installed latest, 2026-09-25).
EN_COMPETITORS = {
    'docxide': 'docxide-pdf 0.17.1',
    'soffice': 'soffice 26.8.0',
    'rdocx': 'rdocx 0.14.0',
    'office2pdf': 'office2pdf 0.7.0',
    'minipdf': 'minipdf 0.7.0',
}
# Competitors on the redlined compared_a_100_vs_b_10 set (2026-09-24).
REDL_COMPETITORS = {'docxide': 'docxide-pdf 0.17.1', 'soffice': 'soffice 26.8.0'}


@dataclass
class Run:
    metric: str  # section key
    tool: str
    version: str
    when: datetime
    mean: float | None
    median: float | None
    n: int
    scores: list[float] | None = None
    corpora: str = ''
    # Pooled tables: one cell per corpus ('mean (docs)' or '—'); a variant row is listed unranked.
    cells: dict[str, str] | None = None
    ranked: bool = True

    @property
    def rank_value(self) -> float | None:
        if self.mean is not None:
            return self.mean
        if self.scores:
            return statistics.mean(self.scores)
        return None


@dataclass
class Metric:
    key: str
    title: str
    kind: str  # "redline markup", "redline speed", "docx->pdf", "docx->pdf speed", "pdf->docx"
    reference: str
    docs: str  # "clean", "redlines", or "-"
    unit: str
    lower_is_better: bool = False
    note: str = ''
    columns: list[str] | None = None  # extra per-corpus columns (pooled tables)


METRICS: dict[str, Metric] = {}
RUNS: list[Run] = []


def metric(key: str, **kw) -> str:
    METRICS.setdefault(key, Metric(key=key, **kw))
    return key


def when_of(value: str | None, path: Path | None = None) -> datetime:
    if value:
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if path is not None and path.exists():
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


# Retired TypeScript ports that shared the jubarte name. RESULTS.md reports jubarte-redlines,
# so their runs are left out here (the bench keeps them).
RETIRED = re.compile(r'^jubarte-(first|native|lossless|second|third|final)\b')


def retired(tool: str, version: str = '') -> bool:
    return bool(RETIRED.match(tool) or RETIRED.match(version))


def add(**kw) -> None:
    if not retired(kw['tool'], str(kw.get('version') or '')):
        RUNS.append(Run(**kw))


def jsonl_objects(lines) -> Iterator[dict]:
    """The JSON objects of a JSONL stream; torn lines and non-object values are skipped."""
    for line in lines:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            yield row


# --- redline markup benches (results/bench.jsonl) ------------------------------------------


def bench_jsonl() -> None:
    path = RES / 'bench.jsonl'
    if not path.exists():
        return
    with path.open() as fh:
        for row in jsonl_objects(fh):
            bench = row.get('benchmark')
            if not bench:
                continue
            env = row.get('environment_config') or {}
            truth = str(env.get('source_of_truth') or '')
            runs = env.get('runs') or []
            render = runs[0].get('render') if runs else None
            reference = 'Word' if 'word' in truth.lower() else (truth or 'unknown')
            if render:
                reference += f' (tool output rendered by {render})'
            n_docs = row.get('itt_n_docs') or row.get('n_docs') or 0
            if n_docs < 20:
                continue  # smoke runs
            corpus = row.get('corpus_revision') or 'unstamped'
            key = metric(
                f'redline:{bench}:{reference}:{corpus}',
                title=f'Redline markup — {bench}' + (f' ({render} render)' if render else '') + f', corpus {corpus}',
                kind='redline markup',
                reference=reference,
                docs='redlines',
                unit='score 0-100',
            )
            version = row.get('tool_version') or (runs[0].get('package') if runs else None) or 'unversioned'
            vendor = row.get('vendor') or '?'
            if ours(vendor) and 'jubarte-final' in str(runs[0].get('dist') if runs else ''):
                continue  # the retired TypeScript port (dist/jubarte-final), not jubarte-redlines
            mean = row.get('itt_mean') if row.get('itt_mean') is not None else row.get('overall_mean')
            median = row.get('itt_median') if row.get('itt_median') is not None else row.get('overall_median')
            add(
                metric=key,
                tool=vendor,
                version=str(version),
                when=when_of(row.get('timestamp')),
                mean=mean,
                median=median,
                n=n_docs,
            )


# --- redline speed ---------------------------------------------------------------------------


def speed_rows(path: Path) -> None:
    if not path.exists():
        return
    for row in jsonl_objects(path.read_text().splitlines()):
        if row.get('unit') != 'ms_per_redline' or (row.get('n') or 0) < 20:
            continue  # smoke runs (2-document probes) time nothing comparable
        # Only runs over the same pair set are comparable: one table per set.
        pairs, fixtures = row.get('pair_count'), row.get('fixture_count')
        pair_set = f'{pairs}x{fixtures}' if pairs and fixtures else str(row.get('n'))
        label = f'{pairs} pairs of {fixtures} fixtures' if pairs and fixtures else f'{row.get("n")} pairs'
        key = metric(
            f'speed:redlines:{pair_set}',
            title=f'Redline speed — ms per redline ({label})',
            kind='redline speed',
            reference='-',
            docs='redlines',
            unit='ms per redline (lower is better)',
            lower_is_better=True,
            note='Docs counts the pairs timed: a pair the tool failed on is excluded from its timing.',
        )
        dist = row.get('dist') or ''
        version = Path(dist).name if dist else (row.get('engine') or 'unversioned')
        add(
            metric=key,
            tool=row.get('tool') or row.get('engine') or '?',
            version=f'{version} [{row.get("runtime") or "?"}]',
            when=when_of(row.get('run_ts'), path),
            mean=row.get('mean'),
            median=row.get('median'),
            n=row.get('n') or 0,
        )


def speed() -> None:
    speed_rows(RES / 'speed.jsonl')
    for path in sorted((RES / 'redline_speed_bench').rglob('speed.jsonl')):
        speed_rows(path)
    docx_to_pdf_speed()


# corpus -> (title label, Documents cell)
D2P_SPEED_CORPORA = {
    'all': ('every document pooled', 'clean + redlines'),
    'fixtures_500': ('fixtures_500, clean', 'clean'),
    'word_redline_pools': ("Word's redlines of the neurotic pools", 'redlines'),
    'word_redline_en': ("Word's redlines of the English pairs", 'redlines'),
}


def docx_to_pdf_speed() -> None:
    """results/docx_to_pdf_speed/speed.jsonl (scripts/docx_to_pdf_speed.py): ms per document."""
    path = RES / 'docx_to_pdf_speed' / 'speed.jsonl'
    if not path.exists():
        return
    for row in jsonl_objects(path.read_text().splitlines()):
        corpus, tool, version = row.get('corpus'), row.get('tool'), row.get('version')
        n, mean, median = row.get('n'), row.get('mean'), row.get('median')
        # An interrupted or hand-edited row lacks a field: skip it, not the report.
        if not (isinstance(corpus, str) and isinstance(tool, str) and isinstance(version, str)):
            continue
        if not (isinstance(n, int) and all(isinstance(v, (int, float)) for v in (mean, median))):
            continue
        try:
            when = datetime.strptime(str(row.get('run_ts')), '%Y-%m-%dT%H-%M-%SZ').replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        label, docs = D2P_SPEED_CORPORA.get(corpus, (corpus, 'clean'))
        warm = row.get('mode') == 'warm'
        key = metric(
            f'speed:docx2pdf:{"warm:" if warm else ""}{corpus}',
            title=f'docx→pdf speed — ms per document, {"warm worker" if warm else "cold CLI"} ({label})',
            kind='docx->pdf speed',
            reference='-',
            docs=docs,
            unit='ms per document (lower is better)',
            lower_is_better=True,
            note=(
                'Sequential, round-robin across tools per document; one long-lived worker per tool '
                '(the same library calls as its CLI), read + convert + write timed in-process, start-up '
                'paid once as a service would. '
                if warm
                else 'Sequential, round-robin across tools per document; one CLI call per sample, process '
                'start included. '
            )
            + 'Failed conversions are excluded from the timing (Docs counts successes).',
        )
        if tool == 'jubarte' and '@' in version:
            version = 'jubarte@' + version.rsplit('@', 1)[1]
        add(metric=key, tool=tool, version=version, when=when, mean=mean, median=median, n=n)


# --- docx -> pdf, neurotic harness -----------------------------------------------------------


def harness_docx_to_pdf() -> None:
    for path in sorted(RES.glob('docx_to_pdf*.json')):
        try:
            doc = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        track = doc.get('track') or ''
        clean = 'no_redline' in track
        oracle = doc.get('oracle') or ''
        reference = 'Word' if 'word' in oracle.lower() else oracle or 'unknown'
        n_docs = doc.get('n') or 0
        key = metric(
            f'harness:{track}:{n_docs}',
            title=f'docx→pdf — neurotic harness `{track}` ({n_docs} docs)',
            kind='docx->pdf',
            reference=reference,
            docs='clean' if clean else 'redlines',
            unit='harness score 0-100',
        )
        for tool, t in (doc.get('tools') or {}).items():
            per_doc = t.get('per_doc') or {}
            scores = [v for v in per_doc.values() if isinstance(v, (int, float))]
            add(
                metric=key,
                tool=tool,
                version=str(t.get('version') or t.get('converter') or 'unversioned'),
                when=when_of(doc.get('generated_at'), path),
                mean=t.get('mean'),
                median=t.get('median'),
                # A failed document scores 0 inside the mean, so Docs counts every attempt.
                n=len(per_doc) or n_docs,
                scores=scores or None,
            )


def soffice_vs_word() -> None:
    path = RES / 'soffice_vs_word_redlines_randomized' / 'summary.json'
    if not path.exists():
        return
    doc = json.loads(path.read_text())
    key = metric(
        'soffice_vs_word',
        title='docx→pdf — soffice render of Word redlines vs Word export',
        kind='docx->pdf',
        reference='Word',
        docs='redlines',
        unit='visual score 0-100',
    )
    add(
        metric=key,
        tool='soffice',
        version=doc.get('renderer_candidate') or 'soffice',
        when=when_of(None, path),
        mean=doc.get('mean'),
        median=doc.get('median'),
        n=doc.get('n_scored') or 0,
    )


# --- docx -> pdf, docxide-metrics Jaccard vs Word, pooled over every corpus -------------------

# Corpus -> label. Every corpus's references are Microsoft Word PDF exports.
CLEAN_CORPORA = {
    'en_a': 'English part a',
    'en_b': 'English part b',
    'fixtures_500': 'fixtures_500',
    'dxsuite': "docxide's 208-case suite",
    'nb398': 'neurotic no-redline 398',
}
REDLINE_CORPORA = {'en_r': 'English redlines a vs b', 'compared': 'compared_a_100_vs_b_10'}
TOOL_NAMES = {'docxide-pdf': 'docxide', 'generated': 'docxide', 'libreoffice': 'soffice', 'LibreOffice': 'soffice'}


@dataclass
class Sample:
    """One tool run on one corpus: per-document docxide-metrics Jaccard, 0-1."""

    corpus: str
    tool: str
    version: str
    when: datetime
    scores: dict[str, float]

    @property
    def mean(self) -> float:
        return statistics.mean(self.scores.values())


SAMPLES: list[Sample] = []


def jub(tag: str) -> str:
    """A run tagged `compressed` (convert --compress) is its own tool."""
    return 'jubarte-compressed' if 'compressed' in tag else 'jubarte'


def sample(corpus: str, tool: str, version: str, when: datetime, scores: dict[str, float]) -> None:
    scores = {k: float(v) for k, v in scores.items() if isinstance(v, (int, float))}
    if scores and version != SUPERSEDED and not retired(tool, version):
        SAMPLES.append(Sample(corpus, TOOL_NAMES.get(tool, tool), version, when, scores))


def english_corpus() -> None:
    for p in 'abr':
        corpus = f'en_{p}'
        paths = glob.glob(str(LOOP / 'runs' / f'enfull_{p}_*' / 'rows.json'))
        paths += glob.glob(str(LOOP / 'runs' / f'en{p}_full_*' / 'rows.json'))
        if p == 'r':
            paths += glob.glob(str(LOOP / 'runs' / 'en_r_base_*' / 'rows.json'))
        for raw in sorted(paths):
            path = Path(raw)
            rows = json.loads(path.read_text())
            if len(rows) < 400:
                continue
            name = path.parent.name
            tag = name.split(f'enfull_{p}_')[-1].split(f'en{p}_full_')[-1].split('en_r_base_')[-1]
            version = EN_TAGS.get(tag, f'jubarte@{tag}')
            sample(corpus, jub(tag), version, when_of(None, path), {k: r['jubarte'] for k, r in rows.items()})
        comp = LOOP / 'runs' / f'en_{p}_competitors.json'
        if comp.exists():
            for tool, rows in json.loads(comp.read_text()).items():
                sample(corpus, tool, EN_COMPETITORS.get(tool, tool), when_of(None, comp), rows)


# The competitors' fixtures_500 run of 2026-09-22 (same Word references, same scorer), kept
# per file in jubarte-loop/baseline.json; its jubarte column is an old build and is not read.
F500_COMPETITORS = {'docxide': 'docxide-pdf 261618a9 (0.17.1+)', 'soffice': 'soffice 26.8.0.3'}


def fixtures_500() -> None:
    base = LOOP / 'baseline.json'
    if base.exists():
        rows = json.loads(base.read_text())
        for tool, version in F500_COMPETITORS.items():
            scores = {k: r[tool] for k, r in rows.items() if isinstance(r, dict) and r.get(tool) is not None}
            sample('fixtures_500', tool, version, when_of('2026-09-22T21:52:00Z'), scores)
    for path in sorted((LOOP / 'runs').glob('full_*/result.json')):
        rows = json.loads(path.read_text())
        scores = {k: r['new'] for k, r in rows.items() if isinstance(r, dict) and r.get('new') is not None}
        if len(scores) < 400 or not any(scores.values()):
            continue  # partial runs, and runs whose output folder was missing
        tag = path.parent.name.removeprefix('full_')
        sample('fixtures_500', jub(tag), EN_TAGS.get(tag, f'jubarte@{tag}'), when_of(None, path), scores)


def docxide_suite() -> None:
    published = DXSUITE / 'published_scores.json'
    if published.exists():
        by_engine: dict[str, dict[str, float]] = {}
        for case in json.loads(published.read_text()):
            for engine, sc in (case.get('scores') or {}).items():
                if isinstance(sc, dict) and sc.get('jaccard') is not None:
                    by_engine.setdefault(engine, {})[case['case']] = sc['jaccard'] / 100
        for engine, scores in by_engine.items():
            sample('dxsuite', engine, 'published (sverrejb.github.io/docxide-pdf)', when_of(None, published), scores)
    for path in sorted((LOOP / 'dxruns').glob('*/result.json')):
        rows = json.loads(path.read_text())
        if len(rows) < 200:
            continue
        tag = path.parent.name.removeprefix('dx_')
        scores = {k: r['new'] for k, r in rows.items() if isinstance(r, dict) and r.get('new') is not None}
        sample('dxsuite', jub(tag), EN_TAGS.get(tag, f'jubarte@{tag}'), when_of(None, path), scores)


def neurotic_398() -> None:
    for path in sorted(RES.glob('docxide_metrics*.json')):
        if path.name in SUPERSEDED_FILES:
            continue
        doc = json.loads(path.read_text())
        if 'word' not in str(doc.get('oracle') or '').lower():
            continue
        for tool, t in (doc.get('tools') or {}).items():
            per_doc = {
                k: v['jaccard'] / 100 for k, v in (t.get('per_doc') or {}).items() if v.get('jaccard') is not None
            }
            version = str(t.get('version') or 'unversioned')
            # jubarte-first (the 0.2.0 docxToPdf adapter) is its own tool, not jubarte.
            name = 'jubarte-first' if 'jubarte-first' in version else tool
            if name == 'jubarte':
                name = jub(path.name)
            version = FILE_VERSIONS.get(path.name, version)
            sample('nb398', name, version, when_of(doc.get('generated_at'), path), per_doc)


def redlined_compared_set() -> None:
    redl = LOOP / 'redl'
    base = redl / 'all_scores.json'
    if base.exists():
        doc = json.loads(base.read_text())
        for tool, ver in REDL_COMPETITORS.items():
            sample('compared', tool, ver, when_of(None, base), doc.get(tool) or {})
    for path in sorted(redl.glob('*_rows.json')):
        rows = json.loads(path.read_text())
        if len(rows) < 900:
            continue
        tag = path.name.removesuffix('_rows.json').removeprefix('rl_')
        sample('compared', jub(tag), EN_TAGS.get(tag, f'jubarte@{tag}'), when_of(None, path), rows)


def ours(tool: str) -> bool:
    return tool.startswith('jubarte')


# A flag variant of jubarte (convert --compress) is listed but never takes a rank.
VARIANT = re.compile(r'^jubarte-compressed\b')


def variant(tool: str) -> bool:
    return bool(VARIANT.match(tool))


def engine(tool: str) -> bool:
    """A row of this repository's engine (jubarte-redlines), in any runtime or flag, not a retired port."""
    return ours(tool) and not retired(tool)


def pooled(corpora: dict[str, str], key: str, title: str, docs: str) -> None:
    """One table over every corpus in `corpora`, the same rule for every tool.

    Each tool takes its latest run per corpus. The ranked mean covers only the corpora every
    ranked tool ran, over the same documents: those any tool scored there, a document a tool
    has no score for counting 0. One column per corpus shows each tool's own mean there.
    """
    metric(
        key,
        title=title,
        kind='docx->pdf',
        reference='Word',
        docs=docs,
        unit='docxide-metrics Jaccard 0-1',
        columns=list(corpora.values()),
    )
    picks: dict[str, dict[str, Sample]] = {}
    for s in SAMPLES:
        if s.corpus in corpora:
            mine = picks.setdefault(s.tool, {})
            if s.corpus not in mine or s.when > mine[s.corpus].when:
                mine[s.corpus] = s
    universe: dict[str, set[str]] = {}
    for mine in picks.values():
        for c, s in mine.items():
            universe.setdefault(c, set()).update(s.scores)
    ranked = [tool for tool in picks if not variant(tool)]
    common = [c for c in corpora if ranked and all(c in picks[tool] for tool in ranked)]
    for tool in sorted(picks):
        mine = picks[tool]
        cells = {}
        for c, label in corpora.items():
            if c in mine:
                cells[label] = (
                    f'{statistics.mean(mine[c].scores.get(d, 0.0) for d in universe[c]):.4f} ({len(universe[c])})'
                )
            else:
                cells[label] = '—'
        on_common = all(c in mine for c in common) and common
        scores = [mine[c].scores.get(d, 0.0) for c in common for d in sorted(universe[c])] if on_common else []
        mean, median = stats(scores) if scores else (None, None)
        add(
            metric=key,
            tool=tool,
            version='; '.join(sorted({s.version for s in mine.values()})),
            when=max(s.when for s in mine.values()),
            mean=mean,
            median=median,
            n=len(scores),
            corpora=', '.join(corpora[c] for c in common),
            cells=cells,
            ranked=not variant(tool) and bool(scores),
        )


def stats(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), statistics.median(values)


def docx_to_pdf_pooled() -> None:
    english_corpus()
    fixtures_500()
    docxide_suite()
    neurotic_398()
    redlined_compared_set()
    pooled(CLEAN_CORPORA, 'pool:clean', 'docx→pdf — every clean corpus pooled (no redlines)', 'clean')
    pooled(REDLINE_CORPORA, 'pool:redlines', 'docx→pdf — every redlined corpus pooled (redlines only)', 'redlines')


# Word truth for redlines: Word's own redline of each pair (word_redline.py), converted to PDF
# by Word (word_pdf.py). Files: results/redline_wordpdf/[en_]<row>[~<maker>]-<version>_<scorer>.json,
# <scorer> = harness (`bench compare`, {stem: 0-100}) or docxide (docxide-metrics rows). Each row
# swaps one side of the pipeline, so its score isolates what that side does.
WORDPDF_SETS = {'': 'neurotic redline pools', 'en_': 'English redlines'}
# row -> (stage, tool label). Rows rank only against rows of the same stage: a redliner is
# never ranked against a converter.
WORDPDF_ROWS = {
    'A_redline': ('redlining', '{maker} redline (Word PDF)'),
    'B_convert': ('conversion', 'jubarte PDF (Word redline)'),
    'C_soffice': ('conversion', 'soffice PDF (Word redline)'),
    'C_convert': ('conversion', '{maker} PDF (Word redline)'),
    'D_e2e': ('end to end', 'jubarte redline + jubarte PDF'),
    'E_e2e_soffice': ('end to end', 'jubarte redline + soffice PDF'),
}
WORDPDF_STAGES = ['redlining', 'conversion', 'end to end']
WORDPDF_NOTES = {
    'redlining': 'Each tool redlines the pair; Word converts that redline to PDF. Only the redline differs.',
    'conversion': "Word redlines the pair; each tool converts Word's redline to PDF. Only the renderer differs.",
    'end to end': 'One tool redlines and converts, as a user without Word would.',
}
WORDPDF_SKIPS = (
    'A pair Word itself could not redline or convert is skipped, so Docs counts the scored pairs. '
    'A tool that fails or refuses a pair scores zero there (superdoc refuses most pairs: '
    'header/footer topology, shared definitions, numbering replay).'
)


def wordpdf_row(stem: str) -> tuple[str, str, str, str, str] | None:
    """`[en_]<row>[~<maker>]-<version>_<scorer>` -> (set, stage, tool, version, scorer)."""
    name, _, rest = stem.partition('-')
    version, _, scorer = rest.rpartition('_')
    if scorer not in ('harness', 'docxide') or not version:
        return None
    corpus = 'en_' if name.startswith('en_') else ''
    row, _, maker = name.removeprefix(corpus).partition('~')
    if row not in WORDPDF_ROWS:
        return None
    stage, label = WORDPDF_ROWS[row]
    maker = maker or 'jubarte'
    tool = label.format(maker=maker)
    if tool.startswith('jubarte'):
        version = EN_TAGS.get(version, f'jubarte@{version}')
    elif row == 'C_soffice':
        version = EN_COMPETITORS['soffice']
    else:
        version = f'{maker} {version}'
    return corpus, stage, tool, version, scorer


def redline_wordpdf() -> None:
    paths = [*(RES / 'redline_wordpdf').glob('*.json'), *WORDAB.glob('*.json')]
    for path in sorted(paths, key=lambda p: p.name):
        parsed = wordpdf_row(path.stem)
        if parsed is None:
            continue
        corpus, stage, tool, version, scorer = parsed
        doc = json.loads(path.read_text())
        if scorer == 'harness':
            scores = [float(v) for v in doc.values() if isinstance(v, (int, float))]
            unit = 'harness score 0-100'
        else:
            scores = [float(r.get('jaccard') or 0.0) for r in doc]
            unit = 'docxide-metrics Jaccard 0-1'
        if not scores:
            continue
        key = metric(
            f'wordpdf:{corpus}:{stage}:{scorer}',
            title=f'{stage.capitalize()} vs Word truth — {WORDPDF_SETS[corpus]} ({unit.split(" ")[0]})',
            kind='redline markup',
            reference='Word (Word redline, Word PDF)',
            docs='redlines',
            unit=unit,
            note=f'{WORDPDF_NOTES[stage]} {WORDPDF_SKIPS}',
        )
        mean, median = stats(scores)
        add(
            metric=key,
            tool=tool,
            version=version,
            when=when_of(None, path),
            mean=mean,
            median=median,
            n=len(scores),
            scores=scores,
        )


def pdf_to_docx() -> None:
    metric('pdf_to_docx', title='pdf→docx', kind='pdf->docx', reference='-', docs='-', unit='-')


# --- report ----------------------------------------------------------------------------------


def latest_per_tool(runs: list[Run]) -> list[Run]:
    """Each tool's latest run, jubarte and competitors alike: no best-of-week pick."""
    out: dict[str, Run] = {}
    for r in runs:
        if r.rank_value is not None and (r.tool not in out or r.when > out[r.tool].when):
            out[r.tool] = r
    return list(out.values())


# A run this much older than its table's newest is flagged: the tool may have moved since.
STALE = timedelta(days=7)


VERSION_WIDTH = 20


def short_version(v: str) -> str:
    """A Version cell of at most VERSION_WIDTH chars; a cut ends in an ellipsis."""
    return v if len(v) <= VERSION_WIDTH else v[: VERSION_WIDTH - 1] + '…'


def fmt(v: float | None, unit: str) -> str:
    """Jaccard (0-1) keeps four decimals; scores and milliseconds keep two."""
    if v is None:
        return '—'
    return f'{v:.4f}' if 'Jaccard' in unit else f'{v:.2f}'


KIND_ORDER = ['docx->pdf', 'redline markup', 'docx->pdf speed', 'redline speed', 'pdf->docx']
# Reference groups, in page order: Word truth first, then speed, then the superseded soffice truth.
GROUPS = [
    (
        'Microsoft Word® reference PDFs',
        lambda m: m.reference.startswith('Word') and 'rendered by' not in m.reference,
        '',
    ),
    ('No reference PDFs (speed, pdf→docx)', lambda m: not m.reference.startswith('Word'), ''),
    (
        'Superseded: tool output rendered by soffice, playwright or passthrough',
        lambda m: True,
        "Kept for history only. These tables render each tool's redline with LibreOffice, playwright or "
        'the passthrough renderer before scoring against Word, so they measure the renderer as much as '
        'the redline. The Word-truth tables above replace them; new runs are not added here.',
    ),
]


def group_of(m: Metric) -> int:
    return next(i for i, (_, test, _) in enumerate(GROUPS) if test(m))


def render() -> str:
    lines = [
        # REUSE-IgnoreStart
        '<!-- SPDX-FileCopyrightText: 2026 Jandira Technologies, LLC -->',
        '<!-- SPDX-License-Identifier: AGPL-3.0-only -->',
        # REUSE-IgnoreEnd
        '<!-- Generated by scripts/results_by_version.py — do not edit by hand. -->',
        '# Results by tool version',
        '',
        f'Generated {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}. One rule for every tool,',
        "jubarte included: each table keeps a tool's latest run, never its best one. Rows rank by mean",
        '(speed: lowest first); a row without a mean ranks by the average of its per-document scores. A',
        'failed document scores 0 in every score table. A date marked † is over 7 days older than the',
        "table's newest run: that tool may have released since. jubarte's `--compress` variant is",
        'listed under the ranked rows with no rank. Only jubarte-redlines is reported: a table without',
        'a jubarte-redlines run, and the retired TypeScript ports (jubarte-first, -native, -lossless),',
        'are left out. Scores are only comparable inside one table.',
        '',
        'The docx→pdf docxide-metrics tables pool the per-document Jaccard of every corpus the tools',
        'converted, each scored against the Microsoft Word® PDF export of the same document: one table',
        'for the clean corpora, one for the redlined documents only. The ranked Mean and Median cover',
        'only the corpora every ranked tool ran, over the same documents (Docs is equal for every',
        'ranked row); a corpus only some tools ran shows in its own column, never in the rank. Each',
        "corpus column is that tool's mean there, with the documents counted in parentheses.",
        '',
        'The "vs Word truth" tables score every row against Word\'s own redline of the pair',
        '(word_redline.py), converted to PDF by Word (word_pdf.py). Each row swaps one side, and each',
        'stage has its own table: Redlining ("<tool> redline (Word PDF)"), Conversion ("<tool> PDF',
        '(Word redline)") and End to end ("jubarte redline + <converter> PDF"). A pair Word could not',
        'redline or convert is skipped; a tool that produced no PDF for a pair scores 0 on it. jubarte',
        "converts with `--revisions word` (Word's revision colours) so its PDF is comparable to Word's.",
        '',
        '| Metric | Kind | Reference PDFs | Documents | Unit |',
        '| --- | --- | --- | --- | --- |',
    ]
    # A table no jubarte-redlines run is in compares other vendors only: not ours to publish.
    shown = {r.metric for r in RUNS if engine(r.tool)}
    ordered = sorted(
        (m for m in METRICS.values() if m.key in shown),
        key=lambda m: (
            group_of(m),
            KIND_ORDER.index(m.kind),
            not m.key.startswith('pool:'),
            m.docs,
            WORDPDF_STAGES.index(m.key.split(':')[2]) if m.key.startswith('wordpdf:') else -1,
            m.title,
        ),
    )
    lines.extend(
        f'| [{m.title}](#{anchor(m.title)}) | {m.kind} | {m.reference} | {m.docs} | {m.unit} |' for m in ordered
    )
    for gi, (heading, _, blurb) in enumerate(GROUPS):
        mets = [m for m in ordered if group_of(m) == gi]
        if not mets:
            continue
        lines += ['', f'## {heading}']
        if blurb:
            lines += ['', blurb]
        for m in mets:
            lines += ['', f'### {m.title}', '']
            lines.append(
                f'Kind: {m.kind}. Reference PDFs: **{m.reference}**. Documents: **{m.docs}**. Unit: {m.unit}.'
            )
            if m.note:
                lines += ['', m.note]
            runs = all_runs = [r for r in RUNS if r.metric == m.key]
            if not m.key.startswith('pool:'):  # a pooled row already is its tool's latest runs
                runs = latest_per_tool(runs)
            ranked = [(v, r) for r in runs if (v := r.rank_value) is not None]
            if not ranked:
                lines += ['', '_No run measured yet._']
                continue
            ranked.sort(key=lambda vr: vr[0], reverse=not m.lower_is_better)
            # Unranked: variants, then pooled rows off the common corpora (their columns still show).
            for _, r in ranked:
                r.ranked = r.ranked and not variant(r.tool)
            runs = [r for _, r in ranked if r.ranked] + [r for _, r in ranked if not r.ranked]
            runs += [r for r in all_runs if r.rank_value is None and r.cells]
            newest = max(r.when for r in runs)
            extra = m.columns or []
            head = '| Rank | Tool | Version | Date | Docs | Mean | Median |' + ''.join(f' {c} |' for c in extra)
            lines += ['', head, '|' + ' --- |' * (7 + len(extra))]
            place = 0
            for r in runs:
                place += r.ranked
                if r.mean is not None or r.rank_value is None:
                    mean = fmt(r.mean, m.unit)
                else:
                    mean = f'{fmt(r.rank_value, m.unit)} (avg)'
                date = r.when.strftime('%Y-%m-%d') + (' †' if newest - r.when > STALE else '')
                row = (
                    f'| {place if r.ranked else "—"} | {r.tool} | {short_version(r.version)} | {date} | {r.n} '
                    f'| {mean} | {fmt(r.median, m.unit)} |'
                )
                lines.append(row + ''.join(f' {(r.cells or {}).get(c, "—")} |' for c in extra))
    return '\n'.join(lines) + '\n'


def anchor(title: str) -> str:
    keep = ''.join(c for c in title.lower() if c.isalnum() or c in ' -_')
    return keep.replace(' ', '-')


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', default=str(REPO / 'RESULTS_BY_VERSION.md'))
    args = ap.parse_args()
    for load in (
        bench_jsonl,
        speed,
        redline_wordpdf,
        harness_docx_to_pdf,
        soffice_vs_word,
        docx_to_pdf_pooled,
        pdf_to_docx,
    ):
        load()
    Path(args.out).write_text(render())
    print(f'wrote {args.out}: {len(METRICS)} metrics, {len(RUNS)} runs')


if __name__ == '__main__':
    main()
