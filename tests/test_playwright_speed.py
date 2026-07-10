"""Standalone Playwright render-speed benchmark — row shape + stats, without
launching real Chromium (the render callable is injectable).

The methodology mirrors ``superdoc_speed`` / ``scripts/speed-bench.ts``: init
(browser + harness server) timed separately, warmup, reps, per-call high-res
sampling, failures excluded from timing stats, full distribution. Output is a
``results/speed.jsonl`` row with ``unit: "ms_per_render"`` so render-speed is
distinct from the generation-speed rows (``ms_per_redline``).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from neurotic_docx_bench import playwright_speed
from neurotic_docx_bench.render.base import RenderResult


def _fake_render_factory(path_delay_ms: float = 5.0):
    """Return a render_fn that produces a successful RenderResult with a fixed
    synthetic ``duration_ns`` (so no real browser/page is needed). ``duration_ns``
    is what the bench reads for its per-call timing — a fixed value keeps the
    distribution deterministic and the assertions stable.
    """

    def render_fn(page, docx: Path, out_dir: Path, *, force: bool) -> RenderResult:
        pdf = out_dir / f"{docx.stem}.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        return RenderResult(
            source=docx, pdf=pdf, ok=True,
            duration_ns=int(path_delay_ms * 1_000_000),
        )

    return render_fn


def test_run_emits_speed_row_with_render_unit(tmp_path: Path) -> None:
    docs = [tmp_path / "a_b_redline.docx", tmp_path / "c_d_redline.docx"]
    for d in docs:
        d.write_bytes(b"PK fake docx")

    row = playwright_speed.run(
        docs=docs,
        reps=3,
        warmup=1,
        render_fn=_fake_render_factory(path_delay_ms=4.0),
        tool="folio-playwright",
        url="http://127.0.0.1:5175/harness.html",
        init_ms=42.0,
    )

    # Identity + schema markers.
    assert row["schema"] == 1
    assert row["kind"] == "speed"
    assert row["tool"] == "folio-playwright"
    assert row["runtime"] == "python"
    # Render-speed is its own unit, distinct from generation (ms_per_redline).
    assert row["unit"] == "ms_per_render"
    # init timed separately, never mixed into per-call samples.
    assert row["init_ms"] == 42.0
    # 2 docs × 3 reps = 6 samples (warmup is untimed and excluded).
    assert row["n"] == 6
    assert row["failures"] == 0
    # Full distribution present.
    for k in ("mean", "median", "p90", "p95", "p99", "min", "max", "std",
              "total", "throughput_per_s"):
        assert k in row, f"missing stat {k}"
    # Every sample is 4.0 ms → the whole distribution collapses to 4.0.
    assert row["min"] == 4.0
    assert row["max"] == 4.0
    assert row["median"] == 4.0
    assert row["std"] == 0.0


def test_run_excludes_failures_from_timing(tmp_path: Path) -> None:
    docs = [tmp_path / "ok_redline.docx", tmp_path / "bad_redline.docx"]
    for d in docs:
        d.write_bytes(b"PK fake docx")

    def render_fn(page, docx: Path, out_dir: Path, *, force: bool) -> RenderResult:
        if docx.stem.startswith("bad"):
            return RenderResult(source=docx, pdf=None, ok=False, error="boom",
                                duration_ns=1_000_000)
        pdf = out_dir / f"{docx.stem}.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake")
        return RenderResult(source=docx, pdf=pdf, ok=True, duration_ns=5_000_000)

    row = playwright_speed.run(
        docs=docs, reps=2, warmup=0,
        render_fn=render_fn, tool="t", url="http://x", init_ms=0.0,
    )
    # 1 ok doc × 2 reps = 2 timed samples; the failing doc is counted, not timed.
    assert row["n"] == 2
    assert row["failures"] == 2
    assert row["median"] == 5.0


def test_main_appends_row_to_speed_jsonl(tmp_path: Path, monkeypatch) -> None:
    """CLI wiring: arg-parse → row → append. The browser launch is patched out
    (the ``_run_with_browser`` seam) so this stays deterministic and browser-free;
    a fake render_fn exercises ``run`` for real.
    """
    docs_dir = tmp_path / "docx"
    docs_dir.mkdir()
    (docs_dir / "a_b_redline.docx").write_bytes(b"PK fake docx")

    def fake_run_with_browser(harness, docs, reps, warmup, tool, url, *, t0):
        return playwright_speed.run(
            docs=docs, reps=reps, warmup=warmup,
            render_fn=_fake_render_factory(path_delay_ms=3.0),
            tool=tool, url=url,
            init_ms=(time.perf_counter() - t0) * 1000.0,
        )

    monkeypatch.setattr(playwright_speed, "_run_with_browser", fake_run_with_browser)

    out = tmp_path / "speed.jsonl"
    rc = playwright_speed.main([
        "--docx-dir", str(docs_dir),
        "--pairs", "1", "--reps", "2", "--warmup", "0",
        "--out", str(out),
        "--tool", "folio-playwright",
        "--url", "http://127.0.0.1:5175/harness.html",
    ])
    assert rc == 0
    lines = out.read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["unit"] == "ms_per_render"
    assert row["tool"] == "folio-playwright"
    assert row["n"] == 2  # 1 doc × 2 reps


def test_init_ms_includes_browser_launch(tmp_path: Path, monkeypatch) -> None:
    """``init_ms`` must cover the browser launch, not just the harness server —
    otherwise it's not comparable to the generation-speed rows' ``init_ms`` (which
    times engine init). A fake Playwright whose ``launch()`` sleeps proves the launch
    is inside the timed window.
    """
    docs_dir = tmp_path / "docx"
    docs_dir.mkdir()
    (docs_dir / "a_b_redline.docx").write_bytes(b"PK fake docx")

    BROWSER_LAUNCH_MS = 60.0

    class _FakeBrowser:
        def new_context(self):
            class _Ctx:
                def new_page(self): return None
                def close(self): pass
            return _Ctx()

        def close(self): pass

    class _FakePW:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        @property
        def chromium(self):
            class _C:
                def launch(_self):
                    time.sleep(BROWSER_LAUNCH_MS / 1000.0)
                    return _FakeBrowser()
            return _C()

    monkeypatch.setattr(playwright_speed, "_sync_playwright", lambda: _FakePW())
    # The real _render_one needs a live page; patch _default_render_fn so the fake
    # page (None) is accepted and the render "succeeds" — we're testing init timing,
    # not render. _default_render_fn(harness) must itself return a render_fn.
    monkeypatch.setattr(
        playwright_speed, "_default_render_fn",
        lambda harness: _fake_render_factory(path_delay_ms=2.0),
    )

    out = tmp_path / "speed.jsonl"
    rc = playwright_speed.main([
        "--docx-dir", str(docs_dir), "--pairs", "1", "--reps", "1", "--warmup", "0",
        "--out", str(out), "--tool", "t", "--url", "http://127.0.0.1:5175/harness.html",
    ])
    assert rc == 0
    row = json.loads(out.read_text().strip())
    # The browser launch alone took ~60ms, so init_ms must be ≥ that (server=0 here).
    assert row["init_ms"] >= BROWSER_LAUNCH_MS - 5.0  # small slack


def test_main_no_row_when_all_fail(tmp_path: Path, monkeypatch) -> None:
    """When every render fails, no row is appended and main returns non-zero —
    matching ``scripts/speed-bench.ts`` (which skips emission on 0 samples) so a
    bogus zero-row never lands in the trend log.
    """
    docs_dir = tmp_path / "docx"
    docs_dir.mkdir()
    (docs_dir / "a_b_redline.docx").write_bytes(b"PK fake docx")

    def failing_render_fn(page, docx, out_dir, *, force):
        return RenderResult(source=docx, pdf=None, ok=False, error="boom")

    def fake_run_with_browser(harness, docs, reps, warmup, tool, url, *, t0):
        return playwright_speed.run(
            docs=docs, reps=reps, warmup=warmup,
            render_fn=failing_render_fn, tool=tool, url=url,
            init_ms=(time.perf_counter() - t0) * 1000.0,
        )

    monkeypatch.setattr(playwright_speed, "_run_with_browser", fake_run_with_browser)

    out = tmp_path / "speed.jsonl"
    rc = playwright_speed.main([
        "--docx-dir", str(docs_dir), "--pairs", "1", "--reps", "1", "--warmup", "0",
        "--out", str(out), "--tool", "t", "--url", "http://127.0.0.1:5175/harness.html",
    ])
    assert rc != 0
    assert not out.exists() or out.read_text() == ""
