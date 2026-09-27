"""Content-addressed cache for the three expensive stages of a run: rendering a
source document to PDF, rasterizing a PDF to page PNGs, and scoring a pair.

Layout under ``root`` (``.bench-cache/`` in the repo by default; ``BENCH_CACHE_DIR``
overrides it, ``BENCH_NO_CACHE=1`` or ``bench run --no-cache`` disables it):

    render/<renderer id>/<source sha256>.pdf
    raster/<pdf sha256>-<dpi>-<raster engine>/page_NNNN.png  (+ a completion marker)
    score/<xx>/<key>.json

A score key hashes the candidate sha256, the oracle sha256, the base sha256 (or
none), the DPI, the renderer id and :func:`scorer_fingerprint`, a digest of the
scoring sources and the raster engine version. Any change to how a score is
computed therefore misses instead of returning a stale number, without anyone
remembering to bump a constant.

Entries are written atomically (temp file or directory, then rename), so pool
workers can share a cache without locks. Nothing is ever evicted here; ``bench
cache --clear`` empties the tree.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, replace
from functools import cache as _memo
from pathlib import Path

import pymupdf as fitz

from neurotic_docx_bench import kernels, raster
from neurotic_docx_bench.render.base import Renderer, RenderReport, RenderResult

DEFAULT_DIRNAME = ".bench-cache"
COMPLETE_MARKER = ".complete"
SCHEMA = 1
_SCORER_MODULES = ("score.py", "score_v2.py", "page_metrics.py", "pipeline.py", "raster.py", "kernels.py")
_active: ContentCache | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scorer_source_files() -> list[Path]:
    here = Path(__file__).resolve().parent
    return [here / name for name in _SCORER_MODULES]


def raster_engine() -> str:
    return f"mupdf-{fitz.version[1]}"


@_memo
def scorer_fingerprint() -> str:
    """16 hex chars over the scoring sources, the raster engine and the cache schema."""
    digest = hashlib.sha256(f"schema={SCHEMA};engine={raster_engine()}".encode())
    for src in _scorer_source_files():
        digest.update(src.name.encode())
        digest.update(src.read_bytes())
    return digest.hexdigest()[:16]


def score_key(
    *,
    candidate_sha: str,
    oracle_sha: str,
    base_sha: str | None,
    dpi: int,
    renderer_id: str,
    scorer: str | None = None,
    backend: str | None = None,
) -> str:
    """The score-row key; ``backend`` is the scorer kernel backend (``kernels.backend_id()``
    when omitted), so rows scored on torch never serve a numpy run or vice versa."""
    scorer = scorer if scorer is not None else scorer_fingerprint()
    backend = backend if backend is not None else kernels.backend_id()
    parts = (candidate_sha, oracle_sha, base_sha or "", str(dpi), renderer_id, scorer, backend)
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text) or "_"


@dataclass(frozen=True)
class ContentCache:
    root: Path

    # ---- score rows

    def _score_path(self, key: str) -> Path:
        return self.root / "score" / key[:2] / f"{key}.json"

    def get_score(self, key: str) -> dict | None:
        path = self._score_path(key)
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            return None

    def put_score(self, key: str, row: dict) -> None:
        path = self._score_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(path, json.dumps(row))

    # ---- rasters

    def rasterize(self, pdf: Path, out_dir: Path, *, dpi: int, sha: str | None = None) -> list[Path]:
        """Page PNGs of ``pdf`` at ``dpi`` under ``out_dir`` (which must not hold stale
        pages), copied from the cache when present, rasterized and stored otherwise."""
        sha = sha or sha256_file(pdf)
        entry = self.root / "raster" / f"{sha}-{dpi}-{raster_engine()}"
        out_dir.mkdir(parents=True, exist_ok=True)
        if (entry / COMPLETE_MARKER).exists():
            for png in sorted(entry.glob("page_*.png")):
                shutil.copyfile(png, out_dir / png.name)
        else:
            raster.rasterize_pdf(pdf, out_dir, dpi=dpi)
            self._store_dir(entry, sorted(out_dir.glob("page_*.png")))
        return sorted(out_dir.glob("page_*.png"))

    def _store_dir(self, entry: Path, files: list[Path]) -> None:
        entry.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(tempfile.mkdtemp(prefix=".tmp-", dir=entry.parent))
        for f in files:
            shutil.copyfile(f, tmp / f.name)
        (tmp / COMPLETE_MARKER).write_text("")
        if entry.exists():
            shutil.rmtree(entry, ignore_errors=True)
        try:
            os.replace(tmp, entry)
        except OSError:
            shutil.rmtree(tmp, ignore_errors=True)
            if not (entry / COMPLETE_MARKER).exists():
                raise

    # ---- renders

    def _render_path(self, renderer_id: str, sha: str) -> Path:
        return self.root / "render" / _slug(renderer_id) / f"{sha}.pdf"

    def get_render(self, renderer_id: str, sha: str) -> Path | None:
        path = self._render_path(renderer_id, sha)
        return path if path.is_file() else None

    def put_render(self, renderer_id: str, sha: str, pdf: Path) -> None:
        path = self._render_path(renderer_id, sha)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".tmp-{os.getpid()}-{path.name}")
        shutil.copyfile(pdf, tmp)
        os.replace(tmp, path)

    # ---- housekeeping

    def stats(self) -> dict[str, int]:
        render = sum(1 for _ in (self.root / "render").rglob("*.pdf")) if (self.root / "render").is_dir() else 0
        rasters = sum(1 for _ in (self.root / "raster").glob(f"*/{COMPLETE_MARKER}")) if (self.root / "raster").is_dir() else 0
        score = sum(1 for _ in (self.root / "score").rglob("*.json")) if (self.root / "score").is_dir() else 0
        size = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()) if self.root.is_dir() else 0
        return {"render": render, "raster": rasters, "score": score, "bytes": size}

    def clear(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_name(f".tmp-{os.getpid()}-{path.name}")
    tmp.write_text(text)
    os.replace(tmp, path)


class CachedRenderer:
    """Wrap a :class:`Renderer`: a source whose sha256 was rendered before by the same
    renderer id gets its PDF restored into ``work_dir/pdf`` (the backend then skips
    it), and every fresh successful render is stored. Restored results carry
    ``cached=True`` and no ``duration_ns``: no render happened."""

    def __init__(self, inner: Renderer, cache: ContentCache, *, renderer_id: str) -> None:
        self.inner = inner
        self.cache = cache
        self.renderer_id = renderer_id
        self.name = inner.name

    def to_pdfs(
        self,
        source_dir: Path,
        work_dir: Path,
        *,
        force: bool = False,
        jobs: int = 12,
        **kwargs: object,
    ) -> RenderReport:
        shas = {docx: sha256_file(docx) for docx in sorted(source_dir.glob("*.docx"))}
        restored: set[Path] = set()
        if not force:
            out_dir = work_dir / "pdf"
            for docx, sha in shas.items():
                hit = self.cache.get_render(self.renderer_id, sha)
                target = out_dir / f"{docx.stem}.pdf"
                if hit is not None and not target.exists():
                    out_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(hit, target)
                    restored.add(docx)
        report = self.inner.to_pdfs(source_dir, work_dir, force=force, jobs=jobs, **kwargs)
        results: list[RenderResult] = []
        for r in report.results:
            if r.source in restored:
                results.append(replace(r, skipped=True, cached=True, duration_ns=None))
                continue
            if r.ok and not r.skipped and r.pdf is not None and r.source in shas:
                self.cache.put_render(self.renderer_id, shas[r.source], r.pdf)
            results.append(r)
        return RenderReport(pdf_dir=report.pdf_dir, results=results)


def from_env(repo_root: Path, *, enabled: bool = True) -> ContentCache | None:
    """The cache the CLI should use: None when disabled by flag or ``BENCH_NO_CACHE``."""
    if not enabled or os.environ.get("BENCH_NO_CACHE"):
        return None
    override = os.environ.get("BENCH_CACHE_DIR")
    return ContentCache(Path(override) if override else repo_root / DEFAULT_DIRNAME)


def configure(cache: ContentCache | None) -> None:
    global _active
    _active = cache


def active() -> ContentCache | None:
    return _active
