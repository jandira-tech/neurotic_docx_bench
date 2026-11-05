"""Content-addressed render / raster / score cache (plan item 9a).

Every entry is keyed by what determines its bytes: the input file's sha256, the
DPI, the raster engine, the renderer id and a fingerprint of the scoring sources.
A cache hit must reproduce the uncached result exactly and still leave the page
PNGs the gallery reads under the run's work dir.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pymupdf as fitz
import pytest

from neurotic_docx_bench import content_cache as cc
from neurotic_docx_bench import pipeline, raster
from neurotic_docx_bench.render.base import RenderReport, RenderResult

PAGE_A = "Video provides a powerful way to help you prove your point. " * 12
PAGE_B = "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. " * 12


def _make_pdf(path: Path, page_texts: list[str]) -> Path:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        rect = fitz.Rect(72, 72, page.rect.width - 72, page.rect.height - 72)
        page.insert_textbox(rect, text, fontsize=12)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    return path


TIMINGS = {"raster_ns", "score_ns"}


def _untimed(row: Mapping[str, object]) -> dict[str, object]:
    """A scored row minus the wall-clock keys a cache hit does not carry."""
    return {k: v for k, v in row.items() if k not in TIMINGS}


# ---------------------------------------------------------------- keys / fingerprint


def test_sha256_file_is_the_content_hash(tmp_path: Path) -> None:
    p = tmp_path / "x.bin"
    p.write_bytes(b"hello")
    assert cc.sha256_file(p) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"


def test_scorer_fingerprint_tracks_the_scoring_sources(tmp_path: Path, monkeypatch) -> None:
    src = tmp_path / "score.py"
    src.write_text("a = 1\n")
    monkeypatch.setattr(cc, "_scorer_source_files", lambda: [src])
    cc.scorer_fingerprint.cache_clear()
    first = cc.scorer_fingerprint()
    assert len(first) == 16 and int(first, 16) >= 0
    src.write_text("a = 2\n")
    cc.scorer_fingerprint.cache_clear()
    assert cc.scorer_fingerprint() != first
    cc.scorer_fingerprint.cache_clear()


def test_scorer_fingerprint_covers_the_modules_that_make_a_score() -> None:
    names = {p.name for p in cc._scorer_source_files()}
    assert {"score.py", "score_v2.py", "page_metrics.py", "pipeline.py", "raster.py"} <= names


def test_score_key_changes_with_every_component() -> None:
    def key(
        candidate_sha: str = "c" * 64,
        oracle_sha: str = "o" * 64,
        base_sha: str | None = None,
        dpi: int = 144,
        renderer_id: str = "soffice-24.2",
        scorer: str | None = None,
    ) -> str:
        return cc.score_key(
            candidate_sha=candidate_sha, oracle_sha=oracle_sha, base_sha=base_sha,
            dpi=dpi, renderer_id=renderer_id, scorer=scorer,
        )

    ref = key()
    assert ref == key()
    assert key(candidate_sha="d" * 64) != ref
    assert key(oracle_sha="p" * 64) != ref
    assert key(base_sha="b" * 64) != ref
    assert key(dpi=150) != ref
    assert key(renderer_id="word-16.9") != ref
    assert key(scorer="other") != ref


# ---------------------------------------------------------------- score entries


def test_score_entry_round_trips_and_misses_cleanly(tmp_path: Path) -> None:
    cache = cc.ContentCache(tmp_path / "cache")
    key = cc.score_key(candidate_sha="c" * 64, oracle_sha="o" * 64, base_sha=None, dpi=144, renderer_id="x")
    assert cache.get_score(key) is None
    row = {"overall_score": 91.5, "pages": [{"page": 1, "score": 91.5}], "max_break_drift": -3}
    cache.put_score(key, row)
    assert cache.get_score(key) == row
    files = list((tmp_path / "cache" / "score").rglob("*.json"))
    assert len(files) == 1 and json.loads(files[0].read_text()) == row


def test_corrupt_score_entry_is_a_miss(tmp_path: Path) -> None:
    cache = cc.ContentCache(tmp_path / "cache")
    key = cc.score_key(candidate_sha="c" * 64, oracle_sha="o" * 64, base_sha=None, dpi=144, renderer_id="x")
    cache.put_score(key, {"overall_score": 1.0})
    path = next((tmp_path / "cache" / "score").rglob("*.json"))
    path.write_text("{not json")
    assert cache.get_score(key) is None


# ---------------------------------------------------------------- raster entries


def test_rasterize_hits_copy_pages_without_a_second_render(tmp_path: Path, monkeypatch) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", [PAGE_A, PAGE_B])
    cache = cc.ContentCache(tmp_path / "cache")
    calls: list[Path] = []
    real = raster.rasterize_pdf

    def spy(path: Path, out_dir: Path, dpi: int = 144, prefix: str = "page") -> int:
        calls.append(path)
        return real(path, out_dir, dpi=dpi, prefix=prefix)

    monkeypatch.setattr(raster, "rasterize_pdf", spy)
    first = cache.rasterize(pdf, tmp_path / "w1", dpi=144)
    assert [p.name for p in first] == ["page_0001.png", "page_0002.png"]
    assert calls == [pdf]
    second = cache.rasterize(pdf, tmp_path / "w2", dpi=144)
    assert calls == [pdf], "second call must come from the cache"
    assert [p.name for p in second] == ["page_0001.png", "page_0002.png"]
    assert [p.read_bytes() for p in second] == [p.read_bytes() for p in first]
    assert all(p.parent == tmp_path / "w2" for p in second)
    # A different DPI is a different entry.
    cache.rasterize(pdf, tmp_path / "w3", dpi=72)
    assert calls == [pdf, pdf]


def test_partial_raster_entry_is_not_trusted(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "a.pdf", [PAGE_A])
    cache = cc.ContentCache(tmp_path / "cache")
    cache.rasterize(pdf, tmp_path / "w1", dpi=144)
    entry = next((tmp_path / "cache" / "raster").iterdir())
    (entry / cc.COMPLETE_MARKER).unlink()
    (entry / "page_0001.png").write_bytes(b"garbage")
    pages = cache.rasterize(pdf, tmp_path / "w2", dpi=144)
    assert pages[0].read_bytes() != b"garbage"
    assert (entry / cc.COMPLETE_MARKER).exists()


# ---------------------------------------------------------------- render entries


class _FakeRenderer:
    """Behaves like the real backends: writes ``work_dir/pdf/<stem>.pdf`` and skips
    a PDF that is already there."""

    name = "fake"

    def __init__(self) -> None:
        self.rendered: list[str] = []

    def to_pdfs(self, source_dir: Path, work_dir: Path, *, force: bool = False, jobs: int = 12, timeout: float = 1.0) -> RenderReport:
        out = work_dir / "pdf"
        out.mkdir(parents=True, exist_ok=True)
        results = []
        for docx in sorted(source_dir.glob("*.docx")):
            pdf = out / f"{docx.stem}.pdf"
            if pdf.exists() and not force:
                results.append(RenderResult(source=docx, pdf=pdf, ok=True, skipped=True, duration_ns=5))
                continue
            if docx.stem.startswith("bad"):
                results.append(RenderResult(source=docx, pdf=None, ok=False, error="boom", duration_ns=7))
                continue
            self.rendered.append(docx.stem)
            _make_pdf(pdf, [docx.read_text()])
            results.append(RenderResult(source=docx, pdf=pdf, ok=True, duration_ns=1_000_000))
        return RenderReport(pdf_dir=out, results=results)


def test_cached_renderer_restores_pdfs_and_marks_them(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "one.docx").write_text(PAGE_A)
    (src / "two.docx").write_text(PAGE_B)
    (src / "bad.docx").write_text("x")
    cache = cc.ContentCache(tmp_path / "cache")
    inner = _FakeRenderer()
    renderer = cc.CachedRenderer(inner, cache, renderer_id="fake-1")
    assert renderer.name == "fake"

    first = renderer.to_pdfs(src, tmp_path / "run1", jobs=1)
    assert inner.rendered == ["one", "two"]
    assert first.fail_count == 1 and first.ok_count == 2
    assert all(not r.cached for r in first.results)
    assert first.pdf_dir == tmp_path / "run1" / "pdf"

    second = renderer.to_pdfs(src, tmp_path / "run2", jobs=1)
    assert inner.rendered == ["one", "two"], "nothing re-rendered"
    by_stem = {r.source.stem: r for r in second.results}
    assert by_stem["one"].cached and by_stem["one"].ok and by_stem["one"].skipped
    assert by_stem["one"].duration_ns is None, "a restored PDF has no render time"
    restored = by_stem["one"].pdf
    assert restored == tmp_path / "run2" / "pdf" / "one.pdf"
    assert restored is not None
    assert restored.read_bytes() == (tmp_path / "run1" / "pdf" / "one.pdf").read_bytes()
    assert not by_stem["bad"].ok and not by_stem["bad"].cached, "failures are never cached"

    # A changed source is a miss, a changed renderer id too.
    (src / "one.docx").write_text(PAGE_A + " changed")
    renderer.to_pdfs(src, tmp_path / "run3", jobs=1)
    assert inner.rendered == ["one", "two", "one"]
    other = cc.CachedRenderer(_FakeRenderer(), cache, renderer_id="fake-2")
    report = other.to_pdfs(src, tmp_path / "run4", jobs=1)
    assert all(not r.cached for r in report.results)


def test_cached_renderer_force_bypasses_the_cache(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "one.docx").write_text(PAGE_A)
    cache = cc.ContentCache(tmp_path / "cache")
    inner = _FakeRenderer()
    renderer = cc.CachedRenderer(inner, cache, renderer_id="fake-1")
    renderer.to_pdfs(src, tmp_path / "run1", jobs=1)
    renderer.to_pdfs(src, tmp_path / "run2", jobs=1, force=True)
    assert inner.rendered == ["one", "one"]


# ---------------------------------------------------------------- pipeline integration


def test_score_pdf_pair_hit_reproduces_the_row_and_the_gallery_pages(tmp_path: Path, monkeypatch) -> None:
    oracle = _make_pdf(tmp_path / "o.pdf", [PAGE_A, PAGE_B])
    cand = _make_pdf(tmp_path / "c.pdf", [PAGE_A, PAGE_A])
    cache = cc.ContentCache(tmp_path / "cache")
    cold = pipeline.score_pdf_pair(oracle, cand, tmp_path / "w1", cache=cache, renderer_id="r")
    assert cold.get("cached") is None
    assert (tmp_path / "w1" / "c" / "oracle" / "page_0001.png").exists()

    def boom(*a, **k):
        raise AssertionError("scoring must not run on a cache hit")

    monkeypatch.setattr(pipeline, "score_document", boom)
    monkeypatch.setattr(raster, "rasterize_pdf", boom)
    warm = pipeline.score_pdf_pair(oracle, cand, tmp_path / "w2", cache=cache, renderer_id="r")
    assert warm.pop("cached") is True
    # A restored row carries no raster/score timings: those belong to the pass that
    # produced it, like a restored render carries no duration_ns.
    assert not TIMINGS & warm.keys()
    assert _untimed(cold) == warm
    # The gallery reads page PNGs under the run's work dir; a hit must still leave them.
    assert sorted(p.name for p in (tmp_path / "w2" / "c" / "candidate").glob("page_*.png")) == ["page_0001.png", "page_0002.png"]
    assert sorted(p.name for p in (tmp_path / "w2" / "c" / "oracle").glob("page_*.png")) == ["page_0001.png", "page_0002.png"]


def test_score_pdf_pair_without_cache_never_touches_disk_cache(tmp_path: Path) -> None:
    oracle = _make_pdf(tmp_path / "o.pdf", [PAGE_A])
    row = pipeline.score_pdf_pair(oracle, oracle, tmp_path / "w")
    assert "cached" not in row


def test_score_key_includes_the_base_pdf(tmp_path: Path) -> None:
    oracle = _make_pdf(tmp_path / "o.pdf", [PAGE_A, PAGE_B])
    cand = _make_pdf(tmp_path / "c.pdf", [PAGE_A, PAGE_A])
    base = _make_pdf(tmp_path / "b.pdf", [PAGE_B])
    cache = cc.ContentCache(tmp_path / "cache")
    plain = pipeline.score_pdf_pair(oracle, cand, tmp_path / "w1", cache=cache)
    with_base = pipeline.score_pdf_pair(oracle, cand, tmp_path / "w2", cache=cache, base_pdf=base)
    assert "cached" not in with_base, "a base PDF changes the row (null/skill), so it is a different entry"
    assert with_base["null_score"] is not None and plain["null_score"] is None
    again = pipeline.score_pdf_pair(oracle, cand, tmp_path / "w3", cache=cache, base_pdf=base)
    assert again.pop("cached") is True and again == _untimed(with_base)


def test_score_folders_full_threads_the_cache_to_workers(tmp_path: Path, monkeypatch) -> None:
    oracle_dir = tmp_path / "oracle"
    cand_dir = tmp_path / "cand"
    _make_pdf(oracle_dir / "a_b_redline.pdf", [PAGE_A])
    _make_pdf(cand_dir / "a_b_tool_redline.pdf", [PAGE_B])
    cache = cc.ContentCache(tmp_path / "cache")
    cold = pipeline.score_folders_full(oracle_dir, cand_dir, tmp_path / "w1", jobs=1, candidate_tool="tool", cache=cache, renderer_id="r")
    assert list(cold) == ["a_b"] and "cached" not in cold["a_b"]
    monkeypatch.setattr(raster, "rasterize_pdf", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no re-raster")))
    warm = pipeline.score_folders_full(oracle_dir, cand_dir, tmp_path / "w2", jobs=1, candidate_tool="tool", cache=cache, renderer_id="r")
    assert warm["a_b"].pop("cached") is True and warm["a_b"] == _untimed(cold["a_b"])
    for fn in (pipeline.score_folders_plain, pipeline.score_folders_base):
        out = fn(oracle_dir, oracle_dir, tmp_path / "w3", jobs=1, cache=cache)
        assert out, fn.__name__


def test_legacy_task_tuples_still_score(tmp_path: Path) -> None:
    pdf = _make_pdf(tmp_path / "o.pdf", [PAGE_A])
    key, row = pipeline._score_one(("k", pdf, pdf, tmp_path / "w", 144))
    assert key == "k" and row["overall_score"] == pytest.approx(100.0)


# ---------------------------------------------------------------- configuration


def test_from_env_honours_the_switches(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("BENCH_NO_CACHE", raising=False)
    monkeypatch.delenv("BENCH_CACHE_DIR", raising=False)
    default = cc.from_env(tmp_path)
    assert default is not None and default.root == tmp_path / cc.DEFAULT_DIRNAME
    monkeypatch.setenv("BENCH_CACHE_DIR", str(tmp_path / "elsewhere"))
    elsewhere = cc.from_env(tmp_path)
    assert elsewhere is not None
    assert elsewhere.root == tmp_path / "elsewhere"
    monkeypatch.setenv("BENCH_NO_CACHE", "1")
    assert cc.from_env(tmp_path) is None
    assert cc.from_env(tmp_path, enabled=False) is None


def test_configure_and_active(tmp_path: Path) -> None:
    cc.configure(None)
    assert cc.active() is None
    cache = cc.ContentCache(tmp_path / "c")
    cc.configure(cache)
    try:
        assert cc.active() is cache
    finally:
        cc.configure(None)


def test_stats_count_entries_and_bytes(tmp_path: Path) -> None:
    cache = cc.ContentCache(tmp_path / "cache")
    assert cache.stats() == {"render": 0, "raster": 0, "score": 0, "bytes": 0}
    pdf = _make_pdf(tmp_path / "a.pdf", [PAGE_A])
    cache.rasterize(pdf, tmp_path / "w", dpi=144)
    cache.put_score("k" * 64, {"overall_score": 1.0})
    cache.put_render("r", "s" * 64, pdf)
    s = cache.stats()
    assert s["render"] == 1 and s["raster"] == 1 and s["score"] == 1 and s["bytes"] > 0
    cache.clear()
    assert cache.stats() == {"render": 0, "raster": 0, "score": 0, "bytes": 0}


def test_gitignore_hides_the_default_cache_dir() -> None:
    root = Path(__file__).resolve().parents[1]
    assert f"/{cc.DEFAULT_DIRNAME}/" in (root / ".gitignore").read_text().splitlines()
