"""``bench try``: score one tryout fixture through any tool and compare it with jubarte.

The tryout set is 100 fixture pairs drawn once from
``corpus/no_comments_pdf_was_generated_by_word`` (the corpus whose PDFs Microsoft Word
exported itself), recorded in ``corpus/tryout/tryout_100.csv`` with the sha256 of every
file, and shipped with jubarte's precomputed outputs under ``corpus/tryout/jubarte/``.
A Hugging Face Space (or anyone) picks one fixture, random or by name, runs a tool on
it, and gets the tool's score against the Word oracle next to jubarte's score against
the same oracle.

Every function here is a plain function over paths so the Space can call them without
the CLI; network happens only in :func:`fetch`, through the injected ``api``.

Tasks: ``redline`` (inputs ``{base}`` and ``{next}`` docx; oracle
``pdf_redline_word``; jubarte output ``jubarte/redline/<pair>_jubarte_redline.pdf``)
and ``convert`` (input ``{input}`` = the base docx; oracle ``pdf_base_word``; jubarte
output ``jubarte/convert/<base>_jubarte.pdf``).

Nothing is written under ``results/``.
"""

from __future__ import annotations

import csv
import difflib
import json
import random
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from neurotic_docx_bench import content_cache, pipeline
from neurotic_docx_bench.hub import sha256_file
from neurotic_docx_bench.render.base import Renderer

SET_SIZE = 100
SET_SEED = 20260927
SET_NAME = "tryout_100.csv"
CORPUS = Path("corpus/no_comments_pdf_was_generated_by_word")
HOLDOUTS = (Path("corpus/holdout_combined.txt"), Path("corpus/word_based/holdout.txt"))
TRYOUT_DIR = Path("corpus/tryout")
JUBARTE_SUBDIR = "jubarte"
JUBARTE_MANIFEST = "MANIFEST.json"
HUB_PREFIX = Path("corpus")  # the fixtures dataset is rooted at corpus/
WORD_VARIANT = "_word_redline"
PLAIN_VARIANT = "_redline"
TASKS = ("redline", "convert")
RENDERERS = ("passthrough", "soffice", "word")
FILE_COLUMNS = (
    "docx_base",
    "docx_next",
    "pdf_base_word",
    "pdf_next_word",
    "docx_redline_word",
    "pdf_redline_word",
    "docx_accepted_word",
    "pdf_accepted_word",
)
SET_COLUMNS = ("pair_stem", "base", "next", *FILE_COLUMNS, *(f"sha256_{c}" for c in FILE_COLUMNS))
ORACLE_COLUMN = {"redline": "pdf_redline_word", "convert": "pdf_base_word"}
PLACEHOLDERS = {"redline": ("{base}", "{next}"), "convert": ("{input}",)}


class TryoutError(Exception):
    """A tryout step refused to proceed; the message says why."""


@dataclass(frozen=True)
class Fixture:
    pair_stem: str
    base: str
    next: str
    files: dict[str, Path]  # column -> path relative to the repository root
    sha256: dict[str, str]  # column -> sha256 of that file

    def path(self, column: str, root: Path) -> Path:
        return root / self.files[column]

    def to_dict(self) -> dict[str, Any]:
        return {
            "pair_stem": self.pair_stem,
            "base": self.base,
            "next": self.next,
            "files": {k: v.as_posix() for k, v in self.files.items()},
            "sha256": dict(self.sha256),
        }


@dataclass(frozen=True)
class TryoutSet:
    root: Path
    csv_path: Path
    sha256: str
    fixtures: tuple[Fixture, ...]

    @property
    def stems(self) -> list[str]:
        return [f.pair_stem for f in self.fixtures]

    def get(self, stem: str) -> Fixture:
        for fixture in self.fixtures:
            if fixture.pair_stem == stem:
                return fixture
        raise TryoutError(f"no fixture {stem!r} in {self.csv_path}; {_closest(stem, self.stems)}")


@dataclass(frozen=True)
class Pick:
    fixture: Fixture
    seed: int | None


@dataclass(frozen=True)
class ToolRun:
    command: list[str]
    output: Path
    seconds: float


@dataclass(frozen=True)
class Rendered:
    pdf: Path
    renderer_id: str
    seconds: float = 0.0


@dataclass(frozen=True)
class TryReport:
    fixture: Fixture
    task: str
    oracle: Path
    tool: dict[str, Any]
    against: dict[str, Any]
    against_label: str
    delta: float
    sha256: dict[str, str]
    renderer_id: str
    scorer_fingerprint: str
    raster_engine: str
    dpi: int
    timings: dict[str, float] = field(default_factory=dict)
    seed: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture": self.fixture.to_dict(),
            "task": self.task,
            "oracle": self.oracle.as_posix(),
            "tool": self.tool,
            "against": self.against,
            "against_label": self.against_label,
            "delta": self.delta,
            "sha256": dict(self.sha256),
            "renderer_id": self.renderer_id,
            "scorer_fingerprint": self.scorer_fingerprint,
            "raster_engine": self.raster_engine,
            "dpi": self.dpi,
            "timings": dict(self.timings),
            "seed": self.seed,
        }


# --- the set --------------------------------------------------------------------


def _closest(stem: str, stems: list[str]) -> str:
    near = difflib.get_close_matches(stem, stems, n=3, cutoff=0.0)
    return "closest: " + ", ".join(near) if near else "the set is empty"


def read_holdout(path: Path) -> set[str]:
    """Stems listed in a holdout file; blank lines and ``#`` comments are skipped."""
    if not path.is_file():
        return set()
    out: set[str] = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def word_variant(directory: Path, stem: str, suffix: str) -> Path | None:
    """``<stem>_word_redline<suffix>`` when it exists, else ``<stem>_redline<suffix>``,
    else None (the same preference as ``pipeline._index_redlines``)."""
    for variant in (WORD_VARIANT, PLAIN_VARIANT):
        candidate = directory / f"{stem}{variant}{suffix}"
        if candidate.is_file():
            return candidate
    return None


def eligible_pairs(root: Path, corpus: Path = CORPUS, holdouts: tuple[Path, ...] = HOLDOUTS) -> list[Fixture]:
    """Mapping rows whose eight files all exist and whose stem is on no holdout, sorted
    by ``pair_stem``. The mapping supplies only ``pair_stem``, ``base`` and ``next``;
    every file is located on the filesystem. ``sha256`` is left empty here."""
    root = Path(root)
    holdout: set[str] = set()
    for h in holdouts:
        holdout |= read_holdout(root / h)
    mapping = root / corpus / "centralized_mapping.csv"
    if not mapping.is_file():
        raise TryoutError(f"{mapping} is missing")
    pairs: list[Fixture] = []
    with mapping.open(newline="") as fh:
        for row in csv.DictReader(fh):
            stem = row["pair_stem"]
            if stem in holdout:
                continue
            located = {
                "docx_redline_word": word_variant(root / corpus / "docx_redlines_word", stem, ".docx"),
                "pdf_redline_word": word_variant(root / corpus / "pdf_redlines_word", stem, ".pdf"),
                "docx_accepted_word": word_variant(root / corpus / "docx_accepted_word", stem, ".docx"),
                "pdf_accepted_word": word_variant(root / corpus / "pdf_accepted_word", stem, ".pdf"),
            }
            if any(p is None for p in located.values()):
                continue
            files: dict[str, Path] = {
                "docx_base": corpus / "docx_source" / f"{row['base']}.docx",
                "docx_next": corpus / "docx_source" / f"{row['next']}.docx",
                "pdf_base_word": corpus / "pdf_source" / f"{row['base']}.pdf",
                "pdf_next_word": corpus / "pdf_source" / f"{row['next']}.pdf",
            }
            files.update({k: p.relative_to(root) for k, p in located.items() if p is not None})
            if not all((root / p).is_file() for p in files.values()):
                continue
            pairs.append(Fixture(pair_stem=stem, base=row["base"], next=row["next"], files=files, sha256={}))
    pairs.sort(key=lambda f: f.pair_stem)
    return pairs


def build_set(root: Path, *, size: int = SET_SIZE, seed: int = SET_SEED, corpus: Path = CORPUS) -> list[Fixture]:
    """``size`` eligible pairs drawn with ``random.Random(seed)``, sorted, with sha256."""
    root = Path(root)
    pool = eligible_pairs(root, corpus)
    if len(pool) < size:
        raise TryoutError(f"{len(pool)} eligible pairs in {corpus}, fewer than the {size} asked for")
    chosen = sorted(random.Random(seed).sample(pool, size), key=lambda f: f.pair_stem)
    return [
        Fixture(
            pair_stem=f.pair_stem,
            base=f.base,
            next=f.next,
            files=dict(f.files),
            sha256={column: sha256_file(root / path) for column, path in f.files.items()},
        )
        for f in chosen
    ]


def write_set(root: Path, fixtures: list[Fixture], *, name: str = SET_NAME) -> Path:
    path = Path(root) / TRYOUT_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer: csv.DictWriter[str] = csv.DictWriter(fh, fieldnames=list(SET_COLUMNS))
        writer.writeheader()
        for f in fixtures:
            row: dict[str, str] = {"pair_stem": f.pair_stem, "base": f.base, "next": f.next}
            for column in FILE_COLUMNS:
                row[column] = f.files[column].as_posix()
                row[f"sha256_{column}"] = f.sha256[column]
            writer.writerow(row)
    return path


def load_set(root: Path, *, name: str = SET_NAME) -> TryoutSet:
    """Read ``corpus/tryout/<name>`` under ``root``; refuse an older layout."""
    root = Path(root)
    path = root / TRYOUT_DIR / name
    if not path.is_file():
        raise TryoutError(f"{path} is missing; run `bench try build-set` or `bench try fetch`")
    fixtures: list[Fixture] = []
    with path.open(newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in SET_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise TryoutError(f"{path} lacks column(s) {', '.join(missing)}: an older set; rebuild it with --force")
        for row in reader:
            fixtures.append(
                Fixture(
                    pair_stem=row["pair_stem"],
                    base=row["base"],
                    next=row["next"],
                    files={c: Path(row[c]) for c in FILE_COLUMNS},
                    sha256={c: row[f"sha256_{c}"] for c in FILE_COLUMNS},
                )
            )
    return TryoutSet(root=root, csv_path=path, sha256=sha256_file(path), fixtures=tuple(fixtures))


def verify_set(tryout: TryoutSet, fixtures: tuple[Fixture, ...] | None = None) -> list[str]:
    """Paths (relative, posix) whose file is missing or whose sha256 differs from the CSV."""
    bad: list[str] = []
    for f in fixtures if fixtures is not None else tryout.fixtures:
        for column, rel in f.files.items():
            path = tryout.root / rel
            if not path.is_file() or sha256_file(path) != f.sha256[column]:
                bad.append(rel.as_posix())
    return bad


# --- picking ---------------------------------------------------------------------


def pick(tryout: TryoutSet, *, stem: str | None = None, seed: int | None = None) -> Pick:
    """By ``stem`` (exact) or at random; without a seed one is drawn from
    ``SystemRandom`` and reported so the pick can be repeated."""
    if not tryout.fixtures:
        raise TryoutError(f"{tryout.csv_path} holds no fixtures")
    if stem is not None:
        return Pick(fixture=tryout.get(stem), seed=None)
    if seed is None:
        seed = random.SystemRandom().randrange(1, 2**31)
    return Pick(fixture=random.Random(seed).choice(tryout.fixtures), seed=seed)


# --- the tool ---------------------------------------------------------------------


def run_tool(
    template: str,
    fixture: Fixture,
    task: str,
    out_dir: Path,
    *,
    root: Path,
    ext: str = "pdf",
    timeout: float = 600.0,
) -> ToolRun:
    """Run ``template`` (a shell-style command with ``{base}`` ``{next}`` ``{out}`` for
    redline, ``{input}`` ``{out}`` for convert) and return the output it wrote."""
    if task not in TASKS:
        raise TryoutError(f"unknown task {task!r}; one of {', '.join(TASKS)}")
    tokens = shlex.split(template)
    for needed in (*PLACEHOLDERS[task], "{out}"):
        if not any(needed in t for t in tokens):
            raise TryoutError(f"the tool template lacks {needed}: {template!r}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = fixture.pair_stem if task == "redline" else fixture.base
    output = out_dir / f"{stem}_{task}.{ext.lstrip('.')}"
    if output.exists():
        output.unlink()
    values = {
        "{base}": str(fixture.path("docx_base", root)),
        "{next}": str(fixture.path("docx_next", root)),
        "{input}": str(fixture.path("docx_base", root)),
        "{out}": str(output),
    }
    command: list[str] = []
    for token in tokens:
        for key, value in values.items():
            token = token.replace(key, value)
        command.append(token)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise TryoutError(f"tool not found: {command[0]!r}") from exc
    except subprocess.TimeoutExpired as exc:
        raise TryoutError(f"tool timed out after {timeout:.0f}s: {shlex.join(command)}") from exc
    seconds = time.perf_counter() - t0
    stderr = " ".join(proc.stderr.split())
    if proc.returncode != 0:
        raise TryoutError(f"tool exit {proc.returncode}: {shlex.join(command)}; stderr: {stderr}")
    if not output.is_file():
        raise TryoutError(f"tool did not write {output}: {shlex.join(command)}; stderr: {stderr}")
    return ToolRun(command=command, output=output, seconds=seconds)


# --- rendering --------------------------------------------------------------------


def _default_renderer(backend: str) -> tuple[Renderer, str]:
    if backend == "soffice":
        from neurotic_docx_bench import hardware
        from neurotic_docx_bench.render.soffice import SofficeRenderer

        return SofficeRenderer(), f"soffice-{hardware.soffice_version() or 'unknown'}"
    if backend == "word":
        from neurotic_docx_bench.render.word import WordRenderer

        return WordRenderer(), "word"
    raise TryoutError(f"unknown renderer {backend!r}; one of {', '.join(RENDERERS)}")


def render(
    path: Path,
    backend: str,
    work_dir: Path,
    *,
    renderer: Renderer | None = None,
    renderer_id: str | None = None,
) -> Rendered:
    """The PDF to score: ``path`` itself for ``passthrough`` (it must be a PDF), else
    the render of ``path``'s folder by ``backend`` (or the injected ``renderer``)."""
    path = Path(path)
    if backend == "passthrough":
        if path.suffix.lower() != ".pdf":
            raise TryoutError(f"passthrough needs a PDF, the tool wrote {path.name}; pass --renderer soffice or word")
        return Rendered(pdf=path, renderer_id="passthrough")
    if renderer is None:
        renderer, default_id = _default_renderer(backend)
        renderer_id = renderer_id or default_id
    elif backend not in RENDERERS:
        raise TryoutError(f"unknown renderer {backend!r}; one of {', '.join(RENDERERS)}")
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    report = renderer.to_pdfs(path.parent, work_dir)
    seconds = time.perf_counter() - t0
    for result in report.results:
        if result.source == path and result.ok and result.pdf is not None:
            return Rendered(pdf=result.pdf, renderer_id=renderer_id or backend, seconds=seconds)
    errors = "; ".join(r.error or "no PDF" for r in report.results if not r.ok) or "no PDF for the tool's output"
    raise TryoutError(f"{backend} did not render {path.name}: {errors}")


# --- scoring ----------------------------------------------------------------------


def jubarte_output(tryout: TryoutSet, fixture: Fixture, task: str) -> Path:
    """Where the set keeps jubarte's precomputed PDF for ``fixture`` and ``task``."""
    if task not in TASKS:
        raise TryoutError(f"unknown task {task!r}; one of {', '.join(TASKS)}")
    base = tryout.root / TRYOUT_DIR / JUBARTE_SUBDIR
    if task == "redline":
        return base / "redline" / f"{fixture.pair_stem}_jubarte_redline.pdf"
    return base / "convert" / f"{fixture.base}_jubarte.pdf"


def score_against(
    oracle_pdf: Path,
    candidate_pdf: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    key: str,
    base_pdf: Path | None = None,
    renderer_id: str = "",
) -> dict[str, Any]:
    """``pipeline.score_pdf_pair`` reduced to what a tryout shows: the pagefair overall,
    the raw overall, page counts, the change-region scores when ``base_pdf`` is
    given, and the rasterized page paths."""
    work_dir = Path(work_dir)
    result = pipeline.score_pdf_pair(
        Path(oracle_pdf), Path(candidate_pdf), work_dir, dpi=dpi, key=key, base_pdf=base_pdf, renderer_id=renderer_id
    )
    pages_root = work_dir / key
    return {
        "overall": pipeline.overall_from_result(result),
        "overall_raw": float(result["overall_score"]),
        "page_count_oracle": int(result["page_count_oracle"]),
        "page_count_candidate": int(result["page_count_candidate"]),
        "page_count_mismatch": bool(result["page_count_mismatch"]),
        "null_score": result.get("null_score"),
        "skill_score": result.get("skill_score"),
        "score_v2": result.get("score_v2"),
        "raster_s": float(result.get("raster_ns", 0)) / 1e9,
        "score_s": float(result.get("score_ns", 0)) / 1e9,
        "pages": {
            "oracle": [p.as_posix() for p in sorted((pages_root / "oracle").glob("page_*.png"))],
            "candidate": [p.as_posix() for p in sorted((pages_root / "candidate").glob("page_*.png"))],
        },
    }


def compare(
    tryout: TryoutSet,
    fixture: Fixture,
    task: str,
    candidate_pdf: Path,
    work_dir: Path,
    *,
    dpi: int = 144,
    renderer_id: str,
    against_pdf: Path | None = None,
    against_label: str | None = None,
    timings: dict[str, float] | None = None,
    seed: int | None = None,
) -> TryReport:
    """Score ``candidate_pdf`` and the comparison PDF (jubarte's precomputed output by
    default) against the fixture's Word oracle for ``task``."""
    if task not in TASKS:
        raise TryoutError(f"unknown task {task!r}; one of {', '.join(TASKS)}")
    oracle_rel = fixture.files[ORACLE_COLUMN[task]]
    oracle_pdf = tryout.root / oracle_rel
    if against_pdf is None:
        against_pdf = jubarte_output(tryout, fixture, task)
        against_label = against_label or "jubarte"
        if not against_pdf.is_file():
            raise TryoutError(
                f"jubarte's precomputed output is missing: {against_pdf}; "
                "run scripts/tryout_jubarte.py or `bench try fetch`"
            )
    against_label = against_label or str(against_pdf)
    base_pdf = fixture.path("pdf_base_word", tryout.root) if task == "redline" else None
    work_dir = Path(work_dir)
    tool_scores = score_against(
        oracle_pdf, candidate_pdf, work_dir, dpi=dpi, key="tool", base_pdf=base_pdf, renderer_id=renderer_id
    )
    against_scores = score_against(
        oracle_pdf, against_pdf, work_dir, dpi=dpi, key="against", base_pdf=base_pdf, renderer_id=""
    )
    return TryReport(
        fixture=fixture,
        task=task,
        oracle=oracle_rel,
        tool=tool_scores,
        against=against_scores,
        against_label=against_label,
        delta=tool_scores["overall"] - against_scores["overall"],
        sha256={
            "oracle": fixture.sha256[ORACLE_COLUMN[task]],
            "candidate": sha256_file(Path(candidate_pdf)),
            "against": sha256_file(against_pdf),
        },
        renderer_id=renderer_id,
        scorer_fingerprint=content_cache.scorer_fingerprint(),
        raster_engine=content_cache.raster_engine(),
        dpi=dpi,
        timings=dict(timings or {}),
        seed=seed,
    )


# --- the hub ----------------------------------------------------------------------


class FileApi(Protocol):
    """The slice of ``huggingface_hub.HfApi`` :func:`fetch` uses: one file at a time."""

    def hf_hub_download(
        self,
        repo_id: str,
        filename: str,
        *,
        repo_type: str,
        revision: str | None = None,
        local_dir: str | Path | None = None,
    ) -> str: ...


def _hub_path(rel: Path) -> str:
    """A repository-relative path as the fixtures dataset stores it (rooted at corpus/)."""
    return rel.relative_to(HUB_PREFIX).as_posix()


def fetch(repo_id: str, revision: str | None, stem: str, dest: Path, *, api: FileApi) -> tuple[TryoutSet, Fixture]:
    """Download the set CSV, jubarte's manifest, and the one fixture ``stem`` (its eight
    files and jubarte's two outputs) under ``dest``, verifying every sha256."""
    from neurotic_docx_bench.hub import REPO_TYPE

    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    local = dest / HUB_PREFIX

    def get(rel: Path) -> Path:
        try:
            api.hf_hub_download(repo_id, _hub_path(rel), repo_type=REPO_TYPE, revision=revision, local_dir=local)
        except FileNotFoundError as exc:
            raise TryoutError(f"{repo_id}@{revision or 'main'} has no {_hub_path(rel)}") from exc
        return dest / rel

    get(TRYOUT_DIR / SET_NAME)
    manifest_path = get(TRYOUT_DIR / JUBARTE_SUBDIR / JUBARTE_MANIFEST)
    tryout = load_set(dest)
    fixture = tryout.get(stem)
    for rel in fixture.files.values():
        get(rel)
    bad = verify_set(tryout, (fixture,))
    if bad:
        raise TryoutError(f"sha256 mismatch after download for: {', '.join(bad)}")
    outputs = json.loads(manifest_path.read_text()).get("outputs", {})
    for task in TASKS:
        rel = jubarte_output(tryout, fixture, task).relative_to(dest)
        path = get(rel)
        expected = outputs.get(rel.as_posix(), {}).get("sha256")
        if expected is None:
            raise TryoutError(f"{JUBARTE_MANIFEST} does not list {rel.as_posix()}")
        if sha256_file(path) != expected:
            raise TryoutError(f"{JUBARTE_MANIFEST} sha256 mismatch for {rel.as_posix()}")
    return tryout, fixture
