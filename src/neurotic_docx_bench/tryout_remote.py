"""``bench try remote``: score a tool on random documents from the superdoc docx-corpus.

Documents come from the Hugging Face dataset ``superdoc-dev/docx-corpus`` (one parquet
index, each row a ``url`` to the docx). The tasks, and the source of truth (SOT) each is
scored against:

* ``redline`` (two documents, base -> next): Word's compare of the pair when
  ``corpus/word/comparisons.csv`` has it, else docxodus's redline. The SOT redline and the
  tool's redline go through the same renderer (``soffice`` by default); under ``word`` the
  Word PDF of Word's compare is used as is, under ``soffice`` its LibreOffice render in
  ``corpus/libreoffice`` when present.
* ``convert`` (DOCX -> PDF, the base document): Word's PDF when ``corpus/word/documents.csv``
  has it, else soffice's PDF.
* ``png`` (PDF -> PNG pages): pdftoppm's pages of the ``convert`` SOT PDF. A tool that
  rasterizes from the docx (jubarte) gets the docx as ``{input}``.

The docx-corpus bytes are the bytes ``corpus/word`` holds, so the SOT lookup is by sha256.
A tool is a known name (:data:`KNOWN_TASKS`) or a shell template whose placeholders name
its task; by default it runs every task it can. A tool that is a task's fallback SOT is not
scored against itself. Every raster lives in a temporary folder that is gone when
:func:`run` returns.
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neurotic_docx_bench import pipeline

DATASET = 'superdoc-dev/docx-corpus'
PARQUET = 'data/train-00000-of-00001.parquet'
TASKS = ('redline', 'convert', 'png')
DOCS_NEEDED = {'redline': 2, 'convert': 1, 'png': 1}
FALLBACK = {'redline': 'docxodus', 'convert': 'soffice', 'png': 'pdftoppm'}
KNOWN_TASKS: dict[str, tuple[str, ...]] = {
    'jubarte': ('redline', 'convert', 'png'),
    'docxodus': ('redline',),
    'soffice': ('convert',),
    'pdftoppm': ('png',),
    'mutool': ('png',),
    'pymupdf': ('png',),
}
REDLINE_STATES = ('tracking_without_comments', 'with_comments_tracking')
# Placeholders that name a template's task; {out} is the output file, {outdir} a folder of PNGs.
TEMPLATE_TASKS = (
    ('redline', ('{base}', '{next}', '{out}')),
    ('png', ('{outdir}',)),
    ('convert', ('{input}', '{out}')),
)
OUTPUT_EXT = {'redline': '.docx', 'convert': '.pdf'}

Runner = Callable[[dict[str, Path], Path, int], Path]
RenderDocx = Callable[[Path, Path], Path]


class RemoteError(Exception):
    """A remote tryout step refused to proceed; the message says why."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# --- the remote corpus -------------------------------------------------------------------


@dataclass(frozen=True)
class Doc:
    id: str
    url: str
    path: Path
    sha256: str
    language: str | None = None
    type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {'id': self.id, 'url': self.url, 'sha256': self.sha256, 'language': self.language, 'type': self.type}


def load_index(*, revision: str | None = None):  # -> polars.DataFrame
    """The docx-corpus parquet index (downloaded once into the Hugging Face cache)."""
    import polars as pl
    from huggingface_hub import hf_hub_download

    return pl.read_parquet(hf_hub_download(DATASET, PARQUET, repo_type='dataset', revision=revision))


def pick_rows(
    df, n: int, *, seed: int, language: str | None = None, doc_type: str | None = None, sot: SotIndex | None = None
) -> list[dict]:
    """``n`` distinct rows drawn with ``random.Random(seed)`` from the rows matching the
    filters. With ``sot`` only documents we hold Word SOT for: for ``n == 2`` one of
    Word's compared pairs (base first), else documents with a Word PDF."""
    import polars as pl

    if language:
        df = df.filter(pl.col('language') == language)
    if doc_type:
        df = df.filter(pl.col('type') == doc_type)
    rng = random.Random(seed)
    if sot is not None:
        if n == 2:
            present = set(df.filter(pl.col('id').is_in(sorted(sot.corpus_ids(pairs=True))))['id'].to_list())
            pairs = [p for p in sot.corpus_pairs() if p[0] in present and p[1] in present]
            if not pairs:
                raise RemoteError(f'no Word-compared pair matches language={language!r} type={doc_type!r}')
            chosen = rng.choice(pairs)
            by_id = {r['id']: r for r in df.filter(pl.col('id').is_in(list(chosen))).iter_rows(named=True)}
            return [by_id[chosen[0]], by_id[chosen[1]]]
        df = df.filter(pl.col('id').is_in(sorted(sot.corpus_ids())))
    if df.height < n:
        raise RemoteError(f'{df.height} rows match language={language!r} type={doc_type!r}; {n} needed')
    return [df.row(i, named=True) for i in rng.sample(range(df.height), n)]


def download_doc(row: dict, dest: Path, *, fetch: Callable[[str], bytes]) -> Doc:
    """The row's docx at ``dest/<id[:16]>/<id>.docx`` (one folder per document, so a
    folder renderer sees only it)."""
    path = Path(dest) / row['id'][:16] / f'{row["id"]}.docx'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fetch(row['url']))
    return Doc(
        id=row['id'],
        url=row['url'],
        path=path,
        sha256=sha256_file(path),
        language=row.get('language'),
        type=row.get('type'),
    )


# --- the SOT we hold -------------------------------------------------------------------


def _four_part(text: str) -> str | None:
    """A LibreOffice build number (26.2.4.2) in a version or producer string."""
    match = re.search(r'\b(\d+\.\d+\.\d+\.\d+)\b', text)
    return match.group(1) if match else None


def _is_corpus_id(name: str) -> bool:
    return len(name) == 64 and all(c in '0123456789abcdef' for c in name)


def _corpus_names(names: str) -> list[str]:
    return [n for n in names.split(';') if _is_corpus_id(n)]


@dataclass(frozen=True)
class SotIndex:
    """``corpus/word``'s documents and comparisons by content; empty when absent."""

    root: Path
    documents: dict[str, dict] = field(default_factory=dict)  # sha256 -> documents.csv row
    comparisons: dict[tuple[str, str], list[dict]] = field(default_factory=dict)  # (base_id, next_id) -> rows
    lo_producers: dict[str, str] = field(default_factory=dict)  # corpus/libreoffice pdf -> its producer

    def _file(self, rel: str) -> Path | None:
        path = self.root / rel if rel else None
        return path if path is not None and path.is_file() else None

    def word_pdf(self, sha256: str) -> Path | None:
        row = self.documents.get(sha256)
        return self._file(row['pdf']) if row else None

    def word_redline(self, base_sha: str, next_sha: str) -> tuple[Path, Path | None] | None:
        """Word's compare of base -> next (tracking without comments first): its docx
        and its Word PDF (None when absent on disk)."""
        rows = self.comparisons.get((base_sha[:10], next_sha[:10]), [])
        rank = {s: i for i, s in enumerate(REDLINE_STATES)}
        for row in sorted(rows, key=lambda r: rank.get(r['state'], len(rank))):
            if (docx := self._file(row['docx'])) is not None:
                return docx, self._file(row['pdf'])
        return None

    def corpus_ids(self, *, pairs: bool = False) -> set[str]:
        """docx-corpus ids (64-hex names) of the documents with a Word PDF, or with
        ``pairs`` of every document in a Word-compared pair."""
        if pairs:
            return {i for p in self.corpus_pairs() for i in p}
        return {n for row in self.documents.values() if self._file(row['pdf']) for n in _corpus_names(row['names'])}

    def corpus_pairs(self) -> list[tuple[str, str]]:
        """(base id, next id) of every Word compare between two docx-corpus documents, sorted."""
        out: set[tuple[str, str]] = set()
        for rows in self.comparisons.values():
            for row in rows:
                if row['state'] in REDLINE_STATES and self._file(row['docx']):
                    sides = row['names'].split('__vs__')
                    if len(sides) == 2 and all(_is_corpus_id(s) for s in sides):
                        out.add((sides[0], sides[1]))
        return sorted(out)

    def libreoffice_pdf(self, word_pdf: Path, soffice_version: str) -> Path | None:
        """The LibreOffice render ``corpus/libreoffice`` files under a Word PDF's name, when
        ``word_map.csv`` says the installed soffice (``soffice_version``) made it."""
        rel = word_pdf.relative_to(self.root).as_posix()
        path = self.root.parent / 'libreoffice' / rel
        made_by = _four_part(self.lo_producers.get(rel, ''))
        if not path.is_file() or made_by is None or made_by != _four_part(soffice_version):
            return None
        return path


def load_sot(root: Path) -> SotIndex:
    root = Path(root).resolve()
    documents: dict[str, dict] = {}
    comparisons: dict[tuple[str, str], list[dict]] = {}
    if (root / 'documents.csv').is_file():
        with (root / 'documents.csv').open(newline='') as fh:
            for row in csv.DictReader(fh):
                documents.setdefault(row['sha256'], row)
    if (root / 'comparisons.csv').is_file():
        with (root / 'comparisons.csv').open(newline='') as fh:
            for row in csv.DictReader(fh):
                comparisons.setdefault((row['base_id'], row['next_id']), []).append(row)
    lo_producers: dict[str, str] = {}
    word_map = root.parent / 'libreoffice' / 'word_map.csv'
    if word_map.is_file():
        with word_map.open(newline='') as fh:
            lo_producers = {row['libreoffice_pdf']: row.get('producer', '') for row in csv.DictReader(fh)}
    return SotIndex(root=root, documents=documents, comparisons=comparisons, lo_producers=lo_producers)


# --- tools -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Tool:
    name: str
    version: str
    runners: dict[str, Runner]


def _run(cmd: list[str], *, timeout: float = 600.0, cwd: Path | None = None) -> None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd, check=False)
    except FileNotFoundError as exc:
        raise RemoteError(f'not found: {cmd[0]}') from exc
    except subprocess.TimeoutExpired as exc:
        raise RemoteError(f'timed out after {timeout:.0f}s: {shlex.join(cmd)}') from exc
    if proc.returncode != 0:
        tail = ' '.join((proc.stderr or proc.stdout or '').split())[-400:]
        raise RemoteError(f'exit {proc.returncode}: {shlex.join(cmd)}; {tail}')


def _pngs(out: Path) -> Path:
    if not any(out.glob('*.png')):
        raise RemoteError(f'no PNG pages in {out}')
    return out


def _written(path: Path) -> Path:
    if not path.is_file():
        raise RemoteError(f'no output at {path}')
    return path


def _template_runner(template: str, task: str) -> Runner:
    tokens = shlex.split(template)

    def runner(inputs: dict[str, Path], out: Path, dpi: int) -> Path:
        out = Path(out).resolve()  # the command runs inside ``out``: every path must be absolute
        out.mkdir(parents=True, exist_ok=True)
        target = out / f'{task}{OUTPUT_EXT[task]}' if task in OUTPUT_EXT else out
        values = {f'{{{k}}}': str(Path(v).resolve()) for k, v in inputs.items()}
        values.update({'{out}': str(target), '{outdir}': str(out), '{dpi}': str(dpi)})  # noqa: RUF027 - literal placeholders
        cmd = []
        for token in tokens:
            for key, value in values.items():
                token = token.replace(key, value)
            cmd.append(token)
        _run(cmd, cwd=out)
        return _pngs(out) if task == 'png' else _written(target)

    return runner


def template_tool(template: str, *, name: str = 'script', version: str = '') -> Tool:
    """A shell template; its placeholders name its task: ``{base} {next} {out}`` redline
    (a .docx), ``{input} {out}`` convert (docx -> .pdf), ``{outdir}`` png (page PNGs into
    that folder, from ``{pdf}`` or the docx ``{input}``; ``{dpi}`` is available)."""
    for task, needed in TEMPLATE_TASKS:
        if all(p in template for p in needed):
            return Tool(
                name=name, version=version or f'{name}: {template}', runners={task: _template_runner(template, task)}
            )
    raise RemoteError(
        f'the template names no task: {template!r}; use {{base}} {{next}} {{out}} (redline), '
        '{input} {out} (convert) or {pdf}/{input} {outdir} (png)'
    )


def _jubarte_runners(binary: Path) -> dict[str, Runner]:
    b = str(binary)

    def redline(inputs, out, dpi):
        out.mkdir(parents=True, exist_ok=True)
        _run([b, str(inputs['base']), str(inputs['next']), '-o', str(out / 'redline.docx'), '--force', '--quiet'])
        return _written(out / 'redline.docx')

    def convert(inputs, out, dpi):
        out.mkdir(parents=True, exist_ok=True)
        _run([b, 'convert', str(inputs['input']), '-o', str(out / 'convert.pdf'), '--force'])
        return _written(out / 'convert.pdf')

    def png(inputs, out, dpi):  # jubarte rasterizes from the docx, not from the SOT PDF
        out.mkdir(parents=True, exist_ok=True)
        _run([b, 'convert', str(inputs['input']), '--png', '--dpi', str(dpi), '-o', str(out / 'j.pdf'), '--force'])
        return _pngs(out)

    return {'redline': redline, 'convert': convert, 'png': png}


def _docxodus_runner(root: Path) -> Runner:
    def redline(inputs, out, dpi):
        out.mkdir(parents=True, exist_ok=True)
        base, nxt = Path(inputs['base']), Path(inputs['next'])
        manifest = out / 'pair.csv'
        with manifest.open('w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['key', 'base', 'next'])
            w.writerow(['pair', str(base.with_suffix('')), str(nxt.with_suffix(''))])
        _run(
            [
                'node',
                '--import',
                'tsx',
                'scripts/generate-native-redlines.ts',
                '--method=docxodus',
                '--tool=docxodus',
                f'--manifest={manifest}',
                '--source-dir=/',
                f'--out={out}',
                f'--run-dir={out}',
            ],
            cwd=root,
        )
        return _written(out / 'pair_docxodus.docx')

    return {'redline': redline}


def _soffice_runner() -> Runner:
    def convert(inputs, out, dpi):
        from neurotic_docx_bench import tryout

        return tryout.render(Path(inputs['input']), 'soffice', out).pdf

    return convert


def _pymupdf_runner(inputs, out, dpi):
    import pymupdf

    out.mkdir(parents=True, exist_ok=True)
    with pymupdf.open(inputs['pdf']) as doc:
        for i, page in enumerate(doc, 1):
            page.get_pixmap(dpi=dpi, alpha=False).save(out / f'page-{i:03d}.png')
    return _pngs(out)


def _version_line(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=False)
    except OSError, subprocess.TimeoutExpired:
        return 'unknown'
    text = (proc.stdout or '') + (proc.stderr or '')
    return next((line.strip() for line in text.splitlines() if line.strip()), 'unknown')


def _npm_version(root: Path, package: str) -> str:
    import json

    pkg = root / 'node_modules' / package / 'package.json'
    return (
        f'{package} {json.loads(pkg.read_text())["version"]} (npm)' if pkg.is_file() else f'{package} (not installed)'
    )


def known_tool(name: str, *, root: Path, version: str | None = None, fetch=None) -> Tool:
    """A tool of :data:`KNOWN_TASKS`. Only jubarte takes a version (resolved local ->
    GitHub release -> crates.io, see :mod:`jubarte_release`); the others run as installed."""
    if name not in KNOWN_TASKS:
        raise RemoteError(f'unknown tool {name!r}; known tools: {", ".join(KNOWN_TASKS)}, or pass a template')
    if version is not None and name != 'jubarte':
        raise RemoteError(f'--version is for jubarte only; {name} runs as installed')
    if name == 'jubarte':
        from neurotic_docx_bench import jubarte_release as jr

        try:
            got = jr.resolve(version, root=root, **({'fetch': fetch} if fetch else {}))
        except jr.JubarteNotFound as exc:
            raise RemoteError(str(exc)) from exc
        return Tool(
            name='jubarte',
            version=f'jubarte {got.version} ({got.source}: {got.path})',
            runners=_jubarte_runners(got.path),
        )
    if name == 'docxodus':
        return Tool(name=name, version=_npm_version(root, 'docxodus'), runners=_docxodus_runner(root))
    if name == 'soffice':
        return Tool(name=name, version=_version_line(['soffice', '--version']), runners={'convert': _soffice_runner()})
    if name == 'pdftoppm':

        def pdftoppm(inputs, out, dpi):
            out.mkdir(parents=True, exist_ok=True)
            _run(['pdftoppm', '-png', '-r', str(dpi), str(inputs['pdf']), str(out / 'page')])
            return _pngs(out)

        return Tool(name=name, version=_version_line(['pdftoppm', '-v']), runners={'png': pdftoppm})
    if name == 'mutool':

        def mutool(inputs, out, dpi):
            out.mkdir(parents=True, exist_ok=True)
            _run(['mutool', 'draw', '-q', '-r', str(dpi), '-o', str(out / 'page-%03d.png'), str(inputs['pdf'])])
            return _pngs(out)

        return Tool(name=name, version=_version_line(['mutool', '-v']), runners={'png': mutool})
    import pymupdf

    return Tool(name=name, version=f'pymupdf {pymupdf.VersionBind}', runners={'png': _pymupdf_runner})


def make_tool(spec: str, *, root: Path, version: str | None = None, fetch=None) -> Tool:
    """A known tool name, or a shell template (anything with a ``{placeholder}``)."""
    if '{' in spec:
        if version is not None:
            raise RemoteError('--version is for jubarte only; a template runs as written')
        return template_tool(spec)
    return known_tool(spec, root=root, version=version, fetch=fetch)


def fallback_tools(root: Path) -> dict[str, Tool]:
    return {task: known_tool(name, root=root) for task, name in FALLBACK.items()}


def select_tasks(tool: Tool, requested: Sequence[str] | None) -> list[str]:
    """``requested`` (each must be one the tool can run) or every task the tool can run."""
    if not requested:
        return [t for t in TASKS if t in tool.runners]
    for task in requested:
        if task not in TASKS:
            raise RemoteError(f'unknown task {task!r}; one of {", ".join(TASKS)}')
        if task not in tool.runners:
            raise RemoteError(f'{tool.name} cannot run {task}; it runs {", ".join(tool.runners) or "nothing"}')
    return list(requested)


# --- scoring ---------------------------------------------------------------------------


def score_pdfs(oracle: Path, candidate: Path, work: Path, *, dpi: int, key: str) -> dict[str, Any]:
    result = pipeline.score_pdf_pair(Path(oracle), Path(candidate), work, dpi=dpi, key=key)
    return {
        'overall': pipeline.overall_from_result(result),
        'overall_raw': float(result['overall_score']),
        'ink_jaccard': result.get('ink_jaccard'),
        'text_boundary': result.get('text_boundary'),
        'page_count_oracle': int(result['page_count_oracle']),
        'page_count_candidate': int(result['page_count_candidate']),
        'page_count_mismatch': bool(result['page_count_mismatch']),
    }


def score_pages(oracle_dir: Path, candidate_dir: Path, work: Path) -> dict[str, Any]:
    """The pixel score and ink Jaccard (x100) of two page-PNG folders; candidate pages
    are resized to the oracle page's size where they differ (copies, in ``work``)."""
    from PIL import Image

    from neurotic_docx_bench.page_metrics import jaccard_from_rasters
    from neurotic_docx_bench.score import score_document

    ref = sorted(Path(oracle_dir).glob('*.png'))
    work.mkdir(parents=True, exist_ok=True)
    cand = [Path(shutil.copy(p, work / p.name)) for p in sorted(Path(candidate_dir).glob('*.png'))]
    resized = False
    for r, c in zip(ref, cand, strict=False):
        with Image.open(r) as o, Image.open(c) as im:
            if im.size != o.size:
                im.convert('RGB').resize(o.size, Image.LANCZOS).save(c)
                resized = True
    jac = jaccard_from_rasters(ref, cand)
    return {
        'pixel': float(score_document(ref, cand)['overall_score']),
        'jaccard': 100.0 * float(jac) if jac is not None else None,
        'page_count_oracle': len(ref),
        'page_count_candidate': len(cand),
        'page_count_mismatch': len(ref) != len(cand),
        'resized': resized,
    }


# --- running ---------------------------------------------------------------------------


def _sot_convert_pdf(doc: Doc, sot: SotIndex, fallback: dict[str, Tool], work: Path, dpi: int) -> tuple[Path, dict]:
    word = sot.word_pdf(doc.sha256)
    if word is not None:
        return word, {'source': 'word', 'version': 'Microsoft Word', 'renderer': None, 'files': {'pdf': str(word)}}
    tool = fallback['convert']
    pdf = tool.runners['convert']({'input': doc.path}, work / 'sot_convert', dpi)
    return pdf, {'source': tool.name, 'version': tool.version, 'renderer': None}


def _sot_redline_pdf(
    base: Doc,
    nxt: Doc,
    sot: SotIndex,
    fallback: dict[str, Tool],
    work: Path,
    dpi: int,
    render_docx: RenderDocx,
    renderer: str,
    renderer_version: str,
) -> tuple[Path, dict]:
    word = sot.word_redline(base.sha256, nxt.sha256)
    if word is not None:
        docx, word_pdf = word
        info = {'source': 'word', 'version': 'Microsoft Word', 'renderer': renderer, 'files': {'docx': str(docx)}}
        pdf = None
        if renderer == 'word':
            pdf = word_pdf
        elif renderer == 'soffice' and word_pdf is not None:
            pdf = sot.libreoffice_pdf(word_pdf, renderer_version)
        if pdf is None:
            local = work / 'sot_redline_docx'
            local.mkdir(parents=True, exist_ok=True)
            pdf = render_docx(Path(shutil.copy(docx, local / docx.name)), work / 'sot_redline_render')
        info['files']['pdf'] = str(pdf)
        return pdf, info
    tool = fallback['redline']
    docx = tool.runners['redline']({'base': base.path, 'next': nxt.path}, work / 'sot_redline', dpi)
    pdf = render_docx(docx, work / 'sot_redline_render')
    return pdf, {'source': tool.name, 'version': tool.version, 'renderer': renderer}


def run_task(
    task: str,
    tool: Tool,
    docs: Sequence[Doc],
    sot: SotIndex,
    *,
    work: Path,
    fallback: dict[str, Tool],
    render_docx: RenderDocx,
    renderer: str,
    dpi: int,
    memo: dict,
    renderer_version: str = '',
) -> dict[str, Any]:
    used = list(docs[: DOCS_NEEDED[task]])
    row: dict[str, Any] = {
        'task': task,
        'tool': tool.name,
        'tool_version': tool.version,
        'dpi': dpi,
        'renderer': renderer if task == 'redline' else None,
        'renderer_version': renderer_version if task == 'redline' else None,
        'inputs': [d.to_dict() for d in used],
        'ok': False,
        'skipped': None,
        'error': None,
        'sot': None,
        'scores': None,
        'seconds': {},
    }
    seconds = row['seconds']
    work = work / task
    try:
        t0 = time.perf_counter()
        base = used[0]
        if task in ('convert', 'png'):
            if 'convert' not in memo:
                memo['convert'] = _sot_convert_pdf(base, sot, fallback, work.parent / 'sot', dpi)
            sot_pdf, sot_info = memo['convert']
        if task == 'convert':
            row['sot'] = sot_info
        elif task == 'png':
            pdftoppm = fallback['png']
            row['sot'] = {
                'source': pdftoppm.name,
                'version': pdftoppm.version,
                'renderer': None,
                'files': {'pdf': str(sot_pdf)},
                'pdf_source': sot_info['source'],
            }
        else:
            sot_pdf, row['sot'] = _sot_redline_pdf(
                used[0], used[1], sot, fallback, work, dpi, render_docx, renderer, renderer_version
            )
        seconds['sot'] = time.perf_counter() - t0
        if row['sot']['source'] == tool.name:
            row['skipped'] = f"{tool.name} is this task's SOT (no Word SOT for these documents)"
            return row
        inputs = {'input': base.path}
        if task == 'redline':
            inputs = {'base': used[0].path, 'next': used[1].path}
        elif task == 'png':
            inputs = {'input': base.path, 'pdf': sot_pdf}
        t0 = time.perf_counter()
        output = tool.runners[task](inputs, work / 'tool', dpi)
        seconds['tool'] = time.perf_counter() - t0
        if task == 'redline':
            t0 = time.perf_counter()
            output = render_docx(output, work / 'tool_render')
            seconds['render'] = time.perf_counter() - t0
        t0 = time.perf_counter()
        if task == 'png':
            oracle_pages = fallback['png'].runners['png'](
                {'input': base.path, 'pdf': sot_pdf}, work / 'sot_pages', dpi
            )
            row['scores'] = score_pages(oracle_pages, output, work / 'scored')
        else:
            row['scores'] = score_pdfs(sot_pdf, output, work / 'scored', dpi=dpi, key=task)
        seconds['score'] = time.perf_counter() - t0
        row['ok'] = True
    except Exception as exc:
        row['error'] = f'{type(exc).__name__}: {exc}'[:600]
    return row


def default_render(renderer: str) -> RenderDocx:
    def render_docx(docx: Path, work: Path) -> Path:
        from neurotic_docx_bench import tryout

        return tryout.render(docx, renderer, work).pdf

    return render_docx


def run(
    tool: Tool,
    docs: Sequence[Doc],
    sot: SotIndex,
    tasks: Sequence[str],
    *,
    fallback: dict[str, Tool],
    render_docx: RenderDocx | None = None,
    renderer: str = 'soffice',
    renderer_version: str | None = None,
    dpi: int = 144,
) -> list[dict[str, Any]]:
    """One row per task. Every intermediate file (PDFs, page PNGs) is deleted on return.
    ``renderer_version`` (default: the soffice fallback's version under soffice) decides
    whether a stored LibreOffice render of Word's compare may stand in for a fresh one."""
    render_docx = render_docx or default_render(renderer)
    if renderer_version is None:
        renderer_version = fallback['convert'].version if renderer == 'soffice' else renderer
    memo: dict = {}
    with tempfile.TemporaryDirectory(prefix='bench-try-remote.') as tmp:
        return [
            run_task(
                task,
                tool,
                docs,
                sot,
                work=Path(tmp),
                fallback=fallback,
                render_docx=render_docx,
                renderer=renderer,
                dpi=dpi,
                memo=memo,
                renderer_version=renderer_version,
            )
            for task in tasks
        ]
