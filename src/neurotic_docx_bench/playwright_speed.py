"""Meticulous Playwright RENDER-speed benchmark.

Companion to ``scripts/speed-bench.ts`` (Node generation) and ``superdoc_speed``
(Python generation): this measures how long a web viewer takes to *render* a DOCX
to a rasterisable PDF — the cost the ``visual_*`` benchmarks pay per document,
isolated from generation. Same rigor: init (browser + harness server) timed
separately, warmup, reps, per-call high-res sampling, failures excluded from the
timing stats, full distribution.

Output: one ``results/speed.jsonl`` row with ``unit: "ms_per_render"`` (distinct
from the generation rows' ``ms_per_redline``), so render-speed and generation-speed
never get conflated.

Usage:
  uv run python -m neurotic_docx_bench.playwright_speed \
    --docx-dir corpus/word_based/docx_redlines_word \
    --pairs 30 --reps 3 --warmup 3 --out results/speed.jsonl \
    --tool folio-playwright --url http://127.0.0.1:5175/harness.html \
    --file-input "#fileInput" --page-selector ".layout-page" \
    --readiness-js "window.__folioReady === true" --timeout-ms 90000

The harness server is auto-started when ``--server`` is given (the shell command
from the run's ``harness.server``); otherwise the user is expected to have started
it (e.g. ``bench serve folio-playwright``).
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from neurotic_docx_bench.render.base import RenderResult
from neurotic_docx_bench.speed_stats import stats as _stats

RenderFn = Callable[..., RenderResult]
PageProvider = Callable[[], "tuple[Any, Callable[[], None]]"]


def _default_render_fn(harness: dict[str, Any]) -> RenderFn:
    """Bind a real ``PlaywrightRenderer._render_one`` to a harness profile."""
    from neurotic_docx_bench.render.playwright import PlaywrightRenderer

    renderer = PlaywrightRenderer(harness)
    return renderer._render_one  # noqa: SLF001 — same instance method the bench uses


def _static_page_provider(page: Any | None) -> PageProvider:
    """A page provider that always returns the same (page, no-op closer).

    Used by tests whose fake ``render_fn`` ignores the page argument entirely.
    """
    def provide() -> tuple[Any, Callable[[], None]]:
        return page, lambda: None
    return provide


def run(
    *,
    docs: list[Path],
    reps: int,
    warmup: int,
    render_fn: RenderFn,
    tool: str,
    url: str,
    init_ms: float,
    page_provider: PageProvider | None = None,
) -> dict:
    """Run the render-speed loop and return one ``speed.jsonl`` row.

    ``render_fn(page, docx, out_dir, *, force) -> RenderResult`` is the timed
    callable; its ``RenderResult.duration_ns`` is the per-call walltime (the same
    field the bench reads). ``page_provider()`` returns a fresh ``(page, closer)``
    per call — the real path gives each render its own browser context (mirroring
    ``PlaywrightRenderer.to_pdfs``, so a stale readiness flag from doc N-1 can't
    short-circuit doc N's wait). Tests pass a static provider (or none → a
    ``None`` page) since their fake ``render_fn`` ignores the page.

    Init (browser + harness server) is passed in as ``init_ms`` and never mixed
    into per-call samples.
    """
    out_dir = Path(_mkdtemp())
    samples: list[float] = []
    failures = 0
    provider = page_provider or _static_page_provider(None)

    def _one(docx: Path) -> RenderResult | None:
        page, close = provider()
        try:
            return render_fn(page, docx, out_dir, force=True)
        finally:
            close()

    n_warmup = min(warmup, len(docs)) if docs else 0
    for w in range(n_warmup):  # warmup (untimed)
        try:
            _one(docs[w])
        except Exception:  # noqa: BLE001 — warmup failures don't count
            pass

    for _ in range(max(0, reps)):
        for docx in docs:
            t0 = time.perf_counter()
            try:
                result = _one(docx)
            except Exception:  # noqa: BLE001 — a throw is a failure, not a sample
                failures += 1
                continue
            if result is None or not result.ok:
                failures += 1
                continue
            # Prefer the renderer's own duration_ns (consistent with the bench);
            # fall back to the outer timer if a fake render_fn didn't set it.
            ns = result.duration_ns if result.duration_ns is not None else (time.perf_counter() - t0) * 1e9
            samples.append(ns / 1e6)

    row: dict[str, Any] = {
        "schema": 1,
        "kind": "speed",
        "tool": tool,
        "runtime": "python",
        "unit": "ms_per_render",
        "init_ms": round(init_ms, 3),
        "failures": failures,
        "url": url,
        **_stats(samples),
    }
    return row


def _mkdtemp() -> str:
    import tempfile

    return tempfile.mkdtemp(prefix="pw-speed.")


def _start_server(server_cmd: str, url: str, timeout_s: float) -> Any:
    """Start the harness dev server (mirrors cli._start_harness_server) and poll
    ``url`` until ready. Returns the Popen handle (caller stops it).
    """
    import subprocess
    from urllib.error import URLError
    from urllib.request import urlopen

    proc = subprocess.Popen(
        server_cmd, shell=True, cwd=str(Path.cwd()),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as resp:  # noqa: S310 — localhost dev server
                if resp.status == 200:
                    return proc
        except (URLError, OSError, TimeoutError):
            pass
        time.sleep(0.5)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    raise RuntimeError(f"harness server did not become ready at {url} within {timeout_s:.0f}s")


def _stop_server(proc: Any) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:  # noqa: BLE001
        proc.kill()


def _run_with_browser(
    harness: dict[str, Any], docs: list[Path], reps: int, warmup: int, tool: str, url: str,
    *, t0: float,
) -> dict:
    """Real path: launch Chromium, bind ``PlaywrightRenderer._render_one``, run.

    ``t0`` is the init-window start (set in ``main`` before the harness server
    starts); ``init_ms`` is computed **after** ``browser.launch()`` so it covers
    server startup + Chromium launch — the full one-time cost, comparable to the
    generation-speed rows' ``init_ms`` (which times engine init).

    Each timed render gets a fresh browser context + page (then closed) — exactly
    what ``PlaywrightRenderer.to_pdfs`` does, so a doc's readiness flag can't leak
    into the next and the per-call timing reflects the bench's real per-doc cost.
    """
    with _sync_playwright() as pw:
        browser = pw.chromium.launch()
        init_ms = (time.perf_counter() - t0) * 1000.0
        try:
            render_fn = _default_render_fn(harness)

            def fresh_page():
                ctx = browser.new_context()
                try:
                    page = ctx.new_page()
                except Exception:
                    ctx.close()
                    raise
                return page, ctx.close

            return run(
                docs=docs, reps=reps, warmup=warmup,
                render_fn=render_fn, tool=tool, url=url, init_ms=init_ms,
                page_provider=fresh_page,
            )
        finally:
            browser.close()


def _sync_playwright():
    """Indirection so tests can monkeypatch the Playwright entry point."""
    from playwright.sync_api import sync_playwright

    return sync_playwright()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Playwright render-speed benchmark")
    p.add_argument("--docx-dir", required=True, help="folder of DOCX to render")
    p.add_argument("--pairs", type=int, default=30, help="cap on number of docs")
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--warmup", type=int, default=3)
    p.add_argument("--out", default="results/speed.jsonl")
    p.add_argument("--tool", required=True, help="tool label for the row (e.g. folio-playwright)")
    p.add_argument("--url", required=True, help="harness URL to drive")
    p.add_argument("--file-input", default="#fileInput")
    p.add_argument("--page-selector", default="")
    p.add_argument("--readiness-js", default="")
    p.add_argument("--hide", default="", help="comma-separated selectors to hide")
    p.add_argument("--timeout-ms", type=int, default=60000)
    p.add_argument("--server", default="", help="harness server shell command (auto-started)")
    p.add_argument("--server-timeout-s", type=float, default=30.0)
    p.add_argument("--run-ts", default="")
    args = p.parse_args(argv)

    src = Path(args.docx_dir)
    docs = sorted(src.glob("*.docx"))[: args.pairs]
    if not docs:
        print(f"playwright-speed: no .docx in {src}", flush=True)
        return 1
    print(f"playwright-speed: {len(docs)} docs, reps={args.reps}, warmup={args.warmup}", flush=True)

    harness: dict[str, Any] = {"url": args.url, "file_input": args.file_input}
    if args.page_selector:
        harness["page_selector"] = args.page_selector
    if args.readiness_js:
        harness["readiness_js"] = args.readiness_js
    if args.hide:
        harness["hide"] = [s.strip() for s in args.hide.split(",") if s.strip()]
    harness["timeout_ms"] = args.timeout_ms

    # Init = harness server (if any) + browser launch. ``t0`` starts before the
    # server; ``_run_with_browser`` computes ``init_ms`` AFTER ``browser.launch()``
    # so the full one-time cost (server + Chromium) is captured, never mixed into
    # per-call samples.
    t0 = time.perf_counter()
    server_proc = _start_server(args.server, args.url, args.server_timeout_s) if args.server else None
    try:
        row = _run_with_browser(
            harness, docs, args.reps, args.warmup, args.tool, args.url, t0=t0,
        )
    finally:
        _stop_server(server_proc)

    # Match scripts/speed-bench.ts: when every call failed (n==0), do not append a
    # bogus zero-row to the trend log — report and exit non-zero instead.
    if row["n"] == 0:
        print(
            f"playwright-speed: all {row['failures']} render calls failed; no row written",
            flush=True,
        )
        return 1

    row["run_ts"] = args.run_ts
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(
        f"  {args.tool}  init {row['init_ms']:.0f}ms  median {row['median']:.1f}ms  "
        f"mean {row['mean']:.1f}ms  p95 {row['p95']:.1f}ms  "
        f"{row['throughput_per_s']:.2f}/s  (n={row['n']}, fail={row['failures']})",
        flush=True,
    )
    print(f"wrote 1 row → {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
