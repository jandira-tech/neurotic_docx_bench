"""Playwright renderer — verified against a minimal local harness (proves the upload →
readiness → page.pdf contract; real superdoc/react-docxodus-viewer harnesses are config).
"""

from __future__ import annotations

import functools
import http.server
import shutil
import socketserver
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pymupdf as fitz
import pytest

HARNESS_DIR = Path(__file__).resolve().parent / "harness"

try:
    from playwright.sync_api import sync_playwright  # noqa: F401

    _HAVE_PW = True
except Exception:  # pragma: no cover
    _HAVE_PW = False

requires_playwright = pytest.mark.skipif(not _HAVE_PW, reason="playwright not installed")


class _Server(socketserver.TCPServer):
    allow_reuse_address = True


@pytest.fixture
def harness_server() -> Iterator[str]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HARNESS_DIR))
    with _Server(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            yield f"http://127.0.0.1:{port}/minimal.html"
        finally:
            httpd.shutdown()


@requires_playwright
def test_playwright_renders_docx_to_pdf(
    tmp_path: Path, harness_server: str, sample_docx: list[Path],
) -> None:
    from neurotic_docx_bench.render.playwright import PlaywrightRenderer

    docx_dir = tmp_path / "in"
    docx_dir.mkdir()
    shutil.copy(sample_docx[0], docx_dir / sample_docx[0].name)

    renderer = PlaywrightRenderer(
        {
            "url": harness_server,
            "file_input": "#fileInput",
            "page_selector": ".page",
            "readiness_js": "window.__ready === true",
        },
    )
    report = renderer.to_pdfs(docx_dir, tmp_path / "work")
    assert report.ok_count == 1, [(r.source.name, r.error) for r in report.results]
    pdf = report.pdfs[0]
    with fitz.open(pdf) as doc:
        assert doc.page_count >= 1


@requires_playwright
def test_playwright_records_duration_ns(
    tmp_path: Path, harness_server: str, sample_docx: list[Path],
) -> None:
    """Every Playwright RenderResult carries ``duration_ns`` — the per-doc walltime is
    what feeds the render-speed distribution for visual_* benchmarks (soffice already
    does this; Playwright must too so its render cost is measurable).
    """
    from neurotic_docx_bench.render.playwright import PlaywrightRenderer

    docx_dir = tmp_path / "in"
    docx_dir.mkdir()
    shutil.copy(sample_docx[0], docx_dir / sample_docx[0].name)

    renderer = PlaywrightRenderer(
        {
            "url": harness_server,
            "file_input": "#fileInput",
            "page_selector": ".page",
            "readiness_js": "window.__ready === true",
        },
    )
    report = renderer.to_pdfs(docx_dir, tmp_path / "work")
    assert report.ok_count == 1
    [result] = report.results
    assert result.duration_ns is not None
    assert result.duration_ns > 0


@requires_playwright
def test_playwright_records_duration_ns_on_skip(
    tmp_path: Path, harness_server: str, sample_docx: list[Path],
) -> None:
    """A skipped render (PDF already present) still records ``duration_ns`` — the
    soffice backend does this so the timing contract is uniform across backends; a
    None here would make a re-run's speed stats silently empty.
    """
    from neurotic_docx_bench.render.playwright import PlaywrightRenderer

    docx_dir = tmp_path / "in"
    docx_dir.mkdir()
    shutil.copy(sample_docx[0], docx_dir / sample_docx[0].name)

    work = tmp_path / "work"
    renderer = PlaywrightRenderer(
        {
            "url": harness_server,
            "file_input": "#fileInput",
            "page_selector": ".page",
            "readiness_js": "window.__ready === true",
        },
    )
    first = renderer.to_pdfs(docx_dir, work)
    assert first.ok_count == 1
    # Second call without --force: PDF exists → skip, but duration_ns must still be set.
    again = renderer.to_pdfs(docx_dir, work, force=False)
    assert again.ok_count == 1
    skipped = next(r for r in again.results if r.skipped)
    assert skipped.duration_ns is not None


def test_playwright_requires_harness() -> None:
    from neurotic_docx_bench.render.playwright import PlaywrightRenderer

    with pytest.raises(ValueError, match="harness"):
        PlaywrightRenderer(None)
    with pytest.raises(ValueError, match="harness"):
        PlaywrightRenderer({"url": "http://x"})  # missing file_input


@requires_playwright
def test_playwright_fail_fast_on_error_js(
    tmp_path: Path, sample_docx: list[Path],
) -> None:
    """Viewer conversion errors must not become 60s selector timeouts.

    Mirrors the docxodus WASM failure mode: window.__rdvError is set immediately
    with ArgumentNull…part while [data-page-number] never appears. The renderer
    races readiness against error_js and returns the real error in < timeout.
    """
    from neurotic_docx_bench.render.playwright import PlaywrightRenderer

    harness_dir = tmp_path / "err_harness"
    harness_dir.mkdir()
    (harness_dir / "index.html").write_text(
        """<!doctype html>
<meta charset="utf-8" />
<input id="fileInput" type="file" />
<script>
  window.__ready = false;
  window.__err = "";
  document.getElementById("fileInput").addEventListener("change", () => {
    // Simulate WASM conversion crash before any page chrome is painted.
    window.__err = "ArgumentNull_Generic Arg_ParamName_Name, part";
  });
</script>
""",
        encoding="utf-8",
    )

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(harness_dir),
    )
    with _Server(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            url = f"http://127.0.0.1:{port}/index.html"
            docx_dir = tmp_path / "in"
            docx_dir.mkdir()
            shutil.copy(sample_docx[0], docx_dir / sample_docx[0].name)

            renderer = PlaywrightRenderer(
                {
                    "url": url,
                    "file_input": "#fileInput",
                    "page_selector": ".page",
                    "readiness_js": "window.__ready === true",
                    "error_js": "window.__err",
                    "reject_blank": False,
                    "timeout_ms": 15000,
                },
            )
            t0 = time.perf_counter()
            report = renderer.to_pdfs(docx_dir, tmp_path / "work")
            elapsed = time.perf_counter() - t0
        finally:
            httpd.shutdown()

    assert report.ok_count == 0
    assert report.fail_count == 1
    [result] = report.results
    assert result.error is not None
    assert "ArgumentNull_Generic" in result.error
    # Must fail fast — well under a 15s timeout budget (was 60s+ before).
    assert elapsed < 5.0, f"expected fail-fast, took {elapsed:.1f}s"


@requires_playwright
def test_playwright_rejects_blank_shell(
    tmp_path: Path, sample_docx: list[Path],
) -> None:
    """Page chrome without text/media is a blank shell, not a successful render.

    The broken readiness_js OR `[data-page-number].length > 0` previously accepted
    white empty page boxes (docxodus visual_rendering text_box / mcdoc shells).
    """
    from neurotic_docx_bench.render.playwright import PlaywrightRenderer

    harness_dir = tmp_path / "blank_harness"
    harness_dir.mkdir()
    (harness_dir / "index.html").write_text(
        """<!doctype html>
<meta charset="utf-8" />
<style>
  .page { width: 620px; min-height: 820px; background: #fff; }
</style>
<input id="fileInput" type="file" />
<div id="out"></div>
<script>
  window.__ready = false;
  document.getElementById("fileInput").addEventListener("change", () => {
    const div = document.createElement("div");
    div.className = "page";
    div.setAttribute("data-page-number", "1");
    // Intentionally empty — white chrome only.
    document.getElementById("out").appendChild(div);
    requestAnimationFrame(() => { window.__ready = true; });
  });
</script>
""",
        encoding="utf-8",
    )

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(harness_dir),
    )
    with _Server(("127.0.0.1", 0), handler) as httpd:
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            url = f"http://127.0.0.1:{port}/index.html"
            docx_dir = tmp_path / "in"
            docx_dir.mkdir()
            shutil.copy(sample_docx[0], docx_dir / sample_docx[0].name)

            renderer = PlaywrightRenderer(
                {
                    "url": url,
                    "file_input": "#fileInput",
                    "page_selector": ".page",
                    "readiness_js": "window.__ready === true",
                    "reject_blank": True,
                    "timeout_ms": 10000,
                },
            )
            report = renderer.to_pdfs(docx_dir, tmp_path / "work")
        finally:
            httpd.shutdown()

    assert report.ok_count == 0
    assert report.fail_count == 1
    assert report.results[0].error is not None
    assert "blank render" in report.results[0].error
